from app.config import settings


def test_settings_loads():
    assert settings.api_key is not None
    assert settings.database_path is not None
