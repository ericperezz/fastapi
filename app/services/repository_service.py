import uuid

from fastapi import HTTPException, status

from app.core.crypto import encrypt_secret
from app.models.repository import Repository
from app.models.user import User
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.services.git_service import GitService

import shutil
from datetime import datetime, timezone

from app.models.repository_test_run import RepositoryTestRun
from app.repositories.repository_test_run_repository import RepositoryTestRunRepository
from app.services.docker_test_runner import DockerTestRunner

from pathlib import Path
from app.core.config import settings
from app.core.test_run_status import (
    TEST_STATUS_FAILED,
    TEST_STATUS_PASSED,
    TEST_STATUS_RUNNER_ERROR,
    TEST_STATUS_SKIPPED,
    TEST_STATUS_TIMEOUT,
)


class RepositoryService:
    def __init__(
        self,
        repository_repository: RepositoryRepository,
        test_run_repository: RepositoryTestRunRepository | None = None,
    ):
        self.repository_repository = repository_repository
        self.test_run_repository = test_run_repository
        self.git_service = GitService()
        self.docker_test_runner = DockerTestRunner()

    def _is_admin(self, user: User) -> bool:
        return user.role == "admin"

    async def create_repository(
        self,
        data: RepositoryCreate,
        current_user: User,
    ) -> Repository:
        existing = await self.repository_repository.get_by_name_for_owner(
            name=data.name,
            owner_user_id=current_user.id,
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya tienes un repositorio con ese nombre"
            )

        repository = Repository(
            owner_user_id=current_user.id,
            name=data.name,
            repository_url=data.repository_url,
            git_username=data.git_username,
            encrypted_git_password=encrypt_secret(data.git_password),
            is_active=True,
        )

        return await self.repository_repository.create(repository)

    async def list_repositories(
        self,
        current_user: User,
    ) -> list[Repository]:
        if self._is_admin(current_user):
            return await self.repository_repository.list_all()

        return await self.repository_repository.list_by_owner(current_user.id)

    async def get_repository(
        self,
        repository_id: uuid.UUID,
        current_user: User,
    ) -> Repository:
        repository = await self.repository_repository.get_by_id(repository_id)

        if not repository:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Repositorio no encontrado"
            )

        if not self._is_admin(current_user) and repository.owner_user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para acceder a este repositorio"
            )

        return repository

    async def update_repository(
        self,
        data: RepositoryUpdate,
        current_user: User,
    ) -> Repository:
        repository = await self.get_repository(
            repository_id=data.repository_id,
            current_user=current_user,
        )

        update_data = data.model_dump(
            exclude_unset=True,
            exclude={"repository_id"}
        )

        if "name" in update_data:
            existing = await self.repository_repository.get_by_name_for_owner(
                name=update_data["name"],
                owner_user_id=repository.owner_user_id,
            )

            if existing and existing.id != repository.id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe un repositorio con ese nombre para este usuario"
                )

        if data.git_password is not None:
            repository.encrypted_git_password = encrypt_secret(data.git_password)

        if data.name is not None:
            repository.name = data.name

        if data.repository_url is not None:
            repository.repository_url = data.repository_url

        if data.git_username is not None:
            repository.git_username = data.git_username

        if data.is_active is not None:
            repository.is_active = data.is_active

        return await self.repository_repository.update(repository)

    async def delete_repository(
        self,
        repository_id: uuid.UUID,
        current_user: User,
    ) -> None:
        repository = await self.get_repository(
            repository_id=repository_id,
            current_user=current_user,
        )

        await self.repository_repository.delete(repository)

    async def clone_repository(
        self,
        repository_id: uuid.UUID,
        current_user: User,
    ) -> tuple[Repository, object]:
        repository = await self.get_repository(
            repository_id=repository_id,
            current_user=current_user,
        )

        if not repository.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El repositorio está desactivado"
            )

        local_path = self.git_service.clone_repository(repository)

        repository.local_path = local_path

        repository = await self.repository_repository.update(repository)

        status_info = self.git_service.get_repository_status(repository)

        return repository, status_info


    async def get_repository_status(
        self,
        repository_id: uuid.UUID,
        current_user: User,
    ):
        repository = await self.get_repository(
            repository_id=repository_id,
            current_user=current_user,
        )

        if not repository.local_path:
            return repository, self.git_service.get_repository_status(repository)

        status_info = self.git_service.get_repository_status(repository)

        return repository, status_info

    async def run_tests_if_repository_changed(
        self,
        repository_id: uuid.UUID,
        current_user: User,
        pull_before_tests: bool = True,
    ):
        if not self.test_run_repository:
            raise RuntimeError("RepositoryTestRunRepository no fue inicializado")

        repository = await self.get_repository(
            repository_id=repository_id,
            current_user=current_user,
        )

        if not repository.local_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El repositorio todavía no ha sido clonado"
            )

        status_info = self.git_service.get_repository_status(repository)

        has_changes = (
            status_info.has_local_changes
            or status_info.has_remote_changes
        )

        if not has_changes:
            test_run = RepositoryTestRun(
                repository_id=repository.id,
                triggered_by_user_id=current_user.id,
                docker_image=settings.REPOSITORY_TEST_DOCKER_IMAGE,
                command=settings.REPOSITORY_TEST_COMMAND,
                tests_ran=False,
                success=None,
                status=TEST_STATUS_SKIPPED,
                exit_code=None,
                stdout=None,
                stderr=None,
                duration_seconds=None,
                has_local_changes=status_info.has_local_changes,
                has_remote_changes=status_info.has_remote_changes,
                message="No se ejecutaron tests porque no se detectaron cambios",
                finished_at=datetime.now(timezone.utc),
            )

            test_run = await self.test_run_repository.create(test_run)

            return repository, status_info, test_run

        temp_repo_path = None

        try:
            temp_repo_path = self.git_service.prepare_temporary_copy_and_pull(
                repository=repository,
                has_remote_changes=status_info.has_remote_changes,
                pull_before_tests=pull_before_tests,
            )

            docker_result = self.docker_test_runner.run_tests(temp_repo_path)

            run_status = docker_result.get("status") or TEST_STATUS_RUNNER_ERROR
            success = docker_result.get("success", False)

            if run_status == TEST_STATUS_PASSED:
                message = (
                    "Se detectaron cambios, se ejecutaron los tests en Docker "
                    "y pasaron correctamente"
                )
            elif run_status == TEST_STATUS_FAILED:
                message = (
                    "Se detectaron cambios, se ejecutaron los tests en Docker "
                    "pero fallaron"
                )
            elif run_status == TEST_STATUS_TIMEOUT:
                message = (
                    "Se detectaron cambios, pero la ejecución de tests superó el timeout"
                )
            else:
                message = (
                    "Se detectaron cambios, pero ocurrió un error en el runner de Docker"
                )

            test_run = RepositoryTestRun(
                repository_id=repository.id,
                triggered_by_user_id=current_user.id,
                docker_image=docker_result.get(
                    "docker_image",
                    settings.REPOSITORY_TEST_DOCKER_IMAGE,
                ),
                command=docker_result.get(
                    "command",
                    settings.REPOSITORY_TEST_COMMAND,
                ),
                tests_ran=True,
                success=success,
                status=run_status,
                exit_code=docker_result.get("exit_code"),
                stdout=docker_result.get("stdout", ""),
                stderr=docker_result.get("stderr", ""),
                duration_seconds=docker_result.get("duration_seconds"),
                has_local_changes=status_info.has_local_changes,
                has_remote_changes=status_info.has_remote_changes,
                message=message,
                finished_at=datetime.now(timezone.utc),
            )

            test_run = await self.test_run_repository.create(test_run)

            return repository, status_info, test_run

        finally:
            if temp_repo_path:
                shutil.rmtree(
                    Path(temp_repo_path).parent,
                    ignore_errors=True,
                )