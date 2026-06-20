"""Бизнес-логика экзаменов: получение, создание/редактирование и проверка ответов."""
from sqlalchemy.orm import Session

from app.domain.enums import QuestionType
from app.domain.errors import NotFoundError
from app.domain.models import Answer, AuditLog, Exam, Notification, Question
from app.domain.schemas import ExamCreate, ExamResult, ExamSubmission, ExamUpdate
from app.repositories.courses import CourseRepository
from app.repositories.exams import ExamRepository

PASS_THRESHOLD = 60  # процент для прохождения


class ExamService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.exams = ExamRepository(db)
        self.courses = CourseRepository(db)

    def list_for_course(self, course_id: int) -> list[Exam]:
        return self.exams.list_for_course(course_id)

    def get(self, exam_id: int) -> Exam:
        exam = self.exams.get_with_questions(exam_id)
        if not exam:
            raise NotFoundError("Экзамен не найден")
        return exam

    def create(self, actor_id: int, course_id: int, data: ExamCreate) -> Exam:
        if not self.courses.get(course_id):
            raise NotFoundError("Курс не найден")
        exam = Exam(course_id=course_id, title=data.title, duration_minutes=data.duration_minutes)
        for q in data.questions:
            question = Question(question=q.question, type=q.type)
            question.answers = [
                Answer(answer=a.answer, is_correct=a.is_correct) for a in q.answers
            ]
            exam.questions.append(question)
        self.exams.add(exam)
        self.db.add(AuditLog(user_id=actor_id, action="exam_created", payload=f"{course_id}:{exam.title}"))
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def update(self, actor_id: int, exam_id: int, data: ExamUpdate) -> Exam:
        exam = self.get(exam_id)
        updates = data.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(exam, field, value)
        self.db.add(AuditLog(user_id=actor_id, action="exam_updated", payload=f"{exam_id}:{list(updates)}"))
        self.db.commit()
        self.db.refresh(exam)
        return exam

    def delete(self, actor_id: int, exam_id: int) -> None:
        exam = self.get(exam_id)
        self.db.add(AuditLog(user_id=actor_id, action="exam_deleted", payload=f"{exam_id}:{exam.title}"))
        self.exams.delete(exam)
        self.db.commit()

    def submit(self, user_id: int, exam_id: int, submission: ExamSubmission) -> ExamResult:
        exam = self.get(exam_id)
        submitted = {a.question_id: a for a in submission.answers}

        total = len(exam.questions)
        correct = 0
        for question in exam.questions:
            ans = submitted.get(question.id)
            if ans is None:
                continue
            if self._is_correct(question, ans):
                correct += 1

        score = round(correct / total * 100) if total else 0
        passed = score >= PASS_THRESHOLD
        certificate_url = f"/certificates/exam-{exam_id}-user-{user_id}.pdf" if passed else None

        msg = (
            f"Экзамен «{exam.title}» сдан, результат {score}%."
            if passed else
            f"Экзамен «{exam.title}» не сдан, результат {score}%."
        )
        self.db.add(Notification(user_id=user_id, message=msg))
        self.db.add(AuditLog(user_id=user_id, action="exam_completed", payload=f"{exam_id}:{score}"))
        self.db.commit()

        return ExamResult(
            exam_id=exam_id, total=total, correct=correct,
            score=score, passed=passed, certificate_url=certificate_url,
        )

    @staticmethod
    def _is_correct(question, ans) -> bool:
        correct_ids = {a.id for a in question.answers if a.is_correct}
        if question.type in (QuestionType.SINGLE, QuestionType.MULTI, QuestionType.DND):
            return set(ans.answer_ids) == correct_ids
        if question.type == QuestionType.TEXT:
            expected = {a.answer.strip().lower() for a in question.answers if a.is_correct}
            return bool(ans.text) and ans.text.strip().lower() in expected
        return False
