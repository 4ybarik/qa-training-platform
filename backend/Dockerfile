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

# В проде seed не запускается автоматически (ENVIRONMENT=production).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
