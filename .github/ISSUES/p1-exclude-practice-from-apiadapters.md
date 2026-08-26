---
title: "[P1] Exclude practice/integration APIs from ApiAdapters invariant"
labels: ["P1", "formal", "practice"]
---

## Problem

`ApiAdapters.tla` invariant `EndpointDelegatesToService` assumed all API endpoints delegate to domain services.
`/api/practice/*` and `/api/integrations/*` intentionally hold in-memory / Redis adapter state for student tests.

## Patch

- `formal/tla/adapters/PracticeTargets.tla` + `.cfg` — separate spec for excluded endpoints
- `formal/tla/adapters/ApiAdapters.tla` — comment + LIMITATIONS cross-ref
- `backend/app/formal/inventory.py` — maps `app.api.practice`, `app.api.integrations` → `PracticeTargets.tla`
- `formal/LIMITATIONS.md` — lists exclusions

## Acceptance criteria

- [ ] Inventory coverage unchanged (0 unmapped)
- [ ] ApiAdapters applies only to domain-delegating endpoints
- [ ] Practice targets remain intentionally stateful in API layer
