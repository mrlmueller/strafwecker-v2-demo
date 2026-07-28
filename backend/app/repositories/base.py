import sqlite3
from contextlib import contextmanager
from typing import Generator
from app.config import settings


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.database_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
