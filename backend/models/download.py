import enum

from sqlalchemy import BigInteger, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class DownloadType(str, enum.Enum):
    TORRENT = "torrent"
    USENET = "usenet"


class DownloadStatus(str, enum.Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    SEEDING = "seeding"
    COMPLETED = "completed"
    FAILED = "failed"
    IMPORTING = "importing"
    IMPORTED = "imported"


class DownloadCategory(str, enum.Enum):
    MOVIES = "movies"
    TV = "tv"
    MUSIC = "music"
    OTHER = "other"


class Download(TimestampMixin, Base):
    __tablename__ = "downloads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[DownloadType] = mapped_column(Enum(DownloadType), nullable=False)
    status: Mapped[DownloadStatus] = mapped_column(
        Enum(DownloadStatus), default=DownloadStatus.QUEUED, nullable=False
    )
    category: Mapped[DownloadCategory] = mapped_column(
        Enum(DownloadCategory), default=DownloadCategory.OTHER, nullable=False
    )

    # Content info
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    indexer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    download_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    info_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Progress
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    downloaded_bytes: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    speed_bytes_sec: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    eta_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Torrent specific
    seed_ratio: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    peers: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seeds: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Usenet specific
    nzb_name: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # Post-processing
    output_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Link to media
    movie_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    episode_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
