---
name: Renogy BLE Client Guidelines
description: Guidelines for managing and writing tests/code for the custom Renogy BLE Client communication.
---

# Renogy BLE Client Guidelines

This skill ensures that all changes and additions to the BLE communication within the `ha-renogy` integration follow safe, async, and correct patterns when interfacing with BLE devices using `bleak` and Home Assistant's `bluetooth` component.

## Guidelines

### 1. BLE Connection Management
* Never perform blocking operations on the event loop. Always use async methods for connecting, disconnecting, reading, and writing to characteristics.
* Implement robust retry/reconnection logic when connection attempts fail. Ensure the client releases any active connections or handles `BleakError` / `BleakDBusError` exceptions cleanly.
* Leverage `async_register_callback` or the bluetooth integration's connection tracking hooks to clean up BLE client instances when the config entry is unloaded.

### 2. BLE Notifications and Subscriptions
* Keep notification handlers/callbacks lightweight. Delegate any complex parsing or state changes to async tasks or dispatcher signals rather than executing them inside the raw Bluetooth callback thread/context.
* Ensure characteristics notifications are successfully unsubscribed on disconnect/unload.

### 3. Testing BLE Clients
* When testing BLE components, mock the `bleak` client calls and Home Assistant's `bluetooth` scanner components.
* Ensure all BLE tests yield control back to the event loop so that connection hooks can trigger mock events properly.
