"""Subtitle engine using subliminal library for multi-provider search."""

import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.exceptions import NotFoundError
from backend.logging_config import get_logger
from backend.models.subtitle import SubtitleProfile
from backend.modules.subtitles.schemas import SubtitleProfileCreate, SubtitleProfileUpdate, SubtitleSearchResult

logger = get_logger("subtitles")

# Try importing subliminal
try:
    import subliminal
    from babelfish import Language

    HAS_SUBLIMINAL = True
except ImportError:
    HAS_SUBLIMINAL = False
    logger.warning("subliminal_not_available", msg="Install subliminal for subtitle support")


async def create_profile(data: SubtitleProfileCreate, db: AsyncSession) -> SubtitleProfile:
    profile = SubtitleProfile(
        name=data.name,
        languages=json.dumps(data.languages),
        min_score=data.min_score,
        providers=json.dumps(data.providers),
        hearing_impaired=data.hearing_impaired,
        auto_download=data.auto_download,
        auto_upgrade=data.auto_upgrade,
        preferred_format=data.preferred_format,
        is_default=data.is_default,
    )
    db.add(profile)
    await db.flush()
    return profile


async def list_profiles(db: AsyncSession) -> list[SubtitleProfile]:
    result = await db.execute(select(SubtitleProfile).order_by(SubtitleProfile.name))
    return list(result.scalars().all())


async def get_profile(profile_id: int, db: AsyncSession) -> SubtitleProfile:
    result = await db.execute(select(SubtitleProfile).where(SubtitleProfile.id == profile_id))
    profile = result.scalar_one_or_none()
    if not profile:
        raise NotFoundError("SubtitleProfile", profile_id)
    return profile


async def update_profile(profile_id: int, data: SubtitleProfileUpdate, db: AsyncSession) -> SubtitleProfile:
    profile = await get_profile(profile_id, db)
    if data.name is not None:
        profile.name = data.name
    if data.languages is not None:
        profile.languages = json.dumps(data.languages)
    if data.min_score is not None:
        profile.min_score = data.min_score
    if data.providers is not None:
        profile.providers = json.dumps(data.providers)
    if data.hearing_impaired is not None:
        profile.hearing_impaired = data.hearing_impaired
    if data.auto_download is not None:
        profile.auto_download = data.auto_download
    if data.auto_upgrade is not None:
        profile.auto_upgrade = data.auto_upgrade
    if data.preferred_format is not None:
        profile.preferred_format = data.preferred_format
    if data.is_default is not None:
        profile.is_default = data.is_default
    await db.flush()
    return profile


async def delete_profile(profile_id: int, db: AsyncSession) -> None:
    profile = await get_profile(profile_id, db)
    await db.delete(profile)


async def search_subtitles(
    file_path: str,
    languages: list[str],
    providers: list[str] | None = None,
) -> list[SubtitleSearchResult]:
    """Search for subtitles for a given video file."""
    if not HAS_SUBLIMINAL:
        return []

    path = Path(file_path)
    if not path.exists():
        return []

    video = subliminal.scan_video(str(path))
    lang_set = {Language.fromalpha2(lang) for lang in languages}

    provider_list = providers or ["opensubtitles", "podnapisi", "addic7ed"]

    try:
        subs = subliminal.list_subtitles(
            {video},
            lang_set,
            providers=provider_list,
        )
    except Exception as e:
        logger.error("subtitle_search_failed", error=str(e), file=file_path)
        return []

    results = []
    for sub in subs.get(video, []):
        score = subliminal.compute_score(sub, video)
        results.append(SubtitleSearchResult(
            provider=sub.provider_name,
            title=getattr(sub, "release", "") or getattr(sub, "id", ""),
            language=str(sub.language),
            score=score,
            hearing_impaired=getattr(sub, "hearing_impaired", False),
            download_url="",  # subliminal handles downloads internally
            hash_match=getattr(sub, "hash_verifiable", False),
        ))

    results.sort(key=lambda r: r.score, reverse=True)
    return results


async def download_best_subtitle(
    file_path: str,
    languages: list[str],
    min_score: int = 60,
    providers: list[str] | None = None,
) -> bool:
    """Download the best matching subtitle for a video file."""
    if not HAS_SUBLIMINAL:
        return False

    path = Path(file_path)
    if not path.exists():
        return False

    video = subliminal.scan_video(str(path))
    lang_set = {Language.fromalpha2(lang) for lang in languages}
    provider_list = providers or ["opensubtitles", "podnapisi"]

    try:
        subs = subliminal.download_best_subtitles(
            {video},
            lang_set,
            providers=provider_list,
            min_score=min_score,
        )

        if subs.get(video):
            subliminal.save_subtitles(video, subs[video])
            logger.info("subtitle_downloaded", file=file_path, count=len(subs[video]))
            return True
    except Exception as e:
        logger.error("subtitle_download_failed", error=str(e), file=file_path)

    return False
