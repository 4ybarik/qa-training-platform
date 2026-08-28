---
title: "[P1][formal] Exclude practice/integration APIs from ApiAdapters invariant"
labels: ["P1", "formal", "practice", "documentation"]
---

> **Languages:** English · Русский
> **Type:** documentation + formal spec scope
> **Priority:** P1
> **Branch (fix):** `fix/formal-spec-alignment-p0-p1`
> **Related PR:** see [`formal/PR.md`](https://github.com/maximusmakarov/qa-training-platform/blob/fix/formal-spec-alignment-p0-p1/formal/PR.md)

---

## English

### Summary

Formal spec `ApiAdapters.tla` states that API endpoints must not mutate domain state directly — they delegate to services. Practice and integration endpoints **intentionally** hold in-memory or Redis-local state for student automation tests.

### Problem

| Module | Role | Fits `ApiAdapters`? |
|--------|------|---------------------|
| `app/api/courses.py` | Delegates to `CourseService` | Yes |
| `app/api/practice.py` | In-memory jobs, resources, files | **No** — test targets |
| `app/api/integrations.py` | Redis cache / queue adapters | **No** — adapter layer |

Applying `EndpointDelegatesToService` to practice would mis-model the system and block legitimate test surface design.

### Proposed solution

- [x] New spec: `formal/tla/adapters/PracticeTargets.tla` + `.cfg`
- [x] Comment + cross-ref in `ApiAdapters.tla`
- [x] `backend/app/formal/inventory.py` maps `app.api.practice`, `app.api.integrations` → `PracticeTargets.tla`
- [x] Document exclusions in `formal/LIMITATIONS.md`

### Acceptance criteria

- [ ] `ApiAdapters.tla` documents excluded path prefixes
- [ ] Inventory coverage remains **0 unmapped** (`python -m app.formal.inventory`)
- [ ] Practice endpoints remain stateful by design — no forced move to services
- [ ] `make formal` / `pytest tests/formal` pass

### Excluded endpoints (non-exhaustive)

| Prefix | State owner |
|--------|-------------|
| `/api/practice/*` | Process memory (`practice.py`) |
| `/api/integrations/*` | Redis |

### Affected files

- `formal/tla/adapters/PracticeTargets.tla`
- `formal/tla/adapters/PracticeTargets.cfg`
- `formal/tla/adapters/ApiAdapters.tla`
- `backend/app/formal/inventory.py`
- `formal/LIMITATIONS.md`

### References

- Practice jobs spec: `formal/tla/practice/Job.tla`
- Practice resources: `formal/tla/practice/Resource.tla`
- Student catalog: `AUTOMATION_PRACTICE_CATALOG.md`

---

## Русский

### Кратко

Спека `ApiAdapters.tla` требует, чтобы API не менял домен напрямую. Эндпоинты **practice** и **integrations** намеренно держат локальное состояние для ученических автотестов.

### Проблема

| Модуль | Роль | Подходит под ApiAdapters? |
|--------|------|---------------------------|
| `app/api/courses.py` | Делегирует в сервис | Да |
| `app/api/practice.py` | In-memory мишени | **Нет** |
| `app/api/integrations.py` | Redis | **Нет** |

### Решение

- [x] Спека `PracticeTargets.tla`
- [x] Пометка в `ApiAdapters.tla`
- [x] Inventory → `PracticeTargets.tla` для practice/integration
- [x] `formal/LIMITATIONS.md`

### Критерии приёмки

- [ ] Исключения задокументированы в спеках и LIMITATIONS
- [ ] Inventory: 0 unmapped
- [ ] Practice остаётся stateful в API-слое
- [ ] `pytest tests/formal` проходит

### Исключённые префиксы

| Префикс | Где состояние |
|---------|---------------|
| `/api/practice/*` | Память процесса |
| `/api/integrations/*` | Redis |

### Затронутые файлы

- `formal/tla/adapters/PracticeTargets.tla`
- `formal/tla/adapters/ApiAdapters.tla`
- `backend/app/formal/inventory.py`
- `formal/LIMITATIONS.md`

---

### Metadata (for maintainers)

| Field | Value |
|-------|-------|
| Labels | `P1`, `formal`, `practice`, `documentation` |
| Milestone | Formal spec alignment |
| Closes via PR | yes — include `Closes #NN` in PR description |
