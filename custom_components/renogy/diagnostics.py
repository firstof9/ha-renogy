"""Provide diagnostics for Renogy."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry

from . import RenogyConfigEntry
from .const import CONF_ACCESS_KEY, CONF_MAC_ADDRESS, CONF_SECRET_KEY

REDACT_KEYS = {CONF_ACCESS_KEY, CONF_MAC_ADDRESS, CONF_SECRET_KEY, "mac", "serial"}


async def async_get_config_entry_diagnostics(  # pylint: disable-next=unused-argument
    hass: HomeAssistant, config_entry: RenogyConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diag: dict[str, Any] = {}
    diag["config"] = config_entry.as_dict()
    return async_redact_data(diag, REDACT_KEYS)


async def async_get_device_diagnostics(  # pylint: disable-next=unused-argument
    hass: HomeAssistant, config_entry: RenogyConfigEntry, device: DeviceEntry
) -> dict[str, Any]:
    """Return diagnostics for a device."""
    return async_redact_data(config_entry.runtime_data.coordinator.data, REDACT_KEYS)
