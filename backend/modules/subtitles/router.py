"""Subtitles API — proxies to Bazarr."""

from fastapi import APIRouter, Depends, HTTPException

from backend.auth.permissions import require_admin, require_power_user
from backend.logging_config import get_logger
from backend.models.user import User
from backend.services.arr_client import bazarr_request

logger = get_logger("subtitles.router")

router = APIRouter(prefix="/subtitles", tags=["subtitles"])


@router.get("/status")
async def bazarr_status(user: User = Depends(require_power_user)):
    """Check Bazarr connection status."""
    try:
        resp = await bazarr_request("GET", "/api/system/status")
        if resp.status_code == 200:
            return {"connected": True, "data": resp.json()}
    except Exception:
        pass
    return {"connected": False}


@router.get("/profiles")
async def get_subtitle_profiles(user: User = Depends(require_power_user)):
    """Get subtitle language profiles from Bazarr."""
    try:
        resp = await bazarr_request("GET", "/api/system/languages/profiles")
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        logger.error("bazarr_profiles_fetch_failed", error=str(e))
    return []


@router.post("/profiles")
async def create_subtitle_profile(data: dict, user: User = Depends(require_admin)):
    """Create a subtitle profile in Bazarr."""
    resp = await bazarr_request("POST", "/api/system/languages/profiles", json=data)
    if resp.status_code in (200, 201):
        return resp.json()
    raise HTTPException(status_code=resp.status_code, detail="Failed to create profile")


@router.put("/profiles/{profile_id}")
async def update_subtitle_profile(profile_id: int, data: dict, user: User = Depends(require_admin)):
    """Update a subtitle profile in Bazarr."""
    resp = await bazarr_request("PUT", f"/api/system/languages/profiles/{profile_id}", json=data)
    if resp.status_code == 200:
        return resp.json()
    raise HTTPException(status_code=resp.status_code, detail="Failed to update profile")


@router.delete("/profiles/{profile_id}")
async def delete_subtitle_profile(profile_id: int, user: User = Depends(require_admin)):
    """Delete a subtitle profile from Bazarr."""
    resp = await bazarr_request("DELETE", f"/api/system/languages/profiles/{profile_id}")
    if resp.status_code == 200:
        return {"status": "deleted"}
    raise HTTPException(status_code=resp.status_code, detail="Failed to delete profile")


@router.get("/languages")
async def get_languages(user: User = Depends(require_power_user)):
    """Get available subtitle languages from Bazarr."""
    try:
        resp = await bazarr_request("GET", "/api/system/languages")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


@router.get("/providers")
async def get_providers(user: User = Depends(require_power_user)):
    """Get available subtitle providers from Bazarr."""
    try:
        resp = await bazarr_request("GET", "/api/providers")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


@router.get("/movies")
async def get_wanted_movies(user: User = Depends(require_power_user)):
    """Get movies wanting subtitles from Bazarr."""
    try:
        resp = await bazarr_request("GET", "/api/movies/wanted")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


@router.get("/series")
async def get_wanted_series(user: User = Depends(require_power_user)):
    """Get episodes wanting subtitles from Bazarr."""
    try:
        resp = await bazarr_request("GET", "/api/episodes/wanted")
        if resp.status_code == 200:
            return resp.json()
    except Exception:
        pass
    return []


@router.post("/search/{media_type}/{media_id}")
async def search_subtitles(
    media_type: str,
    media_id: int,
    language: str = "en",
    user: User = Depends(require_power_user),
):
    """Trigger a subtitle search in Bazarr."""
    if media_type == "movie":
        resp = await bazarr_request("POST", f"/api/movies/{media_id}/subtitles", json={
            "language": language,
            "forced": False,
            "hi": False,
        })
    else:
        resp = await bazarr_request("POST", f"/api/episodes/{media_id}/subtitles", json={
            "language": language,
            "forced": False,
            "hi": False,
        })

    if resp.status_code in (200, 201):
        return {"status": "search_triggered"}
    raise HTTPException(status_code=resp.status_code, detail="Subtitle search failed")
