# Formal spec alignment — P0/P1 issues

Tracking issues for discrepancies found during TLA+ / python-statemachine analysis.

## P0 — must fix before relying on invariants

| ID | Title | Scope |
|----|-------|-------|
| #1 | Block enroll on ARCHIVED courses | `CourseService.enroll`, API 409, formal oracle |
| #2 | Surface web enroll errors to user | `web/router.py`, `course_detail.html`, web test |

## P1 — document or narrow spec scope

| ID | Title | Scope |
|----|-------|-------|
| #3 | Document course delete cascade | `ARCHITECTURE.md` §3.1, `LIMITATIONS.md` |
| #4 | Exclude practice/integration from ApiAdapters | `ApiAdapters.tla`, `PracticeTargets.tla`, inventory |

## Verification

```bash
cd backend && python -m pytest tests/test_courses_api.py tests/test_courses_web.py tests/formal -q
make formal
```

Replace `#N` with actual GitHub issue numbers after `gh issue create`.
