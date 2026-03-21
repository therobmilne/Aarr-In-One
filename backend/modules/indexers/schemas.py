from pydantic import BaseModel

from backend.models.indexer import IndexerStatus, IndexerType


class IndexerCreate(BaseModel):
    name: str
    type: IndexerType
    url: str
    api_key: str | None = None
    enabled: bool = True
    priority: int = 25
    categories: list[int] | None = None
    tags: list[str] | None = None


class IndexerResponse(BaseModel):
    id: int
    name: str
    type: IndexerType
    url: str
    enabled: bool
    priority: int
    status: IndexerStatus
    average_response_ms: float
    total_queries: int
    total_grabs: int
    consecutive_failures: int

    model_config = {"from_attributes": True}


class IndexerTestResult(BaseModel):
    success: bool
    message: str
    response_time_ms: float = 0


class SearchResult(BaseModel):
    title: str
    indexer: str
    size_bytes: int
    download_url: str
    info_hash: str | None = None
    seeders: int | None = None
    leechers: int | None = None
    quality: str | None = None
    codec: str | None = None
    source: str | None = None
    age_days: int | None = None
    score: int = 0
