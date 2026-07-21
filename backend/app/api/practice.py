"""Детерминированные мишени для пользовательских API- и интеграционных тестов."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from itertools import count
import re
from threading import RLock
from typing import Any, Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, Request, Response, UploadFile
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field

from app.practice.catalog import CHALLENGES_BY_SLUG, serialize_catalog, serialize_challenge
from app.practice.mutations import is_active, serialize_mutations

router = APIRouter(prefix="/api/practice", tags=["practice"])

_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,63}$")
_MAX_FILE_BYTES = 1024 * 1024
_lock = RLock()
_ids = count(1)
_resources: dict[str, dict[int, dict[str, Any]]] = {}
_idempotency: dict[tuple[str, str], tuple[int, str]] = {}
_jobs: dict[str, dict[str, dict[str, Any]]] = {}
_files: dict[str, dict[str, dict[str, Any]]] = {}
_webhooks: dict[str, list[dict[str, Any]]] = {}
_rate_attempts: dict[str, int] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _namespace(x_test_run_id: str | None = Header(default=None)) -> str:
    if not x_test_run_id or not _RUN_ID.fullmatch(x_test_run_id):
        raise HTTPException(
            status_code=400,
            detail="X-Test-Run-Id must be 3-64 safe characters",
        )
    return x_test_run_id


class EchoBody(BaseModel):
    model_config = ConfigDict(extra="allow")
    message: str | None = None


class ResourceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(default=1, ge=0, le=10_000)
    price: float = Field(default=0, ge=0, le=1_000_000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class ResourceUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)
    quantity: int = Field(ge=0, le=10_000)
    price: float = Field(ge=0, le=1_000_000)
    tags: list[str] = Field(default_factory=list, max_length=10)


class JobCreate(BaseModel):
    polls_to_complete: int = Field(default=2, ge=1, le=5)
    outcome: Literal["completed", "failed"] = "completed"


@router.get("/catalog")
def practice_catalog(language: Literal["ru", "en"] = "ru"):
    return {"tracks": serialize_catalog(language), "total": len(CHALLENGES_BY_SLUG)}


@router.get("/catalog/{slug}")
def practice_challenge(slug: str, language: Literal["ru", "en"] = "ru"):
    challenge = CHALLENGES_BY_SLUG.get(slug)
    if challenge is None:
        raise HTTPException(status_code=404, detail="Practice challenge not found")
    return serialize_challenge(challenge, language)


@router.get("/mutations")
def practice_mutations():
    """Возвращает каталог доступных контролируемых дефектов."""
    items = serialize_mutations()
    return {"items": items, "total": len(items)}


@router.get("/echo")
def echo_get(request: Request, x_echo: str | None = Header(default=None)):
    return {
        "method": request.method,
        "query": dict(request.query_params),
        "x_echo": x_echo,
        "content_type": request.headers.get("content-type"),
    }


@router.post("/echo")
def echo_post(request: Request, payload: EchoBody, x_echo: str | None = Header(default=None)):
    return {
        "method": request.method,
        "query": dict(request.query_params),
        "x_echo": x_echo,
        "body": payload.model_dump(),
        "content_type": request.headers.get("content-type"),
    }


@router.get("/status/{code}")
def status_response(code: int):
    allowed = {200, 201, 202, 204, 400, 401, 403, 404, 409, 422, 429, 500, 503}
    if code not in allowed:
        raise HTTPException(status_code=422, detail=f"Supported status codes: {sorted(allowed)}")
    if code == 204:
        return Response(status_code=204)
    return JSONResponse(status_code=code, content={"requested_status": code, "ok": code < 400})


@router.get("/rate-limit")
def rate_limit_target(
    request: Request,
    namespace: str = Depends(_namespace),
    limit: int = Query(default=3, ge=1, le=10),
):
    with _lock:
        attempt = _rate_attempts.get(namespace, 0) + 1
        _rate_attempts[namespace] = attempt
    remaining = max(limit - attempt, 0)
    headers = {
        "RateLimit-Limit": str(limit),
        "RateLimit-Remaining": str(remaining),
    }
    if attempt > limit and not is_active(request, "rate-limit-disabled"):
        return JSONResponse(
            status_code=429,
            content={"detail": "Practice rate limit exceeded", "attempt": attempt},
            headers={**headers, "Retry-After": "1"},
        )
    return JSONResponse(
        status_code=200,
        content={"allowed": True, "attempt": attempt},
        headers=headers,
    )


@router.get("/schema/{variant}")
def schema_variant(
    request: Request,
    variant: Literal["stable", "nullable", "missing", "extra", "wrong-type"],
):
    payload: dict[str, Any] = {
        "id": 101,
        "name": "Contract fixture",
        "active": True,
        "metadata": {"source": "practice", "revision": 1},
    }
    if variant == "stable" and is_active(request, "schema-wrong-type"):
        payload["id"] = "101"
    elif variant == "nullable":
        payload["name"] = None
    elif variant == "missing":
        payload.pop("name")
    elif variant == "extra":
        payload["unexpected"] = "contract drift"
    elif variant == "wrong-type":
        payload["id"] = "101"
    return payload


@router.post("/resources", status_code=201)
def create_resource(
    payload: ResourceCreate,
    response: Response,
    namespace: str = Depends(_namespace),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key is not None and not (3 <= len(idempotency_key) <= 128):
        raise HTTPException(status_code=400, detail="Idempotency-Key must be 3-128 characters")
    fingerprint = payload.model_dump_json()
    with _lock:
        known = _idempotency.get((namespace, idempotency_key)) if idempotency_key else None
        if known is not None:
            known_id, known_fingerprint = known
            if known_fingerprint != fingerprint:
                raise HTTPException(
                    status_code=409,
                    detail="Idempotency-Key was already used with a different payload",
                )
            item = _resources[namespace][known_id]
            response.status_code = 200
            response.headers["Idempotent-Replayed"] = "true"
            response.headers["ETag"] = f'"{item["version"]}"'
            return item
        item_id = next(_ids)
        item = {
            "id": item_id,
            **payload.model_dump(),
            "version": 1,
            "created_at": _now(),
            "updated_at": _now(),
        }
        _resources.setdefault(namespace, {})[item_id] = item
        if idempotency_key:
            _idempotency[(namespace, idempotency_key)] = (item_id, fingerprint)
        response.headers["Location"] = f"/api/practice/resources/{item_id}"
        response.headers["ETag"] = '"1"'
        return item


@router.get("/resources")
def list_resources(
    request: Request,
    namespace: str = Depends(_namespace),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=50),
    search: str | None = Query(default=None, max_length=100),
    sort: Literal["name", "-name", "created_at", "-created_at"] = "created_at",
):
    with _lock:
        items = list(_resources.get(namespace, {}).values())
    if search:
        needle = search.casefold()
        items = [item for item in items if needle in item["name"].casefold()]
    descending = sort.startswith("-")
    field = sort.lstrip("-")
    items.sort(key=lambda item: (item[field].casefold() if field == "name" else item[field], item["id"]), reverse=descending)
    total = len(items)
    if is_active(request, "practice-list-phantom") and not items:
        items = [{
            "id": -1,
            "name": "phantom",
            "quantity": 1,
            "price": 0,
            "tags": [],
            "version": 1,
            "created_at": _now(),
            "updated_at": _now(),
        }]
        total = 1
    start = (page - 1) * size
    page_items = (
        items[start:]
        if is_active(request, "pagination-ignore-size")
        else items[start:start + size]
    )
    return {"items": page_items, "total": total, "page": page, "size": size}


def _get_resource(namespace: str, resource_id: int) -> dict[str, Any]:
    item = _resources.get(namespace, {}).get(resource_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Resource not found")
    return item


@router.get("/resources/{resource_id}")
def get_resource(resource_id: int, response: Response, namespace: str = Depends(_namespace)):
    with _lock:
        item = _get_resource(namespace, resource_id)
        response.headers["ETag"] = f'"{item["version"]}"'
        return item.copy()


@router.put("/resources/{resource_id}")
def update_resource(
    request: Request,
    resource_id: int,
    payload: ResourceUpdate,
    response: Response,
    namespace: str = Depends(_namespace),
    if_match: str | None = Header(default=None, alias="If-Match"),
):
    if if_match is None:
        raise HTTPException(status_code=428, detail="If-Match header is required")
    with _lock:
        item = _get_resource(namespace, resource_id)
        expected = f'"{item["version"]}"'
        if if_match != expected and not is_active(request, "etag-ignore-if-match"):
            raise HTTPException(status_code=412, detail="Resource version is stale")
        item.update(payload.model_dump())
        item["version"] += 1
        item["updated_at"] = _now()
        response.headers["ETag"] = f'"{item["version"]}"'
        return item.copy()


@router.delete("/resources/{resource_id}", status_code=204)
def delete_resource(
    request: Request,
    resource_id: int,
    namespace: str = Depends(_namespace),
):
    with _lock:
        _get_resource(namespace, resource_id)
        if is_active(request, "resource-delete-noop"):
            return Response(status_code=204)
        del _resources[namespace][resource_id]
        for key, (item_id, _) in list(_idempotency.items()):
            if key[0] == namespace and item_id == resource_id:
                del _idempotency[key]
    return Response(status_code=204)


@router.delete("/resources", status_code=204)
def clear_resources(namespace: str = Depends(_namespace)):
    with _lock:
        _resources.pop(namespace, None)
        for key in [key for key in _idempotency if key[0] == namespace]:
            del _idempotency[key]
    return Response(status_code=204)


@router.delete("/state", status_code=204)
def clear_practice_state(namespace: str = Depends(_namespace)):
    """Адресный teardown всех временных данных одного тестового запуска."""
    with _lock:
        _resources.pop(namespace, None)
        _jobs.pop(namespace, None)
        _files.pop(namespace, None)
        _webhooks.pop(namespace, None)
        _rate_attempts.pop(namespace, None)
        for key in [key for key in _idempotency if key[0] == namespace]:
            del _idempotency[key]
    return Response(status_code=204)


@router.post("/jobs", status_code=202)
def create_job(payload: JobCreate, response: Response, namespace: str = Depends(_namespace)):
    with _lock:
        job_id = f"job-{next(_ids)}"
        job = {
            "id": job_id,
            "status": "PENDING",
            "polls": 0,
            "polls_to_complete": payload.polls_to_complete,
            "outcome": payload.outcome,
            "created_at": _now(),
        }
        _jobs.setdefault(namespace, {})[job_id] = job
    response.headers["Location"] = f"/api/practice/jobs/{job_id}"
    return {"id": job_id, "status": "PENDING"}


@router.get("/jobs/{job_id}")
def get_job(request: Request, job_id: str, namespace: str = Depends(_namespace)):
    with _lock:
        job = _jobs.get(namespace, {}).get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        job["polls"] += 1
        if (
            job["polls"] >= job["polls_to_complete"]
            and not is_active(request, "job-never-completes")
        ):
            job["status"] = "COMPLETED" if job["outcome"] == "completed" else "FAILED"
        result = {"id": job["id"], "status": job["status"], "polls": job["polls"]}
        if job["status"] == "COMPLETED":
            result["result"] = {"processed": True}
        elif job["status"] == "FAILED":
            result["error"] = {"code": "PRACTICE_JOB_FAILED", "retryable": False}
        return result


@router.post("/files", status_code=201)
async def upload_file(file: UploadFile = File(...), namespace: str = Depends(_namespace)):
    content = await file.read(_MAX_FILE_BYTES + 1)
    if not content:
        raise HTTPException(status_code=422, detail="File must not be empty")
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 1 MiB")
    raw_name = (file.filename or "upload.bin").replace("\\", "/").split("/")[-1][:200]
    safe_name = re.sub(r'[\x00-\x1f\x7f"]', "_", raw_name) or "upload.bin"
    file_id = f"file-{next(_ids)}"
    item = {
        "id": file_id,
        "filename": safe_name,
        "content_type": file.content_type or "application/octet-stream",
        "size": len(content),
        "sha256": hashlib.sha256(content).hexdigest(),
        "content": content,
    }
    with _lock:
        _files.setdefault(namespace, {})[file_id] = item
    return {key: value for key, value in item.items() if key != "content"}


@router.get("/files/{file_id}")
def download_file(request: Request, file_id: str, namespace: str = Depends(_namespace)):
    with _lock:
        item = _files.get(namespace, {}).get(file_id)
        if item is None:
            raise HTTPException(status_code=404, detail="File not found")
        ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", item["filename"]) or "upload.bin"
        encoded_name = quote(item["filename"], safe="")
        content = item["content"]
        if is_active(request, "file-content-corrupted"):
            content += b"-corrupted"
        return Response(
            content,
            media_type=item["content_type"],
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{encoded_name}'
                )
            },
        )


@router.get("/redirect/{hops}")
def redirect_chain(hops: int):
    if not 0 <= hops <= 5:
        raise HTTPException(status_code=422, detail="hops must be between 0 and 5")
    if hops == 0:
        return {"status": "arrived", "hops_remaining": 0}
    return RedirectResponse(f"/api/practice/redirect/{hops - 1}", status_code=302)


@router.post("/cookies/set")
def set_practice_cookie(response: Response, value: str = Query(min_length=1, max_length=100)):
    response.set_cookie("practice_session", value, httponly=True, samesite="lax")
    return {"set": True}


@router.get("/cookies/read")
def read_practice_cookie(request: Request):
    return {"value": request.cookies.get("practice_session")}


@router.delete("/cookies")
def delete_practice_cookie(response: Response):
    response.delete_cookie("practice_session", httponly=True, samesite="lax")
    return {"deleted": True}


@router.post("/webhooks", status_code=202)
async def record_webhook(request: Request, namespace: str = Depends(_namespace)):
    try:
        body: Any = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Webhook body must be JSON") from exc
    event = {
        "sequence": 0,
        "received_at": _now(),
        "correlation_id": request.headers.get("X-Correlation-Id"),
        "body": body,
    }
    with _lock:
        events = _webhooks.setdefault(namespace, [])
        event["sequence"] = (
            1 if is_active(request, "webhook-sequence-duplicate") else len(events) + 1
        )
        events.append(event)
    return {"accepted": True, "sequence": event["sequence"]}


@router.get("/webhooks")
def list_webhooks(namespace: str = Depends(_namespace)):
    with _lock:
        events = [event.copy() for event in _webhooks.get(namespace, [])]
    return {"items": events, "total": len(events)}


@router.delete("/webhooks", status_code=204)
def clear_webhooks(namespace: str = Depends(_namespace)):
    with _lock:
        _webhooks.pop(namespace, None)
    return Response(status_code=204)
