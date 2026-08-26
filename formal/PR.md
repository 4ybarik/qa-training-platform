# Pull Request: Formal spec alignment (P0–P1)

**Branch:** `fix/formal-spec-alignment-p0-p1`  
**Base:** `main`  
**Create:** https://github.com/maximusmakarov/qa-training-platform/pull/new/fix/formal-spec-alignment-p0-p1

## Summary

- Adds formal model infrastructure (TLA+ specs, python-statemachine oracles, AST inventory, `make formal` / `make tla`)
- Closes P0–P1 gaps between formal specs, ARCHITECTURE.md, and runtime

## Changes by issue

### [P0] Block enroll on ARCHIVED courses

| File | Change |
|------|--------|
| `backend/app/services/courses.py` | `ConflictError` when `course.status == ARCHIVED` |
| `backend/app/formal/machines/course_lifecycle.py` | Oracle guard on `course_status` |
| `backend/tests/test_courses_api.py` | `test_enroll_archived_course_conflict` |

### [P0] Surface web enroll errors

| File | Change |
|------|--------|
| `backend/app/web/router.py` | Redirect `?enroll_error=` on `DomainError` |
| `backend/app/templates/course_detail.html` | `data-testid="enroll-error"` |
| `backend/tests/test_courses_web.py` | Web duplicate enroll test |

### [P1] Document delete cascade

| File | Change |
|------|--------|
| `ARCHITECTURE.md` | §3.1 cascade delete documented |
| `formal/LIMITATIONS.md` | Accepted limitation recorded |

### [P1] ApiAdapters scope

| File | Change |
|------|--------|
| `formal/tla/adapters/PracticeTargets.tla` | Practice/integration spec |
| `backend/app/formal/inventory.py` | Route practice/integration to PracticeTargets |
| `formal/LIMITATIONS.md` | Exclusion list |

## Test plan

- [x] `cd backend && python -m pytest tests/test_courses_api.py tests/test_courses_web.py tests/formal -q` — 53 passed
- [x] `make formal` — inventory + formal tests
- [ ] `make tla` — requires Java or Docker `tlaplus/tlc` (optional CI stage)

## Reviewer notes

- Machines in `backend/app/formal/machines/` are **oracles**, not wired into production services
- Course delete behavior unchanged (cascade) — only documented
- Create GitHub issues from `.github/ISSUES/p0-*.md` and `p1-*.md` if not using `gh cli`

## Suggested commit to link issues (after creating issues on GitHub)

Replace `#NN` with issue numbers:

```
Closes #NN  P0 archived enroll
Closes #NN  P0 web enroll errors
Closes #NN  P1 delete cascade docs
Closes #NN  P1 ApiAdapters scope
```
