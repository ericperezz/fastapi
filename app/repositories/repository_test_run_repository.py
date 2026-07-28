from sqlalchemy.ext.asyncio import AsyncSession

from app.models.repository_test_run import RepositoryTestRun


class RepositoryTestRunRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, test_run: RepositoryTestRun) -> RepositoryTestRun:
        self.db.add(test_run)
        await self.db.commit()
        await self.db.refresh(test_run)
        return test_run