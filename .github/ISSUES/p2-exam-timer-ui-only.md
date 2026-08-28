---
title: "[P2][exams] Document that exam timer is client-only"
labels: ["P2", "formal", "documentation"]
---

> **Languages:** English · Русский
> **Type:** documentation / accepted limitation
> **Priority:** P2

---

## English

### Summary

`duration_minutes` drives a browser countdown (`exam.html` `data-minutes`). `ExamService.submit` does **not** reject late submissions. Students/automation can submit after the timer.

### Proposed solution

- [ ] Document in `formal/LIMITATIONS.md` and ARCHITECTURE (exam section)
- [ ] Note in practice catalog criteria if tasks mention timing
- [ ] Optional future: server-side deadline (store attempt start, reject after duration) — out of scope unless product asks

### Acceptance criteria

- [ ] LIMITATIONS states timer is UI-only
- [ ] No false claim that API enforces duration

---

## Русский

### Кратко

Таймер экзамена только в UI; сервер late submit не режет. Нужно явно задокументировать.

### Критерии приёмки

- [ ] LIMITATIONS / дока обновлены
- [ ] Нет обещания server-side deadline без реализации

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P2`, `formal`, `documentation` |
| Files | `formal/LIMITATIONS.md`, `backend/app/templates/exam.html`, `backend/app/services/exams.py` |
