"""Зависимости FastAPI: извлечение текущего пользователя и проверка ролей.

Токен принимается двумя способами:
- заголовок Authorization: Bearer <token>  — для API/автотестов;
- httpOnly cookie "access_token"             — для серверного веб-интерфейса.
"""
import jwt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core import security
from app.core.database import get_db
from app.domain.enums import Role
from app.domain.models import User
from app.repositories.users import UserRepository

def _cred_exc() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учётные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization")
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get("access_token")


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = _extract_token(request)
    if not token:
        raise _cred_exc()
    try:
        payload = security.decode_token(token)
    except jwt.PyJWTError:
        raise _cred_exc()
    if payload.get("type") != security.ACCESS:
        raise _cred_exc()
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise _cred_exc()
    user = UserRepository(db).get(user_id)
    if not user or not user.is_active:
        raise _cred_exc()
    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Для веб-страниц: вернуть пользователя, если авторизован, иначе None."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


def require_roles(*roles: Role):
    """Фабрика зависимостей контроля доступа по ролям (RBAC)."""
    allowed = set(roles)

    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Недостаточно прав для выполнения операции",
            )
        return user

    return checker
