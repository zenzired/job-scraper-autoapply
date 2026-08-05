import os
from typing import AsyncGenerator
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from src.db.models import Base

# Load environment variables from .env file
load_dotenv()

# Get DB URL from environment or fall back to local docker default
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql+asyncpg://postgres:postgrespassword@localhost:5432/job_sandbox"
)

# Initialize Async Engine
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,  # Set to True if you want to see raw SQL logs in terminal
    future=True
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def init_db():
    """Utility function to create all tables (used for initial setup/testing)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency generator that yields an async database session and handles cleanup."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()