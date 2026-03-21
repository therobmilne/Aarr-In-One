from datetime import datetime, timedelta, timezone

import httpx
from jose import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.exceptions import AuthenticationError, ExternalServiceError
from backend.logging_config import get_logger
from backend.models.user import User, UserRole

logger = get_logger("auth")


async def authenticate_with_jellyfin(
    username: str, password: str, db: AsyncSession
) -> tuple[User, str]:
    """Authenticate against Jellyfin and return local user + JWT token."""
    jellyfin_url = settings.JELLYFIN_URL
    if not jellyfin_url:
        raise AuthenticationError("Jellyfin URL not configured")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{jellyfin_url.rstrip('/')}/Users/AuthenticateByName",
                json={"Username": username, "Pw": password},
                headers={
                    "Content-Type": "application/json",
                    "X-Emby-Authorization": (
                        'MediaBrowser Client="MediaForge", Device="Server", '
                        'DeviceId="mediaforge-server", Version="0.1.0"'
                    ),
                },
            )
    except httpx.RequestError as e:
        raise ExternalServiceError("Jellyfin", f"Connection failed: {e}")

    if resp.status_code == 401:
        raise AuthenticationError("Invalid username or password")
    if resp.status_code != 200:
        raise ExternalServiceError("Jellyfin", f"Unexpected response: {resp.status_code}")

    data = resp.json()
    jellyfin_user = data.get("User", {})
    jellyfin_id = jellyfin_user.get("Id", "")
    is_admin = jellyfin_user.get("Policy", {}).get("IsAdministrator", False)

    # Upsert local user
    result = await db.execute(select(User).where(User.jellyfin_id == jellyfin_id))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(
            jellyfin_id=jellyfin_id,
            username=username,
            display_name=jellyfin_user.get("Name", username),
            role=UserRole.ADMIN if is_admin else UserRole.BASIC_USER,
            is_active=True,
        )
        db.add(user)
        await db.flush()
        logger.info("user_created", username=username, role=user.role)
    else:
        user.display_name = jellyfin_user.get("Name", username)
        if is_admin and user.role != UserRole.ADMIN:
            user.role = UserRole.ADMIN
        await db.flush()

    token = create_jwt(user)
    return user, token


def create_jwt(user: User) -> str:
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role.value,
        "jellyfin_id": user.jellyfin_id,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.JWTError as e:
        raise AuthenticationError(f"Invalid token: {e}")
