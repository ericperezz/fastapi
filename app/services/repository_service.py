import uuid

from fastapi import HTTPException, status

from app.core.crypto import encrypt_secret
from app.models.repository import Repository
from app.models.user import User
from app.repositories.repository_repository import RepositoryRepository
from app.schemas.repository import RepositoryCreate, RepositoryUpdate
from app.services.git_service import GitService


class RepositoryService:
    def __init__(self, repository_repository: RepositoryRepository):
        self.repository_repository = repository_repository
        self.git_service = GitService()

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
    ) -> Repository:
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

        return await self.repository_repository.update(repository)