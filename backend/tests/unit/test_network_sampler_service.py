from app.services.network_sampler_service import (
    parse_ping_latency_ms,
    parse_wifi_signal_dbm,
    parse_temperature_c,
)


def test_parse_ping_latency_from_rtt_line():
    output = (
        "PING 8.8.8.8 (8.8.8.8) 56(84) bytes of data.\n"
        "64 bytes from 8.8.8.8: icmp_seq=1 ttl=117 time=14.2 ms\n"
        "\n"
        "--- 8.8.8.8 ping statistics ---\n"
        "1 packets transmitted, 1 received, 0% packet loss, time 0ms\n"
        "rtt min/avg/max/mdev = 14.207/14.207/14.207/0.000 ms\n"
    )
    assert parse_ping_latency_ms(output) == "14.207 ms"


def test_parse_ping_latency_from_time_field_only():
    output = "64 bytes from 192.168.0.1: icmp_seq=1 ttl=64 time=2.41 ms\n"
    assert parse_ping_latency_ms(output) == "2.41 ms"


def test_parse_ping_latency_no_match_returns_na():
    assert parse_ping_latency_ms("network unreachable") == "N/A"
    assert parse_ping_latency_ms("") == "N/A"


def test_parse_wifi_signal_dbm():
    output = (
        "wlan0     IEEE 802.11  ESSID:\"Home\"\n"
        "          Mode:Managed  Frequency:2.412 GHz  Access Point: AA:BB:CC:DD:EE:FF\n"
        "          Bit Rate=54 Mb/s   Tx-Power=20 dBm\n"
        "          Link Quality=58/70  Signal level=-52 dBm\n"
    )
    assert parse_wifi_signal_dbm(output) == "-52"


def test_parse_wifi_signal_dbm_no_match():
    assert parse_wifi_signal_dbm("no such interface") == "N/A"


def test_parse_temperature_c():
    assert parse_temperature_c("temp=49.4'C") == "49.4"
    assert parse_temperature_c("temp=72.1'C\n") == "72.1"


def test_parse_temperature_c_no_match():
    assert parse_temperature_c("") == "N/A"
    assert parse_temperature_c("error") == "N/A"
