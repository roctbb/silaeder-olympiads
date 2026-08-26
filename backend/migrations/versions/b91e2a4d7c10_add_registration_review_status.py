"""add registration review status

Revision ID: b91e2a4d7c10
Revises: f7b2d4e6a810
Create Date: 2026-08-26 07:15:00
"""

import sqlalchemy as sa
from alembic import op

revision = "b91e2a4d7c10"
down_revision = "f7b2d4e6a810"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("olympiad_editions", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "registration_status",
                sa.Enum(
                    "open",
                    "announced",
                    "not_open",
                    "not_found",
                    name="registrationstatus",
                    native_enum=False,
                    length=40,
                ),
                server_default=sa.text("'not_found'"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("registration_checked_on", sa.Date(), nullable=True)
        )
        batch_op.create_index(
            batch_op.f("ix_olympiad_editions_registration_status"),
            ["registration_status"],
            unique=False,
        )

    op.execute(
        sa.text(
            "UPDATE olympiad_editions "
            "SET registration_status = 'open' "
            "WHERE registration_url IS NOT NULL"
        )
    )

    with op.batch_alter_table("olympiad_editions", schema=None) as batch_op:
        batch_op.alter_column("registration_status", server_default=None)


def downgrade():
    with op.batch_alter_table("olympiad_editions", schema=None) as batch_op:
        batch_op.drop_index(
            batch_op.f("ix_olympiad_editions_registration_status")
        )
        batch_op.drop_column("registration_checked_on")
        batch_op.drop_column("registration_status")
