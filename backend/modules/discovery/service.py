import json

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.logging_config import get_logger
from backend.models.request import MediaRequest, RequestStatus
from backend.models.user import User
from backend.modules.discovery.schemas import RequestCreate, RequestResponse
from backend.websocket_manager import manager

logger = get_logger("discovery")


async def create_request(
    data: RequestCreate, user: User, db: AsyncSession
) -> MediaRequest:
    request = MediaRequest(
        type=data.type,
        tmdb_id=data.tmdb_id,
        tvdb_id=data.tvdb_id,
        title=data.title,
        year=data.year,
        poster_url=data.poster_url,
        requested_by_id=user.id,
        requested_seasons=json.dumps(data.requested_seasons) if data.requested_seasons else None,
    )

    # Auto-approve for trusted users
    if user.auto_approve:
        request.status = RequestStatus.APPROVED
        request.approved_by_id = user.id

    db.add(request)
    await db.flush()

    await manager.broadcast(
        "request:new",
        {"id": request.id, "title": data.title, "user": user.username},
    )

    logger.info("request_created", title=data.title, user=user.username, auto_approved=user.auto_approve)

    # If auto-approved, kick off the search/download pipeline
    if user.auto_approve:
        from backend.modules.media_pipeline import schedule_request_processing
        await schedule_request_processing(request.id)

    return request


async def approve_request(
    request_id: int, admin: User, db: AsyncSession
) -> MediaRequest:
    result = await db.execute(select(MediaRequest).where(MediaRequest.id == request_id))
    request = result.scalar_one_or_none()
    if not request:
        from backend.exceptions import NotFoundError

        raise NotFoundError("Request", request_id)

    request.status = RequestStatus.APPROVED
    request.approved_by_id = admin.id
    await db.flush()

    await manager.broadcast(
        "request:approved",
        {"id": request.id, "title": request.title},
    )

    # Kick off the search/download pipeline
    from backend.modules.media_pipeline import schedule_request_processing
    await schedule_request_processing(request.id)

    return request


async def deny_request(
    request_id: int, reason: str | None, admin: User, db: AsyncSession
) -> MediaRequest:
    result = await db.execute(select(MediaRequest).where(MediaRequest.id == request_id))
    request = result.scalar_one_or_none()
    if not request:
        from backend.exceptions import NotFoundError

        raise NotFoundError("Request", request_id)

    request.status = RequestStatus.DENIED
    request.approved_by_id = admin.id
    request.denied_reason = reason
    await db.flush()
    return request


async def list_requests(
    db: AsyncSession,
    status: RequestStatus | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[MediaRequest]:
    query = select(MediaRequest).order_by(MediaRequest.created_at.desc())
    if status:
        query = query.where(MediaRequest.status == status)
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_pending_count(db: AsyncSession) -> int:
    result = await db.execute(
        select(func.count(MediaRequest.id)).where(
            MediaRequest.status == RequestStatus.PENDING
        )
    )
    return result.scalar_one()
