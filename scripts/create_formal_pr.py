#!/usr/bin/env python3
"""Create GitHub PR for formal spec alignment branch on the project owner repo.

Target: 4ybarik/qa-training-platform (upstream)
Head:   maximusmakarov:fix/formal-spec-alignment-p0-p1 (fork)
"""
from __future__ import annotations

import json
import os
import subprocess
import urllib.request


UPSTREAM = "4ybarik/qa-training-platform"
FORK_OWNER = "maximusmakarov"
HEAD_BRANCH = "fix/formal-spec-alignment-p0-p1"
HEAD = f"{FORK_OWNER}:{HEAD_BRANCH}"
BASE = "main"

PR_BODY = """## Summary

- Adds formal model infrastructure (TLA+ specs, python-statemachine oracles, AST inventory, `make formal` / `make tla`)
- Closes P0–P1 gaps between formal specs, ARCHITECTURE.md, and runtime

## Changes

### P0
- Block enroll on ARCHIVED courses (`CourseService.enroll` → 409)
- Surface web enroll `DomainError` via `?enroll_error=` + `data-testid="enroll-error"`

### P1
- Document course delete cascade in ARCHITECTURE.md §3.1
- Exclude `/api/practice` and `/api/integrations` from ApiAdapters invariant (`PracticeTargets.tla`)

## Test plan

- [x] `cd backend && python -m pytest tests/test_courses_api.py tests/test_courses_web.py tests/formal -q` — 53 passed
- [x] `make formal`
- [ ] `make tla` — requires Java or Docker `tlaplus/tlc`

Closes #4
Closes #5
Closes #6
Closes #7
"""


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
    raise SystemExit("No GitHub token found")


def api(token: str, method: str, path: str, payload: dict | None = None) -> dict | list:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        raw = resp.read().decode("utf-8")
        return json.loads(raw) if raw else {}


def main() -> int:
    token = get_token()
    existing = api(
        token,
        "GET",
        f"/repos/{UPSTREAM}/pulls?head={HEAD}&state=open",
    )
    if existing:
        print(f"PR already open: {existing[0]['html_url']}")
        return 0

    result = api(
        token,
        "POST",
        f"/repos/{UPSTREAM}/pulls",
        {
            "title": "fix(formal): align runtime with TLA specs (P0-P1)",
            "head": HEAD,
            "base": BASE,
            "body": PR_BODY,
            "maintainer_can_modify": True,
        },
    )
    print(result["html_url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
