from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.user import User
from backend.modules.series import service
from backend.modules.series.schemas import EpisodeResponse, SeriesCreate, SeriesResponse

router = APIRouter(prefix="/series", tags=["series"])


@router.get("", response_model=list[SeriesResponse])
async def list_series(
    monitored: bool | None = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    items = await service.list_series(db, monitored, limit, offset)
    return [SeriesResponse.model_validate(s) for s in items]


@router.post("", response_model=SeriesResponse, status_code=201)
async def add_series(
    body: SeriesCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    s = await service.add_series(body, db)
    return SeriesResponse.model_validate(s)


@router.get("/{series_id}", response_model=SeriesResponse)
async def get_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    s = await service.get_series(series_id, db)
    return SeriesResponse.model_validate(s)


@router.get("/{series_id}/episodes", response_model=list[EpisodeResponse])
async def get_episodes(
    series_id: int,
    season: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    episodes = await service.get_episodes(series_id, season, db)
    return [
        EpisodeResponse(
            id=e.id,
            season_number=e.season.season_number if hasattr(e, "season") and e.season else 0,
            episode_number=e.episode_number,
            absolute_number=e.absolute_number,
            title=e.title,
            air_date=e.air_date,
            status=e.status,
            monitored=e.monitored,
            file_path=e.file_path,
            quality=e.quality,
        )
        for e in episodes
    ]


@router.delete("/{series_id}")
async def delete_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    await service.delete_series(series_id, db)
    return {"status": "deleted"}


@router.post("/{series_id}/search")
async def search_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    return {"status": "search_triggered", "series_id": series_id}
