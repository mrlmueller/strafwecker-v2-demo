"""add nap-timer columns

Revision ID: 003
Revises: 002
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "alarms",
        sa.Column("kind", sa.Text, nullable=False, server_default="alarm"),
    )
    op.add_column(
        "alarms",
        sa.Column("nap_target_at", sa.Text, nullable=True),
    )
    op.add_column(
        "alarms",
        sa.Column("nap_duration_minutes", sa.Integer, nullable=True),
    )
    op.add_column(
        "alarms",
        sa.Column("esp32_button", sa.Integer, nullable=False, server_default="1"),
    )


def downgrade() -> None:
    op.drop_column("alarms", "esp32_button")
    op.drop_column("alarms", "nap_duration_minutes")
    op.drop_column("alarms", "nap_target_at")
    op.drop_column("alarms", "kind")
