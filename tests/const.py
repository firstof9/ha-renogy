"""Renogy tests consts."""

CONFIG_DATA = {
    "name": "Renogy Core",
    "secret_key": "fakeRandomSecretKey",
    "access_key": "fakeRandomAccessKey",
}

DIAG_RESULTS = {
    "1234567890": {
        "connection": "Hub",
        "data": {},
        "deviceId": "1234567890",
        "firmware": "V1.1.157",
        "mac": "DE:AD:BE:EF:FE:ED",
        "model": "RSHGWSN-W02W-G1",
        "name": "Renogy ONE Core",
        "serial": "TOTALLYFAKESN",
        "status": "online",
    },
    "12345678901": {
        "connection": "RS485",
        "data": {},
        "deviceId": "12345678901",
        "firmware": "0100.0102.0202",
        "mac": "32",
        "model": "RINVTPGH110111S",
        "name": "Inverter",
        "serial": "",
        "status": "online",
    },
    "12345678902": {
        "connection": "Bluetooth",
        "data": {},
        "deviceId": "12345678902",
        "firmware": "",
        "mac": "F0:F8:F2:5D:5D:8716",
        "model": "RNG-CTRL-RVR40",
        "name": "RNG-CTRL-RVR40",
        "serial": "",
        "status": "online",
    },
    "12345678903": {
        "connection": "RS485",
        "data": {
            "averageTemperature": -3,
            "batteryLevel": 54.784637,
            "heatingModeStatus": 0,
            "maximumCapacity": 99.505997,
            "presentAmps": 0.0,
            "presentCapacity": 54.518002,
            "presentVolts": 13.0,
            "sku": "RBT100LFP12SH-G1",
        },
        "deviceId": "12345678903",
        "firmware": "",
        "mac": "48",
        "model": "RBT100LFP12SH-G1",
        "name": "RBT100LFP12SH-G1",
        "serial": "",
        "status": "online",
    },
}
