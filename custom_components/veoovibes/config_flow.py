from __future__ import annotations
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
)
from .api import VeoovibesClient, VeoovibesApiError

class VeoovibesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors = {}
        if user_input is not None:
            session = async_get_clientsession(self.hass)
            client = VeoovibesClient(
                user_input[CONF_BASE_URL],
                user_input.get(CONF_TOKEN),
                user_input.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                session,
            )
            try:
                rooms = await client.list_rooms()
                if not rooms:
                    errors["base"] = "no_rooms"
                else:
                    await self.async_set_unique_id(user_input[CONF_BASE_URL].rstrip("/"))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(title="Veoovibes", data=user_input)
            except VeoovibesApiError:
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required(CONF_BASE_URL, default="http://veoovibes.local"): str,
            vol.Required(CONF_TOKEN): str,
            vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)
