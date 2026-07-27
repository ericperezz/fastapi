from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import (
    LoginRequest,
    TokenResponse,
    LoginResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
    RefreshTokenRequest,
    LogoutRequest,
    RegisterResponse
)
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.services.audit_service import AuditService
from app.core.request_context import get_client_ip, get_user_agent
from app.core import audit_events
from app.core.rate_limit import limiter
from app.core.config import settings
from app.dependencies.auth import get_current_admin
from app.core.security import generate_secure_token, create_access_token, hash_password, verify_password
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from app.repositories.password_reset_token_repository import PasswordResetTokenRepository
from app.schemas.auth import ResetPasswordRequest
from fastapi import Depends, Request, Response



router = APIRouter(prefix="/auth", tags=["Auth"])

FORGOT_PASSWORD_MESSAGE = (
    "Si el correo existe, recibirás instrucciones para recuperar tu contraseña"
)


def get_client_ip(request: Request) -> str | None:
    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    if request.client:
        return request.client.host

    return None


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit(settings.RATE_LIMIT_REGISTER)
async def register(
    request: Request,
    response: Response,
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user_repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    user_service = UserService(user_repository)

    auth_service = AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository
    )

    user = await user_service.create_user(data)

    login_data = LoginRequest(
        email=data.email,
        password=data.password
    )

    access_token, refresh_token = await auth_service.login(
        data=login_data,
        user_agent=get_user_agent(request),
        ip_address=get_client_ip(request)
    )

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.USER_CREATED,
        actor_user_id=current_admin.id,
        metadata={
            "created_user_id": str(user.id),
            "email": user.email,
            "username": user.username,
            "created_by_admin_id": str(current_admin.id),
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return RegisterResponse(
        user=user,
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer"
    )


@router.post("/login", response_model=LoginResponse)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    user_repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository
    )

    audit_service = AuditService(db)

    login_data = LoginRequest(
        email=form_data.username,
        password=form_data.password
    )

    try:
        access_token, refresh_token = await service.login(
            data=login_data,
            user_agent=get_user_agent(request),
            ip_address=get_client_ip(request)
        )

        if request.cookies.get("docs_access_token"):
            response.set_cookie(
                key="docs_api_access_token",
                value=access_token,
                httponly=True,
                secure=False,
                samesite="lax",
                max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                path="/",
            )

        user = await user_repository.get_by_email(login_data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

        login_at = get_login_datetime()

        await audit_service.log_event(
            event_type=audit_events.AUTH_LOGIN_SUCCESS,
            actor_user_id=user.id,
            metadata={
                "email": login_data.email,
                "login_at": login_at.isoformat()
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        return LoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            username=user.username,
            email=user.email,
            login_at=login_at
        )

    except Exception as e:
        user = await user_repository.get_by_email(login_data.email)

        await audit_service.log_event(
            event_type=audit_events.AUTH_LOGIN_FAILED,
            actor_user_id=user.id if user else None,
            metadata={
                "email": login_data.email,
                "reason": type(e).__name__
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    user_repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository
    )

    access_token, new_refresh_token = await service.refresh(
        refresh_token=data.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=get_client_ip(request)
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    data: LogoutRequest,
    db: AsyncSession = Depends(get_db),
):
    user_repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
    )

    await service.logout(data.refresh_token)

    response.delete_cookie(
        key="docs_api_access_token",
        path="/",
    )

    return {
        "message": "Sesión cerrada correctamente"
    }


@router.post("/logout-all")
async def logout_all(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user_repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = AuthService(
        user_repository=user_repository,
        refresh_token_repository=refresh_token_repository,
    )

    await service.logout_all(current_user.id)

    response.delete_cookie(
        key="docs_api_access_token",
        path="/",
    )

    return {
        "message": "Todas las sesiones fueron cerradas correctamente"
    }


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit(settings.RATE_LIMIT_FORGOT_PASSWORD)
async def forgot_password(
    request: Request,
    response: Response,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    user_repository = UserRepository(db)
    password_reset_token_repository = PasswordResetTokenRepository(db)

    service = AuthService(
        user_repository=user_repository,
        password_reset_token_repository=password_reset_token_repository
    )

    await service.forgot_password(data.email)

    user = await user_repository.get_by_email(data.email)

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.PASSWORD_RESET_REQUESTED,
        actor_user_id=user.id if user else None,
        metadata={
            "email": data.email
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return MessageResponse(
        message=FORGOT_PASSWORD_MESSAGE
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db)
):
    user_repository = UserRepository(db)
    password_reset_token_repository = PasswordResetTokenRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = AuthService(
        user_repository=user_repository,
        password_reset_token_repository=password_reset_token_repository,
        refresh_token_repository=refresh_token_repository
    )

    user = await service.reset_password(
        token=data.token,
        new_password=data.new_password
    )

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.PASSWORD_RESET_COMPLETED,
        actor_user_id=user.id if user else None,
        metadata={
            "email": user.email
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return MessageResponse(
        message="Contraseña actualizada correctamente"
    )

def get_login_datetime():
    try:
        return datetime.now(ZoneInfo("Europe/Madrid"))
    except ZoneInfoNotFoundError:
        return datetime.now(timezone.utc)


