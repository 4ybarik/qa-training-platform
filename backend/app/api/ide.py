"""Встроенная IDE платформы: файлы решений, запуск тестов, поиск локаторов.

Эндпоинты дают запись на диск в ``student_tests/`` и исполняют pytest, поэтому
маршруты существуют только в development/test окружении — в production они
отвечают 404 (тот же приём, что и у Test Data API).
"""
from __future__ import annotations

import html.parser

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.config import get_settings
from app.core.database import get_db
from app.domain.models import User
from app.learning.catalog import lesson_for
from app.learning.grading import grade_lesson
from app.learning.runner import execute_pytest
from app.learning.workspace import safe_test_path, student_tests_dir
from app.practice.catalog import CHALLENGES_BY_SLUG
from app.services.learning import LearningService, serialize_run

router = APIRouter(prefix="/api/ide", tags=["ide"])
settings = get_settings()

def _require_dev() -> None:
    if settings.environment not in {"development", "test"}:
        raise HTTPException(status_code=404, detail="Not found")


class FileCreate(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    content: str = Field(default="", max_length=512 * 1024)


@router.post("/files")
def create_file(payload: FileCreate, user: User = Depends(get_current_user)) -> dict:
    """Создаёт новый файл решения из встроенной IDE."""
    _require_dev()
    target = safe_test_path(payload.path, allow_create=True)
    if target.exists():
        raise HTTPException(status_code=409, detail="Файл уже существует")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"path": payload.path, "bytes": len(payload.content.encode("utf-8"))}



class FileSave(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    content: str = Field(max_length=512 * 1024)


class FileRun(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    challenge_slug: str | None = Field(default=None, min_length=1, max_length=100)


@router.get("/files")
def list_files(user: User = Depends(get_current_user)) -> dict:
    """Список учебных файлов (test_*.py) относительно student_tests."""
    _require_dev()
    root = student_tests_dir()
    files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if path.name.startswith("test_")
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )
    return {"root": root.name, "files": files}


@router.get("/file")
def read_file(path: str, user: User = Depends(get_current_user)) -> dict:
    _require_dev()
    target = safe_test_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@router.put("/file")
def save_file(payload: FileSave, user: User = Depends(get_current_user)) -> dict:
    _require_dev()
    target = safe_test_path(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"path": payload.path, "bytes": len(payload.content.encode("utf-8"))}


@router.delete("/file")
def delete_file(path: str, user: User = Depends(get_current_user)) -> dict:
    """Удаляет файл решения. Файлы под git'ом восстановимы через git checkout."""
    _require_dev()
    target = safe_test_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")
    target.unlink()
    return {"deleted": path}



@router.post("/run")
def run_tests(
    payload: FileRun,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Прогон файла; для урока дополнительно оценивает критерии и прогресс."""
    _require_dev()
    if not settings.ide_allow_local_runner:
        raise HTTPException(status_code=503, detail="Локальный исполнитель IDE отключён")
    target = safe_test_path(payload.path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")
    root = student_tests_dir().parent
    relative_path = f"student_tests/{payload.path}"

    if payload.challenge_slug is None:
        result = execute_pytest(root, relative_path)
        return {
            "exit_code": result.exit_code,
            "output": result.output,
            "truncated": result.truncated,
            "duration_ms": result.duration_ms,
            "tests_collected": result.tests_collected,
            "tests_passed": result.tests_passed,
            "tests_failed": result.tests_failed,
            "score": 100 if result.exit_code == 0 and result.tests_collected else 0,
            "passed": result.exit_code == 0 and result.tests_collected > 0,
            "criteria": [],
        }

    challenge = CHALLENGES_BY_SLUG.get(payload.challenge_slug)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Практическая задача не найдена")
    lesson = lesson_for(challenge, "ru")
    if lesson.editable_path != payload.path:
        raise HTTPException(status_code=400, detail="Файл не соответствует выбранной задаче")
    grade = grade_lesson(root, relative_path, target, lesson)
    run = LearningService(db).record_grade(
        user.id, lesson.slug, payload.path, target, grade,
    )
    return serialize_run(run)


class _LocatorParser(html.parser.HTMLParser):
    """Собирает элементы с data-testid и видимый текст внутри них."""

    _VOID = {"br", "img", "input", "hr", "meta", "link", "source", "wbr"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.items: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        test_id = attrs_dict.get("data-testid")
        known = {item["testid"] for item in self.items}
        if test_id and test_id not in known and len(self.items) < 500:
            self._finish()
            self._current = {
                "tag": tag,
                "testid": test_id,
                "text": "",
                "selector": f'page.get_by_test_id("{test_id}")',
                "css": f'[data-testid="{test_id}"]',
            }
            self.items.append(self._current)
            self._depth = 0 if tag in self._VOID else 1
        elif self._current and tag not in self._VOID:
            self._depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if self._current and self._depth == 0:
            self._finish()

    def handle_data(self, data: str) -> None:
        if self._current:
            self._current["text"] = (self._current["text"] + data).strip()[:80]

    def handle_endtag(self, tag: str) -> None:
        if self._current:
            self._depth -= 1
            if self._depth <= 0:
                self._finish()

    def _finish(self) -> None:
        if self._current and not self._current["text"]:
            self._current["text"] = "(нет текста)"
        self._current = None
        self._depth = 0


@router.get("/locators")
async def find_locators(
    request: Request,
    url: str,
    user: User = Depends(get_current_user),
) -> dict:
    """Все data-testid на странице приложения по её пути (например /login).

    Страницу получаем через ASGI-транспорт собственного приложения — работает
    и под TestClient в юнит-тестах, и под живым uvicorn без сетевых запросов.
    """
    _require_dev()
    if not url.startswith("/") or ".." in url or len(url) > 300:
        raise HTTPException(status_code=400, detail="Ожидается внутренний путь вида /login")
    transport = httpx.ASGITransport(app=request.app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver",
    ) as client:
        response = await client.get(url, follow_redirects=True)
    parser = _LocatorParser()
    parser.feed(response.text)
    return {
        "url": url,
        "final_url": response.url.path,
        "count": len(parser.items),
        "locators": parser.items,
    }
