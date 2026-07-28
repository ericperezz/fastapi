import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import get_current_user
from app.models.user import User
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import (
    CloneRepositoryResponse,
    RepositoryCloneRequest,
    RepositoryCreate,
    RepositoryDeleteRequest,
    RepositoryGetRequest,
    RepositoryResponse,
    RepositoryUpdate,
)
from app.services.repository_service import RepositoryService


router = APIRouter()


@router.post(
    "",
    response_model=RepositoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_repository(
    data: RepositoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    return await service.create_repository(
        data=data,
        current_user=current_user,
    )


@router.get(
    "",
    response_model=list[RepositoryResponse],
)
async def list_repositories(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    return await service.list_repositories(current_user=current_user)


@router.post(
    "/get",
    response_model=RepositoryResponse,
    operation_id="get_repository_by_id",
)
async def get_repository(
    data: RepositoryGetRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    return await service.get_repository(
        repository_id=data.repository_id,
        current_user=current_user,
    )


@router.patch(
    "",
    response_model=RepositoryResponse,
    operation_id="update_repository_by_id",
)
async def update_repository(
    data: RepositoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    return await service.update_repository(
        data=data,
        current_user=current_user,
    )


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    operation_id="delete_repository_by_id",
)
async def delete_repository(
    data: RepositoryDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    await service.delete_repository(
        repository_id=data.repository_id,
        current_user=current_user,
    )

    return {
        "message": "Repositorio eliminado correctamente"
    }


@router.post(
    "/clone",
    response_model=CloneRepositoryResponse,
    operation_id="clone_repository_by_id",
)
async def clone_repository(
    data: RepositoryCloneRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    repository = await service.clone_repository(
        repository_id=data.repository_id,
        current_user=current_user,
    )

    return CloneRepositoryResponse(
        message="Repositorio clonado correctamente",
        repository_id=repository.id,
        local_path=repository.local_path,
    )