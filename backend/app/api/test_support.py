"""Изолированный Test Data API для локальных и CI-автотестов."""
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.domain.enums import CourseStatus, Role
from app.services.test_support import TestSupportService

router = APIRouter(prefix="/api/test-support", tags=["test-support"])
settings = get_settings()
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,63}$")


class TestUserCreate(BaseModel):
    email: EmailStr | None = None
    password: str = Field(default="Password123!", min_length=8, max_length=128)
    role: Role = Role.USER
    first_name: str = Field(default="Auto", max_length=100)
    last_name: str = Field(default="Test", max_length=100)


class TestCourseCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    price: float = Field(default=0, ge=0)
    category: str = Field(default="autotest", max_length=100)
    status: CourseStatus = CourseStatus.PUBLISHED


def _require_test_run(
    request: Request,
    x_test_run_id: str | None = Header(default=None),
    x_test_support_key: str | None = Header(default=None),
) -> str:
    if settings.environment not in {"development", "test"}:
        raise HTTPException(status_code=404, detail="Not found")
    if not x_test_support_key or x_test_support_key != settings.test_support_key:
        raise HTTPException(status_code=403, detail="Invalid test support key")
    if not x_test_run_id or not _RUN_ID.fullmatch(x_test_run_id):
        raise HTTPException(status_code=400, detail="Invalid X-Test-Run-Id")
    return x_test_run_id


@router.post("/users", status_code=201)
def create_test_user(
    payload: TestUserCreate,
    run_id: str = Depends(_require_test_run),
    db: Session = Depends(get_db),
):
    try:
        user = TestSupportService(db).create_user(
            run_id,
            email=str(payload.email) if payload.email else None,
            password=payload.password,
            role=payload.role,
            first_name=payload.first_name,
            last_name=payload.last_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return {
        "id": user.id,
        "email": user.email,
        "password": payload.password,
        "role": user.role.value,
        "run_id": run_id,
    }


@router.post("/courses", status_code=201)
def create_test_course(
    payload: TestCourseCreate,
    run_id: str = Depends(_require_test_run),
    db: Session = Depends(get_db),
):
    course = TestSupportService(db).create_course(
        run_id,
        title=payload.title,
        description=payload.description,
        price=payload.price,
        category=payload.category,
        status=payload.status,
    )
    return {
        "id": course.id,
        "title": course.title,
        "status": course.status.value,
        "run_id": run_id,
    }


@router.delete("/state")
def cleanup_test_state(
    run_id: str = Depends(_require_test_run),
    db: Session = Depends(get_db),
):
    return {"run_id": run_id, "removed": TestSupportService(db).cleanup(run_id)}
