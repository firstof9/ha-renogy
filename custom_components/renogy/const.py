"""Constants for Renogy."""

from __future__ import annotations

from typing import Final

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntityDescription,
)
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    PERCENTAGE,
    Platform,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.helpers.entity import EntityCategory

# config flow
CONF_SECRET_KEY = "secret_key"
CONF_ACCESS_KEY = "access_key"
CONF_NAME = "name"
DEFAULT_NAME = "Renogy Core"

DOMAIN = "renogy"
COORDINATOR = "coordinator"
VERSION = "1.0.0"
ISSUE_URL = "http://github.com/firstof9/ha-renogy/"
PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]
USER_AGENT = "Home Assistant"
MANAGER = "manager"


BINARY_SENSORS: Final[dict[str, BinarySensorEntityDescription]] = {
    "status": BinarySensorEntityDescription(
        name="Status",
        key="status",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "heatingModeStatus": BinarySensorEntityDescription(
        name="Heating Mode",
        key="heatingModeStatus",
    ),
    "state": BinarySensorEntityDescription(
        name="State",
        key="state",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "alarm": BinarySensorEntityDescription(
        name="Alarm",
        key="alarm",
        device_class=BinarySensorDeviceClass.DOOR,
    ),
}

SENSOR_TYPES: Final[dict[str, SensorEntityDescription]] = {
    "connection": SensorEntityDescription(
        key="connection",
        name="Connection Type",
        icon="mdi:help",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "auxiliaryBatteryTemperature": SensorEntityDescription(
        key="auxiliaryBatteryTemperature",
        name="AUX Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "averageTemperature": SensorEntityDescription(
        key="averageTemperature",
        name="Average Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "presentVolts": SensorEntityDescription(
        key="presentVolts",
        name="Present Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "presentCapacity": SensorEntityDescription(
        key="presentCapacity",
        name="Present Capacity",
        icon="mdi:car-battery",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "maximumCapacity": SensorEntityDescription(
        key="maximumCapacity",
        name="Maximum Capacity",
        icon="mdi:car-battery",
        native_unit_of_measurement="Ah",
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    "presentAmps": SensorEntityDescription(
        key="presentAmps",
        name="Present Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=2,
    ),
    "totalKwhGenerated": SensorEntityDescription(
        key="totalKwhGenerated",
        name="Total Energy Generated",
        native_unit_of_measurement=UnitOfEnergy.WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    "soc": SensorEntityDescription(
        key="soc",
        name="State of Charge",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    "batteryLevel": SensorEntityDescription(
        key="batteryLevel",
        name="Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
    ),
    "loadAmps": SensorEntityDescription(
        key="loadAmps",
        name="Load Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=1,
    ),
    "solarWatts": SensorEntityDescription(
        name="Current Solar Watts",
        key="solarWatts",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "solarChargingVolts": SensorEntityDescription(
        key="solarChargingVolts",
        name="Solar Charging Voltage",
        icon="mdi:solar-power",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "loadWatts": SensorEntityDescription(
        name="Load Watts",
        key="loadWatts",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=1,
    ),
    "auxiliaryBatteryChargingVolts": SensorEntityDescription(
        key="auxiliaryBatteryChargingVolts",
        name="Aux Battery Charging Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "solarChargingAmps": SensorEntityDescription(
        key="solarChargingAmps",
        name="Solar Charging Ampers",
        icon="mdi:solar-power",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=1,
    ),
    "systemVolts": SensorEntityDescription(
        key="systemVolts",
        name="System Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=0,
    ),
    "auxiliaryBatteryChargingWatts": SensorEntityDescription(
        name="Aux Battery Charging Watts",
        key="auxiliaryBatteryChargingWatts",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
        suggested_display_precision=1,
    ),
    "gridChargeAmps": SensorEntityDescription(
        key="gridChargeAmps",
        name="Grid Charging Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=1,
    ),
    # Inverter Sensors (some overlap)
    "loadActiveWatts": SensorEntityDescription(
        name="Load Active Watts",
        key="loadActiveWatts",
        icon="mdi:flash",
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.POWER,
    ),
    "temperature": SensorEntityDescription(
        key="temperature",
        name="Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "batteryVolts": SensorEntityDescription(
        key="batteryVolts",
        name="Battery Voltage",
        icon="mdi:car-battery",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=2,
    ),
    "acOutputHz": SensorEntityDescription(
        key="acOutputHz",
        name="Output Frequency",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    "outputVolts": SensorEntityDescription(
        key="outputVolts",
        name="Output Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=0,
    ),
    "outputAmps": SensorEntityDescription(
        key="outputAmps",
        name="Output Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.MILLIAMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=1,
    ),
    "ueiVolts": SensorEntityDescription(
        key="ueiVolts",
        name="UEI Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=0,
    ),
    "chargePriority": SensorEntityDescription(
        key="chargePriority",
        name="Charge Priority",
        icon="mdi:priority-high",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "output": SensorEntityDescription(
        key="output",
        name="Output",
        icon="mdi:directions-fork",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    # End Inverter
    # Panels
    "batteryType": SensorEntityDescription(
        key="batteryType",
        name="Battery Type",
        icon="mdi:car-battery",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    "batteryTemperature": SensorEntityDescription(
        key="batteryTemperature",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.TEMPERATURE,
    ),
    "solarVolts": SensorEntityDescription(
        key="solarVolts",
        name="Solar Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "batteryChargingVolts": SensorEntityDescription(
        key="batteryChargingVolts",
        name="Battery Charging Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "loadVolts": SensorEntityDescription(
        key="loadVolts",
        name="Load Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "solarAmps": SensorEntityDescription(
        key="solarAmps",
        name="Solar Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=2,
    ),
    "batteryChargingAmps": SensorEntityDescription(
        key="batteryChargingAmps",
        name="Battery Charging Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=2,
    ),
    "totalEnergyProduced": SensorEntityDescription(
        key="totalEnergyProduced",
        name="Total Energy Produced",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        suggested_display_precision=2,
    ),
    "humidity": SensorEntityDescription(
        key="humidity",
        name="Humidity",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
    ),
    "lowbattery": SensorEntityDescription(
        key="lowbattery",
        name="Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        suggested_display_precision=1,
    ),
    "current": SensorEntityDescription(
        key="current",
        name="Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=2,
    ),
    "startBatteryVolts": SensorEntityDescription(
        key="startBatteryVolts",
        name="Start Battery Voltage",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLTAGE,
        suggested_display_precision=1,
    ),
    "startBatteryAmps": SensorEntityDescription(
        key="startBatteryAmps",
        name="Start Battery Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=1,
    ),
    "auxiliaryBatteryChargingAmps": SensorEntityDescription(
        key="auxiliaryBatteryChargingAmps",
        name="Aux Battery Charging Ampers",
        icon="mdi:sine-wave",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.CURRENT,
        suggested_display_precision=1,
    ),    
}
