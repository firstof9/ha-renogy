"""Test renogy config flow."""

import logging
from unittest.mock import patch

import pytest
from homeassistant import config_entries, setup
from homeassistant.components.binary_sensor import DOMAIN as BINARY_SENSOR_DOMAIN
from homeassistant.data_entry_flow import FlowResult, FlowResultType
from homeassistant.components.sensor import DOMAIN as SENSOR_DOMAIN
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.renogy.const import (
    DOMAIN,
    CONF_ACCESS_KEY,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_MAC_ADDRESS,
    CONF_NAME,
    CONF_SECRET_KEY,
    CONNECTION_TYPE_BLE,
    CONNECTION_TYPE_CLOUD,
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
    from unittest.mock import MagicMock

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
    from unittest.mock import MagicMock

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

