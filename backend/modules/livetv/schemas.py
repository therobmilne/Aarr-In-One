from pydantic import BaseModel

from backend.models.livetv import RecordingStatus


class PlaylistCreate(BaseModel):
    name: str
    url: str
    enabled: bool = True
    auto_refresh: bool = True
    refresh_interval_hours: int = 24


class PlaylistResponse(BaseModel):
    id: int
    name: str
    url: str
    enabled: bool
    auto_refresh: bool
    channel_count: int

    model_config = {"from_attributes": True}


class ChannelResponse(BaseModel):
    id: int
    playlist_id: int
    name: str
    channel_number: int | None
    group: str | None
    logo_url: str | None
    stream_url: str
    epg_id: str | None
    enabled: bool
    category: str | None

    model_config = {"from_attributes": True}


class ChannelUpdate(BaseModel):
    name: str | None = None
    channel_number: int | None = None
    group: str | None = None
    enabled: bool | None = None
    category: str | None = None
    epg_id: str | None = None


class EPGEntryResponse(BaseModel):
    id: int
    channel_epg_id: str
    title: str
    description: str | None
    start_time: str
    end_time: str
    category: str | None

    model_config = {"from_attributes": True}


class RecordingCreate(BaseModel):
    channel_id: int
    title: str
    start_time: str
    end_time: str
    is_series_rule: bool = False
    series_rule_pattern: str | None = None


class RecordingResponse(BaseModel):
    id: int
    channel_id: int
    title: str
    start_time: str
    end_time: str
    status: RecordingStatus
    file_path: str | None
    is_series_rule: bool

    model_config = {"from_attributes": True}
