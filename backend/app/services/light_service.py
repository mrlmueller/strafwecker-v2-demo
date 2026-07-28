import logging
from typing import Optional
from app.schemas.light import LightRequest

logger = logging.getLogger(__name__)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))


def interpolate_hex(start_hex: str, end_hex: str, fraction: float) -> str:
    fraction = max(0.0, min(1.0, fraction))
    sr, sg, sb = hex_to_rgb(start_hex)
    er, eg, eb = hex_to_rgb(end_hex)
    r = int(sr + (er - sr) * fraction)
    g = int(sg + (eg - sg) * fraction)
    b = int(sb + (eb - sb) * fraction)
    return f"#{r:02X}{g:02X}{b:02X}"


def _hsv_to_rgb(h: int, s: int, v: int) -> tuple[int, int, int]:
    s_f = s / 1000.0
    v_f = v / 1000.0
    h_mod = h % 360
    c = v_f * s_f
    x = c * (1 - abs((h_mod / 60.0) % 2 - 1))
    m = v_f - c
    if 0 <= h_mod < 60:
        rp, gp, bp = c, x, 0.0
    elif 60 <= h_mod < 120:
        rp, gp, bp = x, c, 0.0
    elif 120 <= h_mod < 180:
        rp, gp, bp = 0.0, c, x
    elif 180 <= h_mod < 240:
        rp, gp, bp = 0.0, x, c
    elif 240 <= h_mod < 300:
        rp, gp, bp = x, 0.0, c
    else:
        rp, gp, bp = c, 0.0, x
    return int((rp + m) * 255), int((gp + m) * 255), int((bp + m) * 255)


COLOR_RATIO = 15 / 35
WHITE_RATIO = 20 / 35
START_HEX = "#050501"
END_HEX = "#fff1a6"
WHITE_COLOR_TEMP = 350
MIN_BRIGHTNESS = 10  # /light schema minimum; used both for color-phase fixed brightness and as the white-phase ramp floor.


def compute_sunrise_payload(remaining_seconds: int, total_seconds: int) -> dict:
    """Pure function: derive the bulb command for one sunrise tick.

    Two phases over total_seconds:
      • Color phase (first 15/35 of total): hex interpolated START_HEX → END_HEX, brightness fixed at 10.
      • White phase (last 20/35 of total): white mode, brightness 10 → 1000 at color_temp 350.
    """
    total_white_s = total_seconds * WHITE_RATIO
    total_color_s = total_seconds * COLOR_RATIO

    if remaining_seconds > total_white_s:
        elapsed_in_color = (total_seconds - remaining_seconds)
        fraction = elapsed_in_color / total_color_s if total_color_s > 0 else 0.0
        fraction = max(0.0, min(1.0, fraction))
        return {"hex": interpolate_hex(START_HEX, END_HEX, fraction),
                "brightness": MIN_BRIGHTNESS}

    if total_white_s <= 0:
        return {"brightness": 1000, "color_temp": WHITE_COLOR_TEMP}
    fraction = (total_white_s - remaining_seconds) / total_white_s
    fraction = max(0.0, min(1.0, fraction))
    brightness = max(MIN_BRIGHTNESS, int(1000 * fraction))
    return {"brightness": brightness, "color_temp": WHITE_COLOR_TEMP}


def apply_light(req: LightRequest) -> dict:
    """Send light command to Tuya device. Imports tinytuya at call time."""
    import tinytuya
    from app.config import settings

    d = tinytuya.BulbDevice(
        dev_id=settings.tuya_dev_id,
        address=settings.tuya_ip,
        local_key=settings.tuya_local_key,
        version=3.3,
    )
    status = d.status()
    dps = status.get("dps", {})
    is_on = dps.get("20", False)
    current_mode = dps.get("21", "white")

    if req.hex:
        r, g, b = hex_to_rgb(req.hex)
        if current_mode != "colour":
            d.set_mode("colour", nowait=True)
        d.set_colour(r, g, b, nowait=True)
        if not is_on:
            d.turn_on()
        return {"mode": "colour", "rgb": [r, g, b], "hex": req.hex}

    elif req.color:
        h_val, s_val = 0, 1000
        for part in req.color.split(","):
            kv = part.strip().split(":")
            if len(kv) == 2:
                if kv[0] == "h":
                    h_val = int(kv[1])
                elif kv[0] == "s":
                    s_val = int(kv[1])
        r, g, b = _hsv_to_rgb(h_val, s_val, req.brightness)
        if current_mode != "colour":
            d.set_mode("colour", nowait=True)
        d.set_colour(r, g, b, nowait=True)
        if not is_on:
            d.turn_on()
        return {"mode": "colour", "rgb": [r, g, b]}

    else:
        color_temp = req.color_temp or 500
        if current_mode != "white":
            d.set_mode("white", nowait=True)
        d.set_white(req.brightness, color_temp, nowait=True)
        return {"mode": "white", "brightness": req.brightness, "color_temp": color_temp}
