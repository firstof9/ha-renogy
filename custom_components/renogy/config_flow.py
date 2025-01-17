"""Adds config flow for Renogy."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.helpers import config_validation as cv
from renogyapi import Renogy as api
from renogyapi.exceptions import (
    APIError,
    NoDevices,
    NotAuthorized,
    RateLimit,
    UrlNotFound,
)

from .const import CONF_ACCESS_KEY, CONF_NAME, CONF_SECRET_KEY, DEFAULT_NAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


@config_entries.HANDLERS.register(DOMAIN)
class OpenEVSEFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for KeyMaster."""

    VERSION = 1
    DEFAULTS = {CONF_NAME: DEFAULT_NAME}

    def __init__(self):
        """Set up the instance."""
        self._errors = {}
        self._data = {}
        self._entry = {}

    async def async_step_user(
        self, user_input: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Handle a flow initialized by the user."""
        self._errors = {}

        if user_input is not None:
            renogy = api(
                secret_key=user_input[CONF_SECRET_KEY],
                access_key=user_input[CONF_ACCESS_KEY],
            )
            # Test connection
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
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return await self._show_config_form(user_input)

    async def _show_config_form(self, user_input):
        """Show the configuration form."""
        return self.async_show_form(
            step_id="user",
            data_schema=_get_schema(user_input, self.DEFAULTS),
            errors=self._errors,
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None):
        """Add reconfigure step to allow to reconfigure a config entry."""
        self._entry = self._get_reconfigure_entry()
        assert self._entry
        self._data = dict(self._entry.data)
        self._errors = {}

        if user_input is not None:
            renogy = api(
                secret_key=user_input[CONF_SECRET_KEY],
                access_key=user_input[CONF_ACCESS_KEY],
            )
            # Test connection
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
            except APIError:
                _LOGGER.exception("API error communicating with Renogy.")
                self._errors[CONF_NAME] = "api_error"
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
        return await self._show_reconfig_form(user_input)

    async def _show_reconfig_form(self, user_input):
        """Show the configuration form to edit configuration data."""
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_get_schema(user_input, self._data),
            errors=self._errors,
        )


def _get_schema(  # pylint: disable-next=unused-argument
    user_input: Optional[Dict[str, Any]],
    default_dict: Dict[str, Any],
    # pylint: disable-next=unused-argument
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
