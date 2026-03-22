from __future__ import annotations

from typing import Any

import httpx

from backend.logging_config import get_logger

logger = get_logger("iptv.xtream")


class XtreamClient:
    """Async client for the Xtream Codes IPTV API."""

    def __init__(self, server_url: str, username: str, password: str) -> None:
        # Normalise the server URL: strip trailing slash, ensure no trailing path
        self.server_url = server_url.rstrip("/")
        self.username = username
        self.password = password
        self._timeout = httpx.Timeout(60.0, connect=15.0)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _base_params(self) -> dict[str, str]:
        return {"username": self.username, "password": self.password}

    def _api_url(self) -> str:
        return f"{self.server_url}/player_api.php"

    async def _request(self, action: str | None = None) -> Any:
        """Make a GET request to the Xtream API and return parsed JSON."""
        params = self._base_params()
        if action:
            params["action"] = action

        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            try:
                resp = await client.get(self._api_url(), params=params)
                resp.raise_for_status()
                return resp.json()
            except httpx.TimeoutException:
                logger.error("xtream_timeout", action=action, url=self.server_url)
                raise ConnectionError(f"Timeout connecting to IPTV provider ({action or 'auth'})")
            except httpx.HTTPStatusError as exc:
                logger.error("xtream_http_error", action=action, status=exc.response.status_code)
                raise ConnectionError(
                    f"IPTV provider returned HTTP {exc.response.status_code} for {action or 'auth'}"
                )
            except httpx.RequestError as exc:
                logger.error("xtream_request_error", action=action, error=str(exc))
                raise ConnectionError(f"Cannot reach IPTV provider: {exc}")
            except Exception as exc:
                logger.error("xtream_unexpected_error", action=action, error=str(exc))
                raise ConnectionError(f"Unexpected error from IPTV provider: {exc}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def test_connection(self) -> dict[str, Any]:
        """Authenticate with the provider and return account info.

        Returns the raw JSON dict from the provider which typically contains
        ``user_info`` and ``server_info`` keys.  Raises ``ConnectionError``
        on failure.
        """
        data = await self._request()  # no action = auth / server info
        if isinstance(data, dict) and data.get("user_info"):
            user_info = data["user_info"]
            if user_info.get("auth") == 0:
                raise ConnectionError("Authentication failed: invalid credentials")
            logger.info("xtream_auth_ok", username=self.username)
            return data
        raise ConnectionError("Unexpected response from provider during authentication")

    async def get_live_categories(self) -> list[dict[str, Any]]:
        data = await self._request("get_live_categories")
        return data if isinstance(data, list) else []

    async def get_live_channels(self) -> list[dict[str, Any]]:
        data = await self._request("get_live_streams")
        return data if isinstance(data, list) else []

    async def get_vod_categories(self) -> list[dict[str, Any]]:
        data = await self._request("get_vod_categories")
        return data if isinstance(data, list) else []

    async def get_vod_movies(self) -> list[dict[str, Any]]:
        data = await self._request("get_vod_streams")
        return data if isinstance(data, list) else []

    async def get_series_categories(self) -> list[dict[str, Any]]:
        data = await self._request("get_series_categories")
        return data if isinstance(data, list) else []

    async def get_vod_series(self) -> list[dict[str, Any]]:
        data = await self._request("get_series")
        return data if isinstance(data, list) else []

    def generate_stream_url(self, stream_id: int | str, stream_type: str = "movie") -> str:
        """Build the direct stream URL for a given stream.

        ``stream_type`` should be one of: ``movie``, ``series``, ``live``.
        """
        ext_map = {
            "movie": "mp4",
            "series": "mp4",
            "live": "ts",
        }
        ext = ext_map.get(stream_type, "mp4")
        return f"{self.server_url}/{stream_type}/{self.username}/{self.password}/{stream_id}.{ext}"
