from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _to_async_url(url: str) -> str:
    # Convert sync URL to asyncpg URL if needed
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://") :]
    if url.startswith("postgres://"):
        # Heroku-style URLs
        return "postgresql+asyncpg://" + url[len("postgres://") :]
    return url


ASYNC_DATABASE_URL: str = _to_async_url(settings.DATABASE_URL)

# Create async engine
engine: AsyncEngine = create_async_engine(
    ASYNC_DATABASE_URL,
    # echo=settings.DEBUG,
    pool_pre_ping=True,
    future=True,
    connect_args={
        "server_settings": {
            "application_name": "scourt-scheduler",
        }
    },
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency:
        async def endpoint(session: AsyncSession = Depends(get_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        yield session
