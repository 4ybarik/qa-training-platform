"""Безопасная работа с файлами решений внутри ``student_tests``."""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException


ALLOWED_FOLDERS = frozenset({"api", "contract", "integration", "ui"})


def student_tests_dir() -> Path:
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


def safe_test_path(relative: str, *, allow_create: bool = False) -> Path:
    root = student_tests_dir().resolve()
    candidate = (root / relative).resolve()
    if root not in candidate.parents:
        raise HTTPException(status_code=400, detail="Путь вне student_tests запрещён")
    if not candidate.name.startswith("test_") or candidate.suffix != ".py":
        raise HTTPException(
            status_code=400,
            detail="Разрешены только файлы вида test_*.py внутри student_tests",
        )
    if allow_create:
        parent = candidate.parent.relative_to(root).as_posix()
        if parent not in ALLOWED_FOLDERS:
            raise HTTPException(
                status_code=400,
                detail="Новый файл создаётся в api/, contract/, integration/ или ui/",
            )
    return candidate


def ensure_starter(relative: str, content: str) -> tuple[Path, bool]:
    target = safe_test_path(relative, allow_create=True)
    if target.exists():
        return target, False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target, True
