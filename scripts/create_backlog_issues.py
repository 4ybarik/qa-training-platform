#!/usr/bin/env python3
"""Create backlog P1/P2 bilingual issues on 4ybarik/qa-training-platform."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "4ybarik/qa-training-platform"
ROOT = Path(__file__).resolve().parents[1]
ISSUES_DIR = ROOT / ".github" / "ISSUES"

BACKLOG = [
    {
        "file": "p1-web-admin-active-errors.md",
        "title": "[P1][web] Surface admin set_active DomainError · Показ ошибок admin set_active",
        "labels": ["P1", "formal", "web"],
    },
    {
        "file": "p1-enroll-draft-policy.md",
        "title": "[P1][courses] Define enroll policy for DRAFT · Политика записи на DRAFT",
        "labels": ["P1", "formal", "courses"],
    },
    {
        "file": "p2-exam-submit-enrollment.md",
        "title": "[P2][exams] Exam submit vs enrollment · Сдача экзамена и enrollment",
        "labels": ["P2", "formal", "courses"],
    },
    {
        "file": "p2-manager-rbac.md",
        "title": "[P2][rbac] MANAGER permissions or drop promises · Права MANAGER или убрать обещания",
        "labels": ["P2", "formal", "documentation"],
    },
    {
        "file": "p2-ci-formal-tests.md",
        "title": "[P2][ci] Add formal tests to CI · Formal-тесты в CI",
        "labels": ["P2", "formal", "documentation"],
    },
    {
        "file": "p2-exam-timer-ui-only.md",
        "title": "[P2][exams] Document exam timer is client-only · Таймер экзамена только UI",
        "labels": ["P2", "formal", "documentation"],
    },
    {
        "file": "p2-progress-check-constraint.md",
        "title": "[P2][db] Enforce progress 0..100 CheckConstraint · Constraint progress 0..100",
        "labels": ["P2", "formal", "courses"],
    },
]

EXTRA_LABELS = [
    {"name": "P2", "color": "fbca04", "description": "Important follow-up: product decision or CI/integrity"},
]


def get_token() -> str:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n",
        capture_output=True,
        text=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise SystemExit("No GitHub token")


def strip_front_matter(text: str) -> str:
    match = re.match(r"\A---\r?\n.*?\r?\n---\r?\n(.*)\Z", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def api(token: str, method: str, path: str, payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()
        # Labels may 404 without write; issues may work without labels
        raise SystemExit(f"{method} {path} -> {exc.code}: {body[:500]}") from exc


def ensure_label(token: str, label: dict) -> None:
    try:
        api(token, "POST", f"/repos/{REPO}/labels", label)
        print(f"  label created: {label['name']}")
    except SystemExit as exc:
        if "422" in str(exc):
            print(f"  label exists: {label['name']}")
        else:
            print(f"  label skip ({label['name']}): {exc}")


def create_issue(token: str, title: str, body: str, labels: list[str]) -> dict:
    # Upstream may disallow creating labels on issues for fork collaborators.
    payload = {"title": title, "body": body}
    _ = labels  # kept in templates for maintainers
    return api(token, "POST", f"/repos/{REPO}/issues", payload)


def main() -> int:
    dry = "--dry-run" in sys.argv
    token = get_token()
    # Label create needs write on upstream; skip for fork collaborators.

    created: list[str] = []
    for item in BACKLOG:
        path = ISSUES_DIR / item["file"]
        body = strip_front_matter(path.read_text(encoding="utf-8"))
        print(f"\n=== {item['title']} ===")
        if dry:
            print(f"  body chars: {len(body)}")
            continue
        issue = create_issue(token, item["title"], body, item["labels"])
        print(f"  -> {issue['html_url']}")
        created.append(issue["html_url"])

    if created:
        print("\nCreated:")
        for url in created:
            print(f"  {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
