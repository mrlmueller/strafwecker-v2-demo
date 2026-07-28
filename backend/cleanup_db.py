#!/usr/bin/env python3
"""
Database retention sweeper — runs daily via cleanup_db.timer.

Retention policy (time-based):
  - network_log:     last 30 days (~43k rows at 1/min)
  - logs:            last 180 days (alarm history)
  - reboot_log:      last 365 days
  - reboot_history:  last 365 days

Also VACUUMs the database on Sundays to reclaim space freed by deletes.

Why two cutoff formats:
  - `logs.timestamp` is written by SQLite's CURRENT_TIMESTAMP, which is UTC
    in the format 'YYYY-MM-DD HH:MM:SS' (no 'T' separator).
  - The other timestamp columns are written by Python's datetime.now().isoformat(),
    which is local time with a 'T' separator.

ISO-style timestamps order lexicographically, so a `WHERE ts < ?` works for both
formats independently — but we need a different cutoff string per column.
"""
import logging
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)

NETWORK_LOG_DAYS = 30
LOGS_DAYS = 180
REBOOT_DAYS = 365


def utc_cutoff_str(days: int, now_utc: datetime | None = None) -> str:
    """UTC cutoff in SQLite CURRENT_TIMESTAMP format: 'YYYY-MM-DD HH:MM:SS'."""
    base = now_utc if now_utc is not None else datetime.now(timezone.utc).replace(tzinfo=None)
    return (base - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def local_iso_cutoff(days: int, now_local: datetime | None = None) -> str:
    """Local-time cutoff as ISO with 'T' separator: 'YYYY-MM-DDTHH:MM:SS'."""
    base = now_local if now_local is not None else datetime.now()
    return (base - timedelta(days=days)).isoformat(timespec="seconds")


def main() -> None:
    from app.repositories import network_repository, log_repository
    from app.repositories.base import get_db

    deleted = network_repository.delete_older_than(local_iso_cutoff(NETWORK_LOG_DAYS))
    logger.info("Pruned %d network_log rows older than %d days.", deleted, NETWORK_LOG_DAYS)

    deleted = log_repository.delete_older_than(utc_cutoff_str(LOGS_DAYS))
    logger.info("Pruned %d alarm-log rows older than %d days (UTC).", deleted, LOGS_DAYS)

    reboot_cutoff = local_iso_cutoff(REBOOT_DAYS)
    with get_db() as conn:
        c = conn.execute("DELETE FROM reboot_log WHERE timestamp < ?", (reboot_cutoff,))
        logger.info("Pruned %d reboot_log rows older than %d days.", c.rowcount, REBOOT_DAYS)
        c = conn.execute("DELETE FROM reboot_history WHERE timestamp < ?", (reboot_cutoff,))
        logger.info("Pruned %d reboot_history rows older than %d days.", c.rowcount, REBOOT_DAYS)

    # VACUUM on Sundays to reclaim freed space. Held off other days so daily
    # cleanups are quick; weekly is enough to keep the DB compact.
    if datetime.now().weekday() == 6:
        logger.info("Sunday — running VACUUM.")
        with get_db() as conn:
            conn.execute("VACUUM")
        logger.info("VACUUM done.")


if __name__ == "__main__":
    main()
