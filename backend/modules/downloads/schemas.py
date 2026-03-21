from pydantic import BaseModel

from backend.models.download import DownloadCategory, DownloadStatus, DownloadType


class DownloadCreate(BaseModel):
    type: DownloadType
    title: str
    download_url: str
    category: DownloadCategory = DownloadCategory.OTHER
    movie_id: int | None = None
    episode_id: int | None = None


class DownloadResponse(BaseModel):
    id: int
    type: DownloadType
    status: DownloadStatus
    category: DownloadCategory
    title: str
    indexer_name: str | None
    size_bytes: int
    downloaded_bytes: int
    speed_bytes_sec: int
    progress: float
    eta_seconds: int | None
    seed_ratio: float
    peers: int
    seeds: int
    error_message: str | None

    model_config = {"from_attributes": True}


class DownloadStats(BaseModel):
    active_count: int
    total_speed_bytes_sec: int
    total_downloaded_bytes: int
    total_size_bytes: int
