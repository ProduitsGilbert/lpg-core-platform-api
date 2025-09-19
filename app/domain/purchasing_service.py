"""
Purchasing domain service with business logic.

This module implements the core business rules for purchasing operations,
including PO line updates, receipts, returns, and related workflows.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

from app.adapters.erp_client import ERPClient
from app.adapters.ai_client import AIClient
from app.ports import ERPClientProtocol, AIClientProtocol
from app.audit import (
    get_idempotency_record,
    save_idempotency_record,
    write_audit_log,
    AuditContext
)
from app.domain.dtos import (
    POLineDTO,
    UpdatePOLineDateCommand,
    UpdatePOLinePriceCommand,
    UpdatePOLineQuantityCommand,
    CreateReceiptCommand,
    CreateReturnCommand,
    ReceiptDTO,
    ReturnDTO,
    ReturnLineDTO,
    PurchaseOrderDTO
)
from app.errors import ValidationException, ERPError


class PurchasingService:
    """
    Service layer for purchasing domain operations.
    
    Implements business rules, orchestrates adapters, and ensures
    data consistency with idempotency and audit logging.
    """
    
    def __init__(self, erp_client: Optional[ERPClientProtocol] = None, ai_client: Optional[AIClientProtocol] = None):
        """
        Initialize purchasing service.
        
        Args:
            erp_client: Optional ERP client override
            ai_client: Optional AI client override
        """
        self.erp = erp_client or ERPClient()
        self.ai = ai_client or AIClient()
    
    def update_poline_date(
        self,
        command: UpdatePOLineDateCommand,
        db_session: Session
    ) -> POLineDTO:
        """
        Update PO line promise date with business rule validation.
        
        Business Rules:
        1. New date must be >= today
        2. New date must be >= order date (if available)
        3. Cannot update closed/cancelled lines
        4. Idempotency enforced via key
        
        Args:
            command: Update command with new date and reason
            db_session: Database session for audit/idempotency
        
        Returns:
            Updated PO line DTO
        
        Raises:
            ValidationException: If business rules are violated
            ERPError: If ERP operation fails
        """
        from app.settings import settings
        
        if settings.logfire_api_key:
            import logfire
            span_context = logfire.span(
                "update_poline_date",
                po_id=command.po_id,
                line_no=command.line_no,
                new_date=str(command.new_date)
            )
        else:
            from contextlib import nullcontext
            span_context = nullcontext()
        
        with span_context:
            # Check idempotency
            if command.idempotency_key:
                cached = get_idempotency_record(db_session, command.idempotency_key)
                if cached:
                    if settings.logfire_api_key:
                        logfire.info(f"Returning cached response for key: {command.idempotency_key}")
                    else:
                        logger.info(f"Returning cached response for key: {command.idempotency_key}")
                    return POLineDTO(**cached)
            
            # Use audit context for automatic logging
            with AuditContext(
                db_session,
                "POLine.PromiseDateChanged",
                command.actor,
                command.trace_id
            ) as audit:
                
                # Fetch current PO line from ERP
                current_data = self.erp.get_poline(command.po_id, command.line_no)
                current_date = date.fromisoformat(current_data["promise_date"])
                
                # Set audit entity
                audit.set_entity(command.po_id, command.line_no)
                
                # Business rule validation
                self._validate_date_update(
                    current_data,
                    command.new_date,
                    command.po_id,
                    command.line_no
                )
                
                # Update in ERP
                updated_data = self.erp.update_poline_date(
                    command.po_id,
                    command.line_no,
                    command.new_date
                )
                
                # Set audit change details
                audit.set_change(
                    previous={"promise_date": str(current_date)},
                    next={"promise_date": str(command.new_date)},
                    reason=command.reason
                )
                
                # Create DTO from updated data
                result = self._map_to_poline_dto(updated_data)
                
                # Save idempotency record
                if command.idempotency_key:
                    save_idempotency_record(
                        db_session,
                        command.idempotency_key,
                        result.model_dump()
                    )
                
                if settings.logfire_api_key:
                    logfire.info(
                        f"PO line date updated successfully",
                        po_id=command.po_id,
                        line_no=command.line_no,
                        old_date=str(current_date),
                        new_date=str(command.new_date)
                    )
                else:
                    logger.info(
                        f"PO line date updated successfully: po_id={command.po_id}, line_no={command.line_no}, old_date={current_date}, new_date={command.new_date}"
                    )
                
                return result
    
    def _validate_date_update(
        self,
        current_data: Dict[str, Any],
        new_date: date,
        po_id: str,
        line_no: int
    ) -> None:
        """
        Validate date update against business rules.
        
        Args:
            current_data: Current PO line data
            new_date: Proposed new date
            po_id: Purchase order ID
            line_no: Line number
        
        Raises:
            ValidationException: If validation fails
        """
        # Check line status
        status = current_data.get("status", "").lower()
        if status in ["closed", "cancelled"]:
            raise ValidationException(
                f"Cannot update date for {status} PO line",
                field="status",
                context={"po_id": po_id, "line_no": line_no, "status": status}
            )
        
        # Check date is not in past
        if new_date < date.today():
            raise ValidationException(
                "Promise date cannot be in the past",
                field="new_date",
                context={"po_id": po_id, "line_no": line_no, "new_date": str(new_date)}
            )
        
        # Check against order date if available
        if "order_date" in current_data:
            order_date = date.fromisoformat(current_data["order_date"])
            if new_date < order_date:
                raise ValidationException(
                    f"Promise date cannot be before order date ({order_date})",
                    field="new_date",
                    context={
                        "po_id": po_id,
                        "line_no": line_no,
                        "new_date": str(new_date),
                        "order_date": str(order_date)
                    }
                )
    
    def update_poline_price(
        self,
        command: UpdatePOLinePriceCommand,
        db_session: Session
    ) -> POLineDTO:
        """
        Update PO line unit price with business rule validation.
        
        Business Rules:
        1. New price must be > 0
        2. Cannot update if line is partially/fully received
        3. Cannot update closed/cancelled/invoiced lines
        4. Price changes > 10% trigger AI review (if enabled)
        
        Args:
            command: Update command with new price and reason
            db_session: Database session for audit/idempotency
        
        Returns:
            Updated PO line DTO
        
        Raises:
            ValidationException: If business rules are violated
            ERPError: If ERP operation fails
        """
        from app.settings import settings
        
        if settings.logfire_api_key:
            import logfire
            span_context = logfire.span(
                "update_poline_price",
                po_id=command.po_id,
                line_no=command.line_no,
                new_price=str(command.new_price)
            )
        else:
            from contextlib import nullcontext
            span_context = nullcontext()
        
        with span_context:
            # Check idempotency
            if command.idempotency_key:
                cached = get_idempotency_record(db_session, command.idempotency_key)
                if cached:
                    if settings.logfire_api_key:
                        logfire.info(f"Returning cached response for key: {command.idempotency_key}")
                    else:
                        logger.info(f"Returning cached response for key: {command.idempotency_key}")
                    return POLineDTO(**cached)
            
            with AuditContext(
                db_session,
                "POLine.PriceChanged",
                command.actor,
                command.trace_id
            ) as audit:
                
                # Fetch current PO line
                current_data = self.erp.get_poline(command.po_id, command.line_no)
                current_price = Decimal(str(current_data["unit_price"]))
                
                audit.set_entity(command.po_id, command.line_no)
                
                # Validate price update
                self._validate_price_update(
                    current_data,
                    command.new_price,
                    command.po_id,
                    command.line_no
                )
                
                # Check for significant price change
                price_change_pct = abs((command.new_price - current_price) / current_price * 100)
                if price_change_pct > 10:
                    if settings.logfire_api_key:
                        logfire.warning(
                            f"Significant price change: {price_change_pct:.1f}%",
                            po_id=command.po_id,
                            line_no=command.line_no
                        )
                    else:
                        logger.warning(
                            f"Significant price change: {price_change_pct:.1f}% for po_id={command.po_id}, line_no={command.line_no}"
                        )
                    
                    # Trigger AI review if enabled
                    if self.ai.enabled:
                        ai_review = self.ai.analyze_purchase_order(
                            {
                                "po_id": command.po_id,
                                "line_no": command.line_no,
                                "old_price": float(current_price),
                                "new_price": float(command.new_price),
                                "change_pct": float(price_change_pct),
                                "reason": command.reason
                            },
                            analysis_type="optimization"
                        )
                        audit.add_context(ai_recommendations=ai_review.get("recommendations"))
                
                # Update in ERP
                updated_data = self.erp.update_poline_price(
                    command.po_id,
                    command.line_no,
                    command.new_price
                )
                
                audit.set_change(
                    previous={"unit_price": str(current_price)},
                    next={"unit_price": str(command.new_price)},
                    reason=command.reason
                )
                
                result = self._map_to_poline_dto(updated_data)
                
                # Save idempotency record
                if command.idempotency_key:
                    save_idempotency_record(
                        db_session,
                        command.idempotency_key,
                        result.model_dump()
                    )
                
                if settings.logfire_api_key:
                    logfire.info(
                        f"PO line price updated successfully",
                        po_id=command.po_id,
                        line_no=command.line_no,
                        old_price=str(current_price),
                        new_price=str(command.new_price),
                        change_pct=price_change_pct
                    )
                else:
                    logger.info(
                        f"PO line price updated successfully: po_id={command.po_id}, line_no={command.line_no}, old_price={current_price}, new_price={command.new_price}, change_pct={price_change_pct}"
                    )
                
                return result
    
    def _validate_price_update(
        self,
        current_data: Dict[str, Any],
        new_price: Decimal,
        po_id: str,
        line_no: int
    ) -> None:
        """
        Validate price update against business rules.
        
        Args:
            current_data: Current PO line data
            new_price: Proposed new price
            po_id: Purchase order ID
            line_no: Line number
        
        Raises:
            ValidationException: If validation fails
        """
        # Check line status
        status = current_data.get("status", "").lower()
        if status in ["closed", "cancelled", "invoiced"]:
            raise ValidationException(
                f"Cannot update price for {status} PO line",
                field="status",
                context={"po_id": po_id, "line_no": line_no, "status": status}
            )
        
        # Check if already received
        qty_received = Decimal(str(current_data.get("quantity_received", 0)))
        if qty_received > 0:
            raise ValidationException(
                f"Cannot update price after receiving goods (received: {qty_received})",
                field="quantity_received",
                context={
                    "po_id": po_id,
                    "line_no": line_no,
                    "quantity_received": str(qty_received)
                }
            )
        
        # Validate price is positive
        if new_price <= 0:
            raise ValidationException(
                "Price must be greater than zero",
                field="new_price",
                context={"po_id": po_id, "line_no": line_no, "new_price": str(new_price)}
            )
    
    def update_poline_quantity(
        self,
        command: UpdatePOLineQuantityCommand,
        db_session: Session
    ) -> POLineDTO:
        """
        Update PO line quantity with business rule validation.
        
        Business Rules:
        1. New quantity must be > 0
        2. Cannot reduce below received quantity
        3. Cannot update closed/cancelled lines
        4. Quantity increases > 20% trigger AI review
        
        Args:
            command: Update command with new quantity and reason
            db_session: Database session for audit/idempotency
        
        Returns:
            Updated PO line DTO
        
        Raises:
            ValidationException: If business rules are violated
            ERPError: If ERP operation fails
        """
        from app.settings import settings
        
        if settings.logfire_api_key:
            import logfire
            span_context = logfire.span(
                "update_poline_quantity",
                po_id=command.po_id,
                line_no=command.line_no,
                new_quantity=str(command.new_quantity)
            )
        else:
            from contextlib import nullcontext
            span_context = nullcontext()
        
        with span_context:
            # Check idempotency
            if command.idempotency_key:
                cached = get_idempotency_record(db_session, command.idempotency_key)
                if cached:
                    if settings.logfire_api_key:
                        logfire.info(f"Returning cached response for key: {command.idempotency_key}")
                    else:
                        logger.info(f"Returning cached response for key: {command.idempotency_key}")
                    return POLineDTO(**cached)
            
            with AuditContext(
                db_session,
                "POLine.QuantityChanged",
                command.actor,
                command.trace_id
            ) as audit:
                
                # Fetch current PO line
                current_data = self.erp.get_poline(command.po_id, command.line_no)
                current_quantity = Decimal(str(current_data["quantity"]))
                
                audit.set_entity(command.po_id, command.line_no)
                
                # Validate quantity update
                self._validate_quantity_update(
                    current_data,
                    command.new_quantity,
                    command.po_id,
                    command.line_no
                )
                
                # Check for significant quantity change
                qty_change_pct = abs((command.new_quantity - current_quantity) / current_quantity * 100)
                if qty_change_pct > 20:
                    if settings.logfire_api_key:
                        logfire.warning(
                            f"Significant quantity change: {qty_change_pct:.1f}%",
                            po_id=command.po_id,
                            line_no=command.line_no
                        )
                    else:
                        logger.warning(
                            f"Significant quantity change: {qty_change_pct:.1f}% for po_id={command.po_id}, line_no={command.line_no}"
                        )
                
                # Update in ERP
                updated_data = self.erp.update_poline_quantity(
                    command.po_id,
                    command.line_no,
                    command.new_quantity
                )
                
                audit.set_change(
                    previous={"quantity": str(current_quantity)},
                    next={"quantity": str(command.new_quantity)},
                    reason=command.reason
                )
                
                result = self._map_to_poline_dto(updated_data)
                
                # Save idempotency record
                if command.idempotency_key:
                    save_idempotency_record(
                        db_session,
                        command.idempotency_key,
                        result.model_dump()
                    )
                
                if settings.logfire_api_key:
                    logfire.info(
                        f"PO line quantity updated successfully",
                        po_id=command.po_id,
                        line_no=command.line_no,
                        old_quantity=str(current_quantity),
                        new_quantity=str(command.new_quantity),
                        change_pct=qty_change_pct
                    )
                else:
                    logger.info(
                        f"PO line quantity updated successfully: po_id={command.po_id}, line_no={command.line_no}, old_quantity={current_quantity}, new_quantity={command.new_quantity}, change_pct={qty_change_pct}"
                    )
                
                return result
    
    def _validate_quantity_update(
        self,
        current_data: Dict[str, Any],
        new_quantity: Decimal,
        po_id: str,
        line_no: int
    ) -> None:
        """
        Validate quantity update against business rules.
        
        Args:
            current_data: Current PO line data
            new_quantity: Proposed new quantity
            po_id: Purchase order ID
            line_no: Line number
        
        Raises:
            ValidationException: If validation fails
        """
        # Check line status
        status = current_data.get("status", "").lower()
        if status in ["closed", "cancelled"]:
            raise ValidationException(
                f"Cannot update quantity for {status} PO line",
                field="status",
                context={"po_id": po_id, "line_no": line_no, "status": status}
            )
        
        # Check against received quantity
        qty_received = Decimal(str(current_data.get("quantity_received", 0)))
        if new_quantity < qty_received:
            raise ValidationException(
                f"Cannot reduce quantity below received amount ({qty_received})",
                field="new_quantity",
                context={
                    "po_id": po_id,
                    "line_no": line_no,
                    "new_quantity": str(new_quantity),
                    "quantity_received": str(qty_received)
                }
            )
        
        # Validate quantity is positive
        if new_quantity <= 0:
            raise ValidationException(
                "Quantity must be greater than zero",
                field="new_quantity",
                context={"po_id": po_id, "line_no": line_no, "new_quantity": str(new_quantity)}
            )
    
    def create_receipt(
        self,
        command: CreateReceiptCommand,
        db_session: Session
    ) -> ReceiptDTO:
        """
        Create a goods receipt for PO lines.
        
        Business Rules:
        1. PO must be in receivable status
        2. Cannot exceed ordered quantities
        3. All lines must be valid
        
        Args:
            command: Receipt creation command
            db_session: Database session for audit/idempotency
        
        Returns:
            Created receipt DTO
        
        Raises:
            ValidationException: If business rules are violated
            ERPError: If ERP operation fails
        """
        from app.settings import settings
        
        if settings.logfire_api_key:
            import logfire
            span_context = logfire.span(
                "create_receipt",
                po_id=command.po_id,
                line_count=len(command.lines)
            )
        else:
            from contextlib import nullcontext
            span_context = nullcontext()
        
        with span_context:
            # Check idempotency
            if command.idempotency_key:
                cached = get_idempotency_record(db_session, command.idempotency_key)
                if cached:
                    if settings.logfire_api_key:
                        logfire.info(f"Returning cached response for key: {command.idempotency_key}")
                    else:
                        logger.info(f"Returning cached response for key: {command.idempotency_key}")
                    return ReceiptDTO(**cached)
            
            with AuditContext(
                db_session,
                "Receipt.Created",
                command.actor,
                command.trace_id
            ) as audit:
                
                audit.set_entity(po_id=command.po_id)
                
                # Validate receipt lines and collect shipment references
                shipment_refs = set()
                if command.vendor_shipment_no:
                    shipment_refs.add(command.vendor_shipment_no)

                for line in command.lines:
                    po_line = self.erp.get_poline(command.po_id, line.line_no)
                    self._validate_receipt_line(po_line, line.quantity)
                    if line.vendor_shipment_no:
                        shipment_refs.add(line.vendor_shipment_no)

                if not shipment_refs:
                    raise ValidationException(
                        "Vendor shipment number is required to create a receipt",
                        field="vendor_shipment_no",
                        context={"po_id": command.po_id},
                    )

                if len(shipment_refs) > 1:
                    raise ValidationException(
                        "Multiple vendor shipment numbers provided; only one is supported",
                        field="vendor_shipment_no",
                        context={"po_id": command.po_id, "values": list(shipment_refs)},
                    )

                vendor_shipment_no = shipment_refs.pop()
                
                # Create receipt in ERP
                receipt_lines = [
                    {
                        "line_no": line.line_no,
                        "quantity": float(line.quantity),
                        "location_code": line.location_code,
                    }
                    for line in command.lines
                ]
                
                receipt_data = self.erp.create_receipt(
                    command.po_id,
                    receipt_lines,
                    command.receipt_date,
                    vendor_shipment_no,
                    command.job_check_delay_seconds,
                    command.notes,
                )
                
                audit.set_change(
                    previous=None,
                    next=receipt_data,
                    reason=f"Receipt created with {len(command.lines)} lines"
                )
                
                result = self._map_to_receipt_dto(receipt_data)
                
                # Save idempotency record
                if command.idempotency_key:
                    save_idempotency_record(
                        db_session,
                        command.idempotency_key,
                        result.model_dump()
                    )
                
                if settings.logfire_api_key:
                    logfire.info(
                        f"Receipt created successfully",
                        receipt_id=result.receipt_id,
                        po_id=command.po_id,
                        line_count=len(command.lines)
                    )
                else:
                    logger.info(
                        f"Receipt created successfully: receipt_id={result.receipt_id}, po_id={command.po_id}, line_count={len(command.lines)}"
                    )
                
                return result
    
    def _validate_receipt_line(
        self,
        po_line_data: Dict[str, Any],
        receipt_quantity: Decimal
    ) -> None:
        """
        Validate receipt line against PO line.
        
        Args:
            po_line_data: PO line data
            receipt_quantity: Quantity to receive
        
        Raises:
            ValidationException: If validation fails
        """
        # Check PO line status
        status = po_line_data.get("status", "").lower()
        if status in ["closed", "cancelled"]:
            raise ValidationException(
                f"Cannot receive against {status} PO line",
                field="status",
                context={
                    "po_id": po_line_data.get("po_id"),
                    "line_no": po_line_data.get("line_no"),
                    "status": status
                }
            )
        
        # Check quantity doesn't exceed outstanding
        ordered = Decimal(str(po_line_data.get("quantity", 0)))
        received = Decimal(str(po_line_data.get("quantity_received", 0)))
        outstanding = ordered - received
        
        if receipt_quantity > outstanding:
            raise ValidationException(
                f"Receipt quantity ({receipt_quantity}) exceeds outstanding ({outstanding})",
                field="quantity",
                context={
                    "po_id": po_line_data.get("po_id"),
                    "line_no": po_line_data.get("line_no"),
                    "ordered": str(ordered),
                    "received": str(received),
                    "outstanding": str(outstanding),
                    "receipt_quantity": str(receipt_quantity)
                }
            )
    
    def _map_to_poline_dto(self, data: Dict[str, Any]) -> POLineDTO:
        """Map ERP data to PO line DTO."""
        return POLineDTO(
            po_id=data["po_id"],
            line_no=data["line_no"],
            item_no=data["item_no"],
            description=data["description"],
            quantity=Decimal(str(data["quantity"])),
            unit_of_measure=data["unit_of_measure"],
            unit_price=Decimal(str(data["unit_price"])),
            line_amount=Decimal(str(data["line_amount"])),
            promise_date=date.fromisoformat(data["promise_date"]),
            requested_date=date.fromisoformat(data["requested_date"]) if data.get("requested_date") else None,
            quantity_received=Decimal(str(data.get("quantity_received", 0))),
            quantity_invoiced=Decimal(str(data.get("quantity_invoiced", 0))),
            quantity_to_receive=Decimal(str(data["quantity"])) - Decimal(str(data.get("quantity_received", 0))),
            status=data.get("status", "open"),
            location_code=data.get("location_code")
        )
    
    def _map_to_receipt_dto(self, data: Dict[str, Any]) -> ReceiptDTO:
        """Map ERP data to receipt DTO."""
        return ReceiptDTO(
            receipt_id=data["receipt_id"],
            po_id=data["po_id"],
            vendor_id=data.get("vendor_id", ""),
            vendor_name=data.get("vendor_name", ""),
            receipt_date=date.fromisoformat(data["receipt_date"]),
            posting_date=date.fromisoformat(data["posting_date"]) if data.get("posting_date") else None,
            status=data.get("status", "posted"),
            lines=[],  # Would be populated from line data
            notes=data.get("notes"),
            created_by=data.get("created_by"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None
        )

    # ------------------------------------------------------------------
    # Purchase return operations

    def create_return(
        self,
        command: CreateReturnCommand,
        db_session: Session
    ) -> ReturnDTO:
        """Create a purchase return order in Business Central."""
        from app.settings import settings

        return_date = command.return_date or date.today()

        if settings.logfire_api_key:
            import logfire
            span_context = logfire.span(
                "create_return",
                receipt_id=command.receipt_id,
                line_count=len(command.lines)
            )
        else:
            from contextlib import nullcontext
            span_context = nullcontext()

        with span_context:
            if command.idempotency_key:
                cached = get_idempotency_record(db_session, command.idempotency_key)
                if cached:
                    return ReturnDTO(**cached)

            with AuditContext(
                db_session,
                "Return.Created",
                command.actor,
                command.trace_id
            ) as audit:
                receipt_lines = self.erp.get_posted_purchase_receipt_lines(command.receipt_id)
                if not receipt_lines:
                    raise ValidationException(
                        "Posted receipt has no lines or does not exist",
                        field="receipt_id",
                        context={"receipt_id": command.receipt_id}
                    )

                receipt_line_map = {
                    int(line.get("Line_No", 0)): line
                    for line in receipt_lines
                    if line.get("Line_No") is not None
                }

                line_payloads: List[Dict[str, Any]] = []
                for input_line in command.lines:
                    receipt_line = receipt_line_map.get(int(input_line.line_no))
                    if not receipt_line:
                        raise ValidationException(
                            f"Receipt line {input_line.line_no} not found",
                            field="line_no",
                            context={
                                "receipt_id": command.receipt_id,
                                "line_no": input_line.line_no,
                            }
                        )

                    self._validate_return_line(receipt_line, input_line.quantity)

                    line_payloads.append({
                        "line_no": int(receipt_line.get("Line_No", input_line.line_no)),
                        "item_no": receipt_line.get("Item_No") or receipt_line.get("No"),
                        "description": receipt_line.get("Description"),
                        "quantity": float(input_line.quantity),
                        "unit_of_measure": receipt_line.get("Unit_of_Measure_Code"),
                        "location_code": receipt_line.get("Location_Code"),
                        "return_reason_code": receipt_line.get("Return_Reason_Code"),
                        "variant_code": receipt_line.get("Variant_Code"),
                    })

                return_no = self.erp.create_return(
                    command.receipt_id,
                    line_payloads,
                    return_date,
                    command.reason,
                )

                audit.set_entity(po_id=return_no)
                audit.set_change(
                    previous=None,
                    next={
                        "return_id": return_no,
                        "receipt_id": command.receipt_id,
                        "line_count": len(line_payloads),
                        "reason": command.reason,
                    },
                    reason="Return order created"
                )

                header = self.erp.get_purchase_return_order(return_no)
                lines = self.erp.get_purchase_return_order_lines(return_no)

                if not header:
                    raise ERPError(
                        "Return order was created but could not be retrieved",
                        context={"return_id": return_no}
                    )

                result = self._map_to_return_dto(header, lines)

                if command.idempotency_key:
                    save_idempotency_record(
                        db_session,
                        command.idempotency_key,
                        result.model_dump()
                    )

                return result

    async def get_return_order(self, return_id: str) -> Optional[ReturnDTO]:
        """Retrieve a purchase return order by its ID."""
        header = self.erp.get_purchase_return_order(return_id)
        if not header:
            return None
        lines = self.erp.get_purchase_return_order_lines(return_id)
        return self._map_to_return_dto(header, lines)

    @staticmethod
    def _parse_date(value: Optional[str]) -> Optional[date]:
        if not value:
            return None
        try:
            return date.fromisoformat(value[:10])
        except Exception:
            return None

    @staticmethod
    def _parse_datetime(value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except Exception:
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except Exception:
                return None

    def _map_to_return_dto(
        self,
        header: Dict[str, Any],
        lines: List[Dict[str, Any]]
    ) -> ReturnDTO:
        return ReturnDTO(
            return_id=header.get("No") or header.get("no"),
            receipt_id=header.get("External_Document_No") or header.get("Vendor_Shipment_No") or "",
            po_id=header.get("Vendor_Order_No") or header.get("Order_No") or header.get("Purch_Order_No") or "",
            vendor_id=header.get("Buy_from_Vendor_No", ""),
            vendor_name=header.get("Buy_from_Vendor_Name", ""),
            return_date=self._parse_date(header.get("Posting_Date")) or date.today(),
            reason=header.get("Comments") or header.get("Return_Reason_Code") or "",
            status=header.get("Status", "Open"),
            lines=[
                self._map_to_return_line_dto(
                    header.get("No") or header.get("no"),
                    line
                )
                for line in lines
            ],
            created_by=header.get("Assigned_User_ID") or header.get("Created_By"),
            created_at=self._parse_datetime(header.get("Last_Modified_DateTime")),
        )

    def _map_to_return_line_dto(
        self,
        return_id: str,
        line: Dict[str, Any]
    ) -> ReturnLineDTO:
        quantity = line.get("Quantity")
        return ReturnLineDTO(
            return_id=return_id,
            line_no=int(line.get("Line_No", 0) or 0),
            receipt_line_no=int(line.get("Receipt_Line_No", 0) or line.get("Line_No", 0) or 0),
            item_no=line.get("No") or line.get("Item_No", ""),
            description=line.get("Description", ""),
            quantity_returned=Decimal(str(quantity)) if quantity is not None else Decimal("0"),
            unit_of_measure=line.get("Unit_of_Measure_Code", ""),
        )

    def _validate_return_line(
        self,
        receipt_line: Dict[str, Any],
        quantity: Decimal
    ) -> None:
        if quantity <= 0:
            raise ValidationException(
                "Return quantity must be greater than zero",
                field="quantity",
                context={"quantity": str(quantity)}
            )

        received_quantity = Decimal(str(receipt_line.get("Quantity", 0)))
        if quantity > received_quantity:
            raise ValidationException(
                "Return quantity exceeds received quantity",
                field="quantity",
                context={
                    "receipt_line": receipt_line.get("Line_No"),
                    "requested": str(quantity),
                    "received": str(received_quantity)
                }
            )
