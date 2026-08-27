"""Локальный исполнитель pytest с машиночитаемым результатом.

В production локальный исполнитель запрещён настройкой. Интерфейс отделён от
API, чтобы заменить его одноразовым контейнерным runner без изменения обучения.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import xml.etree.ElementTree as ET


MAX_OUTPUT_CHARS = 12_000
RUN_TIMEOUT_SECONDS = 180
COVERAGE_ENV_PREFIXES = ("COV_CORE_", "COVERAGE_")


@dataclass(frozen=True)
class TestExecution:
    exit_code: int
    output: str
    truncated: bool
    duration_ms: int
    tests_collected: int
    tests_passed: int
    tests_failed: int
    tests_skipped: int
    timed_out: bool = False


def _junit_counts(path: Path) -> tuple[int, int, int, int]:
    if not path.is_file():
        return 0, 0, 0, 0
    root = ET.parse(path).getroot()
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    total = sum(int(float(item.attrib.get("tests", 0))) for item in suites)
    failed = sum(
        int(float(item.attrib.get("failures", 0))) + int(float(item.attrib.get("errors", 0)))
        for item in suites
    )
    skipped = sum(int(float(item.attrib.get("skipped", 0))) for item in suites)
    return total, max(total - failed - skipped, 0), failed, skipped


def execute_pytest(repo_root: Path, relative_path: str, mutation: str | None = None) -> TestExecution:
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(COVERAGE_ENV_PREFIXES)
    }
    env.setdefault("BASE_URL", "http://localhost:8000")
    if mutation:
        env["TEST_MUTATION"] = mutation
    else:
        env.pop("TEST_MUTATION", None)

    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="qatp-run-") as temp_dir:
        junit = Path(temp_dir) / "junit.xml"
        try:
            completed = subprocess.run(  # noqa: S603 - команда и путь проверены вызывающим кодом
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    relative_path,
                    "-q",
                    f"--junitxml={junit}",
                ],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
                timeout=RUN_TIMEOUT_SECONDS,
            )
            output = (completed.stdout or "") + (completed.stderr or "")
            exit_code = completed.returncode
            timed_out = False
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            output = stdout + stderr + f"\nТаймаут: тесты не завершились за {RUN_TIMEOUT_SECONDS} секунд."
            exit_code = -1
            timed_out = True
        total, passed, failed, skipped = _junit_counts(junit)

    duration_ms = round((time.monotonic() - started) * 1000)
    return TestExecution(
        exit_code=exit_code,
        output=output[-MAX_OUTPUT_CHARS:],
        truncated=len(output) > MAX_OUTPUT_CHARS,
        duration_ms=duration_ms,
        tests_collected=total,
        tests_passed=passed,
        tests_failed=failed,
        tests_skipped=skipped,
        timed_out=timed_out,
    )
