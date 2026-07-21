"""Чтение постоянной истории CI без зависимости от Jenkins API."""
from __future__ import annotations

import json
from pathlib import Path

from app.core.config import get_settings


def quality_history(limit: int = 50) -> list[dict]:
    path = Path(get_settings().quality_history_dir) / "history.jsonl"
    if not path.exists():
        return []
    entries = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(entries[-limit:]))
