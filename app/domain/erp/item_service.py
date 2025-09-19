"""
Item service for Business Central integration
"""
import logging
import logfire
from typing import Optional, List, Dict, Any
from decimal import Decimal
from datetime import datetime

from app.domain.erp.models import ItemResponse, ItemValueChange
from app.adapters.erp_client import ERPClient
from app.errors import ERPNotFound, ERPConflict, ERPError

logger = logging.getLogger(__name__)

class ItemService:
    """Service for item operations with Business Central"""
    
    def __init__(self):
        self.erp_client = ERPClient()
    
    def _map_item(self, item_data: Dict[str, Any], fallback_id: str) -> ItemResponse:
        """Convert raw ERP item payload into ItemResponse."""
        return ItemResponse(
            id=item_data.get("No", fallback_id),
            description=item_data.get("Description", ""),
            unit_of_measure=item_data.get("Base_Unit_of_Measure", "EA"),
            unit_cost=Decimal(str(item_data.get("Unit_Cost", 0))),
            unit_price=Decimal(str(item_data.get("Unit_Price", 0))),
            inventory=Decimal(str(item_data.get("Inventory", 0))),
            item_category_code=item_data.get("Item_Category_Code"),
            blocked=item_data.get("Blocked", False),
            last_modified=datetime.fromisoformat(item_data["Last_Date_Modified"]) if item_data.get("Last_Date_Modified") else None,
            vendor_id=item_data.get("Vendor_No"),
            vendor_name=item_data.get("Vendor_Name"),
            vendor_item_no=item_data.get("Vendor_Item_No"),
            qty_on_purchase_order=Decimal(str(item_data.get("Qty_on_Purch_Order", 0))),
            qty_on_sales_order=Decimal(str(item_data.get("Qty_on_Sales_Order", 0))),
            lead_time_calculation=item_data.get("Lead_Time_Calculation"),
            replenishment_system=item_data.get("Replenishment_System"),
            gross_weight=Decimal(str(item_data.get("Gross_Weight", 0))) if item_data.get("Gross_Weight") else None,
            net_weight=Decimal(str(item_data.get("Net_Weight", 0))) if item_data.get("Net_Weight") else None,
            country_region_of_origin=item_data.get("Country_Region_of_Origin_Code"),
            safety_stock_quantity=Decimal(str(item_data.get("Safety_Stock_Quantity", 0))) if item_data.get("Safety_Stock_Quantity") else None
        )

    async def get_item(self, item_id: str) -> Optional[ItemResponse]:
        """
        Get item from Business Central
        
        Args:
            item_id: Item number/ID
            
        Returns:
            ItemResponse or None if not found
        """
        try:
            # Get item data from ERP
            item_data = self.erp_client.get_item(item_id)
            
            if not item_data:
                logfire.info(f"Item {item_id} not found in Business Central")
                return None
            
            logfire.info(f"Successfully retrieved item {item_id}")
            return self._map_item(item_data, item_id)
                
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            raise

    async def update_item(self, item_id: str, changes: List[ItemValueChange]) -> ItemResponse:
        """Update one or more item fields after validating current values."""
        if not changes:
            raise ERPError("No updates provided for item")

        with logfire.span("item_service.update_item", item_id=item_id, fields=[c.field for c in changes]):
            item_data = self.erp_client.get_item(item_id)

            if not item_data:
                raise ERPNotFound("Item", item_id)

            system_id = item_data.get("SystemId")
            etag = item_data.get("@odata.etag", "*")

            if not system_id:
                raise ERPError("ERP response missing SystemId for item update")

            mismatches = []
            payload: Dict[str, Any] = {}

            for change in changes:
                current_value = item_data.get(change.field)
                if change.current_value is not None:
                    if not self._values_match(current_value, change.current_value):
                        mismatches.append({
                            "field": change.field,
                            "expected": change.current_value,
                            "actual": current_value
                        })
                        continue

                payload[change.field] = change.new_value

            if mismatches:
                raise ERPConflict(
                    "Item has changed in ERP; one or more current values differ",
                )

            if not payload:
                raise ERPConflict("No updates applied; payload is empty")

            self.erp_client.update_item_record(system_id, payload, etag)

            updated_item = self.erp_client.get_item(item_id)
            if not updated_item:
                raise ERPError("Failed to load item after update")

            return self._map_item(updated_item, item_id)

    async def create_item_from_template(self, item_id: str, template_item: str) -> ItemResponse:
        """Create a new item by copying from a template."""
        with logfire.span(
            "item_service.create_item_from_template",
            item_id=item_id,
            template_item=template_item
        ):
            existing = self.erp_client.get_item(item_id)
            if existing:
                raise ERPConflict(f"Item {item_id} already exists in ERP")

            self.erp_client.copy_item_from_template(template_item, item_id)

            created = self.erp_client.get_item(item_id)
            if not created:
                raise ERPError("Item creation succeeded but item could not be retrieved")

            return self._map_item(created, item_id)

    async def create_purchased_item(self, item_id: str) -> ItemResponse:
        """Create a purchased item using template '000'."""
        return await self.create_item_from_template(item_id, template_item="000")

    async def create_manufactured_item(self, item_id: str) -> ItemResponse:
        """Create a manufactured item using template '00000'."""
        return await self.create_item_from_template(item_id, template_item="00000")

    @staticmethod
    def _values_match(current: Any, expected: Any) -> bool:
        """Normalize values before comparison to avoid false mismatches."""
        if isinstance(current, Decimal) and isinstance(expected, (Decimal, int, float, str)):
            try:
                return Decimal(str(current)) == Decimal(str(expected))
            except Exception:
                return str(current) == str(expected)
        return current == expected
