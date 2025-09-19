"""
Purchase Order service for Business Central integration
"""
import logging
import logfire
from typing import Optional, List
from decimal import Decimal
from datetime import date, datetime

from app.domain.erp.models import PurchaseOrderResponse, PurchaseOrderLineResponse
from app.adapters.erp_client import ERPClient

logger = logging.getLogger(__name__)

class PurchaseOrderService:
    """Service for purchase order operations with Business Central"""
    
    def __init__(self):
        self.erp_client = ERPClient()
    
    async def get_purchase_order(self, po_id: str) -> Optional[PurchaseOrderResponse]:
        """
        Get purchase order from Business Central
        
        Args:
            po_id: Purchase order number
            
        Returns:
            PurchaseOrderResponse or None if not found
        """
        try:
            with logfire.span(f"po_service.get_purchase_order", po_id=po_id):
                # Get PO data from ERP
                po_data = self.erp_client.get_purchase_order(po_id)
                
                if not po_data:
                    logfire.info(f"Purchase order {po_id} not found")
                    return None
                
                # Map to response model
                po = PurchaseOrderResponse(
                    id=po_data.get("No", po_id),
                    vendor_id=po_data.get("Buy_from_Vendor_No", ""),
                    vendor_name=po_data.get("Buy_from_Vendor_Name", ""),
                    order_date=date.fromisoformat(po_data.get("Order_Date", str(date.today()))),
                    expected_receipt_date=date.fromisoformat(po_data["Expected_Receipt_Date"]) if po_data.get("Expected_Receipt_Date") else None,
                    status=po_data.get("Status", "Open"),
                    total_amount=Decimal(str(po_data.get("Amount_Including_VAT", 0))),
                    currency_code=po_data.get("Currency_Code", "USD"),
                    buyer_id=po_data.get("Purchaser_Code"),
                    location_code=po_data.get("Location_Code")
                )
                
                logfire.info(f"Successfully retrieved purchase order {po_id}")
                return po
                
        except Exception as e:
            logger.error(f"Error getting purchase order {po_id}: {e}")
            raise
    
    async def get_purchase_order_lines(self, po_id: str) -> Optional[List[PurchaseOrderLineResponse]]:
        """
        Get purchase order lines from Business Central
        
        Args:
            po_id: Purchase order number
            
        Returns:
            List of PurchaseOrderLineResponse or None if PO not found
        """
        try:
            with logfire.span(f"po_service.get_purchase_order_lines", po_id=po_id):
                # Check if PO exists
                po_exists = self.erp_client.get_purchase_order(po_id)
                if not po_exists:
                    return None
                
                # Get lines from ERP
                lines_data = self.erp_client.get_purchase_order_lines(po_id)
                
                if not lines_data:
                    logfire.info(f"No lines found for purchase order {po_id}")
                    return []
                
                # Map to response models with all Gilbert custom fields
                lines = []
                for line_data in lines_data:
                    # Helper function to parse dates
                    def parse_date(date_str):
                        if date_str and date_str != "0001-01-01":
                            try:
                                return date.fromisoformat(date_str[:10])  # Take first 10 chars for date part
                            except:
                                return None
                        return None
                    
                    line = PurchaseOrderLineResponse(
                        id=f"{po_id}-{line_data.get('Line_No', 0)}",
                        line_no=line_data.get("Line_No", 0),
                        item_no=line_data.get("No", ""),
                        description=line_data.get("Description", ""),
                        quantity=Decimal(str(line_data.get("Quantity", 0))),
                        quantity_received=Decimal(str(line_data.get("Quantity_Received", 0))),
                        quantity_invoiced=Decimal(str(line_data.get("Quantity_Invoiced", 0))),
                        outstanding_qty=Decimal(str(line_data.get("Outstanding_Qty", 0))) if line_data.get("Outstanding_Qty") else None,
                        unit_of_measure=line_data.get("Unit_of_Measure_Code", "EA"),
                        unit_cost=Decimal(str(line_data.get("Direct_Unit_Cost", 0))),
                        line_amount=Decimal(str(line_data.get("Line_Amount", 0))),
                        promised_receipt_date=parse_date(line_data.get("Promised_Receipt_Date")),
                        expected_receipt_date=parse_date(line_data.get("Expected_Receipt_Date")),
                        mrp_date_requise=parse_date(line_data.get("MRP_Date_Requise")),
                        location_code=line_data.get("Location_Code"),
                        vendor_item_no=line_data.get("Vendor_Item_No"),
                        suivi_status=line_data.get("Suivi_Status"),
                        no_suivi=line_data.get("No_Suivi"),
                        no_job_ref=line_data.get("No_Job_Ref"),
                        job_no=line_data.get("Job_No"),
                        job_task_no=line_data.get("Job_Task_No")
                    )
                    lines.append(line)
                
                logfire.info(f"Successfully retrieved {len(lines)} lines for purchase order {po_id}")
                return lines
                
        except Exception as e:
            logger.error(f"Error getting purchase order lines for {po_id}: {e}")
            raise