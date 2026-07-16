import pytest

from tests.helpers import register_user


@pytest.mark.asyncio
async def test_forgot_password_same_response_for_existing_and_non_existing_email(client):
    await register_user(client)

    response_existing = await client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "user@example.com"
        }
    )

    response_non_existing = await client.post(
        "/api/v1/auth/forgot-password",
        json={
            "email": "noexiste@example.com"
        }
    )

    assert response_existing.status_code == 200
    assert response_non_existing.status_code == 200

    assert response_existing.json() == response_non_existing.json()