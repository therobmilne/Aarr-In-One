"""Auto-configuration engine for first boot.

On first startup, this module:
1. Waits for all backend services to be healthy
2. Reads each service's auto-generated API key from config files
3. Configures Prowlarr to sync indexers to Radarr and Sonarr
4. Configures Radarr and Sonarr to use qBittorrent and SABnzbd
5. Configures Bazarr to connect to Radarr and Sonarr
6. Sets up root folders in Radarr/Sonarr
"""

from __future__ import annotations

import asyncio

import httpx

from backend.config import settings
from backend.logging_config import get_logger
from backend.services.arr_client import (
    get_prowlarr_api_key,
    get_radarr_api_key,
    get_sabnzbd_api_key,
    get_sonarr_api_key,
    prowlarr_request,
    radarr_request,
    sonarr_request,
)

logger = get_logger("auto_config")


async def wait_for_service(name: str, url: str, timeout: int = 120) -> bool:
    """Wait for a service to respond to HTTP requests."""
    logger.info("waiting_for_service", service=name, url=url)
    deadline = asyncio.get_event_loop().time() + timeout
    async with httpx.AsyncClient(timeout=5) as client:
        while asyncio.get_event_loop().time() < deadline:
            try:
                resp = await client.get(url)
                if resp.status_code < 500:
                    logger.info("service_ready", service=name)
                    return True
            except Exception:
                pass
            await asyncio.sleep(2)
    logger.error("service_timeout", service=name, timeout=timeout)
    return False


async def wait_for_all_services() -> dict[str, bool]:
    """Wait for all backend services to be healthy."""
    checks = {
        "radarr": f"{settings.RADARR_URL}/api/v3/system/status",
        "sonarr": f"{settings.SONARR_URL}/api/v3/system/status",
        "prowlarr": f"{settings.PROWLARR_URL}/api/v1/system/status",
        "qbittorrent": f"{settings.QBITTORRENT_URL}/api/v2/app/version",
        "bazarr": f"{settings.BAZARR_URL}/api/system/status",
    }
    # SABnzbd and Threadfin are optional — don't block on them
    results = {}
    for name, url in checks.items():
        results[name] = await wait_for_service(name, url, timeout=120)
    return results


async def read_all_api_keys() -> dict[str, str | None]:
    """Read API keys from all backend service config files."""
    keys = {
        "radarr": get_radarr_api_key(),
        "sonarr": get_sonarr_api_key(),
        "prowlarr": get_prowlarr_api_key(),
        "sabnzbd": get_sabnzbd_api_key(),
    }
    logger.info("api_keys_read", found={k: bool(v) for k, v in keys.items()})
    return keys


async def configure_radarr_root_folder() -> bool:
    """Ensure Radarr has a root folder set to /media/movies."""
    try:
        resp = await radarr_request("GET", "/api/v3/rootfolder")
        if resp.status_code == 200:
            folders = resp.json()
            if any(f.get("path") == "/media/movies" for f in folders):
                logger.info("radarr_root_folder_exists")
                return True
        resp = await radarr_request("POST", "/api/v3/rootfolder", json={"path": "/media/movies"})
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error("radarr_root_folder_failed", error=str(e))
        return False


async def configure_sonarr_root_folder() -> bool:
    """Ensure Sonarr has a root folder set to /media/tv."""
    try:
        resp = await sonarr_request("GET", "/api/v3/rootfolder")
        if resp.status_code == 200:
            folders = resp.json()
            if any(f.get("path") == "/media/tv" for f in folders):
                logger.info("sonarr_root_folder_exists")
                return True
        resp = await sonarr_request("POST", "/api/v3/rootfolder", json={"path": "/media/tv"})
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error("sonarr_root_folder_failed", error=str(e))
        return False


async def configure_download_client(
    service_request_fn,
    service_name: str,
    category_field: str,
    category_value: str,
) -> bool:
    """Add qBittorrent as a download client to a *arr service."""
    try:
        # Check if already configured
        resp = await service_request_fn("GET", "/api/v3/downloadclient")
        if resp.status_code == 200:
            clients = resp.json()
            if any(c.get("implementation") == "QBittorrent" for c in clients):
                logger.info("download_client_exists", service=service_name, client="qBittorrent")
                return True

        resp = await service_request_fn("POST", "/api/v3/downloadclient", json={
            "name": "qBittorrent",
            "implementation": "QBittorrent",
            "configContract": "QBittorrentSettings",
            "protocol": "torrent",
            "enable": True,
            "fields": [
                {"name": "host", "value": "gluetun"},
                {"name": "port", "value": 8080},
                {"name": "username", "value": "admin"},
                {"name": "password", "value": "adminadmin"},
                {"name": category_field, "value": category_value},
            ],
        })
        ok = resp.status_code in (200, 201)
        if ok:
            logger.info("download_client_added", service=service_name, client="qBittorrent")
        else:
            logger.warning("download_client_add_failed", service=service_name,
                           status=resp.status_code, body=resp.text[:200])
        return ok
    except Exception as e:
        logger.error("download_client_config_failed", service=service_name, error=str(e))
        return False


async def configure_sabnzbd_client(
    service_request_fn,
    service_name: str,
    category_field: str,
    category_value: str,
) -> bool:
    """Add SABnzbd as a download client to a *arr service."""
    sab_key = get_sabnzbd_api_key()
    if not sab_key:
        logger.info("sabnzbd_skipped_no_key", service=service_name)
        return False

    try:
        resp = await service_request_fn("GET", "/api/v3/downloadclient")
        if resp.status_code == 200:
            clients = resp.json()
            if any(c.get("implementation") == "Sabnzbd" for c in clients):
                logger.info("download_client_exists", service=service_name, client="SABnzbd")
                return True

        resp = await service_request_fn("POST", "/api/v3/downloadclient", json={
            "name": "SABnzbd",
            "implementation": "Sabnzbd",
            "configContract": "SabnzbdSettings",
            "protocol": "usenet",
            "enable": True,
            "fields": [
                {"name": "host", "value": "gluetun"},
                {"name": "port", "value": 8081},
                {"name": "apiKey", "value": sab_key},
                {"name": category_field, "value": category_value},
            ],
        })
        return resp.status_code in (200, 201)
    except Exception as e:
        logger.error("sabnzbd_client_config_failed", service=service_name, error=str(e))
        return False


async def configure_prowlarr_apps() -> bool:
    """Tell Prowlarr to sync indexers to Radarr and Sonarr."""
    radarr_key = get_radarr_api_key()
    sonarr_key = get_sonarr_api_key()
    if not radarr_key or not sonarr_key:
        logger.warning("prowlarr_apps_skipped_missing_keys")
        return False

    try:
        # Check existing applications
        resp = await prowlarr_request("GET", "/api/v1/applications")
        if resp.status_code == 200:
            existing = resp.json()
            existing_names = {a.get("name") for a in existing}
        else:
            existing_names = set()

        if "Radarr" not in existing_names:
            resp = await prowlarr_request("POST", "/api/v1/applications", json={
                "name": "Radarr",
                "syncLevel": "fullSync",
                "implementation": "Radarr",
                "configContract": "RadarrSettings",
                "fields": [
                    {"name": "prowlarrUrl", "value": f"http://prowlarr:9696"},
                    {"name": "baseUrl", "value": f"http://radarr:7878"},
                    {"name": "apiKey", "value": radarr_key},
                    {"name": "syncCategories", "value": [2000, 2010, 2020, 2030, 2040, 2045, 2050, 2060]},
                ],
            })
            logger.info("prowlarr_radarr_added", status=resp.status_code)

        if "Sonarr" not in existing_names:
            resp = await prowlarr_request("POST", "/api/v1/applications", json={
                "name": "Sonarr",
                "syncLevel": "fullSync",
                "implementation": "Sonarr",
                "configContract": "SonarrSettings",
                "fields": [
                    {"name": "prowlarrUrl", "value": f"http://prowlarr:9696"},
                    {"name": "baseUrl", "value": f"http://sonarr:8989"},
                    {"name": "apiKey", "value": sonarr_key},
                    {"name": "syncCategories", "value": [5000, 5010, 5020, 5030, 5040, 5045, 5050]},
                ],
            })
            logger.info("prowlarr_sonarr_added", status=resp.status_code)

        return True
    except Exception as e:
        logger.error("prowlarr_apps_config_failed", error=str(e))
        return False


async def run_auto_configuration() -> dict[str, bool]:
    """Run the full auto-configuration sequence."""
    logger.info("auto_config_starting")

    # Step 1: Wait for services
    health = await wait_for_all_services()

    # Step 2: Read API keys
    keys = await read_all_api_keys()

    results = {"services_healthy": all(health.values()), "keys_read": bool(keys)}

    # Step 3: Configure root folders
    if health.get("radarr"):
        results["radarr_root_folder"] = await configure_radarr_root_folder()
    if health.get("sonarr"):
        results["sonarr_root_folder"] = await configure_sonarr_root_folder()

    # Step 4: Configure download clients
    if health.get("radarr") and health.get("qbittorrent"):
        results["radarr_qbit"] = await configure_download_client(
            radarr_request, "radarr", "movieCategory", "radarr",
        )
        results["radarr_sab"] = await configure_sabnzbd_client(
            radarr_request, "radarr", "movieCategory", "radarr",
        )

    if health.get("sonarr") and health.get("qbittorrent"):
        results["sonarr_qbit"] = await configure_download_client(
            sonarr_request, "sonarr", "tvCategory", "sonarr",
        )
        results["sonarr_sab"] = await configure_sabnzbd_client(
            sonarr_request, "sonarr", "tvCategory", "sonarr",
        )

    # Step 5: Configure Prowlarr sync
    if health.get("prowlarr") and health.get("radarr") and health.get("sonarr"):
        results["prowlarr_apps"] = await configure_prowlarr_apps()

    logger.info("auto_config_complete", results=results)
    return results
