"""Standalone alarm audio player.

Run as a subprocess:  ``python -m app.audio_player <sound_path>``

This process does one thing: loop the alarm sound forever until it is killed.
It is deliberately isolated from the API process so that exactly ONE audio
stream can ever exist system-wide — ``player_service`` kills any previous
instance (tracked by PID + a ``/proc`` scan for this module's name) before
starting a new one. That is what prevents the "layered / stacking ring tone"
bug: even orphaned players left behind by a crashed or restarted API process
get reaped before the next ring starts.

The process blocks on the main thread while pygame drives playback on its own
audio thread; a SIGTERM/SIGKILL from ``player_service`` ends it and releases
the ALSA device.
"""
import logging
import sys
import time

logger = logging.getLogger(__name__)

# Marker used by player_service._scan_proc_for_players() to find every running
# player. Must match the module path this file is launched with (``-m``).
PLAYER_MARKER = "app.audio_player"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print("usage: python -m app.audio_player <sound_path>", file=sys.stderr)
        return 2
    sound_path = argv[0]

    try:
        import pygame
    except ImportError:
        print("pygame not available — audio disabled", file=sys.stderr)
        return 1

    try:
        pygame.mixer.init()
        pygame.mixer.music.load(sound_path)
        # Loop forever (-1) with a gentle fade-in, matching the original behaviour.
        pygame.mixer.music.play(-1, fade_ms=20000)
    except Exception as exc:  # noqa: BLE001 — this is a leaf process; log and exit
        print(f"failed to start alarm audio: {exc}", file=sys.stderr)
        return 1

    # Stay alive until the process is killed by player_service. pygame plays on
    # a background thread, so the main thread just has to block.
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
