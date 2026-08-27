# Formal spec alignment — issues (RU/EN)

Шаблоны issues на **английском и русском** лежат в [`.github/ISSUES/`](../.github/ISSUES/).

## Целевой репозиторий

**Project owner:** [`4ybarik/qa-training-platform`](https://github.com/4ybarik/qa-training-platform)  
**Fork (head branch):** `maximusmakarov:fix/formal-spec-alignment-p0-p1`

## Созданные issues (upstream)

| # | EN / RU | URL |
|---|---------|-----|
| **#4** | Block ARCHIVED enroll · Запрет ARCHIVED | https://github.com/4ybarik/qa-training-platform/issues/4 |
| **#5** | Web enroll errors · Ошибки web-enroll | https://github.com/4ybarik/qa-training-platform/issues/5 |
| **#6** | Delete cascade docs · Каскад delete | https://github.com/4ybarik/qa-training-platform/issues/6 |
| **#7** | Practice ApiAdapters · Practice в ApiAdapters | https://github.com/4ybarik/qa-training-platform/issues/7 |

## PR

**https://github.com/4ybarik/qa-training-platform/pull/3**

```markdown
Closes #4
Closes #5
Closes #6
Closes #7
```

Описание: [`formal/PR.md`](PR.md)

## Создать issues повторно (если нужно)

```powershell
$env:GITHUB_TOKEN = "ghp_..."
python scripts/create_formal_issues.py
```

Или: `pwsh scripts/create-formal-issues.ps1`
