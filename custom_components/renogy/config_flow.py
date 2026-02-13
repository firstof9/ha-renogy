"""Adds config flow for Renogy."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.helpers import config_validation as cv
from renogyapi import Renogy as api
from renogyapi.exceptions import (
    NoDevices,
    NotAuthorized,
    RateLimit,
    UrlNotFound,
)

from .const import (
    CONF_ACCESS_KEY,
    CONF_CONNECTION_TYPE,
    CONF_DEVICE_ID,
    CONF_DEVICE_TYPE,
    CONF_MAC_ADDRESS,
    CONF_NAME,
    CONF_SECRET_KEY,
    CONNECTION_TYPE_BLE,
    CONNECTION_TYPE_CLOUD,
    DEFAULT_BLE_NAME,
    DEFAULT_DEVICE_ID,
    DEFAULT_NAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPES = ["controller", "battery", "inverter"]


@config_entries.HANDLERS.register(DOMAIN)
class RenogyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Renogy."""

    VERSION = 1
    DEFAULTS = {CONF_NAME: DEFAULT_NAME}

    def __init__(self):
        """Set up the instance."""
        self._errors = {}
        self._data = {}
        self._entry = {}
        self._discovered_device: BluetoothServiceInfoBleak | None = None

    # ------------------------------------------------------------------
    # Step 1: Choose connection type (manual setup)
    # ------------------------------------------------------------------

    async def async_step_user(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        if user_input is not None:
            connection_type = user_input.get(CONF_CONNECTION_TYPE)
            self._data[CONF_CONNECTION_TYPE] = connection_type

            if connection_type == CONNECTION_TYPE_BLE:
                return await self.async_step_ble()
            return await self.async_step_cloud()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_CONNECTION_TYPE, default=CONNECTION_TYPE_CLOUD
                    ): vol.In(
                        {
                            CONNECTION_TYPE_CLOUD: "Cloud API",
                            CONNECTION_TYPE_BLE: "Bluetooth (BLE)",
                        }
                    ),
                }
            ),
        )

    # ------------------------------------------------------------------
    # Bluetooth auto-discovery
    # ------------------------------------------------------------------

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> Dict[str, Any]:
        """Handle a Bluetooth discovery."""
        _LOGGER.debug(
            "Discovered Renogy BLE device: %s (%s)",
            discovery_info.name,
            discovery_info.address,
        )

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_device = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or "Renogy BLE Device"
        }

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Confirm Bluetooth discovery and configure device."""
        self._errors = {}

        if user_input is not None:
            assert self._discovered_device is not None
            mac_address = self._discovered_device.address.upper()

            data = {
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_BLE,
                CONF_NAME: user_input.get(
                    CONF_NAME,
                    self._discovered_device.name or DEFAULT_BLE_NAME,
                ),
                CONF_MAC_ADDRESS: mac_address,
                CONF_DEVICE_TYPE: user_input.get(CONF_DEVICE_TYPE, "controller"),
                CONF_DEVICE_ID: user_input.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
            }
            return self.async_create_entry(title=data[CONF_NAME], data=data)

        assert self._discovered_device is not None
        device_name = self._discovered_device.name or DEFAULT_BLE_NAME

        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=_get_ble_schema(
                defaults={
                    CONF_NAME: device_name,
                    CONF_MAC_ADDRESS: self._discovered_device.address,
                    CONF_DEVICE_TYPE: "controller",
                    CONF_DEVICE_ID: DEFAULT_DEVICE_ID,
                },
                show_mac=False,
            ),
            description_placeholders={"name": device_name},
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Step 2a: Cloud API configuration
    # ------------------------------------------------------------------

    async def async_step_cloud(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle cloud API configuration step."""
        self._errors = {}

        if user_input is not None:
            renogy = api(
                secret_key=user_input[CONF_SECRET_KEY],
                access_key=user_input[CONF_ACCESS_KEY],
            )
            try:
                await renogy.get_devices()
            except NoDevices:
                _LOGGER.exception("No devices found in API request.")
                self._errors[CONF_ACCESS_KEY] = "no_devices"
            except NotAuthorized:
                _LOGGER.exception("Invalid key(s).")
                self._errors[CONF_SECRET_KEY] = "invalid_key"
                self._errors[CONF_ACCESS_KEY] = "invalid_key"
            except RateLimit:
                _LOGGER.exception("Rate limit exceeded.")
                self._errors[CONF_NAME] = "rate_limit"
            except UrlNotFound:
                _LOGGER.exception("URL error communicating with Renogy.")
                self._errors[CONF_NAME] = "api_error"
            except Exception as ex:
                _LOGGER.exception(
                    "Error contacting Renogy API: %s",
                    ex,
                )
                self._errors[CONF_NAME] = "general"

            if not self._errors:
                data = {
                    **self._data,
                    **user_input,
                }
                return self.async_create_entry(
                    title=user_input.get(CONF_NAME, DEFAULT_NAME), data=data
                )

        defaults = self.DEFAULTS
        return self.async_show_form(
            step_id="cloud",
            data_schema=_get_cloud_schema(user_input, defaults),
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Step 2b: BLE configuration (manual)
    # ------------------------------------------------------------------

    async def async_step_ble(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle BLE configuration step."""
        self._errors = {}

        if user_input is not None:
            mac_address = user_input.get(CONF_MAC_ADDRESS, "").strip().upper()
            if not mac_address:
                self._errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                data = {
                    **self._data,
                    **user_input,
                    CONF_MAC_ADDRESS: mac_address,
                }
                title = user_input.get(CONF_NAME, DEFAULT_BLE_NAME)
                return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="ble",
            data_schema=_get_ble_schema(
                defaults={
                    CONF_NAME: DEFAULT_BLE_NAME,
                    CONF_DEVICE_TYPE: "controller",
                    CONF_DEVICE_ID: DEFAULT_DEVICE_ID,
                },
                show_mac=True,
            ),
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Reconfigure
    # ------------------------------------------------------------------

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Add reconfigure step to allow to reconfigure a config entry."""
        self._entry = self._get_reconfigure_entry()
        assert self._entry
        self._data = dict(self._entry.data)
        self._errors = {}

        connection_type = self._data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_CLOUD)

        if connection_type == CONNECTION_TYPE_BLE:
            return await self._reconfigure_ble(user_input)
        return await self._reconfigure_cloud(user_input)

    async def _reconfigure_cloud(self, user_input: dict[str, Any] | None = None):
        """Reconfigure cloud API settings."""
        if user_input is not None:
            renogy = api(
                secret_key=user_input[CONF_SECRET_KEY],
                access_key=user_input[CONF_ACCESS_KEY],
            )
            try:
                await renogy.get_devices()
            except NoDevices:
                _LOGGER.exception("No devices found in API request.")
                self._errors[CONF_ACCESS_KEY] = "no_devices"
            except NotAuthorized:
                _LOGGER.exception("Invalid key(s).")
                self._errors[CONF_SECRET_KEY] = "invalid_key"
                self._errors[CONF_ACCESS_KEY] = "invalid_key"
            except RateLimit:
                _LOGGER.exception("Rate limit exceeded.")
                self._errors[CONF_NAME] = "rate_limit"
            except UrlNotFound:
                _LOGGER.exception("URL error communicating with Renogy.")
                self._errors[CONF_NAME] = "api_error"
            except Exception as ex:
                _LOGGER.exception(
                    "Error contacting Renogy API: %s",
                    ex,
                )
                self._errors[CONF_NAME] = "general"

            if not self._errors:
                _LOGGER.debug("%s reconfigured.", DOMAIN)
                return self.async_update_reload_and_abort(
                    self._entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_get_cloud_schema(user_input, self._data),
            errors=self._errors,
        )

    async def _reconfigure_ble(self, user_input: dict[str, Any] | None = None):
        """Reconfigure BLE settings."""
        if user_input is not None:
            mac_address = user_input.get(CONF_MAC_ADDRESS, "").strip().upper()
            if not mac_address:
                self._errors[CONF_MAC_ADDRESS] = "invalid_mac"
            else:
                user_input[CONF_MAC_ADDRESS] = mac_address
                _LOGGER.debug("%s BLE reconfigured.", DOMAIN)
                return self.async_update_reload_and_abort(
                    self._entry,
                    data_updates=user_input,
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_get_ble_schema(
                defaults={
                    CONF_NAME: self._data.get(CONF_NAME, DEFAULT_BLE_NAME),
                    CONF_MAC_ADDRESS: self._data.get(CONF_MAC_ADDRESS, ""),
                    CONF_DEVICE_TYPE: self._data.get(CONF_DEVICE_TYPE, "controller"),
                    CONF_DEVICE_ID: self._data.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
                },
                show_mac=True,
            ),
            errors=self._errors,
        )


def _get_cloud_schema(
    user_input: Optional[Dict[str, Any]],
    default_dict: Dict[str, Any],
) -> vol.Schema:
    """Get a schema using the default_dict as a backup."""
    if user_input is None:
        user_input = {}

    def _get_default(key: str, fallback_default: Any = None) -> None:
        """Get default value for key."""
        return user_input.get(key, default_dict.get(key, fallback_default))

    return vol.Schema(
        {
            vol.Optional(
                CONF_NAME, default=_get_default(CONF_NAME, DEFAULT_NAME)
            ): cv.string,
            vol.Required(
                CONF_SECRET_KEY, default=_get_default(CONF_SECRET_KEY, "")
            ): cv.string,
            vol.Required(
                CONF_ACCESS_KEY, default=_get_default(CONF_ACCESS_KEY, "")
            ): cv.string,
        },
    )


def _get_ble_schema(
    defaults: Dict[str, Any],
    show_mac: bool = True,
) -> vol.Schema:
    """Build the BLE configuration schema.

    Args:
        defaults: Default values for each field.
        show_mac: Whether to include the MAC address field.
                  False for auto-discovery (MAC is already known).
    """
    schema_dict: dict[vol.Marker, Any] = {
        vol.Optional(
            CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_BLE_NAME)
        ): cv.string,
    }

    if show_mac:
        schema_dict[vol.Required(
            CONF_MAC_ADDRESS,
            default=defaults.get(CONF_MAC_ADDRESS, ""),
        )] = cv.string

    schema_dict[vol.Required(
        CONF_DEVICE_TYPE,
        default=defaults.get(CONF_DEVICE_TYPE, "controller"),
    )] = vol.In(DEVICE_TYPES)

    schema_dict[vol.Optional(
        CONF_DEVICE_ID,
        default=defaults.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
    )] = cv.positive_int

    return vol.Schema(schema_dict)
