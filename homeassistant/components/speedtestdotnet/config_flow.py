"""Config flow for Transmission Bittorent Client."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import callback

from .const import (
    CONF_MANUAL,
    CONF_SERVER_ID,
    CONF_SERVER_NAME,
    DEFAULT_NAME,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_SERVER,
)
from .const import DOMAIN  # pylint: disable=unused-import

_LOGGER = logging.getLogger(__name__)


class SpeedTestFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle SpeedTest config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return SpeedTestOptionsFlowHandler(config_entry)

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        if self._async_current_entries():
            return self.async_abort(reason="one_instance_allowed")

        if user_input is None:
            return self.async_show_form(step_id="user")

        return self.async_create_entry(title=DEFAULT_NAME, data=user_input)


class SpeedTestOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle SpeedTest options."""

    def __init__(self, config_entry):
        """Initialize options flow."""
        self.config_entry = config_entry
        self._servers = {}

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        errors = {}

        if user_input is not None:
            server_name = user_input[CONF_SERVER_NAME]
            if server_name != "*Auto Detect":
                server_id = self._servers[server_name][0]["id"]
                user_input[CONF_SERVER_ID] = server_id
            else:
                user_input[CONF_SERVER_ID] = None

            return self.async_create_entry(title="", data=user_input)

        self._servers = self.hass.data[DOMAIN].servers
        options = {
            vol.Optional(
                CONF_SERVER_NAME,
                default=self.config_entry.options.get(CONF_SERVER_NAME, DEFAULT_SERVER),
            ): vol.In(self._servers.keys()),
            vol.Optional(
                CONF_SCAN_INTERVAL,
                default=self.config_entry.options.get(
                    CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                ),
            ): int,
            vol.Optional(
                CONF_MANUAL, default=self.config_entry.options.get(CONF_MANUAL, False)
            ): bool,
        }

        return self.async_show_form(
            step_id="init", data_schema=vol.Schema(options), errors=errors
        )
