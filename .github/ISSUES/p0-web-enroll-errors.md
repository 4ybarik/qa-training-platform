---
title: "[P0] Surface web enroll DomainError to user"
labels: ["P0", "formal", "web"]
---

## Problem

`POST /web/courses/{id}/enroll` caught `DomainError` and silently redirected (303).
Duplicate enroll and other domain failures looked like success to the user.

## Patch

- `backend/app/web/router.py` — redirect with `?enroll_error=...` on `DomainError`
- `backend/app/templates/course_detail.html` — `<p data-testid="enroll-error">`
- `backend/app/web/router.py` — `_ctx` localizes `enroll_error`
- `backend/tests/test_courses_web.py` — `test_web_enroll_duplicate_shows_error`

## Acceptance criteria

- [ ] Duplicate web enroll shows visible error on course page
- [ ] `data-testid="enroll-error"` present in HTML
- [ ] API and web share same `CourseService.enroll` contract

## Spec reference

`formal/tla/adapters/ApiAdapters.tla` — web adapter must not hide service errors
