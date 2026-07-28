import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.middleware import APIKeyMiddleware
from app.api.v1.router import router
from app.services import player_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Strafwecker API")
    # Reap any alarm-audio player left behind by a previous (crashed/redeployed)
    # process so a restart always starts from a clean, silent state.
    player_service.cleanup_orphans()
    player_service.setup_gpio()
    yield
    logger.info("Shutting down Strafwecker API")
    # Don't leave a forever-looping player orphaned when this process exits.
    player_service.cleanup_orphans()


app = FastAPI(title="Strafwecker API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://raspberryalarm.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APIKeyMiddleware)
app.include_router(router)
