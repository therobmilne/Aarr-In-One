from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class QualityProfile(TimestampMixin, Base):
    __tablename__ = "quality_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    upgrade_allowed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cutoff: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # JSON: ordered list of quality items with allowed/preferred flags
    # e.g. [{"quality": "Bluray-2160p", "allowed": true}, ...]
    qualities: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON: minimum custom format score required
    min_format_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    upgrade_until_score: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)


class CustomFormat(TimestampMixin, Base):
    __tablename__ = "custom_formats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON: conditions array
    # e.g. [{"type": "release_title", "pattern": "x265|HEVC", "negate": false, "required": true}]
    conditions: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    # JSON: per-profile scores
    # e.g. {"profile_id_1": 100, "profile_id_2": -50}
    profile_scores: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
