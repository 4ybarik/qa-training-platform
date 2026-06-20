"""Pydantic-схемы: контракты запросов и ответов.

Эти модели формируют OpenAPI-документацию (request/response/ошибки).
"""
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.enums import CourseStatus, NotificationStatus, QuestionType, Role


# ---------- Аутентификация ----------
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    first_name: str = Field(default="", max_length=100)
    last_name: str = Field(default="", max_length=100)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class MessageResponse(BaseModel):
    detail: str


class ErrorResponse(BaseModel):
    detail: str


# ---------- Пользователь / профиль ----------
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    email: EmailStr
    first_name: str
    last_name: str
    role: Role
    is_active: bool
    created_at: datetime


class ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    phone: str | None = None
    birthday: date | None = None
    address: str | None = None
    avatar_url: str | None = None
    skills: list[str] = []


class ProfileUpdate(BaseModel):
    phone: str | None = None
    birthday: date | None = None
    address: str | None = None
    skills: list[str] | None = None


class RoleUpdate(BaseModel):
    role: Role


class UserActiveUpdate(BaseModel):
    is_active: bool


# ---------- Курсы ----------
class CourseOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    description: str
    price: float
    category: str
    status: CourseStatus


class CoursePage(BaseModel):
    items: list[CourseOut]
    total: int
    page: int
    size: int


class CourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    price: float = Field(default=0.0, ge=0)
    category: str = Field(default="general", max_length=100)
    status: CourseStatus = CourseStatus.PUBLISHED


class CourseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=4000)
    price: float | None = Field(default=None, ge=0)
    category: str | None = Field(default=None, max_length=100)
    status: CourseStatus | None = None


# ---------- Экзамены ----------
class AnswerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    answer: str


class AnswerAdminOut(BaseModel):
    """Та же сущность, но с признаком правильности — только для ADMIN."""
    model_config = ConfigDict(from_attributes=True)
    id: int
    answer: str
    is_correct: bool


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question: str
    type: QuestionType
    answers: list[AnswerOut]


class QuestionAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    question: str
    type: QuestionType
    answers: list[AnswerAdminOut]


class ExamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    title: str
    duration_minutes: int
    questions: list[QuestionOut] = []


class ExamAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    course_id: int
    title: str
    duration_minutes: int
    questions: list[QuestionAdminOut] = []


class AnswerCreate(BaseModel):
    answer: str = Field(min_length=1, max_length=500)
    is_correct: bool = False


class QuestionCreate(BaseModel):
    question: str = Field(min_length=1)
    type: QuestionType = QuestionType.SINGLE
    answers: list[AnswerCreate] = Field(default_factory=list, min_length=1)


class ExamCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    duration_minutes: int = Field(default=15, ge=1, le=240)
    questions: list[QuestionCreate] = Field(default_factory=list)


class ExamUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    duration_minutes: int | None = Field(default=None, ge=1, le=240)


class SubmittedAnswer(BaseModel):
    question_id: int
    answer_ids: list[int] = []
    text: str | None = None


class ExamSubmission(BaseModel):
    answers: list[SubmittedAnswer]


class ExamResult(BaseModel):
    exam_id: int
    total: int
    correct: int
    score: int  # процент 0..100
    passed: bool
    certificate_url: str | None = None


# ---------- Уведомления ----------
class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    message: str
    status: NotificationStatus
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: int | None = None  # None = отправить всем пользователям (broadcast)
    message: str = Field(min_length=1, max_length=500)


# ---------- Аудит ----------
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    action: str
    payload: str | None
    created_at: datetime
