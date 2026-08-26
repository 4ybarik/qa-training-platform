# Formal spec alignment — P0/P1 issues

Issue templates live in [`.github/ISSUES/`](../.github/ISSUES/). Create on GitHub manually or with `gh issue create -F .github/ISSUES/<file>.md`.

PR description: [`formal/PR.md`](PR.md)

**Branch pushed:** `fix/formal-spec-alignment-p0-p1`  
**Open PR:** https://github.com/maximusmakarov/qa-training-platform/pull/new/fix/formal-spec-alignment-p0-p1

## P0 — must fix

| Template | Title |
|----------|-------|
| `p0-block-enroll-archived.md` | Block enroll on ARCHIVED courses |
| `p0-web-enroll-errors.md` | Surface web enroll DomainError to user |

## P1 — document / narrow spec

| Template | Title |
|----------|-------|
| `p1-document-delete-cascade.md` | Document course delete cascade |
| `p1-exclude-practice-from-apiadapters.md` | Exclude practice/integration from ApiAdapters |

## Verification

```bash
cd backend && python -m pytest tests/test_courses_api.py tests/test_courses_web.py tests/formal -q
make formal
```
