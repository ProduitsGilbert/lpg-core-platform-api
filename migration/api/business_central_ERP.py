"""
Business Central integration client
Streamlined version with only essential functions needed by V2 processors
Based on migrations/BC.py HTTP API calls
"""

import asyncio
import functools
import logging
from typing import Any

import aiohttp

from ..config import settings

logger = logging.getLogger(__name__)


def retry_bc_api(max_retries=3, initial_delay=1.0, backoff_factor=2.0, max_delay=30.0):
    """
    Retry decorator for BC API calls with exponential backoff

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Factor to multiply delay by for each retry
        max_delay: Maximum delay between retries in seconds
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None

            for attempt in range(max_retries + 1):  # +1 for initial attempt
                try:
                    result = await func(*args, **kwargs)

                    # Consider None result as a failure for critical operations
                    if result is None and "update" in func.__name__.lower():
                        if attempt < max_retries:
                            logger.warning(
                                f"🔄 BC API returned None for {func.__name__}, attempt {attempt + 1}/{max_retries + 1}"
                            )
                            await asyncio.sleep(delay)
                            delay = min(delay * backoff_factor, max_delay)
                            continue

                    # Success - log retry recovery if we had previous failures
                    if attempt > 0:
                        logger.info(f"✅ BC API recovered for {func.__name__} after {attempt} retries")

                    return result

                except Exception as e:
                    last_exception = e

                    # Don't retry on certain types of errors
                    if "authentication" in str(e).lower() or "unauthorized" in str(e).lower():
                        logger.error(f"❌ BC API authentication error, not retrying: {e}")
                        break

                    if attempt < max_retries:
                        logger.warning(
                            f"🔄 BC API error for {func.__name__}, attempt {attempt + 1}/{max_retries + 1}: {e}"
                        )
                        logger.info(f"⏱️ Retrying in {delay:.1f}s...")
                        await asyncio.sleep(delay)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        logger.error(f"💥 BC API failed after {max_retries + 1} attempts: {e}")

            # All retries exhausted
            if last_exception:
                raise last_exception
            return None

        return wrapper

    return decorator


class BCClient:
    """
    Streamlined Business Central client using HTTP API
    Only includes functions actually used by V2 processors
    """

    def __init__(self):
        self.base_url = "https://bc.gilbert-tech.com:7063/ProductionBCBasic/ODataV4/Company('Gilbert-Tech')"
        self.api_url = "https://bc.gilbert-tech.com:7063/ProductionBCBasic/api/GITECH/Explorateur/beta"
        # Use API credentials for HTTP/OData access
        self.username = settings.bc_api_username
        self.password = settings.bc_api_password
        self.session = None

        # Configure timeout and retry settings
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        # Note: V1 uses lowercase 't' in Gilbert-tech
        self.headers = {"company": "Gilbert-tech"}

    async def __aenter__(self):
        """Async context manager entry"""
        # Create connector with SSL verification handling
        # In production, use proper certificates
        connector = aiohttp.TCPConnector(limit=10, ssl=False)  # Disable SSL verification for self-signed certificates
        self.session = aiohttp.ClientSession(
            auth=aiohttp.BasicAuth(self.username, self.password), timeout=self.timeout, connector=connector
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()

    async def _make_request(self, method: str, url: str, **kwargs) -> dict[str, Any] | None:
        """Make authenticated request to Business Central"""
        try:
            # Ensure we have a session
            if not self.session:
                # Create a new session if needed
                connector = aiohttp.TCPConnector(limit=10, ssl=False)
                self.session = aiohttp.ClientSession(
                    auth=aiohttp.BasicAuth(self.username, self.password), timeout=self.timeout, connector=connector
                )

            # Add default headers
            headers = kwargs.get("headers", {})
            headers.update(self.headers)
            kwargs["headers"] = headers

            # Log outgoing request for debugging
            if "PurchaseOrderLines" in url and "filter" in url:
                logger.debug(f"📤 BC API Request: {method} {url}")

            async with self.session.request(method, url, **kwargs) as response:
                if response.status in [200, 201]:
                    json_data = await response.json()
                    # Log successful responses for PO lines
                    if "PurchaseOrderLines" in url and method == "GET":
                        value_count = len(json_data.get("value", [])) if json_data else 0
                        logger.debug(f"📥 BC API Response: Status {response.status}, {value_count} records")
                    return json_data
                elif response.status == 204:
                    return {"success": True}  # For POST/PATCH operations with no content
                else:
                    text = await response.text()
                    logger.error(f"❌ BC API error {response.status} for {url}: {text[:500]}")
                    return None
        except Exception as e:
            logger.error(f"💥 BC API request failed for {url}: {e}")
            return None

    # Essential functions for processors

    async def get_item_card(self, item_number: str) -> dict[str, Any] | None:
        """
        Get item card from Business Central
        Used by: SoumissionProcessor, CreationProcessor, RevisionProcessor
        Migrated from BC.py Get_ItemCard()
        """
        item_number = item_number.strip()
        if len(item_number) == 7 and item_number.isdigit():
            url = f"{self.base_url}/ItemCard('{item_number}')"
            return await self._make_request("GET", url)
        return None

    async def get_vendor_from_po_no(self, po_number: str) -> str | None:
        """
        Get vendor from PO number
        Used by: EnvoiPlanProcessor
        Migrated from BC.py get_Vendor_From_PO_No()
        """
        url = f"{self.base_url}/PurchaseOrderHeaders?$filter=No eq '{po_number}'&$select=Buy_from_Vendor_No"
        data = await self._make_request("GET", url)

        if data and data.get("value"):
            return data["value"][0].get("Buy_from_Vendor_No")
        return None

    async def get_po_header(self, po_number: str) -> dict[str, Any] | None:
        """
        Get PO header information from Business Central
        Used by: JulesClient for enhanced context
        Returns: PO header dictionary with order date, status, etc.
        """
        url = f"{self.base_url}/PurchaseOrderHeaders?$filter=No eq '{po_number}'&$select=No,Document_Date,Requested_Receipt_Date,Status,Buy_from_Vendor_No,Buy_from_Vendor_Name,Purchaser_Code"
        data = await self._make_request("GET", url)

        if data and data.get("value") and len(data.get("value", [])) > 0:
            header = data["value"][0]
            # Convert field names to camelCase for consistency
            return {
                "no": header.get("No"),
                "orderDate": header.get("Document_Date"),
                "requestedReceiptDate": header.get("Requested_Receipt_Date"),
                "status": header.get("Status"),
                "vendorNo": header.get("Buy_from_Vendor_No"),
                "vendorName": header.get("Buy_from_Vendor_Name"),
                "purchaserCode": header.get("Purchaser_Code"),
            }
        return None

    async def get_purchase_order(self, po_number: str) -> dict[str, Any] | None:
        """
        Get purchase order header data from Business Central
        Used by: ConfirmationProcessorAI
        Returns complete PO header information
        """
        url = f"{self.base_url}/PurchaseOrderHeaders?$filter=No eq '{po_number}'&$select=No,Buy_from_Vendor_No,Buy_from_Vendor_Name,Document_Date,Requested_Receipt_Date,Status,Purchaser_Code"
        data = await self._make_request("GET", url)

        if data and data.get("value") and len(data.get("value", [])) > 0:
            header = data["value"][0]
            return {
                "po_number": header.get("No"),
                "vendor_code": header.get("Buy_from_Vendor_No"),
                "vendor_name": header.get("Buy_from_Vendor_Name"),
                "order_date": header.get("Document_Date"),
                "requested_receipt_date": header.get("Requested_Receipt_Date"),
                "status": header.get("Status"),
                "purchaser_code": header.get("Purchaser_Code"),
            }

        logger.warning(f"PO {po_number} not found in Business Central")
        return None

    async def get_purchase_order_lines(self, po_number: str) -> list[dict[str, Any]] | None:
        """
        Get purchase order lines from Business Central
        Used by: ConfirmationProcessorAI
        Returns list of PO lines with all relevant fields
        """
        # Use the existing get_po_line method for consistency
        lines = await self.get_po_line(po_number)

        if lines:
            # Format lines for confirmation processor
            formatted_lines = []
            for line in lines:
                formatted_lines.append(
                    {
                        "line_no": line.get("Line_No"),
                        "item_no": line.get("No"),
                        "vendor_item_no": line.get("Vendor_Item_No"),  # Add vendor's item number for cross-reference
                        "description": line.get("Description"),
                        "quantity": line.get("Quantity"),
                        "quantity_received": line.get("Quantity_Received"),
                        "unit_of_measure": line.get("Unit_of_Measure_Code"),
                        "unit_cost": line.get("Direct_Unit_Cost"),
                        "line_amount": line.get("Line_Amount"),  # Add total line amount
                        "promised_receipt_date": line.get("Promised_Receipt_Date"),
                        "type": line.get("Type"),
                        "job_no": line.get("Job_No"),
                        "job_task_no": line.get("Job_Task_No"),
                    }
                )
            return formatted_lines

        return None

    async def get_po_line(self, po_number: str) -> list[dict[str, Any]] | None:
        """
        Get PO lines from Business Central
        Used by: EnvoiPlanProcessor, ConfirmationProcessor
        Migrated from BC.py Get_PO_Line()
        Returns: List of PO line dictionaries, or None if not found
        """
        # Include Type in selection to filter properly
        # Include Job fields for updating (No G_L field in lines - it's based on Type)
        # Include Vendor_Item_No and Line_Amount for better confirmation matching
        url = f"{self.base_url}/PurchaseOrderLines?$filter=Document_No eq '{po_number}'&$select=Document_No,No,Description,Promised_Receipt_Date,Quantity,Quantity_Received,Line_No,Prod_Order_No,Prod_Order_Line_No,Operation_No,Type,Unit_of_Measure_Code,Direct_Unit_Cost,Job_No,Job_Task_No,Vendor_Item_No,Line_Amount"

        logger.info(f"🔍 Fetching PO lines for {po_number} from BC API")
        logger.debug(f"BC API URL: {url}")

        data = await self._make_request("GET", url)

        if data and data.get("value"):
            all_lines = data.get("value", [])

            # Log raw response details
            logger.info(f"📦 BC API returned {len(all_lines)} total lines for PO {po_number}")

            # IMPORTANT: Include ALL valid lines (Item AND G/L Account) for confirmation processing
            # Only filter out truly empty/comment lines
            valid_lines = []
            for line in all_lines:
                # Include if has a number (Item or G/L account) OR meaningful description
                if (line.get("No") and line.get("No").strip()) or (
                    line.get("Description") and line.get("Description").strip() and line.get("Quantity")
                ):
                    valid_lines.append(line)
                    logger.debug(
                        f"✅ Valid line {line.get('Line_No')}: Type={line.get('Type')}, No={line.get('No')}, Desc={line.get('Description')[:30] if line.get('Description') else 'None'}"
                    )
                else:
                    logger.debug(
                        f"⏭️ Skipping empty line in PO {po_number}: No={line.get('No')}, Desc={line.get('Description')[:20] if line.get('Description') else 'None'}"
                    )

            logger.info(
                f"✅ Retrieved {len(valid_lines)} valid lines (from {len(all_lines)} total lines) for PO {po_number}"
            )
            return valid_lines
        else:
            logger.warning(f"⚠️ No data returned from BC API for PO {po_number}. Response: {data}")
        return None

    async def get_email_from_vendor(self, vendor_no: str) -> str:
        """
        Get vendor email address
        Used by: SoumissionProcessor
        Migrated from BC.py GetEmailFromVendor()
        """
        # Special case for WAJIN01 (from V1 logic)
        if vendor_no == "WAJIN01":
            return "qc600ventes@wajax.com"

        url = f"{self.api_url}/easyPDFAddress?$filter=ownerNo eq '{vendor_no}' and addressType eq 'To' and documentCode eq 'PURCHASE ORDER'"
        data = await self._make_request("GET", url)

        if data and data.get("value") and len(data["value"]) > 0:
            return data["value"][0].get("address", "")

        logger.warning(f"No email found for vendor {vendor_no}")
        return ""

    async def get_language_from_vendor(self, vendor_no: str) -> str:
        """
        Get vendor language preference
        Used by: SoumissionProcessor
        Migrated from BC.py GetLangueFromVendor()
        """
        url = f"{self.base_url}/Vendor?$filter=No eq '{vendor_no}'&$select=Language_Code"
        data = await self._make_request("GET", url)

        if data and data.get("value") and len(data["value"]) > 0:
            language_code = data["value"][0].get("Language_Code")
            if language_code != "FRA":
                return "English"
            else:
                return "Francais"

        return "English"  # Default fallback

    async def create_purchased_item(self, item_number: str) -> bool:
        """
        Create new purchased item
        Used by: CreationProcessor
        Migrated from BC.py Creation_new_Item_Achetees()
        """
        url = "https://bc.gilbert-tech.com:7063/ProductionBCBasic/ODataV4/copyItems_copyItemFrom"
        data = {"sourceItem": "000", "destinationItem": item_number}

        result = await self._make_request("POST", url, json=data)
        if result:
            logger.info(f"Created purchased item {item_number}")
            return True
        else:
            logger.error(f"Failed to create purchased item {item_number}")
            return False

    async def update_item(
        self, item_number: str, description: str, vendor_item: str, price: float, item_type: str = "SCIERIE"
    ) -> bool:
        """
        Update item in Business Central
        Used by: CreationProcessor
        Migrated from BC.py Update_Item()
        """
        try:
            # Get current item data first for etag
            item_data = await self.get_item_card(item_number)
            if not item_data:
                return False

            if not price:
                price = 0.0

            # Calculate standard price (5% markup)
            std_price = float(price) * 1.05

            update_data = {
                "Description": description,
                "Vendor_Item_No": vendor_item,
                "Last_Direct_Cost": price,
                "Unit_Cost": price,
                "Standard_Cost": std_price,
                "Item_Category_Code": item_type,
            }

            # Get etag for update
            etag = item_data.get("@odata.etag", "*")
            headers = {"if-match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            url = f"{self.base_url}/ItemCard('{item_number}')"
            result = await self._make_request("PATCH", url, json=update_data, headers=headers)

            if result:
                logger.info(f"Updated item {item_number}")
                return True
            else:
                logger.error(f"Failed to update item {item_number}")
                return False

        except Exception as e:
            logger.error(f"Error updating item {item_number}: {e}")
            return False

    async def get_po_line_etag(self, po_number: str, line_no: str) -> str | None:
        """
        Get PO line etag for updates
        Used by: ConfirmationProcessor (via confirmation_commande.py)
        Migrated from BC.py get_PO_Line_etag()
        """
        url = f"{self.base_url}/PurchaseOrderLines?$filter=Document_No eq '{po_number}' and Line_No eq {line_no}"
        data = await self._make_request("GET", url)

        if data and data.get("value") and len(data["value"]) > 0:
            return data["value"][0].get("@odata.etag")
        return None

    @retry_bc_api(max_retries=3, initial_delay=2.0)
    async def update_po_order_confirmation(
        self, po_number: str, line_no: str, etag: str, quantity: float, unit_cost: float, delivery_date: str
    ) -> bool:
        """
        Update PO line with order confirmation data
        Used by: ConfirmationProcessor (via confirmation_commande.py)
        Migrated from BC.py Update_PO_OrderConfirmation()
        """
        try:
            update_data = {"Quantity": quantity, "Direct_Unit_Cost": unit_cost, "Promised_Receipt_Date": delivery_date}

            logger.info(
                f"Attempting to update PO {po_number} line {line_no} with: "
                f"Qty={quantity}, Cost={unit_cost}, Delivery={delivery_date}"
            )

            headers = {"if-match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            # PurchaseOrderLines requires 3 keys: Document_Type, Document_No, Line_No
            url = f"{self.base_url}/PurchaseOrderLines('Order','{po_number}',{line_no})"
            result = await self._make_request("PATCH", url, json=update_data, headers=headers)

            if result:
                logger.info(
                    f"✅ Successfully updated PO {po_number} line {line_no} - " f"Delivery date set to {delivery_date}"
                )
                return True
            else:
                logger.error(f"❌ Failed to update PO {po_number} line {line_no} - " f"BC API returned None/False")
                return False

        except Exception as e:
            logger.error(f"Error updating PO {po_number} line {line_no}: {e}")
            return False

    @retry_bc_api(max_retries=3, initial_delay=1.5)
    async def update_po_line(self, po_number: str, line_no: int, update_data: dict[str, Any]) -> bool:
        """Update a Purchase Order line with specified fields

        Args:
            po_number: Purchase order number
            line_no: Line number to update
            update_data: Dictionary of fields to update (e.g., G_L_Account_No, Job_No, etc.)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current etag for the line
            etag = await self.get_po_line_etag(po_number, line_no)
            if not etag:
                logger.error(f"Could not get etag for PO {po_number} line {line_no}")
                return False

            # Update the line
            url = (
                f"{self.base_url}/PurchaseOrderLines(Document_Type='Order',Document_No='{po_number}',Line_No={line_no})"
            )
            headers = {"if-match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            result = await self._make_request("PATCH", url, json=update_data, headers=headers)

            if result:
                logger.info(f"Successfully updated PO {po_number} line {line_no}")
                return True
            else:
                logger.error(f"Failed to update PO {po_number} line {line_no}")
                return False

        except Exception as e:
            logger.error(f"Error updating PO {po_number} line {line_no}: {e}")
            return False

    async def get_revision(self, part_number: str) -> str | None:
        """
        Get part revision from Business Central
        Used by: EnvoiPlanProcessor
        Migrated from BC.py get_revision()
        """
        url = f"{self.base_url}/Item?$filter=No eq '{part_number}'&$select=No,Description"
        data = await self._make_request("GET", url)

        if data and data.get("value") and len(data["value"]) > 0:
            # Extract revision from description or other field
            # This is a simplified version - real implementation may need PLM integration
            return "A"  # Default revision
        return None

    @retry_bc_api(max_retries=3, initial_delay=1.5)
    async def update_po_line_price(self, po_number: str, line_no: int, new_price: float) -> bool:
        """
        Update the unit price of a PO line in Business Central
        Used by: ConfirmationProcessorAI for price discrepancy updates
        """
        try:
            # Get the key ID for the line
            filter_query = f"Document_Type eq 'Order' and Document_No eq '{po_number}' and Line_No eq {line_no}"
            url = f"{self.base_url}/PurchaseOrderLines?$filter={filter_query}"

            data = await self._make_request("GET", url)

            if not data or not data.get("value") or len(data["value"]) == 0:
                logger.error(f"PO line not found: {po_number} line {line_no}")
                return False

            line_data = data["value"][0]
            etag = line_data.get("@odata.etag", "")

            # Update the price
            update_data = {"Direct_Unit_Cost": new_price}

            # Make the PATCH request with proper headers
            headers = {"If-Match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            # Use the full path with systemId for the update
            if "systemId" in line_data:
                update_url = f"{self.base_url}/PurchaseOrderLines('{line_data['systemId']}')"
            else:
                # Fallback to using composite key
                update_url = f"{self.base_url}/PurchaseOrderLines(Document_Type='Order',Document_No='{po_number}',Line_No={line_no})"

            result = await self._make_request("PATCH", update_url, json=update_data, headers=headers)

            if result:
                logger.info(f"Successfully updated PO {po_number} line {line_no} price to {new_price}")
                return True
            else:
                logger.error(f"Failed to update PO {po_number} line {line_no} price")
                return False

        except Exception as e:
            logger.error(f"Error updating PO {po_number} line {line_no} price: {e}")
            return False

    @retry_bc_api(max_retries=3, initial_delay=1.5)
    async def update_po_line_delivery(self, po_number: str, line_no: int, delivery_date: str) -> bool:
        """
        Update the delivery date of a PO line in Business Central
        Used by: ConfirmationProcessorV3 for updating promised receipt dates

        Args:
            po_number: Purchase order number
            line_no: Line number to update
            delivery_date: New delivery date in YYYY-MM-DD format

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the key ID for the line
            filter_query = f"Document_Type eq 'Order' and Document_No eq '{po_number}' and Line_No eq {line_no}"
            url = f"{self.base_url}/PurchaseOrderLines?$filter={filter_query}"

            logger.info(f"📅 Attempting to update delivery date for PO {po_number} line {line_no} to {delivery_date}")

            data = await self._make_request("GET", url)

            if not data or not data.get("value") or len(data["value"]) == 0:
                logger.error(f"❌ PO line not found: {po_number} line {line_no}")
                return False

            line_data = data["value"][0]
            etag = line_data.get("@odata.etag", "")

            # Update the delivery date
            update_data = {"Promised_Receipt_Date": delivery_date}

            # Make the PATCH request with proper headers
            headers = {"If-Match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            # Use the full path with systemId for the update
            if "systemId" in line_data:
                update_url = f"{self.base_url}/PurchaseOrderLines('{line_data['systemId']}')"
            else:
                # Fallback to using composite key
                update_url = f"{self.base_url}/PurchaseOrderLines(Document_Type='Order',Document_No='{po_number}',Line_No={line_no})"

            result = await self._make_request("PATCH", update_url, json=update_data, headers=headers)

            if result:
                logger.info(f"✅ Successfully updated PO {po_number} line {line_no} delivery date to {delivery_date}")
                return True
            else:
                logger.error(f"❌ Failed to update PO {po_number} line {line_no} delivery date")
                return False

        except Exception as e:
            logger.error(f"💥 Error updating PO {po_number} line {line_no} delivery date: {e}")
            return False

    @retry_bc_api(max_retries=3, initial_delay=1.5)
    async def update_po_line_quantity(self, po_number: str, line_no: int, new_quantity: float) -> bool:
        """
        Update the quantity of a PO line in Business Central
        Used by: ConfirmationProcessorAI for updating quantities

        Args:
            po_number: Purchase order number
            line_no: Line number to update
            new_quantity: New quantity

        Returns:
            True if successful, False otherwise
        """
        try:
            # Get the key ID for the line
            filter_query = f"Document_Type eq 'Order' and Document_No eq '{po_number}' and Line_No eq {line_no}"
            url = f"{self.base_url}/PurchaseOrderLines?$filter={filter_query}"

            logger.info(f"📦 Attempting to update quantity for PO {po_number} line {line_no} to {new_quantity}")

            data = await self._make_request("GET", url)

            if not data or not data.get("value") or len(data["value"]) == 0:
                logger.error(f"❌ PO line not found: {po_number} line {line_no}")
                return False

            line_data = data["value"][0]
            etag = line_data.get("@odata.etag", "")

            # Update the quantity
            update_data = {"Quantity": new_quantity}

            # Make the PATCH request with proper headers
            headers = {"If-Match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            # Use the full path with systemId for the update
            if "systemId" in line_data:
                update_url = f"{self.base_url}/PurchaseOrderLines('{line_data['systemId']}')"
            else:
                # Fallback to using composite key
                update_url = f"{self.base_url}/PurchaseOrderLines(Document_Type='Order',Document_No='{po_number}',Line_No={line_no})"

            result = await self._make_request("PATCH", update_url, json=update_data, headers=headers)

            if result:
                logger.info(f"✅ Successfully updated PO {po_number} line {line_no} quantity to {new_quantity}")
                return True
            else:
                logger.error(f"❌ Failed to update PO {po_number} line {line_no} quantity")
                return False

        except Exception as e:
            logger.error(f"💥 Error updating PO {po_number} line {line_no} quantity: {e}")
            return False

    async def update_achat_kpi(self, type_: str, sous_type: str, vendor: str = "") -> bool:
        """
        Update KPI tracking
        Used by: BaseProcessor
        Simplified version for V2
        """
        try:
            # This would integrate with KPI tracking system
            # For now, just log the KPI update
            logger.info(f"KPI Update: {type_}/{sous_type}/{vendor}")
            return True
        except Exception as e:
            logger.error(f"Error updating KPI: {e}")
            return False

    async def get_job_task_lines(self, job_number: str) -> list[dict[str, Any]] | None:
        """
        Get job task lines for a specific job
        Used by: RequisitionPeintureProcessor
        """
        try:
            # Get job task lines
            url = (
                f"{self.base_url}/JobTaskLines?$filter=Job_No eq '{job_number}'&$select=Job_No,Job_Task_No,Description"
            )

            data = await self._make_request("GET", url)

            if data and data.get("value"):
                task_lines = data.get("value", [])
                logger.info(f"Retrieved {len(task_lines)} task lines for job {job_number}")
                return task_lines
            else:
                logger.info(f"No task lines found for job {job_number}")
                return []

        except Exception as e:
            logger.error(f"Error getting job task lines: {e}")
            return []

    async def add_paint_line_to_po(self, po_number: str, job_no: str, job_task_no: str = "") -> bool:
        """
        Add a paint (PEINTURE) line to a purchase order
        Used by: RequisitionPeintureProcessor
        """
        try:
            # Prepare the new line data
            new_line = {
                "Document_Type": "Order",
                "Document_No": po_number,
                "Type": "Item",
                "No": "PEINTURE",
                "Description": "Paint/Peinture",
                "Quantity": 1,
                "Direct_Unit_Cost": 0,
                "Job_No": job_no if job_no else "",
                "Job_Task_No": job_task_no if job_task_no else "",
            }

            url = f"{self.base_url}/PurchaseOrderLines"

            # Use the session's _make_request method which handles auth properly
            result = await self._make_request("POST", url, json=new_line)

            if result:
                logger.info(f"Added PEINTURE line to PO {po_number} for job {job_no}")
                return True
            else:
                logger.error(f"Failed to add paint line to PO {po_number}")
                return False

        except Exception as e:
            logger.error(f"Error adding paint line to PO: {e}")
            return False

    async def is_item_purchased(self, item_number: str) -> bool:
        """
        Check if item is purchased (not manufactured)
        Used by: DelaisProcessor
        Migrated from BC.py Get_if_achetee()
        """
        try:
            # Use same endpoint as V1: Items with specific filter
            url = f"{self.base_url}/Items?$filter=No eq '{item_number}'&$select=Replenishment_System"
            data = await self._make_request("GET", url)

            if data and data.get("value") and len(data["value"]) > 0:
                replenishment = data["value"][0].get("Replenishment_System", "")
                # V1 logic: Purchase items have "Purchase" value
                return replenishment == "Purchase"

            return False

        except Exception as e:
            logger.error(f"Error checking if item {item_number} is purchased: {e}")
            return False

    async def get_subcontracting_worksheets(self, filters: str = None, limit: int = 100) -> list[dict[str, Any]] | None:
        """
        Get subcontracting worksheets from Business Central
        Used by: DemandeTraitementProcessor

        Args:
            filters: OData filter string (e.g., "Prod_Order_No eq 'M173732'")
            limit: Maximum number of records to return

        Returns:
            List of subcontracting worksheet records
        """
        try:
            url = f"{self.base_url}/SubcontractingWorksheets"
            params = {"$top": limit}

            if filters:
                params["$filter"] = filters

            data = await self._make_request("GET", url, params=params)

            if data and data.get("value"):
                logger.info(f"Retrieved {len(data['value'])} subcontracting worksheet records")
                return data["value"]

            return []

        except Exception as e:
            logger.error(f"Error getting subcontracting worksheets: {e}")
            return []

    async def get_posted_receipt_dates(self, item_number: str) -> dict[str, Any] | None:
        """
        Get posted receipt dates for item purchase history
        Used by: DelaisProcessor
        Migrated from BC.py Get_PostedReceiptDate()
        """
        try:
            # Use same endpoint as V1: PostedPurchaseReceiptLines with filters
            url = f"{self.base_url}/PostedPurchaseReceiptLines?$filter=No eq '{item_number}' and Quantity ne 0 and Livraison_Repoussée eq false&$select=Order_Date,Posting_Date,Document_No,Quantity"
            data = await self._make_request("GET", url)

            if data and data.get("value"):
                logger.info(f"Retrieved {len(data['value'])} receipt records for item {item_number}")
                return data

            return None

        except Exception as e:
            logger.error(f"Error getting receipt dates for item {item_number}: {e}")
            return None

    async def update_item_lead_time(self, item_number: str, lead_time_weeks: int) -> bool:
        """
        Update item lead time in Business Central
        Used by: DelaisProcessor
        Migrated from BC.py Update_Delais_Item()
        """
        try:
            # Get current item data for etag
            item_data = await self.get_item_card(item_number)
            if not item_data:
                logger.error(f"Could not get item data for {item_number}")
                return False

            # Prepare update data
            update_data = {"Lead_Time_Calculation": f"{lead_time_weeks}W"}

            # Get etag for update
            etag = item_data.get("@odata.etag", "*")
            headers = {"if-match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            url = f"{self.base_url}/ItemCard('{item_number}')"
            result = await self._make_request("PATCH", url, json=update_data, headers=headers)

            if result:
                logger.info(f"Updated lead time for item {item_number} to {lead_time_weeks} weeks")
                return True
            else:
                logger.error(f"Failed to update lead time for item {item_number}")
                return False

        except Exception as e:
            logger.error(f"Error updating lead time for item {item_number}: {e}")
            return False

    async def get_po_status(self, document_no: str, item_no: str) -> dict[str, Any] | None:
        """
        Get PO status including Line_No and Etag for updates
        Used by: SuiviProcessor
        """
        import logfire

        try:
            with logfire.span(f"get_po_status PO={document_no} Item={item_no}"):
                url = f"{self.base_url}/PurchaseOrderLines?$filter=Document_No eq '{document_no}' and No eq '{item_no}'&$select=Document_No,Line_No,No,Promised_Receipt_Date"
                logfire.info(f"BC API GET: {url}")

                data = await self._make_request("GET", url)
                logfire.info(f"BC API Response: {data}")

                if data and data.get("value") and len(data["value"]) > 0:
                    line_data = data["value"][0]
                    result = {
                        "Document_No": line_data.get("Document_No"),
                        "Line_No": line_data.get("Line_No"),
                        "No": line_data.get("No"),
                        "Etag": line_data.get("@odata.etag"),
                        "Promised_Receipt_Date": line_data.get("Promised_Receipt_Date"),
                    }
                    logfire.info(f"Found PO line: {result}")
                    return result

                logfire.warning(f"No PO line found for {document_no}/{item_no} - empty result")
                return None

        except Exception as e:
            logfire.error(f"Error getting PO status for {document_no}/{item_no}: {e}")
            logger.error(f"Error getting PO status for {document_no}/{item_no}: {e}")
            return None

    async def get_po_status_by_line(self, document_no: str, line_no: str) -> dict[str, Any] | None:
        """
        Get PO status by line number including Etag for updates
        Used by: SuiviProcessor for retard processing with LineNo
        """
        try:
            # Line_No is an integer field in BC, don't quote it
            url = f"{self.base_url}/PurchaseOrderLines?$filter=Document_No eq '{document_no}' and Line_No eq {line_no}&$select=Document_No,Line_No,No"
            data = await self._make_request("GET", url)

            if data and data.get("value") and len(data["value"]) > 0:
                line_data = data["value"][0]
                return {
                    "Document_No": line_data.get("Document_No"),
                    "Line_No": line_data.get("Line_No"),
                    "No": line_data.get("No"),
                    "Etag": line_data.get("@odata.etag"),
                }

            return None

        except Exception as e:
            logger.error(f"Error getting PO status for {document_no}/Line {line_no}: {e}")
            return None

    async def set_po_promise_delivery(self, document_no: str, line_no: str, etag: str, delivery_date: str) -> bool:
        """
        Set promise delivery date for PO line
        Used by: SuiviProcessor
        Migrated from BC.py Set_PO_PromiseDelivery()
        """
        try:
            update_data = {"Promised_Receipt_Date": delivery_date.strip()}

            # Get fresh etag first (like V1 does)
            fresh_etag = await self.get_po_line_etag(document_no, line_no)
            if fresh_etag:
                etag = fresh_etag

            headers = {"if-match": str(etag), "Content-Type": "application/json", "company": "Gilbert-tech"}

            # Use V1 endpoint format with Document_Type='Order' as first parameter
            url = f"{self.base_url}/PurchaseOrderLines('Order','{document_no}',{line_no})"
            result = await self._make_request("PATCH", url, json=update_data, headers=headers)

            if result:
                logger.info(f"Updated promise delivery date for PO {document_no} line {line_no}")
                return True
            else:
                logger.error(f"Failed to update promise delivery date for PO {document_no} line {line_no}")
                return False

        except Exception as e:
            logger.error(f"Error updating promise delivery date for PO {document_no} line {line_no}: {e}")
            return False

    async def get_nombres_suivi_po_line(self, document_no: str, line_no: str) -> tuple[int, str | None]:
        """
        Get Nombre_de_Suivi count and fresh Etag for PO line
        Based on V1 Get_Nombres_Suivi_PO_Line function
        """
        try:
            # Handle -1 line numbers as in V1
            if str(line_no) == "-1":
                line_no = "10000"

            url = f"{self.base_url}/PurchaseOrderLines?$filter=Document_No eq '{document_no}' and Line_No eq {line_no}&$select=Nombre_de_Suivi"
            data = await self._make_request("GET", url)

            if data and data.get("value"):
                value_count = len(data.get("value", []))
                if value_count > 0:
                    nbr_suivi = data["value"][0].get("Nombre_de_Suivi", 0)
                    etag = data["value"][0].get("@odata.etag")
                    logger.info(f"Retrieved Nombre_de_Suivi: {nbr_suivi} for PO {document_no} line {line_no}")
                    return nbr_suivi, etag
                else:
                    logger.warning(f"No PO line found for {document_no} line {line_no}")
                    return 0, None
            else:
                logger.error(f"Failed to get Nombre de Suivi for PO {document_no} line {line_no}")
                return 0, None

        except Exception as e:
            logger.error(f"Error getting Nombre de Suivi for PO {document_no} line {line_no}: {e}")
            return 0, None

    async def update_suivi_status_po_line(self, document_no: str, line_no: str, etag: str, status: str) -> bool:
        """
        Update suivi status for PO line with KPI tracking
        Based on V1 Update_Suivi_Status_PO_Line function
        """
        try:
            # Get fresh Etag and current Nombre_de_Suivi count
            nbr_suivi, fresh_etag = await self.get_nombres_suivi_po_line(document_no, line_no)

            if fresh_etag is None:
                logger.error(f"Could not get fresh Etag for PO {document_no} line {line_no}")
                return False

            # Increment the suivi counter for KPI tracking
            nbr_suivi = nbr_suivi + 1

            # Get current timestamp in ISO 8601 format (matching V1)
            import json
            from datetime import datetime

            now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

            # Use V1 field names and structure - EXACTLY as V1 does with json.dumps
            update_data = json.dumps(
                {"SuiviStatut": status, "Date_Dernier_Suivi": now, "Nombre_de_Suivi": str(nbr_suivi)}
            )

            headers = {"if-match": fresh_etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            # Use V1 URL format with 'Order' parameter
            line_no_int = int(line_no)
            url = f"{self.base_url}/PurchaseOrderLines('Order','{document_no}',{line_no_int})"
            result = await self._make_request("PATCH", url, data=update_data, headers=headers)

            if result:
                logger.info(
                    f"Updated suivi status for PO {document_no} line {line_no} to '{status}' (count: {nbr_suivi})"
                )
                return True
            else:
                logger.error(f"Failed to update suivi status for PO {document_no} line {line_no}")
                return False

        except Exception as e:
            logger.error(f"Error updating suivi status for PO {document_no} line {line_no}: {e}")
            return False

    async def get_if_purchased(self, item_number: str) -> bool:
        """
        Check if an item is purchased (vs manufactured)
        Used by: DelaisProcessor
        Migrated from BC.py Get_if_achetee()

        Returns True (purchased) by default when unable to determine,
        as most items are purchased rather than manufactured
        """
        try:
            item_data = await self.get_item_card(item_number)
            if item_data:
                replenishment_system = item_data.get("Replenishment_System", "")
                # Check if explicitly marked as Purchase
                if replenishment_system:
                    return replenishment_system.lower() == "purchase"
                # If no replenishment system specified, default to purchased
                logger.warning(f"No Replenishment_System for item {item_number}, defaulting to purchased")
                return True
            # If we can't get item data, default to purchased (safer assumption)
            logger.warning(f"Could not get item data for {item_number}, defaulting to purchased")
            return True
        except Exception as e:
            logger.error(f"Error checking if item {item_number} is purchased: {e}, defaulting to purchased")
            # Default to purchased when API fails - safer assumption
            return True

    async def get_item_data(self, item_number: str) -> dict[str, Any] | None:
        """
        Get item data including lead time information
        Used by: DelaisProcessor
        Migrated from BC.py Get_Items()
        Updated to use correct V1 endpoint
        """
        try:
            url = f"{self.base_url}/Items?$filter=No eq '{item_number}'&$select=No,Lead_Time_Calculation"
            return await self._make_request("GET", url)
        except Exception as e:
            logger.error(f"Error getting item data for {item_number}: {e}")
            return None

    async def update_lead_time(self, item_number: str, lead_time_weeks: int) -> bool:
        """
        Update lead time for an item
        Used by: DelaisProcessor
        Migrated from BC.py Update_Delais_Item()
        """
        try:
            # Get current item data first for etag
            item_data = await self.get_item_card(item_number)
            if not item_data:
                return False

            # Update lead time calculation
            update_data = {"Lead_Time_Calculation": f"{lead_time_weeks}W"}

            # Get etag for update
            etag = item_data.get("@odata.etag", "*")
            headers = {"if-match": etag, "Content-Type": "application/json", "company": "Gilbert-tech"}

            url = f"{self.base_url}/ItemCard('{item_number}')"
            result = await self._make_request("PATCH", url, json=update_data, headers=headers)

            if result:
                logger.info(f"Updated lead time for item {item_number} to {lead_time_weeks}W")
                return True
            else:
                logger.error(f"Failed to update lead time for item {item_number}")
                return False

        except Exception as e:
            logger.error(f"Error updating lead time for item {item_number}: {e}")
            return False


# Sync wrapper functions for V1 compatibility (used by confirmation_commande.py)
def Get_ItemCard(item_number: str) -> dict[str, Any] | None:
    """Sync wrapper for get_item_card - used by confirmation_commande.py"""

    async def _get():
        async with BCClient() as client:
            return await client.get_item_card(item_number)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except RuntimeError:
        # If no event loop, create one
        return asyncio.run(_get())


def get_PO_Line_etag(po_number: str, line_no: str) -> str | None:
    """Sync wrapper for get_po_line_etag - used by confirmation_commande.py"""

    async def _get():
        async with BCClient() as client:
            return await client.get_po_line_etag(po_number, line_no)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except RuntimeError:
        return asyncio.run(_get())


def Update_PO_OrderConfirmation(
    po_number: str, line_no: str, etag: str, quantity: float, unit_cost: float, delivery_date: str
) -> bool:
    """Sync wrapper for update_po_order_confirmation - used by confirmation_commande.py"""

    async def _update():
        async with BCClient() as client:
            return await client.update_po_order_confirmation(
                po_number, line_no, etag, quantity, unit_cost, delivery_date
            )

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_update())
    except RuntimeError:
        return asyncio.run(_update())


def funct_Get_PurchaseOrderLine(po_number: str) -> list[dict[str, Any]] | None:
    """Sync wrapper for get_po_line - used by confirmation_commande.py"""

    async def _get():
        async with BCClient() as client:
            result = await client.get_po_line(po_number)
            return result.get("value", []) if result else []

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except RuntimeError:
        return asyncio.run(_get())


def get_Vendor_From_PO_No(po_number: str) -> str | None:
    """Sync wrapper for get_vendor_from_po_no - used by EnvoiPlanProcessor"""

    async def _get():
        async with BCClient() as client:
            return await client.get_vendor_from_po_no(po_number)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except RuntimeError:
        return asyncio.run(_get())


def Get_PO_Line(po_number: str) -> dict[str, Any] | None:
    """Sync wrapper for get_po_line - used by EnvoiPlanProcessor"""

    async def _get():
        async with BCClient() as client:
            return await client.get_po_line(po_number)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except RuntimeError:
        return asyncio.run(_get())


def get_revision(part_number: str) -> str | None:
    """Sync wrapper for get_revision - used by EnvoiPlanProcessor"""

    async def _get():
        async with BCClient() as client:
            return await client.get_revision(part_number)

    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_get())
    except RuntimeError:
        return asyncio.run(_get())
