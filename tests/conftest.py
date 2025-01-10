"""Provide common pytest fixtures."""

import json
from unittest.mock import patch

import pytest
from aioresponses import aioresponses

from .common import load_fixture
from .const import DUPE_SERIAL

BASE_URL = "https://openapi.renogy.com"
DEVICE_LIST = "/device/list"


# This fixture enables loading custom integrations in all tests.
# Remove to enable selective use of this fixture
@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integration tests."""
    yield


# This fixture is used to prevent HomeAssistant from attempting to create and dismiss persistent
# notifications. These calls would fail without this fixture since the persistent_notification
# integration is never loaded during a test.
@pytest.fixture(name="skip_notifications", autouse=True)
def skip_notifications_fixture():
    """Skip notification calls."""
    with patch("homeassistant.components.persistent_notification.async_create"), patch(
        "homeassistant.components.persistent_notification.async_dismiss"
    ):
        yield


@pytest.fixture
def mock_aioclient():
    """Fixture to mock aioclient calls."""
    with aioresponses() as m:
        yield m


@pytest.fixture(name="mock_api")
def mock_api(mock_aioclient):
    """Fixure to mock API calls."""
    mock_aioclient.get(
        BASE_URL + DEVICE_LIST,
        status=200,
        body=load_fixture("device_list.json"),
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/1234567890",
        status=200,
        body="",
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/12345678901",
        status=200,
        body=load_fixture("realtime_data_inverter.json"),
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/12345678902",
        status=200,
        body=load_fixture("realtime_data_2.json"),
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/12345678903",
        status=200,
        body=load_fixture("realtime_data.json"),
        repeat=True,
    )


@pytest.fixture(name="mock_api_no_devices")
def mock_api_no_devices(mock_aioclient):
    """Fixure to mock API calls."""
    mock_aioclient.get(
        BASE_URL + DEVICE_LIST,
        status=200,
        body="[]",
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/1234567890",
        status=200,
        body="",
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/12345678901",
        status=200,
        body=load_fixture("realtime_data_inverter.json"),
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/12345678902",
        status=200,
        body=load_fixture("realtime_data_2.json"),
        repeat=True,
    )
    mock_aioclient.get(
        f"{BASE_URL}/device/data/latest/12345678903",
        status=200,
        body=load_fixture("realtime_data.json"),
        repeat=True,
    )

@pytest.fixture(name="mock_coordinator")
def mock_coord():
    """Mock charger data."""
    with patch(
        "custom_components.renogy.RenogyUpdateCoordinator._async_update_data"
    ) as mock_value:
        mock_value.return_value = DUPE_SERIAL
        yield