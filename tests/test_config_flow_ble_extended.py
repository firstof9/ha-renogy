"""Test extended BLE config flow."""

from unittest.mock import patch

import pytest
from homeassistant import config_entries, setup
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.renogy.const import (
    DOMAIN,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_MAC_ADDRESS,
)

pytestmark = pytest.mark.asyncio


async def test_form_ble_invalid_mac(hass):
    """Test BLE config flow with invalid MAC."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "ble"}
    )

    # Step 2: Invalid MAC
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "My Solar Controller",
            "mac_address": "INVALID",
            "device_type": "controller",
            "device_id": 255,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"] == {CONF_MAC_ADDRESS: "invalid_mac"}


async def test_form_ble_duplicate_mac(hass):
    """Test BLE config flow with duplicate MAC."""
    # Create existing entry
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Existing Device",
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_CONNECTION_TYPE: "ble",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
        },
    )
    entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    # Step 1
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "ble"}
    )

    # Step 2: Duplicate MAC
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "New Device",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "device_type": "controller",
            "device_id": 255,
        },
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"
