"""Test the DataValidator class."""

import pytest

from custom_components.renogy.ble_validator import (
    DataValidator,
    DataValidatorManager,
    get_controller_validation_limits,
)

pytestmark = pytest.mark.asyncio


async def test_get_controller_validation_limits():
    """Test limit scaling for system voltage."""
    limits_12v = get_controller_validation_limits(12)
    assert limits_12v["battery_voltage"] == (0, 20, 5)

    limits_24v = get_controller_validation_limits(24)
    # Scaled by 2
    assert limits_24v["battery_voltage"] == (0, 40, 10)
    # Non-scaled key
    assert limits_24v["battery_current"] == (-100, 100, 50)

    limits_48v = get_controller_validation_limits(48)
    # Scaled by 4
    assert limits_48v["battery_voltage"] == (0, 80, 20)


async def test_data_validator_init():
    """Test scanner initialization."""
    validator = DataValidator("TestDevice", "controller", 12)
    assert validator.device_name == "TestDevice"
    assert validator.device_type == "controller"
    assert validator._limits["battery_voltage"] == (0, 20, 5)

    validator_inverter = DataValidator("Inverter", "inverter")
    assert not validator_inverter._limits  # Should be empty for non-controller


async def test_validate_data_valid():
    """Test validation with valid data."""
    validator = DataValidator("TestDevice", "controller")
    data = {
        "battery_voltage": 13.5,
        "battery_percentage": 80,
    }
    validated, rejections = validator.validate_data(data)
    assert validated == data
    assert not rejections
    assert validator._last_good_values["battery_voltage"] == 13.5


async def test_validate_data_out_of_range():
    """Test validation with out-of-range data."""
    validator = DataValidator("TestDevice", "controller")

    # First set a good value
    validator.validate_data({"battery_voltage": 12.0})

    # Try invalid high
    data = {"battery_voltage": 25.0}  # Max is 20 for 12V
    validated, rejections = validator.validate_data(data)

    # Should use last good value
    assert validated["battery_voltage"] == 12.0
    assert len(rejections) == 1
    assert "above_maximum" in rejections[0]["reason"]

    # Try invalid low
    data_low = {"battery_voltage": -1.0}
    validated, rejections = validator.validate_data(data_low)
    assert validated["battery_voltage"] == 12.0
    assert "below_minimum" in rejections[0]["reason"]


async def test_validate_data_spike():
    """Test validation for spikes."""
    validator = DataValidator("TestDevice", "controller")

    # Initial value
    validator.validate_data({"battery_voltage": 12.0})

    # Spike (max change is 5V)
    data = {"battery_voltage": 18.0}  # Change is 6.0
    validated, rejections = validator.validate_data(data)

    assert validated["battery_voltage"] == 12.0
    assert len(rejections) == 1
    assert "spike_detected" in rejections[0]["reason"]

    # Valid change
    data_valid = {"battery_voltage": 15.0}  # Change is 3.0
    validated, _ = validator.validate_data(data_valid)
    assert validated["battery_voltage"] == 15.0


async def test_validator_logging_and_stats():
    """Test rejection logging and stats."""
    validator = DataValidator("TestDevice", "controller")

    # Generate some rejections
    validator.validate_data({"battery_voltage": 100.0})  # 1
    validator.validate_data({"battery_voltage": 100.0})  # 2

    stats = validator.get_rejection_stats()
    assert stats["total_rejections"] == 2
    # The count should be 2 for the loop but in `rejection_counts_by_sensor` implementation it counts from log.
    # Ah, implementation iterates log list.
    assert stats["rejection_counts_by_sensor"]["battery_voltage"] == 2

    last = validator.get_last_rejection()
    assert last["sensor"] == "battery_voltage"

    validator.clear_rejection_log()
    stats = validator.get_rejection_stats()
    assert stats["total_rejections"] == 0


async def test_manager():
    """Test DataValidatorManager."""
    manager = DataValidatorManager()

    data = {"battery_voltage": 12.0}
    validated, _ = manager.validate_device_data("Dev1", "controller", data)
    assert validated["battery_voltage"] == 12.0

    validator = manager.get_validator("Dev1", "controller")
    assert validator.device_name == "Dev1"

    stats = manager.get_all_rejection_stats()
    assert "Dev1_controller" in stats


# Detailed coverage for ble_validator.py


async def test_validate_no_limits():
    """Test validation when no limits are defined (e.g. inverter)."""
    validator = DataValidator("Inverter", "inverter")
    data = {"some_val": 123}
    validated, rejections = validator.validate_data(data)
    assert validated == data
    assert len(rejections) == 0


async def test_validate_non_numeric():
    """Test validation ignores non-numeric values."""
    validator = DataValidator("Controller", "controller")
    # 'battery_voltage' has limits, but if we pass a string it should be ignored/skipped
    data = {"battery_voltage": "12.0", "other": "string"}
    validated, rejections = validator.validate_data(data)
    assert validated == data
    assert len(rejections) == 0


async def test_log_truncation():
    """Test that rejection log is truncated at max size."""
    validator = DataValidator("Controller", "controller")
    # Max log is 100

    # Generate 105 rejections
    for _i in range(105):
        validator.validate_data({"battery_voltage": 100.0})  # Max is 20

    stats = validator.get_rejection_stats()
    assert stats["total_rejections"] == 100
    assert len(validator._rejection_log) == 100
