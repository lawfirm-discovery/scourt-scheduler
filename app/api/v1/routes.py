from fastapi import APIRouter

router = APIRouter()


@router.get("/ping", tags=["Utility"])
async def ping() -> dict:
    return {"message": "pong"}


# Top-level API router to aggregate sub-routers as the project grows
api_router = APIRouter()
api_router.include_router(router)
