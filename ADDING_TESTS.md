# Как добавить свои автотесты в Jenkins + Allure

Эта инструкция для двух сценариев:
1. **Самый частый случай** — вы добавляете тесты в уже существующие папки
   проекта (`backend/tests/` для API-тестов на pytest, `e2e/` для
   UI-тестов на Playwright). В этом случае Jenkins подхватит их
   автоматически, без единой правки конфигурации.
2. **Менее частый случай** — вы заводите совершенно новую группу тестов
   (новый инструмент, новый язык, отдельная папка верхнего уровня). Тогда
   нужно явно добавить стадию в `Jenkinsfile`. Это разобрано в разделе 4.

---

## 1. Как устроена цепочка "тест -> Jenkins -> Allure"

Прежде чем писать тесты, важно понимать, что происходит на каждом шаге —
тогда будет понятно, что чинить, если что-то не отобразится.

```
Ваш тест (test_*.py)
   |
   |  pytest запускает тест, плагин allure-pytest перехватывает события
   |  (старт теста, шаги, ассерты, исключения) и на каждый тест пишет
   |  JSON-файл в папку, указанную флагом --alluredir
   v
Папка allure-results/ (общая для api и e2e — см. ниже)
   |
   |  Эта папка смонтирована как общий Docker volume allure_results,
   |  его видят и контейнер app (где гоняется pytest), и отдельный
   |  контейнер allure
   v
Контейнер allure (docker-compose.yml, сервис "allure")
   |
   |  Каждые 5 секунд (настройка CHECK_RESULTS_EVERY_SECONDS) сканирует
   |  папку allure-results/ и перестраивает HTML-отчёт
   v
http://localhost:5050 — готовый отчёт, обновляется автоматически
```

**Главный практический вывод**: чтобы тест попал в Allure, ему достаточно
двух вещей — (а) быть собранным через `pytest` с подключённым плагином
`allure-pytest`, и (б) результаты должны писаться в папку, которую видит
контейнер `allure`. Обе вещи уже настроены в проекте для папок
`backend/tests/` и `e2e/`.

---

## 2. Добавляем API-тест (pytest, папка backend/tests/)

### Шаг 1 — пишем тест

Создайте файл `backend/tests/test_my_feature.py` (имя должно начинаться с
`test_`, иначе pytest его не найдёт — см. `pytest.ini`, там
`python_files = test_*.py`):

```python
"""Тесты моей новой фичи."""
from tests.conftest import auth


def test_my_new_endpoint(client, user_token):
    r = client.get("/api/my-endpoint", headers=auth(user_token))
    assert r.status_code == 200
```

Фикстуры `client`, `user_token`, `admin_token` уже определены в
`backend/tests/conftest.py` — используйте их, не создавайте свои с теми же
именами.

### Шаг 2 — (опционально) обогащаем тест аннотациями Allure

Это необязательно — тест и без этого появится в отчёте. Но Allure умеет
показывать гораздо больше структуры, если её явно разметить:

```python
import allure


@allure.feature("Курсы")
@allure.story("Запись на курс")
@allure.severity(allure.severity_level.CRITICAL)
def test_enroll_in_course(client, user_token):
    with allure.step("Отправляем запрос на запись"):
        r = client.post("/api/courses/1/enroll", headers=auth(user_token))

    with allure.step("Проверяем успешный ответ"):
        assert r.status_code == 200

    allure.attach(r.text, name="Тело ответа", attachment_type=allure.attachment_type.JSON)
```

Что это даёт в отчёте Allure:
- `@allure.feature` / `@allure.story` — тест группируется по функциональным
  блокам на вкладке "Behaviors", а не просто в плоском списке файлов.
- `@allure.severity` — фильтр по критичности (BLOCKER, CRITICAL, NORMAL,
  MINOR, TRIVIAL) на главном экране отчёта.
- `with allure.step(...)` — каждый шаг видно отдельно в развёрнутом тесте,
  с указанием, на каком именно шаге упал тест (если упал).
- `allure.attach(...)` — к тесту прикрепляется файл/текст/скриншот, виден
  во вкладке теста в отчёте.

### Шаг 3 — проверяем локально (до пуша в Jenkins)

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/test_my_feature.py -v --alluredir=../allure-results/api
```

Если хотите сразу посмотреть отчёт локально, без Jenkins вообще:

```bash
pip install allure-commandline --break-system-packages  # один раз
allure serve ../allure-results/api
```

Откроется браузер с тем же отчётом, что в итоге увидите на `:5050`.

### Шаг 4 — всё. Jenkins подхватит тест автоматически

Стадия `API tests (pytest)` в `Jenkinsfile` уже выполняет:

```bash
python -m pytest --alluredir=/app/allure-results
```

Без указания конкретных файлов — значит, pytest сам найдёт **все** файлы
`test_*.py` в `backend/tests/`, включая ваш новый. Ничего в `Jenkinsfile`
менять не нужно. Просто запустите **Build Now** в Jenkins.

---

## 3. Добавляем E2E-тест (Playwright, папка e2e/)

### Шаг 1 — пишем тест

Создайте `e2e/test_my_scenario.py`:

```python
"""E2E: мой новый сценарий."""
from playwright.sync_api import expect


def test_my_scenario(login, base_url):
    page = login()  # фикстура login уже логинит под user@test.com
    page.goto(f"{base_url}/courses")
    expect(page.get_by_test_id("courses-title")).to_be_visible()
```

Фикстуры `page`, `base_url`, `login` уже определены (`page` приходит из
`pytest-playwright`, `base_url`/`login` — из `e2e/conftest.py`).

### Шаг 2 — (опционально) добавляем Allure-аннотации

Точно так же, как в разделе 2, шаг 2 — `import allure`,
`@allure.feature(...)`, `with allure.step(...)`. Для Playwright особенно
полезно прикреплять скриншот при падении:

```python
import allure


def test_my_scenario(login, base_url, page):
    try:
        page.goto(f"{base_url}/courses")
        expect(page.get_by_test_id("courses-title")).to_be_visible()
    except Exception:
        allure.attach(page.screenshot(), name="Скриншот на момент падения",
                      attachment_type=allure.attachment_type.PNG)
        raise
```

### Шаг 3 — проверяем локально

Нужен реально запущенный `app` (например, через обычный
`docker compose up -d app db` без CI-override):

```bash
cd e2e
pip install -r requirements.txt
playwright install chromium
BASE_URL=http://localhost:8000 python -m pytest test_my_scenario.py -v --alluredir=../allure-results/e2e
```

### Шаг 4 — всё. Jenkins подхватит тест автоматически

Стадия `E2E tests (Playwright)` в `Jenkinsfile` тоже выполняет `pytest` без
указания конкретного файла — новый тест в `e2e/` подхватится сам.

---

## 4. Завожу совсем новую группу тестов (отдельная папка/инструмент)

Если хочется тестов, которые не вписываются в pytest API/E2E (например,
нагрузочные тесты на Locust, контрактные тесты на отдельном фреймворке) —
это уже описано в `ARCHITECTURE.md`, раздел 5, но кратко повторю применительно
к Allure:

1. Создайте папку на уровне `backend/`/`e2e/`, например `load/`.
2. Добавьте `requirements.txt` со своими зависимостями + `allure-pytest`
   (если фреймворк на pytest) либо нативный Allure-адаптер для другого
   раннера (Allure поддерживает не только Python — есть адаптеры для JUnit,
   TestNG, NUnit, Cucumber, Robot Framework и других).
3. Пишите результаты в **поддиректорию** общей папки allure-results,
   например `--alluredir=../allure-results/load` — главное, чтобы все группы
   результатов лежали внутри одного корня `allure-results/`, тогда Allure
   объединит их в один отчёт автоматически (он сканирует всё дерево).
4. Добавьте новую стадию в `Jenkinsfile`, по образцу уже существующих.
   Например, для нагрузочных тестов на чистом Python:

```groovy
stage('Load tests') {
    steps {
        dir('/workspace') {
            sh '''
                ${COMPOSE} run --rm \
                  -v "$(pwd)/${ALLURE_RESULTS_DIR}/load:/app/allure-results" \
                  --entrypoint sh app -c \
                  "pip install -r load/requirements.txt --break-system-packages --quiet && \
                   python -m pytest load/ --alluredir=/app/allure-results"
            '''
        }
    }
}
```

Вставьте этот блок внутрь `stages { ... }` в `Jenkinsfile`, рядом с уже
существующими `stage('API tests (pytest)')` / `stage('E2E tests (Playwright)')`.

---

## 5. Как посмотреть результат в Allure

После того как в Jenkins отработала сборка (**Build Now** → дождаться
зелёного/красного статуса):

### Вариант А — через отдельный сервис Allure (всегда работает)

Откройте:
```
http://localhost:5050/allure-docker-service/projects/default/reports/latest/index.html
```

Сервис сканирует общую папку `allure-results/` каждые 5 секунд и сам
перестраивает отчёт — обновлять вручную не нужно, просто подождите и
обновите страницу браузера.

### Вариант Б — через плагин внутри Jenkins (если он у вас стабильно
установлен — см. примечание про нестабильную установку в `Jenkinsfile`)

На странице конкретной сборки (Build #N) появится пункт меню слева
**"Allure Report"**. Это работает, только если в `Jenkinsfile` раскомментирована
строка `allure includeProperties: ...` в блоке `post { always { ... } }`.

---

## 6. Частые проблемы и их причины

| Симптом                                            | Причина и решение |
|-----------------------------------------------------|--------------------|
| Тест не появился в Allure вообще                    | Файл не начинается с `test_`, либо функция не начинается с `test_` (см. `pytest.ini`: `python_files`/`python_functions`). Переименуйте. |
| Тест есть в Allure, но без шагов/фич                 | Это нормально без аннотаций `@allure.feature`/`with allure.step(...)` — Allure покажет тест просто как пройденный/упавший, без подробностей. Добавьте аннотации (раздел 2, шаг 2). |
| Отчёт на `:5050` не обновился после новой сборки     | Подождите 5-10 секунд (интервал сканирования) и обновите страницу. Если не помогло — проверьте, что Jenkins реально писал в `allure-results/` (см. Console Output сборки на наличие строк `Downloading`/`Successfully installed allure-pytest`). |
| `ModuleNotFoundError: No module named 'allure'`     | В контейнере, где гоняется ваш тест, не установлен `allure-pytest`. Для `backend/tests/` он уже в `requirements.txt`; для новой папки (раздел 4) — добавьте его в свой `requirements.txt` или `pip install` команду в стадии. |
| Тесты из новой папки не запускаются в Jenkins        | Вы добавили новую папку (не `backend/tests/` и не `e2e/`), но не добавили для неё стадию в `Jenkinsfile` — см. раздел 4. |
| E2E-тест падает в Jenkins, хотя локально работает    | Часто из-за `BASE_URL`: локально вы используете `http://localhost:8000`, а в Jenkins (внутри docker-сети) — `http://app:8000` (см. переменную `-e BASE_URL=http://app:8000` в стадии E2E `Jenkinsfile`). Не хардкодьте `localhost` внутри теста — используйте фикстуру `base_url`. |

---

## 7. Шпаргалка: минимальный шаблон нового теста с полным набором Allure-фич

```python
import allure
from tests.conftest import auth


@allure.feature("Имя функционального блока")
@allure.story("Конкретный сценарий")
@allure.severity(allure.severity_level.NORMAL)
@allure.description("Развёрнутое описание теста для отчёта (необязательно)")
def test_something(client, user_token):
    with allure.step("Шаг 1: подготовка данных"):
        payload = {"key": "value"}

    with allure.step("Шаг 2: выполнение запроса"):
        r = client.post("/api/something", headers=auth(user_token), json=payload)

    with allure.step("Шаг 3: проверка результата"):
        allure.attach(r.text, name="Ответ сервера", attachment_type=allure.attachment_type.JSON)
        assert r.status_code == 200
```

Скопируйте этот шаблон, переименуйте функцию и файл — и тест готов к
автоматическому подхвату Jenkins и красивому отображению в Allure.
