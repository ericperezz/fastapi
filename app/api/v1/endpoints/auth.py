from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.schemas.user import UserCreate, UserResponse
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=UserResponse)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = UserService(repository)
    return await service.create_user(data)


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    db: AsyncSession = Depends(get_db)
):
    repository = UserRepository(db)
    service = AuthService(repository)

    access_token = await service.login(data)

    return TokenResponse(
        access_token=access_token,
        token_type="bearer"
    )