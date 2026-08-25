"""ОБРАЗЕЦ: базовые приёмы API-автотестов на учебных мишенях.

Это работающий тест — можно запускать как есть и использовать как шпаргалку.
Скопируйте приёмы в свои файлы (test_<task>.py), но не редактируйте образец.

Продемонстрировано:
1. параметризация одного теста множеством входов (@pytest.mark.parametrize);
2. изоляция изменяемых данных через фикстуру run_headers (X-Test-Run-Id);
3. полный жизненный цикл ресурса: create -> read -> update -> delete;
4. проверка заголовков ответа (ETag), а не только тела и статуса.

Запуск: BASE_URL=http://localhost:8000 python -m pytest student_tests/api/test_example_api_patterns.py -v
"""
import pytest


# --- 1. Параметризация: один тест = много кейсов ----------------------------
# Мишень GET /api/practice/status/{code} возвращает запрошенный HTTP-статус.
# Один параметризованный тест заменяет десяток copy-paste тестов; при падении
# pytest покажет, какой именно набор [code, ok] сломался.
@pytest.mark.api
@pytest.mark.parametrize(
    ("code", "ok"),
    [
        pytest.param(200, True, id="ok"),
        pytest.param(201, True, id="created"),
        pytest.param(400, False, id="bad-request"),
        pytest.param(404, False, id="not-found"),
        pytest.param(500, False, id="server-error"),
    ],
)
def test_status_endpoint_returns_requested_code(api_client, code: int, ok: bool):
    response = api_client.get(f"/api/practice/status/{code}")

    assert response.status_code == code
    if response.status_code != 204:  # у 204 нет тела по стандарту HTTP
        body = response.json()
        assert body["requested_status"] == code
        assert body["ok"] is ok


# Неподдерживаемый код — отдельный негативный сценарий со своим контрактом.
@pytest.mark.api
def test_status_endpoint_rejects_unknown_code(api_client):
    response = api_client.get("/api/practice/status/418")  # I'm a teapot не в списке

    assert response.status_code == 422
    assert "Supported status codes" in response.json()["detail"]


# --- 2-4. Жизненный цикл ресурса с проверкой заголовков ---------------------
# run_headers выдаёт каждому запуску тестов уникальный namespace, поэтому:
# - повторный запуск безопасен (нет «мусора» от прошлых прогонов);
# - параллельный запуск (pytest-xdist) не конфликтует;
# - после теста фикстура сама удаляет данные через DELETE /api/practice/state.
@pytest.mark.api
def test_resource_lifecycle_crud(api_client, run_headers):
    # CREATE: обязательное поле name, остальные у POST — опциональные.
    # Для UPDATE тот же набор полей уже обязателен целиком (см. схему ниже),
    # поэтому сразу описываем ресурс полностью.
    payload = {"name": f"example-{run_headers['X-Test-Run-Id'][:8]}", "quantity": 3, "price": 9.9}
    created = api_client.post("/api/practice/resources", headers=run_headers, json=payload)

    assert created.status_code == 201
    resource = created.json()
    resource_id = resource["id"]
    assert resource["name"] == payload["name"]
    assert resource["version"] == 1

    # READ: сервер отдаёт версию ресурса в заголовке ETag — это пригодится
    # для optimistic locking (см. задачу про конкурентное изменение).
    read = api_client.get(f"/api/practice/resources/{resource_id}", headers=run_headers)

    assert read.status_code == 200
    assert read.headers["ETag"] == '"1"'

    # UPDATE без If-Match сервер запрещает (428 Precondition Required) —
    # контракт требует явной оптимистичной блокировки.
    no_precondition = api_client.put(
        f"/api/practice/resources/{resource_id}", headers=run_headers, json=payload
    )
    assert no_precondition.status_code == 428

    # UPDATE с актуальным ETag проходит и наращивает версию.
    updated = api_client.put(
        f"/api/practice/resources/{resource_id}",
        headers={**run_headers, "If-Match": '"1"'},
        json={**payload, "quantity": 5},
    )

    assert updated.status_code == 200
    assert updated.json()["version"] == 2
    assert updated.json()["quantity"] == 5

    # DELETE: затем повторный READ подтверждает фактическое удаление.
    deleted = api_client.delete(f"/api/practice/resources/{resource_id}", headers=run_headers)
    missing = api_client.get(f"/api/practice/resources/{resource_id}", headers=run_headers)

    assert deleted.status_code == 204
    assert missing.status_code == 404
