import logging
from unittest.mock import MagicMock, patch

import pytest
from homeassistant import config_entries, setup
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from renogyapi.exceptions import UrlNotFound

from custom_components.renogy.config_flow import RenogyFlowHandler
from custom_components.renogy.const import (
    CONF_ACCESS_KEY,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_MAC_ADDRESS,
    CONF_NAME,
    CONF_SECRET_KEY,
    CONNECTION_TYPE_BLE,
    CONNECTION_TYPE_CLOUD,
    DOMAIN,
)

from .const import CONFIG_DATA

pytestmark = pytest.mark.asyncio

_LOGGER = logging.getLogger(__name__)
DEVICE_NAME = "Renogy Core"


@pytest.mark.parametrize(
    "input,step_id,title,data",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "cloud",
            DEVICE_NAME,
            {
                "connection_type": "cloud",
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
        ),
    ],
)
async def test_form_user(
    input,
    step_id,
    title,
    data,
    hass,
    mock_api,
):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Step 1: Select connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    # Step 2: Enter cloud credentials
    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], input
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == title
        assert result["data"] == data

        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize(
    "input,step_id,title,data",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "reconfigure",
            DEVICE_NAME,
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
        ),
    ],
)
async def test_form_reconfigure(
    input,
    step_id,
    title,
    data,
    hass,
    mock_api,
    caplog,
):
    """Test we get the form."""
    with caplog.at_level(logging.DEBUG):
        await setup.async_setup_component(hass, "persistent_notification", {})
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=DEVICE_NAME,
            data=CONFIG_DATA,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        reconfigure_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert reconfigure_result["type"] is FlowResultType.FORM
        assert reconfigure_result["step_id"] == step_id

        result = await hass.config_entries.flow.async_configure(
            reconfigure_result["flow_id"], input
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"
        await hass.async_block_till_done()

        _LOGGER.debug("Entries: %s", len(hass.config_entries.async_entries(DOMAIN)))
        entry = hass.config_entries.async_entries(DOMAIN)[0]
        _LOGGER.debug("Entry: %s", entry.data)
        assert entry.data.copy() == data


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "cloud",
        ),
    ],
)
async def test_form_user_no_devices(
    input,
    step_id,
    hass,
    mock_api_no_devices,
):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select cloud connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_ACCESS_KEY: "no_devices"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "reconfigure",
        ),
    ],
)
async def test_form_reconfigure_no_devices(
    input,
    step_id,
    hass,
    mock_api_no_devices,
    caplog,
):
    """Test we get the form."""
    with caplog.at_level(logging.DEBUG):
        await setup.async_setup_component(hass, "persistent_notification", {})
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=DEVICE_NAME,
            data=CONFIG_DATA,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        reconfigure_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert reconfigure_result["type"] is FlowResultType.FORM
        assert reconfigure_result["step_id"] == step_id

        result = await hass.config_entries.flow.async_configure(
            reconfigure_result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_ACCESS_KEY: "no_devices"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "cloud",
        ),
    ],
)
async def test_form_config_bad_auth(
    input,
    step_id,
    hass,
    mock_api_not_auth,
    caplog,
):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select cloud connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {
            CONF_ACCESS_KEY: "invalid_key",
            CONF_SECRET_KEY: "invalid_key",
        }


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "cloud",
        ),
    ],
)
async def test_form_config_rate_limit(
    input,
    step_id,
    hass,
    mock_api_rate_limit,
    caplog,
):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select cloud connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], input
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_NAME: "rate_limit"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "cloud",
        ),
    ],
)
async def test_form_config_api_error(
    input,
    step_id,
    hass,
    mock_api_not_found,
    caplog,
):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select cloud connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], input
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_NAME: "api_error"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "reconfigure",
        ),
    ],
)
async def test_form_reconfigure_bad_auth(
    input,
    step_id,
    hass,
    mock_api_not_auth,
    caplog,
):
    """Test we get the form."""
    with caplog.at_level(logging.DEBUG):
        await setup.async_setup_component(hass, "persistent_notification", {})
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=DEVICE_NAME,
            data=CONFIG_DATA,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        reconfigure_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert reconfigure_result["type"] is FlowResultType.FORM
        assert reconfigure_result["step_id"] == step_id

        result = await hass.config_entries.flow.async_configure(
            reconfigure_result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {
            CONF_ACCESS_KEY: "invalid_key",
            CONF_SECRET_KEY: "invalid_key",
        }


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "reconfigure",
        ),
    ],
)
async def test_form_reconfigure_rate_limit(
    input,
    step_id,
    hass,
    mock_api_rate_limit,
    caplog,
):
    """Test we get the form."""
    with caplog.at_level(logging.DEBUG):
        await setup.async_setup_component(hass, "persistent_notification", {})
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=DEVICE_NAME,
            data=CONFIG_DATA,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        reconfigure_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert reconfigure_result["type"] is FlowResultType.FORM
        assert reconfigure_result["step_id"] == step_id

        result = await hass.config_entries.flow.async_configure(
            reconfigure_result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_NAME: "rate_limit"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "reconfigure",
        ),
    ],
)
async def test_form_reconfigure_api_error(
    input,
    step_id,
    hass,
    mock_api_not_found,
    caplog,
):
    """Test we get the form."""
    with caplog.at_level(logging.DEBUG):
        await setup.async_setup_component(hass, "persistent_notification", {})
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=DEVICE_NAME,
            data=CONFIG_DATA,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        reconfigure_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert reconfigure_result["type"] is FlowResultType.FORM
        assert reconfigure_result["step_id"] == step_id

        result = await hass.config_entries.flow.async_configure(
            reconfigure_result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_NAME: "api_error"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "cloud",
        ),
    ],
)
async def test_form_config_api_error(
    input,
    step_id,
    hass,
    mock_api,
    caplog,
):
    """Test we get the form."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Select cloud connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == step_id

    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry, patch(
        "custom_components.renogy.config_flow.api.get_devices"
    ) as mock_api_error:
        mock_api_error.side_effect = Exception("General Error")
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], input
        )
        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_NAME: "general"}


@pytest.mark.parametrize(
    "input,step_id",
    [
        (
            {
                "name": DEVICE_NAME,
                "secret_key": "SuperSecretKey",
                "access_key": "SuperSpecialAccessKey",
            },
            "reconfigure",
        ),
    ],
)
async def test_form_reconfigure_api_error(
    input,
    step_id,
    hass,
    mock_api_not_found,
    caplog,
):
    """Test we get the form."""
    with caplog.at_level(logging.DEBUG), patch(
        "custom_components.renogy.config_flow.api.get_devices"
    ) as mock_api_error:
        mock_api_error.side_effect = Exception("General Error")
        await setup.async_setup_component(hass, "persistent_notification", {})
        entry = MockConfigEntry(
            domain=DOMAIN,
            title=DEVICE_NAME,
            data=CONFIG_DATA,
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        reconfigure_result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={
                "source": config_entries.SOURCE_RECONFIGURE,
                "entry_id": entry.entry_id,
            },
        )
        assert reconfigure_result["type"] is FlowResultType.FORM
        assert reconfigure_result["step_id"] == step_id

        result = await hass.config_entries.flow.async_configure(
            reconfigure_result["flow_id"], input
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == step_id
        assert result["errors"] == {CONF_NAME: "general"}


# ==========================================================================
# BLE config flow tests
# ==========================================================================


async def test_form_ble(hass):
    """Test BLE config flow creates entry."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"

    # Step 1: Select BLE connection type
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "ble"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "ble"

    # Step 2: Enter BLE config
    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "My Solar Controller",
                "mac_address": "AA:BB:CC:DD:EE:FF",
                "device_type": "controller",
                "device_id": 255,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "My Solar Controller"
        assert result["data"] == {
            "connection_type": "ble",
            "name": "My Solar Controller",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "device_type": "controller",
            "device_id": 255,
        }

        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_form_bluetooth_discovery(hass):
    """Test Bluetooth auto-discovery creates entry."""
    await setup.async_setup_component(hass, "persistent_notification", {})

    # Simulate a BluetoothServiceInfoBleak discovery
    discovery_info = MagicMock()
    discovery_info.name = "BT-TH-AABBCCDD"
    discovery_info.address = "AA:BB:CC:DD:EE:FF"
    discovery_info.rssi = -60
    discovery_info.manufacturer_data = {}
    discovery_info.service_data = {}
    discovery_info.service_uuids = []
    discovery_info.source = "local"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "bluetooth_confirm"

    with patch(
        "custom_components.renogy.async_setup_entry",
        return_value=True,
    ) as mock_setup_entry:
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                "name": "BT-TH-AABBCCDD",
                "device_type": "controller",
                "device_id": 255,
            },
        )

        assert result["type"] == FlowResultType.CREATE_ENTRY
        assert result["title"] == "BT-TH-AABBCCDD"
        assert result["data"] == {
            "connection_type": "ble",
            "name": "BT-TH-AABBCCDD",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "device_type": "controller",
            "device_id": 255,
        }

        await hass.async_block_till_done()
        assert len(mock_setup_entry.mock_calls) == 1


async def test_bluetooth_discovery_already_configured(hass):
    """Test Bluetooth discovery aborts when device is already configured."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="BT-TH-AABBCCDD",
        data={
            "connection_type": "ble",
            "name": "BT-TH-AABBCCDD",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "device_type": "controller",
            "device_id": 255,
        },
        unique_id="AA:BB:CC:DD:EE:FF",
    )
    entry.add_to_hass(hass)

    discovery_info = MagicMock()
    discovery_info.name = "BT-TH-AABBCCDD"
    discovery_info.address = "AA:BB:CC:DD:EE:FF"
    discovery_info.rssi = -60
    discovery_info.manufacturer_data = {}
    discovery_info.service_data = {}
    discovery_info.service_uuids = []
    discovery_info.source = "local"

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_BLUETOOTH},
        data=discovery_info,
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "already_configured"


# Extended BLE config flow tests


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


# Detailed coverage for config_flow.py


async def test_bluetooth_confirm_no_device(hass):
    """Test bluetooth confirm aborts if no device discovered."""
    flow = RenogyFlowHandler()
    flow.hass = hass
    # Direct call without discovery
    result = await flow.async_step_bluetooth_confirm(user_input={})
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "discovery_device_missing"

    # Call with user_input=None
    result = await flow.async_step_bluetooth_confirm(user_input=None)
    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "discovery_device_missing"


async def test_cloud_url_not_found(hass):
    """Test UrlNotFound in cloud setup."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "cloud"}
    )

    with patch("renogyapi.Renogy.get_devices", side_effect=UrlNotFound):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_NAME: "Cloud Device",
                CONF_SECRET_KEY: "secret",
                CONF_ACCESS_KEY: "access",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_NAME] == "api_error"


async def test_ble_invalid_hex_mac(hass):
    """Test BLE setup with invalid HEX in MAC."""
    await setup.async_setup_component(hass, "persistent_notification", {})
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"connection_type": "ble"}
    )

    # Valid length, valid colons, but 'ZZ' is not hex
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "BLE Device",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:ZZ",
            CONF_DEVICE_TYPE: "controller",
            CONF_DEVICE_ID: 255,
        },
    )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_MAC_ADDRESS] == "invalid_mac"


async def test_reconfigure_entry_missing(hass):
    """Test reconfigure aborts if entry missing."""
    # We can fake this by calling async_step_reconfigure on a fresh flow instance
    # that hasn't been initialized with context properly via the manager,
    # or just mocking _get_reconfigure_entry

    flow = RenogyFlowHandler()
    flow.hass = hass
    # Mock _get_reconfigure_entry to return None
    with patch.object(flow, "_get_reconfigure_entry", return_value=None):
        result = await flow.async_step_reconfigure()

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_entry_missing"


async def test_reconfigure_ble_success(hass):
    """Test reconfiguring BLE entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_CONNECTION_TYPE: "ble",
            CONF_NAME: "Old Name",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )
    assert result["type"] == FlowResultType.FORM

    new_data = {
        CONF_NAME: "New Name",
        CONF_MAC_ADDRESS: "11:22:33:44:55:66",
        CONF_DEVICE_TYPE: "battery",
        CONF_DEVICE_ID: 1,
    }

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=new_data
    )

    assert result["type"] == FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"

    assert entry.data[CONF_NAME] == "New Name"
    assert entry.data[CONF_MAC_ADDRESS] == "11:22:33:44:55:66"


async def test_reconfigure_ble_invalid_mac(hass):
    """Test reconfigure BLE with invalid MAC."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_CONNECTION_TYPE: "ble",
            CONF_NAME: "BLE",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    # 1. Bad length/format
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_MAC_ADDRESS: "INVALID"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_MAC_ADDRESS] == "invalid_mac"

    # 2. Bad Hex
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:ZZ"}
    )
    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_MAC_ADDRESS] == "invalid_mac"


async def test_reconfigure_cloud_url_not_found(hass):
    """Test reconfigure Cloud with UrlNotFound."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_CONNECTION_TYPE: "cloud",
            CONF_NAME: "Cloud",
            CONF_SECRET_KEY: "old",
            CONF_ACCESS_KEY: "old",
        },
    )
    entry.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={
            "source": config_entries.SOURCE_RECONFIGURE,
            "entry_id": entry.entry_id,
        },
    )

    with patch("renogyapi.Renogy.get_devices", side_effect=UrlNotFound):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_SECRET_KEY: "new",
                CONF_ACCESS_KEY: "new",
            },
        )

    assert result["type"] == FlowResultType.FORM
    assert result["errors"][CONF_NAME] == "api_error"
