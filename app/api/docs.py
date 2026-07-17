from fastapi import APIRouter, Depends, Form, HTTPException, Request, status
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_access_token, verify_password
from app.db.session import get_db
from app.dependencies.auth import get_current_admin_from_docs_cookie, require_role
from app.models.user import User
from app.repositories.user_repository import UserRepository


router = APIRouter(include_in_schema=False)


@router.get("/docs/login", response_class=HTMLResponse)
async def docs_login_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Swagger Admin Login</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                background: #f4f4f5;
                display: flex;
                justify-content: center;
                align-items: center;
                height: 100vh;
            }
            form {
                background: white;
                padding: 24px;
                border-radius: 8px;
                width: 340px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.15);
            }
            input {
                width: 100%;
                padding: 10px;
                margin-bottom: 12px;
                box-sizing: border-box;
            }
            button {
                width: 100%;
                padding: 10px;
                background: #111827;
                color: white;
                border: none;
                cursor: pointer;
            }
        </style>
    </head>
    <body>
        <form method="post" action="/docs/login">
            <h2>Swagger Admin Login</h2>
            <input type="email" name="email" placeholder="Email" required />
            <input type="password" name="password" placeholder="Password" required />
            <button type="submit">Entrar</button>
        </form>
    </body>
    </html>
    """


@router.post("/docs/login")
async def docs_login(
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    repository = UserRepository(db)

    user = await repository.get_by_email(email.lower())

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
        )

    require_role(user, ["admin"])

    access_token = create_access_token(
        subject=str(user.id)
    )

    response = RedirectResponse(
        url="/docs",
        status_code=status.HTTP_303_SEE_OTHER,
    )

    response.set_cookie(
        key="docs_access_token",
        value=access_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )

    return response


@router.get("/docs/logout")
async def docs_logout():
    response = RedirectResponse(
        url="/docs/login",
        status_code=status.HTTP_303_SEE_OTHER,
    )
    response.delete_cookie(
        key="docs_access_token",
        path="/",
    )
    return response


@router.get("/docs", response_class=HTMLResponse)
async def custom_swagger_ui(
    current_admin: User = Depends(get_current_admin_from_docs_cookie),
):
    return get_swagger_ui_html(
        openapi_url="/openapi.json",
        title=f"{settings.APP_NAME} - Swagger",
    )


@router.get("/openapi.json")
async def custom_openapi(
    request: Request,
    current_admin: User = Depends(get_current_admin_from_docs_cookie),
):
    return JSONResponse(request.app.openapi())