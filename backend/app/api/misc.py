"""API профиля, уведомлений, администрирования и проверки состояния."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.config import get_settings
from app.core.database import get_db
from app.domain.enums import NotificationStatus, Role
from app.domain.models import User
from app.domain.schemas import (
    AuditLogOut, ErrorResponse, MessageResponse, NotificationCreate, NotificationOut,
    ProfileOut, ProfileUpdate, RoleUpdate, UserActiveUpdate, UserOut,
)
from app.services.admin import AdminService, NotificationService, ProfileService

# ---------- Профиль ----------
profile_router = APIRouter(prefix="/api/profile", tags=["profile"])


@profile_router.get("", response_model=ProfileOut)
def get_profile(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> ProfileOut:
    svc = ProfileService(db)
    p = svc.get(user.id)
    return ProfileOut(phone=p.phone, birthday=p.birthday, address=p.address,
                      avatar_url=p.avatar_url, skills=svc.skills_list(p))


@profile_router.put("", response_model=ProfileOut)
def update_profile(data: ProfileUpdate, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)) -> ProfileOut:
    svc = ProfileService(db)
    p = svc.update(user.id, data)
    return ProfileOut(phone=p.phone, birthday=p.birthday, address=p.address,
                      avatar_url=p.avatar_url, skills=svc.skills_list(p))


# ---------- Уведомления ----------
notif_router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@notif_router.get("", response_model=list[NotificationOut])
def list_notifications(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    status: NotificationStatus | None = Query(default=None),
    offset: int = Query(default=0, ge=0), limit: int = Query(default=20, ge=1, le=100),
):
    return NotificationService(db).list_for_user(user.id, status, offset, limit)


@notif_router.post("/{notification_id}/read", response_model=NotificationOut,
                   responses={404: {"model": ErrorResponse}})
def mark_read(notification_id: int, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    return NotificationService(db).mark_read(user.id, notification_id)


@notif_router.delete("/{notification_id}", response_model=MessageResponse,
                     responses={404: {"model": ErrorResponse}})
def delete_notification(notification_id: int, user: User = Depends(get_current_user),
                        db: Session = Depends(get_db)) -> MessageResponse:
    NotificationService(db).delete(user.id, notification_id)
    return MessageResponse(detail="Уведомление удалено")


# ---------- Администрирование (только ADMIN) ----------
admin_router = APIRouter(prefix="/api/admin", tags=["admin"])


@admin_router.get("/users", response_model=list[UserOut])
def list_users(_: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db)):
    return AdminService(db).list_users()


@admin_router.put("/users/{user_id}/role", response_model=UserOut,
                  responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def set_role(user_id: int, payload: RoleUpdate,
             actor: User = Depends(require_roles(Role.ADMIN)),
             db: Session = Depends(get_db)):
    return AdminService(db).set_role(actor, user_id, payload.role)


@admin_router.put("/users/{user_id}/active", response_model=UserOut,
                  responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def set_active(user_id: int, payload: UserActiveUpdate,
               actor: User = Depends(require_roles(Role.ADMIN)),
               db: Session = Depends(get_db)):
    return AdminService(db).set_active(actor, user_id, payload.is_active)


@admin_router.post("/notifications", response_model=list[NotificationOut], status_code=201,
                   responses={404: {"model": ErrorResponse}})
def create_notification(payload: NotificationCreate,
                        actor: User = Depends(require_roles(Role.ADMIN)),
                        db: Session = Depends(get_db)):
    """Создаёт уведомление одному пользователю (user_id указан) либо всем (user_id=null)."""
    return NotificationService(db).create_for_admin(actor.id, payload.user_id, payload.message)


@admin_router.get("/audit", response_model=list[AuditLogOut])
def audit(_: User = Depends(require_roles(Role.ADMIN)), db: Session = Depends(get_db),
          limit: int = Query(default=100, ge=1, le=500)):
    return AdminService(db).audit_logs(limit)


# ---------- Проверка состояния ----------
health_router = APIRouter(tags=["health"])


@health_router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": get_settings().app_version}


@health_router.get("/liveness")
def liveness() -> dict:
    return {"status": "alive"}


@health_router.get("/readiness")
def readiness(db: Session = Depends(get_db)) -> dict:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
