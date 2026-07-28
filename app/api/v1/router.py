from fastapi import APIRouter
from app.api.v1.endpoints import auth, users, repositories

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(users.router)

api_router.include_router(
    repositories.router,
    prefix="/repositories",
    tags=["repositories"],
)