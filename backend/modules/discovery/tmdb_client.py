from typing import Any

import httpx

from backend.config import settings
from backend.logging_config import get_logger
from backend.modules.discovery.schemas import TMDBSearchResult

logger = get_logger("tmdb")

TMDB_BASE = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p"


class TMDBClient:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=TMDB_BASE,
                params={"api_key": settings.TMDB_API_KEY},
                timeout=15.0,
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _get(self, path: str, **params) -> Any:
        client = await self._get_client()
        resp = await client.get(path, params=params)
        resp.raise_for_status()
        return resp.json()

    def _parse_result(self, item: dict, media_type: str = "") -> TMDBSearchResult:
        mt = media_type or item.get("media_type", "movie")
        is_tv = mt == "tv"
        title = item.get("name" if is_tv else "title", "")
        date = item.get("first_air_date" if is_tv else "release_date", "")
        year = int(date[:4]) if date and len(date) >= 4 else None
        poster = item.get("poster_path")
        backdrop = item.get("backdrop_path")

        return TMDBSearchResult(
            tmdb_id=item.get("id", 0),
            title=title,
            original_title=item.get("original_name" if is_tv else "original_title"),
            year=year,
            overview=item.get("overview"),
            poster_url=f"{TMDB_IMAGE_BASE}/w500{poster}" if poster else None,
            backdrop_url=f"{TMDB_IMAGE_BASE}/w1280{backdrop}" if backdrop else None,
            rating=item.get("vote_average"),
            media_type=mt,
        )

    async def search_multi(self, query: str, page: int = 1) -> list[TMDBSearchResult]:
        data = await self._get("/search/multi", query=query, page=page)
        return [
            self._parse_result(item)
            for item in data.get("results", [])
            if item.get("media_type") in ("movie", "tv")
        ]

    async def search_movies(self, query: str, page: int = 1) -> list[TMDBSearchResult]:
        data = await self._get("/search/movie", query=query, page=page)
        return [self._parse_result(item, "movie") for item in data.get("results", [])]

    async def search_tv(self, query: str, page: int = 1) -> list[TMDBSearchResult]:
        data = await self._get("/search/tv", query=query, page=page)
        return [self._parse_result(item, "tv") for item in data.get("results", [])]

    async def get_trending(
        self, media_type: str = "all", time_window: str = "week"
    ) -> list[TMDBSearchResult]:
        data = await self._get(f"/trending/{media_type}/{time_window}")
        return [self._parse_result(item) for item in data.get("results", [])]

    async def get_movie_details(self, tmdb_id: int) -> dict:
        return await self._get(f"/movie/{tmdb_id}", append_to_response="credits,videos")

    async def get_tv_details(self, tmdb_id: int) -> dict:
        return await self._get(f"/tv/{tmdb_id}", append_to_response="credits,external_ids")

    async def get_popular_movies(self, page: int = 1) -> list[TMDBSearchResult]:
        data = await self._get("/movie/popular", page=page)
        return [self._parse_result(item, "movie") for item in data.get("results", [])]

    async def get_popular_tv(self, page: int = 1) -> list[TMDBSearchResult]:
        data = await self._get("/tv/popular", page=page)
        return [self._parse_result(item, "tv") for item in data.get("results", [])]

    async def get_upcoming_movies(self, page: int = 1) -> list[TMDBSearchResult]:
        data = await self._get("/movie/upcoming", page=page)
        return [self._parse_result(item, "movie") for item in data.get("results", [])]


tmdb_client = TMDBClient()
