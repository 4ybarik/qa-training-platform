"""Безопасно обновляет пустую или существующую legacy-базу через Alembic."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.core.database import engine


BASELINE_REVISION = "20260827_00"


def upgrade() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "migrations"))
    inspector = inspect(engine)
    if inspector.has_table("users") and not inspector.has_table("alembic_version"):
        command.stamp(config, BASELINE_REVISION)
    command.upgrade(config, "head")


if __name__ == "__main__":
    upgrade()
