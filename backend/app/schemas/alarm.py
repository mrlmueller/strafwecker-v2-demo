import re
from typing import Optional
from pydantic import BaseModel, field_validator, model_validator


class AlarmCreate(BaseModel):
    time: str
    days_of_week: list[int] = []
    enabled: bool = True
    repeat_type: str = "once"
    label: Optional[str] = None
    light: bool = False
    light_fade_minutes: int = 0
    kind: str = "alarm"
    nap_target_at: Optional[str] = None
    nap_duration_minutes: Optional[int] = None
    esp32_button: bool = True

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("time must be HH:MM format")
        h, m = int(v[:2]), int(v[3:])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError("invalid time value")
        return v

    @field_validator("days_of_week")
    @classmethod
    def validate_days(cls, v: list[int]) -> list[int]:
        if not all(0 <= d <= 6 for d in v):
            raise ValueError("days_of_week must be integers 0–6")
        return sorted(set(v))

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in ("alarm", "nap"):
            raise ValueError("kind must be 'alarm' or 'nap'")
        return v

    @model_validator(mode="after")
    def validate_nap_constraints(self):
        if self.kind == "nap":
            if self.nap_duration_minutes is None:
                raise ValueError("nap_duration_minutes is required when kind='nap'")
            if not (1 <= self.nap_duration_minutes <= 60):
                raise ValueError("nap_duration_minutes must be between 1 and 60")
        return self


class AlarmUpdate(AlarmCreate):
    pass


class AlarmResponse(BaseModel):
    id: int
    time: str
    days_of_week: list[int]
    enabled: bool
    repeat_type: str
    label: Optional[str]
    light: bool
    light_fade_minutes: int
    kind: str
    nap_target_at: Optional[str]
    nap_duration_minutes: Optional[int]
    esp32_button: bool
