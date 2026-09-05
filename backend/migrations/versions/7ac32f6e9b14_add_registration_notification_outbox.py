"""add registration notification outbox

Revision ID: 7ac32f6e9b14
Revises: d42f9a6c1e30
Create Date: 2026-09-05 12:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "7ac32f6e9b14"
down_revision = "d42f9a6c1e30"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("olympiad_editions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "registration_opened_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.create_index(
            batch_op.f("ix_olympiad_editions_registration_opened_at"),
            ["registration_opened_at"],
            unique=False,
        )

    op.create_table(
        "registration_notification_dispatches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("registration_opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("registration_url_sha256", sa.String(length=64), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
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
            name=op.f(
                "ck_registration_notification_dispatches_nonnegative_attempt_count"
            ),
        ),
        sa.CheckConstraint(
            "length(idempotency_key) BETWEEN 8 AND 128",
            name=op.f(
                "ck_registration_notification_dispatches_valid_idempotency_key_length"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["user_olympiad_plans.id"],
            name=op.f(
                "fk_registration_notification_dispatches_plan_id_user_olympiad_plans"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_registration_notification_dispatches")
        ),
        sa.UniqueConstraint(
            "idempotency_key",
            name=op.f("uq_registration_notification_dispatches_idempotency_key"),
        ),
        sa.UniqueConstraint(
            "plan_id",
            "registration_opened_at",
            name="registration_notification_plan_opened_at",
        ),
    )
    with op.batch_alter_table(
        "registration_notification_dispatches", schema=None
    ) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_registration_notification_dispatches_next_attempt_at"),
            ["next_attempt_at"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_registration_notification_dispatches_plan_id"),
            ["plan_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_registration_notification_dispatches_scheduled_for"),
            ["scheduled_for"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_registration_notification_dispatches_status"),
            ["status"],
            unique=False,
        )


def downgrade():
    with op.batch_alter_table(
        "registration_notification_dispatches", schema=None
    ) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_registration_notification_dispatches_status")
        )
        batch_op.drop_index(
            batch_op.f("ix_registration_notification_dispatches_scheduled_for")
        )
        batch_op.drop_index(
            batch_op.f("ix_registration_notification_dispatches_plan_id")
        )
        batch_op.drop_index(
            batch_op.f("ix_registration_notification_dispatches_next_attempt_at")
        )
    op.drop_table("registration_notification_dispatches")

    with op.batch_alter_table("olympiad_editions", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_olympiad_editions_registration_opened_at")
        )
        batch_op.drop_column("registration_opened_at")
