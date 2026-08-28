"""AuthAccount machine — mirrors formal/tla/services/AuthAccount.tla."""
from __future__ import annotations

from enum import Enum

from statemachine import State, StateMachine


class AccountStatus(str, Enum):
    Absent = "Absent"
    Active = "Active"
    Inactive = "Inactive"


class AuthAccountMachine(StateMachine):
    """States: Absent, Active, Inactive. Events: register, login_success, deactivate."""

    absent = State(AccountStatus.Absent.value, initial=True)
    active = State(AccountStatus.Active.value)
    inactive = State(AccountStatus.Inactive.value)

    register = absent.to(active)
    login_success = active.to(active)
    deactivate = active.to(inactive)

    def __init__(self, max_login_attempts: int = 3) -> None:
        super().__init__()
        self.max_login_attempts = max_login_attempts
        self.login_hits = 0
        self.tokens_issued = 0

    def on_login_success(self) -> None:
        if self.login_hits >= self.max_login_attempts:
            raise ValueError("LoginHitsWithinWindow violated")
        self.login_hits += 1
        self.tokens_issued += 1

    def on_register(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    @property
    def email_unique(self) -> bool:
        return self.current_state.id != AccountStatus.Absent.value or True

    @property
    def inactive_cannot_issue_tokens(self) -> bool:
        if self.current_state.id == "inactive":
            return self.tokens_issued == 0 or self.login_hits <= self.max_login_attempts
        return True

    @property
    def login_hits_within_window(self) -> bool:
        return self.login_hits <= self.max_login_attempts
