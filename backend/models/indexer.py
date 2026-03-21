import enum

from sqlalchemy import Boolean, Enum, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class IndexerType(str, enum.Enum):
    TORZNAB = "torznab"
    NEWZNAB = "newznab"
    RSS = "rss"


class IndexerStatus(str, enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    FAILED = "failed"
    DISABLED = "disabled"


class Indexer(TimestampMixin, Base):
    __tablename__ = "indexers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[IndexerType] = mapped_column(Enum(IndexerType), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=25, nullable=False)

    # Categories (JSON array of ints)
    categories: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Status & stats
    status: Mapped[IndexerStatus] = mapped_column(
        Enum(IndexerStatus), default=IndexerStatus.HEALTHY, nullable=False
    )
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    average_response_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_queries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_grabs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Cloudflare bypass
    requires_flaresolverr: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Rate limiting
    rate_limit_requests: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rate_limit_period_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
