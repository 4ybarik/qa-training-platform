FROM python:3.12-slim

# Версия приложения подставляется снаружи (docker-compose.yml передаёт сюда
# результат `git describe --tags` хост-машины). ARG доступен только во время
# сборки образа; ENV ниже делает значение видимым процессу uvicorn внутри
# контейнера во время выполнения — без этого ARG потерялся бы после сборки.
ARG APP_VERSION=0.0.0-dev
ENV APP_VERSION=${APP_VERSION}

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Зависимости устанавливаем отдельным слоем для кэширования.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Непривилегированный пользователь: процесс приложения не должен работать
# от root. Директории под именованные volumes (аватары, история качества)
# заранее созданы и принадлежат appuser, иначе первый mount от root сделал бы
# их недоступными для записи.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /app/app/static/uploads/avatars /app/quality-history \
    && chown -R appuser:appuser /app/app/static/uploads /app/quality-history \
    && chmod 0755 /app/docker-entrypoint.sh

ENTRYPOINT ["/app/docker-entrypoint.sh"]

# Контейнер считается живым только если приложение реально отвечает на /health
# (curl в slim-образе нет, используем стандартную библиотеку Python).
HEALTHCHECK --interval=15s --timeout=5s --start-period=30s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"]

# В проде seed не запускается автоматически (ENVIRONMENT=production).
CMD ["sh", "-c", "python -m app.db_upgrade && exec uvicorn app.main:app --host 0.0.0.0 --port 8000"]
