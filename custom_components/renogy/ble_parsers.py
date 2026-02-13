"""
Renogy device data parsers for BLE communication.

Contains register definitions and parsing logic for:
- Rover/Wanderer charge controllers (BT-1)
- LiFePO4 batteries (BT-2)
- Inverters (BT-2)

Adapted from https://github.com/Anto79-ops/renogy-ble
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List

from .ble_utils import bytes_to_ascii, bytes_to_int, parse_temperature

_LOGGER = logging.getLogger(__name__)


class DeviceType(Enum):
    """Renogy BLE device types."""

    CONTROLLER = "controller"
    BATTERY = "battery"
    INVERTER = "inverter"


# ==========================================================================
# Controller constants and registers
# ==========================================================================

CONTROLLER_CHARGING_STATE = {
    0: "deactivated",
    1: "activated",
    2: "mppt",
    3: "equalizing",
    4: "boost",
    5: "floating",
    6: "current_limiting",
}

CONTROLLER_LOAD_STATE = {
    0: "off",
    1: "on",
}

CONTROLLER_BATTERY_TYPE = {
    1: "open",
    2: "sealed",
    3: "gel",
    4: "lithium",
    5: "custom",
}

CONTROLLER_REGISTERS = [
    {"name": "device_info", "register": 12, "words": 8},
    {"name": "device_id", "register": 26, "words": 1},
    {"name": "charging_info", "register": 256, "words": 34},
    {"name": "faults", "register": 289, "words": 2},
    {"name": "battery_type", "register": 57348, "words": 1},
    {"name": "historical", "register": 60000, "words": 21},
]


def parse_controller_device_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse controller device info (registers 12-19)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 16:
        return result
    result["model"] = bytes_to_ascii(data, offset, 16).strip("\x00")
    return result


def parse_controller_device_id(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse controller device ID (register 26)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 2:
        return result
    result["device_id"] = bytes_to_int(data, offset, 1)
    return result


def parse_controller_charging_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse controller charging info (registers 256-289).

    This is the main data section with battery, PV, load, and controller info.
    """
    result: Dict[str, Any] = {}
    if len(data) < offset + 68:
        _LOGGER.warning("Charging info data too short: %s bytes", len(data))
        return result

    # Battery data
    result["battery_percentage"] = bytes_to_int(data, offset + 0, 2)
    result["battery_voltage"] = bytes_to_int(data, offset + 2, 2, scale=0.1)
    result["battery_current"] = bytes_to_int(data, offset + 4, 2, scale=0.01)

    # Temperature handling (can be signed)
    battery_temp_raw = bytes_to_int(data, offset + 7, 1)
    controller_temp_raw = bytes_to_int(data, offset + 6, 1)
    result["battery_temperature"] = parse_temperature(battery_temp_raw)
    result["controller_temperature"] = parse_temperature(controller_temp_raw)

    # Load data
    result["load_voltage"] = bytes_to_int(data, offset + 8, 2, scale=0.1)
    result["load_current"] = bytes_to_int(data, offset + 10, 2, scale=0.01)
    result["load_power"] = bytes_to_int(data, offset + 12, 2)

    # PV (Solar panel) data
    result["pv_voltage"] = bytes_to_int(data, offset + 14, 2, scale=0.1)
    result["pv_current"] = bytes_to_int(data, offset + 16, 2, scale=0.01)
    result["pv_power"] = bytes_to_int(data, offset + 18, 2)

    # Daily statistics
    result["max_charging_power_today"] = bytes_to_int(data, offset + 30, 2)
    result["max_discharging_power_today"] = bytes_to_int(data, offset + 32, 2)
    result["charging_amp_hours_today"] = bytes_to_int(data, offset + 34, 2)
    result["discharging_amp_hours_today"] = bytes_to_int(data, offset + 36, 2)
    result["power_generation_today"] = bytes_to_int(data, offset + 38, 2)
    result["power_consumption_today"] = bytes_to_int(data, offset + 40, 2)

    # Cumulative totals (4 bytes)
    result["power_generation_total"] = bytes_to_int(data, offset + 56, 4)

    # Status
    load_status_byte = bytes_to_int(data, offset + 64, 1)
    result["load_status"] = CONTROLLER_LOAD_STATE.get(
        (load_status_byte >> 7) & 1, "unknown"
    )

    charging_status_byte = bytes_to_int(data, offset + 65, 1)
    result["charging_status"] = CONTROLLER_CHARGING_STATE.get(
        charging_status_byte, "unknown"
    )

    return result


def parse_controller_battery_type(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse controller battery type (register 57348 / 0xE004)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 2:
        return result
    battery_type_val = bytes_to_int(data, offset, 2)
    result["battery_type"] = CONTROLLER_BATTERY_TYPE.get(battery_type_val, "unknown")
    return result


def parse_controller_faults(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse controller fault and warning information (registers 0x0121-0x0122).

    This is a 32-bit value where each bit represents a specific fault/warning.
    """
    result: Dict[str, Any] = {
        "faults": [],
        "warnings": [],
        "fault_count": 0,
        "warning_count": 0,
    }

    if len(data) < offset + 4:
        _LOGGER.warning("Fault data too short: %s bytes", len(data))
        return result

    high_word = bytes_to_int(data, offset, 2)
    low_word = bytes_to_int(data, offset + 2, 2)
    fault_bits = (high_word << 16) | low_word

    fault_map = {
        30: "charge_mos_short_circuit",
        29: "anti_reverse_mos_short",
        28: "solar_panel_reversed",
        27: "pv_working_point_overvoltage",
        26: "pv_counter_current",
        25: "pv_input_overvoltage",
        24: "pv_input_short_circuit",
        23: "pv_input_overpower",
        22: "ambient_temp_too_high",
        21: "controller_temp_too_high",
        20: "load_overpower",
        19: "load_short_circuit",
        17: "battery_overvoltage",
        16: "battery_over_discharge",
    }

    for bit, name in fault_map.items():
        if fault_bits & (1 << bit):
            result["faults"].append(name)

    # Bit 18 is a warning, not a fault
    if fault_bits & (1 << 18):
        result["warnings"].append("battery_undervoltage")

    result["fault_count"] = len(result["faults"])
    result["warning_count"] = len(result["warnings"])

    if fault_bits != 0:
        _LOGGER.debug(
            "Controller fault bits: 0x%08X, faults: %s, warnings: %s",
            fault_bits,
            result["faults"],
            result["warnings"],
        )

    return result


def parse_controller_historical(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse controller historical data (7 days)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 42:
        return result

    daily_generation = []
    for i in range(7):
        val = bytes_to_int(data, offset + i * 2, 2)
        daily_generation.append(val)
    result["daily_power_generation"] = daily_generation

    daily_charge_ah = []
    for i in range(7):
        val = bytes_to_int(data, offset + 14 + i * 2, 2)
        daily_charge_ah.append(val)
    result["daily_charge_ah"] = daily_charge_ah

    daily_max_power = []
    for i in range(7):
        val = bytes_to_int(data, offset + 28 + i * 2, 2)
        daily_max_power.append(val)
    result["daily_max_power"] = daily_max_power

    return result


# ==========================================================================
# Battery constants and registers
# ==========================================================================

BATTERY_REGISTERS = [
    {"name": "cell_info", "register": 5000, "words": 17},
    {"name": "temp_info", "register": 5017, "words": 17},
    {"name": "battery_info", "register": 5042, "words": 8},
    {"name": "status_info", "register": 5100, "words": 10},
    {"name": "device_info", "register": 5122, "words": 8},
]


def parse_battery_cell_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse battery cell information (registers 5000-5016)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 4:
        return result

    cell_count = bytes_to_int(data, offset, 2)
    result["cell_count"] = min(cell_count, 16)

    cell_voltages = []
    for i in range(result["cell_count"]):
        if offset + 2 + i * 2 + 2 <= len(data):
            voltage = bytes_to_int(data, offset + 2 + i * 2, 2, scale=0.1)
            cell_voltages.append(round(voltage, 2))
    result["cell_voltages"] = cell_voltages

    return result


def parse_battery_temp_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse battery temperature information (registers 5017-5033)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 4:
        return result

    temp_count = bytes_to_int(data, offset, 2)
    result["temperature_count"] = min(temp_count, 8)

    temperatures = []
    for i in range(result["temperature_count"]):
        if offset + 2 + i * 2 + 2 <= len(data):
            temp_raw = bytes_to_int(data, offset + 2 + i * 2, 2, signed=True)
            temperatures.append(round(temp_raw * 0.1, 1))
    result["temperatures"] = temperatures

    if temperatures:
        result["battery_temperature"] = temperatures[0]

    return result


def parse_battery_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse battery main information (registers 5042-5049)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 12:
        _LOGGER.warning(
            "Battery info data too short: %s bytes (need %s)", len(data), offset + 12
        )
        return result

    result["current"] = bytes_to_int(data, offset, 2, scale=0.01, signed=True)
    result["voltage"] = bytes_to_int(data, offset + 2, 2, scale=0.1)
    result["remaining_capacity"] = bytes_to_int(data, offset + 4, 4, scale=0.001)
    result["total_capacity"] = bytes_to_int(data, offset + 8, 4, scale=0.001)

    if result.get("total_capacity", 0) > 0:
        result["soc"] = round(
            (result.get("remaining_capacity", 0) / result["total_capacity"]) * 100, 1
        )
    else:
        result["soc"] = 0

    result["power"] = round(result.get("voltage", 0) * result.get("current", 0), 1)

    return result


def parse_battery_alarm_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse battery alarm/status flags (registers 5100-5109)."""
    result: Dict[str, Any] = {
        "cell_voltage_alarms": [],
        "cell_temperature_alarms": [],
        "protection_alarms": [],
        "warnings": [],
    }

    if len(data) < offset + 20:
        _LOGGER.warning("Battery alarm data too short: %s bytes", len(data))
        result["alarm_count"] = 0
        result["warning_count"] = 0
        return result

    # Registers 5100-5101: Cell Voltage Alarm Info
    cell_voltage_alarm = bytes_to_int(data, offset, 4)
    for cell in range(16):
        alarm_code = (cell_voltage_alarm >> (cell * 2)) & 0x03
        if alarm_code == 1:
            result["cell_voltage_alarms"].append(f"cell_{cell + 1}_undervoltage")
        elif alarm_code == 2:
            result["cell_voltage_alarms"].append(f"cell_{cell + 1}_overvoltage")
        elif alarm_code == 3:
            result["cell_voltage_alarms"].append(f"cell_{cell + 1}_alarm")

    # Registers 5102-5103: Cell Temperature Alarm Info
    cell_temp_alarm = bytes_to_int(data, offset + 4, 4)
    for cell in range(16):
        alarm_code = (cell_temp_alarm >> (cell * 2)) & 0x03
        if alarm_code == 1:
            result["cell_temperature_alarms"].append(f"cell_{cell + 1}_undertemp")
        elif alarm_code == 2:
            result["cell_temperature_alarms"].append(f"cell_{cell + 1}_overtemp")
        elif alarm_code == 3:
            result["cell_temperature_alarms"].append(f"cell_{cell + 1}_temp_alarm")

    # Registers 5104-5105: Other Alarm Info
    other_alarm = bytes_to_int(data, offset + 8, 4)
    alarm_names = [
        ("bms_board_temp", 0),
        ("bms_board_temp", 2),
        ("env_temp_1", 4),
        ("env_temp_1", 6),
        ("env_temp_2", 8),
        ("env_temp_2", 10),
        ("heater_temp_1", 12),
        ("heater_temp_1", 14),
        ("heater_temp_2", 16),
        ("heater_temp_2", 18),
        ("charge_current", 20),
        ("charge_current", 22),
        ("discharge_current", 24),
        ("discharge_current", 26),
    ]
    for name, bit_pos in alarm_names:
        alarm_code = (other_alarm >> bit_pos) & 0x03
        if alarm_code == 1:
            result["protection_alarms"].append(f"{name}_low")
        elif alarm_code == 2:
            result["protection_alarms"].append(f"{name}_high")
        elif alarm_code == 3:
            result["protection_alarms"].append(f"{name}_alarm")

    # Register 5106: Status1
    status1 = bytes_to_int(data, offset + 12, 2)
    status1_faults = {
        15: "module_undervoltage",
        14: "charge_overtemp",
        13: "charge_undertemp",
        12: "discharge_overtemp",
        11: "discharge_undertemp",
        10: "discharge_overcurrent1",
        9: "charge_overcurrent1",
        8: "cell_overvoltage",
        7: "cell_undervoltage",
        6: "module_overvoltage",
        5: "discharge_overcurrent2",
        4: "charge_overcurrent2",
        0: "short_circuit",
    }
    for bit, name in status1_faults.items():
        if status1 & (1 << bit):
            result["protection_alarms"].append(name)

    result["using_battery_power"] = bool(status1 & (1 << 3))
    result["discharge_mosfet"] = "on" if status1 & (1 << 2) else "off"
    result["charge_mosfet"] = "on" if status1 & (1 << 1) else "off"

    # Register 5107: Status2
    status2 = bytes_to_int(data, offset + 14, 2)
    result["effective_charge"] = bool(status2 & (1 << 15))
    result["effective_discharge"] = bool(status2 & (1 << 14))
    result["heater_on"] = bool(status2 & (1 << 13))
    result["fully_charged"] = bool(status2 & (1 << 11))
    result["buzzer_on"] = bool(status2 & (1 << 8))

    # Register 5108: Status3 (Warnings)
    status3 = bytes_to_int(data, offset + 16, 2)
    warning_map_low = {
        7: "discharge_high_temp",
        6: "discharge_low_temp",
        5: "charge_high_temp",
        4: "charge_low_temp",
        3: "module_high_voltage",
        2: "module_low_voltage",
        1: "cell_high_voltage",
        0: "cell_low_voltage",
    }
    for bit, name in warning_map_low.items():
        if status3 & (1 << bit):
            result["warnings"].append(name)

    for i in range(8):
        if status3 & (1 << (8 + i)):
            result["warnings"].append(f"cell_{11 + i}_voltage_error")

    # Register 5109: Charge/Discharge Status
    status4 = bytes_to_int(data, offset + 18, 2)
    result["discharge_enabled"] = bool(status4 & (1 << 7))
    result["charge_enabled"] = bool(status4 & (1 << 6))
    result["charge_immediately"] = bool(status4 & (1 << 5))
    result["full_charge_request"] = bool(status4 & (1 << 3))

    # Combine all alarms
    all_alarms = (
        result["cell_voltage_alarms"]
        + result["cell_temperature_alarms"]
        + result["protection_alarms"]
    )
    result["alarms"] = all_alarms
    result["alarm_count"] = len(all_alarms)
    result["warning_count"] = len(result["warnings"])

    return result


def parse_battery_device_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse battery device info (registers 5122-5129)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 16:
        return result
    result["model"] = bytes_to_ascii(data, offset, 16).strip("\x00")
    return result


# ==========================================================================
# Inverter constants and registers
# ==========================================================================

INVERTER_CHARGING_STATE = {
    0: "not_charging",
    1: "constant_current",
    2: "constant_voltage",
    4: "float",
    6: "battery_activation",
    7: "battery_disconnect",
}

INVERTER_MACHINE_STATE = {
    0: "power_on_delay",
    1: "waiting",
    2: "initialization",
    3: "soft_start",
    4: "mains_operation",
    5: "inverter_operation",
    6: "inverter_to_mains",
    7: "mains_to_inverter",
    10: "shutdown",
    11: "fault",
}

INVERTER_MODE = {
    0x00: "unknown",
    0x01: "normal",
    0x02: "eco",
    0x03: "shutdown",
    0x04: "restore",
}

INVERTER_OUTPUT_PRIORITY = {
    0: "solar",
    1: "line",
    2: "sbu",
}

INVERTER_REGISTERS = [
    {"name": "main_status", "register": 4000, "words": 10},
    {"name": "device_info", "register": 4303, "words": 24},
    {"name": "pv_info", "register": 4327, "words": 7},
    {"name": "settings_status", "register": 4398, "words": 20},
    {"name": "settings", "register": 4441, "words": 4},
    {"name": "statistics", "register": 4543, "words": 25},
]


def parse_inverter_main_status(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse inverter main status (registers 4000-4009)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 18:
        return result

    def safe_value(raw: int, scale: float = 1.0, max_valid: int = 65000) -> float:
        if raw >= max_valid:
            return 0.0
        return round(raw * scale, 2)

    input_v_raw = bytes_to_int(data, offset, 2)
    input_c_raw = bytes_to_int(data, offset + 2, 2)
    result["input_voltage"] = safe_value(input_v_raw, 0.1)
    result["input_current"] = safe_value(input_c_raw, 0.01)

    result["output_voltage"] = bytes_to_int(data, offset + 4, 2, scale=0.1)
    result["output_current"] = bytes_to_int(data, offset + 6, 2, scale=0.01)
    result["output_frequency"] = bytes_to_int(data, offset + 8, 2, scale=0.01)

    result["battery_voltage"] = bytes_to_int(data, offset + 10, 2, scale=0.1)
    result["temperature"] = bytes_to_int(data, offset + 12, 2, scale=0.1)

    if len(data) >= offset + 18:
        status_high = bytes_to_int(data, offset + 14, 2)
        status_low = bytes_to_int(data, offset + 16, 2)

        result["faults"] = []

        high_faults = {
            15: "input_uvp",
            14: "input_ovp",
            13: "output_overload",
            12: "dcdc_overload",
            11: "dcdc_overcurrent",
            10: "bus_overvoltage",
            9: "ground_fault",
            8: "over_temperature",
            7: "output_short_circuit",
            6: "output_uvp",
            5: "output_ovp",
        }
        for bit, name in high_faults.items():
            if status_high & (1 << bit):
                result["faults"].append(name)

        result["eco_mode"] = bool(status_high & (1 << 4))

        low_faults = {
            15: "utility_fail",
            14: "battery_low",
            13: "apr_active",
            12: "ups_fail",
            9: "shutdown_active",
            7: "fan_locked",
            6: "inverter_overload",
            5: "inverter_short_circuit",
            4: "battery_bad",
        }
        for bit, name in low_faults.items():
            if status_low & (1 << bit):
                result["faults"].append(name)

        result["ups_line_interactive"] = bool(status_low & (1 << 11))
        result["test_in_progress"] = bool(status_low & (1 << 10))
        result["beeper_on"] = bool(status_low & (1 << 8))
        result["fault_count"] = len(result["faults"])

    if len(data) >= offset + 20:
        input_freq_raw = bytes_to_int(data, offset + 18, 2)
        result["input_frequency"] = safe_value(input_freq_raw, 0.01)

    if result.get("input_voltage", 0) > 0 and result.get("input_current", 0) > 0:
        result["input_power"] = round(
            result["input_voltage"] * result["input_current"], 1
        )
    else:
        result["input_power"] = 0.0

    result["output_power"] = round(
        result.get("output_voltage", 0) * result.get("output_current", 0), 1
    )

    return result


def parse_inverter_device_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse inverter device info (registers 4303-4326)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 48:
        return result

    result["manufacturer"] = bytes_to_ascii(data, offset, 16)
    result["model"] = bytes_to_ascii(data, offset + 16, 16)
    result["firmware_version"] = bytes_to_ascii(data, offset + 32, 16)

    return result


def parse_inverter_pv_info(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse inverter PV/solar info (registers 4327-4333)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 12:
        return result

    result["battery_soc"] = bytes_to_int(data, offset, 2)
    result["charge_current"] = bytes_to_int(data, offset + 2, 2, scale=0.1)
    result["pv_voltage"] = bytes_to_int(data, offset + 4, 2, scale=0.1)
    result["pv_current"] = bytes_to_int(data, offset + 6, 2, scale=0.1)
    result["pv_power"] = bytes_to_int(data, offset + 8, 2)

    if len(data) >= offset + 12:
        charge_state = bytes_to_int(data, offset + 10, 2) & 0xFF
        result["charging_status"] = INVERTER_CHARGING_STATE.get(charge_state, "unknown")

    return result


def parse_inverter_settings_status(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse inverter settings and status (registers 4398-4417)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 30:
        return result

    if len(data) >= offset + 16:
        machine_state = bytes_to_int(data, offset + 14, 2)
        result["machine_state"] = INVERTER_MACHINE_STATE.get(machine_state, "unknown")

    if len(data) >= offset + 20:
        result["bus_voltage"] = bytes_to_int(data, offset + 18, 2, scale=0.1)

    if len(data) >= offset + 26:
        result["load_current"] = bytes_to_int(data, offset + 20, 2, scale=0.1)
        result["load_active_power"] = bytes_to_int(data, offset + 22, 2)
        result["load_apparent_power"] = bytes_to_int(data, offset + 24, 2)

    if len(data) >= offset + 32:
        result["load_percentage"] = bytes_to_int(data, offset + 30, 2)

    return result


def parse_inverter_statistics(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse inverter energy statistics (registers 4543-4567)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 10:
        return result

    result["battery_charge_ah_today"] = bytes_to_int(data, offset, 2)
    result["battery_discharge_ah_today"] = bytes_to_int(data, offset + 2, 2)
    result["pv_generation_today"] = bytes_to_int(data, offset + 4, 2, scale=0.1)
    result["load_consumption_today"] = bytes_to_int(data, offset + 6, 2, scale=0.1)

    if len(data) >= offset + 30:
        result["battery_charge_ah_total"] = bytes_to_int(data, offset + 14, 4)
        result["battery_discharge_ah_total"] = bytes_to_int(data, offset + 18, 4)
        result["pv_generation_total"] = bytes_to_int(data, offset + 22, 4, scale=0.1)
        result["load_consumption_total"] = bytes_to_int(data, offset + 26, 4, scale=0.1)

    return result


def parse_inverter_settings(data: bytes, offset: int = 3) -> Dict[str, Any]:
    """Parse inverter settings (registers 4441-4444)."""
    result: Dict[str, Any] = {}
    if len(data) < offset + 8:
        return result

    output_priority = bytes_to_int(data, offset, 2)
    result["output_priority"] = INVERTER_OUTPUT_PRIORITY.get(output_priority, "unknown")

    output_freq = bytes_to_int(data, offset + 2, 2)
    result["output_frequency_setting"] = round(output_freq * 0.01, 1)

    ac_range = bytes_to_int(data, offset + 4, 2)
    result["ac_voltage_range"] = "wide" if ac_range == 0 else "narrow"

    power_saving = bytes_to_int(data, offset + 6, 2)
    result["power_saving_mode"] = power_saving == 1

    return result


# ==========================================================================
# Parser dispatch
# ==========================================================================

PARSERS = {
    DeviceType.CONTROLLER: {
        12: parse_controller_device_info,
        26: parse_controller_device_id,
        256: parse_controller_charging_info,
        289: parse_controller_faults,
        57348: parse_controller_battery_type,
        60000: parse_controller_historical,
    },
    DeviceType.BATTERY: {
        5000: parse_battery_cell_info,
        5017: parse_battery_temp_info,
        5042: parse_battery_info,
        5100: parse_battery_alarm_info,
        5122: parse_battery_device_info,
    },
    DeviceType.INVERTER: {
        4000: parse_inverter_main_status,
        4303: parse_inverter_device_info,
        4327: parse_inverter_pv_info,
        4398: parse_inverter_settings_status,
        4441: parse_inverter_settings,
        4543: parse_inverter_statistics,
    },
}

REGISTER_DEFINITIONS = {
    DeviceType.CONTROLLER: CONTROLLER_REGISTERS,
    DeviceType.BATTERY: BATTERY_REGISTERS,
    DeviceType.INVERTER: INVERTER_REGISTERS,
}


def parse_response(
    device_type: DeviceType, register: int, data: bytes
) -> Dict[str, Any]:
    """Parse a Modbus response based on device type and register.

    Args:
        device_type: Type of Renogy device.
        register: Starting register address.
        data: Raw response bytes.

    Returns:
        Dictionary of parsed values.
    """
    if device_type not in PARSERS:
        _LOGGER.warning("Unknown device type: %s", device_type)
        return {}

    if register not in PARSERS[device_type]:
        _LOGGER.warning("Unknown register %s for %s", register, device_type.value)
        return {}

    parser_func = PARSERS[device_type][register]
    try:
        result = parser_func(data)
        _LOGGER.debug("Parsed %s register %s: %s", device_type.value, register, result)
        return result
    except Exception:  # pylint: disable=broad-except
        _LOGGER.error(
            "Error parsing %s register %s", device_type.value, register, exc_info=True
        )
        return {}


def get_registers_for_device(device_type: DeviceType) -> List[Dict]:
    """Get the list of registers to read for a device type."""
    return REGISTER_DEFINITIONS.get(device_type, [])
