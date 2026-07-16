import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.password_reset_token import PasswordResetToken


class PasswordResetTokenRepository:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        password_reset_token: PasswordResetToken
    ) -> PasswordResetToken:
        try:
            self.db.add(password_reset_token)
            await self.db.commit()
            await self.db.refresh(password_reset_token)
            return password_reset_token
        except Exception:
            await self.db.rollback()
            raise

    async def get_by_token_hash(
        self,
        token_hash: str
    ) -> PasswordResetToken | None:
        result = await self.db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    async def mark_as_used(
        self,
        password_reset_token: PasswordResetToken
    ) -> PasswordResetToken:
        try:
            password_reset_token.used_at = datetime.utcnow()
            await self.db.commit()
            await self.db.refresh(password_reset_token)
            return password_reset_token
        except Exception:
            await self.db.rollback()
            raise

    async def invalidate_unused_tokens_by_user_id(
        self,
        user_id: uuid.UUID
    ) -> None:
        try:
            await self.db.execute(
                update(PasswordResetToken)
                .where(
                    PasswordResetToken.user_id == user_id,
                    PasswordResetToken.used_at.is_(None)
                )
                .values(
                    used_at=datetime.utcnow()
                )
            )
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise