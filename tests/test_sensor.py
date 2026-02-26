"""Test renogy sensors."""

import logging

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.renogy.const import DOMAIN

from .const import CONFIG_DATA

pytestmark = pytest.mark.asyncio

DEVICE_NAME = "Renogy Core"


async def test_sensors(hass, mock_api, caplog):
    """Test setup_entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 5
        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 40
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1

        assert DOMAIN in hass.config.components

        state = hass.states.get("sensor.renogy_one_core_connection_type")
        assert state
        assert state.state == "Hub"
        assert state.attributes["icon"] == "mdi:hub"
        state = hass.states.get("sensor.inverter_connection_type")
        assert state
        assert state.state == "RS485"
        state = hass.states.get("sensor.inverter_output")
        assert state
        assert state.state == "Normal"
        state = hass.states.get("sensor.rng_ctrl_rvr40_connection_type")
        assert state
        assert state.state == "Bluetooth"
        state = hass.states.get("sensor.rng_ctrl_rvr40_battery_type")
        assert state
        assert state.state == "Lithium"
        state = hass.states.get("sensor.rbt100lfp12sh_g1_connection_type")
        assert state
        assert state.state == "RS485"
        state = hass.states.get("sensor.rbt100lfp12sh_g1_battery_level")
        assert state
        assert state.state == "54.784637"
        assert state.attributes["unit_of_measurement"] == "%"


async def test_sensors_error(hass, mock_api_error, caplog):
    """Test setup_entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 5
        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 40
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1

        assert DOMAIN in hass.config.components

        state = hass.states.get("sensor.renogy_one_core_connection_type")
        assert state
        assert state.state == "Hub"
        assert state.attributes["icon"] == "mdi:hub"
        state = hass.states.get("sensor.inverter_connection_type")
        assert state
        assert state.state == "RS485"
        state = hass.states.get("sensor.inverter_output")
        assert state
        assert state.state == "unknown"
        state = hass.states.get("sensor.rng_ctrl_rvr40_connection_type")
        assert state
        assert state.state == "Bluetooth"
        state = hass.states.get("sensor.rng_ctrl_rvr40_battery_type")
        assert state
        assert state.state == "unknown"
        state = hass.states.get("sensor.rbt100lfp12sh_g1_connection_type")
        assert state
        assert state.state == "RS485"
        state = hass.states.get("sensor.rbt100lfp12sh_g1_battery_level")
        assert state
        assert state.state == "54.784637"
        assert state.attributes["unit_of_measurement"] == "%"


async def test_sensor_coverage(hass, mock_api, caplog):
    """Test sensor coverage for edge cases."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    device_id = "12345678903"

    # Find a sensor entity
    from homeassistant.helpers.entity_component import EntityComponent

    component: EntityComponent = hass.data["sensor"]
    entity_id = "sensor.rbt100lfp12sh_g1_present_voltage"
    entity = component.get_entity(entity_id)
    assert entity is not None, f"entity {entity_id} not found"

    # Trigger structural guards in native_value (lines 118-121)
    original_data = coordinator.data[device_id]["data"]
    original_val = original_data["presentVolts"]
    coordinator.data[device_id]["data"] = None
    assert entity.native_value is None
    coordinator.data[device_id]["data"] = original_data
    coordinator.data[device_id]["data"]["presentVolts"] = None
    assert entity.native_value is None
    coordinator.data[device_id]["data"]["presentVolts"] = []
    assert entity.native_value is None
    coordinator.data[device_id]["data"]["presentVolts"] = original_val
    assert entity.native_unit_of_measurement == "V"
    coordinator.data[device_id]["data"]["presentVolts"] = (13.0,)
    assert entity.native_unit_of_measurement == "V"
    coordinator.data[device_id]["data"]["presentVolts"] = original_val
