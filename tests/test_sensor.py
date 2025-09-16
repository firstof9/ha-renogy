"""Test renogy sensors."""

import logging
from unittest.mock import patch

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
