import uuid
from datetime import datetime

from fastapi import HTTPException, status

from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserPasswordChange,
    UserAdminUpdate
)
from app.repositories.user_repository import UserRepository
from app.core.security import (
    hash_password,
    verify_password,
    validate_password_strength
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from sqlalchemy.exc import IntegrityError


class UserService:

    def __init__(
        self,
        repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository | None = None
    ):
        self.repository = repository
        self.refresh_token_repository = refresh_token_repository

    async def create_user(self, data: UserCreate) -> User:
        existing_user = await self.repository.get_by_email_any_status(data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado"
            )

        if data.username:
            existing_username = await self.repository.get_by_username_any_status(
                data.username
        )

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El username ya está registrado"
            )

        user = User(
        email=data.email.lower(),
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        hashed_password=hash_password(data.password)
        )

        return await self.repository.create(user)

    async def update_user(
        self,
        user: User,
        data: UserUpdate
    ) -> User:
        update_data = data.model_dump(exclude_unset=True)

        forbidden_fields = {
            "password",
            "hashed_password",
            "role",
            "is_active",
            "is_verified",
            "is_deleted",
        }

        for field in forbidden_fields:
            update_data.pop(field, None)

        new_email = update_data.get("email")
        if new_email is not None:
            normalized_email = str(new_email).strip().lower()

            existing_user = await self.repository.get_by_email_including_deleted(
                normalized_email
            )

            if existing_user and str(existing_user.id) != str(user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está en uso"
                )

            update_data["email"] = normalized_email

        new_username = update_data.get("username")
        if new_username is not None:
            normalized_username = str(new_username).strip()

            existing_user = await self.repository.get_by_username_including_deleted(
                normalized_username
            )

            if existing_user and str(existing_user.id) != str(user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El username ya está en uso"
                )

            update_data["username"] = normalized_username

        for field, value in update_data.items():
            setattr(user, field, value)

        return await self.repository.update(user)

    async def change_password(
        self,
        user: User,
        data: UserPasswordChange
    ) -> None:
        if not verify_password(data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La contraseña actual no es correcta"
            )

        if verify_password(data.new_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nueva contraseña no puede ser igual a la anterior"
            )

        user.hashed_password = hash_password(data.new_password)
        await self.repository.update(user)

        if self.refresh_token_repository:
            await self.refresh_token_repository.revoke_all_by_user_id(user.id)

    async def delete_user(self, user: User) -> None:
        user.is_deleted = True
        user.is_active = False
        user.deleted_at = datetime.utcnow()

        await self.repository.update(user)

    async def list_users(self, limit: int = 20, offset: int = 0) -> list[User]:
        return await self.repository.list_users(limit, offset)

    async def get_user_by_id(self, user_id: uuid.UUID) -> User:
        user = await self.repository.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado"
            )

        return user

    async def admin_update_user(
        self,
        user: User,
        data: UserAdminUpdate
    ) -> User:
        update_data = data.model_dump(
            exclude_unset=True,
            exclude={"user_id"}
        )

        allowed_roles = ["admin", "user"]

        if "role" in update_data and update_data["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol inválido"
            )

        new_email = update_data.get("email")
        if new_email is not None:
            normalized_email = str(new_email).strip().lower()

            existing_user = await self.repository.get_by_email_including_deleted(
                normalized_email
            )

            if existing_user and str(existing_user.id) != str(user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está en uso"
                )

            update_data["email"] = normalized_email

        new_username = update_data.get("username")
        if new_username is not None:
            normalized_username = str(new_username).strip()

            existing_user = await self.repository.get_by_username_including_deleted(
                normalized_username
            )

            if existing_user and str(existing_user.id) != str(user.id):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El username ya está en uso"
                )

            update_data["username"] = normalized_username

        for field, value in update_data.items():
            setattr(user, field, value)

        try:
            return await self.repository.update(user)
        except IntegrityError as exc:
            error_text = str(exc).lower()

            if "ix_users_email" in error_text or "email" in error_text:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El email ya está en uso"
                )

            if "ix_users_username" in error_text or "username" in error_text:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El username ya está en uso"
                )

            raise
    
    async def admin_change_password(
        self,
        user: User,
        new_password: str,
    ) -> User:
        user.hashed_password = hash_password(new_password)

        updated_user = await self.repository.update(user)

        if self.refresh_token_repository:
            await self.refresh_token_repository.revoke_all_by_user_id(user.id)

        return updated_user