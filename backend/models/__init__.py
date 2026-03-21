# Import all models so Alembic can detect them
from backend.models.base import Base
from backend.models.download import Download
from backend.models.indexer import Indexer
from backend.models.livetv import DVRRecording, EPGEntry, IPTVChannel, IPTVPlaylist
from backend.models.media import Episode, Movie, Season, Series
from backend.models.notification import NotificationAgent
from backend.models.quality import CustomFormat, QualityProfile
from backend.models.request import MediaRequest
from backend.models.setting import AppSetting
from backend.models.subtitle import SubtitleProfile
from backend.models.user import User
from backend.models.vpn import VPNConfig

__all__ = [
    "Base",
    "User",
    "AppSetting",
    "Movie",
    "Series",
    "Season",
    "Episode",
    "MediaRequest",
    "Indexer",
    "Download",
    "QualityProfile",
    "CustomFormat",
    "SubtitleProfile",
    "IPTVPlaylist",
    "IPTVChannel",
    "EPGEntry",
    "DVRRecording",
    "NotificationAgent",
    "VPNConfig",
]
