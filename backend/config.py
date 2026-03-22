from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Infrastructure
    DATABASE_URL: str = "sqlite+aiosqlite:///config/db/mediaforge.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    SECRET_KEY: str = "change-me-in-production"
    LOG_LEVEL: str = "INFO"
    APP_PORT: int = 8686

    # Container identity
    PUID: int = 1000
    PGID: int = 1000
    TZ: str = "America/Toronto"

    # Jellyfin (external — user's existing server)
    JELLYFIN_URL: str = "http://192.168.2.54:8096"
    JELLYFIN_API_KEY: str = ""

    # Backend service URLs (internal docker network)
    RADARR_URL: str = "http://radarr:7878"
    SONARR_URL: str = "http://sonarr:8989"
    PROWLARR_URL: str = "http://prowlarr:9696"
    JELLYSEERR_URL: str = "http://jellyseerr:5055"
    QBITTORRENT_URL: str = "http://gluetun:8080"
    SABNZBD_URL: str = "http://gluetun:8081"
    BAZARR_URL: str = "http://bazarr:6767"
    THREADFIN_URL: str = "http://threadfin:34400"
    GLUETUN_URL: str = "http://gluetun:8000"

    # Paths
    CONFIG_DIR: str = "/config"
    DOWNLOAD_DIR: str = "/downloads"
    MEDIA_DIR: str = "/media"

    # Application state
    SETUP_COMPLETE: bool = False

    # TMDB
    TMDB_API_KEY: str = ""

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    @property
    def config_path(self) -> Path:
        return Path(self.CONFIG_DIR)

    @property
    def download_path(self) -> Path:
        return Path(self.DOWNLOAD_DIR)

    @property
    def media_path(self) -> Path:
        return Path(self.MEDIA_DIR)

    @property
    def is_postgres(self) -> bool:
        return self.DATABASE_URL.startswith("postgresql")


settings = Settings()
