"""Бизнес-логика аутентификации, регистрации и обновления токенов."""
import jwt
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import get_settings
from app.core.rate_limit import RateLimiter
from app.domain.errors import AuthError, ConflictError, RateLimitError
from app.domain.enums import Role
from app.domain.models import AuditLog, Notification, Profile, User
from app.repositories.users import UserRepository

settings = get_settings()

# Единый лимитер на процесс (для учебного полигона достаточно).
login_limiter = RateLimiter(settings.rate_limit_login_max, settings.rate_limit_window_seconds)


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)

    def register(self, email: str, password: str, first_name: str, last_name: str) -> User:
        if self.users.get_by_email(email):
            raise ConflictError("Пользователь с таким email уже существует")
        user = User(
            email=email,
            password_hash=security.hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=Role.USER,
        )
        self.users.add(user)
        # Профиль и приветственное уведомление создаём сразу.
        self.db.add(Profile(user_id=user.id))
        self.db.add(Notification(user_id=user.id, message="Добро пожаловать в QA Training Platform!"))
        self.db.add(AuditLog(user_id=user.id, action="user_registered", payload=email))
        self.users.save()
        self.db.refresh(user)
        return user

    def authenticate(self, email: str, password: str, *, client_key: str = "global") -> tuple[str, str, User]:
        if not login_limiter.hit(f"login:{client_key}:{email}"):
            raise RateLimitError("Слишком много попыток входа. Повторите позже.")
        user = self.users.get_by_email(email)
        if not user or not security.verify_password(password, user.password_hash):
            raise AuthError("Неверный email или пароль")
        if not user.is_active:
            raise AuthError("Учётная запись отключена")
        login_limiter.reset(f"login:{client_key}:{email}")
        self.db.add(AuditLog(user_id=user.id, action="user_logged_in", payload=email))
        self.users.save()
        return self._issue(user)

    def refresh(self, refresh_token: str) -> tuple[str, str, User]:
        try:
            payload = security.decode_token(refresh_token)
        except jwt.PyJWTError as exc:  # noqa: PERF203
            raise AuthError("Недействительный refresh-токен") from exc
        if payload.get("type") != security.REFRESH:
            raise AuthError("Ожидался refresh-токен")
        try:
            user_id = int(payload["sub"])
        except (KeyError, TypeError, ValueError) as exc:
            raise AuthError("Недействительный refresh-токен") from exc
        user = self.users.get(user_id)
        if not user:
            raise AuthError("Пользователь не найден")
        return self._issue(user)

    def _issue(self, user: User) -> tuple[str, str, User]:
        access = security.create_access_token(str(user.id), user.role.value)
        refresh = security.create_refresh_token(str(user.id))
        return access, refresh, user
