"""API управления режимом Playground и WebSocket-канал уведомлений."""
import asyncio

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from app.api.deps import get_current_user, require_roles
from app.domain.enums import Role
from app.domain.models import User
from app.middleware import PlaygroundState

router = APIRouter(prefix="/api/playground", tags=["playground"])

# Единый объект состояния, тот же, что передаётся в middleware (см. main.py).
state = PlaygroundState()


class PlaygroundConfig(BaseModel):
    enabled: bool
    latency_ms: int = Field(default=800, ge=0, le=5_000)
    error_rate: float = Field(default=0.2, ge=0.0, le=1.0)


@router.get("", response_model=PlaygroundConfig)
def get_config(user: User = Depends(get_current_user)) -> PlaygroundConfig:
    return PlaygroundConfig(enabled=state.enabled, latency_ms=state.latency_ms, error_rate=state.error_rate)


@router.put("", response_model=PlaygroundConfig)
def set_config(
    cfg: PlaygroundConfig,
    admin: User = Depends(require_roles(Role.ADMIN)),
) -> PlaygroundConfig:
    """Менять глобальный хаос может только администратор учебного стенда."""
    state.enabled = cfg.enabled
    state.latency_ms = cfg.latency_ms
    state.error_rate = cfg.error_rate
    return cfg


# ---------- WebSocket: демонстрационный поток уведомлений ----------
ws_router = APIRouter(tags=["websocket"])


@ws_router.websocket("/ws/notifications")
async def notifications_ws(websocket: WebSocket) -> None:
    await websocket.accept()
    counter = 0
    try:
        while True:
            await asyncio.sleep(5)
            counter += 1
            await websocket.send_json({
                "type": "notification",
                "message": f"Системное событие #{counter}",
            })
    except WebSocketDisconnect:
        return
