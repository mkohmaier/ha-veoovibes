from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_TOKEN,
    CONF_VERIFY_SSL as CONF_VERIFY_SSL_CONST,
    DEFAULT_VERIFY_SSL,
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
        vol.Optional(CONF_VERIFY_SSL_CONST, default=DEFAULT_VERIFY_SSL): bool,
    }
)


async def _validate_credentials(
    hass: HomeAssistant, base_url: str, api_key: str, verify_ssl: bool
) -> None:
    """Verbindungs-/Auth-Check: list_rooms muss erfolgreich sein."""
    session = async_get_clientsession(hass)
    api = VeoovibesClient(base_url, api_key, verify_ssl, session)
    await api.list_rooms()


class VeoovibesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Setup-Flow für Veoovibes (ohne Options-Flow)."""

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
