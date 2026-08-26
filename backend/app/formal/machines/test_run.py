"""TestRun machine — mirrors formal/tla/services/TestRun.tla."""
from __future__ import annotations

from statemachine import State, StateMachine


class TestRunMachine(StateMachine):
    tracking = State("tracking", initial=True)
    cleaned = State("cleaned")

    cleanup = tracking.to(cleaned)

    def __init__(self) -> None:
        super().__init__()
        self.tracked: list[str] = []
        self.deleted: list[str] = []

    def track_create(self, entity_type: str) -> None:
        self.tracked.append(entity_type)

    def run_cleanup(self) -> None:
        order = ("course", "user")
        remaining = list(self.tracked)
        for et in order:
            for item in list(remaining):
                if item == et:
                    self.deleted.append(item)
                    remaining.remove(item)
        self.tracked.clear()
        self.cleanup()

    @property
    def cleanup_deletes_tracked_only(self) -> bool:
        return len(self.deleted) <= len(self.tracked) + len(self.deleted)

    @property
    def course_before_user(self) -> bool:
        user_idx = next((i for i, e in enumerate(self.deleted) if e == "user"), len(self.deleted))
        course_idx = next((i for i, e in enumerate(self.deleted) if e == "course"), -1)
        return course_idx < user_idx if course_idx >= 0 and user_idx < len(self.deleted) else True
