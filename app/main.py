from fastapi import FastAPI
from app.core.config import settings

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