# Каталог практических проверок

Это не курс и не набор уроков. Документ перечисляет задачи, для которых ученик
сам проектирует и пишет автотесты в локальной IDE. Актуальные критерии каждой
задачи доступны в UI `/practice` и через `GET /api/practice/catalog`.

## Рабочий контракт

- решения находятся только в `student_tests/`;
- файл решения называется `test_*.py`;
- адрес приложения читается из `BASE_URL`;
- изменяемые practice-данные изолируются заголовком `X-Test-Run-Id`;
- `DELETE /api/practice/state` удаляет только временные данные текущего запуска;
- Jenkins автоматически запускает новые тесты и публикует Allure-результаты;
- эталонные тесты `backend/tests` и `e2e` не являются решениями задач.

## API и контракты

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| Контракт echo-запроса | `GET/POST /api/practice/echo` | `api/test_echo_contract.py` | basic |
| Матрица HTTP-статусов | `GET /api/practice/status/{code}` | `api/test_status_matrix.py` | basic |
| Негативные варианты схемы | `GET /api/practice/schema/{variant}` | `contract/test_schema_variants.py` | intermediate |
| Полный CRUD ресурса | `/api/practice/resources` | `api/test_resource_crud.py` | intermediate |
| Пагинация, сортировка и поиск | `GET /api/practice/resources` | `api/test_resource_list.py` | intermediate |
| Идемпотентность и optimistic locking — контроль конкурентного изменения | `/api/practice/resources` | `api/test_resource_concurrency.py` | advanced |

## Аутентификация и безопасность

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| Жизненный цикл токена | `/api/auth/*`, `/api/profile` | `api/test_auth_lifecycle.py` | intermediate |
| Матрица ролей RBAC — управление доступом на основе ролей | `/api/admin/*` | `api/test_rbac_matrix.py` | intermediate |
| Cookie-сессия | `/api/practice/cookies/*` | `api/test_cookies.py` | basic |
| Границы входных данных | `POST /api/practice/resources` | `api/test_input_boundaries.py` | intermediate |
| Ограничение частоты запросов | `GET /api/practice/rate-limit` | `api/test_rate_limit.py` | intermediate |
| CORS preflight-контракт | `OPTIONS /api/practice/echo` | `contract/test_cors_preflight.py` | advanced |

## UI и Playwright

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| Вход через UI | `/login` | `ui/test_login.py` | basic |
| Семантическая форма | `/practice/components` | `ui/test_semantic_form.py` | basic |
| Динамический DOM без `sleep` | `/practice/components` | `ui/test_dynamic_content.py` | intermediate |
| Строгие scoped-локаторы — поиск внутри заданного контейнера | `/practice/components` | `ui/test_scoped_locators.py` | intermediate |
| Iframe, Shadow DOM и новая вкладка | `/practice/components` | `ui/test_browser_contexts.py` | advanced |
| Адаптивность и визуальные состояния | `/practice/components` | `ui/test_responsive.py` | advanced |
| Клавиатура и семантика доступности | `/practice/components` | `ui/test_accessibility.py` | intermediate |

## Интеграции и данные

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| API и состояние БД | регистрация + PostgreSQL | `integration/test_database_state.py` | intermediate |
| Polling асинхронной задачи | `/api/practice/jobs` | `integration/test_async_job.py` | intermediate |
| Загрузка и скачивание файла | `/api/practice/files` | `integration/test_file_roundtrip.py` | intermediate |
| Цепочка redirects — перенаправлений | `/api/practice/redirect/{hops}` | `api/test_redirects.py` | basic |
| События WebSocket | `/ws/notifications` | `integration/test_websocket.py` | advanced |
| Регистратор webhook | `/api/practice/webhooks` | `integration/test_webhook_recorder.py` | advanced |

## Надёжность и CI

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| Контролируемый retry — повтор запроса | `X-Playground-Scenario: fail-first` | `api/test_retry_policy.py` | advanced |
| Таймаут и повреждённый JSON | `slow`, `malformed-json` | `api/test_failure_modes.py` | intermediate |
| Изоляция параллельных тестов | `/api/practice/resources` | `integration/test_parallel_isolation.py` | advanced |
| Диагностика в Allure | Jenkins + Allure | `ui/test_end_to_end.py` | intermediate |
| Quality gates — блокирующие критерии качества | `student_tests/**/test_*.py` | `api/test_ci_discovery.py` | advanced |

## Бизнес-процессы

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| Регистрация через UI | `/register` | `ui/test_registration.py` | basic |
| Сброс пароля | `/forgot-password` | `ui/test_password_reset.py` | intermediate |
| Профиль и аватар | `/profile` | `ui/test_profile_avatar.py` | intermediate |
| Уведомления и infinite scroll | `/notifications` | `ui/test_notifications.py` | intermediate |
| Администрирование пользователей | `/admin`, `/api/admin/*` | `ui/test_admin_users.py` | advanced |
| Жизненный цикл курса | `/api/courses`, `/courses` | `api/test_course_lifecycle.py` | advanced |
| Конкурентная запись на курс | `POST /api/courses/{id}/enroll` | `integration/test_enrollment_race.py` | advanced |
| Подсчёт результата экзамена | `/api/exams/*` | `api/test_exam_scoring.py` | advanced |
| Согласованность аудита | `/api/admin/audit`, PostgreSQL | `integration/test_audit_consistency.py` | advanced |
| Сквозная локализация RU/EN | `POST /web/language` | `ui/test_localization.py` | intermediate |

## Инженерные quality gates

| Задача | Мишень | Рекомендуемый файл | Уровень |
|---|---|---|---|
| Mutation score | `GET /api/practice/mutations` | `mutations.json` | advanced |
| Test Data API | `/api/test-support/*` | `integration/test_test_data_api.py` | intermediate |
| Совместимость API v1/v2 | `/api/v1/courses`, `/api/v2/courses` | `contract/test_api_versions.py` | advanced |
| Redis cache | `/api/integrations/cache/*` | `integration/test_redis_cache.py` | intermediate |
| Реальная RQ-очередь | `/api/integrations/jobs` | `integration/test_rq_jobs.py` | advanced |
| Внешний сервис WireMock | `/api/integrations/external/*` | `integration/test_external_service.py` | advanced |
| Accessibility через axe-core | UI + axe-core | `ui/test_accessibility.py` | advanced |
| Нагрузочный p95 gate | `performance/locustfile.py` | `performance/locustfile.py` | advanced |

## Детерминированные сценарии нестабильности

Их можно применить к любому `/api/*` запросу:

| Заголовок `X-Playground-Scenario` | Поведение |
|---|---|
| `slow` | задержка из `X-Playground-Latency-Ms` |
| `fail` | стабильный `500` |
| `fail-first` | первый запрос для уникального `X-Playground-Run` даёт `503`, следующий проходит |
| `malformed-json` | ответ `200` с намеренно повреждённым JSON |

Вероятностный chaos-режим на `/playground` оставлен отдельной мишенью, но для
проверки retry и таймаутов предпочтительны детерминированные заголовки.

## Критерий завершения любой задачи

- тест воспроизводимо проходит локально и в Jenkins;
- тест падает при нарушении заявленного контракта;
- данные изолированы, повторный запуск безопасен;
- имя и отчёт объясняют проверяемое поведение;
- диагностика достаточна для разбора сбоя без повторного ручного прогона;
- секреты и персональные данные не попадают в Git, логи и Allure.
