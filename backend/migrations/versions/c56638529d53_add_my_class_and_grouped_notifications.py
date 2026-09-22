"""add my class and grouped notifications

Revision ID: c56638529d53
Revises: 7ac32f6e9b14
Create Date: 2026-09-22 20:33:53.031026

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "c56638529d53"
down_revision = "7ac32f6e9b14"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "class_students",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=True),
        sa.Column("admin_id", sa.Integer(), nullable=True),
        sa.Column("student_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "(teacher_id IS NULL) != (admin_id IS NULL)",
            name=op.f("ck_class_students_one_class_owner"),
        ),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admins.id"],
            name=op.f("fk_class_students_admin_id_admins"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name=op.f("fk_class_students_student_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            name=op.f("fk_class_students_teacher_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_class_students")),
        sa.UniqueConstraint("admin_id", "student_id", name="class_admin_student"),
        sa.UniqueConstraint("teacher_id", "student_id", name="class_teacher_student"),
    )
    with op.batch_alter_table("class_students", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_class_students_admin_id"), ["admin_id"], unique=False)
        batch_op.create_index(
            batch_op.f("ix_class_students_student_id"), ["student_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_class_students_teacher_id"), ["teacher_id"], unique=False
        )

    op.create_table(
        "class_notification_dispatches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("payload_sha256", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "processing",
                "retry",
                "sent",
                "permanent_failed",
                "cancelled",
                name="reminderstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_status", sa.SmallInteger(), nullable=True),
        sa.Column("last_error", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["edition_id"],
            ["olympiad_editions.id"],
            name=op.f("fk_class_notification_dispatches_edition_id_olympiad_editions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["teacher_id"],
            ["users.id"],
            name=op.f("fk_class_notification_dispatches_teacher_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_class_notification_dispatches")),
        sa.UniqueConstraint(
            "idempotency_key", name=op.f("uq_class_notification_dispatches_idempotency_key")
        ),
        sa.UniqueConstraint(
            "teacher_id", "edition_id", "scheduled_for", name="class_daily_edition"
        ),
    )
    with op.batch_alter_table("class_notification_dispatches", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_class_notification_dispatches_next_attempt_at"),
            ["next_attempt_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_class_notification_dispatches_scheduled_for"),
            ["scheduled_for"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_class_notification_dispatches_status"), ["status"], unique=False
        )



def downgrade():
    with op.batch_alter_table("class_notification_dispatches", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_class_notification_dispatches_status"))
        batch_op.drop_index(batch_op.f("ix_class_notification_dispatches_scheduled_for"))
        batch_op.drop_index(batch_op.f("ix_class_notification_dispatches_next_attempt_at"))

    op.drop_table("class_notification_dispatches")
    with op.batch_alter_table("class_students", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_class_students_teacher_id"))
        batch_op.drop_index(batch_op.f("ix_class_students_student_id"))
        batch_op.drop_index(batch_op.f("ix_class_students_admin_id"))

    op.drop_table("class_students")
