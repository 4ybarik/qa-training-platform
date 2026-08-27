"""Полная схема платформы до появления учебного прогресса."""
from alembic import op
import sqlalchemy as sa


revision = "20260827_00"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    role = sa.Enum("ADMIN", "MANAGER", "USER", name="role")
    course_status = sa.Enum("DRAFT", "PUBLISHED", "ARCHIVED", name="coursestatus")
    question_type = sa.Enum("SINGLE", "MULTI", "TEXT", "DND", name="questiontype")
    notification_status = sa.Enum("UNREAD", "READ", name="notificationstatus")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("role", role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_table(
        "profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("phone", sa.String(50)),
        sa.Column("birthday", sa.Date()),
        sa.Column("address", sa.String(255)),
        sa.Column("avatar_url", sa.String(500)),
        sa.Column("skills", sa.Text()),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("status", course_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_courses_title", "courses", ["title"])
    op.create_index("ix_courses_category", "courses", ["category"])
    op.create_table(
        "enrollments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "course_id", name="uq_enrollment_user_course"),
    )
    op.create_table(
        "exams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
    )
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("type", question_type, nullable=False),
    )
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("questions.id"), nullable=False),
        sa.Column("answer", sa.String(500), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
    )
    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.String(500), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("payload", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "exam_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("exam_id", sa.Integer(), sa.ForeignKey("exams.id"), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_exam_attempts_user_id", "exam_attempts", ["user_id"])
    op.create_index("ix_exam_attempts_exam_id", "exam_attempts", ["exam_id"])
    op.create_table(
        "test_run_entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("run_id", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "entity_type", "entity_id", name="uq_test_run_entity"),
    )
    op.create_index("ix_test_run_entities_run_id", "test_run_entities", ["run_id"])


def downgrade() -> None:
    op.drop_index("ix_test_run_entities_run_id", table_name="test_run_entities")
    op.drop_table("test_run_entities")
    op.drop_index("ix_exam_attempts_exam_id", table_name="exam_attempts")
    op.drop_index("ix_exam_attempts_user_id", table_name="exam_attempts")
    op.drop_table("exam_attempts")
    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("exams")
    op.drop_table("enrollments")
    op.drop_index("ix_courses_category", table_name="courses")
    op.drop_index("ix_courses_title", table_name="courses")
    op.drop_table("courses")
    op.drop_table("profiles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
