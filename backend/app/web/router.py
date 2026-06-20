"""Серверный веб-интерфейс (Jinja).

Страницы намеренно server-rendered: стабильный DOM с атрибутами data-testid —
идеальная мишень для UI-автотестов (Playwright/Selenium). Аутентификация
веб-интерфейса — через httpOnly cookie с access-токеном.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.config import get_settings
from app.core.database import get_db
from app.domain.enums import Role
from app.domain.errors import AuthError, ConflictError, DomainError, RateLimitError
from app.domain.models import User
from app.services.admin import AdminService, NotificationService, ProfileService
from app.services.auth import AuthService
from app.services.courses import CourseService
from app.services.exams import ExamService
from app.domain.schemas import (
    AnswerCreate, CourseCreate, CourseUpdate, ExamCreate, ExamSubmission,
    ProfileUpdate, QuestionCreate, SubmittedAnswer,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

router = APIRouter(tags=["web"], include_in_schema=False)


def _require_web_user(user: User | None) -> RedirectResponse | None:
    if user is None:
        return RedirectResponse("/login", status_code=303)
    return None


def _require_admin(request: Request, user: User | None):
    """Возвращает редирект/403, если доступ запрещён, иначе None."""
    denied = _require_web_user(user)
    if denied:
        return denied
    if user.role != Role.ADMIN:
        return templates.TemplateResponse("forbidden.html", _ctx(request, user), status_code=403)
    return None


def _ctx(request: Request, user: User | None, **extra) -> dict:
    return {
        "request": request, "user": user,
        "app_version": get_settings().app_version,
        **extra,
    }


# ---------- Аутентификация ----------
@router.get("/", response_class=HTMLResponse)
def root(user: User | None = Depends(get_optional_user)):
    return RedirectResponse("/dashboard" if user else "/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", _ctx(request, None, error=None))


@router.post("/web/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                 db: Session = Depends(get_db)):
    try:
        client_key = request.client.host if request.client else "global"
        access, _, _ = AuthService(db).authenticate(email, password, client_key=client_key)
    except (AuthError, RateLimitError) as exc:
        return templates.TemplateResponse(
            "login.html", _ctx(request, None, error=str(exc)), status_code=401
        )
    resp = RedirectResponse("/dashboard", status_code=303)
    resp.set_cookie("access_token", access, httponly=True, samesite="lax")
    return resp


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", _ctx(request, None, error=None))


@router.post("/web/register", response_class=HTMLResponse)
def register_submit(request: Request, email: str = Form(...), password: str = Form(...),
                    confirm: str = Form(...), first_name: str = Form(""),
                    last_name: str = Form(""), db: Session = Depends(get_db)):
    if password != confirm:
        return templates.TemplateResponse(
            "register.html", _ctx(request, None, error="Пароли не совпадают"), status_code=400
        )
    try:
        AuthService(db).register(email, password, first_name, last_name)
    except ConflictError as exc:
        return templates.TemplateResponse(
            "register.html", _ctx(request, None, error=str(exc)), status_code=409
        )
    return RedirectResponse("/login", status_code=303)


@router.post("/web/logout")
def logout_submit():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("access_token")
    return resp


# ---------- Dashboard ----------
@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, user: User | None = Depends(get_optional_user),
              db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    course_svc = CourseService(db)
    enrollments = course_svc.list_enrollments(user.id)
    notif = NotificationService(db).list_for_user(user.id, None, 0, 5)
    _, total_courses = course_svc.search(size=1)
    stats = {
        "courses": total_courses,
        "enrollments": len(enrollments),
        "notifications": len(notif),
    }
    return templates.TemplateResponse(
        "dashboard.html", _ctx(request, user, stats=stats, notifications=notif)
    )


# ---------- Курсы ----------
@router.get("/courses/new", response_class=HTMLResponse)
def course_new_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_admin(request, user)):
        return r
    return templates.TemplateResponse("course_form.html", _ctx(
        request, user, course=None, error=None, mode="create"
    ))


@router.post("/web/courses/new", response_class=HTMLResponse)
def course_new_submit(request: Request, title: str = Form(...), description: str = Form(""),
                      price: float = Form(0.0), category: str = Form("general"),
                      status: str = Form("PUBLISHED"),
                      user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    svc = CourseService(db)
    try:
        course = svc.create(user.id, CourseCreate(
            title=title, description=description, price=price, category=category, status=status
        ))
    except Exception as exc:  # валидация Pydantic/доменные ошибки -> показываем форму с ошибкой
        return templates.TemplateResponse("course_form.html", _ctx(
            request, user, course=None, error=str(exc), mode="create"
        ), status_code=400)
    return RedirectResponse(f"/courses/{course.id}", status_code=303)


@router.get("/courses", response_class=HTMLResponse)
def courses_page(request: Request, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db),
                 q: str | None = Query(default=None), category: str | None = Query(default=None),
                 sort: str = Query(default="id"), order: str = Query(default="asc"),
                 page: int = Query(default=1, ge=1)):
    if (r := _require_web_user(user)):
        return r
    svc = CourseService(db)
    items, total = svc.search(q=q, category=category, sort=sort, order=order, page=page, size=9)
    pages = max((total + 8) // 9, 1)
    return templates.TemplateResponse("courses.html", _ctx(
        request, user, courses=items, total=total, page=page, pages=pages,
        q=q or "", category=category or "", sort=sort, order=order,
        categories=svc.categories(),
    ))


@router.get("/courses/{course_id}", response_class=HTMLResponse)
def course_detail(course_id: int, request: Request,
                  user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    svc = CourseService(db)
    course = svc.get(course_id)
    enrolled = svc.enrollments.get(user.id, course_id) is not None
    exams = ExamService(db).list_for_course(course_id)
    return templates.TemplateResponse("course_detail.html", _ctx(
        request, user, course=course, enrolled=enrolled, exams=exams
    ))


@router.post("/web/courses/{course_id}/enroll")
def course_enroll(course_id: int, user: User | None = Depends(get_optional_user),
                  db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    try:
        CourseService(db).enroll(user.id, course_id)
    except DomainError:
        pass
    return RedirectResponse(f"/courses/{course_id}", status_code=303)


@router.get("/courses/{course_id}/edit", response_class=HTMLResponse)
def course_edit_page(course_id: int, request: Request,
                     user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    course = CourseService(db).get(course_id)
    return templates.TemplateResponse("course_form.html", _ctx(
        request, user, course=course, error=None, mode="edit"
    ))


@router.post("/web/courses/{course_id}/edit", response_class=HTMLResponse)
def course_edit_submit(course_id: int, request: Request, title: str = Form(...),
                       description: str = Form(""), price: float = Form(0.0),
                       category: str = Form("general"), status: str = Form("PUBLISHED"),
                       user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    svc = CourseService(db)
    try:
        svc.update(user.id, course_id, CourseUpdate(
            title=title, description=description, price=price, category=category, status=status
        ))
    except Exception as exc:
        course = svc.get(course_id)
        return templates.TemplateResponse("course_form.html", _ctx(
            request, user, course=course, error=str(exc), mode="edit"
        ), status_code=400)
    return RedirectResponse(f"/courses/{course_id}", status_code=303)


@router.post("/web/courses/{course_id}/delete")
def course_delete_submit(course_id: int, user: User | None = Depends(get_optional_user),
                         db: Session = Depends(get_db)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role != Role.ADMIN:
        return RedirectResponse("/courses", status_code=303)
    CourseService(db).delete(user.id, course_id)
    return RedirectResponse("/courses", status_code=303)


# ---------- Экзамены ----------
@router.get("/courses/{course_id}/exams/new", response_class=HTMLResponse)
def exam_new_page(course_id: int, request: Request,
                  user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    course = CourseService(db).get(course_id)
    return templates.TemplateResponse("exam_form.html", _ctx(
        request, user, course=course, error=None,
        question_types=["SINGLE", "MULTI", "TEXT", "DND"],
    ))


@router.post("/web/courses/{course_id}/exams/new", response_class=HTMLResponse)
async def exam_new_submit(course_id: int, request: Request,
                          user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    form = await request.form()
    title = str(form.get("title", "")).strip()
    try:
        duration = int(form.get("duration_minutes", 15))
    except (TypeError, ValueError):
        duration = 15

    # Вопросы передаются с индексированными именами полей: question_<i>, qtype_<i>,
    # answer_<i>_<j>, correct_<i>_<j> (чекбокс "правильный ответ").
    questions: list[QuestionCreate] = []
    i = 1
    while form.get(f"question_{i}") is not None:
        q_text = str(form.get(f"question_{i}", "")).strip()
        q_type = str(form.get(f"qtype_{i}", "SINGLE"))
        if q_text:
            answers: list[AnswerCreate] = []
            j = 1
            while form.get(f"answer_{i}_{j}") is not None:
                a_text = str(form.get(f"answer_{i}_{j}", "")).strip()
                if a_text:
                    is_correct = form.get(f"correct_{i}_{j}") is not None
                    answers.append(AnswerCreate(answer=a_text, is_correct=is_correct))
                j += 1
            if answers:
                questions.append(QuestionCreate(question=q_text, type=q_type, answers=answers))
        i += 1

    svc = ExamService(db)
    try:
        exam = svc.create(user.id, course_id, ExamCreate(
            title=title, duration_minutes=duration, questions=questions
        ))
    except Exception as exc:
        course = CourseService(db).get(course_id)
        return templates.TemplateResponse("exam_form.html", _ctx(
            request, user, course=course, error=str(exc),
            question_types=["SINGLE", "MULTI", "TEXT", "DND"],
        ), status_code=400)
    return RedirectResponse(f"/courses/{course_id}", status_code=303)


@router.post("/web/exams/{exam_id}/delete")
def exam_delete_submit(exam_id: int, request: Request,
                       user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    svc = ExamService(db)
    exam = svc.get(exam_id)  # 404, если экзамен не существует
    course_id = exam.course_id
    if user.role != Role.ADMIN:
        return RedirectResponse(f"/courses/{course_id}", status_code=303)
    svc.delete(user.id, exam_id)
    return RedirectResponse(f"/courses/{course_id}", status_code=303)


@router.get("/exams/{exam_id}", response_class=HTMLResponse)
def exam_page(exam_id: int, request: Request,
              user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    exam = ExamService(db).get(exam_id)
    return templates.TemplateResponse("exam.html", _ctx(request, user, exam=exam, result=None))


@router.post("/web/exams/{exam_id}/submit", response_class=HTMLResponse)
async def exam_submit(exam_id: int, request: Request,
                      user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    form = await request.form()
    svc = ExamService(db)
    exam = svc.get(exam_id)
    answers: list[SubmittedAnswer] = []
    for question in exam.questions:
        ids = form.getlist(f"q_{question.id}")
        text_val = form.get(f"text_{question.id}")
        answers.append(SubmittedAnswer(
            question_id=question.id,
            answer_ids=[int(i) for i in ids if str(i).isdigit()],
            text=text_val,
        ))
    result = svc.submit(user.id, exam_id, ExamSubmission(answers=answers))
    return templates.TemplateResponse("exam.html", _ctx(request, user, exam=exam, result=result))


# ---------- Профиль ----------
@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    svc = ProfileService(db)
    p = svc.get(user.id)
    return templates.TemplateResponse("profile.html", _ctx(
        request, user, profile=p, skills=svc.skills_list(p), saved=False
    ))


@router.post("/web/profile", response_class=HTMLResponse)
async def profile_update(request: Request,
                         user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    form = await request.form()
    phone = str(form.get("phone", ""))
    address = str(form.get("address", ""))
    skills = form.getlist("skills")
    svc = ProfileService(db)
    p = svc.update(user.id, ProfileUpdate(phone=phone, address=address, skills=list(skills)))
    return templates.TemplateResponse("profile.html", _ctx(
        request, user, profile=p, skills=svc.skills_list(p), saved=True
    ))


# ---------- Уведомления ----------
@router.get("/notifications", response_class=HTMLResponse)
def notifications_page(request: Request, user: User | None = Depends(get_optional_user),
                       db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    items = NotificationService(db).list_for_user(user.id, None, 0, 50)
    return templates.TemplateResponse("notifications.html", _ctx(request, user, notifications=items))


# ---------- Админ-панель ----------
@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, user: User | None = Depends(get_optional_user),
               db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    svc = AdminService(db)
    return templates.TemplateResponse("admin.html", _ctx(
        request, user, users=svc.list_users(), audit=svc.audit_logs(20), roles=list(Role),
        notif_sent=False,
    ))


@router.post("/web/admin/users/{user_id}/active")
def admin_set_active(user_id: int, is_active: str = Form(...),
                     user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if user is None:
        return RedirectResponse("/login", status_code=303)
    if user.role != Role.ADMIN:
        return RedirectResponse("/admin", status_code=303)
    try:
        AdminService(db).set_active(user, user_id, is_active == "true")
    except DomainError:
        pass  # например, попытка деактивировать себя — молча игнорируем на уровне формы
    return RedirectResponse("/admin", status_code=303)


@router.post("/web/admin/notifications", response_class=HTMLResponse)
def admin_send_notification(request: Request, message: str = Form(...),
                            target_user_id: str = Form(""),
                            user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    target = int(target_user_id) if target_user_id.strip().isdigit() else None
    svc = AdminService(db)
    error = None
    try:
        NotificationService(db).create_for_admin(user.id, target, message)
    except DomainError as exc:
        error = str(exc)
    return templates.TemplateResponse("admin.html", _ctx(
        request, user, users=svc.list_users(), audit=svc.audit_logs(20), roles=list(Role),
        notif_sent=error is None, notif_error=error,
    ))


# ---------- Playground ----------
@router.get("/playground", response_class=HTMLResponse)
def playground_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_web_user(user)):
        return r
    return templates.TemplateResponse("playground.html", _ctx(request, user))
