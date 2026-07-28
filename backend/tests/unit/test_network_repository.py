from app.repositories import network_repository as repo


def test_insert_sample_returns_id(test_db_path):
    new_id = repo.insert_sample(
        timestamp="2026-05-11T14:30:00",
        connected=1,
        wifi_signal_dBm="-52",
        ping_external_ms="14.2 ms",
        ping_router_ms="2.4 ms",
        temperature_C="49.4",
    )
    assert isinstance(new_id, int) and new_id > 0


def test_insert_sample_skips_duplicate_minute(test_db_path):
    first = repo.insert_sample(
        timestamp="2026-05-11T14:30:00",
        connected=1, wifi_signal_dBm="-52",
        ping_external_ms="14.2 ms", ping_router_ms="2.4 ms",
        temperature_C="49.4",
    )
    second = repo.insert_sample(
        timestamp="2026-05-11T14:30:00",
        connected=0, wifi_signal_dBm="-99",
        ping_external_ms="N/A", ping_router_ms="N/A",
        temperature_C="50.0",
    )
    assert first is not None
    assert second is None


def test_delete_older_than(test_db_path):
    repo.insert_sample(
        timestamp="2026-04-01T10:00:00", connected=1,
        wifi_signal_dBm="-50", ping_external_ms="10 ms",
        ping_router_ms="2 ms", temperature_C="48.0",
    )
    repo.insert_sample(
        timestamp="2026-05-11T10:00:00", connected=1,
        wifi_signal_dBm="-50", ping_external_ms="10 ms",
        ping_router_ms="2 ms", temperature_C="48.0",
    )
    deleted = repo.delete_older_than("2026-05-01T00:00:00")
    assert deleted == 1
    remaining = repo.get_paginated(limit=100, page=1)
    assert remaining.total == 1
    assert remaining.data[0]["timestamp"] == "2026-05-11T10:00:00"
