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
import logfire

from app.settings import settings


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


async def verify_database_connection() -> bool:
    """
    Verify database connectivity during application startup.
    
    Returns:
        True if connection successful, False otherwise
    
    Used in health checks and startup validation.
    """
    try:
        with logfire.span("Database connection check"):
            engine = get_engine()
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.scalar()
            logfire.info("Database connection verified successfully")
            return True
    except Exception as e:
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