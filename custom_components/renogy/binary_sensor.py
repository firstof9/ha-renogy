"""Binary sensors for Renogy devices."""

import logging
from typing import cast

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import BINARY_SENSORS, COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_devices):
    """Set up binary_sensor platform."""
    coordinator = hass.data[DOMAIN][entry.entry_id][COORDINATOR]

    binary_sensors = []
    for device_id, device in coordinator.data.items():
        for key, spec in BINARY_SENSORS.items():
            if key in device or key in device["data"]:
                binary_sensors.append(
                    RenogyBinarySensor(
                        spec,
                        device_id,
                        coordinator,
                        entry,
                    )
                )

    async_add_devices(binary_sensors, False)


class RenogyBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of an OpenEVSE binary sensor."""

    def __init__(
        self,
        sensor_description: BinarySensorEntityDescription,
        device_id: str,
        coordinator: DataUpdateCoordinator,
        config: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.coordinator = coordinator
        self._config = config
        self.entity_description = sensor_description
        self._name = sensor_description.name
        self._type = sensor_description.key
        self._device_id = device_id

        self._attr_name = f"{coordinator.data[device_id]['name']} {self._name}"
        self._attr_unique_id = f"{self._name}_{device_id}"

    @property
    def device_info(self) -> dict:
        """Return a port description for device registry."""
        info = {
            "identifiers": {(DOMAIN, self._device_id)},
        }

        return info

    @property
    def is_on(self) -> bool:
        """Return True if the service is on."""
        data = self.coordinator.data[self._device_id]
        if self._type in data:
            if self._type == "status":
                return data[self._type] == "online"

        data = self.coordinator.data[self._device_id].get("data")
        if data is None or self._type not in data:
            _LOGGER.info("binary_sensor [%s] not supported.", self._type)
            return False
        _LOGGER.debug("binary_sensor [%s]: %s", self._name, data[self._type][0])
        return cast(bool, data[self._type][0] == 1)
