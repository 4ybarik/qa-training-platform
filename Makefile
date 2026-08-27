.PHONY: up down logs seed migrate migration-check test test-quality e2e e2e-cross-browser student-api student-ui \
	student-ui-cross-browser student-all mutation-score performance quality-summary progress \
	watch-api watch-ui fmt version

up:            ## поднять стек (app + postgres), версия подставляется из Git-тега
	APP_VERSION=$$(git describe --tags --always --dirty 2>/dev/null || echo 0.0.0-dev) docker compose up -d --build

down:          ## остановить стек
	docker compose down

logs:          ## логи приложения
	docker compose logs -f app

seed:          ## загрузить демо-данные вручную
	docker compose exec app python -m app.seed

seed-reset:    ## пересоздать учебный контент (курсы/экзамены/вопросы), пользователи сохраняются
	docker compose exec app python -m app.seed --reset-content

migrate:       ## применить миграции схемы БД
	docker compose exec app python -m app.db_upgrade

migration-check: ## проверить, что ORM и последняя миграция не расходятся
	cd backend && python -m pytest tests/test_migrations.py -q

test:          ## юнит/API-тесты (SQLite, без Docker)
	cd backend && python -m pytest

test-quality:  ## статические проверки и coverage gate как в CI
	cd backend && ruff check app tests
	cd backend && python -m pytest --cov=app --cov-report=term-missing --cov-fail-under=70

e2e:           ## E2E Playwright (требуется запущенный сервер на :8000)
	cd e2e && python -m pytest

e2e-cross-browser: ## Reference E2E в Chromium, Firefox и WebKit
	cd e2e && python -m pytest --browser chromium --browser firefox --browser webkit

student-api:   ## пользовательские API/contract/integration-тесты
	BASE_URL=$${BASE_URL:-http://localhost:8000} python -m pytest student_tests/api student_tests/contract student_tests/integration

student-ui:    ## пользовательские UI-тесты Playwright
	BASE_URL=$${BASE_URL:-http://localhost:8000} python -m pytest student_tests/ui

student-ui-cross-browser: ## пользовательские UI-тесты во всех браузерах
	BASE_URL=$${BASE_URL:-http://localhost:8000} python -m pytest student_tests/ui \
		--browser chromium --browser firefox --browser webkit

student-all: student-api student-ui ## все пользовательские тесты

mutation-score: ## контролируемые дефекты и mutation score
	python tools/mutation_score.py --config student_tests/mutations.json

performance: ## короткий Locust smoke с p95-gate
	locust -f performance/locustfile.py --headless \
		--host $${BASE_URL:-http://localhost:8000} -u 5 -r 5 -t 20s

quality-summary: ## собрать сводку текущих CI-артефактов
	python tools/build_quality_summary.py --artifacts ci-artifacts

progress:      ## показать, какие задачи каталога уже начаты
	python tools/check_progress.py

watch-api:     ## автоперезапуск API/contract-тестов при каждом сохранении файла
	BASE_URL=$${BASE_URL:-http://localhost:8000} \
	STUDENT_TEST_PATHS="student_tests/api student_tests/contract" \
	python -m pytest_watcher student_tests --now --runner tools/ptw_runner.sh

watch-ui:      ## автоперезапуск UI-тестов при каждом сохранении файла
	BASE_URL=$${BASE_URL:-http://localhost:8000} \
	STUDENT_TEST_PATHS="student_tests/ui" \
	python -m pytest_watcher student_tests --now --runner tools/ptw_runner.sh

version:       ## показать версию, которая будет подставлена при следующей сборке
	@git describe --tags --always --dirty 2>/dev/null || echo "0.0.0-dev (нет тегов в репозитории)"
