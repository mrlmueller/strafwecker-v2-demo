from typing import Literal, Optional
from pydantic import BaseModel


class EspCallback(BaseModel):
    status: Literal["button_pressed", "no_press", "timer_started"]
    alarm_id: int
    log_id: int
    time_to_button_sec: Optional[int] = None
    start_time: Optional[float] = None
