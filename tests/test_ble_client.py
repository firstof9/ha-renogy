"""Test BLE client implementation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from custom_components.renogy.ble_client import (
    PersistentBLEConnection,
    DeviceConfig,
    BLEDeviceManager,
)
from bleak.backends.characteristic import BleakGATTCharacteristic

# Mock UUIDs
WRITE_UUID = "0000ffd1-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"


@pytest.fixture
def mock_bleak_client():
    """Mock BleakClient."""
    client = MagicMock()
    client.connect = AsyncMock(return_value=True)
    client.disconnect = AsyncMock(return_value=True)
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    client.write_gatt_char = AsyncMock()
    client.is_connected = True

    # Mock services/characteristics
    service = MagicMock()
    char_write = MagicMock(spec=BleakGATTCharacteristic)
    char_write.uuid = WRITE_UUID
    char_notify = MagicMock(spec=BleakGATTCharacteristic)
    char_notify.uuid = NOTIFY_UUID

    service.characteristics = [char_write, char_notify]
    client.services = [service]

    return client


async def test_persistent_connection_connect(mock_bleak_client):
    """Test connection establishment."""
    with patch(
        "custom_components.renogy.ble_client.BleakClient",
        return_value=mock_bleak_client,
    ), patch(
        "custom_components.renogy.ble_client.BleakScanner.find_device_by_address",
        return_value=MagicMock(),
    ):

        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
        connection = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])

        connected = await connection.connect()
        assert connected is True
        assert connection.is_connected

        mock_bleak_client.connect.assert_awaited_once()
        mock_bleak_client.start_notify.assert_awaited()


async def test_read_registers_success(mock_bleak_client):
    """Test reading registers successfully."""
    with patch(
        "custom_components.renogy.ble_client.BleakClient",
        return_value=mock_bleak_client,
    ), patch(
        "custom_components.renogy.ble_client.BleakScanner.find_device_by_address",
        return_value=MagicMock(),
    ):

        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
        connection = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])
        await connection.connect()

        # Setup notification triggering
        # When write_gatt_char is called, we simulate a notification response
        async def side_effect_write(char, data, response=False):
            # Simulate response: 01 03 02 12 34 CRC
            # ID=1, Func=3, Bytes=2, Val=0x1234
            # CRC for 01 03 02 12 34 is B5 33 (Low High) -> 01 03 02 12 34 33 B5?
            # modbus_crc16(01 03 02 12 34)
            # Just use valid response from bytes_to_int tests or similar.
            # let's assume valid CRC injection or mock validate_modbus_response

            # Response: ID(1) Func(3) Len(2) Data(00 0A) CRC_L CRC_H
            resp = bytes([0x01, 0x03, 0x02, 0x00, 0x0A, 0x38, 0x43])

            # Trigger notification
            connection._notification_handler(None, bytearray(resp))

        mock_bleak_client.write_gatt_char.side_effect = side_effect_write

        # We need to mock validate_modbus_response to always return True to simplify CRC math here
        with patch(
            "custom_components.renogy.ble_client.validate_modbus_response",
            return_value=True,
        ):
            data = await connection.read_registers(
                device_id=1, register=0, word_count=1
            )
            assert data is not None
            assert len(data) == 7  # The full frame


async def test_read_registers_timeout(mock_bleak_client):
    """Test read timeout."""
    with patch(
        "custom_components.renogy.ble_client.BleakClient",
        return_value=mock_bleak_client,
    ), patch(
        "custom_components.renogy.ble_client.BleakScanner.find_device_by_address",
        return_value=MagicMock(),
    ):

        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
        connection = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])
        await connection.connect()

        # Adjust timeout to be fast for test
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            data = await connection.read_registers(1, 0, 1)
            assert data is None


async def test_poll_device(mock_bleak_client):
    """Test full device polling."""
    with patch(
        "custom_components.renogy.ble_client.BleakClient",
        return_value=mock_bleak_client,
    ), patch(
        "custom_components.renogy.ble_client.BleakScanner.find_device_by_address",
        return_value=MagicMock(),
    ), patch(
        "custom_components.renogy.ble_client.validate_modbus_response",
        return_value=True,
    ), patch(
        "custom_components.renogy.ble_client.PersistentBLEConnection.read_registers"
    ) as mock_read:

        # Setup mock read to return dummy data for each call
        mock_read.return_value = b"\x00" * 20  # Dummy data

        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
        connection = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])
        await connection.connect()

        # Mock get_registers_for_device and parse_response
        fake_registers = [{"name": "fake_reg", "register": 100, "words": 1}]

        with patch(
            "custom_components.renogy.ble_client.get_registers_for_device",
            return_value=fake_registers,
        ), patch(
            "custom_components.renogy.ble_client.parse_response",
            return_value={"fake_val": 123},
        ):

            data = await connection.poll_device(config)
            assert data["fake_val"] == 123
            assert data["__device"] == "dev1"


async def test_manager_poll_all(mock_bleak_client):
    """Test manager polling."""
    # Mock connection class
    with patch(
        "custom_components.renogy.ble_client.PersistentBLEConnection"
    ) as MockConn:
        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")

        instance = MockConn.return_value
        instance.connect = AsyncMock(return_value=True)
        instance.poll_device = AsyncMock(return_value={"data": 1})
        instance.device_configs = [config]

        manager = BLEDeviceManager([config])

        await manager.connect_all()
        results = await manager.poll_all()

        key = "AA:BB:CC:DD:EE:FF_controller_255"
        assert key in results
        assert results[key]["data"] == 1


async def test_manager_get_data(mock_bleak_client):
    """Test manager get data methods."""
    with patch(
        "custom_components.renogy.ble_client.PersistentBLEConnection"
    ) as MockConn:
        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
        instance = MockConn.return_value
        instance.connect = AsyncMock(return_value=True)  # Needs to be AsyncMock
        instance.poll_device = AsyncMock(return_value={"data": 1})
        instance.device_configs = [config]

        manager = BLEDeviceManager([config])
        await manager.connect_all()
        await manager.poll_all()

        key = "AA:BB:CC:DD:EE:FF_controller_255"
        device_data = manager.get_device_data(key)
        assert device_data.data["data"] == 1

        all_data = manager.get_all_device_data()
        assert key in all_data


async def test_manager_stop(mock_bleak_client):
    """Test manager stop."""
    with patch(
        "custom_components.renogy.ble_client.PersistentBLEConnection"
    ) as MockConn:
        instance = MockConn.return_value
        instance.connect = AsyncMock(return_value=True)  # Needs to be AsyncMock
        instance.disconnect = AsyncMock()

        config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
        manager = BLEDeviceManager([config])

        await manager.connect_all()
        await manager.stop()

        instance.disconnect.assert_awaited()
