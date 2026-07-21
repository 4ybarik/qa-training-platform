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
