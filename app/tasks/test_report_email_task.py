import logging
from uuid import UUID

from sqlalchemy import select, func

from app.db.session import AsyncSessionLocal
from app.models.repository_test_run import RepositoryTestRun
from app.repositories.test_run_repository import TestRunRepository
from app.services.infobip_email_service import InfobipEmailService
from app.services.test_report_builder import TestReportBuilder

logger = logging.getLogger(__name__)


async def send_test_report_email_task(
    test_run_id: str,
    recipients: list[str] | None = None,
) -> None:
    try:
        async with AsyncSessionLocal() as db:
            repository = TestRunRepository(db)
            test_run = await repository.get_by_id_with_repository(UUID(test_run_id))

            if not test_run:
                logger.warning(
                    "No se encontró test_run_id=%s para enviar reporte",
                    test_run_id,
                )
                return

            related_repository = getattr(test_run, "repository", None)

            # Calculate the run number for this repository
            run_number = 1
            if related_repository:
                stmt = (
                    select(func.count())
                    .select_from(RepositoryTestRun)
                    .where(
                        RepositoryTestRun.repository_id == related_repository.id,
                        RepositoryTestRun.created_at <= test_run.created_at,
                    )
                )
                result = await db.execute(stmt)
                run_number = result.scalar() or 1

            html = TestReportBuilder.build_html_report(
                test_run=test_run,
                repository=related_repository,
                run_number=run_number,
            )

            status = getattr(test_run, "status", "UNKNOWN")
            success = getattr(test_run, "success", None)

            if success is True:
                result_label = "PASSED"
            elif success is False:
                result_label = "FAILED"
            else:
                result_label = str(status)

            repo_name = ""
            if related_repository:
                repo_name = getattr(related_repository, "name", "") or ""

            subject = f"[Tests {result_label}] Reporte de ejecución"

            if repo_name:
                subject += f" - {repo_name}"

            email_service = InfobipEmailService()

            await email_service.send_report(
                subject=subject,
                html=html,
                recipients=recipients,
            )

            logger.info(
                "Reporte de tests enviado correctamente para test_run_id=%s",
                test_run_id,
            )

    except Exception:
        logger.exception(
            "Error enviando reporte de tests para test_run_id=%s",
            test_run_id,
        )
