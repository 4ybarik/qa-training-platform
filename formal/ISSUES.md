# Formal spec alignment — issues (RU/EN)

Шаблоны issues на **английском и русском** лежат в [`.github/ISSUES/`](../.github/ISSUES/).

## Созданные issues (GitHub)

| # | EN / RU | URL |
|---|---------|-----|
| **#1** | Block ARCHIVED enroll · Запрет ARCHIVED | https://github.com/maximusmakarov/qa-training-platform/issues/1 |
| **#2** | Web enroll errors · Ошибки web-enroll | https://github.com/maximusmakarov/qa-training-platform/issues/2 |
| **#3** | Delete cascade docs · Каскад delete | https://github.com/maximusmakarov/qa-training-platform/issues/3 |
| **#4** | Practice ApiAdapters · Practice в ApiAdapters | https://github.com/maximusmakarov/qa-training-platform/issues/4 |

> Issues были отключены в репозитории — включены через API (`has_issues: true`).

## Создать issues повторно (если нужно)

**Способ A — Python + токен** (без `gh`):

```powershell
$env:GITHUB_TOKEN = "ghp_..."   # Settings → Developer settings → Fine-grained tokens → Issues: Read and write
python scripts/create_formal_issues.py --ensure-labels
```

**Способ B — GitHub CLI:**

```powershell
pwsh scripts/create-formal-issues.ps1
```

**Способ C — вручную:** скопировать тело из [`.github/ISSUES/bodies/`](.github/ISSUES/bodies/) в GitHub → New issue.

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
