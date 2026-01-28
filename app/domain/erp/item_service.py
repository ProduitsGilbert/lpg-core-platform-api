"""
Item service for Business Central integration
"""
import asyncio
import logging
import logfire
from typing import Optional, List, Dict, Any, Tuple
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date

from app.domain.erp.models import ItemResponse, ItemValueChange, ItemPricesResponse
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
            item_data = await self.erp_client.get_item(item_id)
            
            if not item_data:
                logfire.info(f"Item {item_id} not found in Business Central")
                return None
            
            logfire.info(f"Successfully retrieved item {item_id}")
            return self._map_item(item_data, item_id)
                
        except Exception as e:
            logger.error(f"Error getting item {item_id}: {e}")
            raise
    
    @staticmethod
    def _parse_bc_date(value: Optional[str]) -> Optional[date]:
        """Convert Business Central date strings to date objects."""
        if not value:
            return None
        try:
            if value.startswith("0001-01-01"):
                return None
            return datetime.fromisoformat(value).date()
        except ValueError:
            return None

    async def get_item_prices(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve active sales prices for an item and derive multi-currency values."""
        with logfire.span("item_service.get_item_prices", item_id=item_id):
            sales_prices = await self.erp_client.get_sales_prices_for_item(item_id)

        if not sales_prices:
            return None

        today = date.today()
        active_prices: Dict[str, Tuple[Decimal, date]] = {}

        for entry in sales_prices:
            currency_code = (entry.get("Currency_Code") or "").strip() or "CAD"
            start_date = self._parse_bc_date(entry.get("Starting_Date")) or date.min
            end_date = self._parse_bc_date(entry.get("Ending_Date"))

            if start_date and start_date > today:
                continue
            if end_date and end_date < today:
                continue

            try:
                unit_price = Decimal(str(entry.get("Unit_Price", 0)))
            except Exception:
                logfire.warning(
                    "Skipping sales price with invalid unit price",
                    item_id=item_id,
                    currency=currency_code,
                    raw_value=entry.get("Unit_Price"),
                )
                continue

            current = active_prices.get(currency_code)
            if current is None or start_date > current[1]:
                active_prices[currency_code] = (unit_price, start_date)

        if "CAD" not in active_prices or "USD" not in active_prices:
            raise ERPError(
                f"Active CAD and USD prices are required for item {item_id}, found currencies: {list(active_prices.keys())}"
            )

        cad_price = active_prices["CAD"][0]
        usd_price = active_prices["USD"][0]

        with logfire.span("item_service.get_item_prices.exchange_rate", item_id=item_id):
            exchange_rates = await self.erp_client.get_currency_exchange_rates("EUR", top=1)

        if not exchange_rates:
            raise ERPError("No EUR exchange rate available in Business Central")

        rate_entry = exchange_rates[0]
        try:
            eur_rate = Decimal(str(rate_entry.get("Relational_Exch_Rate_Amount")))
        except Exception as exc:
            raise ERPError("Invalid EUR exchange rate value returned by Business Central") from exc

        if eur_rate <= 0:
            raise ERPError("EUR exchange rate must be greater than zero")

        eur_price = (cad_price / eur_rate).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)

        return ItemPricesResponse(
            item_id=item_id,
            cad_price=cad_price,
            usd_price=usd_price,
            eur_price=eur_price,
        )

    async def update_item(self, item_id: str, changes: List[ItemValueChange]) -> ItemResponse:
        """Update one or more item fields after validating current values."""
        if not changes:
            raise ERPError("No updates provided for item")

        with logfire.span("item_service.update_item", item_id=item_id, fields=[c.field for c in changes]):
            item_data = await self.erp_client.get_item(item_id)

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

            await self.erp_client.update_item_record(system_id, payload, etag)

            updated_item = await self.erp_client.get_item(item_id)
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
            existing = await self.erp_client.get_item(item_id)
            if existing:
                raise ERPConflict(f"Item {item_id} already exists in ERP")

            await self.erp_client.copy_item_from_template(template_item, item_id)

            created = await self.erp_client.get_item(item_id)
            if not created:
                raise ERPError("Item creation succeeded but item could not be retrieved")

            return self._map_item(created, item_id)

    async def create_purchased_item(
        self,
        item_no: str,
        description: str,
        vendor_item_no: str,
        vendor_no: Optional[str] = None,
        price: Optional[Decimal] = None,
        item_category_code: Optional[str] = None,
    ) -> ItemResponse:
        """Create a purchased item using template '000' and patch required fields."""
        with logfire.span(
            "item_service.create_purchased_item",
            item_no=item_no,
            vendor_no=vendor_no,
        ):
            existing = await self.erp_client.get_item(item_no)
            if existing:
                raise ERPConflict(f"Item {item_no} already exists in ERP")

            await self.erp_client.copy_item_from_template("000", item_no)

            await asyncio.sleep(1)

            created = await self.erp_client.get_item(item_no)
            if not created:
                raise ERPError("Item creation succeeded but item could not be retrieved")

            system_id = created.get("SystemId")
            etag = created.get("@odata.etag")
            if not system_id:
                raise ERPError("ERP response missing SystemId for item update")
            if not etag:
                raise ERPError("ERP response missing etag for item update")

            updates: Dict[str, Any] = {
                "Description": description,
                "Vendor_Item_No": vendor_item_no,
            }
            if vendor_no:
                updates["Vendor_No"] = vendor_no
            if price is not None:
                updates["Unit_Price"] = float(price)
            if item_category_code:
                updates["Item_Category_Code"] = item_category_code

            await self.erp_client.update_item_record(system_id, updates, etag)

            updated = await self.erp_client.get_item(item_no)
            if not updated:
                raise ERPError("Failed to load item after update")

            return self._map_item(updated, item_no)

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
