# Create formal P0/P1 GitHub issues (bilingual bodies).
# Requires: GitHub CLI (`gh auth login`) OR env GITHUB_TOKEN with repo scope.
#
# Usage:
#   pwsh scripts/create-formal-issues.ps1
#   pwsh scripts/create-formal-issues.ps1 -DryRun

param(
    [string]$Repo = "maximusmakarov/qa-training-platform",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$IssuesDir = Join-Path $Root ".github" "ISSUES"

$issues = @(
    @{
        File   = "p0-block-enroll-archived.md"
        Title  = "[P0][formal] Block enroll on ARCHIVED courses · Запрет записи на ARCHIVED-курс"
        Labels = @("P0", "formal", "courses")
    },
    @{
        File   = "p0-web-enroll-errors.md"
        Title  = "[P0][formal] Surface web enroll errors · Показ ошибок web-enroll пользователю"
        Labels = @("P0", "formal", "web")
    },
    @{
        File   = "p1-document-delete-cascade.md"
        Title  = "[P1][formal] Document course delete cascade · Документировать каскадное удаление курса"
        Labels = @("P1", "formal", "documentation", "courses")
    },
    @{
        File   = "p1-exclude-practice-from-apiadapters.md"
        Title  = "[P1][formal] Exclude practice/integration from ApiAdapters · Исключить practice из ApiAdapters"
        Labels = @("P1", "formal", "practice", "documentation")
    }
)

function Get-BodyFromMarkdown {
    param([string]$Path)
    $raw = Get-Content -Raw -Encoding UTF8 $Path
    # Strip YAML front matter if present
    if ($raw -match '(?s)^---\r?\n.*?\r?\n---\r?\n(.*)$') {
        return $Matches[1].Trim()
    }
    return $raw.Trim()
}

foreach ($item in $issues) {
    $path = Join-Path $IssuesDir $item.File
    if (-not (Test-Path $path)) {
        Write-Error "Missing issue body: $path"
    }
    $body = Get-BodyFromMarkdown $path
    Write-Host "`n=== $($item.Title) ===" -ForegroundColor Cyan
    if ($DryRun) {
        Write-Host "[dry-run] labels: $($item.Labels -join ', ')"
        Write-Host "[dry-run] body length: $($body.Length) chars"
        continue
    }
    $labelArgs = $item.Labels | ForEach-Object { "-l", $_ }
    & gh issue create --repo $Repo --title $item.Title --body $body @labelArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Error "gh issue create failed for $($item.File). Run: gh auth login"
    }
}

Write-Host "`nDone. List issues: gh issue list --repo $Repo --label formal" -ForegroundColor Green
