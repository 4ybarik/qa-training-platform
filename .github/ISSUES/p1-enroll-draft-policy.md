---
title: "[P1][courses] Define enroll policy for DRAFT courses"
labels: ["P1", "formal", "courses"]
---

> **Languages:** English · Русский
> **Type:** product decision + enforcement
> **Priority:** P1
> **Related:** #4 (ARCHIVED enroll blocked)
> **Upstream PR:** https://github.com/4ybarik/qa-training-platform/pull/3

---

## English

### Summary

`ARCHIVED` enroll is rejected. `DRAFT` is still enrollable by any USER. Practice catalog mentions DRAFT/PUBLISHED/ARCHIVED rules — product policy for DRAFT is undefined in runtime.

### Problem

| Status | Current `CourseService.enroll` |
|--------|--------------------------------|
| `PUBLISHED` | Allowed |
| `ARCHIVED` | `ConflictError` (fixed in #4 / PR #3) |
| `DRAFT` | Allowed for USER |

TLA `CourseLifecycle` forbids only `ARCHIVED`. Catalog tasks expect status-aware CRUD/enroll behavior.

### Proposed decision (pick one)

**A (recommended):** USER may enroll only on `PUBLISHED`; ADMIN may enroll on `DRAFT` for testing.
**B:** Nobody enrolls on `DRAFT` (publish first).
**C:** Keep current behavior and document it in ARCHITECTURE + LIMITATIONS + TLA comment.

### Acceptance criteria

- [ ] Decision recorded in ARCHITECTURE / LIMITATIONS
- [ ] Runtime matches decision (service guard + API 409 if forbidden)
- [ ] Formal oracle / TLA updated
- [ ] API test covers DRAFT enroll

---

## Русский

### Кратко

На `ARCHIVED` запись запрещена; на `DRAFT` — ещё нет политики. Нужно зафиксировать правило и выровнять код + TLA + тесты.

### Варианты

**A:** USER только на `PUBLISHED`; ADMIN может на `DRAFT`.
**B:** На `DRAFT` никто не записывается.
**C:** Оставить как есть и явно задокументировать.

### Критерии приёмки

- [ ] Решение в доке
- [ ] Код + TLA + тест соответствуют решению

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P1`, `formal`, `courses` |
| Files | `backend/app/services/courses.py`, `formal/tla/services/CourseLifecycle.tla` |
