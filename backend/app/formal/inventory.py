"""AST inventory of backend/app — source of truth for formal spec coverage.

Module names are relative to ``backend/app`` (e.g. ``api.auth``, not ``app.api.auth``).
Class methods inherit the parent class's Tier-A/B mapping when known.
"""
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

# Explicit process specs (state machines with TLC / oracles).
TIER_A_CLASSES: dict[str, str] = {
    "AuthService": "services/AuthAccount.tla",
    "CourseService": "services/CourseLifecycle.tla",
    "Enrollment": "services/CourseLifecycle.tla",
    "ExamService": "services/ExamAttempt.tla",
    "NotificationService": "services/Notification.tla",
    "AdminService": "services/AdminUser.tla",
    "ProfileService": "services/Profile.tla",
    "TestSupportService": "services/TestRun.tla",
    "RateLimiter": "core/RateLimiter.tla",
    "PlaygroundMiddleware": "middleware/Playground.tla",
    "PlaygroundState": "middleware/Playground.tla",
}

# ORM entities and repositories (TypeOK + lifecycle).
TIER_B_CLASSES: frozenset[str] = frozenset({
    "User", "Profile", "Course", "Enrollment", "Exam", "Question", "Answer",
    "Notification", "AuditLog", "ExamAttempt", "TestRunEntity",
    "CourseRepository", "EnrollmentRepository", "UserRepository", "ProfileRepository",
    "ExamRepository", "NotificationRepository", "AuditRepository",
})

# Pure / utility packages → modules/<Name>.tla
TIER_C_PACKAGES: dict[str, str] = {
    "core.security": "modules/Security.tla",
    "core.database": "modules/Database.tla",
    "core.config": "modules/Config.tla",
    "core.rate_limit": "core/RateLimiter.tla",
    "api.deps": "modules/Deps.tla",
    "api.errors": "modules/Errors.tla",
    "domain.errors": "modules/Errors.tla",
    "domain.enums": "modules/Enums.tla",
    "web.i18n": "modules/I18n.tla",
    "practice.mutations": "modules/Mutations.tla",
    "practice.catalog": "modules/Catalog.tla",
    "services.quality": "modules/Quality.tla",
    "api.quality": "modules/Quality.tla",
    "integrations.tasks": "modules/Tasks.tla",
}

# Packages that own in-memory / external adapter state (not domain services).
PRACTICE_PACKAGES: frozenset[str] = frozenset({
    "api.practice",
    "api.integrations",
    "integrations",
    "integrations.tasks",
})

# Domain HTTP adapters (delegate to services).
API_ADAPTER_PREFIXES: tuple[str, ...] = (
    "api.",
    "web.",
)

SKIP_FILES: frozenset[str] = frozenset({
    "seed.py", "seed_content.py", "main.py", "__init__.py",
})

# Specs that must exist under formal/tla/ after inventory rewrite.
REQUIRED_MODULE_SPECS: frozenset[str] = frozenset({
    "modules/Security.tla",
    "modules/Database.tla",
    "modules/Config.tla",
    "modules/Deps.tla",
    "modules/Errors.tla",
    "modules/Enums.tla",
    "modules/I18n.tla",
    "modules/Mutations.tla",
    "modules/Catalog.tla",
    "modules/Quality.tla",
    "modules/Tasks.tla",
    "services/Profile.tla",
    "practice/PracticeModule.tla",
})


@dataclass
class Symbol:
    kind: Literal["class", "function", "method"]
    name: str
    module: str
    file: str
    line: int
    tier: Tier
    spec: str
    owner: str | None = None  # class name for methods


@dataclass
class Inventory:
    symbols: list[Symbol] = field(default_factory=list)

    def coverage_table(self) -> list[dict[str, str | int | None]]:
        return [
            {
                "kind": s.kind,
                "name": s.name,
                "owner": s.owner,
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

    def misc(self) -> list[Symbol]:
        return [s for s in self.symbols if s.spec == "modules/Misc.tla"]

    def summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.symbols:
            counts[s.tier] = counts.get(s.tier, 0) + 1
        counts["total"] = len(self.symbols)
        counts["unmapped"] = len(self.uncovered())
        counts["misc"] = len(self.misc())
        return counts

    def by_spec(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for s in self.symbols:
            counts[s.spec] = counts.get(s.spec, 0) + 1
        return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _module_name(path: Path) -> str:
    rel = path.relative_to(APP_ROOT)
    parts = list(rel.parts[:-1]) + [rel.stem]
    return ".".join(parts)


def _package_of(module: str) -> str:
    return module.rsplit(".", 1)[0] if "." in module else module


def _resolve_for_class(class_name: str, module: str) -> tuple[Tier, str] | None:
    if class_name in TIER_A_CLASSES:
        return "A", TIER_A_CLASSES[class_name]
    if class_name in TIER_B_CLASSES:
        return "B", "domain/Entities.tla"
    if module in TIER_C_PACKAGES:
        return "C", TIER_C_PACKAGES[module]
    if module.endswith("schemas") or module == "domain.schemas":
        return "schema", "domain/Types.tla"
    if module.startswith("domain."):
        return "schema", "domain/Types.tla"
    return None


def _resolve_module(module: str, file: str) -> tuple[Tier, str]:
    if any(file.endswith(s) for s in SKIP_FILES) or file.endswith("/__init__.py"):
        return "skip", "N/A"

    if file == "domain/schemas.py" or module.endswith("schemas"):
        return "schema", "domain/Types.tla"

    if module in TIER_C_PACKAGES:
        return "C", TIER_C_PACKAGES[module]

    # Exact package roots
    if module in PRACTICE_PACKAGES or any(
        module.startswith(f"{p}.") for p in PRACTICE_PACKAGES if "." in p
    ) or module.startswith("api.practice") or module.startswith("api.integrations"):
        return "adapter", "adapters/PracticeTargets.tla"

    if module.startswith("api.") or module.startswith("web."):
        # api.deps / api.errors / api.quality already handled via TIER_C_PACKAGES
        return "adapter", "adapters/ApiAdapters.tla"

    if module.startswith("services."):
        # Fallback for unknown service helpers — still domain service layer
        return "A", f"services/{module.split('.', 1)[1].capitalize()}.tla"

    if module.startswith("repositories."):
        return "B", "domain/Entities.tla"

    if module.startswith("domain."):
        return "schema", "domain/Types.tla"

    if module.startswith("practice."):
        return "C", "practice/PracticeModule.tla"

    if module.startswith("core."):
        stem = module.split(".", 1)[1]
        return "C", f"core/{stem.capitalize()}.tla"

    if module.startswith("integrations"):
        return "adapter", "adapters/PracticeTargets.tla"

    if module.startswith("middleware"):
        return "A", "middleware/Playground.tla"

    return "C", "modules/Misc.tla"


def _resolve_symbol(
    *,
    name: str,
    kind: Literal["class", "function", "method"],
    module: str,
    file: str,
    owner: str | None = None,
) -> tuple[Tier, str]:
    if any(file.endswith(s) for s in SKIP_FILES):
        return "skip", "N/A"

    if kind == "class":
        mapped = _resolve_for_class(name, module)
        if mapped:
            return mapped
        return _resolve_module(module, file)

    if kind == "method" and owner:
        mapped = _resolve_for_class(owner, module)
        if mapped:
            return mapped

    # Top-level function or unowned method — package rules
    return _resolve_module(module, file)


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

        # Top-level only: classes, functions, and methods under classes.
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                tier, spec = _resolve_symbol(
                    name=node.name, kind="class", module=module, file=rel
                )
                inventory.symbols.append(
                    Symbol("class", node.name, module, rel, node.lineno, tier, spec)
                )
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name.startswith("_") and child.name != "__init__":
                            continue
                        mtier, mspec = _resolve_symbol(
                            name=child.name,
                            kind="method",
                            module=module,
                            file=rel,
                            owner=node.name,
                        )
                        inventory.symbols.append(
                            Symbol(
                                "method",
                                child.name,
                                module,
                                rel,
                                child.lineno,
                                mtier,
                                mspec,
                                owner=node.name,
                            )
                        )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("_") and node.name != "__init__":
                    continue
                tier, spec = _resolve_symbol(
                    name=node.name, kind="function", module=module, file=rel
                )
                inventory.symbols.append(
                    Symbol("function", node.name, module, rel, node.lineno, tier, spec)
                )

    return inventory


def missing_spec_files(inv: Inventory | None = None) -> list[str]:
    inv = inv or scan_app()
    missing: list[str] = []
    for spec in sorted({s.spec for s in inv.symbols if s.spec not in {"N/A", "UNMAPPED"}}):
        if not (FORMAL_TLA / spec).exists():
            missing.append(spec)
    return missing


def write_coverage_report(path: Path | None = None) -> dict[str, object]:
    inv = scan_app()
    report = {
        "summary": inv.summary(),
        "by_spec": inv.by_spec(),
        "missing_specs": missing_spec_files(inv),
        "symbols": inv.coverage_table(),
    }
    if path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


if __name__ == "__main__":
    out = REPO_ROOT / "formal" / "coverage.json"
    report = write_coverage_report(out)
    print(json.dumps({"summary": report["summary"], "by_spec": report["by_spec"],
                      "missing_specs": report["missing_specs"]}, indent=2))
