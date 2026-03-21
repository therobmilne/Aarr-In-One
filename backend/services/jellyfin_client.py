from typing import Any

import httpx

from backend.config import settings
from backend.exceptions import ExternalServiceError
from backend.logging_config import get_logger

logger = get_logger("jellyfin")


class JellyfinClient:
    def __init__(self, url: str = "", api_key: str = ""):
        self.url = (url or settings.JELLYFIN_URL).rstrip("/")
        self.api_key = api_key or settings.JELLYFIN_API_KEY
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.url,
                headers={"X-Emby-Token": self.api_key},
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        client = await self._get_client()
        try:
            resp = await client.request(method, path, **kwargs)
            resp.raise_for_status()
            return resp.json() if resp.content else None
        except httpx.RequestError as e:
            raise ExternalServiceError("Jellyfin", f"Connection error: {e}")
        except httpx.HTTPStatusError as e:
            raise ExternalServiceError("Jellyfin", f"HTTP {e.response.status_code}: {e}")

    async def test_connection(self) -> dict:
        return await self._request("GET", "/System/Info")

    async def get_users(self) -> list[dict]:
        return await self._request("GET", "/Users")

    async def get_libraries(self) -> list[dict]:
        data = await self._request("GET", "/Library/MediaFolders")
        return data.get("Items", [])

    async def get_items(
        self,
        parent_id: str,
        include_type: str = "",
        start_index: int = 0,
        limit: int = 50,
    ) -> dict:
        params = {
            "ParentId": parent_id,
            "StartIndex": start_index,
            "Limit": limit,
            "Recursive": "true",
            "Fields": "Path,MediaSources,Overview",
        }
        if include_type:
            params["IncludeItemTypes"] = include_type
        return await self._request("GET", "/Items", params=params)

    async def refresh_library(self) -> None:
        await self._request("POST", "/Library/Refresh")

    async def get_system_info(self) -> dict:
        return await self._request("GET", "/System/Info")


jellyfin_client = JellyfinClient()
