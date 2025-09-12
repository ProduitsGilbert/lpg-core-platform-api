"""
FastAPI application initialization and configuration with Logfire.

This module sets up the FastAPI application with all middleware,
routers, exception handlers, and lifecycle events.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore
import uvicorn

from app.settings import settings
from app.db import verify_database_connection, dispose_engine
from app.errors import register_exception_handlers
from app.routers import health, purchasing
from app.audit import cleanup_expired_idempotency_keys, cleanup_old_audit_logs
from app.db import get_db_session


# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Initialize scheduler if enabled
scheduler = None
if settings.enable_scheduler:
    scheduler = AsyncIOScheduler(
        jobstores={'default': MemoryJobStore()},
        executors={'default': {'type': 'threadpool', 'max_workers': 20}},
        job_defaults={'coalesce': False, 'max_instances': 1},
        timezone='UTC'
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Manage application lifecycle events.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize Logfire if configured
    logfire_configured = False
    if settings.logfire_api_key:
        try:
            import logfire
            logfire.configure(
                service_name=settings.app_name,
                token=settings.logfire_api_key,
                environment=settings.environment
            )
            # Instrument FastAPI app with Logfire
            logfire.instrument_fastapi(app)
            logger.info(f"Logfire initialized and instrumented for {settings.app_name}")
            logfire_configured = True
        except Exception as e:
            logger.warning(f"Failed to initialize Logfire: {e}")
    else:
        logger.warning("Logfire API key not configured - using local logging only")
    
    # Verify database connection
    db_connected = await verify_database_connection()
    if not db_connected:
        logger.error("Failed to connect to database during startup")
        # In production, you might want to fail startup here
        # raise RuntimeError("Database connection failed")
    else:
        logger.info("Database connection verified")
    
    # Start scheduler if enabled
    if scheduler and settings.enable_scheduler:
        # Add cleanup jobs
        scheduler.add_job(
            cleanup_expired_idempotency_keys,
            "interval",
            hours=1,
            id="cleanup_idempotency",
            replace_existing=True,
            kwargs={"session": get_db_session()}
        )
        
        scheduler.add_job(
            cleanup_old_audit_logs,
            "interval", 
            days=1,
            id="cleanup_audit",
            replace_existing=True,
            kwargs={"session": get_db_session()}
        )
        
        scheduler.start()
        logger.info("Background scheduler started")
    
    logger.info(f"{settings.app_name} startup complete")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    
    # Stop scheduler if running
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Background scheduler stopped")
    
    # Dispose database connections
    dispose_engine()
    logger.info("Database connections closed")
    
    logger.info(f"{settings.app_name} shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Minimal FastAPI Core Platform API for ERP integration",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan
)


# Add middleware

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Trace-ID"]
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request ID and tracing middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID and trace ID to request state and response headers."""
    import uuid
    
    # Get or generate request ID
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    trace_id = request.headers.get("X-Trace-ID", request_id)
    
    # Store in request state
    request.state.request_id = request_id
    request.state.trace_id = trace_id
    
    # Process request
    response = await call_next(request)
    
    # Add headers to response
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Trace-ID"] = trace_id
    
    return response


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(
    purchasing.router,
    prefix=f"{settings.api_v1_prefix}/purchasing",
    tags=["Purchasing"]
)

# Register exception handlers
register_exception_handlers(app)


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint showing API information."""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational"
    }


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=7003,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )