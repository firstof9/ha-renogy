"""Test the Mail and Packages diagnostics."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.renogy.const import CONF_ACCESS_KEY, CONF_SECRET_KEY, DOMAIN
from custom_components.renogy.diagnostics import (
    async_get_config_entry_diagnostics,
    async_get_device_diagnostics,
)
from tests.const import CONFIG_DATA, DIAG_RESULTS

DEVICE_NAME = "Renogy Core"


@pytest.mark.asyncio
async def test_config_entry_diagnostics(hass):
    """Test the config entry level diagnostics data dump."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    result = await async_get_config_entry_diagnostics(hass, entry)

    assert isinstance(result, dict)
    assert result["config"]["data"][CONF_SECRET_KEY] == "**REDACTED**"
    assert result["config"]["data"][CONF_ACCESS_KEY] == "**REDACTED**"


@pytest.mark.asyncio
async def test_device_diagnostics(hass, mock_api):
    """Test the device level diagnostics data dump."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await async_get_device_diagnostics(hass, entry, None)

    assert result == DIAG_RESULTS
