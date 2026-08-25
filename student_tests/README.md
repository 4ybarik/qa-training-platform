# Пользовательские автотесты

Это единственная папка для решений практических задач. Код пишется в локальной
IDE, сохраняется в Git и автоматически запускается Jenkins.

Структура:

- `api/` — HTTP API;
- `contract/` — схемы и обратная совместимость контрактов;
- `integration/` — БД, файлы, WebSocket и асинхронные операции;
- `ui/` — Playwright.

Pytest обнаруживает все файлы `test_*.py`. Файлы `_task_template.py` можно
копировать, но сами шаблоны не запускаются. Общие настройки и фикстуры находятся
в `pytest.ini` и `conftest.py`; адрес приложения всегда берётся из `BASE_URL`.

Локальный запуск API-проверок при поднятом приложении:

```bash
python -m pip install -r student_tests/requirements.txt
BASE_URL=http://localhost:8000 python -m pytest student_tests/api student_tests/contract student_tests/integration -v
```

Локальный запуск UI-проверок:

```bash
python -m playwright install chromium
BASE_URL=http://localhost:8000 python -m pytest student_tests/ui -v
```

Не используйте фиксированные email, идентификаторы и имена для изменяемых данных.
Фикстуры `run_id` и `run_headers` дают уникальный `X-Test-Run-Id`, позволяющий
безопасно запускать тесты повторно и параллельно.

## С чего начать: маршрут обучения

Полный каталог задач — в [`AUTOMATION_PRACTICE_CATALOG.md`](../AUTOMATION_PRACTICE_CATALOG.md),
свой прогресс по файлам решений показывает `make progress`. Рекомендуемый
порядок — от простого к сложному:

1. **Разминка (basic).** Запустите стек (`make up`), откройте `/docs` и
   `/practice`, затем напишите первый тест по образцу
   `api/test_example_api_patterns.py` (там же — параметризация и CRUD).
2. **API и контракты.** Задачи из разделов «API и контракты» и
   «Аутентификация и безопасность»: матрица статусов, CRUD, RBAC, rate limit.
3. **UI и Page Object.** Начните с `ui/test_example_page_object.py`: вход через
   готовый Page Object (`ui/pages/`). Затем свои страницы для
   `/register`, `/profile`, `/admin` по тому же шаблону.
4. **Интеграции.** БД, файлы, WebSocket, очереди — раздел «Интеграции и данные».
5. **Надёжность и CI.** Retry, таймауты, параллельная изоляция, mutation score.

Критерии завершения каждой задачи — в конце каталога. Правило номер один:
тест должен падать, если поведение системы нарушает контракт, иначе он ничего
не защищает.

