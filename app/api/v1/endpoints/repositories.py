import uuid

from fastapi import APIRouter, Depends, status, BackgroundTasks
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
    RepositoryRunTestsRequest,
    RepositoryRunTestsResponse,
    RepositoryStatusRequest,
    RepositoryStatusResponse,
    RepositoryUpdate,
)
from app.services.repository_service import RepositoryService
from app.repositories.repository_test_run_repository import RepositoryTestRunRepository

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from app.tasks.test_report_email_task import send_test_report_email_task





router = APIRouter()

def to_madrid_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(ZoneInfo("Europe/Madrid"))


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

    repository, status_info = await service.clone_repository(
        repository_id=data.repository_id,
        current_user=current_user,
    )

    return CloneRepositoryResponse(
        message="Repositorio clonado correctamente",
        repository_id=repository.id,
        local_path=repository.local_path,
        current_branch=status_info.current_branch,
        local_commit=status_info.local_commit,
        remote_commit=status_info.remote_commit,
        has_local_changes=status_info.has_local_changes,
        has_remote_changes=status_info.has_remote_changes,
    )


@router.post(
    "/status",
    response_model=RepositoryStatusResponse,
    operation_id="get_repository_status_by_id",
)
async def get_repository_status(
    data: RepositoryStatusRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    service = RepositoryService(repository_repository)

    repository, status_info = await service.get_repository_status(
        repository_id=data.repository_id,
        current_user=current_user,
    )

    if status_info is None:
        return RepositoryStatusResponse(
            repository_id=repository.id,
            local_path=repository.local_path,
            is_cloned=False,
            current_branch=None,
            local_commit=None,
            remote_commit=None,
            has_local_changes=False,
            has_remote_changes=False,
            message="El repositorio todavía no ha sido clonado",
        )

    return RepositoryStatusResponse(
        repository_id=repository.id,
        local_path=repository.local_path,
        is_cloned=status_info.is_cloned,
        current_branch=status_info.current_branch,
        local_commit=status_info.local_commit,
        remote_commit=status_info.remote_commit,
        has_local_changes=status_info.has_local_changes,
        has_remote_changes=status_info.has_remote_changes,
        message=status_info.message,
    )

@router.post(
    "/run-tests",
    response_model=RepositoryRunTestsResponse,
    operation_id="run_repository_tests_if_changed",
)
async def run_repository_tests(
    data: RepositoryRunTestsRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repository_repository = RepositoryRepository(db)
    test_run_repository = RepositoryTestRunRepository(db)

    service = RepositoryService(
        repository_repository=repository_repository,
        test_run_repository=test_run_repository,
    )

    repository, status_info, test_run = await service.run_tests_if_repository_changed(
        repository_id=data.repository_id,
        current_user=current_user,
        pull_before_tests=data.pull_before_tests,
    )

    if test_run and test_run.id:
        background_tasks.add_task(
            send_test_report_email_task,
            str(test_run.id),
        )

    finished_at_madrid = None
    if test_run.finished_at:
        finished_at_madrid = test_run.finished_at.astimezone(
            ZoneInfo("Europe/Madrid")
        )

    return RepositoryRunTestsResponse(
        test_run_id=test_run.id,
        repository_id=repository.id,
        local_path=repository.local_path,
        tests_ran=test_run.tests_ran,
        success=test_run.success,
        status=test_run.status,
        has_local_changes=test_run.has_local_changes,
        has_remote_changes=test_run.has_remote_changes,
        docker_image=test_run.docker_image,
        command=test_run.command,
        exit_code=test_run.exit_code,
        duration_seconds=test_run.duration_seconds,
        stdout=test_run.stdout,
        stderr=test_run.stderr,
        finished_at=test_run.finished_at,
        message=test_run.message,
    )

