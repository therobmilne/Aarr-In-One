from pydantic import BaseModel, Field


class IPTVCredentials(BaseModel):
    server_url: str = Field(..., description="Xtream Codes server URL (e.g. http://provider.com)")
    username: str
    password: str


class IPTVTestResult(BaseModel):
    success: bool
    message: str
    vod_count: int = 0
    series_count: int = 0
    live_count: int = 0


class ScanProgress(BaseModel):
    phase: str = Field(..., description="Current scan phase: movies, series, live, idle")
    found: int = 0
    processed: int = 0
    total: int = 0
    skipped: int = 0
    is_complete: bool = False
    elapsed_seconds: float = 0.0
