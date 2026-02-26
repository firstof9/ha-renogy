from unittest.mock import patch

from custom_components.renogy.ble_parsers import (
    DeviceType,
    get_registers_for_device,
    parse_battery_alarm_info,
    parse_battery_cell_info,
    parse_battery_device_info,
    parse_battery_info,
    parse_battery_temp_info,
    parse_controller_battery_type,
    parse_controller_charging_info,
    parse_controller_device_id,
    parse_controller_device_info,
    parse_controller_faults,
    parse_controller_historical,
    parse_inverter_device_info,
    parse_inverter_main_status,
    parse_inverter_pv_info,
    parse_inverter_settings,
    parse_inverter_settings_status,
    parse_inverter_statistics,
    parse_response,
)


# Helpers to create byte arrays
def create_buffer(length, offset=3):
    return bytearray(length + offset)


def set_bytes(buffer, offset, value, size=2):
    val_bytes = value.to_bytes(size, byteorder="big")
    for i, b in enumerate(val_bytes):
        buffer[offset + i] = b


def test_parse_controller_device_info():
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


def test_parse_controller_device_id():
    """Test parse_controller_device_id."""
    offset = 3
    data = create_buffer(2, offset)
    data[offset] = 0xAB  # 171

    result = parse_controller_device_id(bytes(data), offset)
    assert result["device_id"] == 0xAB

    # Short
    assert parse_controller_device_id(b"", offset) == {}


def test_parse_controller_battery_type():
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


def test_parse_controller_faults():
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


def test_parse_controller_historical():
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


def test_parse_battery_cell_info():
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


def test_parse_battery_temp_info():
    """Test parse_battery_temp_info."""
    offset = 3
    # 2 bytes count, then temps
    data = create_buffer(6, offset)
    set_bytes(data, offset, 1, 2)  # count 1
    set_bytes(data, offset + 2, 250, 2)  # 25.0 C (scale 0.1)

    result = parse_battery_temp_info(bytes(data), offset)
    assert result["battery_temperature"] == 25.0
    assert result["temperatures"][0] == 25.0


def test_parse_battery_info():
    """Test parse_battery_info."""
    offset = 3
    # offset+0(2): current, +2(2): voltage, +4(4): rem_cap, +8(4): total_cap
    data = create_buffer(14, offset)  # Need +12
    set_bytes(data, offset, 1000, 2)  # 10.00 A
    set_bytes(data, offset + 2, 1200, 2)  # 120.0 V (scale 0.1) -> 1200

    result = parse_battery_info(bytes(data), offset)
    assert result["current"] == 10.0
    assert result["voltage"] == 120.0


def test_parse_battery_alarm_info():
    """Test parse_battery_alarm_info."""
    offset = 3
    # Need offset + 20
    data = create_buffer(20, offset)
    # Status3 (Warnings) at offset + 16 (2 bytes)
    # Bit 0: cell_low_voltage
    set_bytes(data, offset + 16, 0x01, 2)

    result = parse_battery_alarm_info(bytes(data), offset)
    assert "cell_low_voltage" in result["warnings"]


def test_parse_battery_device_info():
    """Test parse_battery_device_info."""
    offset = 3
    # offset+0(16): model
    data = create_buffer(16, offset)
    model = b"RNG-BATT"
    for i, b in enumerate(model):
        data[offset + i] = b

    result = parse_battery_device_info(bytes(data), offset)
    assert result["model"] == "RNG-BATT"


def test_parse_inverter_main_status():
    """Test parse_inverter_main_status."""
    offset = 3
    # Needs offset + 18
    data = create_buffer(20, offset)
    # bat_volt at offset + 10
    set_bytes(data, offset + 10, 120, 2)  # 12V

    result = parse_inverter_main_status(bytes(data), offset)
    assert result["battery_voltage"] == 12.0


def test_parse_inverter_device_info():
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


def test_parse_inverter_pv_info():
    """Test parse_inverter_pv_info."""
    offset = 3
    data = create_buffer(14, offset)
    # PV volt at offset + 4
    set_bytes(data, offset + 4, 120, 2)  # 12V PV

    result = parse_inverter_pv_info(bytes(data), offset)
    assert result["pv_voltage"] == 12.0


# Additional parser tests


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


# Detailed coverage for ble_parsers.py


def test_parse_inverter_settings_status():
    """Test parsing inverter settings status."""
    # Short data
    assert parse_inverter_settings_status(b"\x00" * 10) == {}

    offset = 3
    # Full data length needed ~30+
    data = create_buffer(32, offset)

    # machine_state (offset+14) -> 2 bytes
    data[offset + 14] = 0x00
    data[offset + 15] = 0x00  # 0 -> unknown? Or check dict in code
    # INVERTER_MACHINE_STATE isn't imported but let's assume 0 is Valid

    # bus_voltage (offset+18) -> 200 -> 20.0
    data[offset + 18] = 0x00
    data[offset + 19] = 200

    # load_current (offset+20) -> 10 -> 1.0
    data[offset + 20] = 0x00
    data[offset + 21] = 10

    # load_percentage (offset+30) -> 50
    data[offset + 30] = 0x00
    data[offset + 31] = 50

    result = parse_inverter_settings_status(bytes(data))

    # Check simplified assertions
    assert result["bus_voltage"] == 20.0
    assert result["load_current"] == 1.0
    assert result["load_percentage"] == 50


def test_parse_inverter_statistics():
    """Test parsing inverter statistics."""
    # Short data
    assert parse_inverter_statistics(b"\x00" * 5) == {}

    offset = 3
    # Need ~30 bytes
    data = create_buffer(32, offset)

    # battery_charge_ah_today (offset+0)
    data[offset] = 0x00
    data[offset + 1] = 100

    # battery_discharge_ah_total (offset+18) 4 bytes
    # 0x00 00 00 64 -> 100
    data[offset + 18] = 0x00
    data[offset + 19] = 0x00
    data[offset + 20] = 0x00
    data[offset + 21] = 100

    result = parse_inverter_statistics(bytes(data))

    assert result["battery_charge_ah_today"] == 100
    assert result["battery_discharge_ah_total"] == 100


def test_parse_inverter_settings():
    """Test parsing inverter settings."""
    # Short data
    assert parse_inverter_settings(b"\x00" * 5) == {}

    offset = 3
    data = create_buffer(10, offset)

    # output_priority (offset+0)
    data[offset + 1] = 0

    # output_freq (offset+2) -> 5000 -> 50.0
    data[offset + 2] = 0x13
    data[offset + 3] = 0x88

    # ac_range (offset+4) -> 0 -> wide
    data[offset + 5] = 0

    # power_saving (offset+6) -> 1 -> True
    data[offset + 7] = 1

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

    with patch.dict(
        "custom_components.renogy.ble_parsers.PARSERS",
        {
            DeviceType.CONTROLLER: {
                123: lambda x: (_ for _ in ()).throw(Exception("Parser Error"))
            }
        },
    ):
        result = parse_response(DeviceType.CONTROLLER, 123, b"")
        assert result == {}


def test_get_registers_for_device_unknown():
    """Test get_registers_for_device with unknown type."""
    result = get_registers_for_device("UNKNOWN")
    assert result == []


# Deep coverage tests for ble_parsers.py


def test_parse_controller_battery_type_short():
    """Test short data for battery type."""
    assert parse_controller_battery_type(b"\x00" * 3) == {}


def test_parse_controller_faults_bits():
    """Test fault parsing with specific bits."""
    offset = 3
    data = create_buffer(4, offset)

    # Needs 4 bytes of data (High Word, Low Word)
    # High Word: data[offset], data[offset+1]
    # Low Word: data[offset+2], data[offset+3]

    # Set bit 30 (charge_mos_short_circuit) -> 0x40000000
    # High word: 0x4000
    data[offset] = 0x40
    data[offset + 1] = 0x00

    # Set bit 18 (battery_undervoltage warning) -> 0x00040000
    # High word: 0x0004 -> data[offset+1] |= 0x04
    data[offset + 1] |= 0x04

    result = parse_controller_faults(bytes(data))

    assert "charge_mos_short_circuit" in result["faults"]
    assert "battery_undervoltage" in result["warnings"]
    assert result["fault_count"] == 1
    assert result["warning_count"] == 1


def test_parse_controller_historical_short():
    """Test historical data short."""
    # Needs 42 bytes + offset
    assert parse_controller_historical(b"\x00" * 40) == {}


def test_parse_controller_device_info_short():
    """Test device info short."""
    # registers 0x000A - 0x0011 (8 registers = 16 bytes)
    # limit check is likely around 16
    assert parse_controller_device_info(b"\x00" * 10) == {}


def test_parse_controller_device_id_short():
    """Test device id short."""
    # registers 0x001A (1 register = 2 bytes)
    assert parse_controller_device_id(b"\x00" * 3) == {}


def test_parse_controller_charging_info_short():
    """Test charging info short."""
    # registers 0x0100 -> many
    assert parse_controller_charging_info(b"\x00" * 20) == {}


# Final coverage tests for ble_parsers.py


# =================================================================================
# Controller Tests
# =================================================================================


def test_parse_controller_charging_info_branches():
    """Test branches in parse_controller_charging_info."""
    offset = 3
    # 1. Short data
    assert parse_controller_charging_info(b"\x00" * 60) == {}

    # 2. Unknown status & Partial faults
    # Need length >= 68 for basic, 70 for full faults
    # We provide exactly 68 + offset = 71 bytes to hit 'elif len >= 68' ?
    # Wait:
    # if len >= offset + 70: 4 bytes faults
    # elif len >= offset + 68: 2 bytes faults

    # Let's test Partial Faults branch (Length = offset + 69)
    # 3 + 69 = 72 bytes total? No, index is offset+68.
    # Buffer len = offset + 69
    data = create_buffer(69, offset)

    # Set charging_status (offset + 65) to unknown (e.g. 99)
    data[offset + 65] = 99

    # Set load_status (offset + 64) -> extract bit 7. 0 or 1.
    # If byte is 0x80 -> bit 7 is 1 -> "on"
    # If byte is 0x00 -> bit 7 is 0 -> "off"
    # To get unknown, dict only has 0 and 1. So likely never unknown unless we change dict.

    result = parse_controller_charging_info(bytes(data))

    assert result["charging_status"] == "unknown"
    # Should have hit partial faults branch
    assert "controller_faults" in result
    # We can check specific values if we set them, but coverage just needs the line hit

    # 3. Full faults branch
    data_full = create_buffer(70, offset)
    result_full = parse_controller_charging_info(bytes(data_full))
    assert "controller_faults" in result_full


# =================================================================================
# Battery Tests
# =================================================================================


def test_parse_battery_short_data():
    """Test short data returns for battery parsers."""
    assert parse_battery_cell_info(b"\x00" * 3) == {}
    assert parse_battery_temp_info(b"\x00" * 3) == {}
    assert parse_battery_info(b"\x00" * 10) == {}
    expected_empty_alarm = {
        "cell_voltage_alarms": [],
        "cell_temperature_alarms": [],
        "protection_alarms": [],
        "warnings": [],
        "alarm_count": 0,
        "warning_count": 0,
    }
    assert parse_battery_alarm_info(b"\x00" * 10) == expected_empty_alarm
    assert parse_battery_device_info(b"\x00" * 10) == {}


def test_parse_battery_info_logic():
    """Test logic in parse_battery_info."""
    offset = 3
    data = create_buffer(12, offset)

    # Total capacity (offset+8, 4 bytes)
    # Set to 0 to test 'if total_capacity > 0' else branch
    data[offset + 8] = 0
    data[offset + 9] = 0
    data[offset + 10] = 0
    data[offset + 11] = 0

    result = parse_battery_info(bytes(data))
    assert result["soc"] == 0

    # Set total capacity > 0
    data[offset + 11] = 100  # 100 * 0.001 = 0.1
    # Remaining (offset+4) = 50 -> 0.05
    data[offset + 7] = 50

    result = parse_battery_info(bytes(data))
    # 0.05 / 0.1 * 100 = 50.0
    assert result["soc"] == 50.0


def test_parse_battery_alarm_info_coverage():
    """Test detailed alarm parsing."""
    offset = 3
    data = create_buffer(20, offset)

    # Cell voltage alarms (offset+0, 4 bytes)
    # Set cell 1 to 1 (undervoltage), cell 2 to 2 (overvoltage), cell 3 to 3 (alarm)
    # bytes_to_int(data, offset, 4) parses as big-endian
    # data[offset] is highest byte -> bits 24-31 (Cells 13-16 if we map naively? No)
    # The code: alarm_code = (cell_voltage_alarm >> (cell * 2)) & 0x03
    # Cell 0 (Cell 1) is bits 0-1.
    # In a big-endian 32-bit int, bits 0-1 are the LOWEST bits, which come from the LAST byte (data[offset+3])

    # So we need to set data[offset+3]
    # Cell 1 (bits 0-1) = 1 (01)
    # Cell 2 (bits 2-3) = 2 (10)
    # Cell 3 (bits 4-5) = 3 (11)
    # Binary: 00 11 10 01 -> 0x39
    data[offset + 3] = 0x39

    # Status1 (offset+12, 2 bytes) -> short_circuit (bit 0)
    # 2 bytes big endian. Bit 0 is lowest bit -> data[offset+13]
    data[offset + 13] = 0x01

    # Status2 (offset+14, 2 bytes) -> effective_charge (bit 15)
    # Bit 15 is highest bit -> data[offset+14]
    data[offset + 14] = 0x80

    # Status3 (offset+16, 2 bytes) -> cell_low_voltage (bit 0)
    # Bit 0 is lowest bit -> data[offset+17]
    data[offset + 17] = 0x01

    result = parse_battery_alarm_info(bytes(data))

    assert "cell_1_undervoltage" in result["cell_voltage_alarms"]
    assert "cell_2_overvoltage" in result["cell_voltage_alarms"]
    assert "cell_3_alarm" in result["cell_voltage_alarms"]
    assert "short_circuit" in result["protection_alarms"]
    assert result["effective_charge"] is True
    assert "cell_low_voltage" in result["warnings"]


# =================================================================================
# Inverter Tests
# =================================================================================


def test_parse_inverter_short_data():
    """Test short data for inverter parsers."""
    assert parse_inverter_main_status(b"\x00" * 10) == {}
    assert parse_inverter_device_info(b"\x00" * 40) == {}
    assert parse_inverter_pv_info(b"\x00" * 10) == {}
    assert parse_inverter_settings_status(b"\x00" * 10) == {}
    # parse_inverter_settings_status has multiple ifs
    assert parse_inverter_statistics(b"\x00" * 5) == {}
    assert parse_inverter_settings(b"\x00" * 5) == {}


def test_parse_inverter_main_status_logic():
    """Test logic in parse_inverter_main_status."""
    offset = 3
    data = create_buffer(20, offset)

    # Safe value check: input_v_raw (offset) >= 65000
    data[offset] = 0xFF
    data[offset + 1] = 0xFF  # 65535

    # Calc power branch: input_v > 0 and input_c > 0
    # Set input_c (offset+2) to 100
    data[offset + 2] = 0x00
    data[offset + 3] = 0x64

    # Faults (offset+18 needed)
    # High faults (offset+14) -> input_uvp (bit 15)
    data[offset + 14] = 0x80

    result = parse_inverter_main_status(bytes(data))

    assert result["input_voltage"] == 0.0  # because >= 65000
    assert result["input_power"] == 0.0  # because voltage is 0
    assert "input_uvp" in result["faults"]

    # Input freq (offset+18)
    # We provided 20 bytes, so it should read input_freq
    assert "input_frequency" in result


def test_parse_inverter_pv_info_branches():
    """Test branches in parse_inverter_pv_info."""
    offset = 3
    # Length >= 12 checks
    data = create_buffer(12, offset)

    # Charging status (offset+10) -> unknown
    data[offset + 10] = 0x00
    data[offset + 11] = 99

    result = parse_inverter_pv_info(bytes(data))
    assert result["charging_status"] == "unknown"


def test_parse_inverter_settings_status_branches():
    """Test intermediate length checks."""
    offset = 3
    # 1. < 16 (but guard is at 30, so anything < 30 returns empty)
    assert parse_inverter_settings_status(create_buffer(10, offset)) == {}

    # 2. >= 32 (Full data)
    res = parse_inverter_settings_status(create_buffer(32, offset))
    assert "machine_state" in res
    assert "bus_voltage" in res
    assert "load_current" in res
    assert "load_percentage" in res


def test_parse_inverter_statistics_branches():
    """Test branches in parse_inverter_statistics."""
    offset = 3
    # 1. >= 10 but < 30
    res = parse_inverter_statistics(create_buffer(10, offset))
    assert "battery_charge_ah_today" in res
    assert "battery_charge_ah_total" not in res

    # 2. >= 30
    res = parse_inverter_statistics(create_buffer(30, offset))
    assert "battery_charge_ah_total" in res


# Refinement coverage tests for ble_parsers.py


def test_parse_battery_alarm_more_coverage():
    """Cover remaining alarm branches."""
    offset = 3
    data = create_buffer(20, offset)

    # Cell Temp Alarms (offset+4, 4 bytes)
    # Cell 1 (bits 0-1) -> 1 (undertemp)
    # data[offset+7] is low byte
    data[offset + 7] = 0x01

    # Other Alarms (offset+8, 4 bytes)
    # bms_board_temp (bits 0-1) -> 1 (low)
    # data[offset+11] is low byte
    data[offset + 11] = 0x01

    # Warnings (offset+16, 2 bytes)
    # cell_11_voltage_error -> bit 8 -> (index 0 of range(8) loop starting at bit 8)
    # Actually code:
    # for i in range(8): if status3 & (1 << (8 + i)): ...
    # i=0 -> bit 8.
    # Status3 is offset+16 (high), offset+17 (low).
    # Bit 8 is the lowest bit of the high byte -> data[offset+16] & 0x01
    data[offset + 16] = 0x01

    result = parse_battery_alarm_info(bytes(data))

    assert "cell_1_undertemp" in result["cell_temperature_alarms"]
    assert "bms_board_temp_low" in result["protection_alarms"]
    assert "cell_11_voltage_error" in result["warnings"]


def test_parse_inverter_main_status_low_faults_and_power():
    """Cover low faults loop and input power calc."""
    offset = 3
    data = create_buffer(20, offset)

    # Input Voltage: 120.0 V -> 1200 -> 0x04B0
    data[offset] = 0x04
    data[offset + 1] = 0xB0

    # Input Current: 1.0 A -> 100 -> 0x0064
    data[offset + 2] = 0x00
    data[offset + 3] = 0x64

    # Low Faults (offset+16, 2 bytes)
    # utility_fail (bit 15) -> 0x8000
    # High byte (offset+16) -> 0x80
    data[offset + 16] = 0x80

    result = parse_inverter_main_status(bytes(data))

    assert "utility_fail" in result["faults"]
    assert result["input_power"] == 120.0


def test_parse_response_debug_log():
    """Test debug log in parse_response."""
    with patch("custom_components.renogy.ble_parsers._LOGGER") as mock_logger:
        # Valid parsing
        data = create_buffer(16, 3)  # Enough for device_id (needs 2)
        data[3] = 1  # valid val

        parse_response(DeviceType.CONTROLLER, 26, bytes(data))

        # Verify debug called
        # _LOGGER.debug("Parsed %s register %s: %s", ...)
        assert mock_logger.debug.called


# Final refinement coverage tests for ble_parsers.py


def test_parse_battery_alarm_remaining_variants():
    """Cover remaining alarm code variants 2 and 3."""
    offset = 3
    data = create_buffer(20, offset)

    # cell_temp_alarm (offset + 4, 4 bytes)
    # Cell 1 (bits 0-1) -> 2 (overtemp)
    # Cell 2 (bits 2-3) -> 3 (temp_alarm)
    # data[offset+7] is low byte
    # Bits 0-3: 11 10 -> 0x0E
    data[offset + 7] = 0x0E

    # other_alarm (offset + 8, 4 bytes)
    # bms_board_temp (bits 0-1) -> code variant already test?
    # Let's set different positions to be sure.
    # bms_board_temp is checked twice (pos 0 and 2)?
    # Register 5104-5105 bits mapping:
    # bit 0-1: name1, bit 2-3: name1 (again?), etc.
    # Wait, the parser loop:
    # 382: ("bms_board_temp", 0),
    # 383: ("bms_board_temp", 2),
    # This might be how it's defined in the protocol.

    # Let's set variant 2 (high) for pos 0 and variant 3 (alarm) for pos 2
    # Bits 0-3: 11 10 -> 0x0E
    # data[offset+11] is low byte of 4-byte other_alarm
    data[offset + 11] = 0x0E

    result = parse_battery_alarm_info(bytes(data))

    assert "cell_1_overtemp" in result["cell_temperature_alarms"]
    assert "cell_2_temp_alarm" in result["cell_temperature_alarms"]
    assert "bms_board_temp_high" in result["protection_alarms"]
    assert "bms_board_temp_alarm" in result["protection_alarms"]
