> **Languages:** English · Русский  
> **Type:** documentation (accepted spec/runtime decision)  
> **Priority:** P1  
> **Branch (fix):** `fix/formal-spec-alignment-p0-p1`  
> **Related PR:** see [`formal/PR.md`](https://github.com/maximusmakarov/qa-training-platform/blob/fix/formal-spec-alignment-p0-p1/formal/PR.md)

---

## English

### Summary

Architecture examples suggest guarding course deletion when enrollments exist. Runtime intentionally **cascades** deletes via ORM. Document the decision so developers and formal specs stay aligned.

### Problem

| Source | Statement | Runtime behavior |
|--------|-----------|------------------|
| `ARCHITECTURE.md` (review example narrative) | Implies guarded delete | — |
| `CourseService.delete` | — | Deletes course; ORM cascades `enrollments`, `exams` |
| `domain/models.py` | — | `cascade="all, delete-orphan"` on `Course` relationships |
| `CourseLifecycle.tla` | Models enroll uniqueness | Does **not** model delete guards |

This is **not a runtime bug** — it is an **undocumented product decision**.

### Decision (accepted for training platform)

**Option A — Cascade delete (chosen):** ADMIN can remove a course and all dependent rows in one operation. Suitable for a learning sandbox.

**Option B — Guarded delete (future):** Return `ConflictError` if enrollments exist. Requires TLA action `DeleteCourseGuarded` and service check.

### Proposed solution

- [x] Add **§3.1** to `ARCHITECTURE.md`: cascade behavior, when to switch to guarded delete
- [x] Record in `formal/LIMITATIONS.md`
- [ ] *(Optional future)* Implement Option B if product requires it

### Acceptance criteria

- [ ] `ARCHITECTURE.md` explicitly describes cascade delete as intentional
- [ ] `formal/LIMITATIONS.md` cross-references §3.1
- [ ] No reader assumes guarded delete without reading docs
- [ ] Formal tests still pass (`test_architecture_alignment.py`)

### Affected files

- `ARCHITECTURE.md`
- `formal/LIMITATIONS.md`
- `backend/tests/formal/test_architecture_alignment.py`

### References

- ORM: `backend/app/domain/models.py` — `Course.enrollments`, `Course.exams`
- Service: `backend/app/services/courses.py` — `delete()`

---

## Русский

### Кратко

В архитектурных примерах подразумевается защита от удаления курса с записями. Runtime **намеренно** каскадно удаляет связи через ORM. Нужно задокументировать решение.

### Проблема

| Источник | Формулировка | Поведение |
|----------|--------------|-----------|
| `ARCHITECTURE.md` | Намёк на guarded delete | — |
| `CourseService.delete` | — | Каскад enrollments + exams |
| `CourseLifecycle.tla` | Уникальность enroll | Delete guards нет |

Это **решение продукта**, не баг.

### Решение (принято для учебного полигона)

**Вариант A — каскад (выбран):** ADMIN удаляет курс и зависимости одной операцией.

**Вариант B — запрет (на будущее):** `ConflictError` при наличии enrollments + TLA `DeleteCourseGuarded`.

### Что сделано

- [x] `ARCHITECTURE.md` §3.1
- [x] `formal/LIMITATIONS.md`
- [ ] *(Опционально)* Вариант B по запросу продукта

### Критерии приёмки

- [ ] В `ARCHITECTURE.md` явно описан каскадный delete
- [ ] `LIMITATIONS.md` ссылается на §3.1
- [ ] Формальные тесты проходят

### Затронутые файлы

- `ARCHITECTURE.md`
- `formal/LIMITATIONS.md`

### Ссылки

- `backend/app/domain/models.py`
- `backend/app/services/courses.py`

---

### Metadata (for maintainers)

| Field | Value |
|-------|-------|
| Labels | `P1`, `formal`, `documentation`, `courses` |
| Milestone | Formal spec alignment |
| Closes via PR | yes — include `Closes #NN` in PR description |
