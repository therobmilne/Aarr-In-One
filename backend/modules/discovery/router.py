from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.middleware import get_current_user
from backend.auth.permissions import require_admin, require_any_user
from backend.database import get_db
from backend.models.request import RequestStatus
from backend.models.user import User
from backend.modules.discovery import service
from backend.modules.discovery.schemas import (
    RequestCreate,
    RequestResponse,
    TMDBSearchResult,
)
from backend.modules.discovery.tmdb_client import tmdb_client

router = APIRouter(tags=["discovery"])


# --- TMDB Discovery ---

@router.get("/discover/search", response_model=list[TMDBSearchResult])
async def search_tmdb(
    q: str = Query(..., min_length=1),
    page: int = 1,
    user: User = Depends(require_any_user),
):
    return await tmdb_client.search_multi(q, page)


@router.get("/discover/trending", response_model=list[TMDBSearchResult])
async def get_trending(
    media_type: str = "all",
    time_window: str = "week",
    user: User = Depends(require_any_user),
):
    return await tmdb_client.get_trending(media_type, time_window)


@router.get("/discover/movies/popular", response_model=list[TMDBSearchResult])
async def popular_movies(page: int = 1, user: User = Depends(require_any_user)):
    return await tmdb_client.get_popular_movies(page)


@router.get("/discover/tv/popular", response_model=list[TMDBSearchResult])
async def popular_tv(page: int = 1, user: User = Depends(require_any_user)):
    return await tmdb_client.get_popular_tv(page)


@router.get("/discover/movies/upcoming", response_model=list[TMDBSearchResult])
async def upcoming_movies(page: int = 1, user: User = Depends(require_any_user)):
    return await tmdb_client.get_upcoming_movies(page)


# --- Requests ---

@router.get("/requests", response_model=list[RequestResponse])
async def list_requests(
    status: RequestStatus | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    requests = await service.list_requests(db, status, limit, offset)
    return [
        RequestResponse(
            id=r.id,
            type=r.type,
            status=r.status,
            tmdb_id=r.tmdb_id,
            title=r.title,
            year=r.year,
            poster_url=r.poster_url,
            requested_by=user.username,
            created_at=r.created_at.isoformat() if r.created_at else "",
        )
        for r in requests
    ]


@router.post("/requests", response_model=RequestResponse, status_code=201)
async def create_request(
    body: RequestCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_any_user),
):
    request = await service.create_request(body, user, db)
    return RequestResponse(
        id=request.id,
        type=request.type,
        status=request.status,
        tmdb_id=request.tmdb_id,
        title=request.title,
        year=request.year,
        poster_url=request.poster_url,
        requested_by=user.username,
        created_at=request.created_at.isoformat() if request.created_at else "",
    )


@router.put("/requests/{request_id}/approve")
async def approve_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    req = await service.approve_request(request_id, user, db)
    return {"status": "approved", "id": req.id}


@router.put("/requests/{request_id}/deny")
async def deny_request(
    request_id: int,
    reason: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    req = await service.deny_request(request_id, reason, user, db)
    return {"status": "denied", "id": req.id}
