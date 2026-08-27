"""История запусков, критерии и прогресс практики."""
from alembic import op
import sqlalchemy as sa


revision = "20260827_01"
down_revision = "20260827_00"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "practice_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("challenge_slug", sa.String(100), nullable=False),
        sa.Column("file_path", sa.String(300), nullable=False),
        sa.Column("source_hash", sa.String(64), nullable=False),
        sa.Column("exit_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("tests_collected", sa.Integer(), nullable=False),
        sa.Column("tests_passed", sa.Integer(), nullable=False),
        sa.Column("tests_failed", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("output", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_practice_runs_user_id", "practice_runs", ["user_id"])
    op.create_index("ix_practice_runs_challenge_slug", "practice_runs", ["challenge_slug"])
    op.create_table(
        "practice_criterion_results",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.Integer(), sa.ForeignKey("practice_runs.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(100), nullable=False),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("details", sa.Text(), nullable=False),
        sa.UniqueConstraint("run_id", "position", name="uq_practice_run_criterion"),
    )
    op.create_index(
        "ix_practice_criterion_results_run_id", "practice_criterion_results", ["run_id"]
    )
    op.create_table(
        "practice_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("challenge_slug", sa.String(100), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("best_score", sa.Integer(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("last_run_id", sa.Integer(), sa.ForeignKey("practice_runs.id")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("user_id", "challenge_slug", name="uq_practice_progress_user_challenge"),
    )
    op.create_index("ix_practice_progress_user_id", "practice_progress", ["user_id"])
    op.create_index(
        "ix_practice_progress_challenge_slug", "practice_progress", ["challenge_slug"]
    )


def downgrade() -> None:
    op.drop_index("ix_practice_progress_challenge_slug", table_name="practice_progress")
    op.drop_index("ix_practice_progress_user_id", table_name="practice_progress")
    op.drop_table("practice_progress")
    op.drop_index("ix_practice_criterion_results_run_id", table_name="practice_criterion_results")
    op.drop_table("practice_criterion_results")
    op.drop_index("ix_practice_runs_challenge_slug", table_name="practice_runs")
    op.drop_index("ix_practice_runs_user_id", table_name="practice_runs")
    op.drop_table("practice_runs")
