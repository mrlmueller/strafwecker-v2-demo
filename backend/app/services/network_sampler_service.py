"""Collect one network-state sample (ping, WiFi signal, CPU temp) for the log."""
import logging
import re
import subprocess
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_PING_EXTERNAL_TARGET = "8.8.8.8"
_IWCONFIG_INTERFACE = "wlan0"


def _run(cmd: list[str], timeout: float = 5.0) -> str:
    """Run a subprocess, return stdout (stripped), or empty on any failure."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return ""


def _default_router_ip() -> Optional[str]:
    """Read the default-route gateway IP (e.g. '192.168.178.1'). None if unavailable."""
    out = _run(["ip", "route"], timeout=2.0)
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "default":
            try:
                return parts[parts.index("via") + 1]
            except (ValueError, IndexError):
                return None
    return None


def parse_ping_latency_ms(output: str) -> str:
    """Extract latency from `ping -c1` output. Returns e.g. '24.2 ms' or 'N/A'."""
    m = re.search(r"rtt min/avg/max/[a-z]+\s*=\s*[\d.]+/([\d.]+)/", output)
    if m:
        return f"{m.group(1)} ms"
    m = re.search(r"time=([\d.]+)\s*ms", output)
    if m:
        return f"{m.group(1)} ms"
    return "N/A"


def parse_wifi_signal_dbm(output: str) -> str:
    """Extract `Signal level=-NN dBm` from iwconfig output. Returns 'NN' or 'N/A'."""
    m = re.search(r"Signal level\s*=\s*(-?\d+)\s*dBm", output, re.IGNORECASE)
    return m.group(1) if m else "N/A"


def parse_temperature_c(output: str) -> str:
    """Extract C from `vcgencmd measure_temp` output `temp=49.4'C`. Returns '49.4' or 'N/A'."""
    m = re.search(r"temp=([\d.]+)", output)
    return m.group(1) if m else "N/A"


def collect_sample() -> dict:
    """Run pings + sensors. Returns {timestamp, connected, wifi_signal_dBm, ping_external_ms,
    ping_router_ms, temperature_C}, timestamp truncated to minute precision."""
    now_iso = datetime.now().replace(second=0, microsecond=0).isoformat()

    external = _run(["ping", "-c", "1", "-W", "3", _PING_EXTERNAL_TARGET])
    ping_external_ms = parse_ping_latency_ms(external)

    router_ip = _default_router_ip()
    if router_ip:
        router = _run(["ping", "-c", "1", "-W", "3", router_ip])
        ping_router_ms = parse_ping_latency_ms(router)
    else:
        ping_router_ms = "N/A"

    wifi = _run(["iwconfig", _IWCONFIG_INTERFACE], timeout=3.0)
    wifi_signal_dBm = parse_wifi_signal_dbm(wifi)

    temp = _run(["vcgencmd", "measure_temp"], timeout=2.0)
    temperature_C = parse_temperature_c(temp)

    return {
        "timestamp": now_iso,
        "connected": 1 if ping_external_ms != "N/A" else 0,
        "wifi_signal_dBm": wifi_signal_dBm,
        "ping_external_ms": ping_external_ms,
        "ping_router_ms": ping_router_ms,
        "temperature_C": temperature_C,
    }
