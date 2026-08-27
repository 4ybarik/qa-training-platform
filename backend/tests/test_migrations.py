"""Миграции создают новую БД и безопасно подхватывают legacy-схему."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys


BACKEND_DIR = Path(__file__).resolve().parents[1]


def _run(*args: str, database_url: str) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": database_url}
    return subprocess.run(
        [sys.executable, *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_fresh_migrations_reach_head_and_match_models(tmp_path):
    database = tmp_path / "fresh.db"
    url = f"sqlite:///{database}"

    upgraded = _run("-m", "app.db_upgrade", database_url=url)
    checked = _run("-m", "alembic", "check", database_url=url)

    assert upgraded.returncode == 0, upgraded.stderr
    assert checked.returncode == 0, checked.stdout + checked.stderr
    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        tables = {
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
    assert revision == "20260827_02"
    assert {"users", "practice_runs", "practice_criterion_results", "practice_progress"} <= tables


def test_legacy_database_is_stamped_without_losing_data(tmp_path):
    database = tmp_path / "legacy.db"
    url = f"sqlite:///{database}"
    baseline = _run("-m", "alembic", "upgrade", "20260827_00", database_url=url)
    assert baseline.returncode == 0, baseline.stderr

    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO users "
            "(email,password_hash,first_name,last_name,role,is_active,created_at) "
            "VALUES (?,?,?,?,?,?,?)",
            ("keep@example.com", "hash", "Keep", "Me", "USER", 1, "2026-08-27"),
        )
        connection.execute("DROP TABLE alembic_version")
        connection.execute(
            "CREATE TABLE lesson_progress "
            "(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, lesson_slug TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO lesson_progress (user_id, lesson_slug) VALUES (1, 'legacy-lesson')"
        )
        connection.execute(
            "CREATE TABLE lab_submissions "
            "(id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, lab_slug TEXT NOT NULL)"
        )
        connection.execute(
            "INSERT INTO lab_submissions (user_id, lab_slug) VALUES (1, 'legacy-lab')"
        )
        connection.commit()

    upgraded = _run("-m", "app.db_upgrade", database_url=url)
    checked = _run("-m", "alembic", "check", database_url=url)
    assert upgraded.returncode == 0, upgraded.stderr
    assert checked.returncode == 0, checked.stdout + checked.stderr
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT email FROM users").fetchone()[0] == "keep@example.com"
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone()[0] == "20260827_02"
        assert connection.execute(
            "SELECT lesson_slug FROM lesson_progress"
        ).fetchone()[0] == "legacy-lesson"
        assert connection.execute(
            "SELECT lab_slug FROM lab_submissions"
        ).fetchone()[0] == "legacy-lab"
