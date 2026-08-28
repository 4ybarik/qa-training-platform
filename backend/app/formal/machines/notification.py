"""Notification machine — mirrors formal/tla/services/Notification.tla."""
from __future__ import annotations

from enum import Enum

from statemachine import State, StateMachine


class NotificationStatusEnum(str, Enum):
    UNREAD = "UNREAD"
    READ = "READ"


class NotificationMachine(StateMachine):
    unread = State(NotificationStatusEnum.UNREAD.value, initial=True)
    read = State(NotificationStatusEnum.READ.value)

    mark_read = unread.to(read)

    def __init__(self, owner_id: int) -> None:
        super().__init__()
        self.owner_id = owner_id
        self.deleted = False

    def mark_read_for(self, actor_id: int) -> None:
        if actor_id != self.owner_id:
            raise PermissionError("NoCrossUserMutation")
        self.mark_read()

    def delete_for(self, actor_id: int) -> None:
        if actor_id != self.owner_id:
            raise PermissionError("NoCrossUserMutation")
        self.deleted = True
