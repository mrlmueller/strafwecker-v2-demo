import sqlite3
from fastapi import APIRouter
from app.repositories.base import get_db

router = APIRouter(prefix="/reboot_history", tags=["reboot_history"])


@router.get("/")
def list_reboot_history(limit: int = 100, page: int = 1, success: int | None = None):
    offset = (page - 1) * limit
    with get_db() as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        where = " WHERE success = ?" if success is not None else ""
        filter_params: tuple = (success,) if success is not None else ()
        total = cur.execute(
            f"SELECT COUNT(*) FROM reboot_history{where}", filter_params
        ).fetchone()[0]
        rows = cur.execute(
            f"SELECT id, timestamp, reason AS notes, success FROM reboot_history{where} "
            f"ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            filter_params + (limit, offset),
        ).fetchall()
    return {
        "data": [dict(r) for r in rows],
        "meta": {"page": page, "limit": limit, "total": total, "pages": max(1, -(-total // limit))},
    }
