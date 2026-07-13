from fastapi import HTTPException, status
from app.models.user import User


def require_role(user: User, allowed_roles: list[str]) -> None:
    if user.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción"
        )