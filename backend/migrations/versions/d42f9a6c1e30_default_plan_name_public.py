"""show participant name by default for newly created plans

Revision ID: d42f9a6c1e30
Revises: c38e91a7d420
Create Date: 2026-08-26 21:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "d42f9a6c1e30"
down_revision = "c38e91a7d420"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_olympiad_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "is_name_public",
            existing_type=sa.Boolean(),
            server_default=sa.true(),
            existing_nullable=False,
        )


def downgrade():
    with op.batch_alter_table("user_olympiad_plans", schema=None) as batch_op:
        batch_op.alter_column(
            "is_name_public",
            existing_type=sa.Boolean(),
            server_default=None,
            existing_nullable=False,
        )
