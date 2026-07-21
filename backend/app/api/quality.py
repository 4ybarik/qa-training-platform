"""API истории стабильности, mutation score и производительности."""
from fastapi import APIRouter, Query

from app.services.quality import quality_history

router = APIRouter(prefix="/api/quality", tags=["quality-history"])


@router.get("/history")
def history(limit: int = Query(default=50, ge=1, le=200)):
    items = quality_history(limit)
    return {"items": items, "total": len(items)}


@router.get("/latest")
def latest():
    items = quality_history(1)
    return items[0] if items else None
