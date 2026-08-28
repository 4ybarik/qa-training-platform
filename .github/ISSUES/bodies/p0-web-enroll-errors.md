> **Languages:** English · Русский
> **Type:** bug (UX / adapter layer)
> **Priority:** P0
> **Branch (fix):** `fix/formal-spec-alignment-p0-p1`
> **Related PR:** see [`formal/PR.md`](https://github.com/maximusmakarov/qa-training-platform/blob/fix/formal-spec-alignment-p0-p1/formal/PR.md)

---

## English

### Summary

The web enroll endpoint swallowed all `DomainError` exceptions and always redirected with **303**, so duplicate enrollment and other business-rule failures looked like success.

### Problem

| Entry point | On `ConflictError` (duplicate enroll) | User feedback |
|-------------|--------------------------------------|---------------|
| `POST /api/courses/{id}/enroll` | **409** JSON `detail` | Clear API error |
| `POST /web/courses/{id}/enroll` | Silent redirect **before fix** | No error shown |

```python
# backend/app/web/router.py (before)
try:
    CourseService(db).enroll(user.id, course_id)
except DomainError:
    pass  # error hidden
return RedirectResponse(f"/courses/{course_id}", status_code=303)
```

### Steps to reproduce

1. Register/login as a user.
2. Enroll on course `1` via API or web — succeeds.
3. Enroll again via **web** form on `/courses/1`.
4. **Before fix:** redirect with no message, still shows enroll button. **After fix:** error banner on course page.

### Proposed solution

- [x] On `DomainError`, redirect to `/courses/{id}?enroll_error={quoted_message}`
- [x] `course_detail.html`: render `<p class="error" data-testid="enroll-error">`
- [x] `_ctx`: localize `enroll_error` like other web errors
- [x] Test `tests/test_courses_web.py::test_web_enroll_duplicate_shows_error`

### Acceptance criteria

- [ ] Duplicate web enroll shows visible error text on course detail page
- [ ] Element `data-testid="enroll-error"` present when error occurs
- [ ] Successful enroll still redirects without error param
- [ ] API and web use the same `CourseService.enroll` — no duplicated business rules

### Affected files

- `backend/app/web/router.py`
- `backend/app/templates/course_detail.html`
- `backend/tests/test_courses_web.py`

### References

- Adapter invariant: `formal/tla/adapters/ApiAdapters.tla` — web must not hide service errors
- i18n: `backend/app/web/i18n.py` via `_ctx` / `localize_error`

---

## Русский

### Кратко

Web-эндпоинт записи на курс проглатывал `DomainError` и всегда делал редирект **303**, поэтому повторная запись и другие ошибки домена выглядели как успех.

### Проблема

| Точка входа | При `ConflictError` (повторная запись) | Обратная связь |
|-------------|----------------------------------------|----------------|
| `POST /api/courses/{id}/enroll` | **409** JSON | Явная ошибка |
| `POST /web/courses/{id}/enroll` | **До фикса:** тихий редирект | Ошибки не видно |

### Шаги воспроизведения

1. Зарегистрироваться / войти.
2. Записаться на курс `1`.
3. Повторно отправить форму enroll на `/courses/1`.
4. **До фикса:** редирект без сообщения. **После фикса:** баннер ошибки на странице курса.

### Решение

- [x] При `DomainError` — редирект с `?enroll_error=...`
- [x] Шаблон: `data-testid="enroll-error"`
- [x] Локализация через `_ctx`
- [x] Тест `test_web_enroll_duplicate_shows_error`

### Критерии приёмки

- [ ] Повторная web-запись показывает текст ошибки
- [ ] Есть `data-testid="enroll-error"` при ошибке
- [ ] Успешная запись — редирект без параметра ошибки
- [ ] Бизнес-логика только в `CourseService`, не дублируется в web

### Затронутые файлы

- `backend/app/web/router.py`
- `backend/app/templates/course_detail.html`
- `backend/tests/test_courses_web.py`

### Ссылки

- `formal/tla/adapters/ApiAdapters.tla`
- `backend/app/web/i18n.py`

---

### Metadata (for maintainers)

| Field | Value |
|-------|-------|
| Labels | `P0`, `formal`, `web` |
| Milestone | Formal spec alignment |
| Closes via PR | yes — include `Closes #NN` in PR description |
