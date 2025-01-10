"""The renogy component."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from renogyapi import Renogy as api

from .const import (
    CONF_ACCESS_KEY,
    CONF_NAME,
    CONF_SECRET_KEY,
    COORDINATOR,
    DOMAIN,
    ISSUE_URL,
    MANAGER,
    PLATFORMS,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup(  # pylint: disable-next=unused-argument
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Disallow configuration via YAML."""
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up is called when Home Assistant is loading our component."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info(
        "Version %s is starting, if you have any issues please report them here: %s",
        VERSION,
        ISSUE_URL,
    )

    manager = RenogyManager(hass, config_entry).api
    interval = 30
    coordinator = RenogyUpdateCoordinator(hass, interval, config_entry, manager)

    # Fetch initial data so we have data when entities subscribe
    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
        MANAGER: manager,
    }

    device_registry = dr.async_get(hass)
    hub = await async_find_hub(coordinator)
    for (
        device_id,
        device,
    ) in coordinator.data.items():
        _LOGGER.debug("DEVICE: %s", device)
        if "serial" in device.keys() and device["serial"] != "":
            serial = device["serial"]
        else:
            serial = device_id

        device_check = device_registry.async_get_device(identifiers=(DOMAIN, serial))
        if device_check is not None:
            # Device already exists or duplicate serial number
            # swap to device_id instead
            serial = device_id

        via = (DOMAIN, hub) if serial != hub and hub else None

        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, device["mac"])},
            identifiers={(DOMAIN, serial)},
            serial_number=serial,
            name=device["name"],
            manufacturer="Renogy",
            model=device["name"],
            model_id=device["model"],
            sw_version=device["firmware"],
            via_device=via,
        )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)

    return True


async def async_find_hub(coordinator) -> bool:
    """Find and return hub."""
    hub = None
    for (
        device_id,
        device,
    ) in coordinator.data.items():
        _LOGGER.debug("Looking for hub device...")
        if device["connection"] == "Hub":
            if "serial" in device.keys() and device["serial"] != "":
                hub = device["serial"]
            else:
                hub = device_id

    return hub


async def async_remove_config_entry_device(  # pylint: disable-next=unused-argument
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device if its no longer present."""
    return not any(
        identifier
        for identifier in device_entry.identifiers
        if identifier[0] == DOMAIN
        and config_entry.runtime_data.get_device(identifier[1])
    )


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Handle removal of an entry."""
    _LOGGER.debug("Attempting to unload entities from the %s integration", DOMAIN)

    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(config_entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok:
        _LOGGER.debug("Successfully removed entities from the %s integration", DOMAIN)

    return unload_ok


class RenogyUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching OpenEVSE data."""

    def __init__(self, hass, interval, config, manager):
        """Initialize."""
        self.interval = timedelta(seconds=interval)
        self.name = f"({config.data.get(CONF_NAME)})"
        self.config = config
        self.hass = hass
        self._manager = manager
        self._data = {}

        _LOGGER.debug("Data will be update every %s", self.interval)

        super().__init__(hass, _LOGGER, name=self.name, update_interval=self.interval)

    async def _async_update_data(self):
        """Return data."""
        await self.update_sensors()
        return self._data

    async def update_sensors(self) -> dict:
        """Update sensor data."""
        try:
            self._data = await self._manager.get_devices()
        except RuntimeError:
            pass
        except Exception as error:
            _LOGGER.debug(
                "Error updating sensors [%s]: %s", type(error).__name__, error
            )
            raise UpdateFailed(error) from error

        _LOGGER.debug("Coordinator data: %s", self._data)


class RenogyManager:
    """OpenEVSE connection manager."""

    def __init__(  # pylint: disable-next=unused-argument
        self, hass: HomeAssistant, config_entry: ConfigEntry
    ) -> None:
        """Initialize."""
        self._secret_key = config_entry.data.get(CONF_SECRET_KEY)
        self._access_key = config_entry.data.get(CONF_ACCESS_KEY)
        self.api = api(secret_key=self._secret_key, access_key=self._access_key)
