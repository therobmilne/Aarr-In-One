from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.middleware import get_current_user
from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.media import MediaStatus
from backend.models.user import User
from backend.modules.movies import service
from backend.modules.movies.schemas import MovieCreate, MovieResponse

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("/", response_model=list[MovieResponse])
async def list_movies(
    status: MediaStatus | None = None,
    monitored: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    movies = await service.list_movies(db, status, monitored, limit, offset)
    return [MovieResponse.model_validate(m) for m in movies]


@router.post("/", response_model=MovieResponse, status_code=201)
async def add_movie(
    body: MovieCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    movie = await service.add_movie(body, db)
    return MovieResponse.model_validate(movie)


@router.get("/{movie_id}", response_model=MovieResponse)
async def get_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    movie = await service.get_movie(movie_id, db)
    return MovieResponse.model_validate(movie)


@router.delete("/{movie_id}")
async def delete_movie(
    movie_id: int,
    delete_files: bool = False,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    await service.delete_movie(movie_id, db, delete_files)
    return {"status": "deleted"}


@router.post("/{movie_id}/search")
async def search_movie(
    movie_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    # TODO: Trigger indexer search for this movie
    return {"status": "search_triggered", "movie_id": movie_id}
