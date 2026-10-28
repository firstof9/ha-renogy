"""Adds config flow for Renogy."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from renogyapi import Renogy as api
from renogyapi.exceptions import (
    NoDevices,
    NotAuthorized,
    RateLimit,
    UrlNotFound,
)

from .ble_detector import async_detect_device_type
from .ble_utils import _obfuscate_mac, format_mac_address
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
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)

if TYPE_CHECKING:
    from homeassistant.components.bluetooth import BluetoothServiceInfoBleak

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPES = ["controller", "battery", "inverter"]


class RenogyFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Renogy."""

    VERSION = 1
    DEFAULTS = {CONF_NAME: DEFAULT_NAME}

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> RenogyOptionsFlowHandler:
        """Get the options flow for this handler."""
        return RenogyOptionsFlowHandler(config_entry)

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
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
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
    ) -> dict[str, Any]:
        """Handle a Bluetooth discovery."""
        _LOGGER.debug(
            "Discovered Renogy BLE device: %s (%s)",
            discovery_info.name,
            _obfuscate_mac(discovery_info.address),
        )

        await self.async_set_unique_id(discovery_info.address)
        self._abort_if_unique_id_configured()

        self._discovered_device = discovery_info
        self.context["title_placeholders"] = {
            "name": discovery_info.name or "Renogy BLE Device"
        }

        return await self.async_step_bluetooth_confirm()

    async def async_step_bluetooth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Confirm Bluetooth discovery and configure device."""
        self._errors = {}

        if user_input is not None:
            if self._discovered_device is None:
                return self.async_abort(reason="discovery_device_missing")
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

        if self._discovered_device is None:
            return self.async_abort(reason="discovery_device_missing")

        device_name = self._discovered_device.name or DEFAULT_BLE_NAME

        if not hasattr(self, "_detected_type"):
            await self._async_ensure_detected_device(self._discovered_device.address)

        return self.async_show_form(
            step_id="bluetooth_confirm",
            data_schema=_get_ble_schema(
                defaults={
                    CONF_NAME: device_name,
                    CONF_MAC_ADDRESS: self._discovered_device.address,
                    **self._get_detected_ble_defaults(),
                },
                show_mac=False,
            ),
            description_placeholders={"name": device_name},
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Shared validation & detection helpers
    # ------------------------------------------------------------------

    async def _async_ensure_detected_device(self, mac_address: str) -> None:
        """Probe BLE device type and ID if not already detected."""
        if not hasattr(self, "_detected_type"):
            self._detected_type, self._detected_id = await async_detect_device_type(
                self.hass, mac_address
            )

    def _get_detected_ble_defaults(self) -> dict[str, Any]:
        """Return default BLE device type and ID based on detection."""
        return {
            CONF_DEVICE_TYPE: getattr(self, "_detected_type", None) or "controller",
            CONF_DEVICE_ID: getattr(self, "_detected_id", None) or DEFAULT_DEVICE_ID,
        }

    async def _async_validate_cloud_input(
        self, user_input: dict[str, Any]
    ) -> dict[str, str]:
        """Validate Cloud API credentials and return any field errors."""
        errors: dict[str, str] = {}
        renogy = api(
            secret_key=user_input[CONF_SECRET_KEY],
            access_key=user_input[CONF_ACCESS_KEY],
            session=async_get_clientsession(self.hass),
        )
        try:
            await renogy.get_devices()
        except NoDevices:
            _LOGGER.exception("No devices found in API request.")
            errors[CONF_ACCESS_KEY] = "no_devices"
        except NotAuthorized:
            _LOGGER.exception("Invalid key(s).")
            errors[CONF_SECRET_KEY] = "invalid_key"
            errors[CONF_ACCESS_KEY] = "invalid_key"
        except RateLimit:
            _LOGGER.exception("Rate limit exceeded.")
            errors[CONF_NAME] = "rate_limit"
        except UrlNotFound:
            _LOGGER.exception("URL error communicating with Renogy.")
            errors[CONF_NAME] = "api_error"
        except Exception as ex:
            _LOGGER.exception(
                "Error contacting Renogy API: %s",
                ex,
            )
            errors[CONF_NAME] = "general"
        return errors

    def _validate_and_format_mac(self, raw_mac: str) -> str | None:
        """Validate and normalize a MAC address, setting self._errors on failure."""
        try:
            return format_mac_address(raw_mac.strip())
        except ValueError:
            self._errors[CONF_MAC_ADDRESS] = "invalid_mac"
            return None

    # ------------------------------------------------------------------
    # Step 2a: Cloud API configuration
    # ------------------------------------------------------------------

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle cloud API configuration step."""
        self._errors = {}

        if user_input is not None:
            self._errors = await self._async_validate_cloud_input(user_input)
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
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle BLE configuration step (MAC Address)."""
        self._errors = {}

        if user_input is not None:
            mac_address = self._validate_and_format_mac(
                user_input.get(CONF_MAC_ADDRESS, "")
            )
            if mac_address is not None:
                await self.async_set_unique_id(mac_address)
                self._abort_if_unique_id_configured()

                self._data.update(user_input)
                self._data[CONF_MAC_ADDRESS] = mac_address

                await self._async_ensure_detected_device(mac_address)
                return await self.async_step_ble_step2()

        return self.async_show_form(
            step_id="ble",
            data_schema=_get_ble_schema(
                defaults={
                    CONF_NAME: DEFAULT_BLE_NAME,
                },
                show_mac=True,
                mac_only=True,
            ),
            errors=self._errors,
        )

    async def async_step_ble_step2(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Handle BLE configuration step (Device Type/ID)."""
        self._errors = {}

        if user_input is not None:
            data = {
                **self._data,
                **user_input,
                CONF_CONNECTION_TYPE: CONNECTION_TYPE_BLE,
            }
            title = data.get(CONF_NAME, DEFAULT_BLE_NAME)
            return self.async_create_entry(title=title, data=data)

        return self.async_show_form(
            step_id="ble_step2",
            data_schema=_get_ble_schema(
                defaults=self._get_detected_ble_defaults(),
                show_mac=False,
                mac_only=False,
            ),
            errors=self._errors,
        )

    # ------------------------------------------------------------------
    # Reconfigure
    # ------------------------------------------------------------------

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Add reconfigure step to allow to reconfigure a config entry."""
        self._entry = self._get_reconfigure_entry()
        if not self._entry:
            return self.async_abort(reason="reconfigure_entry_missing")
        self._data = dict(self._entry.data)
        self._errors = {}

        connection_type = self._data.get(CONF_CONNECTION_TYPE, CONNECTION_TYPE_CLOUD)

        if connection_type == CONNECTION_TYPE_BLE:
            return await self._reconfigure_ble(user_input)
        return await self._reconfigure_cloud(user_input)

    async def _reconfigure_cloud(self, user_input: dict[str, Any] | None = None):
        """Reconfigure cloud API settings."""
        if user_input is not None:
            self._errors = await self._async_validate_cloud_input(user_input)
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
            mac_address = self._validate_and_format_mac(
                user_input.get(CONF_MAC_ADDRESS, "")
            )
            if mac_address is not None:
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
    user_input: dict[str, Any] | None,
    default_dict: dict[str, Any],
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
    defaults: dict[str, Any],
    show_mac: bool = True,
    mac_only: bool = False,
) -> vol.Schema:
    """Build the BLE configuration schema.

    Args:
        defaults: Default values for each field.
        show_mac: Whether to include the MAC address field.
                  False for auto-discovery (MAC is already known).
        mac_only: Whether to only show Name & MAC (for manual entry step 1).
    """
    schema_dict: dict[vol.Marker, Any] = {}

    if CONF_NAME in defaults:
        schema_dict[
            vol.Optional(CONF_NAME, default=defaults.get(CONF_NAME, DEFAULT_BLE_NAME))
        ] = cv.string

    if show_mac:
        schema_dict[
            vol.Required(
                CONF_MAC_ADDRESS,
                default=defaults.get(CONF_MAC_ADDRESS, ""),
            )
        ] = cv.string

    if not mac_only:
        schema_dict[
            vol.Required(
                CONF_DEVICE_TYPE,
                default=defaults.get(CONF_DEVICE_TYPE, "controller"),
            )
        ] = vol.In(DEVICE_TYPES)

        schema_dict[
            vol.Optional(
                CONF_DEVICE_ID,
                default=defaults.get(CONF_DEVICE_ID, DEFAULT_DEVICE_ID),
            )
        ] = cv.positive_int

    return vol.Schema(schema_dict)


class RenogyOptionsFlowHandler(config_entries.OptionsFlowWithConfigEntry):
    """Handle Renogy options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Manage the Renogy options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current_interval = self.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCAN_INTERVAL,
                        default=current_interval,
                    ): vol.All(vol.Coerce(int), vol.Clamp(min=MIN_SCAN_INTERVAL)),
                }
            ),
        )
