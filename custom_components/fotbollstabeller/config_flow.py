"""Config flow for Fotbollstabeller integration."""
from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import DEFAULT_API_KEY, DOMAIN


class FotbollstabellerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Fotbollstabeller."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Create entry and optionally accept a custom SportsDB API key."""
        errors = {}

        if user_input is not None:
            api_key = (user_input.get("api_key") or "").strip()
            data = {"api_key": api_key} if api_key else {"api_key": DEFAULT_API_KEY}
            await self.async_set_unique_id(DOMAIN)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Fotbollstabeller", data=data)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Optional("api_key", default=""): str,
                }
            ),
            errors=errors,
            description_placeholders={"default_key": DEFAULT_API_KEY},
        )

    @staticmethod
    def async_get_options_flow(config_entry):
        return FotbollstabellerOptionsFlow(config_entry)


class FotbollstabellerOptionsFlow(config_entries.OptionsFlow):
    """Allow changing the optional SportsDB API key."""

    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            api_key = (user_input.get("api_key") or "").strip()
            return self.async_create_entry(
                title="",
                data={"api_key": api_key or DEFAULT_API_KEY},
            )

        current = (self.config_entry.data.get("api_key") or "").strip()
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional("api_key", default=current or ""): str,
                }
            ),
        )
