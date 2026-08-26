"""RateLimiter machine — mirrors formal/tla/core/RateLimiter.tla."""
from __future__ import annotations

from collections import defaultdict, deque
import time

from statemachine import State, StateMachine


class RateLimiterMachine(StateMachine):
    idle = State("idle", initial=True)
    counting = State("counting")
    rejected = State("rejected")

    hit = idle.to(counting) | counting.to(counting)
    reject = counting.to(rejected) | rejected.to(rejected, cond="still_over_limit")
    reset = counting.to(idle) | rejected.to(idle)

    def __init__(self, max_attempts: int = 3, window_seconds: int = 60) -> None:
        super().__init__()
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def still_over_limit(self) -> bool:
        return True

    def try_hit(self, key: str) -> bool:
        now = time.monotonic()
        q = self._hits[key]
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= self.max_attempts:
            self.reject()
            return False
        q.append(now)
        self.hit()
        return True

    def do_reset(self, key: str) -> None:
        self._hits.pop(key, None)
        self.reset()

    @property
    def hits_never_exceed_max_inside_window(self) -> bool:
        return all(len(q) <= self.max_attempts for q in self._hits.values())
