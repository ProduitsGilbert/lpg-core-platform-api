"""
FastAPI application initialization and configuration.

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
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Initialize scheduler if enabled
scheduler = None
if settings.enable_scheduler:
    jobstores = {"default": MemoryJobStore()}
    scheduler = AsyncIOScheduler(jobstores=jobstores, timezone="UTC")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the application.
    """
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    
    # Initialize Logfire
    if settings.logfire_api_key:
        try:
            import logfire
            logfire.configure(
                service_name=settings.app_name,
                token=settings.logfire_api_key
            )
            logfire.info(f"Logfire initialized for {settings.app_name}")
        except Exception as e:
            logger.warning(f"Failed to initialize Logfire: {e}")
            settings.logfire_api_key = None  # Disable for rest of app
    else:
        logger.warning("Logfire API key not configured - using local logging only")
    
    # Verify database connection
    if settings.logfire_api_key:
        try:
            import logfire
            with logfire.span("Database startup check"):
                db_connected = await verify_database_connection()
                if not db_connected:
                    logger.error("Failed to connect to database during startup")
                    # In production, you might want to fail startup here
                    # raise RuntimeError("Database connection failed")
                else:
                    logger.info("Database connection verified")
        except:
            db_connected = await verify_database_connection()
            if not db_connected:
                logger.error("Failed to connect to database during startup")
                # In production, you might want to fail startup here
                # raise RuntimeError("Database connection failed")
            else:
                logger.info("Database connection verified")
    else:
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
            args=[get_db_session],
            name="Cleanup expired idempotency keys"
        )
        
        scheduler.add_job(
            cleanup_old_audit_logs,
            "interval",
            days=1,
            id="cleanup_audit",
            args=[get_db_session],
            name="Cleanup old audit logs"
        )
        
        scheduler.start()
        logger.info("APScheduler started with cleanup jobs")
    
    logger.info(f"{settings.app_name} startup complete")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.app_name}")
    
    # Stop scheduler
    if scheduler and scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped")
    
    # Dispose database connections
    dispose_engine()
    logger.info("Database connections closed")
    
    # Flush Logfire
    if settings.logfire_api_key:
        import logfire
        logfire.flush()
    
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
    
    # Process request with optional Logfire context
    if settings.logfire_api_key:
        import logfire
        with logfire.span(
            "HTTP Request",
            request_id=request_id,
            trace_id=trace_id,
            method=request.method,
            path=request.url.path
        ):
            # Process request
            response = await call_next(request)
            
            # Add headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Trace-ID"] = trace_id
            
            return response
    else:
        # Process request without Logfire
        response = await call_next(request)
        
        # Add headers to response
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Trace-ID"] = trace_id
        
        return response


# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and responses."""
    import time
    
    start_time = time.time()
    
    # Log request
    if settings.logfire_api_key:
        import logfire
        logfire.info(
            f"Request started: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            client=request.client.host if request.client else None
        )
    else:
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None
            }
        )
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = time.time() - start_time
    
    # Log response
    if settings.logfire_api_key:
        import logfire
        logfire.info(
            f"Request completed: {request.method} {request.url.path}",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2)
        )
    else:
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": round(duration * 1000, 2)
            }
        )
    
    # Add duration header
    response.headers["X-Process-Time"] = str(duration)
    
    return response


# Register exception handlers
register_exception_handlers(app)


# Include routers
app.include_router(health.router)

# Include new v1 API routers
from app.api.v1 import router as v1_router
app.include_router(v1_router)


# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to health check."""
    return JSONResponse(
        content={
            "service": settings.app_name,
            "version": settings.app_version,
            "status": "running",
            "documentation": "/docs" if not settings.is_production else None
        }
    )


# Optional: APScheduler API endpoints (if scheduler is enabled)
if settings.enable_scheduler and not settings.is_production:
    
    @app.get("/scheduler/jobs", include_in_schema=False)
    async def get_scheduler_jobs():
        """Get list of scheduled jobs."""
        if not scheduler:
            return {"error": "Scheduler not enabled"}
        
        jobs = []
        for job in scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger)
            })
        
        return {"jobs": jobs}
    
    @app.post("/scheduler/jobs/{job_id}/run", include_in_schema=False)
    async def run_scheduler_job(job_id: str):
        """Manually trigger a scheduled job."""
        if not scheduler:
            return {"error": "Scheduler not enabled"}
        
        job = scheduler.get_job(job_id)
        if not job:
            return {"error": f"Job {job_id} not found"}
        
        job.modify(next_run_time=None)  # Run immediately
        return {"status": f"Job {job_id} triggered"}


# Application factory for testing
def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    return app


# Entry point for running with uvicorn directly
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info",
        access_log=True
    )
