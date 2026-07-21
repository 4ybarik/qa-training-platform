"""Управление одноразовыми данными ученических автотестов."""
from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.domain.enums import CourseStatus, Role
from app.domain.models import AuditLog, Course, Profile, TestRunEntity, User


class TestSupportService:
    """Создаёт и адресно удаляет сущности одного ``X-Test-Run-Id``."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def create_user(
        self,
        run_id: str,
        *,
        email: str | None,
        password: str,
        role: Role,
        first_name: str,
        last_name: str,
    ) -> User:
        # ``.local`` is rejected by some strict EmailStr validators.  The
        # reserved ``example.com`` domain remains non-deliverable for this
        # training environment while being accepted by strict EmailStr
        # validators used by the authentication API.
        resolved_email = email or f"autotest-{uuid4().hex}@example.com"
        existing = self.db.scalar(select(User).where(User.email == resolved_email))
        if existing is not None:
            raise ValueError("Test user email already exists")
        user = User(
            email=resolved_email,
            password_hash=hash_password(password),
            first_name=first_name,
            last_name=last_name,
            role=role,
        )
        self.db.add(user)
        self.db.flush()
        self.db.add(Profile(user_id=user.id))
        self._track(run_id, "user", user.id)
        self.db.commit()
        self.db.refresh(user)
        return user

    def create_course(
        self,
        run_id: str,
        *,
        title: str,
        description: str,
        price: float,
        category: str,
        status: CourseStatus,
    ) -> Course:
        course = Course(
            title=title,
            description=description,
            price=price,
            category=category,
            status=status,
        )
        self.db.add(course)
        self.db.flush()
        self._track(run_id, "course", course.id)
        self.db.commit()
        self.db.refresh(course)
        return course

    def cleanup(self, run_id: str) -> dict[str, int]:
        tracked = list(
            self.db.scalars(
                select(TestRunEntity)
                .where(TestRunEntity.run_id == run_id)
                .order_by(TestRunEntity.id.desc())
            )
        )
        removed = {"users": 0, "courses": 0}
        # Курсы удаляем раньше пользователей: это сохраняет предсказуемый
        # порядок при появлении новых связей между тестовыми сущностями.
        for entity_type in ("course", "user"):
            for item in tracked:
                if item.entity_type != entity_type:
                    continue
                model = Course if entity_type == "course" else User
                if entity_type == "user":
                    # AuditLog keeps a foreign key to users but is not part of
                    # the user's ORM cascade. Remove those rows first so a
                    # factory-created user can always be disposed safely.
                    self.db.execute(
                        delete(AuditLog).where(AuditLog.user_id == item.entity_id)
                    )
                entity = self.db.get(model, item.entity_id)
                if entity is not None:
                    self.db.delete(entity)
                    removed[f"{entity_type}s"] += 1
        self.db.execute(delete(TestRunEntity).where(TestRunEntity.run_id == run_id))
        self.db.commit()
        return removed

    def _track(self, run_id: str, entity_type: str, entity_id: int) -> None:
        self.db.add(
            TestRunEntity(run_id=run_id, entity_type=entity_type, entity_id=entity_id)
        )
