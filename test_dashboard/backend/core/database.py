"""
Database connection and initialization for Test Dashboard
Provides optional database support - falls back to in-memory storage if dependencies unavailable
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Try to import database dependencies
DATABASE_AVAILABLE = False
try:
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
    from sqlalchemy.pool import NullPool
    import asyncpg
    DATABASE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Database dependencies not available: {e}")
    logger.info("Test dashboard will run in memory-only mode")
    AsyncSession = None
    create_async_engine = None
    async_sessionmaker = None
    asyncpg = None

from test_dashboard.backend.core.config import settings

# Initialize database components only if available
engine = None
AsyncSessionLocal = None

if DATABASE_AVAILABLE:
    try:
        # Create async engine
        engine = create_async_engine(
            settings.database_url,
            echo=settings.DEBUG,
            poolclass=NullPool,  # Use NullPool for better connection management
            future=True
        )

        # Create async session factory
        AsyncSessionLocal = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("Database components initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database components: {e}")
        DATABASE_AVAILABLE = False


async def init_db():
    """Initialize database schema (optional - skips if not available)"""
    # Check if we should skip database initialization (for testing)
    if os.getenv("SKIP_DB_INIT"):
        logger.info("Database initialization skipped (SKIP_DB_INIT=true)")
        return
        
    if not DATABASE_AVAILABLE:
        logger.info("Database not available - using in-memory storage")
        return
        
    logger.info(f"Initializing database: {settings.DB_NAME}")
    
    try:
        # Create schema if not exists using raw connection
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        
        try:
            # Check if schema exists
            schema_exists = await conn.fetchval(
                "SELECT EXISTS(SELECT 1 FROM information_schema.schemata WHERE schema_name = 'test_management')"
            )
            
            if not schema_exists:
                logger.info("Creating test_management schema...")
                # Try to read schema file
                try:
                    with open("test_environment/sql/10_test_management_schema.sql", "r") as f:
                        schema_sql = f.read()
                    # Execute schema creation
                    await conn.execute(schema_sql)
                    logger.info("Schema created successfully")
                except FileNotFoundError:
                    logger.warning("Schema file not found - skipping schema creation")
            else:
                logger.info("Schema already exists")
                
        finally:
            await conn.close()
            
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.info("Continuing with in-memory storage")


@asynccontextmanager
async def get_session() -> AsyncGenerator[Optional[AsyncSession], None]:
    """Get async database session (returns None if database not available)"""
    if not DATABASE_AVAILABLE or not AsyncSessionLocal:
        yield None
        return
        
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def execute_query(query: str, params: dict = None) -> list:
    """Execute a raw SQL query (returns empty list if database not available)"""
    if not DATABASE_AVAILABLE or not asyncpg:
        logger.warning("Database not available for query execution")
        return []
        
    try:
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        
        try:
            if params:
                # Convert named params to positional params for asyncpg
                param_names = list(params.keys())
                # Replace %(name)s with $1, $2, etc
                for i, name in enumerate(param_names, 1):
                    query = query.replace(f"%({name})s", f"${i}")
                result = await conn.fetch(query, *params.values())
            else:
                result = await conn.fetch(query)
            return [dict(row) for row in result]
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Query execution failed: {e}")
        return []


async def execute_update(query: str, params: dict = None) -> Optional[str]:
    """Execute an update/insert/delete query (returns None if database not available)"""
    if not DATABASE_AVAILABLE or not asyncpg:
        logger.warning("Database not available for update execution")
        return None
        
    try:
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME
        )
        
        try:
            if params:
                # Convert named params to positional params for asyncpg
                param_names = list(params.keys())
                # Replace %(name)s with $1, $2, etc
                for i, name in enumerate(param_names, 1):
                    query = query.replace(f"%({name})s", f"${i}")
                
                # Check if query has RETURNING clause
                if 'RETURNING' in query.upper():
                    result = await conn.fetchval(query, *params.values())
                else:
                    result = await conn.execute(query, *params.values())
            else:
                if 'RETURNING' in query.upper():
                    result = await conn.fetchval(query)
                else:
                    result = await conn.execute(query)
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.warning(f"Update execution failed: {e}")
        return None


def is_database_available() -> bool:
    """Check if database functionality is available"""
    return DATABASE_AVAILABLE