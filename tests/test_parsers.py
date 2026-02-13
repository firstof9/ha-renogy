"""Test all BLE parsers."""

import pytest
from custom_components.renogy.ble_parsers import (
    parse_controller_device_info,
    parse_controller_device_id,
    parse_controller_battery_type,
    parse_controller_faults,
    parse_controller_historical,
    parse_battery_cell_info,
    parse_battery_temp_info,
    parse_battery_info,
    parse_battery_alarm_info,
    parse_battery_device_info,
    parse_inverter_main_status,
    parse_inverter_device_info,
    parse_inverter_pv_info,
)


# Helpers to create byte arrays
def create_buffer(length, offset=3):
    return bytearray(length + offset)


def set_bytes(buffer, offset, value, size=2):
    val_bytes = value.to_bytes(size, byteorder="big")
    for i, b in enumerate(val_bytes):
        buffer[offset + i] = b


async def test_parse_controller_device_info():
    """Test parse_controller_device_info."""
    offset = 3
    # Needs len > offset + 16 (19 total)
    data = create_buffer(16, offset)
    # Model: "RNG-CTRL"
    model = b"RNG-CTRL        "  # 16 chars
    for i, b in enumerate(model):
        data[offset + i] = b

    result = parse_controller_device_info(bytes(data), offset)
    assert result["model"] == "RNG-CTRL"

    # Short
    assert parse_controller_device_info(b"", offset) == {}


async def test_parse_controller_device_id():
    """Test parse_controller_device_id."""
    offset = 3
    data = create_buffer(2, offset)
    data[offset] = 0xAB  # 171

    result = parse_controller_device_id(bytes(data), offset)
    assert result["device_id"] == 0xAB

    # Short
    assert parse_controller_device_id(b"", offset) == {}


async def test_parse_controller_battery_type():
    """Test parse_controller_battery_type."""
    offset = 3
    data = create_buffer(2, offset)
    set_bytes(data, offset, 4, 2)  # 4 = lithium

    result = parse_controller_battery_type(bytes(data), offset)
    assert result["battery_type"] == "lithium"

    # Unknown
    set_bytes(data, offset, 99, 2)
    result = parse_controller_battery_type(bytes(data), offset)
    assert result["battery_type"] == "unknown"


async def test_parse_controller_faults():
    """Test parse_controller_faults."""
    offset = 3
    # Needs offset + 4 bytes
    data = create_buffer(4, offset)
    set_bytes(data, offset, 0x10000000, 4)  # Bit 28: solar_panel_reversed

    result = parse_controller_faults(bytes(data), offset)
    assert "solar_panel_reversed" in result["faults"]
    assert result["fault_count"] == 1

    # Short
    assert parse_controller_faults(b"", offset) == {
        "faults": [],
        "warnings": [],
        "fault_count": 0,
        "warning_count": 0,
    }


async def test_parse_controller_historical():
    """Test parse_controller_historical."""
    offset = 3
    # Needs offset + 42 bytes
    data = create_buffer(42, offset)

    # daily_power_generation (offset 0, 7 words)
    # daily_charge_ah (offset 14, 7 words)
    # daily_max_power (offset 28, 7 words)

    # Day 0 power (offset 0)
    set_bytes(data, offset, 100, 2)
    # Day 0 ah (offset 14 -> 14*2 bytes? No, offsets in loop are byte offsets?)
    # loop: offset + 14 + i*2. offset is byte index.
    # So 14 bytes later.
    set_bytes(data, offset + 14, 50, 2)

    result = parse_controller_historical(bytes(data), offset)
    assert result["daily_power_generation"][0] == 100
    assert result["daily_charge_ah"][0] == 50


async def test_parse_battery_cell_info():
    """Test parse_battery_cell_info."""
    offset = 3
    # 4 cells * 2 bytes = 8 bytes needed + 2 bytes for count = 10 bytes
    data = create_buffer(10, offset)
    set_bytes(data, offset, 2, 2)  # count = 2
    set_bytes(data, offset + 2, 32, 2)  # cell 1 -> 3.2V
    set_bytes(data, offset + 4, 33, 2)  # cell 2 -> 3.3V

    result = parse_battery_cell_info(bytes(data), offset)
    assert result["cell_count"] == 2
    assert result["cell_voltages"][0] == 3.2
    assert result["cell_voltages"][1] == 3.3


async def test_parse_battery_temp_info():
    """Test parse_battery_temp_info."""
    offset = 3
    # 2 bytes count, then temps
    data = create_buffer(6, offset)
    set_bytes(data, offset, 1, 2)  # count 1
    set_bytes(data, offset + 2, 250, 2)  # 25.0 C (scale 0.1)

    result = parse_battery_temp_info(bytes(data), offset)
    assert result["battery_temperature"] == 25.0
    assert result["temperatures"][0] == 25.0


async def test_parse_battery_info():
    """Test parse_battery_info."""
    offset = 3
    # offset+0(2): current, +2(2): voltage, +4(4): rem_cap, +8(4): total_cap
    data = create_buffer(14, offset)  # Need +12
    set_bytes(data, offset, 1000, 2)  # 10.00 A
    set_bytes(data, offset + 2, 1200, 2)  # 120.0 V (scale 0.1) -> 1200

    result = parse_battery_info(bytes(data), offset)
    assert result["current"] == 10.0
    assert result["voltage"] == 120.0


async def test_parse_battery_alarm_info():
    """Test parse_battery_alarm_info."""
    offset = 3
    # Need offset + 20
    data = create_buffer(20, offset)
    # Status3 (Warnings) at offset + 16 (2 bytes)
    # Bit 0: cell_low_voltage
    set_bytes(data, offset + 16, 0x01, 2)

    result = parse_battery_alarm_info(bytes(data), offset)
    assert "cell_low_voltage" in result["warnings"]


async def test_parse_battery_device_info():
    """Test parse_battery_device_info."""
    offset = 3
    # offset+0(16): model
    data = create_buffer(16, offset)
    model = b"RNG-BATT"
    for i, b in enumerate(model):
        data[offset + i] = b

    result = parse_battery_device_info(bytes(data), offset)
    assert result["model"] == "RNG-BATT"


async def test_parse_inverter_main_status():
    """Test parse_inverter_main_status."""
    offset = 3
    # Needs offset + 18
    data = create_buffer(20, offset)
    # bat_volt at offset + 10
    set_bytes(data, offset + 10, 120, 2)  # 12V

    result = parse_inverter_main_status(bytes(data), offset)
    assert result["battery_voltage"] == 12.0


async def test_parse_inverter_device_info():
    """Test parse_inverter_device_info."""
    offset = 3
    # Need offset + 48
    data = create_buffer(48, offset)
    model = b"RNG-INV"
    # Manufacturer (0-15), Model (16-31)
    for i, b in enumerate(model):
        data[offset + 16 + i] = b

    result = parse_inverter_device_info(bytes(data), offset)
    assert result["model"].strip() == "RNG-INV"


async def test_parse_inverter_pv_info():
    """Test parse_inverter_pv_info."""
    offset = 3
    data = create_buffer(14, offset)
    # PV volt at offset + 4
    set_bytes(data, offset + 4, 120, 2)  # 12V PV

    result = parse_inverter_pv_info(bytes(data), offset)
    assert result["pv_voltage"] == 12.0


"""Test BLE parsers."""

from custom_components.renogy.ble_parsers import parse_controller_charging_info


def test_parse_controller_charging_info_full_faults():
    """Test parsing with full buffer including all faults."""
    # Create valid buffer of length 70 (3 (offset) + 67 bytes data).
    # Wait, offset=3 usually. So need 3 + 67 bytes?
    # No, parser checks len < offset + 68.
    # To get full faults, check is len >= offset + 70.
    # So need 73 bytes total if offset=3.
    # Data length = 70.

    offset = 3
    data = bytearray(73)

    # Fill standard fields with dummy data
    # Battery Voltage (Offset 2): 256 -> 25.6V
    data[offset + 2] = 0x01
    data[offset + 3] = 0x00

    # Faults (Offset 66): 0x12345678
    data[offset + 66] = 0x12
    data[offset + 67] = 0x34
    data[offset + 68] = 0x56
    data[offset + 69] = 0x78

    result = parse_controller_charging_info(bytes(data), offset)
    assert result["battery_voltage"] == 25.6
    assert result["controller_faults"] == 0x12345678


def test_parse_controller_charging_info_partial_faults():
    """Test parsing with buffer limited to 68 bytes (34 registers)."""
    # Offset=3. Need 3 + 68 = 71 bytes total.
    # If len is 71, index goes up to 70. (0..70)
    # Offset 66 is index 69, 70 (2 bytes).
    # wait. offset+66 = 3+66 = 69.
    # index 69, 70.
    # If len is 71: indices 0..70.
    # So we have 69 and 70.

    # Parser check: len >= offset + 70 (73) -> full.
    # len >= offset + 68 (71) -> partial.

    offset = 3
    data = bytearray(71)

    # Faults (Offset 66): 0x1234
    data[offset + 66] = 0x12
    data[offset + 67] = 0x34

    result = parse_controller_charging_info(bytes(data), offset)
    assert result["controller_faults"] == 0x1234


def test_parse_controller_charging_info_too_short():
    """Test parsing with insufficient buffer."""
    offset = 3
    data = bytearray(70)  # Just short of 71
    result = parse_controller_charging_info(
        bytes(data), offset
    )  # Should check < offset+68?
    # existing check: if len(data) < offset + 68: return {}
    # offset + 68 = 71.
    # So if 70, returns empty.
    assert result == {}
"""Test detailed coverage for ble_parsers.py."""
import pytest
from custom_components.renogy.ble_parsers import (
    parse_inverter_settings_status,
    parse_inverter_statistics,
    parse_inverter_settings,
    parse_response,
    get_registers_for_device,
    DeviceType,
)

def create_buffer(length, offset=3):
    """Create a buffer with given length and offset."""
    return bytearray([0] * (length + offset))

def test_parse_inverter_settings_status():
    """Test parsing inverter settings status."""
    # Short data
    assert parse_inverter_settings_status(b"\x00"*10) == {}
    
    offset = 3
    # Full data length needed ~30+
    data = create_buffer(32, offset)
    
    # machine_state (offset+14) -> 2 bytes
    data[offset+14] = 0x00
    data[offset+15] = 0x00 # 0 -> unknown? Or check dict in code
    # INVERTER_MACHINE_STATE isn't imported but let's assume 0 is Valid
    
    # bus_voltage (offset+18) -> 200 -> 20.0
    data[offset+18] = 0x00
    data[offset+19] = 200
    
    # load_current (offset+20) -> 10 -> 1.0
    data[offset+20] = 0x00
    data[offset+21] = 10
    
    # load_percentage (offset+30) -> 50
    data[offset+30] = 0x00
    data[offset+31] = 50
    
    result = parse_inverter_settings_status(bytes(data))
    
    # Check simplified assertions
    assert result["bus_voltage"] == 20.0
    assert result["load_current"] == 1.0
    assert result["load_percentage"] == 50


def test_parse_inverter_statistics():
    """Test parsing inverter statistics."""
    # Short data
    assert parse_inverter_statistics(b"\x00"*5) == {}
    
    offset = 3
    # Need ~30 bytes
    data = create_buffer(32, offset)
    
    # battery_charge_ah_today (offset+0)
    data[offset] = 0x00
    data[offset+1] = 100
    
    # battery_discharge_ah_total (offset+18) 4 bytes
    # 0x00 00 00 64 -> 100
    data[offset+18] = 0x00
    data[offset+19] = 0x00
    data[offset+20] = 0x00
    data[offset+21] = 100
    
    result = parse_inverter_statistics(bytes(data))
    
    assert result["battery_charge_ah_today"] == 100
    assert result["battery_discharge_ah_total"] == 100


def test_parse_inverter_settings():
    """Test parsing inverter settings."""
    # Short data
    assert parse_inverter_settings(b"\x00"*5) == {}
    
    offset = 3
    data = create_buffer(10, offset)
    
    # output_priority (offset+0)
    data[offset+1] = 0
    
    # output_freq (offset+2) -> 5000 -> 50.0
    data[offset+2] = 0x13
    data[offset+3] = 0x88
    
    # ac_range (offset+4) -> 0 -> wide
    data[offset+5] = 0
    
    # power_saving (offset+6) -> 1 -> True
    data[offset+7] = 1
    
    result = parse_inverter_settings(bytes(data))
    
    assert result["output_frequency_setting"] == 50.0
    assert result["ac_voltage_range"] == "wide"
    assert result["power_saving_mode"] is True


def test_parse_response_edge_cases():
    """Test parse_response edge cases."""
    
    # Unknown Device Type
    # DeviceType enum might be tricky if I can't instantiate an invalid one, 
    # but I can cast an int or mock it.
    # Actually DeviceType is an Enum.
    # We can pass an object that matches the type hint or a random string if not checked strictly by dispatch
    
    result = parse_response("UNKNOWN_TYPE", 123, b"")
    assert result == {}
    
    # Unknown Register
    result = parse_response(DeviceType.CONTROLLER, 99999, b"")
    assert result == {}
    
    # Exception handling
    # We need to trigger an exception in the parser function.
    # We can patch PARSERS[DeviceType.CONTROLLER][12] to raise
    
    from unittest.mock import patch
    
    with patch.dict("custom_components.renogy.ble_parsers.PARSERS", {
        DeviceType.CONTROLLER: {
            123: lambda x: (_ for _ in ()).throw(Exception("Parser Error"))
        }
    }):
        result = parse_response(DeviceType.CONTROLLER, 123, b"")
        assert result == {}


def test_get_registers_for_device_unknown():
    """Test get_registers_for_device with unknown type."""
    result = get_registers_for_device("UNKNOWN")
    assert result == []
