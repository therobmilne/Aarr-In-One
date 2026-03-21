"""Setup wizard service — handles first-run configuration and Jellyfin auto-setup."""

import secrets

import httpx

from backend.config import settings
from backend.logging_config import get_logger

logger = get_logger("setup")

# In-memory state for setup (persisted to DB on completion)
_setup_state = {
    "jellyfin_url": "",
    "jellyfin_api_key": "",
    "jellyfin_server_name": "",
    "tmdb_api_key": "",
    "admin_user_id": "",
    "is_complete": False,
}


def get_setup_state() -> dict:
    return _setup_state.copy()


def is_setup_complete() -> bool:
    return _setup_state["is_complete"] or settings.SETUP_COMPLETE


async def auto_detect_jellyfin() -> dict:
    """Try to connect to Jellyfin at the internal Docker URL."""
    urls_to_try = [
        settings.JELLYFIN_URL,
        "http://jellyfin:8096",
        "http://mediaforge-jellyfin:8096",
        "http://localhost:8096",
    ]

    for url in urls_to_try:
        if not url:
            continue
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{url}/System/Info/Public")
                if resp.status_code == 200:
                    data = resp.json()
                    return {
                        "success": True,
                        "url": url,
                        "server_name": data.get("ServerName", "Jellyfin"),
                        "version": data.get("Version", ""),
                    }
        except Exception:
            continue

    return {"success": False, "url": "", "server_name": "", "version": ""}


async def setup_jellyfin_connection(
    jellyfin_url: str, username: str, password: str
) -> dict:
    """Connect to Jellyfin, authenticate as admin, and create an API key for MediaForge."""
    url = jellyfin_url.rstrip("/")

    # Step 1: Authenticate with admin credentials
    auth_headers = {
        "Content-Type": "application/json",
        "X-Emby-Authorization": (
            'MediaBrowser Client="MediaForge", Device="Setup", '
            'DeviceId="mediaforge-setup", Version="0.1.0"'
        ),
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Authenticate
            auth_resp = await client.post(
                f"{url}/Users/AuthenticateByName",
                json={"Username": username, "Pw": password},
                headers=auth_headers,
            )

            if auth_resp.status_code == 401:
                return {"success": False, "message": "Invalid username or password"}
            if auth_resp.status_code != 200:
                return {"success": False, "message": f"Jellyfin returned {auth_resp.status_code}"}

            auth_data = auth_resp.json()
            access_token = auth_data.get("AccessToken", "")
            user_data = auth_data.get("User", {})
            is_admin = user_data.get("Policy", {}).get("IsAdministrator", False)

            if not is_admin:
                return {"success": False, "message": "User must be a Jellyfin administrator"}

            # Step 2: Create an API key for MediaForge
            api_headers = {"X-Emby-Token": access_token}

            # Check if MediaForge key already exists
            keys_resp = await client.get(f"{url}/Auth/Keys", headers=api_headers)
            existing_key = None
            if keys_resp.status_code == 200:
                keys_data = keys_resp.json()
                for key in keys_data.get("Items", []):
                    if key.get("AppName") == "MediaForge":
                        existing_key = key.get("AccessToken")
                        break

            if existing_key:
                api_key = existing_key
            else:
                # Create new API key
                create_resp = await client.post(
                    f"{url}/Auth/Keys",
                    params={"app": "MediaForge"},
                    headers=api_headers,
                )
                if create_resp.status_code not in (200, 204):
                    return {
                        "success": False,
                        "message": "Failed to create API key. Check admin permissions.",
                    }

                # Fetch the newly created key
                keys_resp = await client.get(f"{url}/Auth/Keys", headers=api_headers)
                api_key = ""
                if keys_resp.status_code == 200:
                    for key in keys_resp.json().get("Items", []):
                        if key.get("AppName") == "MediaForge":
                            api_key = key.get("AccessToken", "")
                            break

            if not api_key:
                return {"success": False, "message": "Created API key but couldn't retrieve it"}

            # Step 3: Get server info
            info_resp = await client.get(f"{url}/System/Info", headers=api_headers)
            server_name = ""
            version = ""
            if info_resp.status_code == 200:
                info_data = info_resp.json()
                server_name = info_data.get("ServerName", "Jellyfin")
                version = info_data.get("Version", "")

            # Save to state
            _setup_state["jellyfin_url"] = url
            _setup_state["jellyfin_api_key"] = api_key
            _setup_state["jellyfin_server_name"] = server_name
            _setup_state["admin_user_id"] = user_data.get("Id", "")

            logger.info("jellyfin_setup_complete", server=server_name, version=version)

            return {
                "success": True,
                "message": "Connected to Jellyfin and created API key",
                "jellyfin_url": url,
                "api_key": api_key,
                "server_name": server_name,
                "version": version,
            }

    except httpx.ConnectError:
        return {"success": False, "message": f"Cannot connect to {url}. Is Jellyfin running?"}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def validate_tmdb_key(api_key: str) -> dict:
    """Test a TMDB API key."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                "https://api.themoviedb.org/3/movie/550",
                params={"api_key": api_key},
            )
            if resp.status_code == 200:
                _setup_state["tmdb_api_key"] = api_key
                return {"success": True, "message": "TMDB API key is valid"}
            elif resp.status_code == 401:
                return {"success": False, "message": "Invalid TMDB API key"}
            else:
                return {"success": False, "message": f"TMDB returned {resp.status_code}"}
    except Exception as e:
        return {"success": False, "message": str(e)}


async def finalize_setup(db) -> dict:
    """Save all setup config to the database and mark setup as complete."""
    from backend.services.settings_service import set_setting

    await set_setting(db, "jellyfin_url", _setup_state["jellyfin_url"], "jellyfin")
    await set_setting(db, "jellyfin_api_key", _setup_state["jellyfin_api_key"], "jellyfin")
    await set_setting(db, "jellyfin_server_name", _setup_state["jellyfin_server_name"], "jellyfin")
    await set_setting(db, "tmdb_api_key", _setup_state["tmdb_api_key"], "tmdb")
    await set_setting(db, "setup_complete", True, "system")

    _setup_state["is_complete"] = True

    # Update runtime config
    settings.JELLYFIN_URL = _setup_state["jellyfin_url"]
    settings.JELLYFIN_API_KEY = _setup_state["jellyfin_api_key"]
    settings.TMDB_API_KEY = _setup_state["tmdb_api_key"]
    settings.SETUP_COMPLETE = True

    logger.info("setup_finalized")
    return {"success": True, "message": "Setup complete! MediaForge is ready."}
