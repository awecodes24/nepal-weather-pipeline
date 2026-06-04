from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str 
    API_KEY: str = ""
    class Config:
        env_file = ".env"

settings = Settings()

# asyncpg driver - non-blocking PostgreSQL I/O
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False, # set True to log all SQL
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)

class Base(DeclarativeBase):
    pass

async def get_db():
    """FastAPI dependency - yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        
    