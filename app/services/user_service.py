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
from app.core.security import hash_password, verify_password


class UserService:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def create_user(self, data: UserCreate) -> User:
        existing_user = await self.repository.get_by_email(data.email)

        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="El email ya está registrado"
            )

        user = User(
            email=data.email.lower(),
            username=data.username,
            first_name=data.first_name,
            last_name=data.last_name,
            hashed_password=hash_password(data.password)
        )

        return await self.repository.create(user)

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
        update_data = data.model_dump(exclude_unset=True)

        allowed_roles = ["admin", "user", "manager", "support"]

        if "role" in update_data and update_data["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Rol inválido"
            )

        for field, value in update_data.items():
            setattr(user, field, value)

        return await self.repository.update(user)