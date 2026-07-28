from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException
from app.schemas.alarm import AlarmCreate, AlarmUpdate, AlarmResponse
from app.repositories import alarm_repository as repo

router = APIRouter(prefix="/alarms", tags=["alarms"])


def _next_wecker_fire_at_or_after(dt: datetime) -> datetime:
    """Smallest datetime >= dt with second=1, microsecond=0 (the wecker.timer schedule)."""
    candidate = dt.replace(second=1, microsecond=0)
    return candidate if candidate >= dt else candidate + timedelta(minutes=1)


def _compute_nap_target_at(duration_minutes: int) -> str:
    """ISO datetime for now + duration, snapped to the next *:*:01 wecker firing.

    Aligning the target to the firing schedule makes the UI countdown reach 0:00
    at the same instant the alarm actually rings, eliminating an up-to-59-second
    "stuck at 0:00" wait at the end of the timer.
    """
    target = _next_wecker_fire_at_or_after(datetime.now() + timedelta(minutes=duration_minutes))
    return target.isoformat(timespec="seconds")


def _alarm_to_response(alarm) -> dict:
    return {
        "id": alarm.id, "time": alarm.time, "days_of_week": alarm.days_of_week,
        "enabled": alarm.enabled, "repeat_type": alarm.repeat_type,
        "label": alarm.label, "light": alarm.light,
        "light_fade_minutes": alarm.light_fade_minutes,
        "kind": alarm.kind, "nap_target_at": alarm.nap_target_at,
        "nap_duration_minutes": alarm.nap_duration_minutes,
        "esp32_button": alarm.esp32_button,
    }


@router.get("/", response_model=list[AlarmResponse])
def list_alarms():
    return [_alarm_to_response(a) for a in repo.get_all()]


@router.get("/{alarm_id}", response_model=AlarmResponse)
def get_alarm(alarm_id: int):
    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    return _alarm_to_response(alarm)


@router.post("/", status_code=201)
def create_alarm(data: AlarmCreate):
    nap_target_at = data.nap_target_at
    if data.kind == "nap" and nap_target_at is None and data.nap_duration_minutes is not None:
        nap_target_at = _compute_nap_target_at(data.nap_duration_minutes)
    alarm_id = repo.create(
        time=data.time, days_of_week=data.days_of_week,
        enabled=data.enabled, repeat_type=data.repeat_type,
        label=data.label, light=data.light,
        light_fade_minutes=data.light_fade_minutes,
        kind=data.kind, nap_target_at=nap_target_at,
        nap_duration_minutes=data.nap_duration_minutes,
        esp32_button=data.esp32_button,
    )
    return {"message": "Alarm created", "alarm_id": alarm_id}


@router.put("/{alarm_id}")
def update_alarm(alarm_id: int, data: AlarmUpdate):
    if not repo.get_by_id(alarm_id):
        raise HTTPException(status_code=404, detail="Alarm not found")
    repo.update(
        alarm_id, data.time, data.days_of_week, data.enabled,
        data.repeat_type, data.label, data.light, data.light_fade_minutes,
        kind=data.kind, nap_target_at=data.nap_target_at,
        nap_duration_minutes=data.nap_duration_minutes,
        esp32_button=data.esp32_button,
    )
    return {"message": "Alarm updated"}


@router.delete("/{alarm_id}")
def delete_alarm(alarm_id: int):
    if not repo.get_by_id(alarm_id):
        raise HTTPException(status_code=404, detail="Alarm not found")
    repo.delete(alarm_id)
    return {"message": "Alarm deleted"}


@router.post("/{alarm_id}/restart")
def restart_nap(alarm_id: int):
    alarm = repo.get_by_id(alarm_id)
    if not alarm:
        raise HTTPException(status_code=404, detail="Alarm not found")
    if alarm.kind != "nap" or alarm.nap_duration_minutes is None:
        raise HTTPException(status_code=400, detail="Restart only valid for naps with a duration")
    new_target = _compute_nap_target_at(alarm.nap_duration_minutes)
    repo.update(
        alarm_id, alarm.time, alarm.days_of_week, True,
        alarm.repeat_type, alarm.label, alarm.light, alarm.light_fade_minutes,
        kind=alarm.kind, nap_target_at=new_target,
        nap_duration_minutes=alarm.nap_duration_minutes,
        esp32_button=alarm.esp32_button,
    )
    return {"message": "Nap restarted", "target_at": new_target}
