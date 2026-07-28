from fastapi import APIRouter
from app.api.v1 import alarms, logs, esp, light, network, reboot_history, test_triggers

router = APIRouter(prefix="/api/v1")
router.include_router(alarms.router)
router.include_router(logs.router)
router.include_router(esp.router)
router.include_router(light.router)
router.include_router(network.router)
router.include_router(network.alias_router)
router.include_router(reboot_history.router)
router.include_router(test_triggers.router)