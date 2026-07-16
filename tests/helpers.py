DEFAULT_EMAIL = "user@example.com"
DEFAULT_USERNAME = "userdemo"
DEFAULT_PASSWORD = "Password123!"


async def register_user(
    client,
    email: str = DEFAULT_EMAIL,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD,
    first_name: str = "Demo",
    last_name: str = "User"
):
    return await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "password": password
        }
    )


async def login_user(
    client,
    email: str = DEFAULT_EMAIL,
    password: str = DEFAULT_PASSWORD
):
    """
    Tu endpoint login usa OAuth2PasswordRequestForm.

    Por eso enviamos data=form,
    no json.
    """
    return await client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password
        },
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )


async def register_and_login(
    client,
    email: str = DEFAULT_EMAIL,
    username: str = DEFAULT_USERNAME,
    password: str = DEFAULT_PASSWORD
):
    register_response = await register_user(
        client,
        email=email,
        username=username,
        password=password
    )

    assert register_response.status_code in [200, 201]

    login_response = await login_user(
        client,
        email=email,
        password=password
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    return {
        "access_token": login_data["access_token"],
        "refresh_token": login_data.get("refresh_token"),
        "email": email,
        "password": password
    }


def auth_headers(access_token: str) -> dict:
    return {
        "Authorization": f"Bearer {access_token}"
    }