"""Tests for the single-owner audio player.

These lock in the anti-stacking guarantee: every ring reaps any existing player
before starting a new one, and the in-memory active-flag semantics that the ESP
callback / status endpoint depend on are preserved.
"""
import pytest

import app.services.player_service as ps


@pytest.fixture(autouse=True)
def _clean_state(tmp_path, monkeypatch):
    """Isolate module globals and the PID file for every test."""
    monkeypatch.setattr(ps, "_PID_FILE", tmp_path / "alarm.pid")
    # Default: no orphan players and no real signals unless a test overrides.
    monkeypatch.setattr(ps, "_scan_proc_for_players", lambda: set())
    with ps._lock:
        ps._reset()
    yield
    with ps._lock:
        ps._reset()


async def test_play_reaps_existing_then_spawns_and_marks_active(monkeypatch):
    killed: list[int] = []
    monkeypatch.setattr(ps, "_find_player_pids", lambda: {111})
    monkeypatch.setattr(ps, "_kill_pid", lambda pid: killed.append(pid))
    monkeypatch.setattr(ps, "_spawn_player", lambda path: 222)

    started = await ps.play(alarm_id=7, log_id=42)

    assert started is True
    assert ps.is_active() is True
    assert ps.get_current_ids() == (7, 42)
    # The previous/orphaned player was killed BEFORE the new one was recorded.
    assert killed == [111]
    assert ps._PID_FILE.read_text().strip() == "222"


async def test_play_is_rejected_while_already_active(monkeypatch):
    spawned: list[str] = []
    monkeypatch.setattr(ps, "_find_player_pids", lambda: set())
    monkeypatch.setattr(ps, "_kill_pid", lambda pid: None)
    monkeypatch.setattr(ps, "_spawn_player", lambda path: spawned.append(path) or 1)

    assert await ps.play(1, 1) is True
    assert len(spawned) == 1

    # Second concurrent ring must NOT start a second stream.
    assert await ps.play(2, 2) is False
    assert len(spawned) == 1
    assert ps.get_current_ids() == (1, 1)


async def test_play_resets_when_spawn_fails(monkeypatch):
    monkeypatch.setattr(ps, "_find_player_pids", lambda: set())
    monkeypatch.setattr(ps, "_kill_pid", lambda pid: None)
    monkeypatch.setattr(ps, "_spawn_player", lambda path: None)  # spawn failed

    assert await ps.play(1, 1) is False
    assert ps.is_active() is False
    assert ps.get_current_ids() == (None, None)


async def test_stop_kills_players_and_resets(monkeypatch):
    killed: list[int] = []
    monkeypatch.setattr(ps, "_find_player_pids", lambda: {333})
    monkeypatch.setattr(ps, "_kill_pid", lambda pid: killed.append(pid))
    monkeypatch.setattr(ps, "_spawn_player", lambda path: 333)

    await ps.play(1, 1)
    killed.clear()  # ignore the pre-play reap

    assert ps.stop() is True
    assert killed == [333]
    assert ps.is_active() is False
    # A second stop is a no-op (nothing active to stop).
    assert ps.stop() is False


def test_stop_when_inactive_returns_false(monkeypatch):
    killed: list[int] = []
    monkeypatch.setattr(ps, "_find_player_pids", lambda: {1})
    monkeypatch.setattr(ps, "_kill_pid", lambda pid: killed.append(pid))

    assert ps.stop() is False
    assert killed == []  # must not touch processes when nothing is active


def test_find_player_pids_includes_verified_pidfile(monkeypatch):
    ps._PID_FILE.write_text("500")
    monkeypatch.setattr(ps, "_scan_proc_for_players", lambda: {600, 700})
    monkeypatch.setattr(ps, "_verify_player_pid", lambda pid: True)

    assert ps._find_player_pids() == {500, 600, 700}


def test_find_player_pids_ignores_unverified_pidfile(monkeypatch):
    # SECURITY: a PID in the file that is NOT confirmed to be our player (e.g.
    # planted by another process) must never be returned for signalling.
    ps._PID_FILE.write_text("500")
    monkeypatch.setattr(ps, "_scan_proc_for_players", lambda: set())
    monkeypatch.setattr(ps, "_verify_player_pid", lambda pid: False)

    assert ps._find_player_pids() == set()


def test_find_player_pids_survives_missing_pidfile(monkeypatch):
    # No PID file written; scan finds an orphan.
    monkeypatch.setattr(ps, "_scan_proc_for_players", lambda: {900})
    assert ps._find_player_pids() == {900}


def test_cmdline_is_player_matches_only_exact_argv():
    # Exact `-m app.audio_player` argv tokens match.
    assert ps._cmdline_is_player(b"/usr/bin/python3\x00-m\x00app.audio_player\x00/x.wav\x00")
    # A loose substring in a single arg must NOT match (anti-spoofing).
    assert not ps._cmdline_is_player(b"/bin/echo\x00app.audio_player is great\x00")
    assert not ps._cmdline_is_player(b"vim\x00app.audio_player.py\x00")


def test_cleanup_orphans_reaps_and_clears_pidfile(monkeypatch):
    killed: list[int] = []
    ps._PID_FILE.write_text("42")
    monkeypatch.setattr(ps, "_scan_proc_for_players", lambda: {42, 43})
    monkeypatch.setattr(ps, "_kill_pid", lambda pid: killed.append(pid))

    ps.cleanup_orphans()

    assert sorted(killed) == [42, 43]
    assert not ps._PID_FILE.exists()
