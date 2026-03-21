from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class SubtitleProfile(TimestampMixin, Base):
    __tablename__ = "subtitle_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    # JSON array of language codes, e.g. ["en", "lt"]
    languages: Mapped[str] = mapped_column(Text, nullable=False, default='["en"]')
    # Minimum score threshold (0-100)
    min_score: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    # JSON array of provider names
    providers: Mapped[str] = mapped_column(Text, nullable=False, default='["opensubtitles"]')
    hearing_impaired: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    auto_download: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_upgrade: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # JSON: tag-based exclusions
    exclude_tags: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # Preferred subtitle format
    preferred_format: Mapped[str] = mapped_column(String(10), default="srt", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
