"""Репозиторий курсов и записей на курсы."""
from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.domain.models import Course, Enrollment

_SORTABLE = {"title": Course.title, "price": Course.price, "id": Course.id}


class CourseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, course_id: int) -> Course | None:
        return self.db.get(Course, course_id)

    def search(
        self,
        *,
        q: str | None = None,
        category: str | None = None,
        sort: str = "id",
        order: str = "asc",
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[Course], int]:
        stmt = select(Course)
        count_stmt = select(func.count()).select_from(Course)

        if q:
            like = f"%{q}%"
            stmt = stmt.where(Course.title.ilike(like))
            count_stmt = count_stmt.where(Course.title.ilike(like))
        if category:
            stmt = stmt.where(Course.category == category)
            count_stmt = count_stmt.where(Course.category == category)

        column = _SORTABLE.get(sort, Course.id)
        direction = desc if order == "desc" else asc
        stmt = stmt.order_by(direction(column))

        total = self.db.scalar(count_stmt) or 0
        page = max(page, 1)
        size = min(max(size, 1), 100)
        stmt = stmt.offset((page - 1) * size).limit(size)
        items = list(self.db.scalars(stmt))
        return items, total

    def categories(self) -> list[str]:
        return list(self.db.scalars(select(Course.category).distinct().order_by(Course.category)))

    def add(self, course: Course) -> Course:
        self.db.add(course)
        self.db.flush()
        return course

    def delete(self, course: Course) -> None:
        self.db.delete(course)


class EnrollmentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, user_id: int, course_id: int) -> Enrollment | None:
        return self.db.scalar(
            select(Enrollment).where(
                Enrollment.user_id == user_id, Enrollment.course_id == course_id
            )
        )

    def list_for_user(self, user_id: int) -> list[Enrollment]:
        return list(
            self.db.scalars(select(Enrollment).where(Enrollment.user_id == user_id))
        )

    def add(self, enrollment: Enrollment) -> Enrollment:
        self.db.add(enrollment)
        self.db.flush()
        return enrollment
