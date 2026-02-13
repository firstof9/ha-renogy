"""
Utility functions for Renogy BLE communication.

Includes Modbus CRC calculation and byte parsing helpers.
Adapted from https://github.com/Anto79-ops/renogy-ble
"""

from __future__ import annotations

import logging
from typing import Union

_LOGGER = logging.getLogger(__name__)


def modbus_crc16(data: bytes) -> tuple:
    """Calculate the Modbus CRC16 checksum.

    Args:
        data: Bytes to calculate CRC for.

    Returns:
        Tuple of (crc_low, crc_high) bytes.
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return (crc & 0xFF, (crc >> 8) & 0xFF)


def create_modbus_read_request(
    device_id: int, function_code: int, register: int, word_count: int
) -> bytearray:
    """Create a Modbus read request frame.

    Frame format:
    [device_id, function_code, register_hi, register_lo,
     word_count_hi, word_count_lo, crc_lo, crc_hi]

    Args:
        device_id: Modbus device address (1-247, or 255 for broadcast).
        function_code: Modbus function code (typically 3 for read holding registers).
        register: Starting register address.
        word_count: Number of 16-bit words to read.

    Returns:
        Bytearray containing the complete Modbus frame.
    """
    frame = bytearray(
        [
            device_id,
            function_code,
            (register >> 8) & 0xFF,
            register & 0xFF,
            (word_count >> 8) & 0xFF,
            word_count & 0xFF,
        ]
    )
    crc_low, crc_high = modbus_crc16(frame)
    frame.extend([crc_low, crc_high])
    _LOGGER.debug("Created Modbus request: register=%s, frame=%s", register, list(frame))
    return frame


def bytes_to_int(
    data: bytes,
    offset: int,
    length: int,
    scale: float = 1.0,
    signed: bool = False,
) -> Union[int, float]:
    """Convert bytes to integer or float value.

    Args:
        data: Raw byte data.
        offset: Starting byte offset.
        length: Number of bytes (1, 2, or 4).
        scale: Scale factor to apply.
        signed: Whether to interpret as signed integer.

    Returns:
        Integer or float value.
    """
    if offset + length > len(data):
        _LOGGER.warning(
            "Data too short: offset=%s, length=%s, data_len=%s",
            offset,
            length,
            len(data),
        )
        return 0

    if length == 1:
        value = data[offset]
        if signed and value > 127:
            value -= 256
    elif length == 2:
        value = (data[offset] << 8) | data[offset + 1]
        if signed and value > 32767:
            value -= 65536
    elif length == 4:
        value = (
            (data[offset] << 24)
            | (data[offset + 1] << 16)
            | (data[offset + 2] << 8)
            | data[offset + 3]
        )
        if signed and value > 2147483647:
            value -= 4294967296
    else:
        _LOGGER.warning("Unsupported byte length: %s", length)
        return 0

    if scale != 1.0:
        return round(value * scale, 3)
    return value


def bytes_to_ascii(data: bytes, offset: int, length: int) -> str:
    """Convert bytes to ASCII string.

    Args:
        data: Raw byte data.
        offset: Starting byte offset.
        length: Number of bytes.

    Returns:
        ASCII string (null characters and control chars stripped).
    """
    if offset + length > len(data):
        return ""

    result = ""
    for i in range(length):
        char = data[offset + i]
        if 32 <= char <= 126:  # Printable ASCII
            result += chr(char)
    return result.strip()


def parse_temperature(raw_value: int, offset: int = 0) -> float:
    """Parse temperature value with sign handling.

    Renogy devices sometimes encode temperature with sign bit.

    Args:
        raw_value: Raw temperature value.
        offset: Optional offset to subtract (e.g., for Kelvin to Celsius).

    Returns:
        Temperature in Celsius.
    """
    if raw_value > 127:
        return -(raw_value - 128) - offset
    return raw_value - offset


def validate_modbus_response(
    data: bytes, expected_device_id: int | None = None
) -> bool:
    """Validate a Modbus response frame.

    Args:
        data: Response data.
        expected_device_id: Expected device ID (optional).

    Returns:
        True if response is valid.
    """
    if len(data) < 5:
        _LOGGER.warning("Response too short: %s bytes", len(data))
        return False

    # Verify device ID if expected
    if expected_device_id is not None:
        actual_device_id = data[0]
        if actual_device_id != expected_device_id:
            _LOGGER.warning(
                "Unexpected device id: got %s, expected %s",
                actual_device_id,
                expected_device_id,
            )
            return False

    # Check for error response
    if data[1] & 0x80:
        error_code = data[2] if len(data) > 2 else 0
        _LOGGER.warning(
            "Modbus error response: function=%s, error_code=%s", data[1], error_code
        )
        return False

    # Validate CRC
    if len(data) >= 5:
        byte_count = data[2]
        expected_len = 3 + byte_count + 2
        if len(data) < expected_len:
            _LOGGER.warning(
                "Response incomplete: got %s, expected %s", len(data), expected_len
            )
            return False

        # Verify CRC
        payload = data[: expected_len - 2]
        received_crc = (data[expected_len - 1] << 8) | data[expected_len - 2]
        crc_low, crc_high = modbus_crc16(payload)
        calculated_crc = (crc_high << 8) | crc_low

        if received_crc != calculated_crc:
            _LOGGER.warning(
                "CRC mismatch: received=%s, calculated=%s",
                hex(received_crc),
                hex(calculated_crc),
            )
            return False

    return True


def format_mac_address(mac: str) -> str:
    """Normalize MAC address format to XX:XX:XX:XX:XX:XX.

    Args:
        mac: MAC address in various formats.

    Returns:
        Normalized MAC address string.
    """
    mac = mac.replace("-", "").replace(":", "").replace(" ", "").upper()

    if len(mac) != 12:
        raise ValueError(f"Invalid MAC address: {mac}")

    return ":".join(mac[i : i + 2] for i in range(0, 12, 2))
