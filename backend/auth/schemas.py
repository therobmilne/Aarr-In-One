from pydantic import BaseModel

from backend.models.user import UserRole


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: "UserInfo"


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str | None
    role: UserRole
    jellyfin_id: str
    avatar_url: str | None

    model_config = {"from_attributes": True}
