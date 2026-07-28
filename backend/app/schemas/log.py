from typing import Optional
from pydantic import BaseModel


class LogResponse(BaseModel):
    id: int
    timestamp: str
    last_update: str
    alarm_id: int
    state: str
    time_to_button_sec: Optional[int] = None
    pressed_in_time: Optional[bool] = None
    error_details: Optional[str] = None
    notes: Optional[str] = None
