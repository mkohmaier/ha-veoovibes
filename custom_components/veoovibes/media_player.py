from __future__ import annotations
from typing import Optional
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
)
from homeassistant.components.media_player.const import MediaPlayerState
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from .const import DOMAIN, KEY_ROOMS, KEY_STATE
from .api import VeoovibesClient

FEATURES = (
    MediaPlayerEntityFeature.PLAY
    | MediaPlayerEntityFeature.STOP
    | MediaPlayerEntityFeature.NEXT_TRACK
    | MediaPlayerEntityFeature.PREVIOUS_TRACK
    | MediaPlayerEntityFeature.VOLUME_SET
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
    _attr_should_poll = False
    _attr_icon = "mdi:speaker-multiple"

    def __init__(self, coordinator, client: VeoovibesClient, entry: ConfigEntry, room_id: str, name: str):
        super().__init__(coordinator)
        self._client = client
        self._room_id = room_id
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_room_{room_id}"
        self._attr_supported_features = FEATURES
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry.entry_id}_room_{room_id}")},  # separate device per room
            name=f"Veoovibes – {name}",
            manufacturer="inveoo",
            configuration_url=entry.data.get("base_url"),
        )

    def _st(self) -> dict:
        return self.coordinator.data[KEY_STATE].get(self._room_id, {}) or {}

    @property
    def state(self):
        st = self._st()
        playing = bool(st.get("is_playing", 0)) or str(st.get("status_code", "")).lower() == "playing"
        return MediaPlayerState.PLAYING if playing else MediaPlayerState.PAUSED

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

    async def async_media_play(self):
        await self._client.play_room(self._room_id)
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
