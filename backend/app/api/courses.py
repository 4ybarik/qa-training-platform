"""API курсов: каталог с поиском/фильтрами/сортировкой/пагинацией, запись на курс
и администрирование (создание/редактирование/удаление — только ADMIN)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.database import get_db
from app.domain.enums import Role
from app.domain.models import User
from app.domain.schemas import (
    CourseCreate, CourseOut, CoursePage, CourseUpdate, ErrorResponse, MessageResponse,
)
from app.services.courses import CourseService

router = APIRouter(prefix="/api/courses", tags=["courses"])


@router.get("", response_model=CoursePage)
def list_courses(
    db: Session = Depends(get_db),
    q: str | None = Query(default=None, description="Поиск по названию"),
    category: str | None = Query(default=None),
    sort: str = Query(default="id", pattern="^(id|title|price)$"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
) -> CoursePage:
    items, total = CourseService(db).search(
        q=q, category=category, sort=sort, order=order, page=page, size=size
    )
    return CoursePage(items=items, total=total, page=page, size=size)


@router.get("/categories", response_model=list[str])
def categories(db: Session = Depends(get_db)) -> list[str]:
    return CourseService(db).categories()


# ВАЖНО: эндпоинты с литеральным путём (/categories выше) должны быть
# зарегистрированы раньше /{course_id}, иначе FastAPI попытается
# матчить "categories" как course_id и упадёт на валидации типа int.
@router.get("/{course_id}", response_model=CourseOut,
            responses={404: {"model": ErrorResponse}})
def get_course(course_id: int, db: Session = Depends(get_db)):
    return CourseService(db).get(course_id)


@router.post("", response_model=CourseOut, status_code=201)
def create_course(payload: CourseCreate,
                  admin: User = Depends(require_roles(Role.ADMIN)),
                  db: Session = Depends(get_db)):
    return CourseService(db).create(admin.id, payload)


@router.put("/{course_id}", response_model=CourseOut,
            responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def update_course(course_id: int, payload: CourseUpdate,
                  admin: User = Depends(require_roles(Role.ADMIN)),
                  db: Session = Depends(get_db)):
    return CourseService(db).update(admin.id, course_id, payload)


@router.delete("/{course_id}", response_model=MessageResponse,
               responses={403: {"model": ErrorResponse}, 404: {"model": ErrorResponse}})
def delete_course(course_id: int,
                  admin: User = Depends(require_roles(Role.ADMIN)),
                  db: Session = Depends(get_db)) -> MessageResponse:
    CourseService(db).delete(admin.id, course_id)
    return MessageResponse(detail="Курс удалён")


@router.post("/{course_id}/enroll", response_model=MessageResponse,
             responses={404: {"model": ErrorResponse}, 409: {"model": ErrorResponse}})
def enroll(course_id: int, user: User = Depends(get_current_user),
           db: Session = Depends(get_db)) -> MessageResponse:
    CourseService(db).enroll(user.id, course_id)
    return MessageResponse(detail="Запись на курс выполнена")
