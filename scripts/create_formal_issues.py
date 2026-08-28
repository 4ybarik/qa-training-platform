#!/usr/bin/env python3
"""Create formal P0/P1 GitHub issues (bilingual EN/RU bodies).

Requires environment variable GITHUB_TOKEN with ``repo`` scope.

Usage:
    set GITHUB_TOKEN=ghp_...
    python scripts/create_formal_issues.py
    python scripts/create_formal_issues.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "4ybarik/qa-training-platform"
ROOT = Path(__file__).resolve().parents[1]
ISSUES_DIR = ROOT / ".github" / "ISSUES"
BODIES_DIR = ISSUES_DIR / "bodies"
LABELS_FILE = ROOT / ".github" / "labels-formal.json"

ISSUES = [
    {
        "file": "p0-block-enroll-archived.md",
        "title": "[P0][formal] Block enroll on ARCHIVED courses · Запрет записи на ARCHIVED-курс",
        "labels": ["P0", "formal", "courses"],
    },
    {
        "file": "p0-web-enroll-errors.md",
        "title": "[P0][formal] Surface web enroll errors · Показ ошибок web-enroll пользователю",
        "labels": ["P0", "formal", "web"],
    },
    {
        "file": "p1-document-delete-cascade.md",
        "title": "[P1][formal] Document course delete cascade · Документировать каскадное удаление курса",
        "labels": ["P1", "formal", "documentation", "courses"],
    },
    {
        "file": "p1-exclude-practice-from-apiadapters.md",
        "title": "[P1][formal] Exclude practice/integration from ApiAdapters · Исключить practice из ApiAdapters",
        "labels": ["P1", "formal", "practice", "documentation"],
    },
]


def strip_front_matter(text: str) -> str:
    match = re.match(r"\A---\r?\n.*?\r?\n---\r?\n(.*)\Z", text, re.DOTALL)
    return match.group(1).strip() if match else text.strip()


def load_body(filename: str) -> str:
    path = ISSUES_DIR / filename
    return strip_front_matter(path.read_text(encoding="utf-8"))


def export_bodies() -> None:
    BODIES_DIR.mkdir(parents=True, exist_ok=True)
    for item in ISSUES:
        body = load_body(item["file"])
        out = BODIES_DIR / item["file"]
        out.write_text(body + "\n", encoding="utf-8")


def api_request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ensure_labels(token: str) -> None:
    if not LABELS_FILE.exists():
        return
    labels = json.loads(LABELS_FILE.read_text(encoding="utf-8"))
    for label in labels:
        url = f"https://api.github.com/repos/{REPO}/labels"
        try:
            api_request("POST", url, token, label)
            print(f"  label created: {label['name']}")
        except urllib.error.HTTPError as exc:
            if exc.code == 422:
                print(f"  label exists: {label['name']}")
            else:
                raise


def create_issue(token: str, title: str, body: str, labels: list[str]) -> dict:
    url = f"https://api.github.com/repos/{REPO}/issues"
    return api_request("POST", url, token, {"title": title, "body": body, "labels": labels})


def main() -> int:
    parser = argparse.ArgumentParser(description="Create formal GitHub issues")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--export-bodies", action="store_true", help="Write body-only files to .github/ISSUES/bodies/")
    parser.add_argument("--ensure-labels", action="store_true")
    args = parser.parse_args()

    export_bodies()
    if args.export_bodies:
        print(f"Exported {len(ISSUES)} body files to {BODIES_DIR}")
        if args.dry_run or not os.environ.get("GITHUB_TOKEN"):
            return 0

    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if args.dry_run:
        for item in ISSUES:
            body = load_body(item["file"])
            print(f"\n=== {item['title']} ===")
            print(f"labels: {', '.join(item['labels'])}")
            print(f"body: {len(body)} chars")
        return 0

    if not token:
        print(
            "GITHUB_TOKEN not set. Options:\n"
            "  1. Fine-grained PAT: https://github.com/settings/tokens — Issues: Read and write\n"
            "  2. set GITHUB_TOKEN=ghp_... && python scripts/create_formal_issues.py\n"
            "  3. gh auth login && pwsh scripts/create-formal-issues.ps1\n"
            "  4. Paste bodies from .github/ISSUES/bodies/ into GitHub UI manually",
            file=sys.stderr,
        )
        return 1

    if args.ensure_labels:
        print("Ensuring labels...")
        ensure_labels(token)

    created: list[str] = []
    for item in ISSUES:
        body = load_body(item["file"])
        print(f"Creating: {item['title']}")
        result = create_issue(token, item["title"], body, item["labels"])
        url = result.get("html_url", result)
        print(f"  -> {url}")
        created.append(url)

    print("\nCreated issues:")
    for url in created:
        print(f"  {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
