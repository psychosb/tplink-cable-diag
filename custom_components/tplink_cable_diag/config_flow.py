"""Config flow for TP-Link Cable Diagnostics."""

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_SWITCH_IP,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SCHEDULE_DAY,
    CONF_SCHEDULE_HOUR,
    DEFAULT_USERNAME,
    DEFAULT_SCHEDULE_DAY,
    DEFAULT_SCHEDULE_HOUR,
    SCHEDULE_DAYS,
)
from .switch_client import TpLinkSwitchClient


class TpLinkCableDiagConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for TP-Link Cable Diagnostics."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            client = TpLinkSwitchClient(
                user_input[CONF_SWITCH_IP],
                user_input[CONF_USERNAME],
                user_input[CONF_PASSWORD],
            )

            if await client.async_test_connection():
                await self.async_set_unique_id(user_input[CONF_SWITCH_IP])
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=f"TL-SG108E ({user_input[CONF_SWITCH_IP]})",
                    data=user_input,
                )
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SWITCH_IP, default="192.168.1.3"): str,
                    vol.Required(CONF_USERNAME, default=DEFAULT_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                    vol.Optional(
                        CONF_SCHEDULE_DAY, default=DEFAULT_SCHEDULE_DAY
                    ): vol.In(SCHEDULE_DAYS),
                    vol.Optional(
                        CONF_SCHEDULE_HOUR, default=DEFAULT_SCHEDULE_HOUR
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow."""
        return TpLinkCableDiagOptionsFlow(config_entry)


class TpLinkCableDiagOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCHEDULE_DAY,
                        default=self.config_entry.data.get(
                            CONF_SCHEDULE_DAY, DEFAULT_SCHEDULE_DAY
                        ),
                    ): vol.In(SCHEDULE_DAYS),
                    vol.Optional(
                        CONF_SCHEDULE_HOUR,
                        default=self.config_entry.data.get(
                            CONF_SCHEDULE_HOUR, DEFAULT_SCHEDULE_HOUR
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
                }
            ),
        )
