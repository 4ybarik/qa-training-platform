---
title: "[P1] Document course delete cascade behavior"
labels: ["P1", "formal", "docs"]
---

## Problem

`ARCHITECTURE.md` examples implied guarded delete when enrollments exist.
Runtime `CourseService.delete` cascades via ORM (`cascade="all, delete-orphan"` on Course).

## Decision

**Accept cascade** for training platform — admin can remove course + dependencies in one step.

## Patch

- `ARCHITECTURE.md` — new §3.1 «Удаление курса и каскадные связи»
- `formal/LIMITATIONS.md` — documents accepted behavior
- Future optional: `DeleteCourseGuarded` in TLA if product requires forbid-delete

## Acceptance criteria

- [ ] Docs explicitly state cascade delete is intentional
- [ ] No silent mismatch between docs and `CourseService.delete`
