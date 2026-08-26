"""add durable reminder dispatch outbox

Revision ID: c4b73de91f20
Revises: a71d3f82c904
Create Date: 2026-08-26 12:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "c4b73de91f20"
down_revision = "a71d3f82c904"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "reminder_dispatches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("event_on", sa.Date(), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("days_before", sa.SmallInteger(), nullable=False),
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
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "attempt_count >= 0",
            name=op.f("ck_reminder_dispatches_nonnegative_attempt_count"),
        ),
        sa.CheckConstraint(
            "days_before BETWEEN 0 AND 90",
            name=op.f("ck_reminder_dispatches_valid_reminder_days_before"),
        ),
        sa.CheckConstraint(
            "length(idempotency_key) BETWEEN 8 AND 128",
            name=op.f("ck_reminder_dispatches_valid_idempotency_key_length"),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["user_olympiad_plans.id"],
            name=op.f("fk_reminder_dispatches_plan_id_user_olympiad_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["stages.id"],
            name=op.f("fk_reminder_dispatches_stage_id_stages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reminder_dispatches")),
        sa.UniqueConstraint("idempotency_key", name=op.f("uq_reminder_dispatches_idempotency_key")),
        sa.UniqueConstraint(
            "plan_id",
            "stage_id",
            "event_on",
            "days_before",
            name="reminder_plan_stage_event_day",
        ),
    )
    with op.batch_alter_table("reminder_dispatches", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_reminder_dispatches_next_attempt_at"),
            ["next_attempt_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_reminder_dispatches_plan_id"), ["plan_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_reminder_dispatches_scheduled_for"),
            ["scheduled_for"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_reminder_dispatches_stage_id"), ["stage_id"], unique=False
        )
        batch_op.create_index(
            batch_op.f("ix_reminder_dispatches_status"), ["status"], unique=False
        )


def downgrade():
    with op.batch_alter_table("reminder_dispatches", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_reminder_dispatches_status"))
        batch_op.drop_index(batch_op.f("ix_reminder_dispatches_stage_id"))
        batch_op.drop_index(batch_op.f("ix_reminder_dispatches_scheduled_for"))
        batch_op.drop_index(batch_op.f("ix_reminder_dispatches_plan_id"))
        batch_op.drop_index(batch_op.f("ix_reminder_dispatches_next_attempt_at"))
    op.drop_table("reminder_dispatches")
