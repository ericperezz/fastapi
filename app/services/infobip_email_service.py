import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

class AsyncEmailRateLimiter:
    def __init__(self, rate_per_minute: int):
        self.rate_per_minute = max(rate_per_minute, 1)
        self.interval_seconds = 60 / self.rate_per_minute
        self._lock = asyncio.Lock()
        self._next_allowed_time = 0.0

    async def wait(self) -> None:
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()

            sleep_for = max(0.0, self._next_allowed_time - now)
            self._next_allowed_time = max(now, self._next_allowed_time) + self.interval_seconds

        if sleep_for > 0:
            await asyncio.sleep(sleep_for)

class InfobipEmailService:
    def __init__(self):
        self.base_url = settings.INFOBIP_BASE_URL.rstrip("/")
        self.api_key = settings.INFOBIP_API_KEY
        self.sender = settings.INFO_MAIL

        self.rate_limiter = AsyncEmailRateLimiter(
            settings.REPORT_EMAIL_RATE_LIMIT_PER_MINUTE
        )

    async def send_report(
        self,
        subject: str,
        html: str,
        recipients: list[str] | None = None,
    ) -> None:
        final_recipients = recipients or settings.report_recipients_list()

        if not self.base_url:
            raise ValueError("INFOBIP_BASE_URL no está configurado")

        if not self.api_key:
            raise ValueError("INFOBIP_API_KEY no está configurado")

        if not self.sender:
            raise ValueError("INFO_MAIL no está configurado")

        if not final_recipients:
            raise ValueError("No hay destinatarios configurados para el reporte")

        endpoint = f"{self.base_url}/email/3/send"

        headers = {
            "Authorization": f"App {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            for recipient in final_recipients:
                await self.rate_limiter.wait()

                data = {
                    "from": self.sender,
                    "to": recipient,
                    "subject": subject,
                    "html": html,
                }

                response = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"App {self.api_key}",
                        "Accept": "application/json",
                    },
                    data=data,
                )

                if response.status_code >= 400:
                    raise RuntimeError(
                        f"Infobip error {response.status_code}: {response.text}"
                    )





