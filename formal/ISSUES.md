# Formal spec alignment — issues (RU/EN)

Шаблоны issues на **английском и русском** лежат в [`.github/ISSUES/`](../.github/ISSUES/).

## Создать issues на GitHub

```powershell
# 1. Установить gh: winget install GitHub.cli
# 2. Войти: gh auth login
# 3. Создать все 4 issue:
pwsh scripts/create-formal-issues.ps1
```

Подробности: [`.github/ISSUES/README.md`](../.github/ISSUES/README.md)

## Список

| Приоритет | EN / RU | Файл |
|-----------|---------|------|
| P0 | Block enroll on ARCHIVED · Запрет записи на ARCHIVED | `p0-block-enroll-archived.md` |
| P0 | Surface web enroll errors · Показ ошибок web-enroll | `p0-web-enroll-errors.md` |
| P1 | Document delete cascade · Каскадное удаление курса | `p1-document-delete-cascade.md` |
| P1 | Exclude practice from ApiAdapters · Исключить practice | `p1-exclude-practice-from-apiadapters.md` |

## PR

Branch: `fix/formal-spec-alignment-p0-p1`  
Описание: [`formal/PR.md`](PR.md)

После создания issues добавьте в PR: `Closes #NN` для каждого номера.
