from pydantic import BaseModel

from backend.models.media import MediaStatus


class MovieCreate(BaseModel):
    tmdb_id: int
    title: str
    year: int | None = None
    quality_profile_id: int | None = None
    monitored: bool = True


class MovieResponse(BaseModel):
    id: int
    tmdb_id: int
    imdb_id: str | None
    title: str
    year: int | None
    overview: str | None
    poster_url: str | None
    rating: float | None
    status: MediaStatus
    monitored: bool
    quality: str | None
    resolution: str | None
    file_path: str | None
    file_size: int | None

    model_config = {"from_attributes": True}


class MovieSearchResult(BaseModel):
    title: str
    indexer: str
    size_bytes: int
    quality: str
    codec: str | None
    seeders: int | None
    download_url: str
    info_hash: str | None
    score: int = 0
