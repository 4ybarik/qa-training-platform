"""Сохраняет архивные учебные данные и нормализует legacy-ограничение."""
from alembic import op
import sqlalchemy as sa


revision = "20260827_02"
down_revision = "20260827_01"
branch_labels = None
depends_on = None


def _postgres_constraint_exists(name: str) -> bool:
    bind = op.get_bind()
    return bool(bind.scalar(sa.text(
        "SELECT 1 FROM pg_constraint WHERE conrelid = 'enrollments'::regclass "
        "AND conname = :name"
    ), {"name": name}))


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    # Старый create_all создавал уникальный индекс, а актуальная ORM-модель
    # описывает UNIQUE constraint. PostgreSQL умеет принять существующий индекс
    # как backing index ограничения без перестроения таблицы и потери данных.
    name = "uq_enrollment_user_course"
    if not _postgres_constraint_exists(name):
        op.execute(sa.text(
            "ALTER TABLE enrollments ADD CONSTRAINT uq_enrollment_user_course "
            "UNIQUE USING INDEX uq_enrollment_user_course"
        ))


def downgrade() -> None:
    # Обратное преобразование ограничения в самостоятельный индекс потребовало
    # бы его перестройки. Это compatibility-миграция без изменения данных,
    # поэтому безопасный downgrade намеренно не меняет схему.
    pass
