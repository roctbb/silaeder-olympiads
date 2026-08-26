"""add edition eligibility notes

Revision ID: d8e4b6c9a271
Revises: c4b73de91f20
Create Date: 2026-08-26 18:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "d8e4b6c9a271"
down_revision = "c4b73de91f20"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "olympiad_editions",
        sa.Column("eligibility_notes", sa.Text(), nullable=True),
    )


def downgrade():
    op.drop_column("olympiad_editions", "eligibility_notes")
