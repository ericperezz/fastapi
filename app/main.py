import logging

from fastapi import FastAPI, Request
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi import _rate_limit_exceeded_handler

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logger import get_logger
from app.core.rate_limit import limiter
from app.core.startup_checks import check_database_connection
from app.db.session import engine
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from fastapi.middleware.cors import CORSMiddleware


logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)

logger = get_logger("main")

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    if settings.APP_ENV == "testing":
        return

    database_ok = await check_database_connection()

    if not database_ok:
        logger.error("❌ Error al verificar la conexión de base de datos")

        if settings.DB_REQUIRED_ON_STARTUP:
            raise RuntimeError("No se pudo conectar a la base de datos")


@app.on_event("shutdown")
async def shutdown_event():
    await engine.dispose()


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.APP_ENV
    }

@app.exception_handler(RateLimitExceeded)
async def custom_rate_limit_handler(
    request: Request,
    exc: RateLimitExceeded
):
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Demasiadas solicitudes. Intenta nuevamente más tarde."
        }
    )