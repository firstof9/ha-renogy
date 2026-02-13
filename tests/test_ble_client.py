"""Test BLE client implementation."""

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from bleak.backends.characteristic import BleakGATTCharacteristic
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError

from custom_components.renogy.ble_client import (
    BLEDeviceManager,
    DeviceConfig,
    DeviceData,
    DeviceType,
    PersistentBLEConnection,
    scan_for_devices,
)

pytestmark = pytest.mark.asyncio

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


# Coverage Tests

# Additional tests for coverage


async def test_device_config_enum_error():
    """Test invalid device type enum conversion."""
    conf = DeviceConfig("test", "AA:BB:CC:DD:EE:FF", "toaster")
    with pytest.raises(ValueError):
        conf.get_device_type_enum()


async def test_device_data_logic():
    """Test DeviceData update and failure logic."""
    conf = DeviceConfig("test", "AA:BB:CC:DD:EE:FF", "controller")
    data = DeviceData(config=conf)

    assert not data.is_available
    assert data.consecutive_failures == 0

    # Update success
    data.update({"volt": 12})
    assert data.is_available
    assert data.consecutive_failures == 0
    assert data.data["volt"] == 12

    # Mark failure
    data.mark_failed()
    assert data.consecutive_failures == 1
    assert data.is_available  # still true until 3

    data.mark_failed()
    assert data.consecutive_failures == 2

    data.mark_failed()
    assert data.consecutive_failures == 3
    assert not data.is_available


async def test_connection_retry_logic():
    """Test connection retry logic when device not found initially."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])

    with patch(
        "custom_components.renogy.ble_client.BleakScanner"
    ) as mock_scanner, patch(
        "custom_components.renogy.ble_client.BleakClient"
    ) as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ) as mock_sleep:

        # 1. find_device_by_address returns None initially
        # 2. discover returns empty list
        # 3. Next attempt find_device returns a device

        mock_device = MagicMock(spec=BLEDevice)
        mock_device.address = "AA:BB:CC:DD:EE:FF"

        # Attempt 1: Not found by address, Not found by scan
        # Attempt 2: Found by address
        mock_scanner.find_device_by_address = AsyncMock(
            side_effect=[None, mock_device, mock_device]
        )
        mock_scanner.discover = AsyncMock(return_value=[])

        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.start_notify = AsyncMock()
        mock_client.is_connected = True

        result = await conn.connect()

        assert result is True
        assert mock_scanner.find_device_by_address.call_count == 2


async def test_connection_retry_fail_after_3():
    """Test connection failure after 3 attempts."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])

    with patch(
        "custom_components.renogy.ble_client.BleakScanner"
    ) as mock_scanner, patch("asyncio.sleep", new_callable=AsyncMock):

        mock_scanner.find_device_by_address = AsyncMock(return_value=None)
        mock_scanner.discover = AsyncMock(return_value=[])

        result = await conn.connect()
        assert result is False
        assert mock_scanner.find_device_by_address.call_count == 3


async def test_connection_bleak_error():
    """Test handling of BleakError during connect."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])

    with patch(
        "custom_components.renogy.ble_client.BleakScanner"
    ) as mock_scanner, patch(
        "custom_components.renogy.ble_client.BleakClient"
    ) as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):

        mock_device = MagicMock(spec=BLEDevice)
        mock_scanner.find_device_by_address = AsyncMock(return_value=mock_device)

        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock(side_effect=BleakError("Connection failed"))

        result = await conn.connect()
        assert result is False
        assert mock_client.connect.call_count == 3


async def test_setup_characteristics_discovery():
    """Test characteristic discovery."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn.client = MagicMock()

    # Case 1: Found correct UUIDs
    service = MagicMock()
    char_w = MagicMock(spec=BleakGATTCharacteristic)
    char_w.uuid = WRITE_UUID
    char_n = MagicMock(spec=BleakGATTCharacteristic)
    char_n.uuid = NOTIFY_UUID
    service.characteristics = [char_w, char_n]
    conn.client.services = [service]

    await conn._setup_characteristics()
    assert conn._write_char == WRITE_UUID
    assert conn._notify_char == NOTIFY_UUID

    # Case 2: Not found, use defaults
    service.characteristics = []
    # conn.client.services is still [service]

    await conn._setup_characteristics()
    assert conn._write_char == WRITE_UUID  # Defaults are same as constants
    assert conn._notify_char == NOTIFY_UUID


async def test_read_registers_preconditions():
    """Test errors if async primitives not ready."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])

    # We mock _ensure_async_primitives to do nothing,
    # so we can trigger the RuntimeError checks
    with patch.object(conn, "_ensure_async_primitives"):
        with pytest.raises(RuntimeError, match="BLE async lock not initialized"):
            await conn.read_registers(1, 0, 1)


async def test_read_registers_write_fail():
    """Test write failure handling."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    # Initialize lock/event manually or via helper
    conn._ensure_async_primitives()
    conn.client = MagicMock()
    conn._connected = True
    conn.client.is_connected = True

    # Mock write failing
    conn.client.write_gatt_char = AsyncMock(side_effect=Exception("Write Error"))

    data = await conn.read_registers(1, 0, 1)
    assert data is None
    assert conn.is_connected is False


async def test_poll_device_no_reg():
    """Test polling device with no registers defined."""
    # Assuming 'inverter' has registers, let's make up a type or mock get_registers
    conf = DeviceConfig("dev", "mac", "controller")
    conn = PersistentBLEConnection("mac", [conf])

    with patch(
        "custom_components.renogy.ble_client.get_registers_for_device", return_value=[]
    ):
        data = await conn.poll_device(conf)
        assert data == {}


async def test_manager_hub_mode():
    """Test manager initialization grouping by MAC."""
    c1 = DeviceConfig("c1", "MAC1", "controller", 1)
    c2 = DeviceConfig("c2", "MAC1", "battery", 2)  # Same MAC
    c3 = DeviceConfig("c3", "MAC2", "inverter", 1)

    manager = BLEDeviceManager([c1, c2, c3])

    # Should have 2 connections
    assert len(manager._connections) == 2
    assert "MAC1" in manager._connections
    assert "MAC2" in manager._connections

    # MAC1 connection should have 2 configs
    assert len(manager._connections["MAC1"].device_configs) == 2


async def test_manager_reconnect_failure_in_poll():
    """Test manager handles reconnection failure during poll."""
    c1 = DeviceConfig("c1", "MAC1", "controller")
    manager = BLEDeviceManager([c1])
    conn = manager._connections["MAC1"]

    # Mock connection state as disconnected
    conn._connected = False
    conn.client = None

    # Mock connect failure
    with patch.object(conn, "connect", new_callable=AsyncMock) as mock_connect:
        mock_connect.return_value = False

        results = await manager.poll_all()

        assert results == {}
        # Verify device marked failed
        d_key = "MAC1_controller_255"
        assert manager._device_data[d_key].consecutive_failures > 0


async def test_scan_for_devices():
    """Test scanning function."""
    with patch(
        "custom_components.renogy.ble_client.BleakScanner.discover"
    ) as mock_discover:
        d1 = MagicMock(spec=BLEDevice)
        d1.name = "BT-TH-123"
        d1.address = "A1"
        d1.rssi = -50
        d2 = MagicMock(spec=BLEDevice)
        d2.name = "Renogy BT"
        d2.address = "A2"
        d2.rssi = -60
        d3 = MagicMock(spec=BLEDevice)
        d3.name = "Other"
        d3.address = "A3"
        d3.rssi = -70

        mock_discover.return_value = [d1, d2, d3]

        # Test Default (filter Renogy)
        results = await scan_for_devices()
        assert len(results) == 2
        names = [r["name"] for r in results]
        assert "BT-TH-123" in names
        assert "Renogy BT" in names
        assert "Other" not in names

        # Test Show All
        results = await scan_for_devices(show_all=True)
        assert len(results) == 3


async def test_scan_failure():
    """Test scan exception handling."""
    with patch(
        "custom_components.renogy.ble_client.BleakScanner.discover",
        side_effect=Exception("Scan fail"),
    ):
        results = await scan_for_devices()
        assert results == []


# Deep coverage tests for ble_client.py


async def test_connect_already_connected():
    """Test connect returns immediately if already connected."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn._connected = True
    conn.client = MagicMock()
    conn.client.is_connected = True

    assert await conn.connect() is True


async def test_connect_full_scan_fallback():
    """Test falling back to full scan when find_device_by_address fails."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])

    with patch(
        "custom_components.renogy.ble_client.BleakScanner"
    ) as mock_scanner, patch(
        "custom_components.renogy.ble_client.BleakClient"
    ) as mock_client_cls:

        # find_device_by_address returns None
        mock_scanner.find_device_by_address = AsyncMock(return_value=None)

        # discover returns list with our device
        mock_device = MagicMock(spec=BLEDevice)
        mock_device.address = "AA:BB:CC:DD:EE:FF"
        mock_scanner.discover = AsyncMock(return_value=[mock_device])

        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock(return_value=True)
        mock_client.is_connected = True
        mock_client.start_notify = AsyncMock()

        assert await conn.connect() is True

        mock_scanner.find_device_by_address.assert_awaited()
        mock_scanner.discover.assert_awaited()


async def test_connect_post_connect_check_fails():
    """Test connection considered failed if is_connected is False after connect()."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])

    with patch(
        "custom_components.renogy.ble_client.BleakScanner"
    ) as mock_scanner, patch(
        "custom_components.renogy.ble_client.BleakClient"
    ) as mock_client_cls, patch(
        "asyncio.sleep", new_callable=AsyncMock
    ):

        mock_device = MagicMock(spec=BLEDevice)
        mock_scanner.find_device_by_address = AsyncMock(return_value=mock_device)

        mock_client = mock_client_cls.return_value
        mock_client.connect = AsyncMock(return_value=True)
        # is_connected returns False even after connect()
        mock_client.is_connected = False

        assert await conn.connect() is False
        # Should try 3 times
        assert mock_client.connect.call_count == 3


async def test_disconnect_handling():
    """Test disconnect and _on_disconnect."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn._connected = True
    conn.client = MagicMock()

    # Test _on_disconnect
    conn._on_disconnect(None)
    assert conn._connected is False

    # Test disconnect with exceptions ignored
    conn.client = MagicMock()
    conn.client.stop_notify = AsyncMock(side_effect=Exception("Stop Notify Error"))
    conn.client.disconnect = AsyncMock(side_effect=Exception("Disconnect Error"))

    await conn.disconnect()
    assert conn.client is None


async def test_setup_characteristics_no_client():
    """Test _setup_characteristics returns early if client is None."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn.client = None
    await conn._setup_characteristics()
    assert conn._notify_char is None


async def test_read_registers_client_none_before_write():
    """Test RuntimeError if client became None before write."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn._ensure_async_primitives()
    conn._connected = True

    # Client is None
    conn.client = None

    # We need to bypass the initial check 'if not self.is_connected'
    # PersistentBLEConnection.is_connected checks self.client is not None
    # So strictly speaking, read_registers will try to reconnect if client is None.
    # We need to simulate: is_connected passes (Mock client), but then inside try block client is None.
    # But is_connected property checks self.client.

    # Let's mock is_connected property?
    with patch.object(PersistentBLEConnection, "is_connected", return_value=True):
        # Now it enters the block
        # But ensure we hit the line `if self.client is None: raise RuntimeError`
        # We need self.client to be None here.
        conn.client = None

        data = await conn.read_registers(1, 0, 1)
        assert data is None


async def test_poll_device_no_data_warning(caplog):
    """Test poll_device logging warning when no data is parsed."""
    config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])

    fake_regs = [{"name": "fake", "register": 1, "words": 1}]

    with patch(
        "custom_components.renogy.ble_client.get_registers_for_device",
        return_value=fake_regs,
    ), patch.object(
        conn, "read_registers", return_value=b"\x01\x03\x02\x00\x00\x00\x00"
    ), patch(
        "custom_components.renogy.ble_client.validate_modbus_response",
        return_value=True,
    ), patch(
        "custom_components.renogy.ble_client.parse_response", return_value={}
    ):

        with caplog.at_level(logging.WARNING):
            data = await conn.poll_device(config)
            assert data == {}
            assert "No data received from any registers" in caplog.text


async def test_connect_all_failures():
    """Test connect_all with mixed success."""
    c1 = DeviceConfig("c1", "MAC1", "controller")
    c2 = DeviceConfig("c2", "MAC2", "controller")  # Fails

    manager = BLEDeviceManager([c1, c2])

    p1 = manager._connections["MAC1"]
    p1.connect = AsyncMock(return_value=True)

    p2 = manager._connections["MAC2"]
    p2.connect = AsyncMock(return_value=False)

    count = await manager.connect_all()
    assert count == 1


async def test_poll_all_callbacks():
    """Test poll_all data callback execution."""
    c1 = DeviceConfig("c1", "MAC1", "controller")

    # Callback
    cb = MagicMock()
    async_cb = AsyncMock()

    # Manager with sync callback
    manager = BLEDeviceManager([c1], on_data_callback=cb)
    manager._connections["MAC1"].connect = AsyncMock(return_value=True)
    manager._connections["MAC1"].poll_device = AsyncMock(return_value={"volts": 12})

    await manager.poll_all()
    cb.assert_called()

    # Manager with async callback
    manager2 = BLEDeviceManager([c1], on_data_callback=async_cb)
    manager2._connections["MAC1"].connect = AsyncMock(return_value=True)
    manager2._connections["MAC1"].poll_device = AsyncMock(return_value={"volts": 12})

    await manager2.poll_all()
    async_cb.assert_awaited()


async def test_poll_all_callback_exception():
    """Test poll_all handles callback exception."""
    c1 = DeviceConfig("c1", "MAC1", "controller")

    cb = MagicMock(side_effect=Exception("Callback Boom"))

    manager = BLEDeviceManager([c1], on_data_callback=cb)
    manager._connections["MAC1"].connect = AsyncMock(return_value=True)
    manager._connections["MAC1"].poll_device = AsyncMock(return_value={"volts": 12})

    # Should not raise
    await manager.poll_all()
    # Device should be marked failed?
    # Logic: try ... poll_device ... if data ... callback ... except ... mark_failed
    # Yes, exception in callback triggers except block which marks failed.

    key = "MAC1_controller_255"
    assert manager._device_data[key].consecutive_failures > 0


# Additional coverage tests for ble_client.py


async def test_read_registers_no_notification_event():
    """Test RuntimeError when notification event is missing."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn._ensure_async_primitives()

    # Manually unset event but keep lock to get past first check
    conn._notification_event = None

    with pytest.raises(RuntimeError, match="BLE notification event not initialized"):
        await conn.read_registers(1, 0, 1)


async def test_read_registers_reconnect_fail():
    """Test reconnection failure inside read_registers."""
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [])
    conn._ensure_async_primitives()

    # We need to enter the lock
    async with conn._lock:
        pass  # Lock is ready

    # Mock is_connected to be False by setting internal state
    conn._connected = False
    conn.client = None

    # Mock connect() to return False
    # Since we are mocking the instance method, we can just replace it
    conn.connect = AsyncMock(return_value=False)

    data = await conn.read_registers(1, 0, 1)
    assert data is None
    conn.connect.assert_awaited()


async def test_poll_device_invalid_response():
    """Test poll_device logging warning on invalid response."""
    config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])

    fake_regs = [{"name": "fake", "register": 1, "words": 1}]

    with patch(
        "custom_components.renogy.ble_client.get_registers_for_device",
        return_value=fake_regs,
    ), patch.object(conn, "read_registers", return_value=b"\x00" * 5), patch(
        "custom_components.renogy.ble_client.validate_modbus_response",
        return_value=False,
    ):

        data = await conn.poll_device(config)
        assert data == {}


async def test_poll_device_no_data_received():
    """Test poll_device when read_registers returns None."""
    config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
    conn = PersistentBLEConnection("AA:BB:CC:DD:EE:FF", [config])

    fake_regs = [{"name": "fake", "register": 1, "words": 1}]

    with patch(
        "custom_components.renogy.ble_client.get_registers_for_device",
        return_value=fake_regs,
    ), patch.object(conn, "read_registers", return_value=None):

        data = await conn.poll_device(config)
        assert data == {}


async def test_poll_all_no_data_warning():
    """Test poll_all logging warning when poll_device returns empty."""
    config = DeviceConfig("dev1", "AA:BB:CC:DD:EE:FF", "controller")
    manager = BLEDeviceManager([config])

    conn = manager._connections["AA:BB:CC:DD:EE:FF"]
    conn._connected = True
    conn.client = MagicMock()
    conn.client.is_connected = True

    conn.connect = AsyncMock(return_value=True)
    conn.poll_device = AsyncMock(return_value={})

    # We just want to ensure it runs without error and hits the line
    await manager.poll_all()

    # Verify mark_failed was called
    key = "AA:BB:CC:DD:EE:FF_controller_255"
    assert manager._device_data[key].consecutive_failures > 0
