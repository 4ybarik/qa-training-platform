"""Короткий CI-профиль нагрузки с блокирующими p95/failure-rate порогами."""
from __future__ import annotations

import logging
import os

from locust import HttpUser, between, events, task


class PlatformUser(HttpUser):
    wait_time = between(0.05, 0.2)

    @task(4)
    def health(self):
        self.client.get("/health", name="GET /health")

    @task(3)
    def courses(self):
        self.client.get("/api/courses?page=1&size=10", name="GET /api/courses")

    @task(2)
    def echo(self):
        self.client.get("/api/practice/echo?source=locust", name="GET /api/practice/echo")


@events.quitting.add_listener
def enforce_quality_gate(environment, **_kwargs):
    stats = environment.stats.total
    p95_limit_ms = int(os.getenv("PERF_P95_LIMIT_MS", "750"))
    failure_limit = float(os.getenv("PERF_FAILURE_RATIO", "0.01"))
    minimum_requests = int(os.getenv("PERF_MIN_REQUESTS", "20"))
    failures = []
    if stats.num_requests < minimum_requests:
        failures.append(f"requests {stats.num_requests} < {minimum_requests}")
    if stats.fail_ratio > failure_limit:
        failures.append(f"failure ratio {stats.fail_ratio:.4f} > {failure_limit:.4f}")
    p95 = stats.get_response_time_percentile(0.95) or 0
    if p95 > p95_limit_ms:
        failures.append(f"p95 {p95} ms > {p95_limit_ms} ms")
    if failures:
        logging.error("Performance quality gate failed: %s", "; ".join(failures))
        environment.process_exit_code = 1
    else:
        environment.process_exit_code = 0
