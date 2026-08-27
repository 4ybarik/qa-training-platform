#!/bin/sh
set -eu

# Именованные Docker volumes могут сохраниться от старой версии, работавшей
# от root. Подготавливаем только каталоги, куда приложение должно писать, и
# сразу сбрасываем привилегии перед запуском Python/RQ.
if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/app/static/uploads/avatars /app/quality-history
    chown -R appuser:appuser /app/app/static/uploads/avatars /app/quality-history
    exec setpriv --reuid=appuser --regid=appuser --init-groups "$@"
fi

exec "$@"
