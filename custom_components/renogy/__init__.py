"""The renogy component."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from renogyapi import Renogy as api

from .const import (
    BLE_TO_HA_KEY_MAP,
    CONF_ACCESS_KEY,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_MAC_ADDRESS,
    CONF_NAME,
    CONF_SECRET_KEY,
    CONNECTION_TYPE_BLE,
    COORDINATOR,
    DEFAULT_DEVICE_ID,
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

    connection_type = config_entry.data.get(CONF_CONNECTION_TYPE, "cloud")

    if connection_type == CONNECTION_TYPE_BLE:
        return await _async_setup_ble_entry(hass, config_entry)
    return await _async_setup_cloud_entry(hass, config_entry)


# ==========================================================================
# Cloud API setup (original path)
# ==========================================================================


async def _async_setup_cloud_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Set up cloud API integration."""
    manager = RenogyManager(hass, config_entry).api
    interval = 30
    coordinator = RenogyUpdateCoordinator(hass, interval, config_entry, manager)

    await coordinator.async_refresh()

    if not coordinator.last_update_success:
        raise ConfigEntryNotReady

    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
        MANAGER: manager,
    }

    _register_cloud_devices(hass, config_entry, coordinator)

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


def _register_cloud_devices(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    coordinator: RenogyUpdateCoordinator,
) -> None:
    """Register cloud API devices."""
    device_registry = dr.async_get(hass)
    mac = []
    for device_id, device in coordinator.data.items():
        _LOGGER.debug("DEVICE: %s", device)
        if "serial" in device.keys() and device["serial"] != "":
            serial = device["serial"]
        else:
            serial = None

        via = (
            (DOMAIN, device["parent"])
            if "parent" in device.keys()
            and device_id != device["parent"]
            and device["parent"]
            else None
        )

        network_mac = device["mac"] if device["mac"] not in mac else device_id
        mac.append(device["mac"])

        _LOGGER.debug("Using device: %s via %s", device_id, via)

        device_registry.async_get_or_create(
            config_entry_id=config_entry.entry_id,
            connections={(dr.CONNECTION_NETWORK_MAC, network_mac)},
            identifiers={(DOMAIN, device_id)},
            serial_number=serial,
            name=device["name"],
            manufacturer="Renogy",
            model=device["name"],
            model_id=device["model"],
            sw_version=device["firmware"],
            via_device=via,
        )


# ==========================================================================
# BLE setup
# ==========================================================================


async def _async_setup_ble_entry(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> bool:
    """Set up BLE integration."""
    from .ble_client import BLEDeviceManager, DeviceConfig  # noqa: E402

    mac_address = config_entry.data.get(CONF_MAC_ADDRESS, "")
    device_type = config_entry.data.get(CONF_DEVICE_TYPE, "controller")
    device_id = config_entry.data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID)
    device_name = config_entry.data.get(CONF_NAME, "Renogy BLE")

    device_config = DeviceConfig(
        name=device_name,
        mac_address=mac_address,
        device_type=device_type,
        device_id=device_id,
    )

    ble_manager = BLEDeviceManager(hass, [device_config])

    interval = 30
    coordinator = BLEUpdateCoordinator(hass, interval, config_entry, ble_manager)

    # Store in hass.data immediately so async_unload_entry can clean up
    # even if the initial refresh fails mid-way through platform setup.
    hass.data[DOMAIN][config_entry.entry_id] = {
        COORDINATOR: coordinator,
        MANAGER: ble_manager,
    }

    try:
        await coordinator.async_refresh()
    except Exception as err:
        # Disconnect BLEDeviceManager to avoid leaked connections
        await ble_manager.disconnect_all()
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
        raise ConfigEntryNotReady(f"BLE initial refresh failed: {err}") from err

    if not coordinator.last_update_success:
        await ble_manager.disconnect_all()
        hass.data[DOMAIN].pop(config_entry.entry_id, None)
        raise ConfigEntryNotReady("BLE coordinator refresh was unsuccessful")

    # Register BLE device in device registry
    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=config_entry.entry_id,
        identifiers={(DOMAIN, f"ble_{mac_address}")},
        name=device_name,
        manufacturer="Renogy",
        model=f"Renogy {device_type.title()} (BLE)",
        connections={(dr.CONNECTION_NETWORK_MAC, mac_address)},
    )

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


# ==========================================================================
# Shared lifecycle
# ==========================================================================


async def async_remove_config_entry_device(  # pylint: disable-next=unused-argument
    hass: HomeAssistant, config_entry: ConfigEntry, device_entry: dr.DeviceEntry
) -> bool:
    """Remove config entry from a device if its no longer present."""
    if not hasattr(config_entry, "runtime_data"):
        return True
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

        # Disconnect BLE if applicable
        entry_data = hass.data[DOMAIN].get(config_entry.entry_id, {})
        manager = entry_data.get(MANAGER)
        if hasattr(manager, "disconnect_all"):
            await manager.disconnect_all()

        hass.data[DOMAIN].pop(config_entry.entry_id, None)

    return unload_ok


# ==========================================================================
# Coordinators
# ==========================================================================


class RenogyUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Renogy data via Cloud API."""

    def __init__(self, hass, interval, config, manager):
        """Initialize."""
        self.interval = timedelta(seconds=interval)
        self.name = f"({config.data.get(CONF_NAME)})"
        self.config = config
        self.hass = hass
        self._manager = manager
        self._data = {}

        _LOGGER.debug("Data will be update every %s", self.interval)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config,
            name=self.name,
            update_interval=self.interval,
        )

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


class BLEUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Renogy data via BLE."""

    def __init__(self, hass, interval, config, ble_manager):
        """Initialize."""
        from .ble_validator import DataValidatorManager  # noqa: E402

        self.interval = timedelta(seconds=interval)
        self.name = f"({config.data.get(CONF_NAME)})"
        self.config = config
        self.hass = hass
        self._ble_manager = ble_manager
        self._validator = DataValidatorManager()
        self._data = {}

        _LOGGER.debug("BLE data will be updated every %s", self.interval)

        super().__init__(
            hass,
            _LOGGER,
            config_entry=config,
            name=self.name,
            update_interval=self.interval,
        )

    async def _async_update_data(self):
        """Fetch data from BLE devices."""
        try:
            raw_results = await self._ble_manager.poll_all()
        except Exception as error:
            _LOGGER.debug("Error polling BLE [%s]: %s", type(error).__name__, error)
            raise UpdateFailed(error) from error

        if not raw_results:
            if self._data:
                return self._data
            raise UpdateFailed("No data received from BLE device")

        # Translate BLE keys to HA sensor keys and build coordinator data
        for _, raw_data in raw_results.items():
            device_name = raw_data.get("__device", "Renogy BLE")
            device_type = raw_data.get("__device_type", "controller")
            mac_address = raw_data.get("__mac_address", "")
            device_id = f"ble_{mac_address}"

            # Validate data (spike detection for controllers)
            validated_data, rejections = self._validator.validate_device_data(
                device_name, device_type, raw_data
            )
            if rejections:
                _LOGGER.debug("Rejected %s values for %s", len(rejections), device_name)

            # Translate keys
            translated = {}
            for ble_key, value in validated_data.items():
                if ble_key.startswith("__"):
                    continue
                ha_key = BLE_TO_HA_KEY_MAP.get(ble_key, ble_key)
                translated[ha_key] = value

            # Build device data structure compatible with cloud API format
            model = validated_data.get("model", f"Renogy {device_type.title()}")
            self._data[device_id] = {
                "name": device_name,
                "model": model,
                "firmware": validated_data.get("firmware_version", ""),
                "serial": "",
                "mac": mac_address,
                "connection": "Bluetooth",
                "data": {k: (v, "") for k, v in translated.items()},
            }

        _LOGGER.debug("BLE Coordinator data: %s", self._data)
        return self._data


# ==========================================================================
# Cloud API manager
# ==========================================================================


class RenogyManager:
    """Renogy connection manager."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize."""
        self._secret_key = config_entry.data.get(CONF_SECRET_KEY)
        self._access_key = config_entry.data.get(CONF_ACCESS_KEY)
        self.api = api(
            secret_key=self._secret_key,
            access_key=self._access_key,
            session=async_get_clientsession(hass),
        )
