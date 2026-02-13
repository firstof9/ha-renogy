"""Test DeviceConfig.get_device_type_enum."""

import pytest
from custom_components.renogy.ble_client import DeviceConfig, DeviceType


def test_get_device_type_enum_valid():
    """Test valid device types."""
    assert (
        DeviceConfig(
            name="test", mac_address="AA:BB:CC:DD:EE:FF", device_type="controller"
        ).get_device_type_enum()
        == DeviceType.CONTROLLER
    )
    assert (
        DeviceConfig(
            name="test", mac_address="AA:BB:CC:DD:EE:FF", device_type="battery"
        ).get_device_type_enum()
        == DeviceType.BATTERY
    )
    assert (
        DeviceConfig(
            name="test", mac_address="AA:BB:CC:DD:EE:FF", device_type="inverter"
        ).get_device_type_enum()
        == DeviceType.INVERTER
    )

    # Test case insensitivity
    assert (
        DeviceConfig(
            name="test", mac_address="AA:BB:CC:DD:EE:FF", device_type="ConTroLLer"
        ).get_device_type_enum()
        == DeviceType.CONTROLLER
    )


def test_get_device_type_enum_invalid():
    """Test invalid device types raise ValueError."""
    config = DeviceConfig(
        name="test", mac_address="AA:BB:CC:DD:EE:FF", device_type="unknown_device"
    )
    with pytest.raises(ValueError) as excinfo:
        config.get_device_type_enum()
    assert "Invalid device type 'unknown_device'" in str(excinfo.value)
    assert "Must be one of: controller, battery, inverter" in str(excinfo.value)
