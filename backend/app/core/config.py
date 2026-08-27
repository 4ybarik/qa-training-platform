"""Конфигурация приложения.

Все параметры читаются из переменных окружения (файл .env). Это единственный
источник конфигурации — слои выше него настроек не знают.
"""
from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Значения, которые заведомо небезопасны для production (встречаются в дефолтах
# этого модуля и docker-compose.yml).
INSECURE_SECRET_KEYS = frozenset({"change-me-in-production", "dev-secret-change-me"})


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

    # Учебная инфраструктура. Test Data API и контролируемые мутации доступны
    # только в development/test, но даже там требуют явный ключ/флаг.
    test_support_key: str = "local-test-support-key"
    allow_test_mutations: bool = False

    # Интеграционные мишени.
    redis_url: str = "redis://redis:6379/0"
    external_service_url: str = "http://wiremock:8080"
    quality_history_dir: str = "/app/quality-history"
    # Локальный runner исполняет произвольный Python и допустим только на
    # персональном учебном стенде. В production всегда должен использоваться
    # отдельный контейнерный исполнитель.
    ide_allow_local_runner: bool = True

    @model_validator(mode="after")
    def _guard_production_secrets(self) -> "Settings":
        """Fail-fast: не даём стартовать production с заведомо слабым ключом.

        Дефолтные значения SECRET_KEY удобны для локальной разработки, но в
        production с ними JWT можно подделать. Лучше упасть на старте, чем
        обнаружить проблему по инциденту.
        """
        if self.environment == "production" and self.secret_key in INSECURE_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY содержит известное небезопасное значение-заглушку. "
                "Задайте длинный случайный секрет через переменную окружения "
                "SECRET_KEY перед запуском в production."
            )
        if self.environment == "production" and self.debug:
            raise ValueError("DEBUG должен быть отключён в production.")
        if self.environment == "production" and "*" in self.cors_origins:
            raise ValueError("CORS_ORIGINS в production не может содержать '*'.")
        if self.environment == "production" and self.ide_allow_local_runner:
            raise ValueError(
                "IDE_ALLOW_LOCAL_RUNNER должен быть false в production: "
                "произвольный код запускается только в изолированном runner."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
