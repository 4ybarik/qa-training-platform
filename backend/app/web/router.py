"""Серверный веб-интерфейс (Jinja).

Страницы намеренно server-rendered: стабильный DOM с атрибутами data-testid —
идеальная мишень для UI-автотестов (Playwright/Selenium). Аутентификация
веб-интерфейса — через httpOnly cookie с access-токеном.
"""
from datetime import date
from pathlib import Path
import secrets
from urllib.parse import urlsplit

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.api.deps import get_optional_user
from app.core.config import get_settings
from app.core.database import get_db
from app.domain.enums import Role
from app.domain.errors import AuthError, ConflictError, DomainError, NotFoundError, RateLimitError
from app.domain.models import User
from app.practice.catalog import CHALLENGES_BY_SLUG, serialize_catalog, serialize_challenge
from app.practice.mutations import is_active
from app.services.admin import AdminService, NotificationService, ProfileService
from app.services.auth import AuthService
from app.services.courses import CourseService
from app.services.exams import ExamService
from app.services.quality import quality_history
from app.web.i18n import (
    LANGUAGE_COOKIE,
    LANGUAGE_OPTIONS,
    get_request_language,
    javascript_messages,
    localize_error,
    normalize_language,
    translator,
)
from app.domain.schemas import (
    AnswerCreate, CourseCreate, CourseUpdate, ExamCreate, ExamSubmission,
    ProfileUpdate, QuestionCreate, SubmittedAnswer,
)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
AVATAR_DIR = TEMPLATES_DIR.parent / "static" / "uploads" / "avatars"
MAX_AVATAR_BYTES = 2 * 1024 * 1024
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
        return templates.TemplateResponse(request, "forbidden.html", _ctx(request, user), status_code=403)
    return None


def _ctx(request: Request, user: User | None, **extra) -> dict:
    language = get_request_language(request)
    for error_key in ("error", "notif_error", "profile_error"):
        if extra.get(error_key):
            extra[error_key] = localize_error(language, extra[error_key])
    return {
        "request": request, "user": user,
        "app_version": get_settings().app_version,
        "lang": language,
        "language_options": LANGUAGE_OPTIONS,
        "t": translator(language),
        "js_messages": javascript_messages(language),
        # Встроенная IDE доступна только в учебных окружениях.
        "ide_enabled": get_settings().environment in {"development", "test"},
        **extra,
    }


def _safe_redirect_target(value: str) -> str:
    """Разрешает возврат только на локальный абсолютный путь приложения."""
    parts = urlsplit(value)
    if (
        parts.scheme
        or parts.netloc
        or not value.startswith("/")
        or value.startswith("//")
        or "\\" in value
        or any(ord(char) < 32 for char in value)
    ):
        return "/"
    return value


def _avatar_extension(content_type: str | None, content: bytes) -> str | None:
    """Проверяет MIME type и сигнатуру, SVG намеренно не принимается из-за XSS."""
    if content_type == "image/png" and content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content_type == "image/jpeg" and content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if (
        content_type == "image/webp"
        and content.startswith(b"RIFF")
        and len(content) >= 12
        and content[8:12] == b"WEBP"
    ):
        return ".webp"
    return None


# ---------- Аутентификация ----------
@router.get("/", response_class=HTMLResponse)
def root(user: User | None = Depends(get_optional_user)):
    return RedirectResponse("/dashboard" if user else "/login", status_code=303)


@router.post("/web/language")
def set_language(request: Request, language: str = Form(...), next_url: str = Form("/")):
    """Сохраняет язык UI и возвращает пользователя на текущую страницу."""
    response = RedirectResponse(_safe_redirect_target(next_url), status_code=303)
    if not is_active(request, "language-noop"):
        response.set_cookie(
            LANGUAGE_COOKIE,
            normalize_language(language),
            max_age=365 * 24 * 60 * 60,
            httponly=True,
            samesite="lax",
            secure=request.url.scheme == "https",
        )
    return response


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        _ctx(
            request,
            None,
            error=None,
            password_reset=request.query_params.get("reset") == "success",
        ),
    )


@router.post("/web/login", response_class=HTMLResponse)
def login_submit(request: Request, email: str = Form(...), password: str = Form(...),
                 db: Session = Depends(get_db)):
    try:
        client_key = request.client.host if request.client else "global"
        access, _, _ = AuthService(db).authenticate(email, password, client_key=client_key)
    except (AuthError, RateLimitError) as exc:
        return templates.TemplateResponse(
            request,
            "login.html",
            _ctx(request, None, error=str(exc), password_reset=False),
            status_code=401,
        )
    target = "/courses" if is_active(request, "login-redirect") else "/dashboard"
    resp = RedirectResponse(target, status_code=303)
    resp.set_cookie("access_token", access, httponly=True, samesite="lax")
    return resp


def _require_direct_password_reset() -> None:
    """Не допускает небезопасный прямой reset за пределами dev-стенда."""
    if get_settings().environment != "development":
        raise NotFoundError("Прямой сброс пароля доступен только в учебном окружении")


@router.get("/forgot-password", response_class=HTMLResponse)
def forgot_password_page(request: Request, user: User | None = Depends(get_optional_user)):
    if user:
        return RedirectResponse("/dashboard", status_code=303)
    _require_direct_password_reset()
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        _ctx(request, None, error=None),
    )


@router.post("/web/forgot-password", response_class=HTMLResponse)
def forgot_password_submit(
    request: Request,
    email: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db),
):
    _require_direct_password_reset()
    if new_password != confirm_password:
        return templates.TemplateResponse(
            request,
            "forgot_password.html",
            _ctx(request, None, error="Пароли не совпадают"),
            status_code=400,
        )
    if not 8 <= len(new_password) <= 128:
        return templates.TemplateResponse(
            request,
            "forgot_password.html",
            _ctx(request, None, error="Пароль должен содержать от 8 до 128 символов"),
            status_code=400,
        )
    try:
        client_key = request.client.host if request.client else "global"
        AuthService(db).reset_password(email, new_password, client_key=client_key)
    except (AuthError, RateLimitError) as exc:
        status_code = 429 if isinstance(exc, RateLimitError) else 404
        return templates.TemplateResponse(
            request,
            "forgot_password.html",
            _ctx(request, None, error=str(exc)),
            status_code=status_code,
        )
    response = RedirectResponse("/login?reset=success", status_code=303)
    response.delete_cookie("access_token")
    return response


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", _ctx(request, None, error=None))


@router.post("/web/register", response_class=HTMLResponse)
def register_submit(request: Request, email: str = Form(...), password: str = Form(...),
                    confirm: str = Form(...), first_name: str = Form(""),
                    last_name: str = Form(""), birthday: str = Form(""),
                    track: str = Form("ui"), experience: str = Form(""),
                    agree: str | None = Form(None), db: Session = Depends(get_db)):
    if password != confirm:
        return templates.TemplateResponse(
            request, "register.html", _ctx(request, None, error="Пароли не совпадают"), status_code=400
        )
    if agree is None:
        return templates.TemplateResponse(
            request, "register.html", _ctx(request, None, error="Необходимо принять условия"), status_code=400
        )
    if track not in {"ui", "api", "perf"} or experience not in {"", "junior", "middle", "senior"}:
        return templates.TemplateResponse(
            request, "register.html", _ctx(request, None, error="Некорректные параметры профиля"), status_code=400
        )
    try:
        birthday_value = date.fromisoformat(birthday) if birthday else None
    except ValueError:
        return templates.TemplateResponse(
            request, "register.html", _ctx(request, None, error="Некорректная дата рождения"), status_code=400
        )
    try:
        registered = AuthService(db).register(email, password, first_name, last_name)
        skills = [f"Track:{track}"]
        if experience:
            skills.append(f"Experience:{experience}")
        ProfileService(db).update(
            registered.id, ProfileUpdate(birthday=birthday_value, skills=skills)
        )
    except ConflictError as exc:
        return templates.TemplateResponse(
            request, "register.html", _ctx(request, None, error=str(exc)), status_code=409
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
        request, "dashboard.html", _ctx(request, user, stats=stats, notifications=notif)
    )


# ---------- Курсы ----------
@router.get("/courses/new", response_class=HTMLResponse)
def course_new_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_admin(request, user)):
        return r
    return templates.TemplateResponse(request, "course_form.html", _ctx(
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
        return templates.TemplateResponse(request, "course_form.html", _ctx(
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
    return templates.TemplateResponse(request, "courses.html", _ctx(
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
    enrollment = svc.enrollments.get(user.id, course_id)
    enrolled = enrollment is not None
    exams = ExamService(db).list_for_course(course_id)
    return templates.TemplateResponse(request, "course_detail.html", _ctx(
        request, user, course=course, enrolled=enrolled,
        enrollment_progress=enrollment.progress if enrollment else 0, exams=exams
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
    return templates.TemplateResponse(request, "course_form.html", _ctx(
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
        return templates.TemplateResponse(request, "course_form.html", _ctx(
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
    return templates.TemplateResponse(request, "exam_form.html", _ctx(
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
        svc.create(user.id, course_id, ExamCreate(
            title=title, duration_minutes=duration, questions=questions
        ))
    except Exception as exc:
        course = CourseService(db).get(course_id)
        return templates.TemplateResponse(request, "exam_form.html", _ctx(
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
    return templates.TemplateResponse(request, "exam.html", _ctx(request, user, exam=exam, result=None))


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
    return templates.TemplateResponse(request, "exam.html", _ctx(request, user, exam=exam, result=result))


@router.get("/certificates/exams/{exam_id}", response_class=HTMLResponse)
def exam_certificate(
    exam_id: int,
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    if (r := _require_web_user(user)):
        return r
    service = ExamService(db)
    exam = service.get(exam_id)
    attempt = service.latest_passed_attempt(user.id, exam_id)
    return templates.TemplateResponse(
        request, "certificate.html", _ctx(request, user, exam=exam, attempt=attempt)
    )


# ---------- Профиль ----------
@router.get("/profile", response_class=HTMLResponse)
def profile_page(request: Request, user: User | None = Depends(get_optional_user),
                 db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    svc = ProfileService(db)
    p = svc.get(user.id)
    return templates.TemplateResponse(request, "profile.html", _ctx(
        request, user, profile=p, skills=svc.skills_list(p), saved=False, profile_error=None
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
    p = svc.get(user.id)
    avatar = form.get("avatar")
    avatar_content: bytes | None = None
    avatar_extension: str | None = None
    if avatar is not None and getattr(avatar, "filename", ""):
        avatar_content = await avatar.read(MAX_AVATAR_BYTES + 1)
        if len(avatar_content) > MAX_AVATAR_BYTES:
            return templates.TemplateResponse(request, "profile.html", _ctx(
                request, user, profile=p, skills=svc.skills_list(p), saved=False,
                profile_error="Файл аватара больше 2 МБ",
            ), status_code=400)
        avatar_extension = _avatar_extension(
            getattr(avatar, "content_type", None), avatar_content
        )
        if avatar_extension is None:
            return templates.TemplateResponse(request, "profile.html", _ctx(
                request, user, profile=p, skills=svc.skills_list(p), saved=False,
                profile_error="Допустимы только PNG, JPEG и WebP",
            ), status_code=400)
    p = svc.update(user.id, ProfileUpdate(phone=phone, address=address, skills=list(skills)))
    if avatar_content is not None and avatar_extension is not None:
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        filename = f"user-{user.id}-{secrets.token_hex(8)}{avatar_extension}"
        (AVATAR_DIR / filename).write_bytes(avatar_content)
        old_url = p.avatar_url
        p = svc.set_avatar_url(user.id, f"/static/uploads/avatars/{filename}")
        if old_url and old_url.startswith("/static/uploads/avatars/"):
            old_name = Path(old_url).name
            if old_name == old_url.rsplit("/", 1)[-1]:
                (AVATAR_DIR / old_name).unlink(missing_ok=True)
    return templates.TemplateResponse(request, "profile.html", _ctx(
        request, user, profile=p, skills=svc.skills_list(p), saved=True, profile_error=None
    ))


# ---------- Уведомления ----------
@router.get("/notifications", response_class=HTMLResponse)
def notifications_page(request: Request, user: User | None = Depends(get_optional_user),
                       db: Session = Depends(get_db)):
    if (r := _require_web_user(user)):
        return r
    page = NotificationService(db).list_for_user(user.id, None, 0, 21)
    items = page[:20]
    return templates.TemplateResponse(request, "notifications.html", _ctx(
        request, user, notifications=items, notification_offset=len(items),
        notifications_has_more=len(page) > 20,
    ))


# ---------- Админ-панель ----------
@router.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, user: User | None = Depends(get_optional_user),
               db: Session = Depends(get_db)):
    if (r := _require_admin(request, user)):
        return r
    svc = AdminService(db)
    return templates.TemplateResponse(request, "admin.html", _ctx(
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
    return templates.TemplateResponse(request, "admin.html", _ctx(
        request, user, users=svc.list_users(), audit=svc.audit_logs(20), roles=list(Role),
        notif_sent=error is None, notif_error=error,
    ))


# ---------- Каталог практических проверок ----------
@router.get("/learning", include_in_schema=False)
def legacy_learning_redirect():
    """Старые закладки не ломаются, но учебного маршрута больше нет."""
    return RedirectResponse("/practice", status_code=308)


@router.get("/quality", response_class=HTMLResponse)
def quality_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_web_user(user)):
        return r
    return templates.TemplateResponse(
        request,
        "quality.html",
        _ctx(request, user, quality_runs=quality_history(100)),
    )


@router.get("/practice", response_class=HTMLResponse)
def practice_page(
    request: Request,
    track: str | None = Query(default=None),
    difficulty: str | None = Query(default=None),
    user: User | None = Depends(get_optional_user),
):
    if (r := _require_web_user(user)):
        return r
    catalog = serialize_catalog(get_request_language(request))
    visible_tracks = []
    for item in catalog:
        challenges = [
            challenge for challenge in item["challenges"]
            if (not difficulty or challenge["difficulty"] == difficulty)
        ]
        if (not track or item["slug"] == track) and challenges:
            visible_tracks.append({**item, "challenges": challenges})
    return templates.TemplateResponse(
        request,
        "practice.html",
        _ctx(
            request,
            user,
            tracks=visible_tracks,
            all_tracks=catalog,
            selected_track=track or "",
            selected_difficulty=difficulty or "",
            total=sum(len(item["challenges"]) for item in visible_tracks),
        ),
    )


@router.get("/practice/challenges/{slug}", response_class=HTMLResponse)
def practice_challenge_page(
    slug: str,
    request: Request,
    user: User | None = Depends(get_optional_user),
):
    if (r := _require_web_user(user)):
        return r
    challenge = CHALLENGES_BY_SLUG.get(slug)
    if challenge is None:
        raise NotFoundError("Практическая задача не найдена")
    return templates.TemplateResponse(
        request,
        "practice_challenge.html",
        _ctx(request, user, challenge=serialize_challenge(challenge, get_request_language(request))),
    )


@router.get("/practice/components", response_class=HTMLResponse)
def practice_components_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_web_user(user)):
        return r
    return templates.TemplateResponse(request, "practice_components.html", _ctx(request, user))


@router.get("/practice/iframe-content", response_class=HTMLResponse)
def practice_iframe_content():
    return HTMLResponse("""<!doctype html><html><body>
      <h2 data-testid=\"iframe-title\">Isolated iframe</h2>
      <label>Frame value <input aria-label=\"Frame value\" data-testid=\"iframe-input\"></label>
      <button data-testid=\"iframe-button\" onclick=\"this.textContent='Frame saved'\">Save frame</button>
    </body></html>""")


@router.get("/practice/new-tab", response_class=HTMLResponse)
def practice_new_tab():
    return HTMLResponse("""<!doctype html><html><body>
      <h1 data-testid=\"new-tab-title\">New tab target</h1>
      <p data-testid=\"new-tab-status\">ready</p>
    </body></html>""")


# ---------- Playground ----------
@router.get("/playground", response_class=HTMLResponse)
def playground_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_web_user(user)):
        return r
    return templates.TemplateResponse(request, "playground.html", _ctx(request, user))


# ---------- Встроенная IDE (development/test) ----------
@router.get("/ide", response_class=HTMLResponse)
def ide_page(request: Request, user: User | None = Depends(get_optional_user)):
    if (r := _require_web_user(user)):
        return r
    # Инструмент пишет файлы и исполняет pytest — только для учебных контуров.
    if get_settings().environment not in {"development", "test"}:
        return templates.TemplateResponse(
            request, "forbidden.html", _ctx(request, user), status_code=403,
        )
    # Версия статики по mtime: браузер не держит устаревший ide.js/css в кэше.
    static_dir = TEMPLATES_DIR.parent / "static"
    version = int(max(
        (static_dir / "js" / "ide.js").stat().st_mtime,
        (static_dir / "css" / "ide.css").stat().st_mtime,
    ))
    return templates.TemplateResponse(
        request, "ide.html", _ctx(request, user, ide_static_version=version),
    )
