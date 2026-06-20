"""Загрузка начальных (демонстрационных) данных.

Создаёт демонстрационные учётные записи (admin/manager/user), пользователей,
курсы, экзамены с вопросами всех типов и уведомления. Идемпотентна: при наличии
данных повторно ничего не создаёт.
"""
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.domain.enums import CourseStatus, QuestionType, Role
from app.domain.models import (
    Answer, Course, Exam, Notification, Profile, Question, User,
)

settings = get_settings()
random.seed(42)

CATEGORIES = ["UI", "API", "Database", "Kafka", "Redis", "Performance", "Security"]
TOPICS = ["Playwright", "Selenium", "Pytest", "REST API", "GraphQL", "SQL",
          "Kafka", "Redis", "Locust", "OWASP", "Contract Testing", "CI/CD"]


def _named_users(pwd: str) -> list[User]:
    return [
        User(email="admin@test.com", password_hash=pwd, first_name="Админ", last_name="Системный", role=Role.ADMIN),
        User(email="manager@test.com", password_hash=pwd, first_name="Менеджер", last_name="Учебный", role=Role.MANAGER),
        User(email="user@test.com", password_hash=pwd, first_name="Пользователь", last_name="Обычный", role=Role.USER),
    ]


def _build_exam(course_id: int, idx: int) -> Exam:
    exam = Exam(course_id=course_id, title=f"Экзамен {idx}", duration_minutes=15)
    # Вопрос одиночного выбора
    q1 = Question(question="Что проверяет UI-тест?", type=QuestionType.SINGLE)
    q1.answers = [
        Answer(answer="Поведение интерфейса", is_correct=True),
        Answer(answer="Скорость диска", is_correct=False),
        Answer(answer="Версию ОС", is_correct=False),
    ]
    # Множественный выбор
    q2 = Question(question="Какие инструменты автоматизируют UI?", type=QuestionType.MULTI)
    q2.answers = [
        Answer(answer="Playwright", is_correct=True),
        Answer(answer="Selenium", is_correct=True),
        Answer(answer="PostgreSQL", is_correct=False),
    ]
    # Текстовый ответ
    q3 = Question(question="Каким атрибутом помечают элементы для тестов?", type=QuestionType.TEXT)
    q3.answers = [Answer(answer="data-testid", is_correct=True)]
    # Drag and drop (моделируется как упорядоченный набор)
    q4 = Question(question="Перетащите в зону ответа уровни пирамиды тестирования", type=QuestionType.DND)
    q4.answers = [
        Answer(answer="Unit", is_correct=True),
        Answer(answer="Integration", is_correct=True),
        Answer(answer="E2E", is_correct=True),
    ]
    q5 = Question(question="HTTP-код успешного ответа?", type=QuestionType.SINGLE)
    q5.answers = [
        Answer(answer="200", is_correct=True),
        Answer(answer="500", is_correct=False),
        Answer(answer="404", is_correct=False),
    ]
    exam.questions = [q1, q2, q3, q4, q5]
    return exam


def seed(db: Session) -> None:
    if db.scalar(select(User).limit(1)):
        return  # уже засеяно

    pwd = hash_password(settings.seed_password)

    users = _named_users(pwd)
    for i in range(1, 31):
        users.append(User(
            email=f"user{i}@test.com", password_hash=pwd,
            first_name=f"Имя{i}", last_name=f"Фамилия{i}", role=Role.USER,
        ))
    db.add_all(users)
    db.flush()
    for u in users:
        db.add(Profile(user_id=u.id))

    # 50 курсов
    courses: list[Course] = []
    for i in range(1, 51):
        topic = TOPICS[i % len(TOPICS)]
        courses.append(Course(
            title=f"{topic}: курс {i}",
            description=f"Учебный курс №{i} по теме «{topic}» для практики автоматизации тестирования.",
            price=float(random.choice([0, 1990, 2990, 4990])),
            category=CATEGORIES[i % len(CATEGORIES)],
            status=CourseStatus.PUBLISHED,
        ))
    db.add_all(courses)
    db.flush()

    # ~100 экзаменов (по 2 на курс) с 5 вопросами => ~500 вопросов
    for course in courses:
        for k in (1, 2):
            db.add(_build_exam(course.id, k))

    # уведомления
    user_ids = [u.id for u in users]
    for n in range(1, 121):
        db.add(Notification(
            user_id=random.choice(user_ids),
            message=f"Демонстрационное уведомление №{n}",
        ))

    db.commit()


def run() -> None:
    init_db()
    with SessionLocal() as db:
        seed(db)
    print("Seed выполнен.")


if __name__ == "__main__":
    run()
