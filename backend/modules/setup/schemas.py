from pydantic import BaseModel


class SetupStatus(BaseModel):
    is_complete: bool
    current_step: int
    jellyfin_connected: bool
    jellyfin_url: str
    has_admin_user: bool
    has_tmdb_key: bool
    has_media_paths: bool
    has_vpn: bool


class JellyfinSetupRequest(BaseModel):
    jellyfin_url: str = ""
    username: str = ""
    password: str = ""


class JellyfinSetupResponse(BaseModel):
    success: bool
    message: str
    jellyfin_url: str = ""
    api_key: str = ""
    server_name: str = ""
    version: str = ""


class TMDBSetupRequest(BaseModel):
    api_key: str


class TMDBSetupResponse(BaseModel):
    success: bool
    message: str


class PathsSetupRequest(BaseModel):
    media_dir: str = "/media"
    download_dir: str = "/downloads"
    movies_path: str = "/media/movies"
    tv_path: str = "/media/tv"
    recordings_path: str = "/media/recordings"


class VPNSetupRequest(BaseModel):
    provider: str = ""
    vpn_type: str = "wireguard"
    enabled: bool = False


class CompleteSetupRequest(BaseModel):
    confirm: bool = True
