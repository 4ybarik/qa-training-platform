# Formal model verification limitations

## Course delete

`CourseService.delete` cascades enrollments and exams via ORM. Documented in
`ARCHITECTURE.md` §3.1. TLA `CourseLifecycle.tla` models enroll uniqueness, not
delete guards.

## Enroll on archived course

Runtime rejects `ARCHIVED` courses in `CourseService.enroll` — aligned with
TLA `Enroll` action (`courseStatus[c] # "ARCHIVED"`).

## ApiAdapters scope

`ApiAdapters.tla` applies to domain API/web endpoints that delegate to
services. **Excluded** (intentional direct state):

- `/api/practice/*` — in-memory practice targets → `PracticeTargets.tla`
- `/api/integrations/*` — Redis cache/queue adapters → `PracticeTargets.tla`

Inventory quality gates (`tests/formal/test_inventory.py`):

- `unmapped == 0`
- `misc == 0` (no dump into `modules/Misc.tla`)
- every referenced `.tla` exists under `formal/tla/`
- `api.*` / `web.*` map to ApiAdapters or PracticeTargets (plus deps/errors/quality)

## TLC

Requires Java+TLC or Docker (`tlaplus/tlc`). When unavailable, run:

```bash
cd backend && python -m pytest tests/formal/test_tlc_invariants.py
```

as bounded invariant surrogate matching `formal/tla/**/*.tla` specs.
