"""Сервисы профиля, уведомлений и администрирования."""
from sqlalchemy.orm import Session

from app.domain.enums import NotificationStatus, Role
from app.domain.errors import NotFoundError, PermissionError_
from app.domain.models import AuditLog, Notification, Profile, User
from app.domain.schemas import ProfileUpdate
from app.repositories.exams import AuditRepository, NotificationRepository
from app.repositories.users import ProfileRepository, UserRepository


class ProfileService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.profiles = ProfileRepository(db)

    def get(self, user_id: int) -> Profile:
        profile = self.profiles.get_by_user(user_id)
        if not profile:
            profile = self.profiles.add(Profile(user_id=user_id))
            self.db.commit()
        return profile

    def update(self, user_id: int, data: ProfileUpdate) -> Profile:
        profile = self.get(user_id)
        if data.phone is not None:
            profile.phone = data.phone
        if data.birthday is not None:
            profile.birthday = data.birthday
        if data.address is not None:
            profile.address = data.address
        if data.skills is not None:
            profile.skills = ",".join(data.skills)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    @staticmethod
    def skills_list(profile: Profile) -> list[str]:
        return [s for s in (profile.skills or "").split(",") if s]


class NotificationService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.repo = NotificationRepository(db)
        self.users = UserRepository(db)

    def list_for_user(self, user_id: int, status: NotificationStatus | None, offset: int, limit: int) -> list[Notification]:
        return self.repo.list_for_user(user_id, status, offset, limit)

    def mark_read(self, user_id: int, notification_id: int) -> Notification:
        n = self.repo.get(notification_id)
        if not n or n.user_id != user_id:
            raise NotFoundError("Уведомление не найдено")
        n.status = NotificationStatus.READ
        self.db.commit()
        self.db.refresh(n)
        return n

    def delete(self, user_id: int, notification_id: int) -> None:
        n = self.repo.get(notification_id)
        if not n or n.user_id != user_id:
            raise NotFoundError("Уведомление не найдено")
        self.repo.delete(n)
        self.db.commit()

    def create_for_admin(self, actor_id: int, target_user_id: int | None, message: str) -> list[Notification]:
        """Создаёт уведомление одному пользователю, либо рассылку всем (target_user_id=None)."""
        if target_user_id is not None:
            if not self.users.get(target_user_id):
                raise NotFoundError("Пользователь не найден")
            targets = [target_user_id]
        else:
            targets = [u.id for u in self.users.list_all()]

        created = [Notification(user_id=uid, message=message) for uid in targets]
        for n in created:
            self.db.add(n)
        scope = f"user:{target_user_id}" if target_user_id is not None else f"broadcast:{len(targets)}"
        self.db.add(AuditLog(user_id=actor_id, action="notification_created", payload=scope))
        self.db.commit()
        for n in created:
            self.db.refresh(n)
        return created


class AdminService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.audit = AuditRepository(db)

    def list_users(self) -> list[User]:
        return self.users.list_all()

    def set_role(self, actor: User, user_id: int, role: Role) -> User:
        if actor.role != Role.ADMIN:
            raise PermissionError_("Недостаточно прав")
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError("Пользователь не найден")
        user.role = role
        self.db.add(AuditLog(user_id=actor.id, action="role_changed", payload=f"{user_id}:{role.value}"))
        self.db.commit()
        self.db.refresh(user)
        return user

    def set_active(self, actor: User, user_id: int, is_active: bool) -> User:
        if actor.role != Role.ADMIN:
            raise PermissionError_("Недостаточно прав")
        user = self.users.get(user_id)
        if not user:
            raise NotFoundError("Пользователь не найден")
        if user.id == actor.id and not is_active:
            raise PermissionError_("Нельзя деактивировать собственную учётную запись")
        user.is_active = is_active
        action = "user_activated" if is_active else "user_deactivated"
        self.db.add(AuditLog(user_id=actor.id, action=action, payload=str(user_id)))
        self.db.commit()
        self.db.refresh(user)
        return user

    def audit_logs(self, limit: int = 100):
        return self.audit.list_recent(limit)
