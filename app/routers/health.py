"""
Health check endpoints for monitoring and readiness.

This module provides health and liveness endpoints for container orchestration
and monitoring systems.
"""

from typing import Dict, Any
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging
import sys
import platform

logger = logging.getLogger(__name__)

from app.deps import get_db
from app.settings import settings
from app.db import verify_database_connection
from app.adapters.ocr_client import OCRClient
from app.adapters.ai_client import AIClient


router = APIRouter(tags=["health"])


@router.get(
    "/healthz",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Health check endpoint",
    description="Returns service health status and metadata"
)
async def health_check() -> Dict[str, Any]:
    """
    Basic health check endpoint.
    
    Returns:
        JSON with status and service information
    
    This endpoint always returns 200 OK if the service is running.
    Used for basic container health checks.
    """
    result = {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }
    
    if settings.logfire_api_key:
        import logfire
        with logfire.span("health_check"):
            return result
    else:
        return result


@router.get(
    "/livez",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Liveness probe endpoint",
    description="Kubernetes liveness probe endpoint"
)
async def liveness_check() -> Dict[str, Any]:
    """
    Liveness probe for Kubernetes.
    
    Returns:
        JSON with liveness status
    
    This endpoint checks if the application is alive and running.
    Returns 200 if alive, otherwise the container should be restarted.
    """
    result = {
        "status": "alive",
        "service": settings.app_name
    }
    
    if settings.logfire_api_key:
        import logfire
        with logfire.span("liveness_check"):
            return result
    else:
        return result


@router.get(
    "/readyz",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Readiness probe endpoint",
    description="Kubernetes readiness probe with dependency checks"
)
async def readiness_check(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Readiness probe for Kubernetes.
    
    Args:
        db: Database session for connectivity check
    
    Returns:
        JSON with readiness status and dependency health
    
    This endpoint checks if the application is ready to serve traffic.
    It verifies database connectivity and other critical dependencies.
    Returns 503 if not ready.
    """
    if settings.logfire_api_key:
        import logfire
        with logfire.span("readiness_check"):
            return await _do_readiness_check(db)
    else:
        return await _do_readiness_check(db)


async def _do_readiness_check(db: Session) -> Dict[str, Any]:
    """Internal readiness check logic."""
    checks = {
        "database": False,
        "ocr": False,
        "ai": False
    }
    
    issues = []
    
    # Check database connectivity
    try:
        result = db.execute(text("SELECT 1"))
        result.scalar()
        checks["database"] = True
    except Exception as e:
        if settings.logfire_api_key:
            import logfire
            logfire.error(f"Database readiness check failed: {e}")
        else:
            logger.error(f"Database readiness check failed: {e}")
        issues.append(f"Database connection failed: {str(e)}")
    
    # Check OCR service if enabled
    if settings.enable_ocr:
        try:
            ocr_client = OCRClient()
            checks["ocr"] = ocr_client.health_check()
            if not checks["ocr"]:
                issues.append("OCR service unhealthy")
        except Exception as e:
            if settings.logfire_api_key:
                import logfire
                logfire.error(f"OCR readiness check failed: {e}")
            else:
                logger.error(f"OCR readiness check failed: {e}")
            issues.append(f"OCR check failed: {str(e)}")
    else:
        checks["ocr"] = True  # Not required
    
    # Check AI service if enabled
    if settings.enable_ai_assistance:
        try:
            ai_client = AIClient()
            ai_health = ai_client.health_check()
            checks["ai"] = ai_health.get("openai") or ai_health.get("local_agent")
            if not checks["ai"]:
                issues.append("No AI service available")
        except Exception as e:
            if settings.logfire_api_key:
                import logfire
                logfire.error(f"AI readiness check failed: {e}")
            else:
                logger.error(f"AI readiness check failed: {e}")
            issues.append(f"AI check failed: {str(e)}")
    else:
        checks["ai"] = True  # Not required
    
    # Determine overall readiness
    is_ready = all(checks.values())
    
    response = {
        "status": "ready" if is_ready else "not_ready",
        "checks": checks,
        "service": settings.app_name,
        "version": settings.app_version
    }
    
    if issues:
        response["issues"] = issues
    
    if not is_ready:
        # Return 503 Service Unavailable if not ready
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=response
        )
    
    return response


@router.get(
    "/metrics",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Application metrics",
    description="Returns application metrics and statistics"
)
async def get_metrics(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Get application metrics.
    
    Args:
        db: Database session for metrics queries
    
    Returns:
        JSON with application metrics
    
    Provides basic metrics for monitoring. In production, consider
    using Prometheus metrics endpoint instead.
    """
    if settings.logfire_api_key:
        import logfire
        with logfire.span("get_metrics"):
            return await _do_get_metrics(db)
    else:
        return await _do_get_metrics(db)


async def _do_get_metrics(db: Session) -> Dict[str, Any]:
    """Internal metrics logic."""
    metrics = {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment
    }
    
    # Add database pool metrics
    try:
        from app.db import get_engine
        engine = get_engine()
        pool = engine.pool
        
        metrics["database"] = {
            "pool_size": pool.size(),
            "checked_out_connections": pool.checked_out(),
            "overflow": pool.overflow(),
            "total": pool.size() + pool.overflow()
        }
    except Exception as e:
        if settings.logfire_api_key:
            import logfire
            logfire.warning(f"Failed to get database metrics: {e}")
        else:
            logger.warning(f"Failed to get database metrics: {e}")
        metrics["database"] = {"error": str(e)}
    
    # Add idempotency metrics
    try:
        result = db.execute(
            text("SELECT COUNT(*) as count FROM [platform-code-app_idempotency]")
        )
        idempotency_count = result.scalar()
        
        result = db.execute(
            text("SELECT COUNT(*) as count FROM [platform-code-app_audit]")
        )
        audit_count = result.scalar()
        
        metrics["storage"] = {
            "idempotency_records": idempotency_count,
            "audit_records": audit_count
        }
    except Exception as e:
        if settings.logfire_api_key:
            import logfire
            logfire.warning(f"Failed to get storage metrics: {e}")
        else:
            logger.warning(f"Failed to get storage metrics: {e}")
        metrics["storage"] = {"error": str(e)}
    
    # Add feature flags
    metrics["features"] = {
        "scheduler_enabled": settings.enable_scheduler,
        "ocr_enabled": settings.enable_ocr,
        "ai_enabled": settings.enable_ai_assistance,
        "erp_mode": settings.erp_mode.value
    }
    
    return metrics


@router.get(
    "/debug",
    status_code=status.HTTP_200_OK,
    response_model=Dict[str, Any],
    summary="Debug information",
    description="Returns debug information (only in non-production)",
    include_in_schema=False
)
async def debug_info() -> Dict[str, Any]:
    """
    Get debug information.
    
    Returns:
        JSON with debug information
    
    Only available in non-production environments.
    Provides detailed configuration and system information.
    """
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debug endpoint not available in production"
        )
    
    debug_data = {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "python": {
            "version": sys.version,
            "platform": platform.platform(),
            "processor": platform.processor()
        },
        "configuration": {
            "debug": settings.debug,
            "erp_mode": settings.erp_mode.value,
            "canary_percent": settings.canary_percent,
            "db_pool_size": settings.db_pool_size,
            "idempotency_ttl_hours": settings.idempotency_ttl_hours,
            "audit_retention_days": settings.audit_retention_days
        },
        "features": {
            "scheduler": settings.enable_scheduler,
            "ocr": settings.enable_ocr,
            "ai": settings.enable_ai_assistance
        },
        "integrations": {
            "erp_configured": bool(settings.erp_base_url or settings.erp_mode == "legacy"),
            "ocr_configured": bool(settings.ocr_service_url),
            "openai_configured": bool(settings.openai_api_key),
            "local_agent_configured": bool(settings.local_agent_base_url),
            "logfire_configured": bool(settings.logfire_api_key)
        }
    }
    
    if settings.logfire_api_key:
        import logfire
        with logfire.span("debug_info"):
            return debug_data
    else:
        return debug_data