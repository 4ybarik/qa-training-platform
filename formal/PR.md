# Pull Request: Formal spec alignment (P0–P1)

**Upstream (project owner):** [`4ybarik/qa-training-platform`](https://github.com/4ybarik/qa-training-platform)
**PR:** https://github.com/4ybarik/qa-training-platform/pull/3
**Head:** `maximusmakarov:fix/formal-spec-alignment-p0-p1` → `main`

## Summary

- Adds formal model infrastructure (TLA+ specs, python-statemachine oracles, AST inventory, `make formal` / `make tla`)
- Closes P0–P1 gaps between formal specs, ARCHITECTURE.md, and runtime

## Changes by issue

### [P0] Block enroll on ARCHIVED courses — [#4](https://github.com/4ybarik/qa-training-platform/issues/4)

| File | Change |
|------|--------|
| `backend/app/services/courses.py` | `ConflictError` when `course.status == ARCHIVED` |
| `backend/app/formal/machines/course_lifecycle.py` | Oracle guard on `course_status` |
| `backend/tests/test_courses_api.py` | `test_enroll_archived_course_conflict` |

### [P0] Surface web enroll errors — [#5](https://github.com/4ybarik/qa-training-platform/issues/5)

| File | Change |
|------|--------|
| `backend/app/web/router.py` | Redirect `?enroll_error=` on `DomainError` |
| `backend/app/templates/course_detail.html` | `data-testid="enroll-error"` |
| `backend/tests/test_courses_web.py` | Web duplicate enroll test |

### [P1] Document delete cascade — [#6](https://github.com/4ybarik/qa-training-platform/issues/6)

| File | Change |
|------|--------|
| `ARCHITECTURE.md` | §3.1 cascade delete documented |
| `formal/LIMITATIONS.md` | Accepted limitation recorded |

### [P1] ApiAdapters scope — [#7](https://github.com/4ybarik/qa-training-platform/issues/7)

| File | Change |
|------|--------|
| `formal/tla/adapters/PracticeTargets.tla` | Practice/integration spec |
| `backend/app/formal/inventory.py` | Route practice/integration to PracticeTargets |
| `formal/LIMITATIONS.md` | Exclusion list |

## Test plan

- [x] `cd backend && python -m pytest tests/test_courses_api.py tests/test_courses_web.py tests/formal -q` — 53 passed
- [x] `make formal` — inventory + formal tests
- [ ] `make tla` — requires Java or Docker `tlaplus/tlc` (optional CI stage)

## Closes

```
Closes #4  P0 archived enroll
Closes #5  P0 web enroll errors
Closes #6  P1 delete cascade docs
Closes #7  P1 ApiAdapters scope
```
