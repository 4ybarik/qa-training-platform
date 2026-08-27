"""API учебного маршрута, прогресса и истории попыток."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.domain.models import User
from app.domain.enums import Role
from app.learning.catalog import lessons, serialize_lesson
from app.services.learning import LearningService, serialize_progress, serialize_run


router = APIRouter(prefix="/api/learning", tags=["learning"])


@router.get("/catalog")
def catalog(
    language: str = Query(default="ru", pattern="^(ru|en)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    progress = LearningService(db).progress_map(user.id)
    items = []
    for lesson in lessons(language):
        data = serialize_lesson(lesson)
        data["progress"] = serialize_progress(progress.get(lesson.slug))
        items.append(data)
    return {"items": items, "total": len(items)}


@router.get("/progress")
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service = LearningService(db)
    progress_by_slug = service.progress_map(user.id)
    return {
        "summary": service.summary(user.id),
        "items": {
            slug: serialize_progress(item) for slug, item in progress_by_slug.items()
        },
    }


@router.get("/runs")
def runs(
    limit: int = Query(default=50, ge=1, le=200),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = LearningService(db).runs(user.id, limit)
    return {"items": [serialize_run(item) for item in items], "total": len(items)}


@router.get("/manage/progress")
def manage_progress(
    instructor: User = Depends(require_roles(Role.MANAGER, Role.ADMIN)),
    db: Session = Depends(get_db),
):
    items = LearningService(db).learner_overview()
    return {"items": items, "total": len(items)}
