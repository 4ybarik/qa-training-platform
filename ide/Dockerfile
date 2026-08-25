# Встроенная веб-IDE платформы: VS Code в браузере (code-server) с полностью
# готовым окружением ученика. Сервис объявлен в docker-compose.override.yml,
# поэтому поднимается локальным `make up` и НЕ собирается Jenkins'ом.
#
# Версия закреплена ради воспроизводимости; обновляется вручную.
# Внимание: база образа — Debian 13 (trixie), системный Python здесь 3.13.
# Все зависимости student_tests/requirements.txt проверены на совместимость.
FROM codercom/code-server:4.134.0

USER root
ENV DEBIAN_FRONTEND=noninteractive

# Python (системный из Debian), make и git для терминала IDE: через них
# работают make watch-api / make progress / git describe.
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        python3 python3-venv make git curl \
 && ln -sf /usr/bin/python3 /usr/local/bin/python \
 && rm -rf /var/lib/apt/lists/*

# Зависимости учебных тестов. Venv живёт ВНЕ монтируемого workspace, чтобы не
# зависеть от содержимого хоста и не попадать в bind mount.
COPY student_tests/requirements.txt /tmp/student-requirements.txt
RUN python -m venv /home/coder/.venv-student \
 && /home/coder/.venv-student/bin/pip install --no-cache-dir --upgrade pip \
 && /home/coder/.venv-student/bin/pip install --no-cache-dir -r /tmp/student-requirements.txt

# Chromium + системные библиотеки для UI-тестов (--with-deps требует root).
RUN /home/coder/.venv-student/bin/playwright install --with-deps chromium

# Расширения ставим при сборке (Open VSX), чтобы IDE была готова сразу после
# старта. Pylance недоступен (закрытый Marketplace MS) — language server Jedi.
USER coder
RUN code-server --install-extension ms-python.python \
 && code-server --install-extension charliermarsh.ruff

# Обёртка готовит workspace до старта code-server (см. сам файл).
# Возвращаемся в root: предыдущий шаг (установка расширений) выполнялся от coder.
USER root
COPY ide/entrypoint-wrapper.sh /usr/local/bin/entrypoint-wrapper.sh
RUN chmod 755 /usr/local/bin/entrypoint-wrapper.sh
USER coder
ENTRYPOINT ["/usr/local/bin/entrypoint-wrapper.sh"]
