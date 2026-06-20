"""Репозитории экзаменов, уведомлений и аудита."""
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.domain.models import (
    AuditLog, Exam, Notification, Question,
)
from app.domain.enums import NotificationStatus


class ExamRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_course(self, course_id: int) -> list[Exam]:
        return list(
            self.db.scalars(
                select(Exam)
                .where(Exam.course_id == course_id)
                .options(selectinload(Exam.questions).selectinload(Question.answers))
            )
        )

    def get_with_questions(self, exam_id: int) -> Exam | None:
        return self.db.scalar(
            select(Exam)
            .where(Exam.id == exam_id)
            .options(selectinload(Exam.questions).selectinload(Question.answers))
        )

    def add(self, exam: Exam) -> Exam:
        self.db.add(exam)
        self.db.flush()
        return exam

    def delete(self, exam: Exam) -> None:
        self.db.delete(exam)


class NotificationRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, notification_id: int) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def list_for_user(
        self, user_id: int, status: NotificationStatus | None = None,
        offset: int = 0, limit: int = 20,
    ) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        if status:
            stmt = stmt.where(Notification.status == status)
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        return list(self.db.scalars(stmt))

    def add(self, notification: Notification) -> Notification:
        self.db.add(notification)
        self.db.flush()
        return notification

    def delete(self, notification: Notification) -> None:
        self.db.delete(notification)


class AuditRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def add(self, log: AuditLog) -> AuditLog:
        self.db.add(log)
        self.db.flush()
        return log

    def list_recent(self, limit: int = 100) -> list[AuditLog]:
        return list(
            self.db.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
        )
