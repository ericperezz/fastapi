from fastapi import HTTPException, status
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest
from app.core.security import verify_password, create_access_token


class AuthService:

    def __init__(self, repository: UserRepository):
        self.repository = repository

    async def login(self, data: LoginRequest) -> str:
        user = await self.repository.get_by_email(data.email)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        if not verify_password(data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuario inactivo"
            )

        return create_access_token(str(user.id))