"""
Protocol definitions for adapter interfaces.

This module defines protocols (interfaces) that adapters must implement.
Using protocols ensures that the domain layer depends on abstractions
rather than concrete implementations, and helps mypy catch missing methods.
"""

from typing import Protocol, Dict, Any, List, Optional, Type
from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel


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

    def reopen_purchase_order(self, header_no: str) -> Dict[str, Any]:
        """Reopen a purchase order header in the ERP system."""
        ...

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an item from ERP by its number."""
        ...

    def update_item_record(self, system_id: str, updates: Dict[str, Any], etag: str) -> None:
        """Patch an item using its SystemId and concurrency token."""
        ...

    def copy_item_from_template(self, template_item: str, destination_item: str) -> None:
        """Copy an item from a template record to a new item number."""
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


class OCRClientProtocol(Protocol):
    """
    Protocol for OCR document extraction clients.
    
    This protocol defines the interface for OCR clients that extract
    structured data from documents using AI/LLM models.
    """
    
    @property
    def enabled(self) -> bool:
        """Whether the OCR client is enabled and available."""
        ...
    
    def extract_purchase_order(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from a Purchase Order document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file for identification
            
        Returns:
            Structured PO data including header and lines
        """
        ...
    
    def extract_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from an Invoice document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file for identification
            
        Returns:
            Structured invoice data including header and lines
        """
        ...
    
    def extract_generic_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        output_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Extract structured data from any document type using a custom model.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file for identification
            document_type: Type of document for prompt customization
            output_model: Pydantic model class defining expected output structure
            
        Returns:
            Extracted data in the specified model format
        """
        ...


class FrontClientProtocol(Protocol):
    """Protocol for Front API client adapters."""

    async def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Fetch conversation metadata from Front."""
        ...

    async def get_conversation_messages(
        self,
        conversation_id: str,
        page: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch paginated messages for a conversation."""
        ...

    async def get_conversation_comments(self, conversation_id: str) -> Dict[str, Any]:
        """Fetch comments for a conversation."""
        ...

    async def create_comment(
        self,
        conversation_id: str,
        body: str,
        author_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a comment inside a conversation."""
        ...

    async def send_conversation_reply(
        self,
        conversation_id: str,
        payload: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a reply message on a conversation."""
        ...

    async def archive_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """Archive a conversation."""
        ...

    async def snooze_conversation(
        self,
        conversation_id: str,
        snooze_until: datetime
    ) -> Dict[str, Any]:
        """Snooze a conversation until the given time."""
        ...

    async def get_message(self, message_id: str) -> Dict[str, Any]:
        """Fetch a single message by ID."""
        ...

    async def download_attachment(self, attachment_id: str) -> bytes:
        """Download attachment content by attachment ID."""
        ...
