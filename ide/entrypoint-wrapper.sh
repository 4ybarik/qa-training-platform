#!/bin/sh
# Обёртка запуска встроенной IDE (см. ide/Dockerfile и docker-compose.override.yml).
#
# Готовит окружение ДО старта code-server:
# 1) симлинк .venv-student в workspace — на этот путь рассчитаны
#    .vscode/settings.json (интерпретатор) и make watch-api/watch-ui;
# 2) safe.directory для git — репозиторий смонтирован с UID хоста, и без этой
#    настройки git отказывается работать ("dubious ownership").
set -eu

WORKSPACE="${DEFAULT_WORKSPACE_DIR:-/home/coder/workspace}"
VENV_LINK="$WORKSPACE/.venv-student"

if [ ! -e "$VENV_LINK" ]; then
    ln -sfn /home/coder/.venv-student "$VENV_LINK"
fi

git config --global --add safe.directory "$WORKSPACE" 2>/dev/null || true

# Оригинальный entrypoint образа code-server: принимает аргументы командной
# строки и запускает code-server (см. command в docker-compose.override.yml).
exec /usr/bin/entrypoint.sh "$@"
