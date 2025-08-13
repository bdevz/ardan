"""
Database connection and session management with connection pooling and health checks
"""
import asyncio
import time
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import QueuePool
from sqlalchemy import text, event
from sqlalchemy.engine import Engine

from shared.config import settings
from shared.utils import setup_logging

logger = setup_logging("database")

# Database connection pool configuration
POOL_SIZE = 20
MAX_OVERFLOW = 30
POOL_TIMEOUT = 30
POOL_RECYCLE = 3600  # 1 hour
POOL_PRE_PING = True

# Create async engine with optimized connection pooling
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=settings.debug,
    pool_size=POOL_SIZE,
    max_overflow=MAX_OVERFLOW,
    pool_timeout=POOL_TIMEOUT,
    pool_pre_ping=POOL_PRE_PING,
    pool_recycle=POOL_RECYCLE,
    poolclass=QueuePool,
    # Connection arguments for better performance
    connect_args={
        "server_settings": {
            "application_name": "upwork_automation",
            "jit": "off",  # Disable JIT for better connection performance
        },
        "command_timeout": 60,
        "statement_cache_size": 0,  # Disable statement cache for async
    }
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Manual control over flushing
    autocommit=False
)

# Base class for models
Base = declarative_base()

# Connection pool monitoring
_pool_stats = {
    "total_connections": 0,
    "active_connections": 0,
    "checked_out_connections": 0,
    "overflow_connections": 0,
    "invalid_connections": 0,
    "last_health_check": None,
    "health_check_failures": 0
}


@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set connection-level settings for PostgreSQL"""
    # This is for PostgreSQL, not SQLite, but keeping the pattern
    pass


async def init_db():
    """Initialize database connection and create tables if needed"""
    try:
        # Test connection and update pool stats
        async with engine.begin() as conn:
            # Import all models to ensure they're registered
            from . import models
            
            # Test basic connectivity
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            logger.info(f"Connected to PostgreSQL: {version}")
            
            # Create tables (in production, use Alembic migrations)
            if settings.debug:
                await conn.run_sync(Base.metadata.create_all)
                logger.info("Database tables created/verified")
        
        # Update pool statistics
        await _update_pool_stats()
        logger.info("Database connection initialized successfully")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        _pool_stats["health_check_failures"] += 1
        raise


async def close_db():
    """Close database connections gracefully"""
    try:
        # Log final pool statistics
        await _update_pool_stats()
        logger.info(f"Final pool stats: {_pool_stats}")
        
        # Dispose of the engine and all connections
        await engine.dispose()
        logger.info("Database connections closed successfully")
        
    except Exception as e:
        logger.error(f"Error closing database connections: {e}")


@asynccontextmanager
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Context manager to get database session with proper error handling"""
    session = AsyncSessionLocal()
    try:
        yield session
        await session.commit()
    except Exception as e:
        await session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        await session.close()


async def get_db_dependency() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    async with get_db() as session:
        yield session


async def check_db_health() -> dict:
    """Comprehensive database health check with detailed metrics"""
    health_status = {
        "healthy": False,
        "timestamp": time.time(),
        "response_time_ms": None,
        "pool_stats": {},
        "error": None
    }
    
    start_time = time.time()
    
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connectivity
            await session.execute(text("SELECT 1"))
            
            # Test a more complex query
            result = await session.execute(text("""
                SELECT 
                    current_database() as database_name,
                    current_user as current_user,
                    version() as version,
                    now() as server_time
            """))
            db_info = result.fetchone()
            
            # Calculate response time
            response_time = (time.time() - start_time) * 1000
            
            # Update pool statistics
            await _update_pool_stats()
            
            health_status.update({
                "healthy": True,
                "response_time_ms": round(response_time, 2),
                "pool_stats": _pool_stats.copy(),
                "database_info": {
                    "name": db_info[0],
                    "user": db_info[1],
                    "version": db_info[2].split()[0:2],  # Just PostgreSQL version
                    "server_time": db_info[3].isoformat()
                }
            })
            
            # Reset failure count on successful check
            _pool_stats["health_check_failures"] = 0
            _pool_stats["last_health_check"] = time.time()
            
    except Exception as e:
        error_msg = f"Database health check failed: {str(e)}"
        logger.error(error_msg)
        
        _pool_stats["health_check_failures"] += 1
        health_status.update({
            "healthy": False,
            "error": error_msg,
            "pool_stats": _pool_stats.copy()
        })
    
    return health_status


async def _update_pool_stats():
    """Update connection pool statistics"""
    try:
        pool = engine.pool
        _pool_stats.update({
            "total_connections": pool.size(),
            "checked_out_connections": pool.checkedout(),
            "overflow_connections": pool.overflow(),
            "invalid_connections": pool.invalidated(),
            "pool_size_limit": POOL_SIZE,
            "max_overflow": MAX_OVERFLOW,
            "last_updated": time.time()
        })
    except Exception as e:
        logger.warning(f"Failed to update pool stats: {e}")


async def get_pool_stats() -> dict:
    """Get current connection pool statistics"""
    await _update_pool_stats()
    return _pool_stats.copy()


async def reset_pool():
    """Reset the connection pool (useful for recovery scenarios)"""
    try:
        logger.warning("Resetting database connection pool")
        await engine.dispose()
        
        # The engine will automatically recreate the pool on next use
        logger.info("Database connection pool reset successfully")
        
    except Exception as e:
        logger.error(f"Failed to reset connection pool: {e}")
        raise


class DatabaseHealthMonitor:
    """Background task for monitoring database health"""
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False
        self._task = None
    
    async def start(self):
        """Start the health monitoring task"""
        if self.running:
            return
        
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info(f"Database health monitor started (interval: {self.check_interval}s)")
    
    async def stop(self):
        """Stop the health monitoring task"""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Database health monitor stopped")
    
    async def _monitor_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                health = await check_db_health()
                
                if not health["healthy"]:
                    logger.warning(f"Database health check failed: {health.get('error')}")
                    
                    # If we have too many consecutive failures, try to reset the pool
                    if _pool_stats["health_check_failures"] >= 5:
                        logger.error("Too many health check failures, resetting connection pool")
                        await reset_pool()
                
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in database health monitor: {e}")
                await asyncio.sleep(self.check_interval)


# Global health monitor instance
health_monitor = DatabaseHealthMonitor()