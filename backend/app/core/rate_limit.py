"""Ограничение частоты запросов (rate limiting).

Реализация в памяти — скользящее окно по ключу. Интерфейс намеренно простой,
чтобы при необходимости заменить хранилище на Redis без изменения вызывающего кода.
"""
import threading
import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_attempts: int, window_seconds: int) -> None:
        self._max = max_attempts
        self._window = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, key: str) -> bool:
        """Регистрирует обращение. Возвращает True, если лимит НЕ превышен."""
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > self._window:
                q.popleft()
            if len(q) >= self._max:
                return False
            q.append(now)
            return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._hits.pop(key, None)
