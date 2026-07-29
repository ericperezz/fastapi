from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.repository_test_run import RepositoryTestRun

class TestRunRepository:
    def __init__(self, db):
        self.db = db

    async def get_by_id_with_repository(self, test_run_id: UUID):
        stmt = (
            select(RepositoryTestRun)
            .options(selectinload(RepositoryTestRun.repository))
            .where(RepositoryTestRun.id == test_run_id)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()


