"""
Data validation module for Renogy BLE devices.

Implements spike detection and validation to filter out erroneous readings,
particularly from the Rover 40 charge controller which can occasionally
produce invalid data spikes.

Adapted from https://github.com/Anto79-ops/renogy-ble
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_LOGGER = logging.getLogger(__name__)

# Base validation limits for a 12V system: (min, max, max_change_per_update)
_CONTROLLER_BASE_LIMITS: Dict[str, Tuple[float, float, float]] = {
    # Battery sensors
    "battery_voltage": (0, 20, 5),
    "battery_current": (-100, 100, 50),
    "battery_percentage": (0, 100, 50),
    "battery_temperature": (-40, 85, 20),
    "charging_amp_hours_today": (0, 10000, 200),
    "discharging_amp_hours_today": (0, 10000, 200),
    # PV (solar panel) sensors
    "pv_voltage": (0, 30, 10),
    "pv_current": (0, 100, 50),
    "pv_power": (0, 5000, 2000),
    "max_charging_power_today": (0, 5000, 5000),
    "power_generation_today": (0, 50000, 50000),
    "power_generation_total": (0, 1000000000, 100000),
    # Load sensors
    "load_voltage": (0, 20, 20),
    "load_current": (0, 20, 20),
    "load_power": (0, 3000, 1500),
    "power_consumption_today": (0, 50000, 50000),
    "max_discharging_power_today": (0, 3000, 3000),
    # Controller sensors
    "controller_temperature": (-40, 85, 20),
}

# Keys whose max and max_change scale with system voltage
_VOLTAGE_SCALED_KEYS = {"battery_voltage", "pv_voltage", "load_voltage"}


def get_controller_validation_limits(
    system_voltage: int = 12,
) -> Dict[str, Tuple[float, float, float]]:
    """Return controller validation limits scaled for the given system voltage.

    Voltage-dependent keys (battery_voltage, pv_voltage, load_voltage) have
    their max and max_change values multiplied by a factor derived from the
    system voltage (12V → 1×, 24V → 2×, 48V → 4×).

    Args:
        system_voltage: Nominal system voltage (12, 24, or 48).

    Returns:
        Dictionary of (min, max, max_change_per_update) tuples.
    """
    multiplier = max(system_voltage / 12, 1.0)
    limits: Dict[str, Tuple[float, float, float]] = {}
    for key, (min_val, max_val, max_change) in _CONTROLLER_BASE_LIMITS.items():
        if key in _VOLTAGE_SCALED_KEYS:
            limits[key] = (min_val, max_val * multiplier, max_change * multiplier)
        else:
            limits[key] = (min_val, max_val, max_change)
    return limits


class DataValidator:
    """Validates sensor data and detects invalid spikes.

    Maintains history of last known good values and rejection logs.
    """

    def __init__(
        self,
        device_name: str,
        device_type: str = "controller",
        system_voltage: int = 12,
    ) -> None:
        """Initialize the data validator.

        Args:
            device_name: Name of the device for logging.
            device_type: Type of device ('controller', 'battery', 'inverter').
            system_voltage: Nominal system voltage (12, 24, or 48).
        """
        self.device_name = device_name
        self.device_type = device_type
        self._last_good_values: Dict[str, float] = {}
        self._rejection_log: List[Dict[str, Any]] = []
        self._max_rejection_log = 100

        if device_type == "controller":
            self._limits = get_controller_validation_limits(system_voltage)
        else:
            self._limits: Dict[str, tuple] = {}

    def validate_data(
        self, data: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Validate sensor data and replace invalid values with last known good values.

        Args:
            data: Dictionary of sensor readings.

        Returns:
            Tuple of (validated_data, list_of_rejections).
        """
        if not self._limits:
            return data, []

        validated = data.copy()
        rejections: List[Dict[str, Any]] = []

        for key, value in data.items():
            if key not in self._limits:
                continue

            if not isinstance(value, (int, float)):
                continue

            min_val, max_val, max_change = self._limits[key]
            rejection_reason = None

            if value < min_val:
                rejection_reason = (
                    f"below_minimum (value={value}, min={min_val})"
                )
            elif value > max_val:
                rejection_reason = (
                    f"above_maximum (value={value}, max={max_val})"
                )

            if rejection_reason is None and key in self._last_good_values:
                last_value = self._last_good_values[key]
                change = abs(value - last_value)
                if change > max_change:
                    rejection_reason = (
                        f"spike_detected (value={value}, last={last_value}, "
                        f"change={change:.2f}, max_change={max_change})"
                    )

            if rejection_reason:
                rejection = {
                    "timestamp": datetime.now().isoformat(),
                    "sensor": key,
                    "rejected_value": value,
                    "reason": rejection_reason,
                    "last_good_value": self._last_good_values.get(key),
                }
                rejections.append(rejection)
                self._add_to_rejection_log(rejection)

                _LOGGER.warning(
                    "[%s] Data rejected: %s=%s - %s",
                    self.device_name,
                    key,
                    value,
                    rejection_reason,
                )

                if key in self._last_good_values:
                    validated[key] = self._last_good_values[key]
            else:
                self._last_good_values[key] = value

        return validated, rejections

    def _add_to_rejection_log(self, rejection: Dict[str, Any]) -> None:
        """Add a rejection to the log, maintaining max size."""
        self._rejection_log.append(rejection)
        if len(self._rejection_log) > self._max_rejection_log:
            self._rejection_log = self._rejection_log[-self._max_rejection_log :]

    def get_rejection_stats(self) -> Dict[str, Any]:
        """Get statistics about recent rejections."""
        if not self._rejection_log:
            return {
                "total_rejections": 0,
                "recent_rejections": [],
                "rejection_counts_by_sensor": {},
            }

        counts: Dict[str, int] = {}
        for rejection in self._rejection_log:
            sensor = rejection["sensor"]
            counts[sensor] = counts.get(sensor, 0) + 1

        recent = self._rejection_log[-5:]

        return {
            "total_rejections": len(self._rejection_log),
            "recent_rejections": recent,
            "rejection_counts_by_sensor": counts,
            "last_rejection_time": (
                self._rejection_log[-1]["timestamp"] if self._rejection_log else None
            ),
        }

    def get_last_rejection(self) -> Optional[Dict[str, Any]]:
        """Get the most recent rejection, if any."""
        return self._rejection_log[-1] if self._rejection_log else None

    def clear_rejection_log(self) -> None:
        """Clear the rejection log."""
        self._rejection_log = []


class DataValidatorManager:
    """Manages data validators for multiple devices."""

    def __init__(self) -> None:
        """Initialize the manager."""
        self._validators: Dict[str, DataValidator] = {}

    def get_validator(
        self, device_name: str, device_type: str, system_voltage: int = 12
    ) -> DataValidator:
        """Get or create a validator for a device."""
        key = f"{device_name}_{device_type}"
        if key not in self._validators:
            self._validators[key] = DataValidator(
                device_name, device_type, system_voltage
            )
        return self._validators[key]

    def validate_device_data(
        self,
        device_name: str,
        device_type: str,
        data: Dict[str, Any],
        system_voltage: int = 12,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Validate data for a device."""
        validator = self.get_validator(device_name, device_type, system_voltage)
        return validator.validate_data(data)

    def get_all_rejection_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get rejection stats for all devices."""
        return {
            name: validator.get_rejection_stats()
            for name, validator in self._validators.items()
        }
