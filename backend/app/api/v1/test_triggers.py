import asyncio
import logging
from fastapi import APIRouter
from app.services import player_service
from app.services.light_service import apply_light
from app.schemas.light import LightRequest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/test", tags=["test"])


@router.post("/ring")
async def test_ring():
    """Start alarm sound (plays until /test/ring-stop or auto-stops after 30s)."""
    started = await player_service.play(alarm_id=0, log_id=0)
    if not started:
        return {"message": "alarm already active"}
    asyncio.create_task(_auto_stop_test())
    return {"message": "alarm started — call POST /api/v1/test/ring-stop to stop early"}


@router.post("/ring-stop")
def test_ring_stop():
    """Stop alarm sound."""
    player_service.stop()
    return {"message": "alarm stopped"}


@router.post("/light-on")
def test_light_on():
    """Turn Tuya light on at full white brightness."""
    try:
        import tinytuya
        import time
        from app.config import settings
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
        return {"message": "light on — full white brightness"}
    except Exception as e:
        logger.exception("test_light_on failed")
        return {"message": f"error: {e}"}


@router.post("/light-off")
def test_light_off():
    """Turn Tuya light off."""
    try:
        import tinytuya
        from app.config import settings
        d = tinytuya.BulbDevice(
            dev_id=settings.tuya_dev_id,
            address=settings.tuya_ip,
            local_key=settings.tuya_local_key,
            version=3.3,
        )
        d.turn_off()
        return {"message": "light off"}
    except Exception as e:
        logger.exception("test_light_off failed")
        return {"message": f"error: {e}"}


async def _auto_stop_test():
    await asyncio.sleep(30)
    if player_service.is_active():
        player_service.stop()
