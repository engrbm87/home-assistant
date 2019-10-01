"""Config flow for Mikrotik."""
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import (
    CONF_HOST,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback

from .const import (
    CONF_ARP_PING,
    CONF_DETECTION_TIME,
    CONF_TRACK_DEVICES,
    DEFAULT_API_PORT,
    DEFAULT_NAME,
    DOMAIN,
)
from .errors import CannotConnect, LoginError
from .hub import get_hub


class MikrotikFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Mikrotik config flow."""

    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return MikrotikOptionsFlowHandler(config_entry)

    def __init__(self):
        """Initialize the UniFi flow."""
        self.config = {}

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            for entry in self.hass.config_entries.async_entries(DOMAIN):
                if entry.data[CONF_HOST] == user_input[CONF_HOST]:
                    return self.async_abort(reason="already_configured")

            errors = self.validate_user_input(user_input)
            if not errors:
                return self.async_create_entry(
                    title=self.config[CONF_NAME], data=self.config
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_HOST): str,
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_API_PORT): int,
                    vol.Optional(CONF_VERIFY_SSL, default=False): bool,
                }
            ),
            errors=errors,
        )

    def validate_user_input(self, user_input):
        """Validate user input."""
        errors = {}
        try:
            get_hub(self.hass, user_input)
            self.config.update(user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except LoginError:
            errors[CONF_USERNAME] = "wrong_credentials"
            errors[CONF_PASSWORD] = "wrong_credentials"

        return errors


class MikrotikOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Mikrotik options."""

    def __init__(self, config_entry):
        """Initialize UniFi options flow."""
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the Mikrotik options."""
        return await self.async_step_device_tracker()

    async def async_step_device_tracker(self, user_input=None):
        """Manage the device tracker options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = {
            vol.Optional(
                CONF_TRACK_DEVICES,
                default=self.config_entry.options.get(CONF_TRACK_DEVICES),
            ): bool,
            vol.Optional(
                CONF_ARP_PING, default=self.config_entry.options.get(CONF_ARP_PING)
            ): bool,
            vol.Optional(
                CONF_DETECTION_TIME,
                default=self.config_entry.options.get(CONF_DETECTION_TIME),
            ): int,
        }

        return self.async_show_form(
            step_id="device_tracker", data_schema=vol.Schema(options)
        )
