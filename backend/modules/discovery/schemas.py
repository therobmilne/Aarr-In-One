from pydantic import BaseModel

from backend.models.request import RequestStatus, RequestType


class RequestCreate(BaseModel):
    type: RequestType
    tmdb_id: int
    tvdb_id: int | None = None
    title: str
    year: int | None = None
    poster_url: str | None = None
    requested_seasons: list[int] | None = None


class RequestResponse(BaseModel):
    id: int
    type: RequestType
    status: RequestStatus
    tmdb_id: int
    title: str
    year: int | None
    poster_url: str | None
    requested_by: str
    created_at: str

    model_config = {"from_attributes": True}


class TMDBSearchResult(BaseModel):
    tmdb_id: int
    title: str
    original_title: str | None = None
    year: int | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    rating: float | None = None
    media_type: str = "movie"


class TMDBTrendingResponse(BaseModel):
    results: list[TMDBSearchResult] = []
    page: int = 1
    total_pages: int = 1
