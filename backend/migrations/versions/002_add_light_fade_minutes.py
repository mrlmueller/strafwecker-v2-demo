"""add light_fade_minutes

Revision ID: 002
Revises: 001
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alarms",
        sa.Column("light_fade_minutes", sa.Integer, nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("alarms", "light_fade_minutes")
