"""add registration close timestamp

Revision ID: f7b2d4e6a810
Revises: e4a1c7d9b203
Create Date: 2026-08-26 23:15:00
"""

import sqlalchemy as sa
from alembic import op

revision = "f7b2d4e6a810"
down_revision = "e4a1c7d9b203"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "olympiad_editions",
        sa.Column("registration_closes_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_column("olympiad_editions", "registration_closes_at")
