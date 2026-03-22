import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.permissions import require_admin, require_power_user
from backend.database import get_db
from backend.models.user import User
from backend.modules.subtitles import service
from backend.modules.subtitles.schemas import (
    SubtitleProfileCreate,
    SubtitleProfileResponse,
    SubtitleProfileUpdate,
    SubtitleSearchResult,
)

router = APIRouter(prefix="/subtitles", tags=["subtitles"])


@router.get("/profiles", response_model=list[SubtitleProfileResponse])
async def list_profiles(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    profiles = await service.list_profiles(db)
    results = []
    for p in profiles:
        results.append(SubtitleProfileResponse(
            id=p.id,
            name=p.name,
            languages=json.loads(p.languages),
            min_score=p.min_score,
            providers=json.loads(p.providers),
            hearing_impaired=p.hearing_impaired,
            auto_download=p.auto_download,
            auto_upgrade=p.auto_upgrade,
            preferred_format=p.preferred_format,
            is_default=p.is_default,
        ))
    return results


@router.post("/profiles", response_model=SubtitleProfileResponse, status_code=201)
async def create_profile(
    body: SubtitleProfileCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    profile = await service.create_profile(body, db)
    return SubtitleProfileResponse(
        id=profile.id,
        name=profile.name,
        languages=json.loads(profile.languages),
        min_score=profile.min_score,
        providers=json.loads(profile.providers),
        hearing_impaired=profile.hearing_impaired,
        auto_download=profile.auto_download,
        auto_upgrade=profile.auto_upgrade,
        preferred_format=profile.preferred_format,
        is_default=profile.is_default,
    )


@router.put("/profiles/{profile_id}", response_model=SubtitleProfileResponse)
async def update_profile(
    profile_id: int,
    body: SubtitleProfileUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    profile = await service.update_profile(profile_id, body, db)
    return SubtitleProfileResponse(
        id=profile.id,
        name=profile.name,
        languages=json.loads(profile.languages),
        min_score=profile.min_score,
        providers=json.loads(profile.providers),
        hearing_impaired=profile.hearing_impaired,
        auto_download=profile.auto_download,
        auto_upgrade=profile.auto_upgrade,
        preferred_format=profile.preferred_format,
        is_default=profile.is_default,
    )


@router.delete("/profiles/{profile_id}")
async def delete_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    await service.delete_profile(profile_id, db)
    return {"status": "deleted"}


@router.post("/search/{media_id}", response_model=list[SubtitleSearchResult])
async def search_subtitles(
    media_id: int,
    languages: str = "en",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    # TODO: Look up media file path from movie/episode by ID
    return []


@router.post("/download/{media_id}")
async def download_subtitle(
    media_id: int,
    languages: str = "en",
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_power_user),
):
    # TODO: Look up media file path and trigger download
    return {"status": "triggered", "media_id": media_id}
