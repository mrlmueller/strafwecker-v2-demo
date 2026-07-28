from datetime import datetime, timedelta
from cleanup_db import utc_cutoff_str, local_iso_cutoff


def test_utc_cutoff_uses_space_separator_and_subtracts_days():
    base_utc = datetime(2026, 5, 11, 14, 30, 0)
    cutoff = utc_cutoff_str(180, now_utc=base_utc)
    assert cutoff == (base_utc - timedelta(days=180)).strftime("%Y-%m-%d %H:%M:%S")
    assert "T" not in cutoff
    assert cutoff == "2025-11-12 14:30:00"


def test_local_iso_cutoff_uses_t_separator_and_subtracts_days():
    base_local = datetime(2026, 5, 11, 14, 30, 0)
    cutoff = local_iso_cutoff(30, now_local=base_local)
    assert cutoff == "2026-04-11T14:30:00"


def test_local_iso_cutoff_format_lex_sorts_correctly():
    # 'YYYY-MM-DDTHH:MM:SS' is lexicographically ordered, so a string < comparison
    # in SQL works the same as a chronological comparison.
    a = local_iso_cutoff(30, now_local=datetime(2026, 5, 11, 14, 30, 0))
    b = local_iso_cutoff(10, now_local=datetime(2026, 5, 11, 14, 30, 0))
    assert a < b
