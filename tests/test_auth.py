import pytest

from tests.helpers import (
    register_user,
    login_user,
    DEFAULT_EMAIL,
    DEFAULT_PASSWORD
)


@pytest.mark.asyncio
async def test_register_user_success(client):
    response = await register_user(client)

    assert response.status_code in [200, 201]

    data = response.json()

    assert data["email"] == DEFAULT_EMAIL
    assert data["username"] == "userdemo"
    assert data["role"] == "user"
    assert data["is_active"] is True
    assert data["is_verified"] is False

    # No deben exponerse datos sensibles.
    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email_fails(client):
    first_response = await register_user(client)
    assert first_response.status_code in [200, 201]

    second_response = await register_user(
        client,
        username="otro_username"
    )

    assert second_response.status_code == 409

    data = second_response.json()

    assert "detail" in data


@pytest.mark.asyncio
async def test_login_success(client):
    register_response = await register_user(client)
    assert register_response.status_code in [200, 201]

    login_response = await login_user(client)

    assert login_response.status_code == 200

    data = login_response.json()

    assert "access_token" in data
    assert data["access_token"]

    # Si ya implementaste refresh tokens, debe existir.
    assert "refresh_token" in data
    assert data["refresh_token"]

    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_with_wrong_password_fails(client):
    register_response = await register_user(client)
    assert register_response.status_code in [200, 201]

    login_response = await login_user(
        client,
        email=DEFAULT_EMAIL,
        password="WrongPassword123!"
    )

    assert login_response.status_code == 401

    data = login_response.json()

    assert data["detail"] == "Credenciales inválidas"


@pytest.mark.asyncio
async def test_login_with_non_existing_user_fails(client):
    login_response = await login_user(
        client,
        email="noexiste@example.com",
        password=DEFAULT_PASSWORD
    )

    assert login_response.status_code == 401

    data = login_response.json()

    assert data["detail"] == "Credenciales inválidas"

@pytest.mark.asyncio
async def test_register_with_weak_password_fails(client):
    response = await register_user(
        client,
        email="weak@example.com",
        username="weakuser",
        password="password"
    )

    assert response.status_code in [400, 422]

@pytest.mark.asyncio
async def test_register_duplicate_username_fails(client):
    first_response = await register_user(
        client,
        email="user1@example.com",
        username="sameusername"
    )

    assert first_response.status_code in [200, 201]

    second_response = await register_user(
        client,
        email="user2@example.com",
        username="sameusername"
    )

    assert second_response.status_code == 409