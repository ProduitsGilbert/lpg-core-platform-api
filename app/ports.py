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
    
    async def get_poline(self, po_id: str, line_no: int) -> Dict[str, Any]:
        """
        Retrieve PO line details from ERP.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            
        Returns:
            Dictionary with PO line details
        """
        ...
    
    async def update_poline_date(self, po_id: str, line_no: int, new_date: date) -> Dict[str, Any]:
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
    
    async def update_poline_price(self, po_id: str, line_no: int, new_price: Decimal) -> Dict[str, Any]:
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
    
    async def update_poline_quantity(self, po_id: str, line_no: int, new_quantity: Decimal) -> Dict[str, Any]:
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
    
    async def create_receipt(self, po_id: str, lines: List[Dict[str, Any]], receipt_date: date) -> Dict[str, Any]:
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

    async def reopen_purchase_order(self, header_no: str) -> Dict[str, Any]:
        """Reopen a purchase order header in the ERP system."""
        ...

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an item from ERP by its number."""
        ...

    async def update_item_record(self, system_id: str, updates: Dict[str, Any], etag: str) -> None:
        """Patch an item using its SystemId and concurrency token."""
        ...

    async def copy_item_from_template(self, template_item: str, destination_item: str) -> None:
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

    def extract_supplier_account_statement(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a supplier account statement document."""
        ...

    def extract_customer_account_statement(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a customer account statement document."""
        ...

    def extract_supplier_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a supplier invoice document."""
        ...

    def extract_shipping_bill(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a shipping bill document."""
        ...

    def extract_commercial_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a commercial invoice document."""
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


class ClickUpClientProtocol(Protocol):
    """Protocol for ClickUp API client adapters."""

    async def get_lists_in_folder(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get all lists in a specific folder."""
        ...

    async def get_tasks_in_list(
        self,
        list_id: str,
        include_closed: bool = False,
        page: Optional[int] = None,
        archived: bool = False
    ) -> Dict[str, Any]:
        """Get tasks from a specific list."""
        ...

    async def get_task(self, task_id: str) -> Dict[str, Any]:
        """Get a specific task by ID."""
        ...

    async def get_folder(self, folder_id: str) -> Dict[str, Any]:
        """Get folder information."""
        ...

    async def get_list(self, list_id: str) -> Dict[str, Any]:
        """Get list information."""
        ...


class ZendeskClientProtocol(Protocol):
    """Protocol for Zendesk API client adapters."""

    async def search_tickets(
        self,
        query: str,
        page: Optional[int] = None,
        per_page: Optional[int] = None
    ) -> Dict[str, Any]:
        """Search for tickets using Zendesk search API."""
        ...

    async def list_tickets(
        self,
        status: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        sort_by: Optional[str] = None,
        sort_order: Optional[str] = None
    ) -> Dict[str, Any]:
        """List tickets with optional filtering."""
        ...

    async def get_ticket(self, ticket_id: int) -> Dict[str, Any]:
        """Get a specific ticket by ID."""
        ...

    async def export_search_results(
        self,
        query: str,
        page_size: Optional[int] = None,
        after_cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Export search results using cursor-based pagination."""
        ...
