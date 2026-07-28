from fastapi import APIRouter
from app.schemas.log import LogResponse
from app.repositories import log_repository as repo

router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("/", response_model=list[LogResponse])
def get_logs(limit: int = 10):
    limit = min(max(limit, 1), 100)
    logs = repo.get_recent(limit)
    return [
        {
            "id": l.id, "timestamp": l.timestamp, "last_update": l.last_update,
            "alarm_id": l.alarm_id, "state": l.state,
            "time_to_button_sec": l.time_to_button_sec,
            "pressed_in_time": l.pressed_in_time,
            "error_details": l.error_details, "notes": l.notes,
        }
        for l in logs
    ]
