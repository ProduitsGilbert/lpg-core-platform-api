"""
Common dependencies for FastAPI endpoints.

This module provides reusable dependency injection functions for:
- Database sessions
- User/actor identification
- Idempotency key extraction
- Request context and tracing
"""

from typing import Optional, Dict, Any, Annotated
from uuid import uuid4

from fastapi import Depends, Header, Request, HTTPException, status
from sqlalchemy.orm import Session
import logfire

from app.db import get_session
from app.errors import ValidationException


def get_db() -> Session:
    """
    Get database session dependency.
    
    Yields:
        Database session from the connection pool
    
    This is a wrapper around the db.get_session for cleaner imports.
    """
    yield from get_session()


def get_idempotency_key(
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
    x_idempotency_key: Optional[str] = Header(None, alias="X-Idempotency-Key"),
) -> Optional[str]:
    """
    Extract idempotency key from request headers.
    
    Args:
        idempotency_key: Standard Idempotency-Key header
        x_idempotency_key: Alternative X-Idempotency-Key header
    
    Returns:
        Idempotency key if provided, None otherwise
    
    Checks both standard and X-prefixed header names for compatibility.
    """
    key = idempotency_key or x_idempotency_key
    if key and len(key) > 128:
        raise ValidationException(
            "Idempotency key must be 128 characters or less",
            field="Idempotency-Key"
        )
    return key


def get_request_id(
    request_id: Optional[str] = Header(None, alias="X-Request-ID"),
    x_correlation_id: Optional[str] = Header(None, alias="X-Correlation-ID"),
) -> str:
    """
    Extract or generate request ID for tracing.
    
    Args:
        request_id: X-Request-ID header
        x_correlation_id: Alternative X-Correlation-ID header
    
    Returns:
        Request ID for tracing (uses provided ID or generates new UUID)
    
    Used for distributed tracing across services.
    """
    return request_id or x_correlation_id or str(uuid4())


def get_actor(
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
    x_user_email: Optional[str] = Header(None, alias="X-User-Email"),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
) -> str:
    """
    Extract actor/user information from request headers.
    
    Args:
        x_user_id: User ID from authentication service
        x_user_email: User email from authentication service
        x_api_key: API key for service-to-service auth
    
    Returns:
        Actor identifier for audit logging
    
    In production, this would be extracted from JWT or session.
    For now, uses headers or defaults to 'system'.
    """
    if x_user_id:
        return f"user:{x_user_id}"
    elif x_user_email:
        return f"email:{x_user_email}"
    elif x_api_key:
        # In production, look up API key owner
        return f"api:{x_api_key[:8]}..."
    else:
        return "system"


def get_source(
    user_agent: Optional[str] = Header(None),
    x_source_system: Optional[str] = Header(None, alias="X-Source-System"),
) -> str:
    """
    Extract source system information from request.
    
    Args:
        user_agent: Standard User-Agent header
        x_source_system: Custom header for system identification
    
    Returns:
        Source system identifier
    
    Used for tracking which system or client initiated the request.
    """
    if x_source_system:
        return x_source_system
    elif user_agent:
        # Extract simplified client name from user agent
        if "python" in user_agent.lower():
            return "python-client"
        elif "postman" in user_agent.lower():
            return "postman"
        elif "curl" in user_agent.lower():
            return "curl"
        else:
            return "web"
    else:
        return "unknown"


class RequestContext:
    """
    Container for request-scoped context information.
    
    Aggregates various request metadata for use in services and logging.
    """
    
    def __init__(
        self,
        request_id: str,
        actor: str,
        source: str,
        idempotency_key: Optional[str] = None,
        trace_id: Optional[str] = None
    ):
        self.request_id = request_id
        self.actor = actor
        self.source = source
        self.idempotency_key = idempotency_key
        self.trace_id = trace_id or request_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for logging."""
        return {
            "request_id": self.request_id,
            "actor": self.actor,
            "source": self.source,
            "idempotency_key": self.idempotency_key,
            "trace_id": self.trace_id
        }
    
    def to_audit_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary for audit logging."""
        return {
            "actor": self.actor,
            "trace_id": self.trace_id
        }


def get_request_context(
    request: Request,
    request_id: Annotated[str, Depends(get_request_id)],
    actor: Annotated[str, Depends(get_actor)],
    source: Annotated[str, Depends(get_source)],
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> RequestContext:
    """
    Aggregate all request context into a single object.
    
    Args:
        request: FastAPI request object
        request_id: Request ID from headers or generated
        actor: Actor identifier
        source: Source system identifier
        idempotency_key: Optional idempotency key
    
    Returns:
        RequestContext object with all metadata
    
    Usage:
        @app.post("/api/endpoint")
        def endpoint(ctx: RequestContext = Depends(get_request_context)):
            logfire.info("Processing request", **ctx.to_dict())
    """
    # Extract trace ID from Logfire if available
    trace_id = None
    if hasattr(request.state, "trace_id"):
        trace_id = request.state.trace_id
    
    return RequestContext(
        request_id=request_id,
        actor=actor,
        source=source,
        idempotency_key=idempotency_key,
        trace_id=trace_id
    )


def require_idempotency_key(
    idempotency_key: Annotated[Optional[str], Depends(get_idempotency_key)]
) -> str:
    """
    Require idempotency key to be present.
    
    Args:
        idempotency_key: Optional idempotency key from headers
    
    Returns:
        Idempotency key
    
    Raises:
        HTTPException: If idempotency key is not provided
    
    Use this dependency for endpoints that require idempotency.
    """
    if not idempotency_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Idempotency-Key header is required for this operation"
        )
    return idempotency_key


class PaginationParams:
    """
    Common pagination parameters for list endpoints.
    
    Provides consistent pagination across all list operations.
    """
    
    def __init__(
        self,
        offset: int = 0,
        limit: int = 100,
        sort_by: Optional[str] = None,
        sort_desc: bool = False
    ):
        """
        Initialize pagination parameters.
        
        Args:
            offset: Number of items to skip
            limit: Maximum number of items to return
            sort_by: Field to sort by
            sort_desc: Sort in descending order
        """
        if offset < 0:
            raise ValidationException("Offset must be non-negative", field="offset")
        if limit < 1 or limit > 1000:
            raise ValidationException("Limit must be between 1 and 1000", field="limit")
        
        self.offset = offset
        self.limit = limit
        self.sort_by = sort_by
        self.sort_desc = sort_desc
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "offset": self.offset,
            "limit": self.limit,
            "sort_by": self.sort_by,
            "sort_desc": self.sort_desc
        }


def get_pagination(
    offset: int = 0,
    limit: int = 100,
    sort_by: Optional[str] = None,
    sort_desc: bool = False
) -> PaginationParams:
    """
    Get pagination parameters from query string.
    
    Args:
        offset: Number of items to skip
        limit: Maximum number of items to return
        sort_by: Field to sort by
        sort_desc: Sort in descending order
    
    Returns:
        PaginationParams object
    
    Usage:
        @app.get("/api/items")
        def list_items(
            pagination: PaginationParams = Depends(get_pagination),
            db: Session = Depends(get_db)
        ):
            query = db.query(Item).offset(pagination.offset).limit(pagination.limit)
            return query.all()
    """
    return PaginationParams(offset, limit, sort_by, sort_desc)