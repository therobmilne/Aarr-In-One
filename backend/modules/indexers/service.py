import asyncio
import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import NotFoundError
from backend.logging_config import get_logger
from backend.models.indexer import Indexer, IndexerStatus, IndexerType
from backend.modules.indexers.protocols import search_newznab, search_torznab
from backend.modules.indexers.schemas import IndexerCreate, IndexerTestResult, SearchResult

logger = get_logger("indexers")


async def add_indexer(data: IndexerCreate, db: AsyncSession) -> Indexer:
    indexer = Indexer(
        name=data.name,
        type=data.type,
        url=data.url,
        api_key=data.api_key,
        enabled=data.enabled,
        priority=data.priority,
        categories=json.dumps(data.categories) if data.categories else None,
        tags=json.dumps(data.tags) if data.tags else None,
    )
    db.add(indexer)
    await db.flush()
    logger.info("indexer_added", name=indexer.name, type=indexer.type)
    return indexer


async def list_indexers(db: AsyncSession) -> list[Indexer]:
    result = await db.execute(select(Indexer).order_by(Indexer.priority))
    return list(result.scalars().all())


async def get_indexer(indexer_id: int, db: AsyncSession) -> Indexer:
    result = await db.execute(select(Indexer).where(Indexer.id == indexer_id))
    indexer = result.scalar_one_or_none()
    if not indexer:
        raise NotFoundError("Indexer", indexer_id)
    return indexer


async def delete_indexer(indexer_id: int, db: AsyncSession) -> None:
    indexer = await get_indexer(indexer_id, db)
    await db.delete(indexer)


async def test_indexer(indexer_id: int, db: AsyncSession) -> IndexerTestResult:
    indexer = await get_indexer(indexer_id, db)
    try:
        search_fn = search_torznab if indexer.type == IndexerType.TORZNAB else search_newznab
        _, elapsed = await search_fn(
            url=indexer.url,
            api_key=indexer.api_key or "",
            query="test",
            indexer_name=indexer.name,
        )
        indexer.status = IndexerStatus.HEALTHY
        indexer.consecutive_failures = 0
        indexer.average_response_ms = elapsed
        return IndexerTestResult(success=True, message="OK", response_time_ms=elapsed)
    except Exception as e:
        indexer.consecutive_failures += 1
        if indexer.consecutive_failures >= 5:
            indexer.status = IndexerStatus.FAILED
        else:
            indexer.status = IndexerStatus.WARNING
        return IndexerTestResult(success=False, message=str(e))


async def search_all_indexers(
    db: AsyncSession,
    query: str = "",
    categories: list[int] | None = None,
    imdb_id: str | None = None,
    tvdb_id: int | None = None,
) -> list[SearchResult]:
    """Search across all enabled indexers in parallel."""
    result = await db.execute(
        select(Indexer).where(Indexer.enabled == True, Indexer.status != IndexerStatus.FAILED)
    )
    indexers = list(result.scalars().all())

    async def _search_one(indexer: Indexer) -> list[SearchResult]:
        try:
            if indexer.type == IndexerType.TORZNAB:
                results, elapsed = await search_torznab(
                    url=indexer.url,
                    api_key=indexer.api_key or "",
                    query=query,
                    categories=categories,
                    imdb_id=imdb_id,
                    tvdb_id=tvdb_id,
                    indexer_name=indexer.name,
                )
            else:
                results, elapsed = await search_newznab(
                    url=indexer.url,
                    api_key=indexer.api_key or "",
                    query=query,
                    categories=categories,
                    indexer_name=indexer.name,
                )
            indexer.total_queries += 1
            indexer.average_response_ms = (
                indexer.average_response_ms * 0.9 + elapsed * 0.1
            )
            return results
        except Exception as e:
            logger.warning("indexer_search_failed", indexer=indexer.name, error=str(e))
            indexer.consecutive_failures += 1
            return []

    all_results = await asyncio.gather(*[_search_one(i) for i in indexers])
    combined = [r for results in all_results for r in results]
    # Sort by seeders (descending) for torrents
    combined.sort(key=lambda r: r.seeders or 0, reverse=True)
    return combined
