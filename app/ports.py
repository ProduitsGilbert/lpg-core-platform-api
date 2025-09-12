"""
Protocol definitions for adapter interfaces.

This module defines protocols (interfaces) that adapters must implement.
Using protocols ensures that the domain layer depends on abstractions
rather than concrete implementations, and helps mypy catch missing methods.
"""

from typing import Protocol, Dict, Any, List
from datetime import date
from decimal import Decimal


class ERPClientProtocol(Protocol):
    """
    Protocol for ERP client adapters.
    
    This protocol defines the interface that all ERP clients must implement.
    If a method is called that doesn't exist in the protocol, mypy will
    fail the type check, preventing runtime errors.
    """
    
    def get_poline(self, po_id: str, line_no: int) -> Dict[str, Any]:
        """
        Retrieve PO line details from ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            
        Returns:
            Dictionary with PO line details
        """
        ...
    
    def update_poline_date(self, po_id: str, line_no: int, new_date: date) -> Dict[str, Any]:
        """
        Update PO line promise date in ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_date: New promise date
            
        Returns:
            Updated PO line details
        """
        ...
    
    def update_poline_price(self, po_id: str, line_no: int, new_price: Decimal) -> Dict[str, Any]:
        """
        Update PO line unit price in ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_price: New unit price
            
        Returns:
            Updated PO line details
        """
        ...
    
    def update_poline_quantity(self, po_id: str, line_no: int, new_quantity: Decimal) -> Dict[str, Any]:
        """
        Update PO line quantity in ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_quantity: New quantity
            
        Returns:
            Updated PO line details
        """
        ...
    
    def create_receipt(self, po_id: str, lines: List[Dict[str, Any]], receipt_date: date) -> Dict[str, Any]:
        """
        Create a goods receipt in ERP.
        
        Args:
            po_id: Purchase Order ID
            lines: Receipt lines with quantities
            receipt_date: Receipt posting date
            
        Returns:
            Created receipt details
        """
        ...


class AIClientProtocol(Protocol):
    """
    Protocol for AI client adapters.
    
    This protocol defines the interface that AI clients must implement
    for purchase order analysis and optimization.
    """
    
    @property
    def enabled(self) -> bool:
        """Whether the AI client is enabled and available."""
        ...
    
    def analyze_purchase_order(
        self, 
        po_data: Dict[str, Any], 
        analysis_type: str = "optimization"
    ) -> Dict[str, Any]:
        """
        Analyze purchase order data using AI.
        
        Args:
            po_data: Purchase order data to analyze
            analysis_type: Type of analysis to perform
            
        Returns:
            Analysis results with recommendations
        """
        ...