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
import logging

logger = logging.getLogger(__name__)


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
    
    Raised when interactions with ERP systems fail.
    """
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="ERP_ERROR",
            context=context
        )


class ERPUnavailable(ERPError):
    """
    Raised when ERP system is unavailable.
    
    For connection failures, timeouts, etc.
    """
    
    def __init__(self, detail: str = "ERP system unavailable"):
        super().__init__(detail=detail)


class ERPNotFound(ERPError):
    """
    Raised when resource is not found in ERP.
    
    For 404-like errors from ERP system.
    """
    
    def __init__(self, resource_type: str, resource_id: str):
        detail = f"{resource_type} {resource_id} not found in ERP"
        super().__init__(detail=detail, context={"resource_type": resource_type, "resource_id": resource_id})
        self.status_code = status.HTTP_404_NOT_FOUND
        self.error_code = "ERP_NOT_FOUND"


class ERPConflict(ERPError):
    """
    Raised when there's a conflict in ERP.
    
    For duplicate resources, conflicts, etc.
    """
    
    def __init__(self, detail: str):
        super().__init__(detail=detail)
        self.status_code = status.HTTP_409_CONFLICT
        self.error_code = "ERP_CONFLICT"


class PurchaseOrderNotFoundError(BaseAPIException):
    """
    Raised when a purchase order is not found.
    
    This could be in the database or ERP system.
    """
    
    def __init__(self, po_number: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Purchase order {po_number} not found",
            error_code="PO_NOT_FOUND",
            context={"po_number": po_number}
        )


class PurchaseOrderExistsError(BaseAPIException):
    """
    Raised when attempting to create a purchase order that already exists.
    
    Helps maintain data integrity and prevent duplicates.
    """
    
    def __init__(self, po_number: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Purchase order {po_number} already exists",
            error_code="PO_EXISTS",
            context={"po_number": po_number}
        )


class ValidationException(BaseAPIException):
    """
    Raised when validation fails for API parameters.
    
    Used for custom validation logic beyond Pydantic schema validation.
    """
    
    def __init__(
        self,
        detail: str,
        field: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        combined_context = dict(context or {})
        if field:
            combined_context["field"] = field
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="VALIDATION_ERROR",
            context=combined_context or None,
        )


class InvalidPurchaseOrderError(BaseAPIException):
    """
    Raised when purchase order data is invalid.
    
    This covers business logic validation beyond schema validation.
    """
    
    def __init__(self, detail: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
            error_code="INVALID_PO",
            context=context
        )


class DatabaseError(BaseAPIException):
    """
    Raised when database operations fail.
    
    Wraps database-specific exceptions in a consistent API error.
    """
    
    def __init__(self, detail: str = "Database operation failed"):
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="DATABASE_ERROR"
        )


class AuthenticationError(BaseAPIException):
    """
    Raised when authentication fails.
    
    Used for API key validation and other auth mechanisms.
    """
    
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            error_code="AUTHENTICATION_FAILED"
        )


class AuthorizationError(BaseAPIException):
    """
    Raised when user lacks required permissions.
    
    Different from authentication - user is known but not authorized.
    """
    
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_code="AUTHORIZATION_FAILED"
        )


class RateLimitError(BaseAPIException):
    """
    Raised when rate limits are exceeded.
    
    Helps protect the API from abuse and overload.
    """
    
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        context = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            error_code="RATE_LIMIT_EXCEEDED",
            context=context
        )


class ExternalServiceException(BaseAPIException):
    """
    Raised when external service calls fail.
    
    Used for failures in OCR, AI services, or other external APIs.
    """
    
    def __init__(self, detail: str = "External service unavailable", service: Optional[str] = None):
        context = {"service": service} if service else None
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=detail,
            error_code="EXTERNAL_SERVICE_ERROR",
            context=context
        )


class IdempotencyException(BaseAPIException):
    """
    Raised when idempotency checks fail.
    
    Prevents duplicate processing of requests.
    """
    
    def __init__(self, detail: str = "Request already processed", idempotency_key: Optional[str] = None):
        context = {"idempotency_key": idempotency_key} if idempotency_key else None
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="IDEMPOTENCY_CONFLICT",
            context=context
        )


class IdempotencyError(BaseAPIException):
    """
    Raised when idempotency checks fail.
    
    Prevents duplicate processing of requests.
    """
    
    def __init__(self, detail: str = "Request already processed"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
            error_code="IDEMPOTENCY_CONFLICT"
        )


class CommunicationsError(BaseAPIException):
    """Base error for communications integrations."""

    def __init__(
        self,
        detail: str,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        error_code: str = "COMMUNICATIONS_ERROR",
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code=error_code,
            context=context,
        )


class CommunicationsUnauthorized(CommunicationsError):
    """Raised when Front authentication fails."""

    def __init__(self, detail: str = "Authentication with Front API failed"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="COMMUNICATIONS_UNAUTHORIZED",
        )


class CommunicationsNotFound(CommunicationsError):
    """Raised when a Front resource is not found."""

    def __init__(self, resource_type: str, resource_id: str):
        super().__init__(
            detail=f"{resource_type} {resource_id} not found in Front",
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="COMMUNICATIONS_NOT_FOUND",
            context={"resource_type": resource_type, "resource_id": resource_id},
        )


class CommunicationsRateLimited(CommunicationsError):
    """Raised when Front rate limits a request."""

    def __init__(self, retry_after: Optional[int] = None):
        context = {"retry_after": retry_after} if retry_after else None
        super().__init__(
            detail="Front API rate limit exceeded",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            error_code="COMMUNICATIONS_RATE_LIMITED",
            context=context,
        )


class CommunicationsConfigurationError(CommunicationsError):
    """Raised when Front configuration is missing or invalid."""

    def __init__(self, detail: str = "Front API configuration missing"):
        super().__init__(
            detail=detail,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            error_code="COMMUNICATIONS_CONFIGURATION",
        )


class PlanningServiceError(BaseAPIException):
    """Raised when the internal MRP planning service fails."""

    def __init__(
        self,
        detail: str,
        *,
        status_code: int = status.HTTP_502_BAD_GATEWAY,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            status_code=status_code,
            detail=detail,
            error_code="MRP_SERVICE_ERROR",
            context=context,
        )


# Exception handlers for FastAPI

async def handle_base_api_exception(request: Request, exc: BaseAPIException) -> JSONResponse:
    """
    Handler for BaseAPIException and its subclasses.
    
    Args:
        request: FastAPI Request object
        exc: Exception instance
    
    Returns:
        JSONResponse with appropriate status code and error details
    """
    # Log the exception
    from app.settings import settings
    if settings.logfire_api_key:
        import logfire
        with logfire.span("API exception handled", exc_type=exc.__class__.__name__):
            logfire.error(
                f"API exception: {exc.error_code}",
                error_code=exc.error_code,
                status_code=exc.status_code,
                detail=exc.detail,
                context=exc.context,
                path=str(request.url)
            )
    else:
        logger.error(
            f"API exception: {exc.error_code}",
            extra={
                "error_code": exc.error_code,
                "status_code": exc.status_code,
                "detail": exc.detail,
                "context": exc.context,
                "path": str(request.url)
            }
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict()
    )


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Handler for Pydantic validation errors.
    
    Formats validation errors in a consistent way.
    
    Args:
        request: FastAPI Request object
        exc: Validation exception instance
    
    Returns:
        JSONResponse with 422 status and validation error details
    """
    errors = []
    for error in exc.errors():
        errors.append({
            "field": ".".join(str(x) for x in error.get("loc", [])),
            "message": error.get("msg", ""),
            "type": error.get("type", "")
        })
    
    # Log validation errors
    from app.settings import settings
    if settings.logfire_api_key:
        import logfire
        with logfire.span("Validation error handled"):
            log_method = getattr(logfire, "warning", None) or getattr(logfire, "info", None)
            if log_method:
                log_method(
                    "Validation error",
                    error_count=len(errors),
                    errors=errors[:5],
                )
    else:
        logger.warning(
            "Validation error",
            extra={
                "error_count": len(errors),
                "errors": errors[:5]
            }
        )
    
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
    # Don't expose internal error details in production
    from app.settings import settings
    
    # Only use logfire if configured
    if settings.logfire_api_key:
        import logfire
        with logfire.span("Unhandled exception", exc_type=type(exc).__name__):
            logfire.error(
                f"Unhandled exception: {str(exc)}",
                exc_type=type(exc).__name__,
                exc_message=str(exc),
                path=str(request.url)
            )
    else:
        # Log to standard logger
        logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
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
