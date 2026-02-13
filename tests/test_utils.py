"""Test BLE utilities."""

import pytest
from custom_components.renogy.ble_utils import (
    modbus_crc16,
    create_modbus_read_request,
    bytes_to_int,
    bytes_to_ascii,
    parse_temperature,
    validate_modbus_response,
    format_mac_address,
)


async def test_modbus_crc16():
    """Test CRC calculation."""
    # Example: Read registers 0x000A, 1 word from device 1
    # 01 03 00 0A 00 01
    data = bytes([0x01, 0x03, 0x00, 0x0A, 0x00, 0x01])
    crc_lo, crc_hi = modbus_crc16(data)
    # Expected CRC: A4 08
    assert crc_lo == 0xA4
    assert crc_hi == 0x08


async def test_create_modbus_read_request():
    """Test frame creation."""
    frame = create_modbus_read_request(1, 3, 10, 1)
    # 01 03 00 0A 00 01 A4 08
    expected = bytes([0x01, 0x03, 0x00, 0x0A, 0x00, 0x01, 0xA4, 0x08])
    assert frame == expected


async def test_bytes_to_int():
    """Test byte conversion."""
    data = bytes([0x01, 0xFF, 0x80, 0x00])

    # 1 byte
    assert bytes_to_int(data, 0, 1) == 1
    assert bytes_to_int(data, 1, 1) == 255
    assert bytes_to_int(data, 1, 1, signed=True) == -1

    # 2 bytes
    assert bytes_to_int(data, 0, 2) == 511  # 0x01FF
    assert bytes_to_int(data, 2, 2) == 0x8000  # 32768
    assert bytes_to_int(data, 2, 2, signed=True) == -32768

    # 4 bytes
    assert bytes_to_int(data, 0, 4) == 33521664

    # Scaling
    assert bytes_to_int(data, 0, 2, scale=0.1) == 51.1

    # Invalid length
    assert bytes_to_int(data, 0, 3) == 0

    # Short data
    assert bytes_to_int(data, 10, 1) == 0


async def test_bytes_to_ascii():
    """Test ASCII conversion."""
    data = b"Hello\x00World"
    assert bytes_to_ascii(data, 0, 5) == "Hello"
    assert (
        bytes_to_ascii(data, 0, 11) == "HelloWorld"
    )  # NUL skipped? Logic: if 32<=char<=126

    # NUL is 0, not printable. So skipped.
    # Logic in bytes_to_ascii: ONLY adds chars if 32<=char<=126.

    # Test short
    assert bytes_to_ascii(b"", 0, 5) == ""


async def test_parse_temperature():
    """Test temperature parsing."""
    assert parse_temperature(25) == 25
    assert parse_temperature(138) == -10  # 138 > 127 -> -(138-128) = -10

    # Offset
    assert parse_temperature(25, offset=10) == 15


async def test_validate_modbus_response():
    """Test response validation."""
    # Valid response: Dev 1, Func 3, 2 bytes, val 0x1234, CRC
    # 01 03 02 12 34 <CRC>
    payload = bytes([0x01, 0x03, 0x02, 0x12, 0x34])
    crc_lo, crc_hi = modbus_crc16(payload)
    frame = payload + bytes([crc_lo, crc_hi])  # Correct order for wire is lo, hi

    assert validate_modbus_response(frame, 1) is True
    assert validate_modbus_response(frame, 2) is False  # Wrong ID

    # Error response: 01 83 02 CRC
    err_payload = bytes([0x01, 0x83, 0x02])
    # validate_modbus_response checks data[1] & 0x80
    assert validate_modbus_response(err_payload) is False

    # Short
    assert validate_modbus_response(b"\x00") is False

    # CRC error
    bad_crc = payload + bytes([0x00, 0x00])
    assert validate_modbus_response(bad_crc) is False


async def test_format_mac_address():
    """Test MAC formatting."""
    assert format_mac_address("AA:BB:CC:DD:EE:FF") == "AA:BB:CC:DD:EE:FF"
    assert format_mac_address("aabbccddeeff") == "AA:BB:CC:DD:EE:FF"
    assert format_mac_address("AA-BB-CC-DD-EE-FF") == "AA:BB:CC:DD:EE:FF"

    with pytest.raises(ValueError):
        format_mac_address("invalid")
"""Test detailed coverage for ble_utils.py."""
import pytest
from custom_components.renogy.ble_utils import (
    bytes_to_int,
    validate_modbus_response,
)

def test_bytes_to_int_coverage():
    """Test bytes_to_int edge cases."""
    
    # Test length 4 signed
    # Max positive signed 32-bit: 2147483647 (0x7FFFFFFF)
    # Negative: -1 (0xFFFFFFFF)
    data = b"\xFF\xFF\xFF\xFF"
    val = bytes_to_int(data, 0, 4, signed=True)
    assert val == -1
    
    # Test unsupported length
    assert bytes_to_int(data, 0, 3) == 0
    assert bytes_to_int(data, 0, 5) == 0


def test_validate_modbus_response_coverage():
    """Test validate_modbus_response edge cases."""
    
    # Error response (Function code & 0x80)
    # [ID, Func|0x80, ErrorCode, CRC_L, CRC_H]
    # 0x83 = 0x03 | 0x80
    data = b"\x01\x83\x02\xC0\xF1" 
    assert validate_modbus_response(data) is False
    
    # Incomplete response based on byte count
    # [ID, Func, ByteCount, Data..., CRC_L, CRC_H]
    # ByteCount = 4, but we only provide 2 bytes of data
    # Length should be 3 (head) + 4 (data) + 2 (crc) = 9
    data = b"\x01\x03\x04\x00\x00" # Length 5
    assert validate_modbus_response(data) is False
