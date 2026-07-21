"""Статический quality gate для решений в student_tests."""
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path


def _call_name(node: ast.Call) -> str:
    parts = []
    value = node.func
    while isinstance(value, ast.Attribute):
        parts.append(value.attr)
        value = value.value
    if isinstance(value, ast.Name):
        parts.append(value.id)
    return ".".join(reversed(parts))


def inspect_file(path: Path) -> tuple[int, list[dict], list[dict]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    errors: list[dict] = []
    warnings: list[dict] = []
    tests = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    for test in tests:
        for node in ast.walk(test):
            if isinstance(node, ast.Assert) and isinstance(node.test, ast.Constant):
                if node.test.value is True:
                    errors.append({
                        "file": str(path),
                        "line": node.lineno,
                        "rule": "no-assert-true",
                        "message": "assert True не проверяет поведение системы",
                    })
            if isinstance(node, ast.Pass):
                errors.append({
                    "file": str(path),
                    "line": node.lineno,
                    "rule": "no-empty-test",
                    "message": "Пустой test_* не считается решением",
                })
            if isinstance(node, ast.Call) and _call_name(node) == "time.sleep":
                warnings.append({
                    "file": str(path),
                    "line": node.lineno,
                    "rule": "avoid-fixed-sleep",
                    "message": "Используйте ожидание состояния с конечным deadline",
                })
        decorators = [
            _call_name(item) if isinstance(item, ast.Call) else ""
            for item in test.decorator_list
        ]
        if any(name.endswith(("skip", "xfail")) for name in decorators):
            warnings.append({
                "file": str(path),
                "line": test.lineno,
                "rule": "review-skipped-test",
                "message": "skip/xfail должен иметь проверяемую причину и срок удаления",
            })
    return len(tests), errors, warnings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("root", nargs="?", default="student_tests")
    parser.add_argument("--output", default="ci-artifacts/test-policy.json")
    args = parser.parse_args()
    root = Path(args.root)
    files = sorted(
        path
        for path in root.rglob("test_*.py")
        if "_task_template" not in path.name and "_accessibility_template" not in path.name
    )
    total = 0
    errors: list[dict] = []
    warnings: list[dict] = []
    for path in files:
        count, file_errors, file_warnings = inspect_file(path)
        total += count
        errors.extend(file_errors)
        warnings.extend(file_warnings)
    if total == 0:
        errors.append({
            "file": str(root),
            "line": 0,
            "rule": "tests-required",
            "message": "Не найдено ни одного test_*",
        })
    result = {
        "files": len(files),
        "tests": total,
        "errors": errors,
        "warnings": warnings,
        "passed": not errors,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
