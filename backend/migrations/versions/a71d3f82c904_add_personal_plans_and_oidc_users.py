"""add OIDC users, personal plans and stable stage identity

Revision ID: a71d3f82c904
Revises: 50a1aafe5939
Create Date: 2026-08-26 10:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "a71d3f82c904"
down_revision = "50a1aafe5939"
branch_labels = None
depends_on = None


def _timestamps():
    return (
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
    )


def upgrade():
    with op.batch_alter_table("stages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("key", sa.String(length=160), nullable=True))
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            )
        )

    op.execute(sa.text("UPDATE stages SET key = 'legacy-' || CAST(id AS VARCHAR)"))

    with op.batch_alter_table("stages", schema=None) as batch_op:
        batch_op.alter_column("key", existing_type=sa.String(length=160), nullable=False)
        batch_op.alter_column("is_active", server_default=None)
        batch_op.create_index(batch_op.f("ix_stages_is_active"), ["is_active"], unique=False)
        batch_op.create_unique_constraint("stage_edition_key", ["edition_id", "key"])

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("oidc_issuer", sa.String(length=255), nullable=False),
        sa.Column("oidc_subject", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("preferred_username", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=320), nullable=True),
        sa.Column("crm_role", sa.String(length=80), nullable=True),
        sa.Column("object_type", sa.String(length=80), nullable=True),
        sa.Column("grade", sa.SmallInteger(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "grade IS NULL OR grade BETWEEN 5 AND 11",
            name=op.f("ck_users_valid_grade"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("oidc_issuer", "oidc_subject", name="user_oidc_identity"),
    )

    op.create_table(
        "user_olympiad_plans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("edition_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "planned",
                "registered",
                "participating",
                "completed",
                name="planstatus",
                native_enum=False,
                length=40,
            ),
            nullable=False,
        ),
        sa.Column("is_name_public", sa.Boolean(), nullable=False),
        sa.Column("reminders_enabled", sa.Boolean(), nullable=False),
        sa.Column("reminder_days_before", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["edition_id"],
            ["olympiad_editions.id"],
            name=op.f("fk_user_olympiad_plans_edition_id_olympiad_editions"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_olympiad_plans_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_olympiad_plans")),
        sa.UniqueConstraint("user_id", "edition_id", name="user_edition_plan"),
    )
    with op.batch_alter_table("user_olympiad_plans", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_olympiad_plans_user_id"), ["user_id"])
        batch_op.create_index(batch_op.f("ix_user_olympiad_plans_edition_id"), ["edition_id"])
        batch_op.create_index(batch_op.f("ix_user_olympiad_plans_status"), ["status"])

    op.create_table(
        "user_stage_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("stage_id", sa.Integer(), nullable=False),
        sa.Column("participated", sa.Boolean(), nullable=False),
        sa.Column("advanced", sa.Boolean(), nullable=True),
        sa.Column("result", sa.String(length=500), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["user_olympiad_plans.id"],
            name=op.f("fk_user_stage_progress_plan_id_user_olympiad_plans"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["stage_id"],
            ["stages.id"],
            name=op.f("fk_user_stage_progress_stage_id_stages"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_stage_progress")),
        sa.UniqueConstraint("plan_id", "stage_id", name="plan_stage_progress"),
    )
    with op.batch_alter_table("user_stage_progress", schema=None) as batch_op:
        batch_op.create_index(batch_op.f("ix_user_stage_progress_plan_id"), ["plan_id"])
        batch_op.create_index(batch_op.f("ix_user_stage_progress_stage_id"), ["stage_id"])


def downgrade():
    with op.batch_alter_table("user_stage_progress", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_stage_progress_stage_id"))
        batch_op.drop_index(batch_op.f("ix_user_stage_progress_plan_id"))
    op.drop_table("user_stage_progress")

    with op.batch_alter_table("user_olympiad_plans", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_user_olympiad_plans_status"))
        batch_op.drop_index(batch_op.f("ix_user_olympiad_plans_edition_id"))
        batch_op.drop_index(batch_op.f("ix_user_olympiad_plans_user_id"))
    op.drop_table("user_olympiad_plans")
    op.drop_table("users")

    with op.batch_alter_table("stages", schema=None) as batch_op:
        batch_op.drop_constraint("stage_edition_key", type_="unique")
        batch_op.drop_index(batch_op.f("ix_stages_is_active"))
        batch_op.drop_column("is_active")
        batch_op.drop_column("key")
