from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.user import User
from backend.modules.indexers import service
from backend.modules.indexers.schemas import (
    IndexerCreate,
    IndexerResponse,
    IndexerTestResult,
    SearchResult,
)

router = APIRouter(prefix="/indexers", tags=["indexers"])


@router.get("/", response_model=list[IndexerResponse])
async def list_indexers(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    indexers = await service.list_indexers(db)
    return [IndexerResponse.model_validate(i) for i in indexers]


@router.post("/", response_model=IndexerResponse, status_code=201)
async def add_indexer(
    body: IndexerCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    indexer = await service.add_indexer(body, db)
    return IndexerResponse.model_validate(indexer)


@router.delete("/{indexer_id}")
async def delete_indexer(
    indexer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    await service.delete_indexer(indexer_id, db)
    return {"status": "deleted"}


@router.post("/{indexer_id}/test", response_model=IndexerTestResult)
async def test_indexer(
    indexer_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    return await service.test_indexer(indexer_id, db)


@router.get("/search", response_model=list[SearchResult])
async def search_indexers(
    q: str = Query("", description="Search query"),
    categories: str | None = Query(None, description="Comma-separated category IDs"),
    imdb_id: str | None = None,
    tvdb_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    cats = [int(c) for c in categories.split(",")] if categories else None
    return await service.search_all_indexers(db, q, cats, imdb_id, tvdb_id)


@router.get("/bypass/status")
async def cloudflare_bypass_status(user: User = Depends(require_power_user)):
    """Check Cloudflare bypass engine status."""
    from backend.modules.indexers.cloudflare_bypass import get_cache_status
    return get_cache_status()
