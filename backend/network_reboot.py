#!/usr/bin/env python3
import os
import sys
import sqlite3
import logging
import subprocess
from datetime import datetime, timedelta
import time
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.services.alarm_service import get_next_alarm

# Optional: For playing a sound in debug mode
try:
    import pygame
except ImportError:
    pygame = None

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
DB_PATH = str(settings.database_path)
REBOOT_LOG_TABLE = "reboot_log"

# Hardcoded debug mode: set to 1 for on, 0 for off.
DEBUG_MODE = 0

# Set up logging
logger = logging.getLogger("network_reboot")
logger.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG if DEBUG_MODE else logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

if DEBUG_MODE:
    log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "network_reboot.log")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

# ------------------------------------------------------------
# Helper functions
# ------------------------------------------------------------
def init_reboot_log_table():
    try:
        with sqlite3.connect(DB_PATH) as conn:
            c = conn.cursor()
            c.execute(f"""
                CREATE TABLE IF NOT EXISTS {REBOOT_LOG_TABLE} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT,
                    network_connected INTEGER,
                    details TEXT
                )
            """)
            conn.commit()
            logger.debug("Reboot log table initialized.")
    except Exception as e:
        logger.error(f"Error creating reboot log table: {e}")


def get_current_network_status():
    """Check network by pinging the router and an external host."""
    targets = ["192.168.178.1", "8.8.8.8"]
    for target in targets:
        try:
            result = subprocess.run(
                ["ping", "-c", "1", "-W", "3", target],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                logger.debug(f"Ping to {target} succeeded.")
                return {"connected": 1}
        except Exception as e:
            logger.debug(f"Ping to {target} failed: {e}")
    logger.info("All ping targets failed — network appears down.")
    return {"connected": 0}


def count_recent_reboots(window_minutes=30):
    window_start = (datetime.now() - timedelta(minutes=window_minutes)).isoformat()
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT COUNT(*) FROM {REBOOT_LOG_TABLE} WHERE timestamp >= ?",
                (window_start,)
            )
            count = cursor.fetchone()[0]
            logger.debug(f"Recent reboots in the last {window_minutes} minutes: {count}")
            return count
    except Exception as e:
        logger.error(f"Error counting recent reboots: {e}")
        return 0


def log_reboot_event(network_status, details=""):
    timestamp = datetime.now().isoformat()
    connected = network_status.get("connected", 0) if network_status else 0
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT INTO {REBOOT_LOG_TABLE} (timestamp, network_connected, details) VALUES (?, ?, ?)",
                (timestamp, connected, details)
            )
            conn.commit()
            logger.debug("Logged reboot event with details: " + details)
    except Exception as e:
        logger.error(f"Error logging reboot event: {e}")


def play_debug_sound():
    if not pygame:
        logger.error("pygame is not installed. Skipping sound playback.")
        return
    try:
        pygame.mixer.init()
        pygame.mixer.music.load(str(settings.alarm_sound_path))
        pygame.mixer.music.play()
        time.sleep(5)
        pygame.mixer.music.stop()
    except Exception as e:
        logger.exception("Error playing sound with pygame:")


def is_alarm_active() -> bool:
    """Ask the local API whether an alarm is currently ringing."""
    try:
        import requests as req_lib
        res = req_lib.get(
            "http://localhost:8000/api/v1/esp/alarm/status",
            headers={"x-api-key": os.environ.get("API_KEY", "")},
            timeout=2,
        )
        if res.ok:
            return bool(res.json().get("active", False))
    except Exception:
        pass
    return False


def perform_reboot():
    try:
        logger.info("Executing reboot command.")
        subprocess.run(["sudo", "reboot"])
    except Exception as e:
        logger.error(f"Error executing reboot: {e}")


# ------------------------------------------------------------
# Main check-and-reboot logic
# ------------------------------------------------------------
def check_and_maybe_reboot():
    logger.info("Running network reboot check.")
    init_reboot_log_table()
    now = datetime.now()

    # 1. Never reboot while an alarm is currently ringing.
    if is_alarm_active():
        logger.info("Alarm currently ringing; skipping reboot.")
        return

    # 2. Skip reboot if an alarm fires within the next 7 minutes.
    result = get_next_alarm()
    if result:
        _, next_alarm_dt = result
        minutes_until_alarm = (next_alarm_dt - now).total_seconds() / 60.0
        if minutes_until_alarm <= 7:
            logger.info(f"Upcoming alarm in {minutes_until_alarm:.1f} minutes; skipping reboot.")
            return

    # 3. Check network status.
    net_status = get_current_network_status()
    if net_status and net_status.get("connected", 0) == 1:
        logger.info("Network connection is valid. No reboot needed.")
        return
    else:
        logger.info("Network appears to be down (or no log entry found).")

    # 4. Reboot loop prevention.
    recent_reboots = count_recent_reboots(window_minutes=30)
    if recent_reboots >= 2:
        logger.info(f"{recent_reboots} reboot events in last 30 minutes; aborting to avoid loop.")
        return

    # 5. Log and optionally play debug sound.
    log_reboot_event(net_status, details=f"Network status at reboot attempt: {net_status}")
    if DEBUG_MODE:
        logger.info("Debug mode: playing alarm sound for 5 seconds before reboot.")
        play_debug_sound()

    # 6. Reboot.
    perform_reboot()


# ------------------------------------------------------------
# Entry point
# ------------------------------------------------------------
if __name__ == "__main__":
    check_and_maybe_reboot()
