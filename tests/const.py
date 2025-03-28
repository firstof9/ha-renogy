"""Renogy tests consts."""

CONFIG_DATA = {
    "name": "Renogy Core",
    "secret_key": "fakeRandomSecretKey",
    "access_key": "fakeRandomAccessKey",
}

DIAG_RESULTS = {
    "1234567890": {
        "deviceId": "1234567890",
        "name": "Renogy ONE Core",
        "mac": "DE:AD:BE:EF:FE:ED",
        "firmware": "V1.1.157",
        "status": "online",
        "connection": "Hub",
        "serial": "TOTALLYFAKESN",
        "model": "RSHGWSN-W02W-G1",
        "data": {},
    },
    "12345678901": {
        "deviceId": "12345678901",
        "parent": "1234567890",
        "name": "Inverter",
        "mac": "32",
        "firmware": "0100.0102.0202",
        "status": "online",
        "connection": "RS485",
        "serial": "",
        "model": "RINVTPGH110111S",
        "data": {
            "auxiliaryBatteryTemperature": (None, "°C"),
            "acOutputHz": (60.0, "Hz"),
            "ueiVolts": (None, "V"),
            "outputVolts": (114.099998, "V"),
            "loadAmps": (None, "A"),
            "solarWatts": (None, "W"),
            "chargePriority": (None, ""),
            "output": (1, ""),
            "ueiAmps": (None, "mA"),
            "loadWattsMode": (None, ""),
            "loadActiveWatts": (42, "W"),
            "solarChargingVolts": (None, "V"),
            "temperature": (22.0, "°C"),
            "loadWatts": (None, "W"),
            "outputAmps": (370.0, "A"),
            "sku": "RINVTPGH110111S",
            "solarChargingAmps": (None, "A"),
            "batteryType": (None, ""),
            "batteryVolts": (12.6, "V"),
        },
    },
    "12345678902": {
        "deviceId": "12345678902",
        "parent": "1234567890",
        "name": "RNG-CTRL-RVR40",
        "mac": "F0:F8:F2:5D:5D:8716",
        "firmware": "",
        "status": "online",
        "connection": "Bluetooth",
        "serial": "",
        "model": "RNG-CTRL-RVR40",
        "data": {
            "auxiliaryBatteryTemperature": (2.0, "°C"),
            "totalKwhGenerated": (449358.03125, "KWh"),
            "soc": (100, "%"),
            "loadAmps": (0.0, "A"),
            "solarWatts": (0.0, "W"),
            "solarChargingVolts": (15.3, "V"),
            "auxiliaryBatteryChargingWatts": (None, "W"),
            "loadWatts": (0, "W"),
            "auxiliaryBatteryChargingVolts": (14.4, "V"),
            "sku": "RNG-CTRL-RVR40",
            "solarChargingAmps": (0.0, "A"),
            "systemVolts": (12, ""),
            "loadVolts": (0.0, "W"),
            "gridChargeAmps": (0.0, "mA"),
            "batteryType": (4, ""),
            "status": (None, ""),
        },
    },
    "12345678903": {
        "deviceId": "12345678903",
        "parent": "1234567890",
        "name": "RBT100LFP12SH-G1",
        "mac": "48",
        "firmware": "",
        "status": "online",
        "connection": "RS485",
        "serial": "",
        "model": "RBT100LFP12SH-G1",
        "data": {
            "averageTemperature": (-3, "°C"),
            "presentCapacity": (54.518002, "Ah"),
            "presentVolts": (13.0, "V"),
            "maximumCapacity": (99.505997, "Ah"),
            "sku": "RBT100LFP12SH-G1",
            "batteryLevel": (54.784637, "%"),
            "presentAmps": (0.0, "mA"),
            "heatingModeStatus": (0, ""),
        },
    },
}

DUPE_SERIAL = {
    "230314043002434307": {
        "deviceId": "230314043002434307",
        "name": "Renogy ONE M1",
        "mac": "",
        "firmware": "V1.3.99",
        "status": "online",
        "connection": "Hub",
        "serial": "23RMG3523812001099",
        "model": "RMS-LP4-G2",
        "data": {},
    },
    "250101091000725004": {
        "deviceId": "250101091000725004",
        "parent": "230314043002434307",
        "name": "Temp & RH Sensor",
        "mac": "",
        "firmware": "",
        "status": "online",
        "connection": "Zigbee",
        "serial": "00124B0024CCDB0F",
        "model": "TH01",
        "data": {
            "temperature": (10.8, "C"),
            "humidity": (58, "%"),
            "lowbattery": (57, "%"),
        },
    },
    "230703112949819001": {
        "deviceId": "230703112949819001",
        "parent": "230314043002434307",
        "name": "RBT100LFP12S-G1",
        "mac": "31",
        "firmware": "",
        "status": "online",
        "connection": "Bluetooth",
        "serial": "BT-TH-66EDEF65",
        "model": "RBT100LFP12S-G1",
        "data": {
            "communicationMethod": (None, ""),
            "presentCapacity": (None, ""),
            "error": (None, ""),
            "remainingTime": (None, ""),
            "heatingModeStatus": (None, ""),
            "temperature": (4.0, "C"),
            "presentVolts": (13.50, "V"),
            "cellVolts": (None, ""),
            "maximumCapacity": (100.00, "%"),
            "totalMaximumCapacity": (100.00, "%"),
            "firmwareVersion": "0022",
            "sku": None,
            "batteryLevel": (99.66, "%"),
            "presentAmps": (0.00, "mA"),
        },
    },
    "220327070523454002": {
        "deviceId": "220327070523454002",
        "parent": "230314043002434307",
        "name": "RBT100LFP12S-G1",
        "mac": "30",
        "firmware": "",
        "status": "online",
        "connection": "Bluetooth",
        "serial": "BT-TH-66EDEF65",
        "model": "RBT100LFP12S-G1",
        "data": {
            "communicationMethod": (None, ""),
            "presentCapacity": (None, ""),
            "error": (None, ""),
            "remainingTime": (None, ""),
            "heatingModeStatus": (None, ""),
            "temperature": (4.0, "°C"),
            "presentVolts": (13.50, "V"),
            "cellVolts": (None, ""),
            "maximumCapacity": (100.00, "%"),
            "totalMaximumCapacity": (100.00, "%"),
            "firmwareVersion": "0026",
            "sku": None,
            "batteryLevel": (99.59, "%"),
            "presentAmps": (0.00, "mA"),
        },
    },
}
