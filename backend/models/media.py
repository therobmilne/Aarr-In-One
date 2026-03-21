import enum

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin


class MediaStatus(str, enum.Enum):
    MISSING = "missing"
    WANTED = "wanted"
    DOWNLOADING = "downloading"
    IMPORTED = "imported"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class Movie(TimestampMixin, Base):
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tmdb_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    imdb_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    original_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    genres: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    runtime: Mapped[int | None] = mapped_column(Integer, nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # Library state
    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus), default=MediaStatus.MISSING, nullable=False
    )
    monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("quality_profiles.id"), nullable=True
    )

    # File info
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality: Mapped[str | None] = mapped_column(String(50), nullable=True)
    codec: Mapped[str | None] = mapped_column(String(50), nullable=True)
    resolution: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Jellyfin
    jellyfin_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Series(TimestampMixin, Base):
    __tablename__ = "series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tvdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    tmdb_id: Mapped[int | None] = mapped_column(Integer, unique=True, nullable=True, index=True)
    imdb_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    backdrop_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    genres: Mapped[str | None] = mapped_column(Text, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_text: Mapped[str | None] = mapped_column(String(50), nullable=True)  # Continuing, Ended
    network: Mapped[str | None] = mapped_column(String(255), nullable=True)
    series_type: Mapped[str] = mapped_column(
        String(20), default="standard", nullable=False
    )  # standard, daily, anime

    monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    quality_profile_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("quality_profiles.id"), nullable=True
    )

    jellyfin_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    seasons: Mapped[list["Season"]] = relationship("Season", back_populates="series", cascade="all, delete-orphan")


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id"), nullable=False)
    season_number: Mapped[int] = mapped_column(Integer, nullable=False)
    monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    episode_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    series: Mapped["Series"] = relationship("Series", back_populates="seasons")
    episodes: Mapped[list["Episode"]] = relationship("Episode", back_populates="season", cascade="all, delete-orphan")


class Episode(TimestampMixin, Base):
    __tablename__ = "episodes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    season_id: Mapped[int] = mapped_column(Integer, ForeignKey("seasons.id"), nullable=False)
    series_id: Mapped[int] = mapped_column(Integer, ForeignKey("series.id"), nullable=False)
    episode_number: Mapped[int] = mapped_column(Integer, nullable=False)
    absolute_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    air_date: Mapped[str | None] = mapped_column(String(10), nullable=True)

    status: Mapped[MediaStatus] = mapped_column(
        Enum(MediaStatus), default=MediaStatus.MISSING, nullable=False
    )
    monitored: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    quality: Mapped[str | None] = mapped_column(String(50), nullable=True)

    season: Mapped["Season"] = relationship("Season", back_populates="episodes")
