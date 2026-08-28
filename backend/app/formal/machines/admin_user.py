"""AdminUser machine — mirrors formal/tla/services/AdminUser.tla."""
from __future__ import annotations

from enum import Enum

from statemachine import State, StateMachine


class Role(str, Enum):
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    USER = "USER"


class AdminUserMachine(StateMachine):
    active = State("active", initial=True)
    inactive = State("inactive")

    deactivate = active.to(inactive)

    def __init__(self, actor_role: Role, actor_id: int, target_id: int) -> None:
        super().__init__()
        self.actor_role = actor_role
        self.actor_id = actor_id
        self.target_id = target_id
        self.target_role = Role.USER
        self.target_active = True

    def set_role(self, new_role: Role) -> None:
        if self.actor_role != Role.ADMIN:
            raise PermissionError("OnlyAdminMutatesUsers")
        self.target_role = new_role

    def set_active(self, is_active: bool) -> None:
        if self.actor_role != Role.ADMIN:
            raise PermissionError("OnlyAdminMutatesUsers")
        if self.actor_id == self.target_id and not is_active:
            raise PermissionError("ActorCannotDeactivateSelf")
        self.target_active = is_active
        if not is_active:
            self.deactivate()
