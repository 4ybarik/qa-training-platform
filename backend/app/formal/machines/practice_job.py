"""PracticeJob machine — mirrors formal/tla/practice/Job.tla."""
from __future__ import annotations

from enum import Enum

from statemachine import State, StateMachine


class JobStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class PracticeJobMachine(StateMachine):
    pending = State(JobStatus.PENDING.value, initial=True)
    completed = State(JobStatus.COMPLETED.value, final=True)
    failed = State(JobStatus.FAILED.value, final=True)

    complete = pending.to(completed)
    fail = pending.to(failed)

    def __init__(self, polls_to_complete: int = 2, never_complete: bool = False) -> None:
        super().__init__()
        self.polls = 0
        self.polls_to_complete = polls_to_complete
        self.never_complete = never_complete
        self.outcome = "completed"

    def poll(self) -> JobStatus:
        if self.current_state.final:
            return JobStatus(self.current_state.id.upper())
        self.polls += 1
        if not self.never_complete and self.polls >= self.polls_to_complete:
            if self.outcome == "completed":
                self.complete()
            else:
                self.fail()
        return JobStatus(self.current_state.id.upper())

    @property
    def terminal_is_stable(self) -> bool:
        if self.current_state.final:
            return True
        return self.polls <= self.polls_to_complete + 1
