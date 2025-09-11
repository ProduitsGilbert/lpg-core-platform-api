"""
ERP client adapter for Business Central integration.

This module provides a unified interface for ERP operations, supporting:
- Legacy Python function calls (current implementation)
- Official Business Central API (future implementation)
- Canary deployment for gradual migration
"""

import random
from datetime import date, datetime
from decimal import Decimal
from typing import Dict, Any, List, Optional
import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_multiplier,
    retry_if_exception_type,
    before_sleep_log
)
import logfire
import logging

from app.settings import settings, ERPMode
from app.errors import ERPError, ERPUnavailable, ERPNotFound, ERPConflict


logger = logging.getLogger(__name__)


class ERPClient:
    """
    Unified ERP client supporting multiple integration modes.
    
    Provides abstraction over legacy functions and official API,
    with automatic retry logic and error handling.
    """
    
    def __init__(self, mode: Optional[ERPMode] = None):
        """
        Initialize ERP client.
        
        Args:
            mode: Override default ERP mode from settings
        """
        self.mode = mode or settings.erp_mode
        self.http_client = None
        
        if self.mode in [ERPMode.OFFICIAL, ERPMode.CANARY]:
            # Initialize HTTP client for official API
            self.http_client = httpx.Client(
                base_url=settings.erp_base_url or "",
                timeout=settings.request_timeout,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                }
            )
    
    def __del__(self):
        """Clean up HTTP client on deletion."""
        if self.http_client:
            self.http_client.close()
    
    def _should_use_official_api(self) -> bool:
        """
        Determine whether to use official API based on mode and canary percentage.
        
        Returns:
            True if official API should be used, False for legacy
        """
        if self.mode == ERPMode.OFFICIAL:
            return True
        elif self.mode == ERPMode.CANARY:
            # Random selection based on canary percentage
            return random.randint(1, 100) <= settings.canary_percent
        else:
            return False
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_multiplier(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def get_poline(self, po_id: str, line_no: int) -> Dict[str, Any]:
        """
        Retrieve PO line details from ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
        
        Returns:
            Dictionary with PO line details
        
        Raises:
            ERPNotFound: If PO line doesn't exist
            ERPUnavailable: If ERP is temporarily unavailable
        """
        with logfire.span("ERP get_poline", po_id=po_id, line_no=line_no):
            if self._should_use_official_api():
                return self._get_poline_official(po_id, line_no)
            else:
                return self._get_poline_legacy(po_id, line_no)
    
    def _get_poline_legacy(self, po_id: str, line_no: int) -> Dict[str, Any]:
        """
        Get PO line using legacy Python functions.
        
        This is a stub implementation that simulates legacy ERP calls.
        In production, this would import and call actual legacy functions.
        """
        logfire.info(f"Using legacy ERP for get_poline: {po_id}/{line_no}")
        
        # Simulate legacy function call
        # In production: from legacy_erp import get_purchase_line
        # result = get_purchase_line(po_id, line_no)
        
        # Stub implementation for development
        if po_id == "PO-NOT-FOUND":
            raise ERPNotFound("Purchase Order", po_id)
        
        return {
            "po_id": po_id,
            "line_no": line_no,
            "item_no": "ITEM-001",
            "description": "Sample Item Description",
            "quantity": 100.0,
            "unit_of_measure": "EA",
            "unit_price": 25.50,
            "line_amount": 2550.00,
            "promise_date": "2024-12-31",
            "requested_date": "2024-12-25",
            "quantity_received": 0.0,
            "quantity_invoiced": 0.0,
            "status": "open",
            "location_code": "MAIN"
        }
    
    def _get_poline_official(self, po_id: str, line_no: int) -> Dict[str, Any]:
        """
        Get PO line using official Business Central API.
        
        Future implementation for official API integration.
        """
        logfire.info(f"Using official API for get_poline: {po_id}/{line_no}")
        
        if not self.http_client:
            raise ERPError("Official API client not initialized")
        
        try:
            response = self.http_client.get(
                f"/purchaseOrders/{po_id}/lines/{line_no}"
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
            elif e.response.status_code == 503:
                raise ERPUnavailable()
            else:
                raise ERPError(f"API error: {e.response.status_code}")
        except httpx.TimeoutException:
            raise ERPUnavailable("ERP API timeout")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_multiplier(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def update_poline_date(
        self,
        po_id: str,
        line_no: int,
        new_date: date
    ) -> Dict[str, Any]:
        """
        Update PO line promise date in ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_date: New promise date
        
        Returns:
            Updated PO line details
        
        Raises:
            ERPNotFound: If PO line doesn't exist
            ERPConflict: If PO is in a state that prevents updates
            ERPUnavailable: If ERP is temporarily unavailable
        """
        with logfire.span(
            "ERP update_poline_date",
            po_id=po_id,
            line_no=line_no,
            new_date=str(new_date)
        ):
            if self._should_use_official_api():
                return self._update_poline_date_official(po_id, line_no, new_date)
            else:
                return self._update_poline_date_legacy(po_id, line_no, new_date)
    
    def _update_poline_date_legacy(
        self,
        po_id: str,
        line_no: int,
        new_date: date
    ) -> Dict[str, Any]:
        """
        Update PO line date using legacy Python functions.
        
        Stub implementation for legacy ERP integration.
        """
        logfire.info(f"Using legacy ERP for update_poline_date: {po_id}/{line_no}")
        
        # Simulate legacy function call
        # In production: from legacy_erp import update_purchase_line_date
        # result = update_purchase_line_date(po_id, line_no, new_date)
        
        # Get current line first
        current = self._get_poline_legacy(po_id, line_no)
        
        # Check if PO is in updatable state
        if current.get("status") in ["closed", "cancelled"]:
            raise ERPConflict(f"Cannot update closed/cancelled PO line: {po_id}/{line_no}")
        
        # Update the date
        current["promise_date"] = new_date.isoformat()
        
        return current
    
    def _update_poline_date_official(
        self,
        po_id: str,
        line_no: int,
        new_date: date
    ) -> Dict[str, Any]:
        """
        Update PO line date using official Business Central API.
        
        Future implementation for official API integration.
        """
        logfire.info(f"Using official API for update_poline_date: {po_id}/{line_no}")
        
        if not self.http_client:
            raise ERPError("Official API client not initialized")
        
        try:
            response = self.http_client.patch(
                f"/purchaseOrders/{po_id}/lines/{line_no}",
                json={"promiseDate": new_date.isoformat()}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
            elif e.response.status_code == 409:
                raise ERPConflict(f"Cannot update PO line: {e.response.text}")
            elif e.response.status_code == 503:
                raise ERPUnavailable()
            else:
                raise ERPError(f"API error: {e.response.status_code}")
        except httpx.TimeoutException:
            raise ERPUnavailable("ERP API timeout")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_multiplier(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def update_poline_price(
        self,
        po_id: str,
        line_no: int,
        new_price: Decimal
    ) -> Dict[str, Any]:
        """
        Update PO line unit price in ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_price: New unit price
        
        Returns:
            Updated PO line details
        """
        with logfire.span(
            "ERP update_poline_price",
            po_id=po_id,
            line_no=line_no,
            new_price=str(new_price)
        ):
            if self._should_use_official_api():
                return self._update_poline_price_official(po_id, line_no, new_price)
            else:
                return self._update_poline_price_legacy(po_id, line_no, new_price)
    
    def _update_poline_price_legacy(
        self,
        po_id: str,
        line_no: int,
        new_price: Decimal
    ) -> Dict[str, Any]:
        """Update PO line price using legacy functions."""
        logfire.info(f"Using legacy ERP for update_poline_price: {po_id}/{line_no}")
        
        current = self._get_poline_legacy(po_id, line_no)
        
        if current.get("status") in ["closed", "cancelled", "invoiced"]:
            raise ERPConflict(f"Cannot update price for line in status: {current.get('status')}")
        
        current["unit_price"] = float(new_price)
        current["line_amount"] = float(new_price) * current["quantity"]
        
        return current
    
    def _update_poline_price_official(
        self,
        po_id: str,
        line_no: int,
        new_price: Decimal
    ) -> Dict[str, Any]:
        """Update PO line price using official API."""
        if not self.http_client:
            raise ERPError("Official API client not initialized")
        
        try:
            response = self.http_client.patch(
                f"/purchaseOrders/{po_id}/lines/{line_no}",
                json={"unitPrice": str(new_price)}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
            elif e.response.status_code == 409:
                raise ERPConflict(f"Cannot update price: {e.response.text}")
            else:
                raise ERPError(f"API error: {e.response.status_code}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential_multiplier(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def update_poline_quantity(
        self,
        po_id: str,
        line_no: int,
        new_quantity: Decimal
    ) -> Dict[str, Any]:
        """
        Update PO line quantity in ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_quantity: New quantity
        
        Returns:
            Updated PO line details
        """
        with logfire.span(
            "ERP update_poline_quantity",
            po_id=po_id,
            line_no=line_no,
            new_quantity=str(new_quantity)
        ):
            if self._should_use_official_api():
                return self._update_poline_quantity_official(po_id, line_no, new_quantity)
            else:
                return self._update_poline_quantity_legacy(po_id, line_no, new_quantity)
    
    def _update_poline_quantity_legacy(
        self,
        po_id: str,
        line_no: int,
        new_quantity: Decimal
    ) -> Dict[str, Any]:
        """Update PO line quantity using legacy functions."""
        logfire.info(f"Using legacy ERP for update_poline_quantity: {po_id}/{line_no}")
        
        current = self._get_poline_legacy(po_id, line_no)
        
        # Check if quantity can be reduced below received amount
        if float(new_quantity) < current.get("quantity_received", 0):
            raise ERPConflict(
                f"Cannot reduce quantity below received amount: {current.get('quantity_received')}"
            )
        
        current["quantity"] = float(new_quantity)
        current["line_amount"] = current["unit_price"] * float(new_quantity)
        
        return current
    
    def _update_poline_quantity_official(
        self,
        po_id: str,
        line_no: int,
        new_quantity: Decimal
    ) -> Dict[str, Any]:
        """Update PO line quantity using official API."""
        if not self.http_client:
            raise ERPError("Official API client not initialized")
        
        try:
            response = self.http_client.patch(
                f"/purchaseOrders/{po_id}/lines/{line_no}",
                json={"quantity": str(new_quantity)}
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
            elif e.response.status_code == 409:
                raise ERPConflict(f"Cannot update quantity: {e.response.text}")
            else:
                raise ERPError(f"API error: {e.response.status_code}")
    
    def get_purchase_order(self, po_id: str) -> Dict[str, Any]:
        """
        Retrieve full purchase order with lines.
        
        Args:
            po_id: Purchase Order ID
        
        Returns:
            Dictionary with PO header and lines
        """
        with logfire.span("ERP get_purchase_order", po_id=po_id):
            # Stub implementation
            return {
                "po_id": po_id,
                "vendor_id": "VENDOR-001",
                "vendor_name": "Sample Vendor Inc.",
                "order_date": date.today().isoformat(),
                "status": "open",
                "currency_code": "USD",
                "total_amount": 2550.00,
                "lines": [
                    self._get_poline_legacy(po_id, 1)
                ]
            }
    
    def create_receipt(
        self,
        po_id: str,
        lines: List[Dict[str, Any]],
        receipt_date: date
    ) -> Dict[str, Any]:
        """
        Create a goods receipt in ERP.
        
        Args:
            po_id: Purchase Order ID
            lines: Receipt lines with quantities
            receipt_date: Receipt posting date
        
        Returns:
            Created receipt details
        """
        with logfire.span(
            "ERP create_receipt",
            po_id=po_id,
            line_count=len(lines)
        ):
            # Stub implementation
            receipt_id = f"REC-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return {
                "receipt_id": receipt_id,
                "po_id": po_id,
                "receipt_date": receipt_date.isoformat(),
                "status": "posted",
                "lines": lines
            }
    
    def create_return(
        self,
        receipt_id: str,
        lines: List[Dict[str, Any]],
        return_date: date,
        reason: str
    ) -> Dict[str, Any]:
        """
        Create a purchase return in ERP.
        
        Args:
            receipt_id: Original receipt ID
            lines: Return lines with quantities
            return_date: Return posting date
            reason: Return reason
        
        Returns:
            Created return details
        """
        with logfire.span(
            "ERP create_return",
            receipt_id=receipt_id,
            line_count=len(lines)
        ):
            # Stub implementation
            return_id = f"RET-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            return {
                "return_id": return_id,
                "receipt_id": receipt_id,
                "return_date": return_date.isoformat(),
                "reason": reason,
                "status": "posted",
                "lines": lines
            }