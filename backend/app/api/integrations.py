"""Реальные Redis/RQ/WireMock-мишени для интеграционных автотестов."""
from __future__ import annotations

import re
import json
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Response
from fastapi.responses import JSONResponse
import httpx
from pydantic import BaseModel, Field
from redis import Redis
from redis.exceptions import RedisError
from rq import Queue
from rq.exceptions import NoSuchJobError
from rq.job import Job

from app.core.config import get_settings

router = APIRouter(prefix="/api/integrations", tags=["integrations"])
settings = get_settings()
_RUN_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,63}$")


class CacheValue(BaseModel):
    value: Any
    ttl_seconds: int = Field(default=60, ge=1, le=3600)


class QueueJobCreate(BaseModel):
    payload: dict[str, Any]
    delay_ms: int = Field(default=0, ge=0, le=5000)
    should_fail: bool = False


def _run_id(x_test_run_id: str | None = Header(default=None)) -> str:
    if not x_test_run_id or not _RUN_ID.fullmatch(x_test_run_id):
        raise HTTPException(status_code=400, detail="Invalid X-Test-Run-Id")
    return x_test_run_id


def _redis() -> Redis:
    # RQ хранит сериализованные bytes, поэтому decode_responses включать нельзя.
    return Redis.from_url(settings.redis_url)


def _cache_key(run_id: str, key: str) -> str:
    return f"qatp:test:{run_id}:cache:{key}"


@router.put("/cache/{key}")
def put_cache(key: str, payload: CacheValue, run_id: str = Header(alias="X-Test-Run-Id")):
    validated = _run_id(run_id)
    try:
        _redis().setex(
            _cache_key(validated, key),
            payload.ttl_seconds,
            json.dumps(payload.value, ensure_ascii=False),
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    return {"key": key, "stored": True, "ttl_seconds": payload.ttl_seconds}


@router.get("/cache/{key}")
def get_cache(key: str, run_id: str = Header(alias="X-Test-Run-Id")):
    validated = _run_id(run_id)
    try:
        value = _redis().get(_cache_key(validated, key))
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    if value is None:
        raise HTTPException(status_code=404, detail="Cache key not found")
    return {"key": key, "value": json.loads(value)}


@router.delete("/cache/{key}", status_code=204)
def delete_cache(key: str, run_id: str = Header(alias="X-Test-Run-Id")):
    validated = _run_id(run_id)
    try:
        _redis().delete(_cache_key(validated, key))
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    return Response(status_code=204)


@router.post("/jobs", status_code=202)
def create_queue_job(
    payload: QueueJobCreate,
    response: Response,
    run_id: str = Header(alias="X-Test-Run-Id"),
):
    validated = _run_id(run_id)
    try:
        queue = Queue("qa-training", connection=_redis())
        job = queue.enqueue(
            "app.integrations.tasks.process_payload",
            payload.payload,
            payload.delay_ms,
            payload.should_fail,
            job_timeout=15,
            result_ttl=300,
            failure_ttl=300,
            meta={"run_id": validated},
        )
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Queue unavailable") from exc
    location = f"/api/integrations/jobs/{job.id}"
    response.headers["Location"] = location
    return {"id": job.id, "status": "QUEUED", "location": location}


@router.get("/jobs/{job_id}")
def get_queue_job(job_id: str, run_id: str = Header(alias="X-Test-Run-Id")):
    validated = _run_id(run_id)
    try:
        job = Job.fetch(job_id, connection=_redis())
        if job.meta.get("run_id") != validated:
            raise HTTPException(status_code=404, detail="Job not found")
        raw_status = job.get_status(refresh=True)
        status = getattr(raw_status, "value", str(raw_status)).upper()
    except NoSuchJobError as exc:
        raise HTTPException(status_code=404, detail="Job not found") from exc
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Queue unavailable") from exc
    body: dict[str, Any] = {"id": job.id, "status": status}
    if job.is_finished:
        body["result"] = job.result
    elif job.is_failed:
        body["error"] = {"type": "ControlledJobFailure", "message": "Queue job failed"}
    return body


@router.delete("/state", status_code=204)
def clear_integration_state(run_id: str = Header(alias="X-Test-Run-Id")):
    validated = _run_id(run_id)
    try:
        redis = _redis()
        keys = list(redis.scan_iter(match=f"qatp:test:{validated}:*", count=100))
        if keys:
            redis.delete(*keys)
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Redis unavailable") from exc
    return Response(status_code=204)


@router.get("/external/profiles/{profile_id}")
def external_profile(
    profile_id: str,
    timeout_ms: int = Query(default=1000, ge=50, le=5000),
):
    try:
        upstream = httpx.get(
            f"{settings.external_service_url}/profiles/{profile_id}",
            timeout=timeout_ms / 1000,
        )
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="External service timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="External service unavailable") from exc
    if upstream.status_code == 404:
        raise HTTPException(status_code=404, detail="External profile not found")
    if upstream.status_code >= 500:
        return JSONResponse(status_code=502, content={"detail": "External service failure"})
    try:
        body = upstream.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="External service returned invalid JSON") from exc
    return {"source": "wiremock", "profile": body}
