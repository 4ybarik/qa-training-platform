"""Конфигурация приложения.

Все параметры читаются из переменных окружения (файл .env). Это единственный
источник конфигурации — слои выше него настроек не знают.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Общие
    app_name: str = "QA Training Platform"
    # Версия приложения. Источник правды — Git-теги (формат vX.Y.Z по SemVer).
    # Значение сюда попадает не вручную, а автоматически при сборке Docker-образа:
    # Dockerfile принимает build-arg APP_VERSION (см. docker-compose.yml, где он
    # подставляется из `git describe --tags`) и прокидывает его как переменную
    # окружения APP_VERSION, которую Settings читает здесь. Локально без Docker
    # (просто `uvicorn app.main:app`) используется дефолт "0.0.0-dev" — это
    # сигнал, что версия не была подставлена сборкой.
    app_version: str = "0.0.0-dev"
    environment: str = "development"
    debug: bool = True

    # База данных. Для Docker — postgres, для тестов переопределяется на sqlite.
    database_url: str = "postgresql+psycopg://qatp:qatp@db:5432/qatp"

    # Безопасность / JWT
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    jwt_algorithm: str = "HS256"

    # CORS
    cors_origins: list[str] = ["*"]

    # Ограничение частоты (rate limiting)
    rate_limit_login_max: int = 5          # попыток
    rate_limit_window_seconds: int = 60    # за окно

    # Seed
    seed_password: str = "Password123!"


@lru_cache
def get_settings() -> Settings:
    return Settings()
