from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.api.v1.routes import api_router
from app.service.scheduler import SupremeCourtScheduler


import logging
from logging.handlers import TimedRotatingFileHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        TimedRotatingFileHandler(
            "scheduler.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    나의사건정보 스케줄러를 시작하고 종료하는 생명주기 관리
    """

    scheduler = SupremeCourtScheduler()
    await scheduler.start()
    try:
        yield
    finally:
        await scheduler.shutdown()


app = FastAPI(lifespan=lifespan)


@app.get("/health", tags=["Health"])
async def health() -> dict:
    return {"status": "ok", "app": "scourt-scheduler"}


app.include_router(api_router, prefix="/api/v1")
