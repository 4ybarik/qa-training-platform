# Как добавить автотест в проект

Пользователь работает в локальной IDE. Платформа не содержит редактора кода и
не запускает решения из браузера.

## Рабочий цикл

1. Откройте `/practice`, выберите задачу и изучите мишень и критерии приёмки.
2. Создайте `test_*.py` в подходящей подпапке `student_tests/`.
3. Запустите тест локально против поднятого приложения.
4. Добавьте код в Git и отправьте его в репозиторий.
5. Jenkins через webhook (или polling) заберёт новый commit, создаст отдельный
   Compose project и выполнит найденные тесты. Результат commit публикуется в
   JUnit/Allure и в истории качества.

## Куда класть тест

| Вид проверки | Каталог | Jenkins-стадия |
|---|---|---|
| HTTP API | `student_tests/api/` | `Student API and integration tests` |
| Контракт | `student_tests/contract/` | `Student API and integration tests` |
| БД, файлы, WebSocket, несколько компонентов | `student_tests/integration/` | `Student API and integration tests` |
| Playwright UI | `student_tests/ui/` | `Student UI tests` |

Pytest собирает все файлы `test_*.py`. Править `Jenkinsfile` для обычного нового
Python-теста не требуется. Шаблоны `_task_template.py` намеренно не собираются.

## Первый локальный запуск

```bash
python -m pip install -r student_tests/requirements.txt
python -m playwright install chromium
docker compose up -d --build
```

API, contract и integration:

```bash
BASE_URL=http://localhost:8000 \
python -m pytest student_tests/api student_tests/contract student_tests/integration -v
```

UI:

```bash
BASE_URL=http://localhost:8000 \
python -m pytest student_tests/ui -v
```

Или используйте `make student-api`, `make student-ui`, `make student-all`.

## Доступные фикстуры

- `base_url` — адрес из `BASE_URL`;
- `api_client` — `httpx.Client` с таймаутом и без автоматических redirects;
- `run_id` — уникальный идентификатор запуска;
- `run_headers` — `X-Test-Run-Id` для изоляции stateful-мишеней и автоматический
  teardown через `DELETE /api/practice/state`;
- `integration_headers` — тот же namespace для Redis/RQ и автоматический
  teardown интеграционного состояния;
- `test_support_headers` и `user_factory` — Test Data API с адресной очисткой
  пользователей/курсов на каждый тест;
- `auth_headers` — получение Bearer-токена для созданного фабрикой пользователя;
- `credentials` — тестовый пользователь из переменных окружения;
- `login` — вход через UI для Playwright;
- `axe` — сканер axe-core для accessibility-сценариев;
- `database_url` — строка подключения из `STUDENT_DATABASE_URL`.

Не записывайте адреса, пароли и токены в тест. Jenkins передаёт те же параметры
через окружение во внутренней Docker-сети.

## Минимальный API-тест

```python
import pytest


@pytest.mark.api
def test_resource_can_be_created(api_client, run_headers):
    response = api_client.post(
        "/api/practice/resources",
        headers=run_headers,
        json={"name": "unique resource", "quantity": 1, "price": 10},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "unique resource"
```

## Минимальный UI-тест

```python
import pytest
from playwright.sync_api import expect


@pytest.mark.ui
def test_dynamic_element(login, base_url):
    page = login()
    page.goto(f"{base_url}/practice/components")
    page.get_by_test_id("spawn-dynamic").click()

    expect(page.get_by_test_id("dynamic-element")).to_be_visible()
```

## Обязательные инженерные правила

- тест не зависит от порядка запуска;
- изменяемые данные уникальны, для practice API используется `run_headers`;
- очистка адресная и выполняется в `finally`/yield teardown;
- нет `time.sleep` в UI-тестах и бесконечного polling;
- таймауты и число retry ограничены;
- токены, cookies и пароли не прикладываются к Allure;
- assertions проверяют контракт и результат, а не случайные детали реализации;
- `xfail`, retry и отключение теста не маскируют дефект без объяснённой причины.

## Что запускает Jenkins

Пайплайн разделён на четыре независимых контура:

1. `Reference API tests` — защищает backend самого полигона.
2. `Student API and integration tests` — решения из `student_tests/api`,
   `contract`, `integration`.
3. `Reference E2E tests` — защищает интерфейс самого полигона.
4. `Student UI tests` — решения из `student_tests/ui`.

Jenkins запускает UI-проверки последовательно в Chromium, Firefox и WebKit и
дополнительно выполняет axe-core. Для включённых параметров сборки запускаются
контролируемые мутации (`mutation-score.json`) и Locust с блокирующим p95.
Результаты всех контуров попадают в общий Allure volume. Playwright сохраняет
trace, screenshot и video при падении; Jenkins архивирует `test-results` и
`ci-artifacts/`.

Если пользовательский тест красный, исправлять эталонный тест или ослаблять
контракт платформы нельзя: причина должна устраняться в решении либо оформляться
как подтверждённый дефект тестовой мишени.
