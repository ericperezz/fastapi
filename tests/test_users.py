import pytest

from tests.helpers import (
    register_user,
    login_user,
    register_and_login,
    auth_headers,
    DEFAULT_EMAIL,
    DEFAULT_PASSWORD
)


@pytest.mark.asyncio
async def test_users_me_without_token_fails(client):
    response = await client.get("/api/v1/users/me")

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_users_me_with_token_success(client):
    auth_data = await register_and_login(client)

    response = await client.get(
        "/api/v1/users/me",
        headers=auth_headers(auth_data["access_token"])
    )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == DEFAULT_EMAIL
    assert data["is_active"] is True

    assert "password" not in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_update_my_profile_success(client):
    auth_data = await register_and_login(client)

    response = await client.patch(
        "/api/v1/users/me",
        json={
            "first_name": "Eric",
            "last_name": "Tester"
        },
        headers=auth_headers(auth_data["access_token"])
    )

    assert response.status_code == 200

    data = response.json()

    assert data["first_name"] == "Eric"
    assert data["last_name"] == "Tester"
    assert data["email"] == DEFAULT_EMAIL


@pytest.mark.asyncio
async def test_change_password_success(client):
    auth_data = await register_and_login(client)

    response = await client.patch(
        "/api/v1/users/me/password",
        json={
            "current_password": DEFAULT_PASSWORD,
            "new_password": "NewPassword123!"
        },
        headers=auth_headers(auth_data["access_token"])
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_login_with_old_password_fails_after_password_change(client):
    auth_data = await register_and_login(client)

    change_response = await client.patch(
        "/api/v1/users/me/password",
        json={
            "current_password": DEFAULT_PASSWORD,
            "new_password": "NewPassword123!"
        },
        headers=auth_headers(auth_data["access_token"])
    )

    assert change_response.status_code == 204

    old_login_response = await login_user(
        client,
        email=DEFAULT_EMAIL,
        password=DEFAULT_PASSWORD
    )

    assert old_login_response.status_code == 401


@pytest.mark.asyncio
async def test_login_with_new_password_success_after_password_change(client):
    auth_data = await register_and_login(client)

    change_response = await client.patch(
        "/api/v1/users/me/password",
        json={
            "current_password": DEFAULT_PASSWORD,
            "new_password": "NewPassword123!"
        },
        headers=auth_headers(auth_data["access_token"])
    )

    assert change_response.status_code == 204

    new_login_response = await login_user(
        client,
        email=DEFAULT_EMAIL,
        password="NewPassword123!"
    )

    assert new_login_response.status_code == 200

    data = new_login_response.json()

    assert "access_token" in data


@pytest.mark.asyncio
async def test_soft_delete_blocks_login(client):
    auth_data = await register_and_login(client)

    delete_response = await client.delete(
        "/api/v1/users/me",
        headers=auth_headers(auth_data["access_token"])
    )

    assert delete_response.status_code == 204

    login_response = await login_user(
        client,
        email=DEFAULT_EMAIL,
        password=DEFAULT_PASSWORD
    )

    assert login_response.status_code == 401

@pytest.mark.asyncio
async def test_update_username_success(client):
    auth_data = await register_and_login(client)

    response = await client.patch(
        "/api/v1/users/me",
        json={
            "username": "newusername"
        },
        headers=auth_headers(auth_data["access_token"])
    )

    assert response.status_code == 200

    data = response.json()

    assert data["username"] == "newusername"