import enum

from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base, TimestampMixin


class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    SEARCHING = "searching"
    DOWNLOADING = "downloading"
    IMPORTED = "imported"
    AVAILABLE = "available"
    FAILED = "failed"


class RequestType(str, enum.Enum):
    MOVIE = "movie"
    SERIES = "series"


class MediaRequest(TimestampMixin, Base):
    __tablename__ = "media_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    type: Mapped[RequestType] = mapped_column(Enum(RequestType), nullable=False)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), default=RequestStatus.PENDING, nullable=False
    )
    tmdb_id: Mapped[int] = mapped_column(Integer, nullable=False)
    tvdb_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    requested_by_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=False
    )
    approved_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    denied_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Specific seasons requested (null = all, JSON array of season numbers)
    requested_seasons: Mapped[str | None] = mapped_column(Text, nullable=True)

    requested_by: Mapped["User"] = relationship("User", foreign_keys=[requested_by_id])
    approved_by: Mapped["User | None"] = relationship("User", foreign_keys=[approved_by_id])
