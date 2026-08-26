# GitHub Issues — formal spec alignment (P0/P1)

Bilingual issue bodies (English + Русский) ready for GitHub.

## Create issues on GitHub

### Prerequisites

1. Install [GitHub CLI](https://cli.github.com/): `winget install GitHub.cli`
2. Authenticate: `gh auth login`
3. *(Optional)* Create labels:

```powershell
cd d:\qa-training-platform
Get-Content .github/labels-formal.json | ConvertFrom-Json | ForEach-Object {
  gh label create $_.name --color $_.color --description $_.description --repo maximusmakarov/qa-training-platform 2>$null
}
```

### One command (all 4 issues)

```powershell
pwsh scripts/create-formal-issues.ps1
```

Dry run:

```powershell
pwsh scripts/create-formal-issues.ps1 -DryRun
```

### Manual (single issue)

```powershell
gh issue create --repo maximusmakarov/qa-training-platform `
  --title "[P0][formal] Block enroll on ARCHIVED courses · Запрет записи на ARCHIVED-курс" `
  --label "P0,formal,courses" `
  --body-file .github/ISSUES/p0-block-enroll-archived.md
```

> **Note:** `--body-file` must contain **body only**. Strip YAML front matter manually, or use the PowerShell script which strips `---` blocks automatically.

## Issue index

| File | Priority | Labels |
|------|----------|--------|
| [`p0-block-enroll-archived.md`](p0-block-enroll-archived.md) | P0 | `P0`, `formal`, `courses` |
| [`p0-web-enroll-errors.md`](p0-web-enroll-errors.md) | P0 | `P0`, `formal`, `web` |
| [`p1-document-delete-cascade.md`](p1-document-delete-cascade.md) | P1 | `P1`, `formal`, `documentation`, `courses` |
| [`p1-exclude-practice-from-apiadapters.md`](p1-exclude-practice-from-apiadapters.md) | P1 | `P1`, `formal`, `practice`, `documentation` |

## GitHub formatting conventions used

- Blockquote header: languages, type, priority, branch, PR link
- Horizontal rule `---` between EN and RU sections
- Tables for expected vs actual behavior
- Task lists `- [ ]` / `- [x]` for acceptance criteria
- Code fences for snippets and commands
- **Metadata** table for maintainers (labels, milestone, `Closes #NN`)
- Bilingual **titles** via script: `English · Русский`

## Link to PR

After creating issues, add to PR description (`formal/PR.md`):

```markdown
Closes #NN  <!-- P0 archived enroll -->
Closes #NN  <!-- P0 web enroll errors -->
Closes #NN  <!-- P1 delete cascade docs -->
Closes #NN  <!-- P1 ApiAdapters scope -->
```

Index (RU): [`formal/ISSUES.md`](../formal/ISSUES.md)
