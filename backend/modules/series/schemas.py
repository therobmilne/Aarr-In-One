from pydantic import BaseModel

from backend.models.media import MediaStatus


class SeriesCreate(BaseModel):
    tmdb_id: int | None = None
    tvdb_id: int | None = None
    title: str
    year: int | None = None
    series_type: str = "standard"
    quality_profile_id: int | None = None
    monitored: bool = True


class SeasonResponse(BaseModel):
    id: int
    season_number: int
    monitored: bool
    episode_count: int

    model_config = {"from_attributes": True}


class EpisodeResponse(BaseModel):
    id: int
    season_number: int
    episode_number: int
    absolute_number: int | None
    title: str | None
    air_date: str | None
    status: MediaStatus
    monitored: bool
    file_path: str | None
    quality: str | None

    model_config = {"from_attributes": True}


class SeriesResponse(BaseModel):
    id: int
    tvdb_id: int | None
    tmdb_id: int | None
    title: str
    year: int | None
    overview: str | None
    poster_url: str | None
    rating: float | None
    status_text: str | None
    network: str | None
    series_type: str
    monitored: bool
    seasons: list[SeasonResponse] = []

    model_config = {"from_attributes": True}
