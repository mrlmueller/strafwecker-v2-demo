import hmac
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


class APIKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        from app.config import settings
        provided = request.headers.get("x-api-key", "")
        if not hmac.compare_digest(provided.encode(), settings.api_key.encode()):
            logger.warning("Rejected request with invalid API key from %s", request.client)
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)