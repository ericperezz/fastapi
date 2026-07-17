import uuid
from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.core.security import decode_token
from app.repositories.user_repository import UserRepository
from app.models.user import User
from app.core.permissions import require_role

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    auto_error=False
)


async def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    docs_access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    raw_token = token or docs_access_token

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(raw_token)

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )

        user_uuid = uuid.UUID(user_id)

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )

    repository = UserRepository(db)
    user = await repository.get_by_id(user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario inactivo"
        )

    return user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
):
    require_role(current_user, ["admin"])
    return current_user

async def get_current_user_from_docs_cookie(
    docs_access_token: str | None = Cookie(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    if not docs_access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado",
        )

    try:
        payload = decode_token(docs_access_token)

        user_id = payload.get("sub")
        token_type = payload.get("type")

        if not user_id or token_type != "access":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )

        user_uuid = uuid.UUID(user_id)

    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    repository = UserRepository(db)

    user = await repository.get_by_id(user_uuid)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario inactivo",
        )

    return user

async def get_current_admin_from_docs_cookie(
    current_user: User = Depends(get_current_user_from_docs_cookie),
) -> User:
    require_role(current_user, ["admin"])
    return current_user