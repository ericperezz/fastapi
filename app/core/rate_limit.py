from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings


def get_client_ip_for_rate_limit(request):
    """
    Obtiene la IP para aplicar rate limiting.

    Primero intenta usar X-Forwarded-For, útil si estás detrás de proxy.
    Si no existe, usa la IP directa del cliente.
    """

    forwarded_for = request.headers.get("x-forwarded-for")

    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return get_remote_address(request)


limiter = Limiter(
    key_func=get_client_ip_for_rate_limit,
    storage_uri=settings.RATE_LIMIT_STORAGE_URI,
    enabled=settings.RATE_LIMIT_ENABLED,
    headers_enabled=True
)