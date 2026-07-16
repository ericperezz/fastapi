from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.logger import get_logger
from app.core.security import (
    verify_password,
    create_access_token,
    generate_secure_token,
    hash_token,
    hash_password
)
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.repositories.user_repository import UserRepository
from app.repositories.password_reset_token_repository import (
    PasswordResetTokenRepository
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from app.schemas.auth import LoginRequest

logger = get_logger("auth_service")


class AuthService:

    def __init__(
        self,
        user_repository: UserRepository,
        password_reset_token_repository: PasswordResetTokenRepository | None = None,
        refresh_token_repository: RefreshTokenRepository | None = None
    ):
        self.user_repository = user_repository
        self.password_reset_token_repository = password_reset_token_repository
        self.refresh_token_repository = refresh_token_repository

    async def login(
        self,
        data: LoginRequest,
        user_agent: str | None = None,
        ip_address: str | None = None
    ) -> tuple[str, str]:
        user = await self.user_repository.get_by_email(data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        access_token = create_access_token(str(user.id))
        refresh_token = await self.create_refresh_token(
            user_id=user.id,
            user_agent=user_agent,
            ip_address=ip_address
        )

        return access_token, refresh_token

    async def create_refresh_token(
        self,
        user_id,
        user_agent: str | None = None,
        ip_address: str | None = None
    ) -> str:
        if not self.refresh_token_repository:
            raise RuntimeError("RefreshTokenRepository no fue inicializado")

        plain_refresh_token = generate_secure_token()
        token_hash = hash_token(plain_refresh_token)

        expires_at = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )

        refresh_token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            user_agent=user_agent,
            ip_address=ip_address
        )

        await self.refresh_token_repository.create(refresh_token)

        return plain_refresh_token

    async def refresh(
        self,
        refresh_token: str,
        user_agent: str | None = None,
        ip_address: str | None = None
    ) -> tuple[str, str]:
        if not self.refresh_token_repository:
            raise RuntimeError("RefreshTokenRepository no fue inicializado")

        token_hash = hash_token(refresh_token)

        stored_refresh_token = await self.refresh_token_repository.get_by_token_hash(
            token_hash
        )

        if not stored_refresh_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido"
            )

        if stored_refresh_token.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token inválido"
            )

        if stored_refresh_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expirado"
            )

        user = await self.user_repository.get_by_id(
            stored_refresh_token.user_id
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        await self.refresh_token_repository.revoke(stored_refresh_token)

        new_access_token = create_access_token(str(user.id))

        new_refresh_token = await self.create_refresh_token(
            user_id=user.id,
            user_agent=user_agent,
            ip_address=ip_address
        )

        return new_access_token, new_refresh_token

    async def logout(self, refresh_token: str) -> None:
        if not self.refresh_token_repository:
            raise RuntimeError("RefreshTokenRepository no fue inicializado")

        token_hash = hash_token(refresh_token)

        stored_refresh_token = await self.refresh_token_repository.get_by_token_hash(
            token_hash
        )

        if not stored_refresh_token:
            return

        if stored_refresh_token.revoked_at is not None:
            return

        await self.refresh_token_repository.revoke(stored_refresh_token)

    async def logout_all(self, user_id) -> None:
        if not self.refresh_token_repository:
            raise RuntimeError("RefreshTokenRepository no fue inicializado")

        await self.refresh_token_repository.revoke_all_by_user_id(user_id)

    async def forgot_password(self, email: str) -> None:
        if not self.password_reset_token_repository:
            raise RuntimeError("PasswordResetTokenRepository no fue inicializado")

        user = await self.user_repository.get_by_email(email)

        if not user:
            return

        if not user.is_active:
            return

        await self.password_reset_token_repository.invalidate_unused_tokens_by_user_id(
            user.id
        )

        plain_token = generate_secure_token()
        token_hash_value = hash_token(plain_token)

        expires_at = datetime.utcnow() + timedelta(
            minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
        )

        password_reset_token = PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash_value,
            expires_at=expires_at
        )

        await self.password_reset_token_repository.create(password_reset_token)

        if settings.APP_ENV == "development":
            logger.warning(
                f"⚠️ DEV ONLY - Token de recuperación para {user.email}: {plain_token}"
            )

    async def reset_password(self, token: str, new_password: str) -> None:
        if not self.password_reset_token_repository:
            raise RuntimeError("PasswordResetTokenRepository no fue inicializado")

        token_hash_value = hash_token(token)

        password_reset_token = await self.password_reset_token_repository.get_by_token_hash(
            token_hash_value
        )

        if not password_reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado"
            )

        if password_reset_token.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado"
            )

        if password_reset_token.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado"
            )

        user = await self.user_repository.get_by_id(
            password_reset_token.user_id
        )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token inválido o expirado"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        user.hashed_password = hash_password(new_password)

        await self.user_repository.update(user)

        await self.password_reset_token_repository.mark_as_used(
            password_reset_token
        )

        await self.password_reset_token_repository.invalidate_unused_tokens_by_user_id(
            user.id
        )

        if self.refresh_token_repository:
            await self.refresh_token_repository.revoke_all_by_user_id(user.id)