---
title: "[P0] Block enroll on ARCHIVED courses"
labels: ["P0", "formal", "courses"]
---

## Problem

TLA `CourseLifecycle.tla` forbids `Enroll` when `courseStatus = ARCHIVED`.
Runtime `CourseService.enroll` did not check course status — users could enroll on archived courses.

## Patch (in branch `fix/formal-spec-alignment-p0-p1`)

- `backend/app/services/courses.py` — `ConflictError` if `course.status == ARCHIVED`
- `backend/app/formal/machines/course_lifecycle.py` — oracle `try_enroll(..., course_status=)`
- `backend/tests/test_courses_api.py` — `test_enroll_archived_course_conflict`
- `backend/tests/formal/test_tlc_invariants.py` — `test_archived_course_forbidden`

## Acceptance criteria

- [ ] `POST /api/courses/{archived_id}/enroll` → **409** with message about archived course
- [ ] `pytest tests/test_courses_api.py::test_enroll_archived_course_conflict` passes
- [ ] Formal oracle rejects `ARCHIVED` enroll

## Spec reference

`formal/tla/services/CourseLifecycle.tla` — action `Enroll`, guard `courseStatus[c] # "ARCHIVED"`
