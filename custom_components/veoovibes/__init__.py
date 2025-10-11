from __future__ import annotations
from datetime import timedelta
import logging
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
)
from .api import VeoovibesClient, VeoovibesApiError

_LOGGER = logging.getLogger(__name__)

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
    hass.data[DOMAIN][entry.entry_id] = {"client": client, "coordinator": coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.MEDIA_PLAYER])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    unload_ok = await hass.config_entries.async_unload_platforms(entry, [Platform.MEDIA_PLAYER])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
