from sqlalchemy import text

from app.core.config import settings
from app.core.logger import get_logger
from app.db.session import engine

logger = get_logger("startup")


async def check_database_connection() -> bool:
    """
    Verifica la conexión al motor de base de datos y a PostgreSQL.
    Muestra:
    - Verde si conecta correctamente.
    - Amarillo si hay advertencias.
    - Rojo si falla.
    """

    try:
        async with engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

        logger.info("✅ Motor de base de datos conectado correctamente")
        logger.info("✅ PostgreSQL conectado correctamente")

        show_startup_warnings()

        return True

    except Exception as e:
        logger.error("❌ No se pudo conectar al motor de base de datos")
        logger.error("❌ No se pudo conectar a PostgreSQL")
        logger.error(f"❌ Error: {type(e).__name__} - {str(e)}")

        return False


def show_startup_warnings() -> None:
    """
    Muestra advertencias simples en amarillo.
    """

    if settings.DEBUG:
        logger.warning("⚠️ DEBUG está activado. Recuerda desactivarlo en producción.")

    if settings.JWT_SECRET_KEY in [
        "change_this_super_secret_key_in_production",
        "secret",
        "123456",
        "changeme"
    ]:
        logger.warning(
            "⚠️ JWT_SECRET_KEY parece ser una clave de desarrollo. "
            "Cámbiala en producción."
        )

    if settings.APP_ENV == "production" and settings.DEBUG:
        logger.warning(
            "⚠️ APP_ENV=production pero DEBUG=true. "
            "Esto no es recomendable."
        )
    
    if settings.APP_ENV == "production" and settings.RATE_LIMIT_STORAGE_URI == "memory://":
        logger.warning(
        "⚠️ RATE_LIMIT_STORAGE_URI=memory:// no es recomendable en producción. Usa Redis."
    )