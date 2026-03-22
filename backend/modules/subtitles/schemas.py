from pydantic import BaseModel


class SubtitleProfileCreate(BaseModel):
    name: str
    languages: list[str] = ["en"]
    min_score: int = 60
    providers: list[str] = ["opensubtitles"]
    hearing_impaired: bool = False
    auto_download: bool = True
    auto_upgrade: bool = True
    preferred_format: str = "srt"
    is_default: bool = False


class SubtitleProfileResponse(BaseModel):
    id: int
    name: str
    languages: list[str]
    min_score: int
    providers: list[str]
    hearing_impaired: bool
    auto_download: bool
    auto_upgrade: bool
    preferred_format: str
    is_default: bool

    model_config = {"from_attributes": True}


class SubtitleProfileUpdate(BaseModel):
    name: str | None = None
    languages: list[str] | None = None
    min_score: int | None = None
    providers: list[str] | None = None
    hearing_impaired: bool | None = None
    auto_download: bool | None = None
    auto_upgrade: bool | None = None
    preferred_format: str | None = None
    is_default: bool | None = None


class SubtitleSearchResult(BaseModel):
    provider: str
    title: str
    language: str
    score: int
    hearing_impaired: bool
    download_url: str
    hash_match: bool = False
