from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.auth.middleware import get_current_user
from backend.auth.schemas import LoginRequest, LoginResponse, UserInfo
from backend.auth.service import authenticate_with_jellyfin
from backend.database import get_db
from backend.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    user, token = await authenticate_with_jellyfin(body.username, body.password, db)
    return LoginResponse(
        token=token,
        user=UserInfo.model_validate(user),
    )


@router.get("/me", response_model=UserInfo)
async def get_me(user: User = Depends(get_current_user)):
    return UserInfo.model_validate(user)
