---
title: "[P2][exams] Decide whether exam submit requires enrollment"
labels: ["P2", "formal", "courses"]
---

> **Languages:** English · Русский
> **Type:** product decision + optional guard
> **Priority:** P2
> **Upstream PR:** https://github.com/4ybarik/qa-training-platform/pull/3

---

## English

### Summary

`ExamService.submit` does not require an enrollment. Attempt + notification are created; `enrollment.progress` updates only if enrollment exists.

### Current behavior

| Condition | Result |
|-----------|--------|
| User enrolled | Progress = max(old, 100 if passed else score) |
| User not enrolled | Attempt saved; progress unchanged |

Matches current TLA `ExamAttempt` (`hasEnrollment` optional). May surprise learners who expect “enroll first”.

### Proposed decision (pick one)

**A:** Require enrollment → `ConflictError` / 409 if missing.
**B:** Keep optional enrollment; document in API docs + LIMITATIONS + practice criteria.

### Acceptance criteria

- [ ] Decision documented
- [ ] If A: service guard + API/web tests
- [ ] If B: LIMITATIONS + OpenAPI/description note
- [ ] TLA stays aligned

---

## Русский

### Кратко

Сдать экзамен можно без записи на курс. Нужно решить: запретить или явно разрешить и задокументировать.

### Варианты

**A:** Требовать enrollment.
**B:** Оставить как есть + документ.

### Критерии приёмки

- [ ] Решение зафиксировано
- [ ] Код/дока/TLA согласованы

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P2`, `formal`, `courses` |
| Files | `backend/app/services/exams.py`, `formal/tla/services/ExamAttempt.tla` |
