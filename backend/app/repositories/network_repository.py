from dataclasses import dataclass
from typing import Optional
from app.repositories.base import get_db


@dataclass
class NetworkLog:
    id: int
    timestamp: str
    connected: int
    wifi_signal_dBm: str
    ping_external_ms: str
    ping_router_ms: str
    temperature_C: str


@dataclass
class PaginatedResult:
    data: list
    page: int
    limit: int
    total: int
    pages: int


def _row_to_network_log(row) -> NetworkLog:
    return NetworkLog(
        id=row["id"],
        timestamp=row["timestamp"],
        connected=row["connected"],
        wifi_signal_dBm=row["wifi_signal_dBm"] or "N/A",
        ping_external_ms=row["ping_external_ms"] or "N/A",
        ping_router_ms=row["ping_router_ms"] or "N/A",
        temperature_C=row["temperature_C"] or "N/A",
    )


def insert_sample(
    timestamp: str,
    connected: int,
    wifi_signal_dBm: str,
    ping_external_ms: str,
    ping_router_ms: str,
    temperature_C: str,
) -> Optional[int]:
    """Insert one network_log row. No-op if a row for the same minute already exists.

    `timestamp` must already be truncated to minute precision (seconds=0) by the caller —
    we rely on that for the idempotency check.
    """
    with get_db() as conn:
        existing = conn.execute(
            "SELECT 1 FROM network_log WHERE timestamp = ? LIMIT 1", (timestamp,)
        ).fetchone()
        if existing is not None:
            return None
        cursor = conn.execute(
            "INSERT INTO network_log "
            "(timestamp, connected, wifi_signal_dBm, ping_external_ms, ping_router_ms, temperature_C) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (timestamp, int(connected), wifi_signal_dBm, ping_external_ms, ping_router_ms, temperature_C),
        )
        return cursor.lastrowid


def delete_older_than(cutoff_iso: str) -> int:
    """Delete network_log rows with timestamp < cutoff_iso. Returns rows deleted."""
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM network_log WHERE timestamp < ?", (cutoff_iso,))
        return cursor.rowcount


def get_paginated(
    limit: int = 100,
    page: int = 1,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    minimal: bool = False,
) -> PaginatedResult:
    limit = min(max(limit, 1), 1000)
    page = max(page, 1)
    offset = (page - 1) * limit

    where_clauses: list[str] = []
    params: list = []
    if start_date:
        where_clauses.append("timestamp >= ?")
        params.append(start_date)
    if end_date:
        where_clauses.append("timestamp <= ?")
        params.append(end_date)
    where_sql = f" WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    cols = "id, timestamp, connected, temperature_C" if minimal else "*"
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT {cols} FROM network_log{where_sql} ORDER BY timestamp DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()
        total = conn.execute(
            f"SELECT COUNT(*) FROM network_log{where_sql}", params
        ).fetchone()[0]

    return PaginatedResult(
        data=[dict(r) for r in rows],
        page=page,
        limit=limit,
        total=total,
        pages=max(1, (total + limit - 1) // limit),
    )
