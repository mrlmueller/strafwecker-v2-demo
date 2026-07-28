"""Alarm playback control.

Root-cause context for the "layered / stacking ring tone" bug
-------------------------------------------------------------
Playback used to run *inside* the API process via ``pygame.mixer.music.play(-1)``
(an infinite loop) guarded only by a per-process in-memory boolean. Nothing in
that design could guarantee "only one sound across the whole system": any second
process that ever started a ring (a uvicorn restart under ``Restart=always``, a
redeploy, a crash-respawn) began an independent forever-looping stream that the
in-process ``stop()`` calls could never reach — so streams accumulated over days
and only a full service restart (which kills the whole cgroup) cleared them.

Fix: audio now runs in a dedicated, disposable subprocess (``app.audio_player``).
Before every ring we kill *any* existing player — the one we tracked via a PID
file AND any orphan found by scanning ``/proc`` for the player module's name — so
at most one audio stream can ever exist, regardless of how the API process was
restarted. ``stop()`` and shutdown do the same reaping.

The in-memory ``_alarm_active`` flag is retained purely as the logical
"an alarm is currently ringing" signal used by callers (ESP callback, status
endpoint, sunrise tick); the authoritative audio owner is the subprocess.
"""
import asyncio
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional

from app.audio_player import PLAYER_MARKER

logger = logging.getLogger(__name__)

_alarm_active = False
_alarm_id: Optional[int] = None
_log_id: Optional[int] = None
_alarm_start_time: Optional[float] = None
_lock = threading.Lock()

# backend/ directory, so the subprocess can `import app.*` with `-m`.
_BACKEND_DIR = Path(__file__).resolve().parents[2]
# Where we remember the current player's PID. Kept in the app-owned data dir —
# NOT world-writable /tmp — so another local user can't pre-create or symlink it
# to redirect our signals. Overridable via env (used by tests).
_PID_FILE = Path(os.environ.get("ALARM_PID_FILE") or (_BACKEND_DIR / "data" / "alarm.pid"))


def is_active() -> bool:
    return _alarm_active


def get_current_ids() -> tuple[Optional[int], Optional[int]]:
    return _alarm_id, _log_id


async def play(alarm_id: int, log_id: int) -> bool:
    """Start alarm. Returns False if already active or if audio fails to start."""
    global _alarm_active, _alarm_id, _log_id, _alarm_start_time
    with _lock:
        if _alarm_active:
            return False
        _alarm_active = True
        _alarm_id = alarm_id
        _log_id = log_id
        _alarm_start_time = time.time()
    loop = asyncio.get_running_loop()
    success = await loop.run_in_executor(None, _start_audio)
    if not success:
        with _lock:
            _reset()
        return False
    return True


def _start_audio() -> bool:
    # Reap any previous/orphaned player FIRST so sounds can never stack.
    _kill_all_players()
    try:
        from app.config import settings
        pid = _spawn_player(str(settings.alarm_sound_path))
    except Exception:
        logger.exception("Error starting alarm audio")
        return False
    if pid is None:
        return False
    _write_pid(pid)
    logger.info("Alarm audio player started (pid=%d).", pid)
    return True


def stop() -> bool:
    """Stop alarm. Returns True only if this call actually stopped it."""
    global _alarm_active
    with _lock:
        if not _alarm_active:
            return False
        _kill_all_players()
        _reset()
        return True


def cleanup_orphans() -> None:
    """Kill any stray alarm-audio players. Used at API startup and shutdown so a
    crashed/redeployed process can never leave a forever-looping stream behind."""
    _kill_all_players()


def _reset() -> None:
    global _alarm_active, _alarm_id, _log_id, _alarm_start_time
    _alarm_active = False
    _alarm_id = None
    _log_id = None
    _alarm_start_time = None


# --- process management (each helper is a seam that tests can monkeypatch) ---

def _spawn_player(sound_path: str) -> Optional[int]:
    """Launch the audio subprocess and return its PID (or None on failure)."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", PLAYER_MARKER, sound_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(_BACKEND_DIR),
            start_new_session=True,  # decouple from uvicorn's own signal handling
        )
    except Exception:
        logger.exception("Failed to spawn audio player subprocess")
        return None
    return proc.pid


def _kill_all_players() -> None:
    for pid in _find_player_pids():
        _kill_pid(pid)
    _clear_pid_file()


def _find_player_pids() -> set[int]:
    """Every PID *verified* to be one of our alarm players: those found by
    scanning /proc for our exact ``-m app.audio_player`` argv, plus the tracked
    PID only if it independently verifies. We never return a PID we haven't
    confirmed is our own player, so a tampered PID file cannot redirect our
    signals at an unrelated process."""
    pids = _scan_proc_for_players()
    tracked = _read_pid_file()
    if tracked is not None and tracked not in pids and _verify_player_pid(tracked):
        pids.add(tracked)
    return pids


def _read_pid_file() -> Optional[int]:
    try:
        text = _PID_FILE.read_text().strip()
    except OSError:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _scan_proc_for_players() -> set[int]:
    """Find running players by exact argv match. Linux-only; empty set elsewhere."""
    proc_dir = Path("/proc")
    if not proc_dir.is_dir():
        return set()
    found: set[int] = set()
    for entry in proc_dir.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            cmdline = (entry / "cmdline").read_bytes()
        except OSError:
            continue
        if _cmdline_is_player(cmdline):
            found.add(int(entry.name))
    return found


def _verify_player_pid(pid: int) -> bool:
    """True only if /proc/<pid> is running our exact ``-m app.audio_player`` argv."""
    try:
        return _cmdline_is_player((Path("/proc") / str(pid) / "cmdline").read_bytes())
    except OSError:
        return False


def _cmdline_is_player(cmdline: bytes) -> bool:
    """Match a /proc cmdline (NUL-separated argv) that runs ``-m app.audio_player``
    as distinct argv tokens — far more specific and harder to spoof than a loose
    substring, so unrelated processes are never mistaken for a player."""
    parts = cmdline.split(b"\x00")
    marker = PLAYER_MARKER.encode()
    for i, part in enumerate(parts[:-1]):
        if part == b"-m" and parts[i + 1] == marker:
            return True
    return False


def _kill_pid(pid: int) -> None:
    """Terminate a player PID, escalating to SIGKILL if it lingers."""
    sigkill = getattr(signal, "SIGKILL", signal.SIGTERM)
    for sig in (signal.SIGTERM, sigkill):
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            return  # already gone
        except OSError as exc:
            logger.warning("Could not signal audio player pid %d: %s", pid, exc)
            return
        # Give SIGTERM a brief moment before escalating.
        for _ in range(5):
            if not _pid_alive(pid):
                return
            time.sleep(0.05)


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except OSError:
        return True  # exists but we can't signal it
    return True


def _write_pid(pid: int) -> None:
    try:
        _PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Owner-only perms and O_NOFOLLOW so a planted symlink can't redirect the
        # write. (O_NOFOLLOW is absent on Windows — falls back to 0 there.)
        flags = os.O_CREAT | os.O_WRONLY | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(_PID_FILE, flags, 0o600)
        try:
            os.write(fd, str(pid).encode())
        finally:
            os.close(fd)
    except OSError as exc:
        logger.warning("Could not write alarm PID file %s: %s", _PID_FILE, exc)


def _clear_pid_file() -> None:
    try:
        _PID_FILE.unlink()
    except FileNotFoundError:
        pass
    except OSError as exc:
        logger.warning("Could not remove alarm PID file %s: %s", _PID_FILE, exc)


def setup_gpio() -> None:
    """Register GPIO interrupt for the physical button on the Pi. No-op on non-Pi."""
    try:
        import RPi.GPIO as GPIO
        BUTTON_PIN = 16
        GPIO.setmode(GPIO.BCM)
        GPIO.cleanup(BUTTON_PIN)
        GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING,
                              callback=_gpio_button_callback, bouncetime=500)
        logger.info("GPIO button listener registered on pin %d.", BUTTON_PIN)
    except ImportError:
        logger.warning("RPi.GPIO not available — physical button disabled.")
    except Exception:
        logger.exception("Failed to set up GPIO.")


def _gpio_button_callback(channel) -> None:
    a_id, l_id = get_current_ids()
    if stop():  # atomic: only write log if this call actually stopped the alarm
        if a_id is not None and l_id is not None:
            from app.services import log_service
            log_service.mark_button_pressed(l_id, a_id, time_to_button_sec=None, source="local")
