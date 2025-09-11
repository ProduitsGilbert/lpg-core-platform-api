"""
Custom exception classes and error handling for the application.

This module defines typed exceptions for different error scenarios
and provides mapping to appropriate HTTP status codes.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
import logfire


class BaseAPIException(Exception):
    """
    Base exception class for all API exceptions.
    
    Attributes:
        status_code: HTTP status code to return
        detail: Human-readable error message
        error_code: Machine-readable error code for client handling
    """
    
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code or self.__class__.__name__
        self.context = context or {}
        super().__init__(detail)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response."""
        return {
            "error": self.error_code,
            "detail": self.detail,
            "context": self.context
        }


class ERPError(BaseAPIException):
    """
    Base exception for ERP-related errors.
    
    Used when ERP operations fail for any reason.
    """
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ERP operation failed: {detail}",
            error_code="ERP_ERROR",
            context=context
        )


class ERPConflict(BaseAPIException):
    """
    Exception for ERP conflict scenarios.
    
    Used when ERP operation cannot proceed due to conflicting state
    (e.g., PO already posted, line already received).
    """
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="ERP_CONFLICT",
            context=context
        )


class ERPUnavailable(BaseAPIException):
    """
    Exception for ERP service unavailability.
    
    Used when ERP system is temporarily unavailable or timeout occurs.
    """
    
    def __init__(self, detail: str = "ERP system is temporarily unavailable", context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="ERP_UNAVAILABLE",
            context=context
        )


class ERPNotFound(BaseAPIException):
    """
    Exception for ERP entity not found scenarios.
    
    Used when requested ERP entity (PO, line, vendor, etc.) doesn't exist.
    """
    
    def __init__(self, entity_type: str, entity_id: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{entity_type} not found: {entity_id}",
            error_code="ERP_NOT_FOUND",
            context={"entity_type": entity_type, "entity_id": entity_id, **(context or {})}
        )


class ValidationException(BaseAPIException):
    """
    Exception for business rule validation failures.
    
    Used when request violates business rules (not schema validation).
    """
    
    def __init__(self, detail: str, field: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
        ctx = context or {}
        if field:
            ctx["field"] = field
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
            context=ctx
        )


class IdempotencyException(BaseAPIException):
    """
    Exception for idempotency key conflicts.
    
    Used when idempotency key is reused with different request parameters.
    """
    
    def __init__(self, key: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Idempotency key conflict: {key}",
            error_code="IDEMPOTENCY_CONFLICT",
            context={"idempotency_key": key, **(context or {})}
        )


class AuthenticationException(BaseAPIException):
    """
    Exception for authentication failures.
    
    Used when authentication is required but not provided or invalid.
    """
    
    def __init__(self, detail: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_REQUIRED"
        )


class AuthorizationException(BaseAPIException):
    """
    Exception for authorization failures.
    
    Used when authenticated user lacks required permissions.
    """
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_FAILED"
        )


class ExternalServiceException(BaseAPIException):
    """
    Exception for external service failures (OCR, AI, etc.).
    
    Used when external services fail or timeout.
    """
    
    def __init__(self, service: str, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service} service error: {detail}",
            error_code="EXTERNAL_SERVICE_ERROR",
            context={"service": service, **(context or {})}
        )


async def handle_base_api_exception(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Exception handler for BaseAPIException and its subclasses.
    
    Args:
        request: FastAPI Request object
        exc: Exception instance
    
    Returns:
        JSONResponse with appropriate status code and error details
    """
    with logfire.span("API exception handled", exc_type=exc.__class__.__name__):
        logfire.error(
            f"API exception: {exc.error_code}",
            error_code=exc.error_code,
            status_code=exc.status_code,
            detail=exc.detail,
            context=exc.context,
            path=str(request.url)
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Exception handler for Pydantic validation errors.
    
    Args:
        request: FastAPI Request object
        exc: RequestValidationError instance
    
    Returns:
        JSONResponse with 422 status and validation error details
    """
    with logfire.span("Validation error handled"):
        logfire.warning(
            "Request validation failed",
            errors=exc.errors(),
            path=str(request.url)
        )
    
    # Format validation errors for cleaner response
    errors = []
    for error in exc.errors():
        loc = " -> ".join(str(x) for x in error["loc"])
        errors.append({
            "field": loc,
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "detail": "Request validation failed",
            "errors": errors
        }
    )


async def handle_generic_exception(request: Request, exc: Exception) -> JSONResponse:
    """
    Generic exception handler for unexpected errors.
    
    Args:
        request: FastAPI Request object
        exc: Exception instance
    
    Returns:
        JSONResponse with 500 status and generic error message
    """
    with logfire.span("Unhandled exception", exc_type=type(exc).__name__):
        logfire.error(
            f"Unhandled exception: {str(exc)}",
            exc_type=type(exc).__name__,
            exc_message=str(exc),
            path=str(request.url)
        )
    
    # Don't expose internal error details in production
    from app.settings import settings
    detail = str(exc) if settings.debug else "An internal error occurred"
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "INTERNAL_ERROR",
            "detail": detail
        }
    )


def register_exception_handlers(app):
    """
    Register all exception handlers with the FastAPI app.
    
    Args:
        app: FastAPI application instance
    
    Should be called during app initialization.
    """
    app.add_exception_handler(BaseAPIException, handle_base_api_exception)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(ValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_generic_exception)