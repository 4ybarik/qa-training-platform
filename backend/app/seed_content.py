"""Учебный контент для seed: курсы, экзамены и вопросы.

Принцип «от простого к сложному»: 10 треков по 5 курсов, у каждого курса два
экзамена («базовые концепции» и «практика»), всего 100 экзаменов и 500 вопросов.
Контент комбинированный: теория автоматизации + знание мишеней полигона
(эндпоинты /api/practice/*, фикстуры student_tests, локаторы страниц).

Вопросы хранятся компактно: (тип, текст, [(вариант, is_correct), ...]).
DND: порядок вариантов с is_correct=True задаёт правильную последовательность.
TEXT сравнивается без учёта регистра (см. services/exams.py).
"""
from app.domain.enums import QuestionType

S, M, T, D = QuestionType.SINGLE, QuestionType.MULTI, QuestionType.TEXT, QuestionType.DND

# Вопросы группируются в пулы по трекам; экзамены курса берут из пула своего
# трека непересекающиеся пятёрки со сдвигом по номеру курса, поэтому соседние
# курсы перекрываются лишь частично, а внутри одного экзамена повторов нет.
TRACK_POOLS: dict[str, list[tuple]] = {}
COURSE_DESCRIPTIONS: dict[str, list[dict]] = {}  # track_slug -> [описания курсов]


def _pool(track: str, questions: list[tuple]) -> None:
    TRACK_POOLS.setdefault(track, []).extend(questions)


def _desc(track: str, courses: list[dict]) -> None:
    COURSE_DESCRIPTIONS.setdefault(track, []).extend(courses)


def build_courses() -> list[dict]:
    """Плоский список 50 курсов в порядке треков."""
    result: list[dict] = []
    for slug, descriptions in COURSE_DESCRIPTIONS.items():
        for position, course in enumerate(descriptions):
            entry = dict(course)
            entry["track"] = slug
            entry["position"] = position
            result.append(entry)
    return result


# ============================== ТРЕК 1. Основы ==============================
_desc("basics", [
    {"title": "Автотесты с нуля: что это и зачем", "category": "Basics", "price": 0,
     "description": (
         "Стартовая точка пути. Чем автотест отличается от ручной проверки, из чего состоит "
         "тест (подготовка → действие → проверка) и почему его запускает машина.\n\n"
         "```python\ndef test_sum():\n    result = 2 + 2      # действие (act)\n"
         "    assert result == 4  # проверка (assert)\n```\n\n"
         "После курса вы прочитаете любой тест в student_tests/ и найдёте в нём arrange, act "
         "и assert. Практика: задачи раздела «Основы» каталога."
     )},
    {"title": "Пирамида тестирования на практике", "category": "Basics", "price": 0,
     "description": (
         "Много быстрых unit, меньше интеграционных, мало дорогих E2E. На полигоне все уровни "
         "реальные: api/ — контракты, integration/ — БД и очереди, ui/ — браузер.\n\n"
         "```python\n@pytest.mark.integration\ndef test_user_really_in_db(api_client, user_factory):\n"
         "    user = user_factory()                       # действие через API\n"
         "    row = fetch_user(user['email'])             # проверка в PostgreSQL\n"
         "    assert row is not None\n```\n\n"
         "Практика: «API и состояние БД», «Изоляция параллельных тестов»."
     )},
    {"title": "Первый тест на pytest: arrange-act-assert", "category": "Basics", "price": 0,
     "description": (
         "Настоящий тест против живого приложения. Фикстура api_client уже настроена на BASE_URL:\n\n"
         "```python\n@pytest.mark.api\ndef test_status_200(api_client):\n"
         "    response = api_client.get(\"/api/practice/status/200\")\n"
         "    assert response.status_code == 200\n    assert response.json()[\"ok\"] is True\n```\n\n"
         "Детерминированная мишень не требует подготовки данных — идеальный первый тест. "
         "Изменяемые данные требуют X-Test-Run-Id (об этом в курсе про фикстуры)."
     )},
    {"title": "Именование и структура тестов", "category": "Basics", "price": 1990,
     "description": (
         "Хорошее имя — половина диагностики. Формула: test_<действие>_<ожидание>.\n\n"
         "```python\n# плохо\ndef test_case1(): ...\n\n"
         "# хорошо\ndef test_put_without_if_match_returns_428(api_client, run_headers): ...\n```\n\n"
         "Структура каталогов повторяет уровни пирамиды: api/, contract/, integration/, ui/. "
         "Рекомендуемое имя файла совпадает со слагом задачи каталога — так Allure группирует результаты."
     )},
    {"title": "Нестабильность: почему тесты «мигают»", "category": "Basics", "price": 1990,
     "description": (
         "Flaky-тест то проходит, то падает без изменения кода. Причины: sleep вместо ожиданий, "
         "разделяемые данные, скрытые зависимости от сети. Полигон умеет нестабильность "
         "контролируемо:\n\n"
         "```python\nheaders = {\"X-Playground-Scenario\": \"fail-first\",\n"
         "           \"X-Playground-Run\": run_id}\nr = api_client.get(\"/health\", headers=headers)\n"
         "# первый запрос -> 503, повторный -> 200\n```\n\n"
         "Практика: «Контролируемый retry», «Таймаут и повреждённый JSON»."
     )},
])

_pool("basics", [
    (S, "Из каких трёх частей состоит классический автотест?",
     [("Подготовка (arrange) → действие (act) → проверка (assert)", True),
      ("Компиляция → сборка → деплой", False), ("План → отчёт → ретроспектива", False)]),
    (S, "Что делает оператор assert в pytest?",
     [("Проваливает тест, если выражение ложно", True),
      ("Выводит сообщение в лог", False), ("Останавливает весь прогон", False)]),
    (S, "Какое имя файла pytest считает тестовым?",
     [("test_login.py", True), ("login_checks.py", False), ("checks_login.txt", False)]),
    (T, "Какая команда запускает все тесты текущего каталога? Напишите одно слово.",
     [("pytest", True)]),
    (M, "Какие свойства хорошего автотеста вы знаете?",
     [("Детерминированность", True), ("Самодостаточность данных", True),
      ("Наглядность падения", True), ("Зависимость от порядка других тестов", False)]),
    (S, "Что такое flaky-тест?",
     [("То проходит, то падает без изменения кода", True),
      ("Всегда падает из-за бага", False), ("Помечен skip", False)]),
    (S, "Какой уровень пирамиды должен быть самым многочисленным?",
     [("Unit", True), ("Integration", False), ("E2E/UI", False)]),
    (S, "Тест вызывает API и сверяет запись в PostgreSQL. Это уровень...",
     [("Интеграционный", True), ("Unit", False), ("Только smoke", False)]),
    (M, "Почему UI-тесты держат наверху пирамиды в меньшинстве?",
     [("Они медленные", True), ("Более хрупкие к изменениям интерфейса", True),
      ("Их нельзя автоматизировать", False)]),
    (S, "Что вернёт GET /api/practice/status/404?",
     [("Статус 404 и тело {\"requested_status\": 404}", True),
      ("Статус 200 с ошибкой в теле", False), ("Бесконечный редирект", False)]),
    (S, "Как получить JSON тела ответа httpx?",
     [("response.json()", True), ("response.body()", False), ("response.text.json()", False)]),
    (D, "Расставьте шаги автотеста по порядку",
     [("Подготовить данные", True), ("Выполнить действие", True),
      ("Сравнить факт с ожиданием", True), ("Убрать за собой", True)]),
    (D, "Расставьте уровни пирамиды от основания к вершине",
     [("Unit", True), ("Integration/API", True), ("E2E (UI)", True)]),
    (S, "Чем автотест лучше ручной проверки регресса?",
     [("Быстро и стабильно повторяется", True), ("Не требует поддержки", False),
      ("Заменяет исследовательское тестирование", False)]),
    (S, "Тест падает только при запуске вместе с другими. Это...",
     [("Зависимость от состояния/порядка", True), ("Сетевой сбой", False),
      ("Регрессия продукта", False)]),
])


# ============================== ТРЕК 2. pytest ==============================
_desc("pytest", [
    {"title": "Запуск и выборка тестов (pytest CLI)", "category": "Pytest", "price": 0,
     "description": (
         "Управляем прогоном из командной строки: pytest student_tests/api -k create -v.\n\n"
         "-k фильтрует по имени, testpaths задаёт каталоги, -x останавливает на первом падении, "
         "-q делает вывод компактным. В проекте уже настроен pytest.ini c --timeout=60 — "
         "зависший тест не заблокирует прогон."
     )},
    {"title": "Фикстуры: setup/teardown без боли", "category": "Pytest", "price": 0,
     "description": (
         "Фикстура — функция, готовящая окружение для теста. В conftest.py полигона их десяток:\n\n"
         "```python\n@pytest.fixture\ndef run_headers(api_client, run_id):\n"
         "    headers = {\"X-Test-Run-Id\": run_id}\n    yield headers        # тест работает\n"
         "    api_client.delete(\"/api/practice/state\", headers=headers)  # teardown\n```\n\n"
         "yield делит фикстуру на setup и teardown. scope управляет временем жизни."
     )},
    {"title": "Параметризация: один тест — много кейсов", "category": "Pytest", "price": 1990,
     "description": (
         "@pytest.mark.parametrize убирает копипасту:\n\n"
         "```python\n@pytest.mark.parametrize((\"code\", \"ok\"), [\n    (200, True), (404, False), (500, False)])\n"
         "def test_status(api_client, code, ok):\n    r = api_client.get(f\"/api/practice/status/{code}\")\n"
         "    assert r.status_code == code and r.json()[\"ok\"] is ok\n```\n\n"
         "Каждый набор становится отдельным тестом с читаемым id (см. api/test_example_api_patterns.py)."
     )},
    {"title": "Маркеры, conftest.py и строгие метки", "category": "Pytest", "price": 1990,
     "description": (
         "--strict-markers запрещает опечатки в маркерах: неизвестный маркер = ошибка сбора. "
         "Маркеры объявлены в student_tests/pytest.ini: api, ui, integration, contract, security, "
         "reliability. Запуск выборки: pytest -m \"api and not ui\". conftest.py делает фикстуры "
         "видимыми всем тестам каталога без импортов."
     )},
    {"title": "Параллельный запуск и таймауты (xdist)", "category": "Pytest", "price": 2990,
     "description": (
         "pytest-xdist запускает тесты в нескольких процессах: pytest -n 4. Параллельность "
         "требует изоляции данных — на полигоне её даёт X-Test-Run-Id: у каждого воркера свой "
         "namespace в practice-хранилище. pytest-timeout ограничивает время теста и превращает "
         "зависание в падение с понятной причиной."
     )},
])

_pool("pytest", [
    (S, "Что делает ключ -k в pytest?",
     [("Фильтрует тесты по подстроке имени", True), ("Задаёт каталог тестов", False),
      ("Останавливает на первом падении", False)]),
    (S, "Какой ключ останавливает прогон на первом упавшем тесте?",
     [("-x", True), ("-q", False), ("-v", False)]),
    (S, "Где pytest ищет фикстуры, не импортируя их явно?",
     [("В conftest.py", True), ("В settings.py", False), ("Только в самом тесте", False)]),
    (S, "Что разделяет ключевое слово yield внутри фикстуры?",
     [("Код до — setup, после — teardown", True), ("Синхронную и асинхронную части", False),
      ("Публичные и приватные данные", False)]),
    (S, "Какой scope у фикстуры run_headers из student_tests?",
     [("function — новая на каждый тест", True), ("session — одна на весь прогон", False),
      ("module", False)]),
    (S, "Сколько тестов породит parametrize с тремя наборами?",
     [("Три отдельных теста", True), ("Один", False), ("Ноль, нужен ещё маркер", False)]),
    (T, "Какой плагин запускает тесты параллельно в процессах? Напишите название пакета.",
     [("pytest-xdist", True), ("xdist", True)]),
    (T, "Какая переменная окружения включает контролируемую мутацию мишеней?",
     [("TEST_MUTATION", True), ("ALLOW_MUTATION", False)]),
    (S, "--strict-markers защищает от...",
     [("Опечаток в имени маркера", True), ("Медленных тестов", False),
      ("Дублирования фикстур", False)]),
    (S, "Что произойдёт с зависшим тестом в этом проекте?",
     [("pytest-timeout оборвёт его по таймауту из pytest.ini", True),
      ("Он будет висеть вечно", False), ("Jenkins перезапустит контейнер", False)]),
    (M, "Зачем параметризации человекочитаемые id (pytest.param(..., id=\"not-found\"))?",
     [("Понятно, какой кейс упал", True), ("Легко перезапустить конкретный кейс", True),
      ("Без id тесты не запускаются", False)]),
    (S, "Какая команда запустит только API-тесты?",
     [("pytest -m api", True), ("pytest --only api", False), ("make api-only", False)]),
    (D, "Расставьте жизненный цикл фикстуры scope=function",
     [("Setup фикстуры", True), ("Тело теста", True), ("Teardown фикстуры", True)]),
    (S, "Фикстура user_factory из student_tests умеет...",
     [("Создавать уникального пользователя через Test Data API и удалять его после теста", True),
      ("Только читать существующих пользователей", False),
      ("Создавать таблицы БД", False)]),
    (S, "Почему фикстуре auth_headers нужна фикстура user_factory?",
     [("Сначала создаём пользователя, потом логинимся за него", True),
      ("Они дублируют друг друга", False), ("Иначе не работает httpx", False)]),
])

def build_exams_for(track: str, position: int, count_per_exam: int = 5) -> list[dict]:
    """Два экзамена курса: базовые концепции и практика.

    Вопросы берутся из пула трека со сдвигом по позиции курса, поэтому
    экзамены одного курса не повторяются, а разные курсы перекрываются частично.
    """
    pool = TRACK_POOLS[track]
    offset = (position * 3) % max(len(pool), 1)
    taken: list[tuple] = []
    i = 0
    while len(taken) < count_per_exam * 2:
        item = pool[(offset + i) % len(pool)]
        if item not in taken:
            taken.append(item)
        i += 1
    return [
        {"title": "Модуль 1: базовые концепции", "duration": 15,
         "questions": taken[:count_per_exam]},
        {"title": "Модуль 2: практика и разбор", "duration": 25,
         "questions": taken[count_per_exam:]},
    ]

# ============================ ТРЕК 3. HTTP и REST ===========================
_desc("http_api", [
    {"title": "HTTP для тестировщика: методы и коды", "category": "HTTP", "price": 0,
     "description": (
         "Методы: GET — читать, POST — создавать, PUT/PATCH — обновлять, DELETE — удалять. "
         "Классы кодов: 2xx успех, 4xx ошибка клиента, 5xx ошибка сервера. Мишень "
         "/api/practice/status/{code} вернёт любой нужный код — тренируйте проверки без ожидания багов."
     )},
    {"title": "JSON в ответах: чтение и проверки", "category": "HTTP", "price": 0,
     "description": (
         "response.json() превращает тело в Python-объекты. Проверяйте контракт: нужные поля, "
         "типы, границы. Мишень /api/practice/schema/{variant} показывает варианты nullable/"
         "missing/wrong-type/extra — готовая тренировка негативных проверок схемы."
     )},
    {"title": "httpx: первый API-тест", "category": "HTTP", "price": 1990,
     "description": (
         "api_client из conftest построен на httpx и уже смотрит на BASE_URL:\n\n"
         "```python\nr = api_client.post(\"/api/practice/resources\", headers=run_headers,\n"
         "                    json={\"name\": \"demo\", \"quantity\": 1})\n"
         "assert r.status_code == 201\n```\n\n"
         "follow_redirects=False — редиректы тестируются явно (задача «Цепочка redirects»)."
     )},
    {"title": "CRUD-сценарий: от создания до удаления", "category": "HTTP", "price": 1990,
     "description": (
         "Полный жизненный цикл на /api/practice/resources: POST→201 (+ETag), GET→200, "
         "PUT с If-Match→200 (version+1), DELETE→204, повторный GET→404. Каждый шаг проверяет "
         "статус, тело и заголовки. Образец: student_tests/api/test_example_api_patterns.py."
     )},
    {"title": "Идемпотентность, ETag и optimistic locking", "category": "HTTP", "price": 2990,
     "description": (
         "Идемпотентность: повтор POST с тем же Idempotency-Key не создаёт дубль. ETag — версия "
         "ресурса; PUT без If-Match запрещён (428), со старой версией — 412. Это защита от "
         "потерянных обновлений при конкуренции клиентов.\n\nПрактика: «Идемпотентность», "
         "«Конкурентная запись на курс»."
     )},
])

_pool("http_api", [
    (S, "Какой метод создаёт ресурс в REST?", [("POST", True), ("GET", False), ("DELETE", False)]),
    (T, "Какой код у успешного DELETE без тела ответа?", [("204", True)]),
    (S, "Код 401 означает...", [("Не аутентифицирован", True),
      ("Нет прав при известной личности", False), ("Ресурс не найден", False)]),
    (S, "Чем 403 отличается от 401?",
     [("Личность известна, но прав нет", True), ("Это синонимы", False),
      ("403 про серверную ошибку", False)]),
    (M, "Какие заголовки относятся к версионированию ресурса?",
     [("ETag", True), ("If-Match", True), ("RateLimit-Remaining", False), ("Retry-After", False)]),
    (S, "PUT без If-Match на /api/practice/resources вернёт...",
     [("428 Precondition Required", True), ("200 OK", False), ("500 Internal Error", False)]),
    (T, "Какой класс кодов означает ошибку клиента? Напишите одну цифру.", [("4", True)]),
    (S, "follow_redirects=False нужен, чтобы...",
     [("Тестировать редиректы явно", True), ("Отключить сеть", False),
      ("Ускорить парсинг JSON", False)]),
    (S, "Заголовок Idempotency-Key защищает от...",
     [("Дубля при повторе POST", True), ("Подслушивания", False),
      ("Превышения rate limit", False)]),
    (S, 'ETag "2" означает, что ресурс...', [("Обновлён дважды (version=2)", True),
      ("Существует 2 секунды", False), ("Весит 2 байта", False)]),
    (D, "Порядок CRUD-жизненного цикла",
     [("POST создать", True), ("GET прочитать", True), ("PUT обновить", True), ("DELETE удалить", True)]),
    (S, "Ответ 429 говорит тесту, что...", [("Сработал rate limit", True),
      ("Ресурс удалён", False), ("Неверный формат запроса", False)]),
    (S, "Повтор POST с тем же Idempotency-Key и другим телом вернёт...",
     [("409 Conflict — ключ занят другим payload", True), ("Новый ресурс", False),
      ("200 без изменений", False)]),
    (S, "Почему тест проверяет статус И тело И заголовки?",
     [("Контракт включает все три части ответа", True), ("Так требует OpenAPI", False),
      ("Иначе падает pytest-timeout", False)]),
])

# =========================== ТРЕК 4. API полигона ===========================
_desc("api_practice", [
    {"title": "Мишень /api/practice/status: матрица кодов", "category": "API", "price": 0,
     "description": (
         "GET /api/practice/status/{code} возвращает запрошенный код из разрешённого набора "
         "(200,201,202,204,400,401,403,404,409,422,429,500,503), неизвестный код → 422. Тело: "
         "{\"requested_status\": code, \"ok\": code < 400}. Идеальна для параметризации и "
         "негативных кейсов."
     )},
    {"title": "Ресурсы /api/practice/resources: полный CRUD", "category": "API", "price": 1990,
     "description": (
         "POST создаёт (201 + ETag \"1\"), PUT требует If-Match, DELETE даёт 204. Поля ресурса: "
         "name (обязательно), quantity, price, tags. extra=\"forbid\" — лишние поля дадут 422.\n\n"
         "Все данные живут в namespace вашего X-Test-Run-Id — тесты не мешают друг другу."
     )},
    {"title": "Список: пагинация, поиск и сортировка", "category": "API", "price": 1990,
     "description": (
         "GET /api/practice/resources?page=1&size=10&search=...&sort=name. Ответ: {items,total,"
         "page,size}. Проверяйте границы: size>50 → 422, пустая страница при total=0, сортировка "
         "-name по убыванию. Мутация pagination-ignore-size покажет баг — найдёт ли его ваш тест?"
     )},
    {"title": "Rate limit: заголовки и Retry-After", "category": "API", "price": 1990,
     "description": (
         "GET /api/practice/rate-limit?limit=N считает попытки вашего namespace: после N-й "
         "возвращается 429 с заголовками RateLimit-Limit/Remaining и Retry-After. Учитесь "
         "проверять лимиты без риска для реальных сервисов."
     )},
    {"title": "Cookies, redirects и async jobs", "category": "API", "price": 2990,
     "description": (
         "Три маленькие мишени — три больших темы: cookies set/read/delete проверяют работу с "
         "куками клиента; redirect/{hops} — цепочки перенаправлений; jobs — асинхронную задачу "
         "со статусами (создана → в работе → готово) через polling."
     )},
])

_pool("api_practice", [
    (S, "GET /api/practice/status/418 вернёт...",
     [("422 со списком поддерживаемых кодов", True), ("418 I'm a teapot", False),
      ("500", False)]),
    (S, "Какое поле ресурса обязательно при POST?",
     [("name", True), ("quantity", False), ("tags", False)]),
    (S, "POST ресурса с лишним полем extra=\"forbid\" вернёт...",
     [("422 Unprocessable Entity", True), ("201 Created", False), ("400 Bad Request", False)]),
    (T, "Какой заголовок изолирует данные ваших тестов? Напишите точное имя.",
     [("X-Test-Run-Id", True)]),
    (S, "Ответ списка /api/practice/resources содержит поля...",
     [("items, total, page, size", True), ("rows, count", False), ("data, meta, links", False)]),
    (S, "size=100 при максимуме 50 вернёт...",
     [("422", True), ("50 записей молча", False), ("200 и пустой список", False)]),
    (S, "После превышения лимита rate-limit ответ содержит заголовок...",
     [("Retry-After", True), ("Location", False), ("Set-Cookie", False)]),
    (S, "Параметр sort=-created_at означает...",
     [("Сортировку по убыванию даты создания", True), ("Фильтр старых записей", False),
      ("Обратную пагинацию", False)]),
    (M, "Какие статусы проходит async job до завершения?",
     [("Создана/в работе", True), ("Готова или упала", True), ("Всегда сразу 200 готово", False)]),
    (S, "DELETE /api/practice/state очищает...",
     [("Только данные вашего X-Test-Run-Id", True), ("Всю базу приложения", False),
      ("Куки браузера", False)]),
    (D, "Жизненный цикл async job",
     [("POST /jobs создать", True), ("Статус running", True), ("Статус completed", True)]),
    (S, "Цепочка redirect/{hops} полезна для проверки...",
     [("Что клиент корректно следует редиректам", True), ("Скорости DNS", False),
      ("Работы куки только", False)]),
    (S, "ETag после первого создания ресурса равен...",
     [('\"1\"', True), ('"0"', False), ("Отсутствует", False)]),
    (S, "Повторный GET удалённого ресурса даст...", [("404", True), ("204", False), ("410 навсегда", False)]),
])


# ========================= ТРЕК 5. Playwright UI ============================
_desc("playwright", [
    {"title": "Локаторы и data-testid", "category": "UI", "price": 0,
     "description": (
         "Стабильный селектор важнее красивого. У всех элементов полигона есть data-testid — "
         "используйте page.get_by_test_id(\"login-button\"). CSS/XPath по классам ломаются при "
         "первом редизайне. Все локаторы страницы можно подсмотреть во встроенной IDE (/ide)."
     )},
    {"title": "Первые UI-тесты на Playwright", "category": "UI", "price": 1990,
     "description": (
         "Фикстура page приходит из pytest-playwright:\n\n"
         "```python\npage.goto(f\"{base_url}/login\")\n"
         "page.get_by_test_id(\"email-input\").fill(\"user@test.com\")\n"
         "page.get_by_test_id(\"login-button\").click()\n"
         "page.wait_for_url(\"**/dashboard\")\n```\n\n"
         "Образец: ui/test_example_page_object.py и шаблон _task_template.py."
     )},
    {"title": "Web-first утверждения expect()", "category": "UI", "price": 1990,
     "description": (
         "expect(locator).to_be_visible() сам ждёт условие до таймаута — это замена sleep. "
         "Другие полезные: to_have_text, to_have_url, to_be_enabled, to_contain_text. "
         "Утверждения читаются как предложения и дают понятный отчёт при падении."
     )},
    {"title": "Ожидания: почему не нужен sleep", "category": "UI", "price": 2990,
     "description": (
         "sleep(3) = медленно И нестабильно. Правильные инструменты: auto-waiting локаторов, "
         "expect-утверждения, wait_for_url, wait_for_response для сетевых событий. "
         "Playwright ждёт элемент сам перед каждым действием."
     )},
    {"title": "Page Object Model", "category": "UI", "price": 2990,
     "description": (
         "Каждая страница — класс с локаторами и действиями; тесты читаются как сценарии. "
         "Готовый каркас в student_tests/ui/pages/ (BasePage + LoginPage). Правила: никаких "
         "assert в POM (кроме переиспользуемых), методы возвращают self или новую страницу."
     )},
])

_pool("playwright", [
    (S, "Какой локатор рекомендован для элементов полигона?",
     [("page.get_by_test_id(\"...\")", True), ("XPath по тексту заголовка", False),
      ("CSS по классам кнопок", False)]),
    (T, "Какой атрибут добавляют элементам для стабильных селекторов?",
     [("data-testid", True)]),
    (S, "Что делает expect(locator).to_be_visible()?",
     [("Ждёт видимость до таймаута, иначе падение", True), ("Проверяет мгновенно", False),
      ("Скрывает элемент", False)]),
    (M, "Какие ожидания есть в Playwright вместо sleep?",
     [("Auto-waiting перед действиями", True), ("wait_for_url", True),
      ("expect(...).to_have_text", True), ("time.sleep(5)", False)]),
    (S, "Фикстура login из student_tests/conftest.py...",
     [("Открывает /login, заполняет форму и ждёт /dashboard", True),
      ("Создаёт пользователя через API", False), ("Запускает браузер", False)]),
    (T, "Напишите метод page для клика по локатору.", [("click", True)]),
    (S, "Главная ценность Page Object Model:",
     [("Локаторы в одном месте, тесты читаются как сценарии", True),
      ("Тесты работают быстрее", False), ("Не нужны фикстуры", False)]),
    (S, "page.get_by_test_id(\"email-input\").fill(text) — что произойдёт?",
     [("Поле будет заполнено значением", True), ("Вернётся текущий текст поля", False),
      ("Нужен ещё и click", False)]),
    (D, "Порядок UI-теста входа",
     [("Открыть страницу /login", True), ("Заполнить email и пароль", True),
      ("Нажать кнопку входа", True), ("Дождаться дашборда", True)]),
    (S, "Почему CSS по классам вида .btn-primary хрупок?",
     [("Классы меняют при редизайне", True), ("Браузеры их не находят", False),
      ("Playwright запрещает CSS", False)]),
    (S, "Как проверить URL после перехода?",
     [("wait_for_url или expect(page).to_have_url", True), ("browser.url == ...", False),
      ("Только скриншотом", False)]),
    (S, "Команда установки браузеров Playwright:",
     [("playwright install chromium", True), ("pip install chromium", False),
      ("npm run browsers", False)]),
    (S, "POM-метод должен возвращать...",
     [("self, новую страницу или данные", True), ("Только None", False),
      ("HTML-код страницы", False)]),
    (M, "Что из этого — web-first утверждения?",
     [("to_be_visible", True), ("to_have_text", True), ("to_be_enabled", True),
      ("to_sleep_10s", False)]),
])


# ========================== ТРЕК 6. UI полигона =============================
_desc("ui_practice", [
    {"title": "Вход и регистрация через UI", "category": "UI", "price": 0,
     "description": (
         "Страницы /login и /register — базовые UI-задачи: позитивный сценарий, негативный "
         "(неверный пароль → login-error), выход. Демо-пользователь user@test.com / "
         "Password123!. Образец: ui/test_example_page_object.py."
     )},
    {"title": "Семантическая форма /practice/components", "category": "UI", "price": 0,
     "description": (
         "Страница-тренажёр форм: поля, чекбоксы, радио, select, дата. Учитесь заполнять разные "
         "типы контролов и проверять валидацию. Все элементы имеют data-testid — подсмотрите их "
         "в панели поиска локаторов встроенной IDE."
     )},
    {"title": "Динамический DOM и scoped-локаторы", "category": "UI", "price": 1990,
     "description": (
         "Элементы появляются и исчезают без перезагрузки. Приёмы: scoped-локаторы "
         "(container.get_by_test_id(...) ищет только внутри), фильтры filter(has_text=...), "
         ".first/.nth(). Никаких глобальных поисков «по всему DOM»."
     )},
    {"title": "Iframe, Shadow DOM и новые вкладки", "category": "UI", "price": 2990,
     "description": (
         "Продвинутый UI: frame_locator для iframe, shadow DOM Playwright пробивает обычными "
         "локаторами, новая вкладка ловится через context.expect_page. Всё это есть на "
         "/practice/components — задача «Iframe, Shadow DOM и новая вкладка»."
     )},
    {"title": "Доступность и клавиатура", "category": "UI", "price": 2990,
     "description": (
         "A11y: axe-core сканирует страницу (фикстура axe в conftest), клавиатурная навигация — "
         "Tab/Enter должны работать, у интерактивных элементов — роли и подписи. Задачи "
         "«Клавиатура и семантика», «Accessibility через axe-core»."
     )},
])

_pool("ui_practice", [
    (S, "Какой testid у кнопки входа на странице /login?",
     [("login-button", True), ("submit-btn", False), ("enter-click", False)]),
    (S, "После неверного пароля появится элемент с testid...",
     [("login-error", True), ("error-message", False), ("alert-danger", False)]),
    (S, "Поиск внутри конкретного контейнера — это...",
     [("Scoped-локатор: container.get_by_test_id(...)", True),
      ("Глобальный page.locator", False), ("XPath от body", False)]),
    (M, "Что умеет Playwright «из коробки»?",
     [("Пробивать shadow DOM обычными локаторами", True), ("Ловить новые вкладки", True),
      ("Чинить сломанные тесты", False), ("Рисовать скриншоты в терминал", False)]),
    (T, "Какой locator-механизм Playwright работает с iframe? Напишите двумя словами через _.",
     [("frame_locator", True)]),
    (S, "Фикстура axe из conftest нужна для...",
     [("Автоматических a11y-проверок страницы", True), ("Замера скорости", False),
      ("Параллельного запуска", False)]),
    (S, "Демо-пользователь полигона:",
     [("user@test.com / Password123!", True), ("admin/admin", False), ("qa/qa12345", False)]),
    (S, "Элемент появляется через 2 секунды после клика. Стратегия:",
     [("expect(element).to_be_visible() — сам подождёт", True),
      ("sleep(2) перед проверкой", False), ("Кликать повторно", False)]),
    (D, "Порядок работы с новой вкладкой",
     [("Открыть expect_page", True), ("Кликнуть ссылку", True),
      ("Переключиться на новую страницу", True), ("Работать в ней", True)]),
    (S, "Отфильтровать список карточек по тексту:",
     [("locator.filter(has_text=\"...\")", True), ("locator.remove_others()", False),
      ("page.search_text()", False)]),
    (S, "Клавиатурная навигация проверяется...",
     [("Tab/Enter с проверкой фокуса", True), ("Только мышью", False),
      ("Без участия браузера", False)]),
    (S, "Регистрация через UI требует...",
     [("Уникальный email + пароль по правилам формы", True), ("Любой email", False),
      ("Cookie админа", False)]),
    (M, "Какие проверки уместны для формы с валидацией?",
     [("Ошибка при пустом обязательном поле", True), ("Успех при валидных данных", True),
      ("Цвет рамки вне спецификации", False)]),
    (S, "iframe тестируется через...", [("page.frame_locator(...)", True),
      ("page.switch_to_iframe()", False), ("Отдельный браузер", False)]),
])

# ====================== ТРЕК 7. Данные и интеграции =========================
_desc("data_integrations", [
    {"title": "SQL для тестировщика", "category": "Database", "price": 0,
     "description": (
         "Минимум без которого никуда: SELECT, WHERE, ORDER BY, LIMIT, COUNT, JOIN. База "
         "полигона — PostgreSQL (в Docker-сети db:5432, на хосте localhost:5432 через override). "
         "Учимся формулировать запросы, которыми тест подтвердит состояние данных."
     )},
    {"title": "Проверка состояния БД после API-вызова", "category": "Database", "price": 1990,
     "description": (
         "Схема интеграционного теста: действие через API → проверка факта в БД → cleanup.\n\n"
         "```python\nuser = user_factory()               # API создал пользователя\n"
         "row = fetch_one('SELECT email FROM users WHERE id=%s', user['id'])\n"
         "assert row['email'] == user['email']\n```\n\nЗадача «API и состояние БД» из каталога."
     )},
    {"title": "Redis как кэш: что проверять", "category": "Redis", "price": 1990,
     "description": (
         "Кэш ломает наивное ожидание «сразу свежие данные». Тестируем: первый запрос идёт в "
         "источник, повторный — из кэша, инвалидация работает. Мишень /api/integrations/cache/* "
         "+ redis-клиент в фикстурах. Ключи кэша чистятся в teardown."
     )},
    {"title": "Очередь RQ: async end-to-end", "category": "Integrations", "price": 2990,
     "description": (
         "POST /api/integrations/jobs кладёт задачу в очередь Redis; worker (отдельный контейнер) "
         "выполняет её. Тест: создать задачу → polling статуса с таймаутом → проверить результат. "
         "Учитесь ждать асинхронность ограниченно, а не вечно."
     )},
    {"title": "WireMock: заглушки внешних сервисов", "category": "Integrations", "price": 2990,
     "description": (
         "Внешний сервис не должен быть зависимостью тестов — его подменяет WireMock (контейнер "
         "со стабами в wiremock/mappings). Тестируем /api/integrations/external/*: как "
         "приложение обрабатывает успех, задержку и ошибку заглушки."
     )},
])

_pool("data_integrations", [
    (T, "Какой SQL-оператор читает данные из таблицы?", [("SELECT", True)]),
    (S, "Как убедиться, что API действительно сохранил данные?",
     [("Прочитать запись напрямую из БД", True), ("Довериться ответу 200", False),
      ("Спросить менеджера", False)]),
    (M, "Что тестируют на кэше?",
     [("Первый запрос — источник, второй — кэш", True), ("Работу инвалидации", True),
      ("Цвет интерфейса", False), ("Только скорость сети", False)]),
    (S, "Worker в архитектуре полигона нужен для...",
     [("Выполнения задач из очереди Redis", True), ("Раздачи статики", False), ("Бэкапов", False)]),
    (S, "WireMock заменяет в тестах...", [("Внешний сторонний сервис заглушкой", True),
      ("Базу данных", False), ("Браузер", False)]),
    (D, "Порядок интеграционного теста",
     [("Подготовить данные через API", True), ("Проверить состояние в БД", True),
      ("Удалить тестовые данные", True)]),
    (S, "Хост PostgreSQL из контейнера приложения:", [("db:5432", True),
      ("localhost:5432 всегда", False), ("postgres.local", False)]),
    (S, "Polling статуса задачи завершается по...", [("Финальному статусу или таймауту", True),
      ("Первой проверке", False), ("Нажатию кнопки", False)]),
    (T, "Напишите SQL-слово для подсчёта строк.", [("COUNT", True), ("count", True)]),
    (S, "Почему кэш-тесты тоже чистят за собой?",
     [("Грязный кэш сломает следующий прогон", True), ("Redis платный", False),
      ("Так требует Jenkins", False)]),
    (S, "JOIN нужен, чтобы...", [("Соединить данные нескольких таблиц", True),
      ("Удалить строки", False), ("Создать индекс", False)]),
    (M, "Чем опасны реальные внешние сервисы в автотестах?",
     [("Недетерминированность ответов", True), ("Сбои вне вашего контроля", True),
      ("Они ускоряют прогоны", False)]),
    (S, "Стаб WireMock с задержкой помогает проверить...",
     [("Таймауты клиента и retry-политику", True), ("Рендеринг шрифтов", False),
      ("Работу cookie", False)]),
    (S, "integration_headers отличается от run_headers...",
     [("Другой namespace очистки (/api/integrations/state)", True),
      ("Ничем не отличается", False), ("Не делает teardown", False)]),
])

# ===================== ТРЕК 8. Контракты и надёжность =======================
_desc("contracts_reliability", [
    {"title": "JSON Schema и контрактный тест", "category": "Contract", "price": 1990,
     "description": (
         "Контрактный тест проверяет СТРУКТУРУ ответа, а не значения: типы полей, "
         "обязательность, формат. Мишень /api/practice/schema/{variant} выдаёт варианты "
         "stable/nullable/missing/wrong-type/extra — ваш тест должен ловить каждый дрейф схемы "
         "с помощью библиотеки jsonschema."
     )},
    {"title": "Совместимость API v1/v2", "category": "Contract", "price": 2990,
     "description": (
         "Клиенты старых версий не должны ломаться. /api/v1/courses и /api/v2/courses отвечают "
         "по-разному — контрактные тесты фиксируют различия и защищают v1 от случайной поломки "
         "при развитии v2. Задача «Совместимость API v1/v2»."
     )},
    {"title": "Retry, таймауты и fail-first", "category": "Reliability", "price": 2990,
     "description": (
         "Заголовки X-Playground-Scenario превращают нестабильность в управляемый эксперимент: "
         "slow (задержка из X-Playground-Latency-Ms), fail (стабильный 500), fail-first (503 "
         "один раз на X-Playground-Run), malformed-json. Пишите клиент с таймаутом и "
         "ограниченным retry — и тестируйте его поведение."
     )},
    {"title": "Параллельная изоляция данных", "category": "Reliability", "price": 2990,
     "description": (
         "pytest-xdist запускает тесты одновременно (-n 4). Без изоляции они воюют за общие "
         "данные. X-Test-Run-Id даёт каждому запуску свой namespace: create/read/delete не "
         "задевают чужих записей. Задача «Изоляция параллельных тестов»."
     )},
    {"title": "Mutation score: насколько хороши тесты", "category": "Reliability", "price": 2990,
     "description": (
         "Mutation testing специально ломает код (меняет == на !=, убирает проверки) и смотрит, "
         "поймали ли тесты. Выживший мутант = дыра в покрытии. На полигоне: GET "
         "/api/practice/mutations, tools/mutation_score.py, команда make mutation-score."
     )},
])

_pool("contracts_reliability", [
    (S, "Контрактный тест проверяет...", [("Структуру и типы ответа", True),
      ("Конкретное бизнес-значение поля", False), ("Скорость ответа", False)]),
    (S, "Вариант schema/wrong-type вернёт поле id...",
     [('Строкой "101" вместо числа', True), ("Отсутствующим", False), ("null", False)]),
    (M, "Какие дрейфы схемы должен ловить контрактный тест?",
     [("Поле пропало", True), ("Изменился тип", True), ("Поменялся цвет логотипа", False)]),
    (S, "Совместимость v1/v2 означает...", [("Старые клиенты продолжают работать", True),
      ("v1 удаляют сразу", False), ("Ответы совпадают байт в байт", False)]),
    (T, "Какой заголовок включает управляемые сценарии нестабильности?",
     [("X-Playground-Scenario", True)]),
    (S, "fail-first отличается от fail тем, что...",
     [("Падает только первый запрос данного X-Playground-Run", True),
      ("Падают все запросы", False), ("Падает сам pytest", False)]),
    (S, "X-Test-Run-Id решает проблему...", [("Параллельной войны за общие данные", True),
      ("Медленной сети", False), ("Ошибок компиляции", False)]),
    (S, "Выживший мутант — это...", [("Изменение кода, которое тесты не заметили", True),
      ("Упавший тест", False), ("Новый эндпоинт", False)]),
    (D, "Порядок mutation testing",
     [("Внести мутацию в код", True), ("Прогнать тесты", True),
      ("Проверить: упали ли тесты", True), ("Зафиксировать выжившего мутанта", True)]),
    (S, "malformed-json полезен для проверки...", [("Обработки некорректного тела клиентом", True),
      ("Валидации HTML", False), ("Кэширования", False)]),
    (S, "Инструмент полигона для расчёта mutation score:",
     [("tools/mutation_score.py", True), ("tools/check_progress.py", False), ("pytest --mutate", False)]),
    (M, "Что даёт изоляция X-Test-Run-Id?", [("Безопасный параллельный запуск", True),
      ("Безопасный повторный запуск", True), ("Автопочинку бага", False)]),
    (S, "jsonschema в student_tests нужен для...", [("Валидации структуры JSON-ответов", True),
      ("Генерации данных", False), ("Запуска браузера", False)]),
    (S, "Таймаут HTTP-клиента защищает от...", [("Вечного зависания запроса", True),
      ("Медленного DNS", False), ("Rate limit", False)]),
])

# ====================== ТРЕК 9. Безопасность и RBAC =========================
_desc("security_rbac", [
    {"title": "Жизненный цикл токена", "category": "Security", "price": 1990,
     "description": (
         "POST /api/auth/login выдаёт access-токен (короткая жизнь) и refresh (длинная). "
         "Тестируем: логин, доступ с токеном, истечение, refresh, logout. Токен — это JWT: "
         "подпись гарантирует подлинность; подделать без SECRET_KEY нельзя."
     )},
    {"title": "RBAC: матрица ролей ADMIN/MANAGER/USER", "category": "Security", "price": 2990,
     "description": (
         "Каждый эндпоинт требует роль. Матрица = таблица «роль × действие → ожидаемый код»: "
         "аноним — 401, USER на /api/admin/* — 403, MANAGER — по спецификации. Параметризованный "
         "тест пробегает всю матрицу за один файл. Задача «Матрица ролей RBAC»."
     )},
    {"title": "Границы входных данных", "category": "Security", "price": 1990,
     "description": (
         "Негативные кейсы: пустая строка, 101 символ там где максимум 100, отрицательная цена, "
         "лишние поля, не-JSON тело. Мишень /api/practice/resources даёт понятные 422 с описанием "
         "нарушения. Хороший тест знает границы валидации и проверяет обе стороны."
     )},
    {"title": "CORS preflight: что проверять", "category": "Security", "price": 2990,
     "description": (
         "Браузер перед «нестандартным» запросом шлёт OPTIONS preflight. Тестируем заголовки "
         "Access-Control-Allow-Origin/Methods/Headers. Мишень OPTIONS /api/practice/echo — "
         "задача «CORS preflight-контракт» уровня advanced."
     )},
    {"title": "Секреты и чувствительные данные", "category": "Security", "price": 2990,
     "description": (
         "Пароли и токены не должны попадать в Git, логи и Allure-вложения. В тестах берите "
         "учётки из переменных окружения (TEST_USER_EMAIL/TEST_USER_PASSWORD). Проверьте, что "
         "ответ API никогда не возвращает password_hash."
     )},
])

_pool("security_rbac", [
    (S, "401 вернут, когда...", [("Запрос без токена или токен просрочен", True),
      ("Роль недостаточна", False), ("Ресурс удалён", False)]),
    (S, "USER обратится к POST /api/admin/users. Ожидаемый код:",
     [("403 Forbidden", True), ("401 Unauthorized", False), ("201 Created", False)]),
    (T, "Какой тип токена используют для обновления доступа?",
     [("refresh", True), ("access", False), ("session", False)]),
    (M, "Что из этого — негативные граничные кейсы поля name (макс. 100 символов)?",
     [("Пустая строка", True), ("101 символ", True), ("Ровно 100 символов — это норма", False)]),
    (S, "Preflight-запрос отправляется методом...", [("OPTIONS", True), ("HEAD", False), ("GET", False)]),
    (S, "Access-Control-Allow-Origin отвечает за...",
     [("Разрешённые источники кросс-доменных запросов", True), ("Кэширование", False),
      ("Сжатие ответа", False)]),
    (S, "Пароли в автотестах правильнее всего...",
     [("Брать из переменных окружения", True), ("Хардкодить в репозитории", False),
      ("Шифровать XOR-ом", False)]),
    (D, "Порядок жизненного цикла доступа",
     [("Логин за учётную запись", True), ("Использовать access-токен", True),
      ("Refresh по истечении", True), ("Logout завершает сессию", True)]),
    (S, "JWT-подпись гарантирует...", [("Токен не подделан без секретного ключа", True),
      ("Шифрование содержимого", False), ("Анонимность пользователя", False)]),
    (S, "Ответ API никогда не должен содержать...", [("password_hash пользователя", True),
      ("email пользователя", False), ("имя курса", False)]),
    (S, "Матрица RBAC параметризуется по...", [("Парам «роль × эндпоинт»", True),
      ("Дате запуска", False), ("Имени файла", False)]),
    (S, "422 при невалидном теле полезнее 400, потому что...",
     [("Перечислены нарушенные поля", True), ("Он быстрее", False),
      ("Его проще игнорировать", False)]),
    (S, "Анонимный запрос к защищённому эндпоинту даст...", [("401", True), ("403", False), ("200", False)]),
    (S, "Фикстуры для тестов безопасности лежат в...",
     [("student_tests/conftest.py (auth_headers, user_factory)", True),
      (".env.example только", False), ("Jenkinsfile", False)]),
])

# ===================== ТРЕК 10. CI/CD и отчётность ==========================
_desc("cicd_reporting", [
    {"title": "Jenkins pipeline платформы: этапы", "category": "CI/CD", "price": 1990,
     "description": (
         "Пайплайн поднимает чистый стек, гонит юнит/API-тесты с coverage gate, затем e2e в "
         "трёх браузерах, потом ваши student_tests, mutation score — и всё это в Allure. "
         "Читается в Jenkinsfile: понимание этапов помогает интерпретировать красные сборки."
     )},
    {"title": "Allure: структура отчёта и шаги", "category": "Reporting", "price": 1990,
     "description": (
         "Allure превращает результаты pytest в отчёт: тесты, шаги, вложения, история. "
         "Результаты пишутся в allure-results (--alluredir), сервис :5050 рендерит их. "
         "Хорошие имена тестов + шаги = отчёт, по которому падение понятно без перезапуска."
     )},
    {"title": "Coverage gate: что измеряет покрытие", "category": "CI/CD", "price": 2990,
     "description": (
         "pytest-cov считает, какие строки приложения выполнили тесты; --cov-fail-under=70 "
         "валит прогон ниже порога. Важно: 100% покрытия не значит «нет багов», но падение "
         "gate значит «тесты не дотягиваются до кода». Локально: make test-quality."
     )},
    {"title": "Docker для автотестов: зачем и как", "category": "CI/CD", "price": 2990,
     "description": (
         "Jenkins запускает дочерние контейнеры через docker.sock хоста: python:3.12-slim для "
         "API-тестов, mcr.microsoft.com/playwright/python для UI. Тестовая среда воспроизводима "
         "и изолирована — тот же принцип легко повторить у себя."
     )},
    {"title": "Quality gates: блокируем merge правильно", "category": "CI/CD", "price": 2990,
     "description": (
         "Gate — автоматический критерий качества на пути изменений: зелёные тесты, покрытие, "
         "mutation score, отсутствие критичных замечаний линтера. На полигоне задача "
         "«Quality gates» учит формулировать такие критерии и проверять их скриптом."
     )},
])

_pool("cicd_reporting", [
    (S, "Что делает coverage gate --cov-fail-under=70?",
     [("Валит прогон при покрытии ниже 70%", True), ("Ускоряет тесты на 70%", False),
      ("Пропускает медленные тесты", False)]),
    (S, "Allure-отчёт строится из...", [("JSON-результатов в allure-results", True),
      ("Логов контейнера", False), ("README проекта", False)]),
    (M, "Какие этапы есть в Jenkinsfile полигона?",
     [("Юнит/API-тесты с coverage", True), ("E2E в трёх браузерах", True),
      ("Mutation score", True), ("Ручное тестирование менеджером", False)]),
    (S, "UI-тесты в Jenkins запускаются в контейнере...",
     [("mcr.microsoft.com/playwright/python", True), ("python:3.12-slim", False),
      ("postgres:17-alpine", False)]),
    (T, "Команда локального прогона с coverage gate:", [("make test-quality", True)]),
    (S, "Quality gate — это...", [("Автоматический критерий качества на пути изменений", True),
      ("Отчёт для заказчика", False), ("Тип браузера", False)]),
    (D, "Порядок пайплайна платформы",
     [("Поднять чистый стек", True), ("Юнит/API-тесты", True),
      ("E2E и student_tests", True), ("Опубликовать Allure-отчёт", True)]),
    (S, "Почему 100% покрытия не гарантирует отсутствие багов?",
     [("Покрытие меряет выполнение строк, а не корректность проверок", True),
      ("Покрытие считает только UI-тесты", False), ("Такое невозможно технически", False)]),
    (S, "docker.sock проброшен в Jenkins для...", [("Запуска дочерних контейнеров тестов", True),
      ("Доступа в интернет", False), ("Хранения артефактов", False)]),
    (S, "История результатов между сборками сохраняется благодаря...",
     [("Именованному тому quality_history с фиксированным именем", True),
      ("Перезаписи логов", False), ("Git-тегам", False)]),
    (M, "Что стоит блокировать merge?",
     [("Красные тесты", True), ("Провал coverage gate", True), ("Стиль коммит-сообщений", False)]),
    (S, "allure-results добавлен в .gitignore, потому что...",
     [("Это генерируемые артефакты прогона", True), ("Они содержат секреты", False),
      ("git не умеет JSON", False)]),
    (S, "Версия приложения в /health берётся из...", [("Git-тега при сборке образа", True),
      ("CHANGELOG.md", False), ("Файла version.txt", False)]),
    (S, "make up поднимает стек командой...", [("docker compose up -d --build", True),
      ("kubectl apply", False), ("ansible-playbook site.yml", False)]),
])


