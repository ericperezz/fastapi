import pytest

from tests.helpers import register_and_login


@pytest.mark.asyncio
async def test_refresh_token_success(client):
    auth_data = await register_and_login(client)

    response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_data["refresh_token"]
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_old_refresh_token_cannot_be_reused(client):
    auth_data = await register_and_login(client)

    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_data["refresh_token"]
        }
    )

    assert first_refresh.status_code == 200

    second_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_data["refresh_token"]
        }
    )

    assert second_refresh.status_code == 401


@pytest.mark.asyncio
async def test_logout_revokes_refresh_token(client):
    auth_data = await register_and_login(client)

    logout_response = await client.post(
        "/api/v1/auth/logout",
        json={
            "refresh_token": auth_data["refresh_token"]
        }
    )

    assert logout_response.status_code == 200

    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        json={
            "refresh_token": auth_data["refresh_token"]
        }
    )

    assert refresh_response.status_code == 401