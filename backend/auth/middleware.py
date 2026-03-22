from fastapi import Depends, Header, HTTPException, Query, WebSocket
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.service import decode_jwt
from backend.database import get_db
from backend.models.user import User, UserRole


async def get_current_user(
    authorization: str = Header(None),
    x_api_key: str = Header(None, alias="X-Api-Key"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract current user from JWT token or API key.

    During initial setup (no users in DB), returns a temporary admin user
    so that configuration endpoints are accessible before Jellyfin auth.
    """
    from backend.config import settings

    # Check if ANY users exist — if not, we're in setup mode
    result = await db.execute(select(User).limit(1))
    any_user = result.scalar_one_or_none()
    if any_user is None:
        # No users yet — return a temporary admin for setup
        return User(
            id=0,
            jellyfin_id="setup",
            username="setup-admin",
            display_name="Setup Admin",
            role=UserRole.ADMIN,
            is_active=True,
            auto_approve=True,
        )

    # API key auth
    if x_api_key:
        if x_api_key == settings.SECRET_KEY:
            result = await db.execute(
                select(User).where(User.role == UserRole.ADMIN).limit(1)
            )
            admin = result.scalar_one_or_none()
            if admin:
                return admin
        raise HTTPException(status_code=401, detail="Invalid API key")

    # JWT auth
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")

    token = authorization.removeprefix("Bearer ")
    payload = decode_jwt(token)

    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_ws_user(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Authenticate WebSocket connections via query param token."""
    payload = decode_jwt(token)
    user_id = int(payload["sub"])
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        await websocket.close(code=4001)
        raise HTTPException(status_code=401)
    return user


def require_role(*roles: UserRole):
    """Dependency that checks user has one of the specified roles."""

    async def check(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return check
