"""Torznab/Newznab protocol client for querying indexers."""

import time
from xml.etree import ElementTree

import httpx

from backend.logging_config import get_logger
from backend.modules.indexers.schemas import SearchResult

logger = get_logger("indexer_protocol")

TORZNAB_NS = {"torznab": "http://torznab.com/schemas/2015/feed"}


async def search_torznab(
    url: str,
    api_key: str,
    query: str = "",
    categories: list[int] | None = None,
    imdb_id: str | None = None,
    tvdb_id: int | None = None,
    season: int | None = None,
    episode: int | None = None,
    indexer_name: str = "Unknown",
) -> tuple[list[SearchResult], float]:
    """Search a Torznab-compatible indexer. Returns results and response time in ms."""
    params: dict = {"apikey": api_key, "t": "search"}
    if query:
        params["q"] = query
    if categories:
        params["cat"] = ",".join(str(c) for c in categories)
    if imdb_id:
        params["imdbid"] = imdb_id
        params["t"] = "movie"
    if tvdb_id:
        params["tvdbid"] = str(tvdb_id)
        params["t"] = "tvsearch"
    if season is not None:
        params["season"] = str(season)
    if episode is not None:
        params["ep"] = str(episode)

    start = time.monotonic()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{url.rstrip('/')}/api", params=params)
        resp.raise_for_status()
    elapsed_ms = (time.monotonic() - start) * 1000

    results = _parse_torznab_response(resp.text, indexer_name)
    return results, elapsed_ms


async def search_newznab(
    url: str,
    api_key: str,
    query: str = "",
    categories: list[int] | None = None,
    indexer_name: str = "Unknown",
) -> tuple[list[SearchResult], float]:
    """Search a Newznab-compatible indexer."""
    params: dict = {"apikey": api_key, "t": "search", "o": "json"}
    if query:
        params["q"] = query
    if categories:
        params["cat"] = ",".join(str(c) for c in categories)

    start = time.monotonic()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{url.rstrip('/')}/api", params=params)
        resp.raise_for_status()
    elapsed_ms = (time.monotonic() - start) * 1000

    results = []
    try:
        data = resp.json()
        for item in data.get("channel", {}).get("item", []):
            attrs = {a["@name"]: a["@value"] for a in item.get("attr", []) if "@name" in a}
            results.append(SearchResult(
                title=item.get("title", ""),
                indexer=indexer_name,
                size_bytes=int(attrs.get("size", 0)),
                download_url=item.get("link", ""),
                seeders=None,
                leechers=None,
                age_days=None,
            ))
    except Exception:
        # Fallback: try XML
        results = _parse_torznab_response(resp.text, indexer_name)

    return results, elapsed_ms


def _parse_torznab_response(xml_text: str, indexer_name: str) -> list[SearchResult]:
    results = []
    try:
        root = ElementTree.fromstring(xml_text)
        for item in root.findall(".//item"):
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            size = 0
            seeders = None
            info_hash = None

            for attr in item.findall("torznab:attr", TORZNAB_NS):
                name = attr.get("name", "")
                value = attr.get("value", "")
                if name == "size":
                    size = int(value)
                elif name == "seeders":
                    seeders = int(value)
                elif name == "infohash":
                    info_hash = value

            # Fallback size from enclosure
            if not size:
                enc = item.find("enclosure")
                if enc is not None:
                    size = int(enc.get("length", 0))
                    if not link:
                        link = enc.get("url", "")

            results.append(SearchResult(
                title=title,
                indexer=indexer_name,
                size_bytes=size,
                download_url=link,
                info_hash=info_hash,
                seeders=seeders,
            ))
    except ElementTree.ParseError:
        logger.error("xml_parse_failed", indexer=indexer_name)
    return results
