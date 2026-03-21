import enum

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class IPTVPlaylist(TimestampMixin, Base):
    __tablename__ = "iptv_playlists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    auto_refresh: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    refresh_interval_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    channel_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class IPTVChannel(TimestampMixin, Base):
    __tablename__ = "iptv_channels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    playlist_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    channel_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    group: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    stream_url: Mapped[str] = mapped_column(Text, nullable=False)
    backup_urls: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON array
    epg_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # For HDHomeRun emulation
    hdhr_channel_number: Mapped[str | None] = mapped_column(String(20), nullable=True)


class EPGEntry(TimestampMixin, Base):
    __tablename__ = "iptv_epg"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_epg_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_time: Mapped[str] = mapped_column(String(30), nullable=False)
    end_time: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    icon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)


class RecordingStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    RECORDING = "recording"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DVRRecording(TimestampMixin, Base):
    __tablename__ = "dvr_recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    channel_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    start_time: Mapped[str] = mapped_column(String(30), nullable=False)
    end_time: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[RecordingStatus] = mapped_column(
        Enum(RecordingStatus), default=RecordingStatus.SCHEDULED, nullable=False
    )
    file_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    file_size: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_series_rule: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    series_rule_pattern: Mapped[str | None] = mapped_column(String(500), nullable=True)
