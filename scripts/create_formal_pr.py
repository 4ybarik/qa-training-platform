#!/usr/bin/env python3
"""Create GitHub PR for formal spec alignment branch."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.request


REPO = "maximusmakarov/qa-training-platform"
HEAD = "fix/formal-spec-alignment-p0-p1"
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

Closes #1
Closes #2
Closes #3
Closes #4
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


def api_post(token: str, path: str, payload: dict) -> dict:
    req = urllib.request.Request(
        f"https://api.github.com{path}",
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    token = get_token()
    # Avoid duplicate PR
    list_req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/pulls?head={REPO.split('/')[0]}:{HEAD}&state=open",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(list_req) as resp:
        existing = json.loads(resp.read().decode("utf-8"))
    if existing:
        print(f"PR already open: {existing[0]['html_url']}")
        return 0

    result = api_post(
        token,
        f"/repos/{REPO}/pulls",
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
