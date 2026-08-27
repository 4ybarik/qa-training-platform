"""ORM-модели (слой предметной области / данных).

Структура таблиц соответствует техническому заданию: users, profiles, courses,
enrollments, exams, questions, answers, notifications, audit_logs.
"""
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean, Date, DateTime, Enum, Float, ForeignKey, Integer, String, Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.domain.enums import (
    CourseStatus, NotificationStatus, QuestionType, Role,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), default="")
    last_name: Mapped[str] = mapped_column(String(100), default="")
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.USER, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    profile: Mapped["Profile"] = relationship(back_populates="user", uselist=False, cascade="all, delete-orphan")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    exam_attempts: Mapped[list["ExamAttempt"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    practice_runs: Mapped[list["PracticeRun"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    practice_progress: Mapped[list["PracticeProgress"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    birthday: Mapped[date | None] = mapped_column(Date)
    address: Mapped[str | None] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    skills: Mapped[str | None] = mapped_column(Text)  # хранится как CSV для простоты

    user: Mapped["User"] = relationship(back_populates="profile")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[float] = mapped_column(Float, default=0.0)
    category: Mapped[str] = mapped_column(String(100), index=True, default="general")
    status: Mapped[CourseStatus] = mapped_column(Enum(CourseStatus), default=CourseStatus.PUBLISHED)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    exams: Mapped[list["Exam"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    enrollments: Mapped[list["Enrollment"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0..100
    enrolled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="enrollments")
    course: Mapped["Course"] = relationship(back_populates="enrollments")


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=15)

    course: Mapped["Course"] = relationship(back_populates="exams")
    questions: Mapped[list["Question"]] = relationship(back_populates="exam", cascade="all, delete-orphan")
    attempts: Mapped[list["ExamAttempt"]] = relationship(
        back_populates="exam", cascade="all, delete-orphan"
    )


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), default=QuestionType.SINGLE)

    exam: Mapped["Exam"] = relationship(back_populates="questions")
    answers: Mapped[list["Answer"]] = relationship(back_populates="question", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False)
    answer: Mapped[str] = mapped_column(String(500), nullable=False)
    is_correct: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship(back_populates="answers")


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(Enum(NotificationStatus), default=NotificationStatus.UNREAD)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="notifications")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class ExamAttempt(Base):
    """История результатов нужна для прогресса и проверяемого сертификата."""

    __tablename__ = "exam_attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id"), nullable=False, index=True)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="exam_attempts")
    exam: Mapped["Exam"] = relationship(back_populates="attempts")


class TestRunEntity(Base):
    """Связывает созданные через Test Data API сущности с тестовым запуском.

    Таблица намеренно не использует внешние ключи: один реестр обслуживает
    разные типы сущностей, а удаление выполняется сервисом в безопасном порядке.
    """

    __tablename__ = "test_run_entities"
    __table_args__ = (
        UniqueConstraint("run_id", "entity_type", "entity_id", name="uq_test_run_entity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class PracticeRun(Base):
    """Одна проверяемая попытка решения практической задачи."""

    __tablename__ = "practice_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    challenge_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(300), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    exit_code: Mapped[int] = mapped_column(Integer, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tests_collected: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tests_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tests_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    output: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    user: Mapped["User"] = relationship(back_populates="practice_runs")
    criteria: Mapped[list["PracticeCriterionResult"]] = relationship(
        back_populates="run", cascade="all, delete-orphan", order_by="PracticeCriterionResult.position"
    )


class PracticeCriterionResult(Base):
    """Результат одного понятного ученику критерия попытки."""

    __tablename__ = "practice_criterion_results"
    __table_args__ = (
        UniqueConstraint("run_id", "position", name="uq_practice_run_criterion"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("practice_runs.id"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    details: Mapped[str] = mapped_column(Text, default="")

    run: Mapped["PracticeRun"] = relationship(back_populates="criteria")


class PracticeProgress(Base):
    """Накопленный прогресс пользователя по задаче, рассчитанный по запускам."""

    __tablename__ = "practice_progress"
    __table_args__ = (
        UniqueConstraint("user_id", "challenge_slug", name="uq_practice_progress_user_challenge"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    challenge_slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    best_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    last_run_id: Mapped[int | None] = mapped_column(ForeignKey("practice_runs.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship(back_populates="practice_progress")
    last_run: Mapped["PracticeRun | None"] = relationship(foreign_keys=[last_run_id])
