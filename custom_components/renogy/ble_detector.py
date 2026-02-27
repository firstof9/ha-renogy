"""BLE device type auto-detection utility."""

import asyncio
import logging
from typing import Any

from bleak import BleakClient, BleakError
from homeassistant.components import bluetooth
from homeassistant.core import HomeAssistant

from .ble_client import NOTIFY_CHAR_UUID, WRITE_CHAR_UUID
from .ble_utils import (
    create_modbus_read_request,
    validate_modbus_response,
)

_LOGGER = logging.getLogger(__name__)

# Timeout for the entire detection process
DETECTION_TIMEOUT = 15.0
# Timeout for waiting for a single characteristic read/notify response
RESPONSE_TIMEOUT = 3.0


async def async_detect_device_type(
    hass: HomeAssistant, mac_address: str
) -> tuple[str | None, int | None]:
    """Attempt to connect and determine device type and ID via Modbus.

    Returns:
        A tuple of (device_type, device_id) or (None, None) if detection fails.
    """
    ble_device = bluetooth.async_ble_device_from_address(hass, mac_address)
    if not ble_device:
        _LOGGER.debug("[%s] Detection failed: device not found in scanner", mac_address)
        return None, None

    client = BleakClient(ble_device)
    notification_event = asyncio.Event()
    response_data = bytearray()

    def notification_handler(sender: Any, data: bytearray) -> None:
        """Handle incoming BLE notifications."""
        response_data.extend(data)
        # We don't try to parse frames here to just trigger the event,
        # we will let the reader loop check the length.
        notification_event.set()

    try:
        async with asyncio.timeout(DETECTION_TIMEOUT):
            _LOGGER.debug("[%s] Connecting for detection...", mac_address)
            connected = await client.connect()
            if not connected:
                _LOGGER.debug("[%s] Detection failed: could not connect", mac_address)
                return None, None

            # Find actual characteristic UUIDs in case they differ slightly
            write_char = WRITE_CHAR_UUID
            notify_char = NOTIFY_CHAR_UUID
            for service in client.services:
                for char in service.characteristics:
                    if (
                        "write" in char.properties
                        or "write-without-response" in char.properties
                    ):
                        write_char = char.uuid
                    if "notify" in char.properties or "indicate" in char.properties:
                        notify_char = char.uuid

            await client.start_notify(notify_char, notification_handler)

            async def _read_register(
                device_id: int, register: int, words: int
            ) -> bytes | None:
                """Send a Modbus request and wait for a response."""
                response_data.clear()
                notification_event.clear()

                request = create_modbus_read_request(device_id, 3, register, words)
                try:
                    await client.write_gatt_char(write_char, request, response=False)
                except Exception as err:
                    _LOGGER.debug("[%s] Write failed: %s", mac_address, err)
                    return None

                expected_len = 3 + (words * 2) + 2
                end_time = asyncio.get_running_loop().time() + RESPONSE_TIMEOUT

                while asyncio.get_running_loop().time() < end_time:
                    wait_time = end_time - asyncio.get_running_loop().time()
                    if wait_time <= 0:
                        break

                    try:
                        async with asyncio.timeout(wait_time):
                            await notification_event.wait()
                    except TimeoutError:
                        break

                    notification_event.clear()

                    # Check for Modbus error frame
                    if len(response_data) >= 5 and response_data[1] & 0x80:
                        return bytes(response_data[:5])

                    # Check for valid full frame
                    if len(response_data) >= expected_len:
                        return bytes(response_data[:expected_len])

                return None

            # ---------------------------------------------------------
            # 1. Check for Controller / Inverter (Register 0x000C / 12)
            # ---------------------------------------------------------
            _LOGGER.debug("[%s] Probing Controller (ID 255)...", mac_address)
            resp = await _read_register(255, 12, 8)

            if resp:
                if validate_modbus_response(resp, 255):
                    # It's a valid controller
                    return "controller", 255

            # ---------------------------------------------------------
            # 2. Check for Battery (Register 5122)
            # ---------------------------------------------------------
            _LOGGER.debug("[%s] Probing Battery (ID 247)...", mac_address)
            resp = await _read_register(247, 5122, 6)

            if resp and validate_modbus_response(resp, 247):
                return "battery", 247

            _LOGGER.debug("[%s] Probing Battery (ID 255)...", mac_address)
            resp = await _read_register(255, 5122, 6)

            if resp and validate_modbus_response(resp, 255):
                return "battery", 255

    except TimeoutError:
        _LOGGER.debug("[%s] Detection timed out", mac_address)
    except BleakError as err:
        _LOGGER.debug("[%s] BLE error during detection: %s", mac_address, err)
    except Exception as err:
        _LOGGER.debug("[%s] Unexpected error during detection: %s", mac_address, err)
    finally:
        # Cleanup
        if client.is_connected:
            try:
                await client.stop_notify(notify_char)
                await client.disconnect()
            except Exception:
                pass

    _LOGGER.debug("[%s] Detection exhausted without a match", mac_address)
    return None, None
