import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User


class UserRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.email == email.lower(),
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.username == username,
                User.is_deleted == False
            )
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        try:
            self.db.add(user)
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except Exception:
            await self.db.rollback()
            raise

    async def update(self, user: User) -> User:
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except Exception:
            await self.db.rollback()
            raise

    async def list_users(self, limit: int = 20, offset: int = 0) -> list[User]:
        result = await self.db.execute(
            select(User)
            .where(User.is_deleted == False)
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())
    
    async def get_by_email_any_status(self, email: str) -> User | None:
        result = await self.db.execute(
        select(User).where(
            User.email == email.lower()
        )
    )
        return result.scalar_one_or_none()
    
    async def get_by_username_any_status(self, username: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                User.username == username
            )
        )
        return result.scalar_one_or_none()