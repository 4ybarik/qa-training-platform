"""Функции, выполняемые отдельным RQ worker-процессом."""
from __future__ import annotations

import time


def process_payload(payload: dict, delay_ms: int = 0, should_fail: bool = False) -> dict:
    if delay_ms:
        time.sleep(delay_ms / 1000)
    if should_fail:
        raise RuntimeError("Controlled queue job failure")
    values = payload.get("values", [])
    return {
        "processed": True,
        "items": len(values),
        "sum": sum(value for value in values if isinstance(value, (int, float))),
        "payload": payload,
    }
