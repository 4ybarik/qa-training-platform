"""ExamAttempt machine — mirrors formal/tla/services/ExamAttempt.tla."""
from __future__ import annotations

from statemachine import State, StateMachine

PASS_THRESHOLD = 60


class ExamAttemptMachine(StateMachine):
    not_submitted = State("not_submitted", initial=True)
    submitted = State("submitted")

    submit = not_submitted.to(submitted) | submitted.to(submitted)

    def __init__(self, max_progress: int = 100) -> None:
        super().__init__()
        self.score = 0
        self.passed = False
        self.progress = 0
        self.has_enrollment = False
        self.certificate_url: str | None = None
        self.max_progress = max_progress

    def set_enrollment(self) -> None:
        self.has_enrollment = True

    def submit_exam(self, score: int) -> None:
        if not (0 <= score <= 100):
            raise ValueError("score must be 0..100")
        self.submit()
        self.score = score
        self.passed = score >= PASS_THRESHOLD
        self.certificate_url = f"/certificates/exams/1" if self.passed else None
        if self.has_enrollment:
            self.progress = (
                self.max_progress if self.passed else max(self.progress, score)
            )

    @property
    def passed_iff_score_ge_60(self) -> bool:
        return self.passed == (self.score >= PASS_THRESHOLD)

    @property
    def certificate_only_if_passed(self) -> bool:
        return self.certificate_url is None or self.passed

    @property
    def progress_monotonic(self) -> bool:
        return 0 <= self.progress <= self.max_progress
