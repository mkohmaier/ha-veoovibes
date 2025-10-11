from __future__ import annotations
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN, KEY_ROOMS, KEY_STATE

async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry):
    data = hass.data[DOMAIN][entry.entry_id]
    coord = data["coordinator"]
    return {
        "rooms": coord.data.get(KEY_ROOMS),
        "state": coord.data.get(KEY_STATE),
        "config": {
            "base_url": entry.data.get("base_url", "***"),
            "verify_ssl": entry.data.get("verify_ssl", True),
            "api_key_present": bool(entry.data.get("token"))
        }
    }
