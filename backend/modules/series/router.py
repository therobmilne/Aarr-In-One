"""TV Series API — proxies to Sonarr with data normalization."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.permissions import require_admin, require_power_user
from backend.models.user import User
from backend.services.arr_client import sonarr_request

router = APIRouter(prefix="/series", tags=["series"])


class SeriesRequest(BaseModel):
    tmdb_id: int
    quality_profile_id: int | None = None
    root_folder_path: str = "/media/tv"


def _normalize_sonarr_series(s: dict) -> dict:
    """Transform a Sonarr series into the format the frontend expects."""
    poster_url = None
    for img in s.get("images", []):
        if img.get("coverType") == "poster":
            remote = img.get("remoteUrl") or img.get("url", "")
            if remote:
                poster_url = remote
                break

    stats = s.get("statistics", {})
    episode_count = stats.get("episodeCount", 0)
    episode_file_count = stats.get("episodeFileCount", 0)

    if episode_file_count > 0 and episode_file_count >= episode_count:
        status = "available"
    elif episode_file_count > 0:
        status = "partial"
    elif s.get("monitored"):
        status = "missing"
    else:
        status = "unmonitored"

    # Build seasons list
    seasons = []
    for season in s.get("seasons", []):
        sn = season.get("seasonNumber", 0)
        s_stats = season.get("statistics", {})
        seasons.append({
            "season_number": sn,
            "episode_count": s_stats.get("totalEpisodeCount", 0),
            "episode_file_count": s_stats.get("episodeFileCount", 0),
            "monitored": season.get("monitored", False),
        })

    return {
        "id": s.get("id"),
        "tmdb_id": s.get("tmdbId") or s.get("tvdbId"),
        "tvdb_id": s.get("tvdbId"),
        "title": s.get("title", ""),
        "year": s.get("year"),
        "poster_url": poster_url,
        "rating": s.get("ratings", {}).get("value"),
        "status": status,
        "monitored": s.get("monitored", False),
        "season_count": stats.get("seasonCount", 0),
        "episode_count": episode_count,
        "episode_file_count": episode_file_count,
        "overview": s.get("overview", ""),
        "seasons": seasons,
    }


def _normalize_sonarr_episode(e: dict) -> dict:
    """Transform a Sonarr episode for the frontend."""
    quality = None
    if e.get("episodeFile"):
        q = e["episodeFile"].get("quality", {}).get("quality", {})
        quality = q.get("name", "")

    return {
        "id": e.get("id"),
        "episode_number": e.get("episodeNumber"),
        "season_number": e.get("seasonNumber"),
        "title": e.get("title", ""),
        "air_date": e.get("airDate", ""),
        "overview": e.get("overview", ""),
        "status": "available" if e.get("hasFile") else "missing",
        "quality": quality,
        "monitored": e.get("monitored", False),
    }


@router.get("")
async def list_series(user: User = Depends(require_power_user)):
    """Get all series from Sonarr, normalized for the frontend."""
    resp = await sonarr_request("GET", "/api/v3/series")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch series from Sonarr")
    return [_normalize_sonarr_series(s) for s in resp.json()]


@router.post("")
async def request_series(body: SeriesRequest, user: User = Depends(require_power_user)):
    """Add a TV series to Sonarr and trigger search."""
    profile_id = body.quality_profile_id
    if not profile_id:
        profiles_resp = await sonarr_request("GET", "/api/v3/qualityprofile")
        if profiles_resp.status_code == 200:
            profiles = profiles_resp.json()
            profile_id = profiles[0]["id"] if profiles else 1
        else:
            profile_id = 1

    lookup_resp = await sonarr_request(
        "GET", "/api/v3/series/lookup",
        params={"term": f"tmdb:{body.tmdb_id}"},
    )
    if lookup_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Series not found")

    lookup = lookup_resp.json()
    if not lookup:
        raise HTTPException(status_code=404, detail="Series not found in lookup")

    series_data = lookup[0]

    add_resp = await sonarr_request("POST", "/api/v3/series", json={
        "title": series_data.get("title", ""),
        "tvdbId": series_data.get("tvdbId"),
        "qualityProfileId": profile_id,
        "rootFolderPath": body.root_folder_path,
        "monitored": True,
        "seasonFolder": True,
        "addOptions": {
            "searchForMissingEpisodes": True,
            "searchForCutoffUnmetEpisodes": False,
        },
    })

    if add_resp.status_code in (200, 201):
        return {"status": "requested", "title": series_data.get("title", "")}
    elif add_resp.status_code == 400:
        return {"status": "exists", "detail": add_resp.json()}
    else:
        raise HTTPException(status_code=add_resp.status_code, detail="Failed to add series")


@router.get("/{series_id}")
async def get_series(series_id: int, user: User = Depends(require_power_user)):
    resp = await sonarr_request("GET", f"/api/v3/series/{series_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Series not found")
    return _normalize_sonarr_series(resp.json())


@router.get("/{series_id}/episodes")
async def get_episodes(series_id: int, season: int | None = None, user: User = Depends(require_power_user)):
    params = {"seriesId": series_id}
    if season is not None:
        params["seasonNumber"] = season
    resp = await sonarr_request("GET", "/api/v3/episode", params=params)
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch episodes")
    return [_normalize_sonarr_episode(e) for e in resp.json()]


@router.delete("/{series_id}")
async def delete_series(
    series_id: int,
    delete_files: bool = False,
    user: User = Depends(require_admin),
):
    resp = await sonarr_request(
        "DELETE", f"/api/v3/series/{series_id}",
        params={"deleteFiles": str(delete_files).lower()},
    )
    if resp.status_code == 200:
        return {"status": "deleted"}
    raise HTTPException(status_code=resp.status_code, detail="Failed to delete series")


@router.post("/{series_id}/search")
async def search_series(series_id: int, user: User = Depends(require_power_user)):
    resp = await sonarr_request("POST", "/api/v3/command", json={
        "name": "SeriesSearch",
        "seriesId": series_id,
    })
    if resp.status_code in (200, 201):
        return {"status": "search_triggered", "series_id": series_id}
    raise HTTPException(status_code=resp.status_code, detail="Failed to trigger search")


@router.get("/quality/profiles")
async def quality_profiles(user: User = Depends(require_power_user)):
    resp = await sonarr_request("GET", "/api/v3/qualityprofile")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch profiles")
    return resp.json()
