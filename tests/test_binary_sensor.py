"""Test renogy binary sensors."""

import logging

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.renogy.const import DOMAIN

from .const import CONFIG_DATA

pytestmark = pytest.mark.asyncio

DEVICE_NAME = "Renogy Core"


async def test_binary_sensors(hass, mock_api, caplog):
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
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1

        assert DOMAIN in hass.config.components

        state = hass.states.get("binary_sensor.renogy_one_core_status")
        assert state
        assert state.state == "on"
        state = hass.states.get("binary_sensor.rbt100lfp12sh_g1_heating_mode")
        assert state
        assert state.state == "off"
        state = hass.states.get("binary_sensor.rng_ctrl_rvr40_status")
        assert state
        assert state.state == "on"


async def test_binary_sensor_unsupported(hass, mock_api, caplog):
    """Test unsupported binary sensor."""
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

    # Find the entity
    from homeassistant.helpers import entity_registry as er

    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "binary_sensor", DOMAIN, f"Heating Mode_{device_id}"
    )
    assert entity_id is not None, f"Entity ID for {device_id} heating mode not found"

    # This is a bit hacky but we need the actual entity object
    from homeassistant.helpers.entity_component import EntityComponent

    component: EntityComponent = hass.data["binary_sensor"]
    entity = component.get_entity(entity_id)
    assert entity is not None, f"Entity with ID {entity_id} not found in component"

    with caplog.at_level(logging.INFO):
        # Remove the key to trigger the unsupported branch in is_on
        if "heatingModeStatus" in coordinator.data[device_id]["data"]:
            del coordinator.data[device_id]["data"]["heatingModeStatus"]

        assert entity.is_on is False
        assert "binary_sensor [heatingModeStatus] not supported." in caplog.text
