from __future__ import annotations
from typing import Any, Dict, List, Optional
import aiohttp
import async_timeout
import logging

_LOGGER = logging.getLogger(__name__)

BASE = "/api/v1"

class VeoovibesApiError(Exception):
    pass

class VeoovibesClient:
    """Async client for Veoovibes HTTP API (documented command endpoints)."""

    def __init__(self, base_url: str, api_key: Optional[str], verify_ssl: bool, session: aiohttp.ClientSession):
        self._base = base_url.rstrip("/")
        self._api_key = api_key
        self._verify_ssl = verify_ssl
        self._session = session

    def _params(self, extra: Optional[dict] = None) -> Dict[str, Any]:
        p: Dict[str, Any] = {}
        if self._api_key:
            p["api_key"] = self._api_key
        if extra:
            p.update(extra)
        return p

    async def _get_cmd(self, cmd: str, params: Optional[dict] = None) -> Any:
        url = f"{self._base}{BASE}/{cmd}"
        try:
            async with async_timeout.timeout(15):
                async with self._session.get(url, params=self._params(params), ssl=self._verify_ssl) as resp:
                    resp.raise_for_status()
                    data = await resp.json()
            if data.get("status") != "succeeded" or str(data.get("code")) != "0":
                raise VeoovibesApiError(f"{cmd} failed: {data}")
            return data.get("result")
        except Exception as exc:
            raise VeoovibesApiError(f"{cmd} error: {exc}") from exc

    @staticmethod
    def _dict_result_to_list(d: Any) -> List[dict]:
        # listrooms -> result is an object: { "95": {...}, "91": {...} }
        if not isinstance(d, dict):
            return []
        out: List[dict] = []
        for key, val in d.items():
            if isinstance(val, dict):
                val.setdefault("key", key)
                out.append(val)
        return out

    # Discovery
    async def list_rooms(self) -> List[dict]:
        result = await self._get_cmd("listrooms")
        return self._dict_result_to_list(result)

    # Status
    async def get_room_status(self, room_id: str | int) -> dict:
        return await self._get_cmd("room_player_status", {"room": room_id})

    # Controls (room)
    async def play_room(self, room_id: str | int) -> None:
        await self._get_cmd("room_play", {"room": room_id})

    async def stop_room(self, room_id: str | int) -> None:
        await self._get_cmd("room_stop", {"room": room_id})

    async def next_room(self, room_id: str | int) -> None:
        await self._get_cmd("room_next", {"room": room_id})

    async def prev_room(self, room_id: str | int) -> None:
        await self._get_cmd("room_prev", {"room": room_id})

    async def set_room_volume(self, room_id: str | int, vol_0_100: int) -> None:
        vol = max(0, min(100, int(vol_0_100)))
        await self._get_cmd("room_vol_set", {"room": room_id, "vol": vol})
