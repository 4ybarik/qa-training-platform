---
title: "[P2][rbac] Give MANAGER real permissions or drop from promises"
labels: ["P2", "formal", "documentation"]
---

> **Languages:** English · Русский  
> **Type:** product / RBAC consistency  
> **Priority:** P2

---

## English

### Summary

`Role.MANAGER` exists in enum, seed (`manager@test.com`), and practice catalog (RBAC matrix), but almost no endpoint uses `require_roles(Role.MANAGER)`. MANAGER ≈ USER in practice.

### Problem

Learners writing RBAC tests see MANAGER in docs/demo accounts but get the same 403/200 matrix as USER for most admin routes.

### Proposed decision (pick one)

**A:** Grant MANAGER meaningful rights (e.g. read audits, manage courses without delete, send notifications).  
**B:** Keep MANAGER as alias of USER; update catalog/seed text so it does not promise a distinct matrix.  
**C:** Remove MANAGER from enum/seed (breaking for existing demos — unlikely).

### Acceptance criteria

- [ ] Decision in ARCHITECTURE §RBAC
- [ ] Either real `require_roles(ADMIN, MANAGER)` usages **or** catalog/demo wording updated
- [ ] Parametrized RBAC practice task matches reality

---

## Русский

### Кратко

Роль `MANAGER` обещана в сиде и каталоге, но почти нигде не отличается от USER.

### Варианты

**A:** Реальные права MANAGER.  
**B:** Оставить ≈ USER и поправить обещания в каталоге.  
**C:** Убрать роль (ломка демо — маловероятно).

### Критерии приёмки

- [ ] ARCHITECTURE обновлён
- [ ] Код или каталог согласованы с решением

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P2`, `formal`, `documentation` |
| Files | `backend/app/api/deps.py`, `backend/app/seed.py`, `AUTOMATION_PRACTICE_CATALOG.md` |
