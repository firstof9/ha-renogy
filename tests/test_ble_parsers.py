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
