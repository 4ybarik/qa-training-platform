# Formal model verification limitations

## Course delete

`CourseService.delete` cascades enrollments and exams via ORM. Documented in
`ARCHITECTURE.md` §3.1. TLA `CourseLifecycle.tla` models enroll uniqueness, not
delete guards.

## Enroll on archived course

Runtime now rejects `ARCHIVED` courses in `CourseService.enroll` — aligned with
TLA `Enroll` action (`courseStatus[c] # "ARCHIVED"`).

## ApiAdapters scope

`ApiAdapters.tla` applies to domain API/web endpoints that delegate to
services. **Excluded** (intentional direct state):

- `/api/practice/*` — in-memory practice targets
- `/api/integrations/*` — Redis cache/queue adapters

## TLC

Requires Java+TLC or Docker (`tlaplus/tlc`). When unavailable, run:

```bash
cd backend && python -m pytest tests/formal/test_tlc_invariants.py
```

as bounded invariant surrogate matching `formal/tla/**/*.tla` specs.
