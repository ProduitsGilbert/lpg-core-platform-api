"""
Database connection and session management using SQLAlchemy 2.x.

This module provides SQLAlchemy engine configuration for MSSQL using pyodbc,
with connection pooling optimized for synchronous operations in a threadpool.
"""

from contextlib import contextmanager
from typing import Generator, Optional
import logging

from sqlalchemy import create_engine, text, Engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
import logging

logger = logging.getLogger(__name__)

from app.settings import settings

try:
    import logfire
except ImportError:
    logfire = None


logger = logging.getLogger(__name__)


def create_db_engine(db_url: Optional[str] = None) -> Engine:
    """
    Create and configure SQLAlchemy engine with MSSQL+pyodbc.
    
    Args:
        db_url: Optional database URL override (for testing)
    
    Returns:
        Configured SQLAlchemy Engine instance
    
    Configuration includes:
    - Connection pooling with QueuePool
    - Proper timeout settings
    - Thread-safe operation
    - Connection validation
    """
    url = db_url or settings.db_dsn
    
    engine = create_engine(
        url,
        # Connection pool configuration
        poolclass=QueuePool,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_pool_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=3600,  # Recycle connections after 1 hour
        pool_pre_ping=True,  # Verify connections before using
        
        # Engine configuration
        echo=settings.debug,  # SQL logging in debug mode
        echo_pool=settings.debug,
        future=True,  # Use SQLAlchemy 2.0 style
        
        # pyodbc specific settings
        connect_args={
            "timeout": settings.db_pool_timeout,
            "autocommit": False,
            "ansi": True,  # Use ANSI mode for better compatibility
        }
    )
    
    # Add event listener for connection pool checkout
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set connection-level settings when a new connection is created."""
        with dbapi_conn.cursor() as cursor:
            # Set session options for better performance
            cursor.execute("SET NOCOUNT ON")
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
    
    return engine


def create_session_factory(engine: Engine) -> sessionmaker:
    """
    Create a session factory bound to the given engine.
    
    Args:
        engine: SQLAlchemy Engine instance
    
    Returns:
        Configured sessionmaker factory
    """
    return sessionmaker(
        bind=engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,  # Don't expire objects after commit
        class_=Session
    )


# Global instances (initialized on first import)
_engine: Optional[Engine] = None
_session_factory: Optional[sessionmaker] = None
_autopilot_engine: Optional[Engine] = None
_autopilot_session_factory: Optional[sessionmaker] = None
_autopilot_dsn: Optional[str] = None  # cached resolved DSN


def get_engine() -> Engine:
    """
    Get or create the global database engine.
    
    Returns:
        SQLAlchemy Engine instance
    
    Thread-safe lazy initialization of the global engine.
    """
    global _engine
    if _engine is None:
        _engine = create_db_engine()
        with logfire.span("Database engine initialized"):
            logfire.info(f"Created database engine with pool size {settings.db_pool_size}")
    return _engine


def get_session_factory() -> sessionmaker:
    """
    Get or create the global session factory.
    
    Returns:
        SQLAlchemy sessionmaker instance
    """
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


def get_autopilot_engine() -> Engine:
    """
    Engine for Fastems1 Autopilot tables (optional override).

    Falls back to the primary engine when no override DSN is configured.
    """
    global _autopilot_engine, _autopilot_session_factory, _autopilot_dsn
    resolved_dsn = settings.fastems1_autopilot_db_dsn or settings.cedule_db_dsn
    if not resolved_dsn:
        return get_engine()
    if _autopilot_dsn != resolved_dsn:
        # DSN changed; reset engine/session
        _autopilot_engine = None
        _autopilot_session_factory = None
        _autopilot_dsn = resolved_dsn
    if _autopilot_engine is None:
        _autopilot_engine = create_db_engine(resolved_dsn)
        if logfire:
            with logfire.span("Autopilot database engine initialized"):
                logfire.info(f"Created autopilot engine with pool size {settings.db_pool_size}")
    return _autopilot_engine


def get_autopilot_session_factory() -> sessionmaker:
    """
    Session factory for Fastems1 Autopilot database.
    """
    global _autopilot_session_factory
    if not (settings.fastems1_autopilot_db_dsn or settings.cedule_db_dsn):
        return get_session_factory()
    if _autopilot_session_factory is None:
        _autopilot_session_factory = create_session_factory(get_autopilot_engine())
    return _autopilot_session_factory


def get_session() -> Generator[Session, None, None]:
    """
    Dependency injection function for FastAPI to get a database session.
    
    Yields:
        SQLAlchemy Session instance
    
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_session)):
            return db.query(Item).all()
    
    Ensures proper cleanup with automatic rollback on error.
    """
    try:
        session_factory = get_session_factory()
        session = session_factory()
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, ImportError) or "pyodbc" in message.lower():
            logger.warning("Database driver unavailable; returning dummy session: %s", exc)

            class DummySession:
                def commit(self):
                    return None

                def rollback(self):
                    return None

                def close(self):
                    return None

            dummy = DummySession()
            try:
                yield dummy
            finally:
                dummy.close()
            return
        raise
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_autopilot_session() -> Generator[Session, None, None]:
    """
    Dependency for Fastems1 Autopilot tables; uses override DSN when provided.
    """
    try:
        session_factory = get_autopilot_session_factory()
        session = session_factory()
    except Exception as exc:
        message = str(exc)
        if isinstance(exc, ImportError) or "pyodbc" in message.lower():
            logger.warning("Autopilot database driver unavailable; returning dummy session: %s", exc)

            class DummySession:
                def commit(self):
                    return None

                def rollback(self):
                    return None

                def close(self):
                    return None

            dummy = DummySession()
            try:
                yield dummy
            finally:
                dummy.close()
            return
        raise
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions outside of FastAPI dependency injection.
    
    Yields:
        SQLAlchemy Session instance
    
    Usage:
        with get_db_session() as session:
            session.execute(text("SELECT 1"))
    """
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_autopilot_db_session() -> Generator[Session, None, None]:
    """
    Context manager for the Autopilot database session.
    """
    if settings.fastems1_autopilot_db_dsn is None:
        with get_db_session() as session:
            yield session
        return
    session = get_autopilot_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


async def verify_database_connection() -> bool:
    """
    Verify database connectivity during application startup.
    
    Returns:
        True if connection successful, False otherwise
    
    Used in health checks and startup validation.
    """
    try:
        # Check if logfire is configured
        from app.settings import settings
        if settings.logfire_api_key:
            with logfire.span("Database connection check"):
                engine = get_engine()
                with engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.scalar()
                logfire.info("Database connection verified successfully")
        else:
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()
        return True
    except Exception as e:
        if logfire and hasattr(settings, 'logfire_api_key') and settings.logfire_api_key:
            logfire.error(f"Database connection failed: {e}")
        return False


def dispose_engine() -> None:
    """
    Dispose of the database engine and close all connections.
    
    Should be called during application shutdown.
    """
    global _engine, _session_factory
    if _engine:
        _engine.dispose()
        logfire.info("Database engine disposed")
        _engine = None
        _session_factory = None
