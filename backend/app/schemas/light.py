from typing import Optional
from pydantic import BaseModel, field_validator


class LightRequest(BaseModel):
    brightness: int
    color_temp: Optional[int] = None
    hex: Optional[str] = None
    color: Optional[str] = None

    @field_validator("brightness")
    @classmethod
    def validate_brightness(cls, v: int) -> int:
        if not (10 <= v <= 1000):
            raise ValueError("brightness must be 10–1000")
        return v
