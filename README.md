# QA Training Platform

Учебная веб-платформа для практики **автоматизации тестирования**. Содержит
реалистичный backend (REST API + серверный веб-интерфейс), базу данных,
ролевую модель доступа, режим имитации нестабильности (*Testing Playground*) и
готовые примеры тестов на **pytest** (API) и **Playwright** (UI/E2E).

Проект сознательно собран как **модульный монолит** с чистым разделением слоёв
(api → service → repository → domain). Это сохраняет архитектурные принципы
оригинального ТЗ (где предполагались отдельные сервисы auth/course/exam/
notification/audit), но запускается одной командой и не требует Kafka/Redis/
Nginx для старта обучения. Как масштабировать до полноценной микросервисной
схемы — описано в разделе «Дальнейшее развитие».

---

## Быстрый старт (Docker)

Требуется Docker и Docker Compose.

```bash
docker compose up -d --build
```

После старта откройте:

- Веб-интерфейс: <http://localhost:8000/>
- Документация API (Swagger): <http://localhost:8000/docs>
- Альтернативная документация (ReDoc): <http://localhost:8000/redoc>
- Проверка состояния: <http://localhost:8000/health>
- Jenkins (CI): <http://localhost:8080> — первичная настройка описана в разделе «CI/CD: Jenkins + Allure»
- Allure-отчёты: <http://localhost:5050> — появятся после первого прогона тестов

На первом запуске автоматически создаётся схема БД и загружаются демо-данные
(50 курсов, ~100 экзаменов, ~500 вопросов, пользователи и уведомления).

### Демонстрационные учётные записи

| Роль    | Email              | Пароль         |
|---------|--------------------|----------------|
| ADMIN   | admin@test.com     | `Password123!` |
| MANAGER | manager@test.com   | `Password123!` |
| USER    | user@test.com      | `Password123!` |

Также созданы `user1@test.com` … `user30@test.com` с тем же паролем.

---

## Запуск без Docker (для разработки)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Для локального запуска удобно использовать SQLite:
export DATABASE_URL="sqlite:///./qatp.db"   # Windows (PowerShell): $env:DATABASE_URL="sqlite:///./qatp.db"
export ENVIRONMENT=development

uvicorn app.main:app --reload
```

---

## Запуск тестов

### API-тесты (pytest, без Docker, на SQLite)

```bash
cd backend
python -m pytest
```

### E2E-тесты (Playwright, требуется запущенный сервер на :8000)

```bash
cd e2e
pip install -r requirements.txt
playwright install chromium
BASE_URL=http://localhost:8000 python -m pytest
```

---

## CI/CD: Jenkins + Allure

`docker compose up -d --build` поднимает не только `app`+`db`, но и **Jenkins**
(порт `:8080`) и **Allure-сервис** (порт `:5050`) для просмотра результатов
автотестов.

Jenkins собирается из `./jenkins/Dockerfile` — это официальный образ
`jenkins/jenkins` с доустановленным **Docker CLI**. Без этого доступ к
`/var/run/docker.sock` есть (канал к демону хоста), а самой команды `docker`
внутри контейнера нет — пайплайн упадёт с `docker: not found`. Поскольку
установка Docker CLI идёт через `apt-get`/`curl` из официального репозитория
Docker, **первая сборка `jenkins` требует доступа в интернет** (как и сборка
любого образа с внешними зависимостями).

Про порты `db`/`app` устроено немного нестандартно, и это важно понимать:
сам `docker-compose.yml` **не пробрасывает** порты `5432`/`8000` на хост —
это сделано в отдельном `docker-compose.override.yml`, который Docker
Compose подключает **автоматически**, но только если команда запущена без
явного `-f` (это стандартное, задокументированное поведение Compose).
Поэтому при обычной разработке (`docker compose up -d --build`, без `-f`)
порты доступны на `localhost` как обычно. А `Jenkinsfile` запускает команды
с явным `-f docker-compose.yml` — из-за этого override **не** подключается,
и CI-копия стека (другое имя проекта compose — `qatp_ci`) поднимается без
портов на хост, не конкурируя за порты `5432`/`8000` с уже запущенным
локально основным стеком (иначе была бы ошибка `port is already allocated`).
Тестам проброс портов и не нужен — все обращения идут по внутренним
DNS-именам docker-сети (`db:5432`, `app:8000`), не через `localhost`.

**Про Docker-outside-of-Docker и пути для volumes.** Jenkins запускает
дочерние контейнеры для тестов через проброшенный `/var/run/docker.sock`
хоста — это значит, что демон Docker, который реально создаёт контейнеры,
работает на **хосте**, а не внутри Jenkins. Поэтому любой volume-маунт для
дочернего контейнера, указывающий на путь файловой системы (например, чтобы
дать контейнеру доступ к исходникам `e2e/`), должен указывать путь на
**реальной файловой системе хоста**, а не путь, видимый изнутри самого
контейнера Jenkins (`/workspace` — это путь только для Jenkins, демон Docker
хоста про него не знает; такая попытка даст ошибку
`is not shared from the host and is not known to Docker` на macOS/Windows).
Решение — переменная `HOST_PROJECT_DIR` в `docker-compose.yml` (сервис
`jenkins`, `environment.HOST_PROJECT_DIR: "${PWD}"`) автоматически
подставляет реальный путь на хосте в момент `docker compose up`; `Jenkinsfile`
использует её для маунта исходников.

Результаты Allure — это **отдельный** случай: они пишутся не на путь
файловой системы, а в **именованный Docker volume** `allure_results` (тот
же, что слушает контейнер `allure`) — см. переменную `ALLURE_VOLUME` в
`Jenkinsfile` и раздел «Просмотр отчётов Allure» ниже.

Если вы на **macOS** и Docker Desktop всё равно ругается на путь — откройте
**Docker Desktop → Settings → Resources → File Sharing** и убедитесь, что
директория с проектом (или весь диск/раздел, где она лежит) добавлена в
список разрешённых для общего доступа.

### Первый запуск

1. `docker compose up -d --build` — поднимет всё, включая Jenkins.
2. Откройте Jenkins на <http://localhost:8080>. Получите начальный пароль:
   ```bash
   docker compose exec jenkins cat /var/jenkins_home/secrets/initialAdminPassword
   ```
3. Установите рекомендуемые плагины. Плагин **Allure Jenkins Plugin**
   (Manage Jenkins → Plugins → Available) можно поставить дополнительно, но
   у некоторых версий Jenkins он ставится нестабильно — это не блокирует
   остальной пайплайн (см. примечание про Allure ниже).
4. Создайте джобу: **New Item → Pipeline** (не "Freestyle project" — пункта
   "Pipeline" не будет в списке, если не установлен плагин **Pipeline**,
   входящий в набор "Suggested plugins"). В настройках джобы, в разделе
   **Pipeline**, поле **Definition** переключите на **"Pipeline script"**
   (не "Pipeline script from SCM" — этот вариант требует настроенный Git и
   без него падает с ошибкой `Jenkinsfile not found`). В появившееся поле
   **Script** вставьте содержимое корневого `Jenkinsfile` целиком.
5. Запустите сборку (Build Now). Пайплайн соберёт `app`, прогонит API-тесты
   (pytest) и E2E-тесты (Playwright через временный контейнер, без
   зависимости от плагина Docker Pipeline), затем опубликует Allure-отчёт.

### Просмотр отчётов Allure

- Через сам Jenkins: вкладка **Allure Report** на странице сборки (если
  установлен плагин).
- Напрямую через сервис Allure: <http://localhost:5050/allure-docker-service/projects/default/reports/latest/index.html>
  — он автоматически подхватывает результаты из именованного Docker volume
  `allure_results` (полное имя — `qa-training-platform_allure_results`,
  формируется Compose как `<имя_проекта>_<имя_volume>`), в который пишут
  и pytest, и Playwright-тесты.

### Локальный запуск с Allure-результатами (без Jenkins)

Если вы хотите быстро посмотреть отчёт сами, без публикации в постоянный
Docker-сервис `:5050` — самый простой путь:

```bash
cd backend
pip install -r requirements.txt
pip install allure-pytest --break-system-packages
python -m pytest --alluredir=/tmp/allure-results

pip install allure-commandline --break-system-packages  # один раз
allure serve /tmp/allure-results
```

`allure serve` поднимает свой временный локальный сервер и сразу открывает
отчёт в браузере — он никак не связан с Docker-сервисом `allure` из
`docker-compose.yml`, это полностью отдельный, более лёгкий путь для
быстрой проверки одного прогона.

Если же вы хотите, чтобы результаты локального прогона попали именно в
**постоянный** Docker-сервис на `:5050` (тот же, что использует Jenkins) —
нужно писать их в тот же именованный Docker volume, а не в папку на диске
(простой `--alluredir=../allure-results` физически не пересечётся с volume,
который слушает контейнер `allure` — это тот же подвох, что и в
Docker-outside-of-Docker сценарии Jenkins, см. выше). Сделать это можно так:

```bash
cd backend
pip install -r requirements.txt allure-pytest --break-system-packages
docker run --rm \
  -v "$(pwd)/..:/repo" \
  -v "qa-training-platform_allure_results:/allure-results" \
  -w /repo/backend \
  python:3.12-slim \
  sh -c "pip install -r requirements.txt --break-system-packages --quiet && \
         python -m pytest --alluredir=/allure-results"
```

Здесь `$(pwd)` выполняется в вашем обычном терминале на хосте (не внутри
Jenkins), поэтому он и так уже даёт реальный путь на диске — в отличие от
сценария внутри Jenkins-контейнера, тут никакой путаницы с путями нет.

### Важная оговорка

`Jenkinsfile` в этом репозитории — рабочая отправная точка, а не выверенный
до мелочей продакшен-пайплайн: точная конфигурация Jenkins (версия Docker,
установленные плагины, сетевые имена контейнеров) отличается от инсталляции
к инсталляции. Перед первым запуском проверьте комментарии в начале
`Jenkinsfile` — там перечислены три места, которые обычно нужно подстроить
под конкретное окружение.

---

## Архитектура и структура

```
qa-training-platform/
├── docker-compose.yml         # app + PostgreSQL + Jenkins + Allure
├── docker-compose.override.yml # порты для разработки (подключается автоматически без -f)
├── Jenkinsfile                # CI-пайплайн: build -> pytest -> Playwright -> Allure
├── ARCHITECTURE.md            # как расширять проект (БД, слои, RBAC, новые сервисы)
├── ADDING_TESTS.md            # как добавлять автотесты, чтобы они шли в Jenkins + Allure
├── CHANGELOG.md                # история изменений по версиям (Keep a Changelog)
├── Makefile                   # ярлыки: up/down/test/e2e/seed
├── jenkins/
│   └── Dockerfile             # образ Jenkins + предустановленный Docker CLI
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── core/              # config, database, security (JWT/хеши), rate_limit
│       ├── domain/            # models (ORM), schemas (Pydantic), enums, errors
│       ├── repositories/      # доступ к данным (CRUD, выборки)
│       ├── services/          # бизнес-логика (auth, courses, exams, admin…)
│       ├── api/               # FastAPI-роутеры + зависимости (RBAC)
│       ├── web/               # серверные страницы (Jinja)
│       ├── templates/         # HTML-шаблоны с data-testid (вкл. формы admin CRUD)
│       ├── static/            # css, js (модалки, тосты, dnd, ws…)
│       ├── middleware.py      # Testing Playground (задержки/ошибки)
│       ├── seed.py            # демо-данные
│       └── main.py            # сборка приложения
│   └── tests/                 # API-тесты (pytest + TestClient, вкл. RBAC/admin)
└── e2e/                       # примеры Playwright-тестов
```

**Поток запроса:** `api (роутер)` принимает HTTP, проверяет права через
зависимости, вызывает `service`, тот выражает бизнес-правила и обращается к
`repository`, который работает с ORM-`models`. Доменные исключения
(`domain/errors.py`) централизованно превращаются в HTTP-коды
(`api/errors.py`). Слои не «перепрыгивают» друг через друга — это и есть
основная идея чистой архитектуры.

**Как расширять проект** (новая таблица в БД, новый эндпоинт, новая
страница, RBAC, интеграция Redis/Kafka) — подробно, со сквозным примером
по всем слоям, в [`ARCHITECTURE.md`](./ARCHITECTURE.md).

**Как добавлять свои автотесты, чтобы они запускались в Jenkins и
отображались в Allure** — пошагово, с шаблонами и разбором частых проблем,
в [`ADDING_TESTS.md`](./ADDING_TESTS.md).

**История изменений по версиям** — в [`CHANGELOG.md`](./CHANGELOG.md).
Как версия попадает из Git-тега в Swagger/`/health`/UI — в разделе
«Версионирование и релизы» ниже.

---

## Что тренировать на этом полигоне

Интерфейс намеренно насыщен типовыми элементами, на которых ломаются или
крепнут автотесты. У каждого интерактивного элемента есть атрибут
`data-testid` — это рекомендуемый стабильный селектор.

| Навык                         | Где практиковать                                   |
|-------------------------------|----------------------------------------------------|
| Формы, все типы полей         | `/register` (text, password, date, select, radio, checkbox) |
| Аутентификация и сессии       | `/login`, cookie `access_token`, `/api/auth/*`     |
| Таблицы, поиск, фильтры, сортировка, пагинация | `/courses`                       |
| Переключение представлений    | таблица ↔ карточки на `/courses`                   |
| Модальные окна, тултипы, тосты| `/dashboard`                                       |
| Вкладки                       | `/courses/{id}`                                    |
| Drag and drop                 | вопрос типа DND на `/exams/{id}`                   |
| Таймеры и динамический прогресс| `/exams/{id}`                                     |
| WebSocket                     | лента событий на `/dashboard`                      |
| Бесконечная прокрутка         | `/notifications`                                   |
| AJAX-действия (fetch)         | прочтение/удаление уведомлений, смена роли         |
| Ролевой доступ (RBAC)         | `/admin` и админ-CRUD (курсы/экзамены/уведомления/пользователи) видны и доступны только ADMIN; USER может только просматривать |
| Нестабильность (flaky)        | `/playground`: задержки и случайные ошибки 500     |
| API-тестирование             | Swagger `/docs`, эндпоинты `/api/*`                |

### Testing Playground

На странице `/playground` (или заголовком `X-Playground: on` к запросам `/api`)
включается имитация нестабильного бэкенда: искусственные задержки и случайные
ответы `500`. Это полигон для отработки ожиданий, таймаутов и ретраев.

---

## Карта API (основное)

| Метод | Путь                                   | Назначение                       |
|-------|----------------------------------------|----------------------------------|
| POST  | `/api/auth/register`                   | регистрация                      |
| POST  | `/api/auth/login`                      | вход (access + refresh)          |
| POST  | `/api/auth/refresh`                    | обновление токена                |
| GET   | `/api/auth/me`                         | текущий пользователь             |
| GET   | `/api/courses`                         | каталог (q/category/sort/page)   |
| POST  | `/api/courses`                         | создать курс (**ADMIN**)         |
| PUT   | `/api/courses/{id}`                    | изменить курс (**ADMIN**)        |
| DELETE| `/api/courses/{id}`                    | удалить курс (**ADMIN**)         |
| POST  | `/api/courses/{id}/enroll`             | запись на курс                   |
| GET   | `/api/exams/{id}`                      | экзамен с вопросами (без ответов)|
| GET   | `/api/exams/{id}/admin`                | экзамен с признаком is_correct (**ADMIN**) |
| POST  | `/api/courses/{id}/exams`              | создать экзамен с вопросами (**ADMIN**) |
| PUT   | `/api/exams/{id}`                      | изменить экзамен (**ADMIN**)     |
| DELETE| `/api/exams/{id}`                      | удалить экзамен (**ADMIN**)      |
| POST  | `/api/exams/{id}/submit`               | отправка ответов, результат      |
| GET   | `/api/notifications`                   | мои уведомления                  |
| POST  | `/api/admin/notifications`             | отправить уведомление: одному или всем (**ADMIN**) |
| GET   | `/api/admin/users`                     | список пользователей (**ADMIN**) |
| PUT   | `/api/admin/users/{id}/role`           | смена роли (**ADMIN**)           |
| PUT   | `/api/admin/users/{id}/active`         | активировать/деактивировать пользователя (**ADMIN**) |
| GET   | `/api/admin/audit`                     | журнал аудита (**ADMIN**)        |
| GET   | `/health` · `/liveness` · `/readiness` | проверки состояния               |

Эндпоинты, помеченные **ADMIN**, требуют роли ADMIN — обычный USER получит
`403 Forbidden`. Полная и всегда актуальная спецификация — в Swagger UI на `/docs`.

---

## Дальнейшее развитие (до уровня исходного ТЗ)

Архитектура подготовлена к расширению точечными изменениями:

- **Redis** вместо in-memory кэша и rate limiter — заменяется реализация за тем
  же интерфейсом (`core/rate_limit.py`), плюс сервис в `docker-compose.yml`.
- **Kafka** — публикацию событий (регистрация, запись, результат экзамена)
  логично вынести из сервисов в шину; точки эмиссии уже локализованы.
- **Разделение на микросервисы** — модули `services/*` и `api/*` уже сгруппированы
  по доменам (auth/courses/exams/notifications/admin) и выделяются в отдельные
  сервисы без переписывания бизнес-логики.
- **SPA-фронтенд (React)** — текущий API самодостаточен; SPA может работать
  поверх тех же эндпоинтов `/api/*`.

---

## Версионирование и релизы

Версия приложения берётся из ближайшего Git-тега (формат `vX.Y.Z` по
[SemVer](https://semver.org/lang/ru/)) автоматически при сборке Docker-образа
и видна в трёх местах: Swagger (`/docs`), эндпоинте `GET /health`
(поле `version`) и подвале веб-интерфейса. Тег — единственный источник
правды; версия нигде не хранится захардкоженной в коде, чтобы не было
рассинхрона между Git и тем, что реально показывает приложение.

```bash
make version   # посмотреть, какая версия подставится при следующей сборке
make up        # пересобрать и поднять стек с актуальной версией из Git
```

Под капотом: `make up` выполняет `git describe --tags --always --dirty` и
передаёт результат как build-arg `APP_VERSION` в `docker-compose.yml` →
`backend/Dockerfile` → переменная окружения → `Settings.app_version`
(`backend/app/core/config.py`). Если в репозитории ещё нет тегов — используется
дефолт `0.0.0-dev`. Суффикс `-dirty` в версии означает, что образ собран не
строго из тега, а с незакоммиченными локальными правками поверх него.

### Как выпустить новую версию

1. Закоммитьте и запушьте все изменения как обычно.
2. Обновите `CHANGELOG.md`: перенесите содержимое `[Unreleased]` в новый
   раздел `[X.Y.Z] — ГГГГ-ММ-ДД`, опишите изменения.
3. Создайте аннотированный тег:
   ```bash
   git tag -a v0.2.0 -m "Краткое описание релиза"
   git push origin v0.2.0
   ```
4. Пересоберите образ (`make up`) — `/health` и Swagger покажут `0.2.0`.

В PyCharm то же самое можно сделать через интерфейс — **Git → New Tag...**
на нужном коммите, затем **Git → Push... → Push Tags** (или явно выбрать
тег в диалоге push).

---

## Технологии

Python 3.12, FastAPI, SQLAlchemy 2.0, Pydantic v2, PostgreSQL 17, Jinja2,
PyJWT, passlib (bcrypt), Uvicorn; тесты — pytest, Playwright.
