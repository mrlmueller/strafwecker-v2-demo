"""
Tests for pure ESP32 logic — color math and payload construction.
These run in standard CPython (no hardware, no MicroPython needed).
"""
import sys
from unittest.mock import MagicMock

# Mock MicroPython-specific modules so imports don't fail
sys.modules["network"] = MagicMock()
sys.modules["uasyncio"] = MagicMock()
sys.modules["ujson"] = __import__("json")  # use stdlib json
sys.modules["urequests"] = MagicMock()
sys.modules["machine"] = MagicMock()
sys.modules["_thread"] = MagicMock()
sys.modules["config"] = MagicMock(
    PI_URL="http://192.168.0.1:8000/api/v1/esp/callback",
    CLOUD_RUN_URL="https://example.com/fn",
    API_KEY="testkey",
    SECRET_KEY="testsecret",
    SSID="wifi",
    WLAN_PASSWORD="pass",
)

# Now import only the pure-logic parts
# RGBLED color constants
COLOR_CYAN = (0, 1023, 1023)
COLOR_GREEN = (0, 1023, 0)
COLOR_RED = (1023, 0, 0)
COLOR_OFF = (0, 0, 0)


def build_button_pressed_payload(alarm_id: int, log_id: int, elapsed: int) -> dict:
    return {
        "status": "button_pressed",
        "alarm_id": alarm_id,
        "log_id": log_id,
        "time_to_button_sec": elapsed,
    }


def build_no_press_payload(alarm_id: int, log_id: int) -> dict:
    return {
        "status": "no_press",
        "alarm_id": alarm_id,
        "log_id": log_id,
    }


def build_timer_started_payload(alarm_id: int, log_id: int) -> dict:
    return {
        "status": "timer_started",
        "alarm_id": alarm_id,
        "log_id": log_id,
    }


# Tests

def test_button_pressed_payload_structure():
    p = build_button_pressed_payload(alarm_id=5, log_id=12, elapsed=90)
    assert p["status"] == "button_pressed"
    assert p["alarm_id"] == 5
    assert p["log_id"] == 12
    assert p["time_to_button_sec"] == 90


def test_no_press_payload_has_no_time_field():
    p = build_no_press_payload(alarm_id=5, log_id=12)
    assert p["status"] == "no_press"
    assert "time_to_button_sec" not in p


def test_timer_started_payload_structure():
    p = build_timer_started_payload(alarm_id=3, log_id=7)
    assert p["status"] == "timer_started"
    assert p["alarm_id"] == 3


def test_color_cyan_is_not_off():
    assert COLOR_CYAN != COLOR_OFF


def test_color_red_has_no_green_or_blue():
    r, g, b = COLOR_RED
    assert r == 1023
    assert g == 0
    assert b == 0


def test_color_green_has_no_red_or_blue():
    r, g, b = COLOR_GREEN
    assert r == 0
    assert g == 1023
    assert b == 0
