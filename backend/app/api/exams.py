"""API экзаменов: список по курсу, получение вопросов, отправка ответов
и администрирование (создание/редактирование/удаление — только ADMIN)."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.domain.enums import Role
from app.domain.models import User
from app.domain.schemas import (
    ErrorResponse, ExamAdminOut, ExamCreate, ExamOut, ExamResult,
    ExamSubmission, ExamUpdate, MessageResponse,
)
from app.services.exams import ExamService

router = APIRouter(prefix="/api", tags=["exams"])


@router.get("/courses/{course_id}/exams", response_model=list[ExamOut])
def list_exams(course_id: int, db: Session = Depends(get_db)):
    return ExamService(db).list_for_course(course_id)


@router.get("/exams/{exam_id}", response_model=ExamOut,
            responses={404: {"model": ErrorResponse}})
def get_exam(exam_id: int, db: Session = Depends(get_db)):
    return ExamService(db).get(exam_id)


@router.get("/exams/{exam_id}/admin", response_model=ExamAdminOut,
            responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def get_exam_admin(exam_id: int,
                   _: User = Depends(require_roles(Role.ADMIN)),
                   db: Session = Depends(get_db)):
    """Та же сущность, но с признаком is_correct у ответов — для редактирования."""
    return ExamService(db).get(exam_id)


@router.post("/courses/{course_id}/exams", response_model=ExamAdminOut, status_code=201,
             responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def create_exam(course_id: int, payload: ExamCreate,
                admin: User = Depends(require_roles(Role.ADMIN)),
                db: Session = Depends(get_db)):
    return ExamService(db).create(admin.id, course_id, payload)


@router.put("/exams/{exam_id}", response_model=ExamAdminOut,
            responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_exam(exam_id: int, payload: ExamUpdate,
                admin: User = Depends(require_roles(Role.ADMIN)),
                db: Session = Depends(get_db)):
    return ExamService(db).update(admin.id, exam_id, payload)


@router.delete("/exams/{exam_id}", response_model=MessageResponse,
               responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def delete_exam(exam_id: int,
                admin: User = Depends(require_roles(Role.ADMIN)),
                db: Session = Depends(get_db)) -> MessageResponse:
    ExamService(db).delete(admin.id, exam_id)
    return MessageResponse(detail="Экзамен удалён")


@router.post("/exams/{exam_id}/submit", response_model=ExamResult,
             responses={404: {"model": ErrorResponse}})
def submit_exam(exam_id: int, submission: ExamSubmission,
                user: User = Depends(get_current_user),
                db: Session = Depends(get_db)) -> ExamResult:
    return ExamService(db).submit(user.id, exam_id, submission)
