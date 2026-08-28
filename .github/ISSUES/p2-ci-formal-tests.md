---
title: "[P2][ci] Add formal tests to CI (make formal / pytest tests/formal)"
labels: ["P2", "formal", "documentation"]
---

> **Languages:** English · Русский
> **Type:** process / CI
> **Priority:** P2
> **Upstream PR:** https://github.com/4ybarik/qa-training-platform/pull/3

---

## English

### Summary

Formal inventory + statemachine oracles live under `backend/tests/formal` and `make formal`, but Jenkins / CI does not run them. Spec/runtime can drift after merge.

### Proposed solution

- [ ] Add CI stage: `cd backend && python -m pytest tests/formal -q`
- [ ] Optionally `make formal` (inventory + tests)
- [ ] Document in README / CONTRIBUTING
- [ ] TLC (`make tla`) remains optional (needs Java/Docker) — keep pytest surrogate as required gate

### Acceptance criteria

- [ ] Formal tests run on every PR/main build
- [ ] Failure blocks merge (or clearly reported)
- [ ] `python-statemachine` present in CI deps (`requirements.txt` already lists it)

---

## Русский

### Кратко

Formal-тесты есть локально, в CI нет — спеки разъедутся с кодом.

### Решение

- [ ] Стадия `pytest tests/formal` в Jenkins / GitHub Actions
- [ ] TLC опционально; surrogate обязателен

### Критерии приёмки

- [ ] Formal гоняется на каждый PR
- [ ] Зависимости установлены в CI-образе

---

### Metadata

| Field | Value |
|-------|-------|
| Labels | `P2`, `formal`, `documentation` |
| Files | `Jenkinsfile`, `Makefile`, `.github/workflows/*` |
