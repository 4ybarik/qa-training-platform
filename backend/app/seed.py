"""Загрузка начальных (демонстрационных) данных.

Создаёт демонстрационные учётные записи (admin/manager/user), пользователей,
учебные курсы с экзаменами и вопросами (см. app/seed_content.py), уведомления.
Идемпотентна: при наличии данных повторно ничего не создаёт.

Для обновления учебного контента на существующей базе:
    python -m app.seed --reset-content
(пользователи сохраняются; курсы/экзамены/вопросы/уведомления пересоздаются).
"""
import argparse
import random

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import SessionLocal, init_db
from app.core.security import hash_password
from app.domain.enums import CourseStatus, Role
from app.domain.models import (
    Answer, Course, Enrollment, Exam, ExamAttempt, Notification, Profile,
    Question, User,
)
from app.seed_content import build_courses, build_exams_for

settings = get_settings()
random.seed(42)


def _named_users(pwd: str) -> list[User]:
    return [
        User(email="admin@test.com", password_hash=pwd, first_name="Админ", last_name="Системный", role=Role.ADMIN),
        User(email="manager@test.com", password_hash=pwd, first_name="Менеджер", last_name="Учебный", role=Role.MANAGER),
        User(email="user@test.com", password_hash=pwd, first_name="Пользователь", last_name="Обычный", role=Role.USER),
    ]


def _build_exam(course_id: int, exam_spec: dict) -> Exam:
    """Экзамен из спецификации курса: вопросы всех четырёх типов."""
    exam = Exam(course_id=course_id, title=exam_spec["title"],
                duration_minutes=exam_spec["duration"])
    questions = []
    for q_type, text, answers in exam_spec["questions"]:
        question = Question(question=text, type=q_type)
        question.answers = [Answer(answer=a, is_correct=ok) for a, ok in answers]
        questions.append(question)
    exam.questions = questions
    return exam


def _reset_content(db: Session) -> None:
    """Удаляет учебный контент вместе с прогрессом по нему, сохраняя пользователей.

    Порядок важен: сначала зависимые таблицы, потом родительские
    (bulk-delete не задействует ORM-каскады).
    """
    for model in (Notification, ExamAttempt, Enrollment, Answer, Question, Exam, Course):
        db.query(model).delete()
    db.commit()


def seed(db: Session, reset_content: bool = False) -> None:
    if reset_content:
        _reset_content(db)
    elif db.scalar(select(User).limit(1)):
        return  # уже засеяно

    pwd = hash_password(settings.seed_password)

    users = db.scalars(select(User)).all() or []
    if not users:
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

    # 50 учебных курсов из seed_content (описания с примерами кода).
    courses: list[Course] = []
    courses_spec = build_courses()
    for spec in courses_spec:
        courses.append(Course(
            title=spec["title"],
            description=spec["description"],
            price=spec["price"],
            category=spec["category"],
            status=CourseStatus.PUBLISHED,
        ))
    db.add_all(courses)
    db.flush()

    # ~100 экзаменов (по 2 на курс) с 5 вопросами => ~500 вопросов.
    for position, course in enumerate(courses):
        track = courses_spec[position]["track"]
        for exam_spec in build_exams_for(track, position):
            db.add(_build_exam(course.id, exam_spec))

    # уведомления
    user_ids = [u.id for u in users]
    for n in range(1, 121):
        db.add(Notification(
            user_id=random.choice(user_ids),
            message=f"Демонстрационное уведомление №{n}",
        ))

    db.commit()


def run(reset_content: bool = False) -> None:
    init_db()
    with SessionLocal() as db:
        seed(db, reset_content=reset_content)
    print("Seed выполнен." if not reset_content else "Учебный контент пересоздан.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset-content", action="store_true",
                        help="пересоздать курсы/экзамены/вопросы, сохранив пользователей")
    args = parser.parse_args()
    run(reset_content=args.reset_content)
