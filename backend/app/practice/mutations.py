"""Реестр безопасных контролируемых дефектов для оценки ученических тестов."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from fastapi import Request

from app.core.config import get_settings


@dataclass(frozen=True)
class Mutation:
    id: str
    target: str
    description: str


MUTATIONS: tuple[Mutation, ...] = (
    Mutation("health-status", "GET /health", "Поле status содержит неверное значение."),
    Mutation(
        "practice-list-phantom",
        "GET /api/practice/resources",
        "Пустой список содержит фантомный ресурс.",
    ),
    Mutation(
        "schema-wrong-type",
        "GET /api/practice/schema/stable",
        "Поле id стабильной схемы меняет тип int на string.",
    ),
    Mutation(
        "pagination-ignore-size",
        "GET /api/practice/resources",
        "Параметр size игнорируется.",
    ),
    Mutation(
        "etag-ignore-if-match",
        "PUT /api/practice/resources/{id}",
        "Устаревший If-Match ошибочно принимается.",
    ),
    Mutation(
        "resource-delete-noop",
        "DELETE /api/practice/resources/{id}",
        "Удаление отвечает 204, но сохраняет ресурс.",
    ),
    Mutation(
        "rate-limit-disabled",
        "GET /api/practice/rate-limit",
        "Лимит запросов никогда не возвращает 429.",
    ),
    Mutation(
        "job-never-completes",
        "GET /api/practice/jobs/{id}",
        "Асинхронная задача навсегда остаётся PENDING.",
    ),
    Mutation(
        "file-content-corrupted",
        "GET /api/practice/files/{id}",
        "Скачанный файл отличается от загруженного.",
    ),
    Mutation(
        "webhook-sequence-duplicate",
        "POST /api/practice/webhooks",
        "Каждое событие получает sequence=1.",
    ),
    Mutation("login-redirect", "POST /web/login", "Успешный вход ведёт не в dashboard."),
    Mutation("language-noop", "POST /web/language", "Переключатель не сохраняет язык."),
)

MUTATION_IDS = frozenset(item.id for item in MUTATIONS)


def is_active(request: Request, mutation_id: str) -> bool:
    settings = get_settings()
    return (
        settings.environment in {"development", "test"}
        and settings.allow_test_mutations
        and mutation_id in MUTATION_IDS
        and request.headers.get("X-Test-Mutation") == mutation_id
    )


def serialize_mutations() -> list[dict[str, str]]:
    return [asdict(item) for item in MUTATIONS]
