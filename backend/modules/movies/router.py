"""Movies API — proxies to Radarr with data normalization."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.middleware import get_current_user
from backend.auth.permissions import require_admin, require_power_user
from backend.models.user import User
from backend.services.arr_client import radarr_request

router = APIRouter(prefix="/movies", tags=["movies"])


class MovieRequest(BaseModel):
    tmdb_id: int
    quality_profile_id: int | None = None
    root_folder_path: str = "/media/movies"


def _normalize_radarr_movie(m: dict) -> dict:
    """Transform a Radarr movie into the format the frontend expects."""
    # Extract poster URL from images array
    poster_url = None
    for img in m.get("images", []):
        if img.get("coverType") == "poster":
            remote = img.get("remoteUrl") or img.get("url", "")
            if remote:
                poster_url = remote
                break

    # Determine status
    if m.get("hasFile"):
        status = "available"
    elif m.get("isAvailable") and not m.get("hasFile"):
        status = "missing"
    elif m.get("monitored"):
        status = "monitored"
    else:
        status = "unmonitored"

    # Extract quality from movie file if available
    quality = None
    movie_file = m.get("movieFile")
    if movie_file:
        q = movie_file.get("quality", {}).get("quality", {})
        quality = q.get("name", "")
        resolution = q.get("resolution", "")
    else:
        resolution = None

    return {
        "id": m.get("id"),
        "tmdb_id": m.get("tmdbId"),
        "title": m.get("title", ""),
        "year": m.get("year"),
        "poster_url": poster_url,
        "rating": m.get("ratings", {}).get("tmdb", {}).get("value"),
        "status": status,
        "quality": quality,
        "resolution": resolution,
        "monitored": m.get("monitored", False),
        "has_file": m.get("hasFile", False),
        "size_on_disk": m.get("sizeOnDisk", 0),
        "overview": m.get("overview", ""),
    }


@router.get("")
async def list_movies(user: User = Depends(require_power_user)):
    """Get all movies from Radarr, normalized for the frontend."""
    resp = await radarr_request("GET", "/api/v3/movie")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch movies from Radarr")
    return [_normalize_radarr_movie(m) for m in resp.json()]


@router.post("")
async def request_movie(body: MovieRequest, user: User = Depends(require_power_user)):
    """Add a movie to Radarr and trigger search."""
    profile_id = body.quality_profile_id
    if not profile_id:
        profiles_resp = await radarr_request("GET", "/api/v3/qualityprofile")
        if profiles_resp.status_code == 200:
            profiles = profiles_resp.json()
            profile_id = profiles[0]["id"] if profiles else 1
        else:
            profile_id = 1

    # Lookup movie in Radarr via TMDB ID
    lookup_resp = await radarr_request("GET", "/api/v3/movie/lookup/tmdb", params={"tmdbId": body.tmdb_id})
    if lookup_resp.status_code != 200:
        raise HTTPException(status_code=404, detail="Movie not found on TMDB")
    movie_data = lookup_resp.json()

    # Add movie to Radarr with auto-search
    add_resp = await radarr_request("POST", "/api/v3/movie", json={
        "title": movie_data.get("title", ""),
        "tmdbId": body.tmdb_id,
        "year": movie_data.get("year", 0),
        "qualityProfileId": profile_id,
        "rootFolderPath": body.root_folder_path,
        "monitored": True,
        "addOptions": {"searchForMovie": True},
    })

    if add_resp.status_code in (200, 201):
        return {"status": "requested", "title": movie_data.get("title", "")}
    elif add_resp.status_code == 400:
        return {"status": "exists", "detail": add_resp.json()}
    else:
        raise HTTPException(status_code=add_resp.status_code, detail="Failed to add movie")


@router.get("/{movie_id}")
async def get_movie(movie_id: int, user: User = Depends(require_power_user)):
    resp = await radarr_request("GET", f"/api/v3/movie/{movie_id}")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Movie not found")
    return _normalize_radarr_movie(resp.json())


@router.delete("/{movie_id}")
async def delete_movie(
    movie_id: int,
    delete_files: bool = False,
    user: User = Depends(require_admin),
):
    resp = await radarr_request(
        "DELETE", f"/api/v3/movie/{movie_id}",
        params={"deleteFiles": str(delete_files).lower()},
    )
    if resp.status_code == 200:
        return {"status": "deleted"}
    raise HTTPException(status_code=resp.status_code, detail="Failed to delete movie")


@router.post("/{movie_id}/search")
async def search_movie(movie_id: int, user: User = Depends(require_power_user)):
    resp = await radarr_request("POST", "/api/v3/command", json={
        "name": "MoviesSearch",
        "movieIds": [movie_id],
    })
    if resp.status_code in (200, 201):
        return {"status": "search_triggered", "movie_id": movie_id}
    raise HTTPException(status_code=resp.status_code, detail="Failed to trigger search")


@router.get("/quality/profiles")
async def quality_profiles(user: User = Depends(require_power_user)):
    resp = await radarr_request("GET", "/api/v3/qualityprofile")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="Failed to fetch profiles")
    return resp.json()
