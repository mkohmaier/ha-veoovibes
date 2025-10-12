from __future__ import annotations
from datetime import timedelta
import logging
import json
import yaml
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from .const import (
    DOMAIN,
    CONF_BASE_URL,
    CONF_TOKEN,
    CONF_VERIFY_SSL,
    DEFAULT_VERIFY_SSL,
    DEFAULT_SCAN_INTERVAL,
    KEY_ROOMS,
    KEY_STATE,
    CONF_SOURCE_MAP,  # <— NEU
)
from .api import VeoovibesClient, VeoovibesApiError

_LOGGER = logging.getLogger(__name__)


def _parse_global_sources(raw: str) -> list[dict]:
    """Erwartet YAML oder JSON der Form:
    sources:
      - name: "FM4"
        group: 1
        prog: 3
    Gibt eine Liste von Dicts mit name/group/prog zurück.
    """
    if not raw or not str(raw).strip():
        return []
    data = None
    try:
        data = yaml.safe_load(raw)
    except Exception:
        try:
            data = json.loads(raw)
        except Exception as exc:
            _LOGGER.warning("veoovibes: source_map parse error: %s", exc)
            return []
    if not isinstance(data, dict):
        return []

    out: list[dict] = []
    for s in (data.get("sources") or []):
        try:
            out.append({
                "name": str(s["name"]),
                "group": int(s["group"]),
                "prog": int(s["prog"]),
            })
        except Exception:
            continue
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    session = async_get_clientsession(hass)
    base = entry.data[CONF_BASE_URL]
    api_key = entry.data.get(CONF_TOKEN)
    verify = entry.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

    client = VeoovibesClient(base, api_key, verify, session)

    async def _update():
        rooms = await client.list_rooms()
        state_by_room: dict[str, dict] = {}
        for r in rooms:
            rid = r.get("id_room") or r.get("api_room_id") or r.get("key")
            if rid is None:
                continue
            try:
                # In deinem Client heißt das get_room_status
                state_by_room[str(rid)] = await client.get_room_status(rid)
            except VeoovibesApiError as exc:
                _LOGGER.debug("room_player_status failed for %s: %s", rid, exc)
        return {KEY_ROOMS: rooms, KEY_STATE: state_by_room}

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="veoovibes",
        update_method=_update,
        update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "client": client,
        "coordinator": coordinator,
        # NEU: globale Quellenliste aus den Optionen parsen
        "global_sources": _parse_global_sources(entry.options.get(CONF_SOURCE_MAP, "")),
        # NEU: Options-Listener registrieren
        "unsub_options": entry.add_update_listener(options_updated),
    }

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.MEDIA_PLAYER])
    return True


async def options_updated(hass: HomeAssistant, entry: ConfigEntry):
    """Wird aufgerufen, wenn die Options (z. B. source_map) geändert wurden."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if not data:
        return
    data["global_sources"] = _parse_global_sources(entry.options.get(CONF_SOURCE_MAP, ""))
    await data["coordinator"].async_request_refresh()


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.MEDIA_PLAYER])
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id, None)
        # NEU: Options-Listener sauber deregistrieren, falls vorhanden
        if data and callable(data.get("unsub_options")):
            try:
                data["unsub_options"]()
            except Exception:  # noqa: BLE001
                pass
    return unload_ok
