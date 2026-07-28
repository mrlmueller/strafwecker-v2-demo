from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    api_key: str
    tuya_dev_id: str
    tuya_local_key: str
    tuya_ip: str
    esp32_ip: str
    database_path: Path = Path("/home/pi/strafwecker/backend/data/strafwecker.db")
    alarm_sound_path: Path = Path("/home/pi/strafwecker/backend/alarm.wav")
    esp32_trigger_duration: int = 300
    alarm_auto_stop_seconds: int = 600

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
