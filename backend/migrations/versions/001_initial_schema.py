"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "alarms",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("time", sa.Text, nullable=False),
        sa.Column("days_of_week", sa.Text),
        sa.Column("enabled", sa.Integer, default=1),
        sa.Column("repeat_type", sa.Text, default="once"),
        sa.Column("label", sa.Text),
        sa.Column("light", sa.Integer, default=0),
    )
    op.create_table(
        "logs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.DateTime, nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_update", sa.DateTime, nullable=False,
                  server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("alarm_id", sa.Integer, nullable=False),
        sa.Column("state", sa.Text, nullable=False, default="triggered"),
        sa.Column("time_to_button_sec", sa.Integer),
        sa.Column("pressed_in_time", sa.Integer),
        sa.Column("error_details", sa.Text),
        sa.Column("notes", sa.Text),
    )
    op.create_table(
        "network_log",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("timestamp", sa.Text),
        sa.Column("connected", sa.Integer),
        sa.Column("wifi_signal_dBm", sa.Text),
        sa.Column("ping_external_ms", sa.Text),
        sa.Column("ping_router_ms", sa.Text),
        sa.Column("temperature_C", sa.Text),
    )


def downgrade() -> None:
    op.drop_table("network_log")
    op.drop_table("logs")
    op.drop_table("alarms")
