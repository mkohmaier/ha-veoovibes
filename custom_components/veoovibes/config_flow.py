from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_VERIFY_SSL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_TOKEN,
    CONF_VERIFY_SSL as CONF_VERIFY_SSL_CONST,
    DEFAULT_VERIFY_SSL,
    CONF_SOURCE_MAP,  # für Optionen
)
from .api import VeoovibesClient, VeoovibesApiError


def _normalize_base_url(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return v
    if not v.startswith(("http://", "https://")):
        v = "http://" + v
    return v.rstrip("/")


USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_BASE_URL): str,
        vol.Required(CONF_TOKEN): str,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def _validate_credentials(
    hass: HomeAssistant, base_url: str, api_key: str, verify_ssl: bool
) -> None:
    session = async_get_clientsession(hass)
    api = VeoovibesClient(base_url, api_key, verify_ssl, session)
    await api.list_rooms()


class VeoovibesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            base_url = _normalize_base_url(user_input[CONF_BASE_URL])
            api_key = user_input[CONF_TOKEN].strip()
            verify_ssl = bool(user_input.get(CONF_VERIFY_SSL_CONST, DEFAULT_VERIFY_SSL))
            try:
                await _validate_credentials(self.hass, base_url, api_key, verify_ssl)
            except VeoovibesApiError:
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title="Veoovibes",
                    data={
                        CONF_BASE_URL: base_url,
                        CONF_TOKEN: api_key,
                        CONF_VERIFY_SSL_CONST: verify_ssl,
                    },
                )

        return self.async_show_form(step_id="user", data_schema=USER_SCHEMA, errors=errors)


# ===== Options-Flow (für globale Quellenliste) =====
from homeassistant.core import callback  # noqa: E402

class VeoovibesOptionsFlow(config_entries.OptionsFlow):
    """Einfacher Options-Dialog: ein Textfeld mit YAML/JSON (source_map)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        return await self.async_step_sources(user_input)

    async def async_step_sources(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = self.config_entry.options.get(CONF_SOURCE_MAP, "")
        schema = vol.Schema({vol.Optional(CONF_SOURCE_MAP, default=current): str})
        return self.async_show_form(step_id="sources", data_schema=schema)

@callback
def async_get_options_flow(config_entry):
    return VeoovibesOptionsFlow(config_entry)
