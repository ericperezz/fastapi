import uuid
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.dependencies.auth import get_current_user, get_current_admin
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserPasswordChange,
    UserAdminUpdate
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    return await service.update_user(current_user, data)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    await service.change_password(current_user, data)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    await service.delete_user(current_user)


@router.get("", response_model=list[UserResponse])
async def list_users(
    limit: int = 20,
    offset: int = 0,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)
    return await service.list_users(limit, offset)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)
    return await service.get_user_by_id(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    data: UserAdminUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    user = await service.get_user_by_id(user_id)
    return await service.admin_update_user(user, data)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def admin_delete_user(
    user_id: uuid.UUID,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    user = await service.get_user_by_id(user_id)
    await service.delete_user(user)