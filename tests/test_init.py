"""Test renogy setup process."""

import logging
from unittest.mock import MagicMock, patch

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


async def test_async_remove_config_entry_device_without_runtime_data(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device when config_entry lacks runtime_data."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Get a device from the registry
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        assert len(devices) > 0
        device = devices[0]

        # Create a config entry without runtime_data attribute
        minimal_entry = MockConfigEntry(
            domain=DOMAIN,
            title="Minimal Entry",
            data=CONFIG_DATA,
        )

        # Verify the entry doesn't have runtime_data
        assert not hasattr(minimal_entry, "runtime_data")

        # Test that the function returns True when runtime_data is missing
        result = await async_remove_config_entry_device(hass, minimal_entry, device)
        assert result is True


async def test_async_remove_config_entry_device_with_runtime_data_device_exists(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device when device exists in runtime_data."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Get a device from the registry
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        assert len(devices) > 0
        device = devices[0]

        # Create a mock runtime_data with get_device method
        mock_runtime_data = MagicMock()
        mock_runtime_data.get_device = MagicMock(return_value={"some": "device_data"})

        # Add runtime_data to entry
        entry.runtime_data = mock_runtime_data

        # Test that the function returns False when device exists
        result = await async_remove_config_entry_device(hass, entry, device)
        assert result is False

        # Verify get_device was called with the correct identifier
        identifiers = list(device.identifiers)
        domain_identifiers = [id for id in identifiers if id[0] == DOMAIN]
        if domain_identifiers:
            mock_runtime_data.get_device.assert_called()


async def test_async_remove_config_entry_device_with_runtime_data_device_not_exists(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device when device does not exist in runtime_data."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Get a device from the registry
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        assert len(devices) > 0
        device = devices[0]

        # Create a mock runtime_data with get_device returning None/False
        mock_runtime_data = MagicMock()
        mock_runtime_data.get_device = MagicMock(return_value=None)

        # Add runtime_data to entry
        entry.runtime_data = mock_runtime_data

        # Test that the function returns True when device doesn't exist
        result = await async_remove_config_entry_device(hass, entry, device)
        assert result is True


async def test_async_remove_config_entry_device_with_no_domain_identifiers(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device with device having no domain identifiers."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Create a device with different domain identifiers
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={("other_domain", "test_device")},
            name="Test Device",
        )

        # Create a mock runtime_data
        mock_runtime_data = MagicMock()
        mock_runtime_data.get_device = MagicMock(return_value={"some": "device_data"})

        # Add runtime_data to entry
        entry.runtime_data = mock_runtime_data

        # Test that the function returns True when no domain identifiers match
        result = await async_remove_config_entry_device(hass, entry, device)
        assert result is True

        # Verify get_device was not called since no matching identifiers
        mock_runtime_data.get_device.assert_not_called()


async def test_async_remove_config_entry_device_with_multiple_identifiers(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device with device having multiple identifiers."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Create a device with multiple identifiers, some from our domain
        device = device_registry.async_get_or_create(
            config_entry_id=entry.entry_id,
            identifiers={
                (DOMAIN, "device_1"),
                (DOMAIN, "device_2"),
                ("other_domain", "other_device"),
            },
            name="Multi-ID Device",
        )

        # Create a mock runtime_data where one device exists but not the other
        mock_runtime_data = MagicMock()
        mock_runtime_data.get_device = MagicMock(
            side_effect=lambda x: {"data": "exists"} if x == "device_1" else None
        )

        # Add runtime_data to entry
        entry.runtime_data = mock_runtime_data

        # Test that the function returns False when at least one device exists
        result = await async_remove_config_entry_device(hass, entry, device)
        assert result is False


async def test_async_remove_config_entry_device_edge_case_empty_identifiers(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device with device having empty identifiers."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Create a mock device with empty identifiers set
        mock_device = MagicMock(spec=dr.DeviceEntry)
        mock_device.identifiers = set()

        # Create a mock runtime_data
        mock_runtime_data = MagicMock()
        mock_runtime_data.get_device = MagicMock(return_value=None)

        # Add runtime_data to entry
        entry.runtime_data = mock_runtime_data

        # Test that the function returns True with empty identifiers
        result = await async_remove_config_entry_device(hass, entry, mock_device)
        assert result is True

        # Verify get_device was not called
        mock_runtime_data.get_device.assert_not_called()


async def test_async_remove_config_entry_device_runtime_data_get_device_exception(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device when get_device raises an exception."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Get a device from the registry
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        assert len(devices) > 0
        device = devices[0]

        # Create a mock runtime_data that raises an exception
        mock_runtime_data = MagicMock()
        mock_runtime_data.get_device = MagicMock(
            side_effect=Exception("Test exception")
        )

        # Add runtime_data to entry
        entry.runtime_data = mock_runtime_data

        # Test that the function handles the exception gracefully
        # The any() should return False if all get_device calls raise exceptions
        with pytest.raises(Exception):
            await async_remove_config_entry_device(hass, entry, device)


async def test_async_remove_config_entry_device_integration(
    hass, mock_api, device_registry: dr.DeviceRegistry, caplog
):
    """Test async_remove_config_entry_device in full integration scenario."""
    from custom_components.renogy import async_remove_config_entry_device

    entry = MockConfigEntry(
        domain=DOMAIN,
        title=DEVICE_NAME,
        data=CONFIG_DATA,
    )

    with caplog.at_level(logging.DEBUG):
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        # Get devices from the registry
        devices = dr.async_entries_for_config_entry(device_registry, entry.entry_id)
        initial_device_count = len(devices)
        assert initial_device_count > 0

        # Test with actual config entry (should not have runtime_data in this context)
        for device in devices:
            result = await async_remove_config_entry_device(hass, entry, device)
            # Should return True because entry doesn't have runtime_data
            assert result is True
"""Test detailed coverage for __init__.py."""
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from homeassistant import config_entries
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import UpdateFailed
from custom_components.renogy.const import (
    DOMAIN,
    CONF_CONNECTION_TYPE,
    CONF_MAC_ADDRESS,
    CONF_NAME,
    CONF_SECRET_KEY,
    CONF_ACCESS_KEY,
)
from custom_components.renogy import RenogyUpdateCoordinator
from pytest_homeassistant_custom_component.common import MockConfigEntry

pytestmark = pytest.mark.asyncio

async def test_setup_ble_success(hass):
    """Test successful BLE setup."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_CONNECTION_TYPE: "ble",
            CONF_NAME: "BLE Device",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.renogy.ble_client.BLEDeviceManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        mock_manager.poll_all = AsyncMock(return_value={
            "ble_AA:BB:CC:DD:EE:FF": {
                "__device": "Test Device",
                "__device_type": "controller",
                "__mac_address": "AA:BB:CC:DD:EE:FF",
                "battery_voltage": 12.0
            }
        })
        mock_manager.disconnect_all = AsyncMock()
        
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == config_entries.ConfigEntryState.LOADED
        assert hass.data[DOMAIN][entry.entry_id] is not None
        
        await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == config_entries.ConfigEntryState.NOT_LOADED
        mock_manager.disconnect_all.assert_called()


async def test_setup_ble_exception_in_refresh(hass):
    """Test BLE setup handles exception during async_refresh (lines 169-173)."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_CONNECTION_TYPE: "ble",
            CONF_NAME: "BLE Device",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.renogy.ble_client.BLEDeviceManager") as mock_manager_cls, \
         patch("custom_components.renogy.BLEUpdateCoordinator.async_refresh", side_effect=Exception("Major Fail")):
        
        mock_manager = mock_manager_cls.return_value
        mock_manager.disconnect_all = AsyncMock()
        
        # async_setup catches Exception -> ConfigEntryNotReady -> SETUP_RETRY
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == config_entries.ConfigEntryState.SETUP_RETRY
        mock_manager.disconnect_all.assert_called()


async def test_setup_ble_refresh_failed(hass):
    """Test BLE setup fails when refresh is unsuccessful (lines 176-178)."""
    # This happens if coordinator returns UpdateFailed, leading to last_update_success=False
    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="AA:BB:CC:DD:EE:FF",
        data={
            CONF_CONNECTION_TYPE: "ble",
            CONF_NAME: "BLE Device",
            CONF_MAC_ADDRESS: "AA:BB:CC:DD:EE:FF",
        },
    )
    entry.add_to_hass(hass)

    with patch("custom_components.renogy.ble_client.BLEDeviceManager") as mock_manager_cls:
        mock_manager = mock_manager_cls.return_value
        # return empty to trigger UpdateFailed in _async_update_data
        mock_manager.poll_all = AsyncMock(return_value={})
        mock_manager.disconnect_all = AsyncMock()
        
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        
        assert entry.state == config_entries.ConfigEntryState.SETUP_RETRY
        mock_manager.disconnect_all.assert_called()


async def test_ble_coordinator_logic_fail(hass):
    """Test BLE Coordinator specific failure logic (lines 318, 324)."""
    from custom_components.renogy import BLEUpdateCoordinator
    
    config = MockConfigEntry(data={CONF_NAME: "Test", CONF_MAC_ADDRESS: "AA..."})
    manager = MagicMock()
    coordinator = BLEUpdateCoordinator(hass, 30, config, manager)
    
    # 1. poll_all raises Exception -> UpdateFailed (lines 318-319)
    manager.poll_all = AsyncMock(side_effect=Exception("Poll Error"))
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
        
    # 2. poll_all returns empty -> UpdateFailed (line 324)
    manager.poll_all = AsyncMock(return_value={})
    coordinator._data = {}
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_ble_coordinator_logic_rejection(hass):
    """Test BLE Coordinator rejection logic (line 338)."""
    from custom_components.renogy import BLEUpdateCoordinator
    
    config = MockConfigEntry(data={CONF_NAME: "Test", CONF_MAC_ADDRESS: "AA..."})
    manager = MagicMock()
    coordinator = BLEUpdateCoordinator(hass, 30, config, manager)
    
    # We need to trigger validator to return rejections
    with patch("custom_components.renogy.ble_validator.DataValidatorManager.validate_device_data") as mock_validate:
        mock_validate.return_value = ({"valid": "data"}, ["rejection1"])
        
        manager.poll_all = AsyncMock(return_value={
            "dev1": {
                "__device": "dev1",
                "__device_type": "controller",
                "__mac_address": "AA...",
                "val": 100
            }
        })
        
        data = await coordinator._async_update_data()
        assert "ble_AA..." in data


async def test_cloud_runtime_error(hass):
    """Test cloud setup with RuntimeError (line 278)."""
    entry = MockConfigEntry(data={
        CONF_CONNECTION_TYPE: "cloud",
        CONF_NAME: "Cloud",
        CONF_SECRET_KEY: "s",
        CONF_ACCESS_KEY: "a"
    })
    entry.add_to_hass(hass)
    
    manager = MagicMock()
    manager.get_devices = AsyncMock(side_effect=[RuntimeError("Oops"), {}])
    
    coordinator = RenogyUpdateCoordinator(hass, 30, entry, manager)
    await coordinator.update_sensors()


async def test_ble_coordinator_logic_success_existing_data(hass):
    """Test BLE Coordinator returns existing data if poll empty (line 323)."""
    from custom_components.renogy import BLEUpdateCoordinator
    
    config = MockConfigEntry(data={CONF_NAME: "Test", CONF_MAC_ADDRESS: "AA..."})
    manager = MagicMock()
    
    coordinator = BLEUpdateCoordinator(hass, 30, config, manager)
    coordinator._data = {"some": "data"}
    manager.poll_all = AsyncMock(return_value={})
    
    data = await coordinator._async_update_data()
    assert data == {"some": "data"}
