> **Languages:** English · Русский
> **Type:** bug (spec/runtime mismatch)
> **Priority:** P0
> **Branch (fix):** `fix/formal-spec-alignment-p0-p1`
> **Related PR:** open from branch `fix/formal-spec-alignment-p0-p1` — see [`formal/PR.md`](https://github.com/maximusmakarov/qa-training-platform/blob/fix/formal-spec-alignment-p0-p1/formal/PR.md)

---

## English

### Summary

Formal spec `CourseLifecycle.tla` forbids enrollment when a course is `ARCHIVED`. Runtime allowed `POST /api/courses/{id}/enroll` on archived courses until aligned.

### Problem

| Layer | Expected | Actual (before fix) |
|-------|----------|---------------------|
| TLA | `Enroll` guarded by `courseStatus[c] # "ARCHIVED"` | — |
| `CourseService.enroll` | Reject archived courses | No status check |
| API | HTTP **409 Conflict** | **200** on archived course |

### Steps to reproduce

1. As **ADMIN**, create a course with `"status": "ARCHIVED"`.
2. As **USER**, call `POST /api/courses/{id}/enroll`.
3. **Before fix:** enrollment succeeds. **After fix:** **409** with archived-course message.

### Proposed solution

- [x] `CourseService.enroll`: raise `ConflictError` when `course.status == CourseStatus.ARCHIVED`
- [x] Update formal oracle `EnrollmentMachine.try_enroll(..., course_status=)`
- [x] API test `test_enroll_archived_course_conflict`
- [x] Formal test `test_archived_course_forbidden`

### Acceptance criteria

- [ ] `POST /api/courses/{archived_id}/enroll` returns **409** and a clear error message
- [ ] `pytest tests/test_courses_api.py::test_enroll_archived_course_conflict` passes
- [ ] Formal oracle rejects `ARCHIVED` enrollment
- [ ] TLA spec unchanged: guard remains in `formal/tla/services/CourseLifecycle.tla`

### Affected files

- `backend/app/services/courses.py`
- `backend/app/formal/machines/course_lifecycle.py`
- `backend/tests/test_courses_api.py`
- `backend/tests/formal/test_tlc_invariants.py`

### References

- Spec: [`formal/tla/services/CourseLifecycle.tla`](https://github.com/maximusmakarov/qa-training-platform/blob/fix/formal-spec-alignment-p0-p1/formal/tla/services/CourseLifecycle.tla) — action `Enroll`
- Limitations: [`formal/LIMITATIONS.md`](https://github.com/maximusmakarov/qa-training-platform/blob/fix/formal-spec-alignment-p0-p1/formal/LIMITATIONS.md)

---

## Русский

### Кратко

Формальная спецификация `CourseLifecycle.tla` запрещает запись на курс со статусом `ARCHIVED`. Runtime до исправления это не проверял.

### Проблема

| Слой | Ожидание | Было |
|------|----------|------|
| TLA | `Enroll` только если статус ≠ `ARCHIVED` | — |
| `CourseService.enroll` | Отказ для архивного курса | Проверки статуса не было |
| API | HTTP **409 Conflict** | **200** |

### Шаги воспроизведения

1. Под **ADMIN** создать курс со `"status": "ARCHIVED"`.
2. Под **USER** вызвать `POST /api/courses/{id}/enroll`.
3. **До фикса:** запись проходит. **После фикса:** **409** с сообщением об архивном курсе.

### Решение

- [x] `CourseService.enroll`: `ConflictError` при `CourseStatus.ARCHIVED`
- [x] Оракул `EnrollmentMachine.try_enroll(..., course_status=)`
- [x] Тест API `test_enroll_archived_course_conflict`
- [x] Формальный тест `test_archived_course_forbidden`

### Критерии приёмки

- [ ] `POST /api/courses/{archived_id}/enroll` → **409** с понятным текстом ошибки
- [ ] `pytest tests/test_courses_api.py::test_enroll_archived_course_conflict` проходит
- [ ] Формальный оракул отклоняет enroll на `ARCHIVED`
- [ ] TLA-спека без изменений guard'а

### Затронутые файлы

- `backend/app/services/courses.py`
- `backend/app/formal/machines/course_lifecycle.py`
- `backend/tests/test_courses_api.py`
- `backend/tests/formal/test_tlc_invariants.py`

### Ссылки

- Спека: `formal/tla/services/CourseLifecycle.tla` — action `Enroll`
- Ограничения: `formal/LIMITATIONS.md`

---

### Metadata (for maintainers)

| Field | Value |
|-------|-------|
| Labels | `P0`, `formal`, `courses` |
| Milestone | Formal spec alignment |
| Closes via PR | yes — include `Closes #NN` in PR description |
