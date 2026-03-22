"""Centralized HTTP client for communicating with all backend arr services.

Provides helper methods for reading API keys from service config files
and making authenticated requests to Radarr, Sonarr, Prowlarr, qBittorrent,
SABnzbd, Bazarr, Gluetun, and Threadfin.
"""

from __future__ import annotations

import configparser
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

import httpx

from backend.config import settings
from backend.logging_config import get_logger

logger = get_logger("arr_client")

# Cached API keys (populated on first boot / auto-config)
_api_keys: dict[str, str] = {}

# qBittorrent session cookie
_qbit_cookie: str | None = None


# ------------------------------------------------------------------
# API Key Reading
# ------------------------------------------------------------------

def _read_xml_api_key(config_path: str) -> str | None:
    """Read an API key from an *arr app's config.xml."""
    path = Path(config_path)
    if not path.exists():
        return None
    try:
        tree = ET.parse(path)
        node = tree.find(".//ApiKey")
        return node.text if node is not None else None
    except Exception as e:
        logger.warning("xml_api_key_read_failed", path=config_path, error=str(e))
        return None


def get_radarr_api_key() -> str | None:
    if "radarr" in _api_keys:
        return _api_keys["radarr"]
    key = _read_xml_api_key("/config/radarr/config.xml")
    if key:
        _api_keys["radarr"] = key
    return key


def get_sonarr_api_key() -> str | None:
    if "sonarr" in _api_keys:
        return _api_keys["sonarr"]
    key = _read_xml_api_key("/config/sonarr/config.xml")
    if key:
        _api_keys["sonarr"] = key
    return key


def get_prowlarr_api_key() -> str | None:
    if "prowlarr" in _api_keys:
        return _api_keys["prowlarr"]
    key = _read_xml_api_key("/config/prowlarr/config.xml")
    if key:
        _api_keys["prowlarr"] = key
    return key


def get_bazarr_api_key() -> str | None:
    if "bazarr" in _api_keys:
        return _api_keys["bazarr"]
    # Bazarr stores its API key in config/config/config.yaml or the DB
    # Try reading from the config.xml-like path first, then fall back
    key = _read_xml_api_key("/config/bazarr/config.xml")
    if key:
        _api_keys["bazarr"] = key
        return key
    # Bazarr uses a config.ini or config.yaml — try config.ini
    ini_path = Path("/config/bazarr/config/config.ini")
    if ini_path.exists():
        try:
            cfg = configparser.ConfigParser()
            cfg.read(str(ini_path))
            key = cfg.get("auth", "apikey", fallback=None)
            if key:
                _api_keys["bazarr"] = key
                return key
        except Exception:
            pass
    return None


def get_sabnzbd_api_key() -> str | None:
    if "sabnzbd" in _api_keys:
        return _api_keys["sabnzbd"]
    ini_path = Path("/config/sabnzbd/sabnzbd.ini")
    if not ini_path.exists():
        return None
    try:
        cfg = configparser.ConfigParser()
        cfg.read(str(ini_path))
        key = cfg.get("misc", "api_key", fallback=None)
        if key:
            _api_keys["sabnzbd"] = key
        return key
    except Exception as e:
        logger.warning("sabnzbd_key_read_failed", error=str(e))
        return None


def get_stored_api_key(service: str) -> str | None:
    """Get a cached API key by service name."""
    readers = {
        "radarr": get_radarr_api_key,
        "sonarr": get_sonarr_api_key,
        "prowlarr": get_prowlarr_api_key,
        "bazarr": get_bazarr_api_key,
        "sabnzbd": get_sabnzbd_api_key,
    }
    reader = readers.get(service)
    if reader:
        return reader()
    return _api_keys.get(service)


def set_api_key(service: str, key: str) -> None:
    """Manually set an API key (e.g. after auto-config discovers it)."""
    _api_keys[service] = key


def clear_api_keys() -> None:
    """Clear all cached API keys (for testing)."""
    _api_keys.clear()


# ------------------------------------------------------------------
# HTTP Helpers
# ------------------------------------------------------------------

async def arr_request(
    method: str,
    service_url: str,
    path: str,
    api_key: str | None = None,
    json: Any = None,
    params: dict | None = None,
    timeout: float = 15.0,
) -> httpx.Response:
    """Make an authenticated request to an *arr service."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-Api-Key"] = api_key

    url = f"{service_url.rstrip('/')}{path}"
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.request(
            method, url, headers=headers, json=json, params=params,
        )
        return resp


async def radarr_request(method: str, path: str, **kwargs) -> httpx.Response:
    key = get_radarr_api_key()
    return await arr_request(method, settings.RADARR_URL, path, api_key=key, **kwargs)


async def sonarr_request(method: str, path: str, **kwargs) -> httpx.Response:
    key = get_sonarr_api_key()
    return await arr_request(method, settings.SONARR_URL, path, api_key=key, **kwargs)


async def prowlarr_request(method: str, path: str, **kwargs) -> httpx.Response:
    key = get_prowlarr_api_key()
    return await arr_request(method, settings.PROWLARR_URL, path, api_key=key, **kwargs)


async def bazarr_request(method: str, path: str, **kwargs) -> httpx.Response:
    key = get_bazarr_api_key()
    return await arr_request(method, settings.BAZARR_URL, path, api_key=key, **kwargs)


# ------------------------------------------------------------------
# qBittorrent (session-cookie based auth)
# ------------------------------------------------------------------

async def qbit_login() -> str | None:
    """Log in to qBittorrent and return the session cookie."""
    global _qbit_cookie
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{settings.QBITTORRENT_URL}/api/v2/auth/login",
                data={"username": "admin", "password": "adminadmin"},
            )
            if resp.status_code == 200 and "SID" in resp.cookies:
                _qbit_cookie = resp.cookies["SID"]
                return _qbit_cookie
    except Exception as e:
        logger.warning("qbit_login_failed", error=str(e))
    return None


async def qbit_request(method: str, path: str, **kwargs) -> httpx.Response:
    """Make a request to qBittorrent's WebUI API."""
    global _qbit_cookie
    if not _qbit_cookie:
        await qbit_login()

    url = f"{settings.QBITTORRENT_URL}{path}"
    cookies = {"SID": _qbit_cookie} if _qbit_cookie else {}

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.request(method, url, cookies=cookies, **kwargs)
        # Re-auth on 403
        if resp.status_code == 403:
            await qbit_login()
            cookies = {"SID": _qbit_cookie} if _qbit_cookie else {}
            resp = await client.request(method, url, cookies=cookies, **kwargs)
        return resp


# ------------------------------------------------------------------
# SABnzbd (API key based)
# ------------------------------------------------------------------

async def sabnzbd_request(mode: str, extra_params: dict | None = None) -> dict:
    """Make a request to SABnzbd's API."""
    key = get_sabnzbd_api_key()
    params = {"mode": mode, "output": "json"}
    if key:
        params["apikey"] = key
    if extra_params:
        params.update(extra_params)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{settings.SABNZBD_URL}/api", params=params)
        if resp.status_code == 200:
            return resp.json()
        return {}


# ------------------------------------------------------------------
# Gluetun
# ------------------------------------------------------------------

async def gluetun_request(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{settings.GLUETUN_URL}{path}"
    async with httpx.AsyncClient(timeout=10) as client:
        return await client.request(method, url, **kwargs)


# ------------------------------------------------------------------
# Threadfin
# ------------------------------------------------------------------

async def threadfin_request(method: str, path: str, **kwargs) -> httpx.Response:
    url = f"{settings.THREADFIN_URL}{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        return await client.request(method, url, **kwargs)
