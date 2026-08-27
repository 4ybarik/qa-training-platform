---
title: "[P2][db] Enforce enrollment.progress 0..100 in the database"
labels: ["P2", "formal", "courses"]
---

> **Languages:** English · Русский  
> **Type:** data integrity  
> **Priority:** P2  
> **Related:** TLA invariant `ProgressIn0to100`

---

## English

### Summary

Formal model requires `progress ∈ 0..100`. ORM has a comment only; no `CheckConstraint`. Today only `ExamService` writes progress via `max(...)`, but raw SQL / future code can violate the invariant.

### Proposed solution

- [ ] Add SQLAlchemy `CheckConstraint("progress >= 0 AND progress <= 100")` on `Enrollment`
- [ ] Document DB recreate / manual ALTER for existing Postgres (no Alembic yet)
- [ ] Keep formal tests asserting bounds

### Acceptance criteria

- [ ] Constraint in `domain/models.py`
- [ ] Out-of-range write fails at DB (test with SQLite/Postgres as available)
- [ ] LIMITATIONS notes migration path if needed

---

## Русский

### Кратко

Инвариант progress 0..100 есть в TLA, в БД — нет. Нужен CheckConstraint.

### Критерии приёмки

- [ ] Constraint в модели
- [ ] Тест / проверка отклонения out-of-range
- [ ] Путь обновления схемы задокументирован

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P2`, `formal`, `courses` |
| Files | `backend/app/domain/models.py`, `formal/tla/services/CourseLifecycle.tla` |
