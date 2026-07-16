import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logger import get_logger
from app.models.audit_log import AuditLog

logger = get_logger("audit")


class AuditService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log_event(
        self,
        event_type: str,
        actor_user_id: uuid.UUID | None = None,
        metadata: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None
    ) -> None:
        """
        Registra un evento de auditoría.

        Importante:
        Este método no debe romper el flujo principal.
        Si falla la auditoría, se registra warning y continúa.
        """

        try:
            audit_log = AuditLog(
                actor_user_id=actor_user_id,
                event_type=event_type,
                metadata_=metadata,
                ip_address=ip_address,
                user_agent=user_agent
            )

            self.db.add(audit_log)
            await self.db.commit()

        except Exception as e:
            await self.db.rollback()

            logger.warning(
                f"⚠️ No se pudo registrar auditoría: "
                f"{type(e).__name__} - {str(e)}"
            )