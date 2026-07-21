"""Параллельные v1/v2 контракты для практики совместимости API."""
from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Depends, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.courses import CourseService

router = APIRouter(prefix="/api", tags=["versioned-api"])


class CourseV1(BaseModel):
    id: int
    title: str
    price: float
    status: str


class CoursePageV1(BaseModel):
    version: str = "v1"
    items: list[CourseV1]
    total: int
    page: int
    size: int


class MoneyV2(BaseModel):
    amount: str
    currency: str = "RUB"


class CourseV2(BaseModel):
    id: int
    name: str
    pricing: MoneyV2
    lifecycle: str


class PaginationV2(BaseModel):
    page: int
    page_size: int
    total_items: int


class CoursePageV2(BaseModel):
    api_version: str = "v2"
    data: list[CourseV2]
    pagination: PaginationV2


def _v1_deprecation_headers(response: Response) -> None:
    response.headers["Deprecation"] = "true"
    response.headers["Sunset"] = "Thu, 31 Dec 2026 23:59:59 GMT"
    response.headers["Link"] = '</api/v2/courses>; rel="successor-version"'


@router.get("/v1/courses", response_model=CoursePageV1, deprecated=True)
def list_courses_v1(
    response: Response,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = CourseService(db).search(page=page, size=size)
    _v1_deprecation_headers(response)
    return CoursePageV1(
        items=[
            CourseV1(
                id=item.id,
                title=item.title,
                price=item.price,
                status=item.status.value,
            )
            for item in items
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get("/v2/courses", response_model=CoursePageV2)
def list_courses_v2(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items, total = CourseService(db).search(page=page, size=page_size)
    return CoursePageV2(
        data=[
            CourseV2(
                id=item.id,
                name=item.title,
                pricing=MoneyV2(amount=f"{Decimal(str(item.price)):.2f}"),
                lifecycle=item.status.value.lower(),
            )
            for item in items
        ],
        pagination=PaginationV2(
            page=page,
            page_size=page_size,
            total_items=total,
        ),
    )
