"""Test renogy setup process."""

import logging
from unittest.mock import patch

import pytest
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.renogy.const import DOMAIN

from .const import CONFIG_DATA

pytestmark = pytest.mark.asyncio

DEVICE_NAME = "Renogy Core"


async def test_setup_entry(hass, mock_api, device_registry: dr.DeviceRegistry, caplog):
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


async def test_setup_and_unload_entry(hass, mock_api, caplog):
    """Test unloading entities."""
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

        assert await hass.config_entries.async_unload(entries[0].entry_id)
        await hass.async_block_till_done()
        assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 5
        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 40
        assert len(hass.states.async_entity_ids(DOMAIN)) == 0

        assert await hass.config_entries.async_remove(entries[0].entry_id)
        await hass.async_block_till_done()
        assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 0
        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 0


async def test_duplicate_serials(
    hass, mock_api, mock_coordinator, device_registry: dr.DeviceRegistry, caplog
):
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

        assert len(hass.states.async_entity_ids(BINARY_SENSOR_DOMAIN)) == 6
        assert len(hass.states.async_entity_ids(SENSOR_DOMAIN)) == 19
        entries = hass.config_entries.async_entries(DOMAIN)
        assert len(entries) == 1
