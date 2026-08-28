"""Playground machine — mirrors formal/tla/middleware/Playground.tla."""
from __future__ import annotations

from enum import Enum

from statemachine import State, StateMachine

CONTROL_PATHS = frozenset({
    "/api/playground", "/health", "/liveness", "/readiness", "/static", "/playground",
})


class PlaygroundMode(str, Enum):
    OFF = "off"
    PROBABILISTIC = "probabilistic"
    SCENARIO = "scenario"


class PlaygroundMachine(StateMachine):
    off = State(PlaygroundMode.OFF.value, initial=True)
    probabilistic = State(PlaygroundMode.PROBABILISTIC.value)
    scenario = State(PlaygroundMode.SCENARIO.value)

    enable_probabilistic = off.to(probabilistic)
    enable_scenario = off.to(scenario)

    def __init__(self) -> None:
        super().__init__()
        self.chaos_applied: dict[str, bool] = {}

    def apply_chaos(self, path: str) -> bool:
        if path in CONTROL_PATHS:
            return False
        if self.current_state.id == PlaygroundMode.OFF.value:
            return False
        self.chaos_applied[path] = True
        return True

    @property
    def control_paths_never_chaosed(self) -> bool:
        return all(not self.chaos_applied.get(p, False) for p in CONTROL_PATHS)
