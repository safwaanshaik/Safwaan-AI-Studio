"""
SAFWAAN AI STUDIO - Database Connection Management
Enterprise-grade database setup with async SQLAlchemy and connection pooling.

This module provides:
- Async SQLAlchemy engine configuration
- Connection pooling and health checks
- Database session management
- Migration support with Alembic
- Database health monitoring
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool
from sqlalchemy import text, event

from app.core.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """Base class for all database models."""
    pass


# Global database engine instance
_engine: Optional[AsyncEngine] = None

# Async session factory
async_session_maker: Optional[async_sessionmaker[AsyncSession]] = None


async def create_engine() -> AsyncEngine:
    """
    Create and configure the async SQLAlchemy engine.

    Returns:
        AsyncEngine: Configured database engine
    """
    global _engine

    if _engine is not None:
        return _engine

    # Database URL for async driver
    database_url = settings.DATABASE_URL
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Engine configuration
    engine_kwargs = {
        "echo": settings.ENVIRONMENT == "development",
        "poolclass": AsyncAdaptedQueuePool,
        "pool_size": 20,  # Maximum number of connections in the pool
        "max_overflow": 30,  # Maximum number of connections that can be created beyond pool_size
        "pool_timeout": 30,  # Timeout for getting a connection from the pool
        "pool_recycle": 3600,  # Recycle connections after 1 hour
        "pool_pre_ping": True,  # Enable connection health checks
        "connect_args": {
            "server_settings": {
                "application_name": f"Safwaan AI Studio {settings.VERSION}",
                "timezone": "UTC",
            }
        }
    }

    # Create engine
    _engine = create_async_engine(database_url, **engine_kwargs)

    # Add event listeners for monitoring
    @event.listens_for(_engine.sync_engine, "connect")
    def connect(dbapi_connection, connection_record):
        """Log database connections."""
        logger.debug("Database connection established")

    @event.listens_for(_engine.sync_engine, "checkout")
    def checkout(dbapi_connection, connection_record, connection_proxy):
        """Log connection checkouts."""
        logger.debug("Database connection checked out from pool")

    @event.listens_for(_engine.sync_engine, "checkin")
    def checkin(dbapi_connection, connection_record):
        """Log connection checkins."""
        logger.debug("Database connection returned to pool")

    logger.info("Database engine created successfully")
    return _engine


async def create_session_maker() -> async_sessionmaker[AsyncSession]:
    """
    Create async session maker.

    Returns:
        async_sessionmaker: Configured session factory
    """
    global async_session_maker

    if async_session_maker is not None:
        return async_session_maker

    engine = await create_engine()

    # Session configuration
    async_session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,  # Keep objects loaded after commit
        autoflush=False,  # Don't auto-flush on access
    )

    logger.info("Database session maker created successfully")
    return async_session_maker


async def create_tables() -> None:
    """
    Create all database tables defined in models.

    This function should be called during application startup.
    """
    try:
        engine = await create_engine()
        async with engine.begin() as conn:
            # Import all models to ensure they are registered
            from app.db import models  # noqa: F401
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create database tables: {e}")
        raise


async def drop_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use with caution.
    """
    try:
        engine = await create_engine()
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        logger.warning("Database tables dropped successfully")

    except Exception as e:
        logger.error(f"Failed to drop database tables: {e}")
        raise


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function for getting database session.

    Yields:
        AsyncSession: Database session
    """
    if async_session_maker is None:
        await create_session_maker()

    session = async_session_maker()
    try:
        yield session
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def health_check() -> dict:
    """
    Perform database health check.

    Returns:
        dict: Health check results
    """
    try:
        engine = await create_engine()
        async with engine.begin() as conn:
            # Simple query to test connection
            result = await conn.execute(text("SELECT 1 as health_check"))
            row = result.fetchone()

            if row and row[0] == 1:
                return {
                    "status": "healthy",
                    "database": settings.POSTGRES_DB,
                    "host": settings.POSTGRES_SERVER,
                    "pool_size": engine.pool.size(),
                    "checked_connections": engine.pool.checkedin(),
                }
            else:
                return {
                    "status": "unhealthy",
                    "error": "Health check query failed"
                }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


async def get_connection_info() -> dict:
    """
    Get database connection information.

    Returns:
        dict: Connection details
    """
    try:
        engine = await create_engine()
        pool = engine.pool

        return {
            "database_url": settings.DATABASE_URL.replace(settings.POSTGRES_PASSWORD, "***"),
            "pool_size": pool.size(),
            "checked_in": pool.checkedin(),
            "checked_out": pool.checkedout(),
            "invalid": pool.invalid(),
            "overflow": pool.overflow(),
            "timeout": pool.timeout,
        }

    except Exception as e:
        logger.error(f"Failed to get connection info: {e}")
        return {"error": str(e)}


async def execute_raw_query(query: str, params: Optional[dict] = None) -> list:
    """
    Execute a raw SQL query.

    Args:
        query: SQL query string
        params: Query parameters

    Returns:
        list: Query results
    """
    try:
        async with get_db() as session:
            result = await session.execute(text(query), params or {})
            return result.fetchall()

    except Exception as e:
        logger.error(f"Raw query execution failed: {e}")
        raise


async def init_database() -> None:
    """
    Initialize database components.

    This function should be called during application startup.
    """
    try:
        # Create engine and session maker
        await create_engine()
        await create_session_maker()

        # Create tables
        await create_tables()

        # Perform initial health check
        health = await health_check()
        if health["status"] != "healthy":
            raise Exception(f"Database health check failed: {health}")

        logger.info("Database initialization completed successfully")

    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


async def close_database() -> None:
    """
    Close database connections.

    This function should be called during application shutdown.
    """
    global _engine, async_session_maker

    try:
        if _engine:
            await _engine.dispose()
            _engine = None
            async_session_maker = None

        logger.info("Database connections closed successfully")

    except Exception as e:
        logger.error(f"Error closing database connections: {e}")
        raise


# Export commonly used functions
__all__ = [
    "Base",
    "get_db",
    "create_tables",
    "drop_tables",
    "health_check",
    "get_connection_info",
    "execute_raw_query",
    "init_database",
    "close_database",
]