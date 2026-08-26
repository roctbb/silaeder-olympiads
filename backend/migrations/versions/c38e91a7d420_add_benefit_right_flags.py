"""add explicit benefit right flags

Revision ID: c38e91a7d420
Revises: b91e2a4d7c10
Create Date: 2026-08-26 09:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "c38e91a7d420"
down_revision = "b91e2a4d7c10"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("benefits", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "has_bvi",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "has_hundred_points",
                sa.Boolean(),
                server_default=sa.false(),
                nullable=False,
            )
        )

    op.execute(
        sa.text(
            "UPDATE benefits SET "
            "has_bvi = CASE WHEN benefit_type = 'bvi' THEN TRUE ELSE FALSE END, "
            "has_hundred_points = CASE "
            "WHEN benefit_type = 'hundred_points' THEN TRUE ELSE FALSE END"
        )
    )

    with op.batch_alter_table("benefits", schema=None) as batch_op:
        batch_op.alter_column("has_bvi", server_default=None)
        batch_op.alter_column("has_hundred_points", server_default=None)


def downgrade():
    with op.batch_alter_table("benefits", schema=None) as batch_op:
        batch_op.drop_column("has_hundred_points")
        batch_op.drop_column("has_bvi")
