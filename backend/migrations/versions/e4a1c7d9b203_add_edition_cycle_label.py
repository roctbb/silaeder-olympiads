"""add edition cycle label

Revision ID: e4a1c7d9b203
Revises: d8e4b6c9a271
Create Date: 2026-08-26 22:30:00
"""

import sqlalchemy as sa
from alembic import op

revision = "e4a1c7d9b203"
down_revision = "d8e4b6c9a271"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "olympiad_editions",
        sa.Column("cycle_label", sa.String(length=120), nullable=True),
    )


def downgrade():
    op.drop_column("olympiad_editions", "cycle_label")
