import sqlite3
from app.repositories.base import get_db


def test_get_db_enables_wal(test_db_path):
    with get_db() as conn:
        mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode == "wal"


def test_get_db_enables_foreign_keys(test_db_path):
    with get_db() as conn:
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
    assert fk == 1


def test_get_db_rolls_back_on_error(test_db_path):
    try:
        with get_db() as conn:
            conn.execute("INSERT INTO alarms (time) VALUES (?)", ("07:00",))
            raise RuntimeError("simulated error")
    except RuntimeError:
        pass
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM alarms").fetchone()[0]
    assert count == 0
