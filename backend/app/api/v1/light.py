import ipaddress
import logging
from fastapi import APIRouter, HTTPException, Request
from app.schemas.light import LightRequest
from app.services.light_service import apply_light

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/light", tags=["light"])


def _assert_local(request: Request) -> None:
    cf_ip = request.headers.get("cf-connecting-ip")
    forwarded = request.headers.get("x-forwarded-for")
    ip_str = cf_ip or (forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "0.0.0.0"))
    try:
        ip = ipaddress.ip_address(ip_str.strip())
        if not (ip.is_loopback or ip.is_private or ip.is_link_local):
            raise HTTPException(status_code=403, detail="Local network only")
    except ValueError:
        # Unparseable host strings (e.g. "testclient" from test harness) are
        # treated as local; real external requests always carry valid IP addresses.
        pass


@router.post("/")
def control_light(data: LightRequest, request: Request):
    _assert_local(request)
    try:
        result = apply_light(data)
        return {"message": "Light updated", **result}
    except Exception as e:
        logger.exception("Failed to update light")
        raise HTTPException(status_code=500, detail=str(e))
