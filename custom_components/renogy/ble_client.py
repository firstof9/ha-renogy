"""
BLE communication module for Renogy devices.

Uses persistent connections via Bleak for reliability.
Adapted from https://github.com/Anto79-ops/renogy-ble
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from bleak import BleakClient, BleakScanner
from bleak.exc import BleakError

from .ble_parsers import DeviceType, get_registers_for_device, parse_response
from .ble_utils import create_modbus_read_request, validate_modbus_response

_LOGGER = logging.getLogger(__name__)

# Renogy BLE Service and Characteristic UUIDs
NOTIFY_CHAR_UUID = "0000fff1-0000-1000-8000-00805f9b34fb"
WRITE_CHAR_UUID = "0000ffd1-0000-1000-8000-00805f9b34fb"

# Timeouts
CONNECTION_TIMEOUT = 30.0
NOTIFICATION_TIMEOUT = 5.0
REQUEST_DELAY = 0.5
RECONNECT_DELAY = 10.0


def _obfuscate_mac(mac: str) -> str:
    """Obfuscate a MAC address for logging, showing only the last 4 chars."""
    parts = mac.split(":")
    if len(parts) == 6:
        return f"**:**:**:**:{parts[4]}:{parts[5]}"
    # Fallback: show last 5 chars
    return f"***{mac[-5:]}" if len(mac) > 5 else "***"


@dataclass
class DeviceConfig:
    """Configuration for a Renogy BLE device."""

    name: str
    mac_address: str
    device_type: str  # 'controller', 'battery', 'inverter'
    device_id: int = 255

    def get_device_type_enum(self) -> DeviceType:
        """Convert string device_type to DeviceType enum."""
        type_map = {
            "controller": DeviceType.CONTROLLER,
            "battery": DeviceType.BATTERY,
            "inverter": DeviceType.INVERTER,
        }
        return type_map.get(self.device_type.lower(), DeviceType.CONTROLLER)


@dataclass
class DeviceData:
    """Stores data collected from a device."""

    config: DeviceConfig
    data: Dict[str, Any] = field(default_factory=dict)
    last_update: Optional[datetime] = None
    is_available: bool = False
    consecutive_failures: int = 0

    def update(self, new_data: Dict[str, Any]) -> None:
        """Update device data with new readings."""
        self.data.update(new_data)
        self.last_update = datetime.now()
        self.is_available = True
        self.consecutive_failures = 0

    def mark_failed(self) -> None:
        """Mark a failed poll attempt."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= 3:
            self.is_available = False


class PersistentBLEConnection:
    """Manages a persistent BLE connection to a Renogy BT module.

    Handles automatic reconnection and supports Hub mode
    (multiple devices on one BT module).
    """

    def __init__(
        self, mac_address: str, device_configs: List[DeviceConfig]
    ) -> None:
        """Initialize the connection."""
        self.mac_address = mac_address
        self.device_configs = device_configs
        self.client: Optional[BleakClient] = None
        self._connected = False
        self._notify_char: Optional[str] = None
        self._write_char: Optional[str] = None
        self._notification_data = bytearray()
        self._notification_event: Optional[asyncio.Event] = None
        self._lock: Optional[asyncio.Lock] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    @property
    def is_connected(self) -> bool:
        """Return True if connected."""
        return self._connected and self.client is not None and self.client.is_connected

    def _ensure_async_primitives(self) -> None:
        """Ensure asyncio primitives are created in the current event loop."""
        current_loop = asyncio.get_event_loop()
        if self._loop is not current_loop:
            self._loop = current_loop
            self._notification_event = asyncio.Event()
            self._lock = asyncio.Lock()

    def _notification_handler(self, sender: int, data: bytearray) -> None:
        """Handle incoming notification data."""
        _LOGGER.debug("[%s] Notification: %s", _obfuscate_mac(self.mac_address), data.hex())
        self._notification_data.extend(data)
        if self._notification_event is not None:
            self._notification_event.set()

    async def connect(self) -> bool:
        """Establish connection to the BT module."""
        self._ensure_async_primitives()

        if self.is_connected:
            return True

        for attempt in range(3):
            try:
                if attempt > 0:
                    _LOGGER.info(
                        "[%s] Retry %s/3...", _obfuscate_mac(self.mac_address), attempt + 1
                    )
                    await asyncio.sleep(5.0)

                _LOGGER.info("[%s] Connecting...", _obfuscate_mac(self.mac_address))

                device = await BleakScanner.find_device_by_address(
                    self.mac_address,
                    timeout=CONNECTION_TIMEOUT,
                )

                if not device:
                    _LOGGER.debug(
                        "[%s] Not found, running full scan...", _obfuscate_mac(self.mac_address)
                    )
                    devices = await BleakScanner.discover(timeout=10.0)
                    for found in devices:
                        if found.address.upper() == self.mac_address.upper():
                            device = found
                            break

                if not device:
                    _LOGGER.warning("[%s] Device not found", _obfuscate_mac(self.mac_address))
                    continue

                self.client = BleakClient(
                    device,
                    timeout=CONNECTION_TIMEOUT,
                    disconnected_callback=self._on_disconnect,
                )
                await self.client.connect()

                if not self.client.is_connected:
                    _LOGGER.warning("[%s] Connection failed", _obfuscate_mac(self.mac_address))
                    continue

                await self._setup_characteristics()

                await self.client.start_notify(
                    self._notify_char, self._notification_handler
                )

                self._connected = True
                _LOGGER.info("[%s] Connected successfully", _obfuscate_mac(self.mac_address))
                return True

            except BleakError as err:
                _LOGGER.warning(
                    "[%s] BLE error (attempt %s): %s",
                    _obfuscate_mac(self.mac_address),
                    attempt + 1,
                    err,
                )
            except Exception:  # pylint: disable=broad-except
                _LOGGER.warning(
                    "[%s] Error (attempt %s)",
                    _obfuscate_mac(self.mac_address),
                    attempt + 1,
                    exc_info=True,
                )

            if self.client:
                try:
                    await self.client.disconnect()
                except Exception:  # pylint: disable=broad-except
                    pass
                self.client = None

        _LOGGER.error(
            "[%s] Failed to connect after 3 attempts", _obfuscate_mac(self.mac_address)
        )
        return False

    def _on_disconnect(self, client: BleakClient) -> None:
        """Handle disconnection callback."""
        _LOGGER.warning("[%s] Disconnected!", _obfuscate_mac(self.mac_address))
        self._connected = False

    async def _setup_characteristics(self) -> None:
        """Find the write and notify characteristics."""
        self._notify_char = None
        self._write_char = None

        standard_write = "0000ffd1-0000-1000-8000-00805f9b34fb"
        standard_notify = "0000fff1-0000-1000-8000-00805f9b34fb"

        if self.client is None:
            return

        _LOGGER.debug("[%s] Discovering characteristics...", _obfuscate_mac(self.mac_address))
        for service in self.client.services:
            for char in service.characteristics:
                if char.uuid.lower() == standard_write:
                    self._write_char = char.uuid
                    _LOGGER.debug(
                        "[%s] Found write char: %s", _obfuscate_mac(self.mac_address), char.uuid
                    )
                elif char.uuid.lower() == standard_notify:
                    self._notify_char = char.uuid
                    _LOGGER.debug(
                        "[%s] Found notify char: %s", _obfuscate_mac(self.mac_address), char.uuid
                    )

        if not self._notify_char:
            self._notify_char = NOTIFY_CHAR_UUID
            _LOGGER.warning(
                "[%s] Using default notify char: %s",
                _obfuscate_mac(self.mac_address),
                self._notify_char,
            )
        if not self._write_char:
            self._write_char = WRITE_CHAR_UUID
            _LOGGER.warning(
                "[%s] Using default write char: %s",
                _obfuscate_mac(self.mac_address),
                self._write_char,
            )

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        self._connected = False
        if self.client:
            try:
                await self.client.stop_notify(self._notify_char)
            except Exception:  # pylint: disable=broad-except
                pass
            try:
                await self.client.disconnect()
            except Exception:  # pylint: disable=broad-except
                pass
            self.client = None
        _LOGGER.info("[%s] Disconnected", _obfuscate_mac(self.mac_address))

    async def read_registers(
        self, device_id: int, register: int, word_count: int
    ) -> Optional[bytes]:
        """Read registers from a device on this BT module.

        Args:
            device_id: Modbus device ID.
            register: Starting register address.
            word_count: Number of words to read.

        Returns:
            Response bytes or None on failure.
        """
        self._ensure_async_primitives()

        assert self._lock is not None
        assert self._notification_event is not None

        async with self._lock:
            if not self.is_connected:
                _LOGGER.warning(
                    "[%s] Not connected, attempting reconnect...",
                    _obfuscate_mac(self.mac_address),
                )
                if not await self.connect():
                    return None

            self._notification_data.clear()
            self._notification_event.clear()

            request = create_modbus_read_request(device_id, 0x03, register, word_count)
            _LOGGER.debug(
                "[%s] Sending request (dev=%s, reg=%s, words=%s): %s",
                _obfuscate_mac(self.mac_address),
                device_id,
                register,
                word_count,
                request.hex(),
            )

            try:
                assert self.client is not None
                await self.client.write_gatt_char(self._write_char, request)
            except Exception as err:
                _LOGGER.error("[%s] Write failed: %s", _obfuscate_mac(self.mac_address), err)
                self._connected = False
                return None

            try:
                await asyncio.wait_for(
                    self._notification_event.wait(), timeout=NOTIFICATION_TIMEOUT
                )
            except asyncio.TimeoutError:
                _LOGGER.warning(
                    "[%s] Timeout waiting for response (reg=%s, dev_id=%s)",
                    _obfuscate_mac(self.mac_address),
                    register,
                    device_id,
                )
                return None

            # Wait a bit more for fragmented responses
            await asyncio.sleep(0.3)

            response = bytes(self._notification_data)
            if response:
                _LOGGER.debug(
                    "[%s] Response (%s bytes): %s",
                    _obfuscate_mac(self.mac_address),
                    len(response),
                    response.hex(),
                )

            return response if len(response) >= 5 else None

    async def poll_device(self, config: DeviceConfig) -> Dict[str, Any]:
        """Poll a specific device on this BT module.

        Args:
            config: Device configuration.

        Returns:
            Dictionary of parsed data.
        """
        device_type_enum = config.get_device_type_enum()
        registers = get_registers_for_device(device_type_enum)
        _LOGGER.debug(
            "[%s] Device type: %s, Reading %s register groups",
            config.name,
            device_type_enum,
            len(registers),
        )

        if not registers:
            _LOGGER.error(
                "[%s] No registers defined for device type: %s",
                config.name,
                config.device_type,
            )
            return {}

        all_data: Dict[str, Any] = {}

        for reg_info in registers:
            _LOGGER.debug(
                "[%s] Reading %s (reg=%s, words=%s)",
                config.name,
                reg_info["name"],
                reg_info["register"],
                reg_info["words"],
            )

            response = await self.read_registers(
                config.device_id,
                reg_info["register"],
                reg_info["words"],
            )

            if response:
                if validate_modbus_response(response, config.device_id):
                    parsed = parse_response(
                        device_type_enum, reg_info["register"], response
                    )
                    all_data.update(parsed)
                    _LOGGER.debug(
                        "[%s] %s: parsed %s fields",
                        config.name,
                        reg_info["name"],
                        len(parsed),
                    )
                else:
                    _LOGGER.warning(
                        "[%s] Invalid response for %s: %s",
                        config.name,
                        reg_info["name"],
                        response.hex(),
                    )
            else:
                _LOGGER.debug(
                    "[%s] No response for %s", config.name, reg_info["name"]
                )

            await asyncio.sleep(REQUEST_DELAY)

        if all_data:
            all_data["__device"] = config.name
            all_data["__mac_address"] = config.mac_address
            all_data["__device_type"] = config.device_type
            _LOGGER.info(
                "[%s] Got %s data fields", config.name, len(all_data) - 3
            )
        else:
            _LOGGER.warning("[%s] No data received from any registers", config.name)

        return all_data


class BLEDeviceManager:
    """Manages persistent BLE connections to multiple Renogy BT modules."""

    def __init__(
        self,
        device_configs: List[DeviceConfig],
        on_data_callback: Optional[Callable] = None,
    ) -> None:
        """Initialize the device manager."""
        self._connections: Dict[str, PersistentBLEConnection] = {}
        self._device_data: Dict[str, DeviceData] = {}

        devices_by_mac: Dict[str, List[DeviceConfig]] = {}
        for config in device_configs:
            mac = config.mac_address.upper()
            if mac not in devices_by_mac:
                devices_by_mac[mac] = []
            devices_by_mac[mac].append(config)

            device_key = f"{mac}_{config.device_type}"
            self._device_data[device_key] = DeviceData(config=config)

        for mac, configs in devices_by_mac.items():
            self._connections[mac] = PersistentBLEConnection(mac, configs)
            if len(configs) > 1:
                _LOGGER.info("Hub mode: %s devices on %s", len(configs), _obfuscate_mac(mac))

        self.on_data_callback = on_data_callback
        self._running = False

        _LOGGER.info(
            "Device manager: %s devices on %s BT modules",
            len(self._device_data),
            len(self._connections),
        )

    async def connect_all(self) -> int:
        """Connect to all BT modules.

        Returns:
            Number of successful connections.
        """
        connected = 0
        for mac, connection in self._connections.items():
            _LOGGER.info("Connecting to BT module: %s", _obfuscate_mac(mac))
            if await connection.connect():
                connected += 1
            else:
                _LOGGER.error("Failed to connect to: %s", _obfuscate_mac(mac))
            await asyncio.sleep(3.0)

        return connected

    async def disconnect_all(self) -> None:
        """Disconnect from all BT modules."""
        for connection in self._connections.values():
            await connection.disconnect()

    async def poll_all(self) -> Dict[str, Dict[str, Any]]:
        """Poll all devices.

        Returns:
            Dictionary mapping device keys to data.
        """
        results: Dict[str, Dict[str, Any]] = {}

        for mac, connection in self._connections.items():
            if not connection.is_connected:
                _LOGGER.warning("[%s] Not connected, reconnecting...", _obfuscate_mac(mac))
                if not await connection.connect():
                    _LOGGER.error("[%s] Reconnection failed", _obfuscate_mac(mac))
                    for config in connection.device_configs:
                        device_key = f"{mac}_{config.device_type}"
                        self._device_data[device_key].mark_failed()
                    continue

            for config in connection.device_configs:
                device_key = f"{mac}_{config.device_type}"
                _LOGGER.info(
                    "Polling: %s (type=%s, id=%s)",
                    config.name,
                    config.device_type,
                    config.device_id,
                )

                try:
                    data = await connection.poll_device(config)

                    if data:
                        self._device_data[device_key].update(data)
                        results[device_key] = data

                        if self.on_data_callback:
                            await self.on_data_callback(device_key, data)
                    else:
                        _LOGGER.warning("  %s: No data", config.name)
                        self._device_data[device_key].mark_failed()

                except Exception:  # pylint: disable=broad-except
                    _LOGGER.error(
                        "  %s: Error polling", config.name, exc_info=True
                    )
                    self._device_data[device_key].mark_failed()

                await asyncio.sleep(1.0)

            await asyncio.sleep(2.0)

        return results

    def get_device_data(self, device_key: str) -> Optional[DeviceData]:
        """Get data for a specific device."""
        return self._device_data.get(device_key)

    def get_all_device_data(self) -> Dict[str, DeviceData]:
        """Get data for all devices."""
        return self._device_data

    async def stop(self) -> None:
        """Stop polling and disconnect."""
        self._running = False
        await self.disconnect_all()
        _LOGGER.info("Device manager stopped")


async def scan_for_devices(
    timeout: float = 15.0, show_all: bool = False
) -> List[Dict]:
    """Scan for nearby Renogy BLE devices.

    Args:
        timeout: Scan timeout in seconds.
        show_all: If True, show all BLE devices, not just Renogy ones.

    Returns:
        List of discovered device dictionaries.
    """
    _LOGGER.info("Scanning for BLE devices (timeout: %ss)...", timeout)

    try:
        devices = await BleakScanner.discover(timeout=timeout)
    except Exception:  # pylint: disable=broad-except
        _LOGGER.error("Scan failed", exc_info=True)
        return []

    results = []
    for device in devices:
        name = device.name or ""

        if show_all or name.startswith("BT-TH") or "RENOGY" in name.upper():
            results.append(
                {
                    "name": name,
                    "address": device.address,
                    "rssi": device.rssi if hasattr(device, "rssi") else None,
                }
            )

    results.sort(key=lambda x: x.get("rssi") or -100, reverse=True)

    _LOGGER.info(
        "Found %s %s devices",
        len(results),
        "total" if show_all else "Renogy",
    )
    return results
