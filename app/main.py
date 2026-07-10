from fastapi import FastAPI
from sqlalchemy import text
from app.core.config import settings
from app.db.session import AsyncSessionLocal

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0"
)


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "environment": settings.APP_ENV
    }


@app.get("/db-check")
async def db_check():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("SELECT 1"))
        return {"db": result.scalar()}