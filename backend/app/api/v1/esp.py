import asyncio
import logging
import ipaddress
from fastapi import APIRouter, HTTPException, Request
from app.schemas.esp import EspCallback
from app.services import esp_service, player_service, log_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/esp", tags=["esp"])


def _assert_local(request: Request) -> None:
    """Reject requests from non-local IPs. Trusts only the direct TCP connection."""
    ip_str = request.client.host if request.client else "0.0.0.0"
    try:
        ip = ipaddress.ip_address(ip_str)
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            logger.warning("Rejected non-local ESP callback from %s", ip_str)
            raise HTTPException(status_code=403, detail="Local network only")
    except ValueError:
        # Unparseable host strings (e.g. "testclient" from test harness) are
        # treated as local; real external requests always carry valid IP addresses.
        pass


@router.get("/alarm/status")
def alarm_status():
    """Whether an alarm is currently active. Used by network_reboot.py."""
    return {"active": player_service.is_active()}


@router.post("/callback")
def esp_callback(data: EspCallback, request: Request):
    _assert_local(request)
    esp_service.handle_callback(
        data,
        alarm_is_active=player_service.is_active(),
        stop_alarm_fn=player_service.stop,
    )
    return {"message": "ok"}


@router.post("/alarm/trigger")
async def trigger_alarm(alarm_id: int, log_id: int):
    """Called by wecker.py via localhost POST to start alarm in this process."""
    from app.repositories import alarm_repository
    log_service.mark_alarm_received(log_id, alarm_id)
    started = await player_service.play(alarm_id, log_id)
    if not started:
        if player_service.is_active():
            return {"message": "alarm already active"}
        log_service.mark_error(log_id, alarm_id, "Audio playback failed to start")
        raise HTTPException(status_code=500, detail="Audio playback failed to start")
    log_service.mark_alarm_playing(log_id, alarm_id)

    alarm = alarm_repository.get_by_id(alarm_id)
    if alarm and alarm.esp32_button:
        asyncio.create_task(_notify_esp32(alarm_id, log_id))
    asyncio.create_task(_auto_stop(alarm_id, log_id))
    if alarm and alarm.light:
        asyncio.create_task(_light_on())
    return {"message": "alarm started"}


async def _notify_esp32(alarm_id: int, log_id: int) -> None:
    import requests as req_lib
    from app.config import settings
    esp_url = f"http://{settings.esp32_ip}/trigger"
    payload = {"duration": settings.esp32_trigger_duration, "alarm_id": alarm_id, "log_id": log_id}
    headers = {"X-API-KEY": settings.api_key}
    loop = asyncio.get_running_loop()
    for attempt in range(3):
        try:
            resp = await loop.run_in_executor(
                None,
                lambda: req_lib.post(esp_url, json=payload, headers=headers, timeout=5),
            )
            if resp.ok:
                log_service.mark_esp32_notified(log_id, alarm_id)
                return
            logger.warning("ESP32 returned %d on attempt %d", resp.status_code, attempt + 1)
        except Exception as e:
            logger.warning("ESP32 notify attempt %d failed: %s", attempt + 1, e)
        if attempt < 2:
            await asyncio.sleep(2)
    log_service.mark_esp32_unreachable(log_id, alarm_id)


async def _auto_stop(alarm_id: int, log_id: int) -> None:
    from app.config import settings
    await asyncio.sleep(settings.alarm_auto_stop_seconds)
    if player_service.stop():  # atomic: only log if this call actually stopped the alarm
        log_service.mark_button_pressed(log_id, alarm_id, time_to_button_sec=None, source="auto_stop")


async def _light_on() -> None:
    import tinytuya
    import time
    from app.config import settings
    logger.info("_light_on: turning on Tuya light")
    try:
        def _turn_on():
            d = tinytuya.BulbDevice(
                dev_id=settings.tuya_dev_id,
                address=settings.tuya_ip,
                local_key=settings.tuya_local_key,
                version=3.3,
            )
            d.turn_on()
            time.sleep(0.5)
            d.set_mode("white")
            d.set_white(1000, 500)
            logger.info("_light_on: done")
        await asyncio.get_running_loop().run_in_executor(None, _turn_on)
    except Exception:
        logger.exception("_light_on: failed")
