"""Оценка ученического теста: baseline, инженерная политика и мутации."""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from app.learning.catalog import Lesson
from app.learning.runner import TestExecution, execute_pytest


@dataclass(frozen=True)
class Criterion:
    code: str
    title: str
    passed: bool
    details: str


@dataclass(frozen=True)
class Grade:
    baseline: TestExecution
    criteria: tuple[Criterion, ...]
    score: int
    passed: bool


def _call_name(node: ast.Call) -> str:
    parts: list[str] = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


def inspect_source(path: Path, expected_marker: str) -> Criterion:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return Criterion("source-quality", "Код решения проходит статическую проверку", False, str(exc))

    tests = [
        node for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_")
    ]
    problems: list[str] = []
    if not tests:
        problems.append("не найдена функция test_*")
    marker_found = False
    for test in tests:
        for decorator in test.decorator_list:
            if isinstance(decorator, ast.Attribute) and decorator.attr == expected_marker:
                marker_found = True
            if isinstance(decorator, ast.Call) and _call_name(decorator).endswith(expected_marker):
                marker_found = True
        for node in ast.walk(test):
            if isinstance(node, ast.Pass):
                problems.append(f"строка {node.lineno}: пустой test_* через pass")
            if isinstance(node, ast.Assert) and isinstance(node.test, ast.Constant) and node.test.value is True:
                problems.append(f"строка {node.lineno}: assert True не проверяет поведение")
            if isinstance(node, ast.Call) and _call_name(node) == "time.sleep":
                problems.append(f"строка {node.lineno}: фиксированный time.sleep создаёт нестабильность")
    if not marker_found:
        problems.append(f"нет ожидаемого маркера @pytest.mark.{expected_marker}")
    return Criterion(
        "source-quality",
        "Код решения проходит статическую проверку",
        not problems,
        "; ".join(dict.fromkeys(problems)) if problems else f"Найдено тестов: {len(tests)}",
    )


def grade_lesson(repo_root: Path, relative_path: str, source_path: Path, lesson: Lesson) -> Grade:
    baseline = execute_pytest(repo_root, relative_path)
    baseline_ok = baseline.exit_code == 0 and baseline.tests_collected > 0
    criteria: list[Criterion] = [
        Criterion(
            "baseline",
            "Тесты проходят на исправном стенде",
            baseline_ok,
            (
                f"Собрано: {baseline.tests_collected}; прошло: {baseline.tests_passed}; "
                f"упало: {baseline.tests_failed}"
            ),
        )
    ]
    folder = lesson.editable_path.split("/", 1)[0] if lesson.editable_path else "api"
    expected_marker = folder if folder in {"api", "contract", "integration", "ui"} else "reliability"
    criteria.append(inspect_source(source_path, expected_marker))

    for mutation_id in lesson.mutation_ids:
        if not baseline_ok:
            criteria.append(Criterion(
                f"mutation:{mutation_id}",
                f"Тест обнаруживает дефект {mutation_id}",
                False,
                "Сначала исправьте baseline-прогон.",
            ))
            continue
        mutated = execute_pytest(repo_root, relative_path, mutation=mutation_id)
        killed = mutated.exit_code == 1 and mutated.tests_failed > 0
        criteria.append(Criterion(
            f"mutation:{mutation_id}",
            f"Тест обнаруживает дефект {mutation_id}",
            killed,
            (
                f"Код pytest: {mutated.exit_code}; упавших тестов: {mutated.tests_failed}."
                if not killed else "Контролируемый дефект корректно привёл к падению теста."
            ),
        ))

    passed_count = sum(item.passed for item in criteria)
    score = round(passed_count / len(criteria) * 100) if criteria else 0
    return Grade(
        baseline=baseline,
        criteria=tuple(criteria),
        score=score,
        passed=bool(criteria) and passed_count == len(criteria),
    )
