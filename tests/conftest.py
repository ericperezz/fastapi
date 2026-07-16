import os

# ============================================================
# IMPORTANTE:
# Estas variables deben definirse ANTES de importar app.main,
# settings, engine o cualquier módulo de la app.
# ============================================================

os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "false"

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://fastapi_user:fastapi_password"
    "@127.0.0.1:5433/fastapi_test_db"
)

os.environ["DB_REQUIRED_ON_STARTUP"] = "false"

# Desactivar rate limit en tests.
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["RATE_LIMIT_STORAGE_URI"] = "memory://"

# Evita configuraciones problemáticas de Redis durante tests.
os.environ["RATE_LIMIT_REGISTER"] = "1000/minute"
os.environ["RATE_LIMIT_LOGIN"] = "1000/minute"
os.environ["RATE_LIMIT_FORGOT_PASSWORD"] = "1000/minute"

import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app as fastapi_app
from app.db.base import Base
from app.db.session import engine

# Importar modelos para que Base.metadata conozca todas las tablas.
import app.models  # noqa: F401


@pytest_asyncio.fixture(autouse=True)
async def reset_database():
    """
    Limpia y recrea todas las tablas antes de cada test.

    Además hace dispose del engine para evitar conexiones asyncpg
    reutilizadas en mal estado entre tests.
    """

    await engine.dispose()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield

    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    """
    Cliente HTTP async para testear la app sin levantar Uvicorn.
    """

    transport = ASGITransport(app=fastapi_app)

    async with AsyncClient(
        transport=transport,
        base_url="http://testserver"
    ) as async_client:
        yield async_client