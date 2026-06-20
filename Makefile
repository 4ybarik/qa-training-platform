.PHONY: up down logs seed test e2e fmt version

up:            ## поднять стек (app + postgres), версия подставляется из Git-тега
	APP_VERSION=$$(git describe --tags --always --dirty 2>/dev/null || echo 0.0.0-dev) docker compose up -d --build

down:          ## остановить стек
	docker compose down

logs:          ## логи приложения
	docker compose logs -f app

seed:          ## загрузить демо-данные вручную
	docker compose exec app python -m app.seed

test:          ## юнит/API-тесты (SQLite, без Docker)
	cd backend && python -m pytest

e2e:           ## E2E Playwright (требуется запущенный сервер на :8000)
	cd e2e && python -m pytest

version:       ## показать версию, которая будет подставлена при следующей сборке
	@git describe --tags --always --dirty 2>/dev/null || echo "0.0.0-dev (нет тегов в репозитории)"
