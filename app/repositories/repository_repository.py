import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository import Repository


class RepositoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, repository: Repository) -> Repository:
        self.db.add(repository)
        await self.db.commit()
        await self.db.refresh(repository)
        return repository

    async def get_by_id(self, repository_id: uuid.UUID) -> Repository | None:
        result = await self.db.execute(
            select(Repository).where(Repository.id == repository_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_owner(
        self,
        repository_id: uuid.UUID,
        owner_user_id: uuid.UUID,
    ) -> Repository | None:
        result = await self.db.execute(
            select(Repository).where(
                Repository.id == repository_id,
                Repository.owner_user_id == owner_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_name_for_owner(
        self,
        name: str,
        owner_user_id: uuid.UUID,
    ) -> Repository | None:
        result = await self.db.execute(
            select(Repository).where(
                Repository.name == name,
                Repository.owner_user_id == owner_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Repository]:
        result = await self.db.execute(
            select(Repository).order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_by_owner(
        self,
        owner_user_id: uuid.UUID,
    ) -> list[Repository]:
        result = await self.db.execute(
            select(Repository)
            .where(Repository.owner_user_id == owner_user_id)
            .order_by(Repository.created_at.desc())
        )
        return list(result.scalars().all())

    async def update(self, repository: Repository) -> Repository:
        try:
            await self.db.commit()
            await self.db.refresh(repository)
            return repository
        except Exception:
            await self.db.rollback()
            raise

    async def delete(self, repository: Repository) -> None:
        await self.db.delete(repository)
        await self.db.commit()