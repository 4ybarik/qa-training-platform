"""API управления режимом Playground и WebSocket-канал уведомлений."""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from app.middleware import PlaygroundState

router = APIRouter(prefix="/api/playground", tags=["playground"])

# Единый объект состояния, тот же, что передаётся в middleware (см. main.py).
state = PlaygroundState()


class PlaygroundConfig(BaseModel):
    enabled: bool
    latency_ms: int = 800
    error_rate: float = 0.2


@router.get("", response_model=PlaygroundConfig)
def get_config() -> PlaygroundConfig:
    return PlaygroundConfig(enabled=state.enabled, latency_ms=state.latency_ms, error_rate=state.error_rate)


@router.put("", response_model=PlaygroundConfig)
def set_config(cfg: PlaygroundConfig) -> PlaygroundConfig:
    state.enabled = cfg.enabled
    state.latency_ms = max(0, cfg.latency_ms)
    state.error_rate = min(max(cfg.error_rate, 0.0), 1.0)
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
