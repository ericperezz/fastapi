import uuid
from fastapi import Depends, Request, status
from fastapi import APIRouter, Depends, status, HTTPException, Request
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
    UserAdminUpdate,
    MessageResponse,
    UserAdminPasswordChange,
    UserAdminDelete
)
from app.repositories.refresh_token_repository import RefreshTokenRepository
from fastapi import Request
from app.services.audit_service import AuditService
from app.core.request_context import get_client_ip, get_user_agent
from app.core import audit_events
from app.repositories.refresh_token_repository import RefreshTokenRepository

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    request: Request,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository = UserRepository(db)
    service = UserService(repository)

    updated_user = await service.update_user(
        current_user,
        data
    )

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.USER_UPDATED,
        actor_user_id=current_user.id,
        metadata={
            "changed_fields": list(data.model_dump(exclude_unset=True).keys())
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return updated_user


@router.patch("/me/password",response_model=MessageResponse,status_code=status.HTTP_200_OK)
async def change_my_password(
    request: Request,
    data: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = UserService(
        repository=repository,
        refresh_token_repository=refresh_token_repository
    )

    await service.change_password(current_user, data)

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.PASSWORD_CHANGED,
        actor_user_id=current_user.id,
        metadata={
            "email": current_user.email
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return MessageResponse(
        message="Contraseña actualizada correctamente"
    )


@router.delete("/me", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def delete_my_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    await service.delete_user(current_user)

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.USER_DELETED,
        actor_user_id=current_user.id,
        metadata={
            "email": current_user.email,
            "username": current_user.username
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return MessageResponse(
        message="Cuenta eliminada correctamente"
    )
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


@router.patch("/admin", response_model=UserResponse, operation_id="admin_update_user")
async def admin_update_user(
    request: Request,
    data: UserAdminUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    user = await service.get_user_by_id(data.user_id)

    old_role = user.role

    updated_user = await service.admin_update_user(user, data)

    audit_service = AuditService(db)

    changed_fields = list(
        data.model_dump(
            exclude_unset=True,
            exclude={"user_id"}
        ).keys()
    )

    await audit_service.log_event(
        event_type=audit_events.USER_UPDATED,
        actor_user_id=admin.id,
        metadata={
            "target_user_id": str(data.user_id),
            "target_email": updated_user.email,
            "changed_fields": changed_fields
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    if data.role is not None and data.role != old_role:
        await audit_service.log_event(
            event_type=audit_events.ROLE_CHANGED,
            actor_user_id=admin.id,
            metadata={
                "target_user_id": str(data.user_id),
                "target_email": updated_user.email,
                "old_role": old_role,
                "new_role": data.role
            },
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request)
        )

    return updated_user


@router.delete("/admin", response_model=MessageResponse, status_code=status.HTTP_200_OK, operation_id="admin_delete_user")
async def admin_delete_user(
    request: Request,
    data: UserAdminDelete,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)

    user = await service.get_user_by_id(data.user_id)

    await service.delete_user(user)

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.USER_DELETED,
        actor_user_id=admin.id,
        metadata={
            "target_user_id": str(data.user_id),
            "target_email": user.email,
            "target_username": user.username,
            "deleted_by_admin_id": str(admin.id),
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return MessageResponse(
        message="Usuario borrado exitosamente"
    )


@router.patch("/admin/password", response_model=MessageResponse, status_code=status.HTTP_200_OK, operation_id="admin_change_user_password")
async def admin_change_user_password(
    request: Request,
    data: UserAdminPasswordChange,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repository = UserRepository(db)
    refresh_token_repository = RefreshTokenRepository(db)

    service = UserService(
        repository=repository,
        refresh_token_repository=refresh_token_repository
    )

    user = await service.get_user_by_id(data.user_id)

    await service.admin_change_password(
        user=user,
        new_password=data.new_password
    )

    audit_service = AuditService(db)
    await audit_service.log_event(
        event_type=audit_events.PASSWORD_CHANGED,
        actor_user_id=admin.id,
        metadata={
            "target_user_id": str(data.user_id),
            "target_email": user.email,
            "target_username": user.username,
            "changed_by_admin_id": str(admin.id),
        },
        ip_address=get_client_ip(request),
        user_agent=get_user_agent(request)
    )

    return MessageResponse(
        message="Contraseña del usuario actualizada correctamente"
    )