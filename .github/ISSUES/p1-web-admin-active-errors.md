---
title: "[P1][web] Surface admin set_active DomainError to user"
labels: ["P1", "formal", "web"]
---

> **Languages:** English · Русский
> **Type:** bug (UX / adapter layer)
> **Priority:** P1
> **Related:** same anti-pattern as #5 (web enroll errors)
> **Upstream PR:** https://github.com/4ybarik/qa-training-platform/pull/3

---

## English

### Summary

`POST /web/admin/users/{id}/active` catches `DomainError` and silently redirects, so attempts to deactivate yourself (and other domain failures) look like success.

### Problem

| Entry | On self-deactivate | User feedback |
|-------|--------------------|---------------|
| API `set_active` | Permission / domain error | Clear HTTP error |
| Web `admin_set_active` | `except DomainError: pass` | Silent 303 to `/admin` |

```python
# backend/app/web/router.py
try:
    AdminService(db).set_active(user, user_id, is_active == "true")
except DomainError:
    pass  # hidden
return RedirectResponse("/admin", status_code=303)
```

### Proposed solution

- [ ] Redirect with `?error=` / flash message (reuse `_ctx` localization like enroll)
- [ ] Show error on `admin.html` with `data-testid="admin-error"`
- [ ] Web test: self-deactivate shows message

### Acceptance criteria

- [ ] Self-deactivate via web shows visible error
- [ ] Successful activate/deactivate still redirects cleanly
- [ ] Business rule stays only in `AdminService`

---

## Русский

### Кратко

Web-админка глотает `DomainError` при смене `is_active` — в т.ч. «нельзя деактивировать себя» выглядит как успех.

### Решение

- [ ] Редирект с `?error=` / flash, показ на `admin.html`
- [ ] Тест: self-deactivate показывает ошибку

### Критерии приёмки

- [ ] Ошибка видна пользователю
- [ ] Успешный сценарий без ложного сообщения
- [ ] Правило только в `AdminService`

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P1`, `formal`, `web` |
| Files | `backend/app/web/router.py`, `backend/app/templates/admin.html` |
