"""Binary sensors for Renogy devices."""

import logging
from typing import cast

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from . import RenogyConfigEntry
from .const import BINARY_SENSORS, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry: RenogyConfigEntry, async_add_devices) -> None:
    """Set up binary_sensor platform."""
    coordinator = entry.runtime_data.coordinator

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
    """Implementation of a Renogy binary sensor."""

    def __init__(
        self,
        sensor_description: BinarySensorEntityDescription,
        device_id: str,
        coordinator: DataUpdateCoordinator,
        config: RenogyConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config = config
        self.entity_description = sensor_description
        self._name = sensor_description.name
        self._type = sensor_description.key
        self._device_id = device_id

        device_data = (
            coordinator.data.get(device_id, {})
            if isinstance(coordinator.data, dict)
            else {}
        )
        device_name = device_data.get("name", device_id)
        self._attr_name = f"{device_name} {self._name}"
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
        if (
            not isinstance(self.coordinator.data, dict)
            or self._device_id not in self.coordinator.data
        ):
            return False
        data = self.coordinator.data[self._device_id]
        if self._type in data:
            if self._type == "status":
                return data[self._type] == "online"

        data = data.get("data")
        if data is None or self._type not in data:
            _LOGGER.info("binary_sensor [%s] not supported.", self._type)
            return False
        _LOGGER.debug("binary_sensor [%s]: %s", self._name, data[self._type][0])
        return cast(bool, data[self._type][0] == 1)
