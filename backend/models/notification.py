import enum

from sqlalchemy import Boolean, Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base, TimestampMixin


class NotificationType(str, enum.Enum):
    DISCORD = "discord"
    EMAIL = "email"
    GOTIFY = "gotify"
    NTFY = "ntfy"
    SLACK = "slack"
    WEBHOOK = "webhook"


class NotificationAgent(TimestampMixin, Base):
    __tablename__ = "notification_agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[NotificationType] = mapped_column(Enum(NotificationType), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # JSON config specific to type (webhook_url, smtp_host, etc.)
    config: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    # JSON array of event types to notify on
    events: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default='["request:new", "request:approved", "download:complete", "import:complete"]',
    )
