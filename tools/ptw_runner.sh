#!/bin/sh
# Обёртка-раннер для pytest-watcher (см. make watch-api / watch-ui).
#
# pytest-watcher вызывает runner БЕЗ аргументов и не умеет передавать путь
# к тестам, поэтому пути подставляет эта обёртка через переменную окружения
# STUDENT_TEST_PATHS. Так watch-режим гоняет только учебные тесты, а не весь
# репозиторий.
set -eu

# Интерпретатор берётся из окружения (активированный venv ученика) либо
# переопределяется явно: STUDENT_PYTHON=/path/to/venv/bin/python make watch-api
: "${STUDENT_PYTHON:=python}"
: "${STUDENT_TEST_PATHS:=student_tests/api student_tests/contract}"
# shellcheck disable=SC2086
exec "$STUDENT_PYTHON" -m pytest $STUDENT_TEST_PATHS
