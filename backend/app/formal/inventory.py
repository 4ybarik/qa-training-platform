"""AST inventory of backend/app — source of truth for formal spec coverage."""
from __future__ import annotations

import ast
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

Tier = Literal["A", "B", "C", "schema", "adapter", "skip"]

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parents[1]
FORMAL_TLA = REPO_ROOT / "formal" / "tla"

# Explicit tier-A process specs (state machines with TLC).
TIER_A_SPECS: dict[str, str] = {
    "AuthService": "services/AuthAccount.tla",
    "CourseService": "services/CourseLifecycle.tla",
    "Enrollment": "services/CourseLifecycle.tla",
    "ExamService": "services/ExamAttempt.tla",
    "NotificationService": "services/Notification.tla",
    "AdminService": "services/AdminUser.tla",
    "TestSupportService": "services/TestRun.tla",
    "PracticeJob": "practice/Job.tla",
    "PracticeResource": "practice/Resource.tla",
    "RateLimiter": "core/RateLimiter.tla",
    "PlaygroundMiddleware": "middleware/Playground.tla",
}

# Tier-B ORM entities and repositories (TypeOK + lifecycle).
TIER_B_ENTITIES: frozenset[str] = frozenset({
    "User", "Profile", "Course", "Enrollment", "Exam", "Question", "Answer",
    "Notification", "AuditLog", "ExamAttempt", "TestRunEntity",
    "CourseRepository", "EnrollmentRepository", "UserRepository", "ProfileRepository",
    "ExamRepository", "NotificationRepository", "AuditRepository",
})

# Tier-C pure/adapter modules (pre/post, no invented states).
TIER_C_MODULES: frozenset[str] = frozenset({
    "security", "deps", "database", "i18n", "mutations", "catalog", "quality",
    "errors", "enums", "config", "tasks", "ApiAdapters",
})

# Pydantic schemas and API DTOs live in Types.tla / ApiAdapters.tla.
SCHEMA_MODULE = "domain/schemas.py"

# Practice/integration APIs hold their own in-memory or adapter state.
PRACTICE_ADAPTER_PREFIXES: frozenset[str] = frozenset({
    "app.api.practice",
    "app.api.integrations",
})

SKIP_MODULES: frozenset[str] = frozenset({
    "seed.py", "seed_content.py", "main.py", "__init__.py",
})


@dataclass
class Symbol:
    kind: Literal["class", "function"]
    name: str
    module: str
    file: str
    line: int
    tier: Tier
    spec: str


@dataclass
class Inventory:
    symbols: list[Symbol] = field(default_factory=list)

    def coverage_table(self) -> list[dict[str, str | int]]:
        return [
            {
                "kind": s.kind,
                "name": s.name,
                "module": s.module,
                "file": s.file,
                "line": s.line,
                "tier": s.tier,
                "spec": s.spec,
            }
            for s in sorted(self.symbols, key=lambda x: (x.file, x.line))
        ]

    def uncovered(self) -> list[Symbol]:
        return [s for s in self.symbols if s.spec == "UNMAPPED"]

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.symbols:
            counts[s.tier] = counts.get(s.tier, 0) + 1
        counts["total"] = len(self.symbols)
        counts["unmapped"] = len(self.uncovered())
        return counts


def _module_name(path: Path) -> str:
    rel = path.relative_to(APP_ROOT)
    parts = list(rel.parts[:-1]) + [rel.stem]
    return ".".join(parts)


def _resolve_tier(name: str, kind: str, module: str, file: str) -> tuple[Tier, str]:
    if any(file.endswith(s) for s in SKIP_MODULES):
        return "skip", "N/A"

    if file == SCHEMA_MODULE or module.endswith("schemas"):
        return "schema", "domain/Types.tla"

    if name in TIER_A_SPECS:
        return "A", TIER_A_SPECS[name]

    if kind == "class" and name in TIER_B_ENTITIES:
        return "B", "domain/Entities.tla"

    module_stem = module.split(".")[-1]
    if module_stem in TIER_C_MODULES or any(
        module.endswith(f".{m}") for m in TIER_C_MODULES
    ):
        if module.startswith("app.api") or module.startswith("app.web"):
            return "adapter", "adapters/ApiAdapters.tla"
        return "C", f"modules/{module_stem.capitalize()}.tla"

    if module.startswith("app.api") or module.startswith("app.web"):
        if any(module.startswith(p) for p in PRACTICE_ADAPTER_PREFIXES):
            return "adapter", "adapters/PracticeTargets.tla"
        return "adapter", "adapters/ApiAdapters.tla"

    if module.startswith("app.services"):
        return "A", f"services/{name}.tla"

    if module.startswith("app.domain"):
        if kind == "class":
            return "schema", "domain/Types.tla"
        return "C", "domain/Types.tla"

    if module.startswith("app.repositories"):
        return "B", "domain/Entities.tla"

    if module.startswith("app.practice"):
        return "C", "practice/PracticeModule.tla"

    if module.startswith("app.core"):
        return "C", f"core/{module_stem.capitalize()}.tla"

    if module.startswith("app.integrations"):
        return "adapter", "adapters/PracticeTargets.tla"

    if module.startswith("app.middleware"):
        return "A", "middleware/Playground.tla"

    return "C", "modules/Misc.tla"


def scan_app(root: Path | None = None) -> Inventory:
    root = root or APP_ROOT
    inventory = Inventory()

    for path in sorted(root.rglob("*.py")):
        if "formal" in path.parts:
            continue
        rel = path.relative_to(APP_ROOT).as_posix()
        module = _module_name(path)
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                tier, spec = _resolve_tier(node.name, "class", module, rel)
                inventory.symbols.append(
                    Symbol("class", node.name, module, rel, node.lineno, tier, spec)
                )
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name.startswith("_") and node.name not in {"__init__"}:
                    continue
                tier, spec = _resolve_tier(node.name, "function", module, rel)
                inventory.symbols.append(
                    Symbol("function", node.name, module, rel, node.lineno, tier, spec)
                )

    return inventory


def write_coverage_report(path: Path | None = None) -> dict[str, int | list]:
    inv = scan_app()
    report = {"summary": inv.summary(), "symbols": inv.coverage_table()}
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    out = REPO_ROOT / "formal" / "coverage.json"
    report = write_coverage_report(out)
    print(json.dumps(report["summary"], indent=2))
