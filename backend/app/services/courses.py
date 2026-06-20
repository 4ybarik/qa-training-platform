"""Бизнес-логика курсов и записи на курс."""
from sqlalchemy.orm import Session

from app.domain.errors import ConflictError, NotFoundError
from app.domain.models import AuditLog, Course, Enrollment, Notification
from app.domain.schemas import CourseCreate, CourseUpdate
from app.repositories.courses import CourseRepository, EnrollmentRepository


class CourseService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.courses = CourseRepository(db)
        self.enrollments = EnrollmentRepository(db)

    def search(self, **kwargs) -> tuple[list[Course], int]:
        return self.courses.search(**kwargs)

    def categories(self) -> list[str]:
        return self.courses.categories()

    def get(self, course_id: int) -> Course:
        course = self.courses.get(course_id)
        if not course:
            raise NotFoundError("Курс не найден")
        return course

    def create(self, actor_id: int, data: CourseCreate) -> Course:
        course = Course(
            title=data.title, description=data.description, price=data.price,
            category=data.category, status=data.status,
        )
        self.courses.add(course)
        self.db.add(AuditLog(user_id=actor_id, action="course_created", payload=course.title))
        self.db.commit()
        self.db.refresh(course)
        return course

    def update(self, actor_id: int, course_id: int, data: CourseUpdate) -> Course:
        course = self.get(course_id)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(course, field, value)
        self.db.add(AuditLog(user_id=actor_id, action="course_updated", payload=f"{course_id}:{list(updates)}"))
        self.db.commit()
        self.db.refresh(course)
        return course

    def delete(self, actor_id: int, course_id: int) -> None:
        course = self.get(course_id)
        self.db.add(AuditLog(user_id=actor_id, action="course_deleted", payload=f"{course_id}:{course.title}"))
        self.courses.delete(course)
        self.db.commit()

    def enroll(self, user_id: int, course_id: int) -> Enrollment:
        course = self.get(course_id)
        if self.enrollments.get(user_id, course_id):
            raise ConflictError("Вы уже записаны на этот курс")
        enrollment = Enrollment(user_id=user_id, course_id=course_id)
        self.enrollments.add(enrollment)
        self.db.add(Notification(user_id=user_id, message=f"Вы записаны на курс «{course.title}»"))
        self.db.add(AuditLog(user_id=user_id, action="course_enrolled", payload=str(course_id)))
        self.db.commit()
        self.db.refresh(enrollment)
        return enrollment

    def list_enrollments(self, user_id: int) -> list[Enrollment]:
        return self.enrollments.list_for_user(user_id)
