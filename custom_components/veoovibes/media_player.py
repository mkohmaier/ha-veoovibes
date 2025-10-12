from __future__ import annotations
from typing import Optional, List
import logging
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import MediaPlayerState, RepeatMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, KEY_ROOMS, KEY_STATE
from .api import VeoovibesClient, VeoovibesApiError

_LOGGER = logging.getLogger(__name__)

# Features: Play/Stop, Pause→Stop (für Tiles), Next/Prev, Volume, Turn On/Off (Power-Icon)
# NEU: Repeat & Select Source
FEATURES = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.PAUSE          # wir mappen Pause auf Stop (Play/Off UX)
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.REPEAT_SET     # NEU
    | MediaPlayerEntityFeature.SELECT_SOURCE  # NEU
    | MediaPlayerEntityFeature.VOLUME_SET
    | MediaPlayerEntityFeature.TURN_ON
    | MediaPlayerEntityFeature.TURN_OFF
)

async def async_setup_entry(hass, entry: ConfigEntry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data["coordinator"]
    client: VeoovibesClient = data["client"]

    def _rid(room: dict) -> Optional[str]:
        rid = room.get("id_room") or room.get("api_room_id") or room.get("key")
        return str(rid) if rid is not None else None

    entities = []
    seen = set()
    for room in coordinator.data[KEY_ROOMS]:
        rid = _rid(room)
        if not rid or rid in seen:
            continue
        seen.add(rid)
        name = room.get("name") or room.get("api_room_name") or f"Room {rid}"
        entities.append(VeoRoomEntity(coordinator, client, entry, rid, name))
    async_add_entities(entities, True)


class VeoRoomEntity(CoordinatorEntity, MediaPlayerEntity):
    """One media_player per Veoovibes room."""

    _attr_should_poll = False
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, coordinator, client: VeoovibesClient, entry: ConfigEntry, room_id: str, name: str):
        super().__init__(coordinator)
        self._client = client
        self._entry = entry  # NEU: für Zugriff auf global_sources
        self._room_id = room_id
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}"
        self._attr_supported_features = FEATURES
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_room_{room_id}")},
            name=f"Veoovibes – {name}",
            manufacturer="inveoo",
            configuration_url=entry.data.get("base_url"),
        )

    # ----- helpers -----
    def _st(self) -> dict:
        return self.coordinator.data[KEY_STATE].get(self._room_id, {}) or {}

    def _global_sources(self) -> list[dict]:
        # Wird in __init__.py unter hass.data[DOMAIN][entry_id]["global_sources"] gepflegt
        data = self.hass.data[DOMAIN][self._entry.entry_id]
        return data.get("global_sources", []) or []

    # ----- state mapping -----
    @property
    def state(self):
        st = self._st()
        playing = bool(st.get("is_playing", 0)) or str(st.get("status_code", "")).lower() == "playing"
        if playing:
            return MediaPlayerState.PLAYING
        # Wunsch: bei "nicht spielend" als AUS anzeigen
        return MediaPlayerState.OFF

    @property
    def volume_level(self):
        st = self._st()
        vol = st.get("zone_volume")
        if isinstance(vol, (int, float)):
            return max(0.0, min(1.0, float(vol) / 100.0))
        vol2 = st.get("current_volume")
        if isinstance(vol2, (int, float)):
            return max(0.0, min(1.0, float(vol2) / 100.0))
        return None

    @property
    def media_title(self):
        st = self._st()
        return st.get("title") or st.get("radio_name")

    @property
    def media_artist(self):
        return self._st().get("artist")

    @property
    def media_album_name(self):
        return self._st().get("album")

    @property
    def media_image_url(self):
        return self._st().get("cover")

    # ----- Repeat (Toggle) -----
    @property
    def repeat(self) -> Optional[str]:
        st = self._st()
        rep = st.get("repeat")
        if isinstance(rep, (bool, int)):
            return RepeatMode.ALL if bool(rep) else RepeatMode.OFF
        if isinstance(rep, str):
            rep_l = rep.lower()
            if rep_l in ("all", "one", "true", "1"):
                return RepeatMode.ALL
            if rep_l in ("off", "false", "0"):
                return RepeatMode.OFF
        return RepeatMode.OFF

    async def async_set_repeat(self, repeat: str) -> None:
        desired_on = repeat != RepeatMode.OFF
        current_on = self.repeat != RepeatMode.OFF
        if desired_on != current_on:
            try:
                # Toggle per API
                await self._client.room_repeat(self._room_id)
            except VeoovibesApiError as exc:
                _LOGGER.debug("repeat toggle failed for room %s: %s", self._room_id, exc)
        await self.coordinator.async_request_refresh()

    # ----- Source-Auswahl (global) -----
    @property
    def source_list(self) -> Optional[List[str]]:
        srcs = self._global_sources()
        return [s["name"] for s in srcs] if srcs else None

    async def async_select_source(self, source: str) -> None:
        srcs = self._global_sources()
        match = next((s for s in srcs if s.get("name") == source), None)
        if not match:
            _LOGGER.warning("select_source: '%s' not in global sources", source)
            return
        try:
            await self._client.music_room(self._room_id, match["group"], match["prog"])
        except VeoovibesApiError as exc:
            _LOGGER.debug("select_source failed for room %s: %s", self._room_id, exc)
        finally:
            await self.coordinator.async_request_refresh()

    # ----- core media controls -----
    async def async_media_play(self):
        await self._client.play_room(self._room_id)
        await self.coordinator.async_request_refresh()

    async def async_media_pause(self):
        """Treat pause as stop (für klare Play/Off UX)."""
        await self._client.stop_room(self._room_id)
        await self.coordinator.async_request_refresh()

    async def async_media_stop(self):
        await self._client.stop_room(self._room_id)
        await self.coordinator.async_request_refresh()

    async def async_media_next_track(self):
        await self._client.next_room(self._room_id)
        await self.coordinator.async_request_refresh()

    async def async_media_previous_track(self):
        await self._client.prev_room(self._room_id)
        await self.coordinator.async_request_refresh()

    async def async_set_volume_level(self, volume: float):
        vol_0_100 = int(max(0.0, min(1.0, volume)) * 100.0)
        await self._client.set_room_volume(self._room_id, vol_0_100)
        await self.coordinator.async_request_refresh()

    # ----- Power toggle for tiles (Play ↔ Off), robust gegen API-Fehler -----
    async def async_turn_on(self):
        """Map 'turn_on' to Play; Fehler werden geloggt, nicht geworfen."""
        try:
            await self._client.play_room(self._room_id)
        except VeoovibesApiError as exc:
            _LOGGER.debug("turn_on failed for room %s: %s", self._room_id, exc)
        finally:
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self):
        """Map 'turn_off' to Stop."""
        try:
            await self._client.stop_room(self._room_id)
        except VeoovibesApiError as exc:
            _LOGGER.debug("turn_off failed for room %s: %s", self._room_id, exc)
        finally:
            await self.coordinator.async_request_refresh()
