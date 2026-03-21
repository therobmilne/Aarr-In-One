import pytest


@pytest.mark.asyncio
async def test_login_without_jellyfin_returns_error(client):
    """Login should fail when Jellyfin is not configured."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "test", "password": "test"},
    )
    assert response.status_code in (401, 502)


@pytest.mark.asyncio
async def test_me_requires_auth(client):
    """GET /auth/me should require authentication."""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 401
