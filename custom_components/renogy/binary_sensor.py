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
        for (
            binary_sensor
        ) in BINARY_SENSORS:  # pylint: disable=consider-using-dict-items
            unique_id = device["serial"] or device_id
            temp_obj = RenogyBinarySensor(
                BINARY_SENSORS[binary_sensor],
                unique_id,
                device_id,
                coordinator,
                entry,
            )
            if (
                binary_sensor in device.keys()
            ):  # pylint: disable=consider-using-dict-items
                if temp_obj not in binary_sensors:
                    binary_sensors.append(temp_obj)
            if binary_sensor in device["data"].keys():
                if temp_obj not in binary_sensors:
                    binary_sensors.append(temp_obj)

    async_add_devices(binary_sensors, False)


class RenogyBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Implementation of an OpenEVSE binary sensor."""

    def __init__(
        self,
        sensor_description: BinarySensorEntityDescription,
        unique_id: str,
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
        self._unique_id = unique_id
        self._device_id = device_id

        self._attr_name = f"{coordinator.data[device_id]["name"]} {self._name}"
        self._attr_unique_id = f"{self._name}_{self._unique_id}"

    @property
    def device_info(self) -> dict:
        """Return a port description for device registry."""
        info = {
            "connections": {(DOMAIN, self._unique_id)},
        }

        return info

    @property
    def is_on(self) -> bool:
        """Return True if the service is on."""
        data = self.coordinator.data[self._device_id]
        if self._type in data.keys():
            if self._type == "status":
                if data[self._type] == "online":
                    return True
                return False

        data = self.coordinator.data[self._device_id]["data"]
        if self._type not in data.keys():
            _LOGGER.info("binary_sensor [%s] not supported.", self._type)
            return None
        _LOGGER.debug("binary_sensor [%s]: %s", self._name, data[self._type])
        return cast(bool, data[self._type] == 1)
