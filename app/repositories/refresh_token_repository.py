import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


class RefreshTokenRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, refresh_token: RefreshToken) -> RefreshToken:
        try:
            self.db.add(refresh_token)
            await self.db.commit()
            await self.db.refresh(refresh_token)
            return refresh_token
        except Exception:
            await self.db.rollback()
            raise

    async def get_by_token_hash(
        self,
        token_hash: str
    ) -> RefreshToken | None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def revoke(self, refresh_token: RefreshToken) -> RefreshToken:
        try:
            refresh_token.revoked_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(refresh_token)
            return refresh_token
        except Exception:
            await self.db.rollback()
            raise

    async def revoke_all_by_user_id(
        self,
        user_id: uuid.UUID
    ) -> None:
        try:
            await self.db.execute(
                update(RefreshToken)
                .where(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked_at.is_(None)
                )
                .values(
                    revoked_at=datetime.utcnow()
                )
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise