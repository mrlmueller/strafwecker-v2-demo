import logging
from app.schemas.esp import EspCallback
from app.services import log_service

logger = logging.getLogger(__name__)


def handle_callback(data: EspCallback, alarm_is_active: bool, stop_alarm_fn) -> None:
    """
    Process an ESP32 status callback.
    alarm_is_active: current value from player_service.is_active()
    stop_alarm_fn: callable — player_service.stop() which returns bool
    """
    if data.status == "timer_started":
        log_service.mark_timer_started(data.log_id, data.alarm_id)
        logger.info("ESP32 timer started for alarm %d", data.alarm_id)

    elif data.status == "button_pressed":
        if alarm_is_active:
            stopped = stop_alarm_fn()
            if stopped:
                log_service.mark_button_pressed(
                    data.log_id, data.alarm_id,
                    time_to_button_sec=data.time_to_button_sec,
                    source="esp32",
                )
                logger.info("Alarm stopped via ESP32 button press.")
            else:
                # Another source (GPIO / auto_stop) already stopped it in the same instant.
                logger.info("ESP32 button pressed but alarm was stopped by another source simultaneously.")
        else:
            # Alarm was already stopped before the callback arrived; still record it.
            log_service.mark_button_pressed(
                data.log_id, data.alarm_id,
                time_to_button_sec=data.time_to_button_sec,
                source="esp32",
            )
            logger.info("ESP32 button pressed but alarm was already stopped.")

    elif data.status == "no_press":
        log_service.mark_no_press(data.log_id, data.alarm_id)
        logger.info("ESP32 reported no button press for alarm %d", data.alarm_id)
