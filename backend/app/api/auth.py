"""API аутентификации: регистрация, вход, refresh, профиль текущего пользователя, выход."""
from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.domain.models import User
from app.domain.schemas import (
    ErrorResponse, LoginRequest, MessageResponse, RefreshRequest,
    RegisterRequest, TokenPair, UserOut,
)
from app.services.auth import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201,
             responses={409: {"model": ErrorResponse}})
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> User:
    return AuthService(db).register(
        payload.email, payload.password, payload.first_name, payload.last_name
    )


@router.post("/login", response_model=TokenPair,
             responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
def login(payload: LoginRequest, request: Request, response: Response,
          db: Session = Depends(get_db)) -> TokenPair:
    client_key = request.client.host if request.client else "global"
    access, refresh, _ = AuthService(db).authenticate(
        payload.email, payload.password, client_key=client_key
    )
    # Кука для серверного веб-интерфейса; API-клиенты используют тело ответа.
    response.set_cookie("access_token", access, httponly=True, samesite="lax")
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair,
             responses={401: {"model": ErrorResponse}})
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    access, refresh_token, _ = AuthService(db).refresh(payload.refresh_token)
    return TokenPair(access_token=access, refresh_token=refresh_token)


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response) -> MessageResponse:
    response.delete_cookie("access_token")
    return MessageResponse(detail="Сеанс завершён")


@router.get("/me", response_model=UserOut, responses={401: {"model": ErrorResponse}})
def me(user: User = Depends(get_current_user)) -> User:
    return user
