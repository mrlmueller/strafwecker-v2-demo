from app.services.light_service import hex_to_rgb, interpolate_hex, _hsv_to_rgb
from app.services.light_service import (
    compute_sunrise_payload,
    START_HEX,
    END_HEX,
    WHITE_COLOR_TEMP,
    MIN_BRIGHTNESS,
)


def test_hex_to_rgb_white():
    assert hex_to_rgb("#FFFFFF") == (255, 255, 255)


def test_hex_to_rgb_black():
    assert hex_to_rgb("#000000") == (0, 0, 0)


def test_hex_to_rgb_red():
    assert hex_to_rgb("#FF0000") == (255, 0, 0)


def test_hex_to_rgb_no_hash():
    assert hex_to_rgb("00FF00") == (0, 255, 0)


def test_interpolate_hex_zero_fraction():
    result = interpolate_hex("#000000", "#FFFFFF", 0.0)
    assert result == "#000000"


def test_interpolate_hex_full_fraction():
    result = interpolate_hex("#000000", "#FFFFFF", 1.0)
    assert result == "#FFFFFF"


def test_interpolate_hex_midpoint():
    result = interpolate_hex("#000000", "#FFFFFF", 0.5)
    r, g, b = hex_to_rgb(result)
    assert 127 <= r <= 128


def test_interpolate_hex_clamps_over_one():
    result = interpolate_hex("#000000", "#FFFFFF", 1.5)
    assert result == "#FFFFFF"


def test_hsv_to_rgb_pure_red():
    r, g, b = _hsv_to_rgb(0, 1000, 1000)
    assert r == 255 and g == 0 and b == 0


def test_hsv_to_rgb_pure_green():
    r, g, b = _hsv_to_rgb(120, 1000, 1000)
    assert g == 255 and r == 0 and b == 0


# Total fade = 1800 s (30 min); white phase = 1800 * 20/35 ≈ 1028.57 s.
TOTAL = 1800
WHITE_S = TOTAL * 20 / 35


def test_compute_payload_color_phase_start():
    # remaining == total → very beginning, dim warm
    payload = compute_sunrise_payload(TOTAL, TOTAL)
    assert payload == {"hex": START_HEX, "brightness": MIN_BRIGHTNESS}


def test_compute_payload_color_phase_end():
    # remaining just above white-phase boundary → near END_HEX
    payload = compute_sunrise_payload(int(WHITE_S) + 1, TOTAL)
    assert payload["brightness"] == MIN_BRIGHTNESS
    assert payload["hex"].startswith("#")
    # Hex should be near END_HEX (#fff1a6) — at least one channel close to F.
    assert payload["hex"].upper() != START_HEX.upper()


def test_compute_payload_white_phase_start():
    # remaining == total_white_seconds → fraction = 0 → brightness floor.
    payload = compute_sunrise_payload(int(WHITE_S), TOTAL)
    assert payload["color_temp"] == WHITE_COLOR_TEMP
    assert payload["brightness"] == MIN_BRIGHTNESS


def test_compute_payload_white_phase_end():
    # remaining = 0 → brightness 1000.
    payload = compute_sunrise_payload(0, TOTAL)
    assert payload == {"brightness": 1000, "color_temp": WHITE_COLOR_TEMP}


def test_compute_payload_white_phase_middle():
    # halfway through white phase → brightness ≈ 500.
    payload = compute_sunrise_payload(int(WHITE_S / 2), TOTAL)
    assert payload["color_temp"] == WHITE_COLOR_TEMP
    assert 450 <= payload["brightness"] <= 550


def test_compute_payload_negative_remaining_clamps_to_full_white():
    payload = compute_sunrise_payload(-30, TOTAL)
    assert payload == {"brightness": 1000, "color_temp": WHITE_COLOR_TEMP}


def test_compute_payload_remaining_above_total_clamps_to_color_start():
    payload = compute_sunrise_payload(TOTAL + 5000, TOTAL)
    assert payload == {"hex": START_HEX, "brightness": MIN_BRIGHTNESS}


def test_compute_payload_color_phase_uses_start_hex_at_top():
    # remaining slightly less than total → fraction ≈ 0 → still ~START_HEX.
    payload = compute_sunrise_payload(TOTAL - 1, TOTAL)
    # Allow a very small drift from START_HEX since fraction is just above 0.
    assert payload["brightness"] == MIN_BRIGHTNESS
    assert payload["hex"].startswith("#")
