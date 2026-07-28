#!/usr/bin/env python3
"""
Network-state collector — runs once per minute via log_network_data.timer.

Pings external + router, reads WiFi signal and CPU temperature, then inserts
one row into the network_log table. Idempotent within a minute (skips insert
if a row for the same minute timestamp already exists).
"""
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    from app.services.network_sampler_service import collect_sample
    from app.repositories import network_repository as repo

    sample = collect_sample()
    inserted_id = repo.insert_sample(
        timestamp=sample["timestamp"],
        connected=sample["connected"],
        wifi_signal_dBm=sample["wifi_signal_dBm"],
        ping_external_ms=sample["ping_external_ms"],
        ping_router_ms=sample["ping_router_ms"],
        temperature_C=sample["temperature_C"],
    )
    if inserted_id is None:
        logger.debug("Row for %s already present; skipping.", sample["timestamp"])
    else:
        logger.info(
            "Logged network sample id=%d ts=%s connected=%d signal=%s temp=%s",
            inserted_id, sample["timestamp"], sample["connected"],
            sample["wifi_signal_dBm"], sample["temperature_C"],
        )


if __name__ == "__main__":
    main()
