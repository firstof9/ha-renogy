"""Tests for the BLE detector auto-discovery."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from bleak.backends.device import BLEDevice

from custom_components.renogy.ble_client import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID
from custom_components.renogy.ble_detector import async_detect_device_type


@pytest.fixture
def mock_ble_device():
    """Mock a bleak BLEDevice."""
    return BLEDevice("AA:BB:CC:DD:EE:FF", "Renogy BT", details={})


@pytest.fixture
def mock_client():
    """Mock BleakClient."""
    client = MagicMock()
    client.is_connected = True
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()

    # Mock service & characteristics
    char_write = MagicMock()
    char_write.uuid = WRITE_CHAR_UUID
    char_write.properties = ["write-without-response"]

    char_notify = MagicMock()
    char_notify.uuid = NOTIFY_CHAR_UUID
    char_notify.properties = ["notify"]

    service = MagicMock()
    service.characteristics = [char_write, char_notify]

    client.services = [service]
    return client


async def test_detect_device_not_found(hass):
    """Test detection when device is not in BLE scanner."""
    with patch(
        "custom_components.renogy.ble_detector.bluetooth.async_ble_device_from_address",
        return_value=None,
    ):
        device_type, device_id = await async_detect_device_type(
            hass, "AA:BB:CC:DD:EE:FF"
        )
        assert device_type is None
        assert device_id is None


async def test_detect_device_cannot_connect(hass, mock_ble_device, mock_client):
    """Test detection when device fails to connect."""
    mock_client.connect.return_value = False

    with (
        patch(
            "custom_components.renogy.ble_detector.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.renogy.ble_detector.BleakClient",
            return_value=mock_client,
        ),
    ):
        device_type, device_id = await async_detect_device_type(
            hass, "AA:BB:CC:DD:EE:FF"
        )
        assert device_type is None
        assert device_id is None


async def test_detect_device_controller_success(hass, mock_ble_device, mock_client):
    """Test successful detection of a controller."""
    # Valid Modbus response for controller (ID 255, func 3, 16 bytes data)
    # 0xFF 0x03 0x10 [16 bytes of "ROVER"] CRC
    resp_data = (
        bytearray([0xFF, 0x03, 0x10]) + b"ROVER           " + bytearray([0x00, 0x00])
    )

    def mock_write(*args, **kwargs):
        # Simulate the notification handler being called
        handler = mock_client.start_notify.call_args[0][1]
        hass.loop.call_soon(handler, None, resp_data)

    mock_client.write_gatt_char.side_effect = mock_write

    with (
        patch(
            "custom_components.renogy.ble_detector.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.renogy.ble_detector.BleakClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.renogy.ble_detector.validate_modbus_response",
            return_value=True,
        ),
    ):
        device_type, device_id = await async_detect_device_type(
            hass, "AA:BB:CC:DD:EE:FF"
        )
        assert device_type == "controller"
        assert device_id == 255


async def test_detect_device_battery_success(hass, mock_ble_device, mock_client):
    """Test successful detection of a battery after controller probe returns Modbus error."""
    # 1. Controller probe returns Modbus error (Illegal Data Address)
    # 0xFF 0x83 0x02 CRC
    err_data = bytearray([0xFF, 0x83, 0x02, 0x50, 0x30])

    # 2. Battery probe returns valid data (ID 247, func 3, 12 bytes data)
    # 0xF7 0x03 0x0C [12 bytes] CRC
    batt_data = (
        bytearray([0xF7, 0x03, 0x0C]) + b"LITHIUM BT  " + bytearray([0x00, 0x00])
    )

    call_count = 0

    def mock_write(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        handler = mock_client.start_notify.call_args[0][1]

        if call_count == 1:
            hass.loop.call_soon(handler, None, err_data)
        elif call_count == 2:
            hass.loop.call_soon(handler, None, batt_data)

    mock_client.write_gatt_char.side_effect = mock_write

    with (
        patch(
            "custom_components.renogy.ble_detector.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.renogy.ble_detector.BleakClient",
            return_value=mock_client,
        ),
        patch(
            "custom_components.renogy.ble_detector.validate_modbus_response",
            side_effect=lambda r, i: not (len(r) == 5 and r[1] & 0x80),
        ),
    ):
        device_type, device_id = await async_detect_device_type(
            hass, "AA:BB:CC:DD:EE:FF"
        )
        assert device_type == "battery"
        assert device_id == 247


async def test_detect_device_battery_no_response(hass, mock_ble_device, mock_client):
    """Test detection when battery never responds."""

    def mock_write(*args, **kwargs):
        pass  # No response from device

    mock_client.write_gatt_char.side_effect = mock_write

    with (
        patch(
            "custom_components.renogy.ble_detector.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.renogy.ble_detector.BleakClient",
            return_value=mock_client,
        ),
        patch("custom_components.renogy.ble_detector.RESPONSE_TIMEOUT", 0.01),
    ):
        device_type, device_id = await async_detect_device_type(
            hass, "AA:BB:CC:DD:EE:FF"
        )
        assert device_type is None
        assert device_id is None


async def test_detect_device_timeout(hass, mock_ble_device, mock_client):
    """Test detection module timeout."""

    async def mock_connect(*args, **kwargs):
        await asyncio.sleep(0.5)
        return True

    mock_client.connect.side_effect = mock_connect

    with (
        patch(
            "custom_components.renogy.ble_detector.bluetooth.async_ble_device_from_address",
            return_value=mock_ble_device,
        ),
        patch(
            "custom_components.renogy.ble_detector.BleakClient",
            return_value=mock_client,
        ),
        patch("custom_components.renogy.ble_detector.DETECTION_TIMEOUT", 0.1),
    ):
        device_type, device_id = await async_detect_device_type(
            hass, "AA:BB:CC:DD:EE:FF"
        )
        assert device_type is None
        assert device_id is None
