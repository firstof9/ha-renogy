# AGENTS.md

A concise orientation for AI coding agents (Claude, Codex, Gemini, Copilot, etc.) working in this repository. For human contributor guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## What this repo is

A Home Assistant custom integration for Renogy products, supporting both:
1. **Renogy Cloud API**: via Renogy Hub / ONE Core using the upstream [`renogyapi`](https://pypi.org/project/renogyapi/) client (renamed/wrapped from `py_renogy`).
2. **Local Bluetooth Low Energy (BLE)**: monitoring Renogy devices locally via BT-1 and BT-2 Bluetooth modules using Home Assistant's `bluetooth` integration and `bleak`.

```
custom_components/renogy/
├── __init__.py          # Setup, entry migration, RenogyManager (Cloud), BLEUpdateCoordinator (BLE)
├── const.py             # Domain constants, configuration keys, register mappings, and sensor schemas
├── config_flow.py       # ConfigFlow & OptionsFlow supporting both Cloud and BLE device pairing
├── sensor.py            # SensorEntity definitions dynamically registered for Cloud and BLE
├── binary_sensor.py     # BinarySensorEntity definitions (online status, alarms, switches)
├── diagnostics.py       # Config-entry and device diagnostics redacting sensitive API keys & MACs
├── ble_client.py        # Persistent BLE connection manager, queueing, retries, and Modbus polling
├── ble_detector.py      # Device auto-detection and identity discovery via Modbus register queries
├── ble_parsers.py       # Modbus register definitions & parsing logic for controllers, batteries, inverters
├── ble_validator.py     # Spike detection and data validation for incoming controller telemetry
├── ble_utils.py         # Modbus RTU frame building, CRC16 calculation, and byte/temperature conversions
├── strings.json         # English source translation strings for config & options flows
└── translations/        # Translated strings (en.json, etc.)
```

## Environment & toolchain

- **Python**: Target is Python 3.14 (`target-version = "py313"` in `pyproject.toml`, test matrix runs on Python 3.14).
- **Package & tool management**: Managed using [`uv`](https://docs.astral.sh/uv/) and [`tox`](https://tox.wiki/) with `tox-uv`.
- **Linting & formatting**: `ruff` and `codespell` via `pre-commit` / `prek`.
- **Tests**: `pytest` + `pytest-homeassistant-custom-component`.

### Local commands

```bash
# Run tests using uv
uv run --with-requirements requirements_test.txt pytest

# Run tests via tox
uv tool run --with tox-uv --with tox-gh-actions tox

# Run linting and style checks
uv run prek run --all-files
# or
pre-commit run --all-files
```

## Architectural notes

### Dual communication paths

1. **Cloud API (`RenogyManager`)**:
   - Authenticates with Renogy Developer Platform API keys (`CONF_ACCESS_KEY` / `CONF_SECRET_KEY`).
   - Polls devices connected to a physical Renogy ONE / Core Hub.
   - Devices and entities are registered under the cloud entry with device info returned from the cloud API.

2. **Local Bluetooth (`BLEUpdateCoordinator` & `RenogyBLEManager`)**:
   - Connects to BT-1 or BT-2 Bluetooth adapters attached to Renogy devices using Home Assistant's bluetooth manager.
   - Communicates using Modbus RTU protocol over BLE GATT characteristics.
   - Detects device type (Charge Controller, Battery, or Inverter) via Modbus register probing (`ble_detector.py`).
   - Polling reads register blocks sequentially with CRC16 verification (`ble_client.py`).
   - Data passes through spike detection and validation (`ble_validator.py`) before translation to Home Assistant sensor entities.

### Data validation and spike detection

- Implemented in `ble_validator.py` (`DataValidator` and `DataValidatorManager`).
- Renogy charge controllers (notably Rover models) can occasionally send corrupt packets or erroneous spikes over BLE.
- Sensor limits define acceptable ranges and allowable delta changes per poll:
  - `battery_voltage` and `load_voltage` scale with nominal battery system voltage (12V, 24V, 48V).
  - `pv_voltage` is independent of battery nominal voltage, supporting high-voltage solar panel strings (up to 160V DC for MPPT controllers).
- Rejected readings are replaced with the last known good value to maintain sensor stability.

### Home Assistant lifecycle & standards

- Adheres to modern Home Assistant component patterns (`ConfigEntry.runtime_data`).
- Never perform blocking I/O calls on the event loop; all BLE operations and API requests are fully async.
- Handles coordinator state transitions gracefully; sensor properties return appropriate fallbacks (`None` or `0`) when telemetry is absent.
- Sensible redaction of sensitive identifiers (API keys, secrets, MAC addresses) in diagnostics.

## When adding or modifying code

- **Adding new sensor entities**: Add mapping to `BLE_TO_HA_KEY_MAP` and sensor descriptions in `const.py` / `sensor.py`.
- **Modifying BLE parsers or registers**: Update `CONTROLLER_REGISTERS`, `BATTERY_REGISTERS`, or `INVERTER_REGISTERS` in `ble_parsers.py` with corresponding test fixtures in `tests/test_parsers.py`.
- **Validation limits**: Ensure any new numerical sensor limits in `_CONTROLLER_BASE_LIMITS` (`ble_validator.py`) accommodate all supported hardware configurations without rejecting valid data.
- **Always run tests**: Verify changes pass with `pytest tests/` before opening a pull request.
