"""Встроенная IDE платформы: файлы решений, запуск тестов, поиск локаторов.

Эндпоинты дают запись на диск в ``student_tests/`` и исполняют pytest, поэтому
маршруты существуют только в development/test окружении — в production они
отвечают 404 (тот же приём, что и у Test Data API).
"""
from __future__ import annotations

import html.parser
import os
import subprocess
import sys
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(prefix="/api/ide", tags=["ide"])
settings = get_settings()

MAX_OUTPUT_CHARS = 8000
RUN_TIMEOUT_SECONDS = 180


def _student_tests_dir() -> Path:
    """Корень student_tests: в Docker он смонтирован в /app/workspace,
    при локальном запуске без Docker лежит рядом с каталогом backend/."""
    candidates = [
        Path(os.getenv("IDE_WORKSPACE_ROOT", "/app/workspace")) / "student_tests",
        Path(__file__).resolve().parents[3] / "student_tests",
    ]
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    raise HTTPException(
        status_code=503,
        detail="Каталог student_tests не найден. Смонтируйте репозиторий в контейнер.",
    )


def _require_dev() -> None:
    if settings.environment not in {"development", "test"}:
        raise HTTPException(status_code=404, detail="Not found")


def _safe_path(relative: str) -> Path:
    """Путь внутри student_tests; защита от traversal за пределы каталога."""
    root = _student_tests_dir()
    candidate = (root / relative).resolve()
    if root.resolve() not in candidate.parents:
        raise HTTPException(status_code=400, detail="Путь вне student_tests запрещён")
    if not candidate.name.startswith("test_") or candidate.suffix != ".py":
        raise HTTPException(
            status_code=400,
            detail="Разрешены только файлы вида test_*.py внутри student_tests",
        )
    return candidate


class FileSave(BaseModel):
    path: str = Field(min_length=1, max_length=256)
    content: str = Field(max_length=512 * 1024)


class FileRun(BaseModel):
    path: str = Field(min_length=1, max_length=256)


@router.get("/files")
def list_files() -> dict:
    """Список учебных файлов (test_*.py) относительно student_tests."""
    _require_dev()
    root = _student_tests_dir()
    files = sorted(
        str(path.relative_to(root))
        for path in root.rglob("*.py")
        if path.name.startswith("test_")
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )
    return {"root": root.name, "files": files}


@router.get("/file")
def read_file(path: str) -> dict:
    _require_dev()
    target = _safe_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="Файл не найден")
    return {"path": path, "content": target.read_text(encoding="utf-8")}


@router.put("/file")
def save_file(payload: FileSave) -> dict:
    _require_dev()
    target = _safe_path(payload.path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"path": payload.path, "bytes": len(payload.content.encode("utf-8"))}


@router.post("/run")
def run_tests(payload: FileRun) -> dict:
    """Прогон одного файла решений. Вывод обрезается до последних строк."""
    _require_dev()
    target = _safe_path(payload.path)
    root = target.parent.parent.parent  # repo root: рядом лежит student_tests/pytest.ini
    env = os.environ.copy()
    env.setdefault("BASE_URL", "http://localhost:8000")
    try:
        completed = subprocess.run(  # noqa: S603 - аргументы зафиксированы выше
            [sys.executable, "-m", "pytest", f"student_tests/{payload.path}", "-q"],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=RUN_TIMEOUT_SECONDS,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        exit_code = completed.returncode
    except subprocess.TimeoutExpired:
        output = f"Таймаут: тесты не завершились за {RUN_TIMEOUT_SECONDS} секунд."
        exit_code = -1
    return {
        "exit_code": exit_code,
        "output": output[-MAX_OUTPUT_CHARS:],
        "truncated": len(output) > MAX_OUTPUT_CHARS,
    }


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
async def find_locators(request: Request, url: str) -> dict:
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


