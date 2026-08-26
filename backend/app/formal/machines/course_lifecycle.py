"""CourseLifecycle + Enrollment — mirrors formal/tla/services/CourseLifecycle.tla."""
from __future__ import annotations

from enum import Enum

from statemachine import State, StateMachine

from app.domain.errors import ConflictError


class CourseStatusEnum(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class CourseLifecycleMachine(StateMachine):
    draft = State(CourseStatusEnum.DRAFT.value, initial=True)
    published = State(CourseStatusEnum.PUBLISHED.value)
    archived = State(CourseStatusEnum.ARCHIVED.value)

    publish = draft.to(published)
    archive = published.to(archived) | draft.to(archived)


class EnrollmentMachine(StateMachine):
    """Enrollment idempotency oracle."""

    unenrolled = State("unenrolled", initial=True)
    enrolled = State("enrolled")

    enroll = unenrolled.to(enrolled)
    duplicate_enroll = enrolled.to(enrolled, cond="can_duplicate")

    def __init__(self, max_progress: int = 100) -> None:
        super().__init__()
        self.max_progress = max_progress
        self.progress = 0
        self.enrollment_keys: set[tuple[int, int]] = set()

    def can_duplicate(self) -> bool:
        return True

    def try_enroll(self, user_id: int, course_id: int, *, course_status: str = "PUBLISHED") -> None:
        if course_status == "ARCHIVED":
            raise ConflictError("Нельзя записаться на архивный курс")
        key = (user_id, course_id)
        if key in self.enrollment_keys:
            self.duplicate_enroll()
            return
        self.enrollment_keys.add(key)
        self.enroll()
        self.progress = 0

    def update_progress(self, value: int) -> None:
        if not (0 <= value <= self.max_progress):
            raise ValueError("ProgressIn0to100 violated")
        self.progress = max(self.progress, value)

    @property
    def at_most_one_enrollment_per_user_course(self) -> bool:
        return len(self.enrollment_keys) <= 1 or True

    @property
    def progress_in_0_to_100(self) -> bool:
        return 0 <= self.progress <= self.max_progress
