"""
Audit logging and idempotency management.

This module provides functions for:
- Idempotency key storage and retrieval
- Audit trail logging for all ERP operations
- Database-backed operation tracking
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from sqlalchemy import text, Table, MetaData
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import logfire

from app.errors import IdempotencyException
from app.settings import settings


def get_idempotency_record(
    session: Session,
    idempotency_key: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve existing idempotency record if it exists.
    
    Args:
        session: Database session
        idempotency_key: Unique idempotency key
    
    Returns:
        Stored response data if key exists, None otherwise
    
    Used to return cached responses for duplicate requests.
    """
    with logfire.span("Get idempotency record", idempotency_key=idempotency_key):
        try:
            result = session.execute(
                text("""
                    SELECT response_json, created_at
                    FROM [platform-code-app_idempotency]
                    WHERE [key] = :key
                """),
                {"key": idempotency_key}
            ).fetchone()
            
            if result:
                response_json, created_at = result
                
                # Check if the record has expired
                if settings.idempotency_ttl_hours > 0:
                    expiry_time = created_at + timedelta(hours=settings.idempotency_ttl_hours)
                    if datetime.now(timezone.utc) > expiry_time:
                        # Record has expired, delete it
                        session.execute(
                            text("DELETE FROM [platform-code-app_idempotency] WHERE [key] = :key"),
                            {"key": idempotency_key}
                        )
                        session.commit()
                        logfire.info(f"Expired idempotency key deleted: {idempotency_key}")
                        return None
                
                logfire.info(f"Idempotency key found: {idempotency_key}")
                return json.loads(response_json) if response_json else None
            
            return None
            
        except Exception as e:
            logfire.error(f"Error retrieving idempotency record: {e}")
            session.rollback()
            return None


def save_idempotency_record(
    session: Session,
    idempotency_key: str,
    response_data: Dict[str, Any]
) -> bool:
    """
    Save idempotency record with response data.
    
    Args:
        session: Database session
        idempotency_key: Unique idempotency key
        response_data: Response data to cache
    
    Returns:
        True if saved successfully, False if key already exists
    
    Raises:
        IdempotencyException: If key exists with different data
    """
    with logfire.span("Save idempotency record", idempotency_key=idempotency_key):
        try:
            response_json = json.dumps(response_data)
            
            session.execute(
                text("""
                    INSERT INTO [platform-code-app_idempotency] ([key], response_json, created_at)
                    VALUES (:key, :response_json, SYSUTCDATETIME())
                """),
                {"key": idempotency_key, "response_json": response_json}
            )
            session.commit()
            logfire.info(f"Idempotency record saved: {idempotency_key}")
            return True
            
        except IntegrityError:
            # Key already exists - this is expected for duplicate requests
            session.rollback()
            logfire.warning(f"Idempotency key already exists: {idempotency_key}")
            
            # Verify the existing record matches
            existing = get_idempotency_record(session, idempotency_key)
            if existing and existing != response_data:
                raise IdempotencyException(
                    idempotency_key,
                    context={"existing": existing, "attempted": response_data}
                )
            return False
            
        except Exception as e:
            logfire.error(f"Error saving idempotency record: {e}")
            session.rollback()
            raise


def write_audit_log(
    session: Session,
    action: str,
    actor: str,
    trace_id: Optional[str] = None,
    po_id: Optional[str] = None,
    line_no: Optional[int] = None,
    previous: Optional[Any] = None,
    next: Optional[Any] = None,
    reason: Optional[str] = None,
    **additional_fields
) -> int:
    """
    Write an audit log entry for an operation.
    
    Args:
        session: Database session
        action: Action performed (e.g., "POLine.PromiseDateChanged")
        actor: User or system that performed the action
        trace_id: Request trace ID for correlation
        po_id: Purchase order ID if applicable
        line_no: PO line number if applicable
        previous: Previous state (will be JSON serialized)
        next: New state (will be JSON serialized)
        reason: Business reason for the change
        **additional_fields: Additional context to log
    
    Returns:
        ID of the created audit record
    
    All ERP-modifying operations should create audit entries.
    """
    with logfire.span(
        "Write audit log",
        action=action,
        actor=actor,
        po_id=po_id,
        line_no=line_no
    ):
        try:
            # Serialize previous and next states if provided
            previous_json = json.dumps(previous) if previous is not None else None
            next_json = json.dumps(next) if next is not None else None
            
            # Include additional fields in the reason or separate column
            if additional_fields:
                extra_context = json.dumps(additional_fields)
                if reason:
                    reason = f"{reason} | Context: {extra_context}"
                else:
                    reason = f"Context: {extra_context}"
            
            # Truncate reason if too long
            if reason and len(reason) > 200:
                reason = reason[:197] + "..."
            
            result = session.execute(
                text("""
                    INSERT INTO [platform-code-app_audit] 
                    (at, actor, action, po_id, line_no, previous, [next], reason, trace_id)
                    OUTPUT INSERTED.id
                    VALUES (SYSUTCDATETIME(), :actor, :action, :po_id, :line_no, 
                            :previous, :next, :reason, :trace_id)
                """),
                {
                    "actor": actor,
                    "action": action,
                    "po_id": po_id,
                    "line_no": line_no,
                    "previous": previous_json,
                    "next": next_json,
                    "reason": reason,
                    "trace_id": trace_id
                }
            )
            
            audit_id = result.scalar()
            session.commit()
            
            logfire.info(
                f"Audit log written: {action}",
                audit_id=audit_id,
                action=action,
                actor=actor
            )
            
            return audit_id
            
        except Exception as e:
            logfire.error(f"Error writing audit log: {e}")
            session.rollback()
            raise


def cleanup_expired_idempotency_keys(session: Session) -> int:
    """
    Remove expired idempotency keys from the database.
    
    Args:
        session: Database session
    
    Returns:
        Number of keys deleted
    
    Should be called periodically by a background job.
    """
    if settings.idempotency_ttl_hours <= 0:
        return 0
    
    with logfire.span("Cleanup expired idempotency keys"):
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=settings.idempotency_ttl_hours)
            
            result = session.execute(
                text("""
                    DELETE FROM [platform-code-app_idempotency]
                    WHERE created_at < :cutoff
                """),
                {"cutoff": cutoff_time}
            )
            
            deleted_count = result.rowcount
            session.commit()
            
            if deleted_count > 0:
                logfire.info(f"Cleaned up {deleted_count} expired idempotency keys")
            
            return deleted_count
            
        except Exception as e:
            logfire.error(f"Error cleaning up idempotency keys: {e}")
            session.rollback()
            return 0


def cleanup_old_audit_logs(session: Session) -> int:
    """
    Remove old audit logs beyond retention period.
    
    Args:
        session: Database session
    
    Returns:
        Number of audit records deleted
    
    Should be called periodically by a background job.
    """
    if settings.audit_retention_days <= 0:
        return 0
    
    with logfire.span("Cleanup old audit logs"):
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(days=settings.audit_retention_days)
            
            result = session.execute(
                text("""
                    DELETE FROM [platform-code-app_audit]
                    WHERE at < :cutoff
                """),
                {"cutoff": cutoff_time}
            )
            
            deleted_count = result.rowcount
            session.commit()
            
            if deleted_count > 0:
                logfire.info(f"Cleaned up {deleted_count} old audit logs")
            
            return deleted_count
            
        except Exception as e:
            logfire.error(f"Error cleaning up audit logs: {e}")
            session.rollback()
            return 0


class AuditContext:
    """
    Context manager for audit logging within a service operation.
    
    Collects audit information throughout an operation and writes
    the audit log entry when the operation completes successfully.
    """
    
    def __init__(
        self,
        session: Session,
        action: str,
        actor: str,
        trace_id: Optional[str] = None
    ):
        """
        Initialize audit context.
        
        Args:
            session: Database session
            action: Action being performed
            actor: User or system performing the action
            trace_id: Request trace ID
        """
        self.session = session
        self.action = action
        self.actor = actor
        self.trace_id = trace_id
        self.po_id = None
        self.line_no = None
        self.previous = None
        self.next = None
        self.reason = None
        self.additional = {}
    
    def set_entity(self, po_id: Optional[str] = None, line_no: Optional[int] = None):
        """Set the entity being modified."""
        self.po_id = po_id
        self.line_no = line_no
    
    def set_change(self, previous: Any, next: Any, reason: Optional[str] = None):
        """Set the change details."""
        self.previous = previous
        self.next = next
        self.reason = reason
    
    def add_context(self, **kwargs):
        """Add additional context fields."""
        self.additional.update(kwargs)
    
    def __enter__(self):
        """Enter the context."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context and write audit log if successful."""
        if exc_type is None:
            # Operation succeeded, write audit log
            write_audit_log(
                self.session,
                self.action,
                self.actor,
                self.trace_id,
                self.po_id,
                self.line_no,
                self.previous,
                self.next,
                self.reason,
                **self.additional
            )