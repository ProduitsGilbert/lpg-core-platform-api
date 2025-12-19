"""
ERP client adapter for Business Central integration.

This module provides direct integration with Business Central OData API.
No mock data - only real API calls with proper error handling.
"""

from datetime import date, datetime, UTC
from decimal import Decimal
from typing import Dict, Any, List, Optional
import asyncio
import httpx
import logfire
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
import logging

from app.settings import settings
from app.errors import ERPError, ERPUnavailable, ERPNotFound, ERPConflict
from app.ports import ERPClientProtocol

logger = logging.getLogger(__name__)


class ERPClient(ERPClientProtocol):
    """
    Business Central API client.
    
    Direct integration with Business Central OData API.
    No mock data, only real API calls with proper error handling.
    """
    
    def __init__(self):
        """
        Initialize ERP client for Business Central API.
        """
        self._http_client: Optional[httpx.AsyncClient] = None
        self._auth_header = None
        
        # Prepare auth header for Business Central
        import base64
        auth_string = f"{settings.bc_api_username}:{settings.bc_api_password}"
        auth_bytes = auth_string.encode('utf-8')
        auth_b64 = base64.b64encode(auth_bytes).decode('utf-8')
        self._auth_header = f"Basic {auth_b64}"

        raw_base_url = (settings.erp_base_url or "").strip()
        if raw_base_url and not raw_base_url.endswith("/"):
            raw_base_url = f"{raw_base_url}/"
        self._base_url = raw_base_url

        base_url_lower = self._base_url.lower()
        if "/odatav4" in base_url_lower:
            odata_index = base_url_lower.find("/odatav4")
            self._custom_odata_base = self._base_url[: odata_index + len("/ODataV4")].rstrip("/")
        else:
            self._custom_odata_base = self._base_url.rstrip("/")
    
    @property
    def http_client(self):
        """Lazy initialization of HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url or "",
                timeout=float(getattr(settings, "request_timeout", 60)),
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "Authorization": self._auth_header,
                    "Company": "Gilbert-Tech"
                },
                verify=False  # For self-signed certs
        )
        return self._http_client
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=20),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def _fetch_odata_collection(
        self,
        resource_path: str,
        *,
        fail_on_404: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve an OData collection and return the raw values list.
        """
        try:
            all_values: List[Dict[str, Any]] = []
            next_url: Optional[str] = resource_path

            # Follow @odata.nextLink to ensure completeness (critical for finance accuracy).
            while next_url:
                response = await self.http_client.get(next_url)
                response.raise_for_status()
                payload = response.json()
                values = payload.get("value", [])
                if not isinstance(values, list):
                    logger.warning(
                        "Unexpected payload structure from Business Central",
                        extra={"resource_path": resource_path, "payload_type": type(payload)},
                    )
                    break
                all_values.extend(values)

                next_url = (
                    payload.get("@odata.nextLink")
                    or payload.get("odata.nextLink")
                    or payload.get("@odata.nextlink")
                )
            return all_values
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else None
            body_text = ""
            try:
                body_text = (exc.response.text or "")[:800] if exc.response is not None else ""
            except Exception:
                body_text = ""
            logger.error(
                "Business Central HTTP error",
                extra={"resource_path": resource_path, "status_code": status_code},
            )
            if status_code == 404:
                if fail_on_404:
                    raise ERPError(
                        f"Business Central returned 404 for required resource: {resource_path}"
                        + (f" | body: {body_text}" if body_text else ""),
                        context={"resource_path": resource_path, "status_code": 404},
                    )
                return []
            # Treat transient 5xx as unavailable so we retry.
            if status_code in (500, 502, 503, 504):
                raise ERPUnavailable(
                    f"Business Central transient error {status_code} for {resource_path}"
                    + (f" | body: {body_text}" if body_text else "")
                )
            # Business Central sometimes returns 400 with an Internal_ServerError payload for transient UI refreshes:
            # "Sorry, we just updated this page. Reopen it, and try again."
            if status_code == 400 and body_text:
                lowered = body_text.lower()
                if "sorry, we just updated this page" in lowered or "internal_servererror" in lowered:
                    raise ERPUnavailable(
                        f"Business Central transient error (400/Internal_ServerError) for {resource_path}"
                        + (f" | body: {body_text}" if body_text else "")
                    )
            if status_code == 503:
                raise ERPUnavailable()
            raise ERPError(
                f"Business Central request failed with status {status_code} for {resource_path}"
                + (f": {body_text}" if body_text else "")
            )
        except httpx.RequestError as exc:
            logger.error(
                "Business Central request error",
                extra={"resource_path": resource_path, "error": str(exc)},
            )
            raise ERPUnavailable("Business Central service unreachable") from exc
        except Exception as exc:
            logger.exception(
                "Unexpected error retrieving Business Central collection",
                extra={"resource_path": resource_path},
            )
            raise ERPError("Unexpected error querying Business Central") from exc

    async def _reset_http_client(self) -> None:
        """Close and reset the HTTP client to force a fresh connection."""
        if self._http_client is not None:
            try:
                await self._http_client.aclose()
            except Exception as exc:
                logfire.warning("Error closing ERP HTTP client", error=str(exc))
            finally:
                self._http_client = None

    async def aclose(self) -> None:
        """Explicitly close the underlying HTTP client."""
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None
    
    async def get_sales_prices_for_item(self, item_no: str) -> List[Dict[str, Any]]:
        """
        Retrieve sales price entries for a given item.
        """
        sanitized_item = item_no.replace("'", "''")
        resource = f"SalesPrices?$filter=Item_No eq '{sanitized_item}'"
        return await self._fetch_odata_collection(resource)

    async def get_currency_exchange_rates(self, currency_code: str, top: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve currency exchange rates ordered by most recent starting date.
        """
        sanitized_code = currency_code.replace("'", "''")
        resource = (
            f"CurrencyExchangeRates?$filter=Currency_Code eq '{sanitized_code}'"
            f"&$orderby=Starting_Date desc"
            f"&$top={top}"
        )
        return await self._fetch_odata_collection(resource)

    async def get_bom_component_lines(self, production_bom_no: str) -> List[Dict[str, Any]]:
        """
        Retrieve BOM component lines for a given production BOM number.
        """
        if not production_bom_no:
            return []
        sanitized = production_bom_no.replace("'", "''")
        resource = f"BOMComponentLines?$filter=Production_BOM_No eq '{sanitized}'"
        return await self._fetch_odata_collection(resource)
    
    async def get_bin_contents(
        self,
        item_no: str,
        *,
        location_code: Optional[str] = None,
        fixed_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve BinContents rows for an item with optional filtering.
        """
        if not item_no:
            return []

        sanitized_item = item_no.replace("'", "''")
        filters = [f"Item_No eq '{sanitized_item}'"]

        if location_code:
            sanitized_location = location_code.replace("'", "''")
            filters.append(f"Location_Code eq '{sanitized_location}'")

        filter_query = " and ".join(filters)
        resource = f"BinContents?$filter={filter_query}"
        entries = await self._fetch_odata_collection(resource)

        if not fixed_only:
            return entries

        filtered: List[Dict[str, Any]] = []
        for entry in entries:
            if bool(entry.get("Fixed")):
                filtered.append(entry)
        return filtered

    async def get_fixed_bin_quantity(self, item_no: str, location_code: str = "GIL") -> Decimal:
        """
        Sum the quantity for an item within fixed bins at the specified location.
        """
        entries = await self.get_bin_contents(item_no, location_code=location_code, fixed_only=True)
        total = Decimal("0")

        for entry in entries:
            quantity_fields = ("Quantity_Base", "Quantity")
            value: Optional[Decimal] = None
            for field in quantity_fields:
                raw_value = entry.get(field)
                if raw_value in (None, "", []):
                    continue
                try:
                    value = Decimal(str(raw_value))
                except (ArithmeticError, ValueError, TypeError):
                    value = None
                if value is not None:
                    break

            if value is None:
                logger.warning(
                    "Skipping BinContents row with invalid quantity",
                    extra={"item_no": item_no, "location_code": location_code, "row": entry},
                )
                continue

            total += value
        return total
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def get_poline(self, po_id: str, line_no: int) -> Dict[str, Any]:
        """
        Retrieve PO line details from Business Central.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
        
        Returns:
            Dictionary with PO line details
        """
        with logfire.span("ERP get_poline", po_id=po_id, line_no=line_no):
            try:
                # Use the Gilbert_PurchaseOrderLines endpoint with filters for custom fields
                response = await self.http_client.get(
                    f"Gilbert_PurchaseOrderLines?$filter=Document_No eq '{po_id}' and Line_No eq {line_no}"
                )
                response.raise_for_status()
                
                data = response.json()
                lines = data.get("value", [])
                
                if not lines:
                    raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
                
                return lines[0]
                
            except httpx.HTTPStatusError as e:
                logfire.error(f"HTTP error getting PO line {po_id}/{line_no}: {e.response.status_code}")
                if e.response.status_code == 404:
                    raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
                elif e.response.status_code == 503:
                    raise ERPUnavailable()
                else:
                    raise ERPError(f"API error: {e.response.status_code} - {e.response.text}")
            except httpx.TimeoutException:
                raise ERPUnavailable("ERP API timeout")
            except Exception as e:
                logfire.error(f"Error getting PO line {po_id}/{line_no}: {e}")
                raise ERPError(f"Failed to get PO line: {str(e)}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def update_poline_date(
        self,
        po_id: str,
        line_no: int,
        new_date: date
    ) -> Dict[str, Any]:
        """
        Update PO line promise date in Business Central.
        
        Args:
            po_id: Purchase Order ID
            line_no: Line number
            new_date: New promise date
        
        Returns:
            Updated PO line details
        """
        with logfire.span(
            "ERP update_poline_date",
            po_id=po_id,
            line_no=line_no,
            new_date=str(new_date)
        ):
            try:
                # First get the line to find its system ID
                line = await self.get_poline(po_id, line_no)
                system_id = line.get("SystemId")
                
                if not system_id:
                    raise ERPError(f"No SystemId found for PO line {po_id}/{line_no}")
                
                # Update using the system ID on Gilbert_PurchaseOrderLines
                response = await self.http_client.patch(
                    f"Gilbert_PurchaseOrderLines('{system_id}')",
                    json={"Promised_Receipt_Date": new_date.isoformat()}  # Use Promised_Receipt_Date for Gilbert
                )
                response.raise_for_status()
                
                # Return the updated line
                return await self.get_poline(po_id, line_no)
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
                elif e.response.status_code == 409:
                    raise ERPConflict(f"Cannot update PO line: {e.response.text}")
                else:
                    raise ERPError(f"API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logfire.error(f"Error updating PO line date {po_id}/{line_no}: {e}")
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def update_poline_price(
        self,
        po_id: str,
        line_no: int,
        new_price: Decimal
    ) -> Dict[str, Any]:
        """
        Update PO line unit price in Business Central.
        
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
            try:
                # First get the line to find its system ID
                line = await self.get_poline(po_id, line_no)
                system_id = line.get("SystemId")
                
                if not system_id:
                    raise ERPError(f"No SystemId found for PO line {po_id}/{line_no}")
                
                # Update using the system ID on Gilbert_PurchaseOrderLines
                response = await self.http_client.patch(
                    f"Gilbert_PurchaseOrderLines('{system_id}')",
                    json={"Direct_Unit_Cost": float(new_price)}
                )
                response.raise_for_status()
                
                # Return the updated line
                return await self.get_poline(po_id, line_no)
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
                elif e.response.status_code == 409:
                    raise ERPConflict(f"Cannot update PO line: {e.response.text}")
                else:
                    raise ERPError(f"API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logfire.error(f"Error updating PO line price {po_id}/{line_no}: {e}")
                raise
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=60),
        retry=retry_if_exception_type((ERPUnavailable, httpx.TimeoutException)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def update_poline_quantity(
        self,
        po_id: str,
        line_no: int,
        new_quantity: Decimal
    ) -> Dict[str, Any]:
        """
        Update PO line quantity in Business Central.
        
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
            try:
                # First get the line to find its system ID
                line = await self.get_poline(po_id, line_no)
                system_id = line.get("SystemId")
                
                if not system_id:
                    raise ERPError(f"No SystemId found for PO line {po_id}/{line_no}")
                
                # Update using the system ID on Gilbert_PurchaseOrderLines
                response = await self.http_client.patch(
                    f"Gilbert_PurchaseOrderLines('{system_id}')",
                    json={"Quantity": float(new_quantity)}
                )
                response.raise_for_status()
                
                # Return the updated line
                return await self.get_poline(po_id, line_no)
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    raise ERPNotFound("Purchase Order Line", f"{po_id}/{line_no}")
                elif e.response.status_code == 409:
                    raise ERPConflict(f"Cannot update PO line: {e.response.text}")
                else:
                    raise ERPError(f"API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logfire.error(f"Error updating PO line quantity {po_id}/{line_no}: {e}")
                raise
    
    async def get_purchase_order(self, po_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve purchase order from Business Central.

        Args:
            po_id: Purchase Order ID

        Returns:
            Dictionary with PO header data or None if not found
        """
        with logfire.span("ERP get_purchase_order", po_id=po_id):
            try:
                # Call Business Central PurchaseOrderHeaders endpoint
                response = await self.http_client.get(
                    f"PurchaseOrderHeaders?$filter=No eq '{po_id}'"
                )
                response.raise_for_status()

                data = response.json()
                orders = data.get("value", [])

                if orders:
                    order = orders[0]
                    logfire.info(f"Retrieved PO {po_id} from Business Central API")
                    return order
                else:
                    logfire.info(f"PO {po_id} not found in Business Central")
                    return None

            except httpx.HTTPStatusError as e:
                logfire.error(f"HTTP error getting PO {po_id}: {e.response.status_code}")
                logfire.error(f"Response: {e.response.text}")
                raise ERPError(f"Business Central API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logfire.error(f"Error getting PO {po_id}: {e}")
                raise ERPError(f"Failed to get PO: {str(e)}")

    async def reopen_purchase_order(self, header_no: str) -> Dict[str, Any]:
        """Invoke the Business Central action to reopen a released purchase order."""
        if not header_no:
            raise ERPError(
                "Purchase order number is required to reopen an order",
                context={"po_id": header_no},
            )

        with logfire.span("ERP reopen_purchase_order", header_no=header_no):
            try:
                payload = {"headerNo": header_no}
                result = await self._post_purchase_operation("createPO_reopen", payload)
                logfire.info("Purchase order reopened", header_no=header_no)
                return result
            except ERPError:
                raise
            except Exception as exc:
                logfire.error(
                    f"Unexpected error reopening purchase order {header_no}: {exc}"
                )
                raise ERPError(
                    f"Failed to reopen purchase order {header_no}",
                    context={"po_id": header_no},
                ) from exc

    async def get_purchase_order_lines(self, po_id: str) -> List[Dict[str, Any]]:
        """
        Get purchase order lines from Business Central.

        Args:
            po_id: Purchase Order ID
        
        Returns:
            List of PO lines
        """
        with logfire.span("ERP get_purchase_order_lines", po_id=po_id):
            try:
                # Call Business Central PurchaseOrderLines endpoint
                response = await self.http_client.get(
                    f"Gilbert_PurchaseOrderLines?$filter=Document_No eq '{po_id}'"
                )
                response.raise_for_status()
                
                data = response.json()
                lines = data.get("value", [])
                
                logfire.info(f"Retrieved {len(lines)} lines for PO {po_id} from Business Central API")
                return lines
                    
            except httpx.HTTPStatusError as e:
                logfire.error(f"HTTP error getting PO lines for {po_id}: {e.response.status_code}")
                logfire.error(f"Response: {e.response.text}")
                raise ERPError(f"Business Central API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                logfire.error(f"Error getting PO lines for {po_id}: {e}")
                raise ERPError(f"Failed to get PO lines: {str(e)}")

    async def get_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve vendor master data from Business Central."""

        with logfire.span("ERP get_vendor", vendor_id=vendor_id):
            try:
                response = await self.http_client.get(
                    f"Vendor?$filter=No eq '{vendor_id}'"
                )
                response.raise_for_status()

                data = response.json()
                vendors = data.get("value", [])

                if vendors:
                    vendor = vendors[0]
                    logfire.info("Retrieved vendor info", vendor_id=vendor_id)
                    return vendor

                logfire.warning("Vendor not found", vendor_id=vendor_id)
                return None

            except httpx.HTTPStatusError as exc:
                logfire.error(
                    "HTTP error getting vendor",
                    vendor_id=vendor_id,
                    status_code=exc.response.status_code,
                )
                raise ERPError(
                    f"Business Central API error: {exc.response.status_code} - {exc.response.text}"
                )
            except Exception as exc:  # pragma: no cover - network failure path
                logfire.error("Error getting vendor", vendor_id=vendor_id, error=str(exc))
                raise ERPError(f"Failed to get vendor: {str(exc)}")

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Get item from Business Central.

        Args:
            item_id: Item number/ID

        Returns:
            Item data or None if not found
        """
        with logfire.span("ERP get_item", item_id=item_id):
            for attempt in range(2):
                try:
                    # Call Business Central Items endpoint
                    response = await self.http_client.get(
                        f"Items?$filter=No eq '{item_id}'"
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    items = data.get("value", [])
                    
                    if items:
                        item = items[0]
                        logfire.info(f"Retrieved item {item_id} from Business Central API")
                        return item
                    else:
                        logfire.info(f"Item {item_id} not found in Business Central")
                        return None
                    
                except httpx.RemoteProtocolError as e:
                    logfire.warning(
                        "Remote protocol error when retrieving item",
                        item_id=item_id,
                        attempt=attempt + 1,
                        error=str(e)
                    )
                    await self._reset_http_client()
                    if attempt == 0:
                        continue
                    raise ERPError(
                        "Failed to get item due to remote protocol error",
                        context={"item_id": item_id}
                    )
                except httpx.HTTPStatusError as e:
                    logfire.error(f"HTTP error getting item {item_id}: {e.response.status_code}")
                    logfire.error(f"Response: {e.response.text}")
                    raise ERPError(f"Business Central API error: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    logfire.error(f"Error getting item {item_id}: {e}")
                    raise ERPError(f"Failed to get item: {str(e)}")

    async def update_item_record(
        self,
        system_id: str,
        updates: Dict[str, Any],
        etag: str
    ) -> None:
        """Patch an item record in Business Central using its system ID."""
        with logfire.span(
            "ERP update_item",
            system_id=system_id,
            fields=list(updates.keys())
        ):
            try:
                headers = {"If-Match": etag}
                response = await self.http_client.patch(
                    f"Items('{system_id}')",
                    json=updates,
                    headers=headers
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else "unknown"
                logfire.error(
                    "HTTP error updating item",
                    system_id=system_id,
                    status_code=status_code,
                    body=e.response.text if e.response else None
                )
                if e.response is not None:
                    if e.response.status_code == 404:
                        raise ERPNotFound("Item", system_id)
                    if e.response.status_code == 409:
                        raise ERPConflict("Conflict updating item in ERP")
                raise ERPError(
                    f"Business Central API error: {status_code}"
                )
            except Exception as e:
                logfire.error(f"Error updating item {system_id}: {e}")
                raise ERPError(f"Failed to update item: {str(e)}")

    async def copy_item_from_template(self, template_item: str, destination_item: str) -> None:
        """Copy an item from a template item number."""
        with logfire.span(
            "ERP copy_item_from_template",
            template_item=template_item,
            destination_item=destination_item
        ):
            try:
                if not self._custom_odata_base:
                    raise ERPError(
                        "Business Central base URL is not configured for template copy operations",
                        context={"template_item": template_item}
                    )

                endpoint_url = f"{self._custom_odata_base}/copyItems_copyItemFrom"

                response = await self.http_client.post(
                    endpoint_url,
                    json={
                        "sourceItem": template_item,
                        "destinationItem": destination_item
                    },
                    headers={"Connection": "close"}
                )
                try:
                    response.raise_for_status()
                    # Drain the body (even on 204 chunked responses) before closing to avoid connection reuse issues
                    await response.aread()
                finally:
                    await response.aclose()
            except httpx.HTTPStatusError as e:
                status_code = e.response.status_code if e.response else "unknown"
                logfire.error(
                    "HTTP error copying item",
                    template_item=template_item,
                    destination_item=destination_item,
                    status_code=status_code,
                    endpoint=endpoint_url,
                    body=e.response.text if e.response else None
                )
                if e.response is not None:
                    if e.response.status_code == 404:
                        body_text = e.response.text or ""
                        if "No HTTP resource was found" in body_text and "copyItems_copyItemFrom" in body_text:
                            raise ERPError(
                                "Business Central copyItems_copyItemFrom endpoint is unavailable",
                                context={"endpoint": endpoint_url}
                            )
                        raise ERPNotFound("Item template", template_item)
                    if e.response.status_code == 409:
                        raise ERPConflict(
                            f"Item {destination_item} already exists in ERP"
                        )
                raise ERPError(
                    f"Business Central API error: {status_code}"
                )
            except Exception as e:
                logfire.error(f"Error copying item {destination_item} from template {template_item}: {e}")
                raise ERPError(f"Failed to copy item from template: {str(e)}")
    
    async def create_receipt(
        self,
        po_id: str,
        lines: List[Dict[str, Any]],
        receipt_date: date,
        vendor_shipment_no: str,
        job_check_delay_seconds: int = 5,
        notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a goods receipt in Business Central.
        
        Args:
            po_id: Purchase Order ID
            lines: Receipt lines with quantities
            receipt_date: Receipt posting date
            vendor_shipment_no: Vendor shipment reference number
            job_check_delay_seconds: Time to wait before checking job queue status
        
        Returns:
            Created receipt details
        """
        with logfire.span(
            "ERP create_receipt",
            po_id=po_id,
            line_count=len(lines)
        ):
            try:
                if not vendor_shipment_no:
                    raise ERPError(
                        "Vendor shipment number is required to create a receipt",
                        context={"po_id": po_id},
                    )

                root_payload = {"noPo": po_id}
                await self._post_purchase_operation("postPurchaseLine_setToZero", root_payload)
                await self._post_purchase_operation(
                    "postPurchaseLine_updateVendShipNo",
                    {"noPo": po_id, "shipmentNo": vendor_shipment_no},
                )

                for line in lines:
                    payload = {
                        "noPo": po_id,
                        "noLigne": line["line_no"],
                        "receivedQuantity": float(line["quantity"]),
                    }
                    if line.get("location_code"):
                        payload["locationCode"] = line["location_code"]
                    await self._post_purchase_operation(
                        "postPurchaseLine_updateToReceiveLine",
                        payload,
                    )

                job_queue_response = await self._post_purchase_operation(
                    "postPurchaseLine_receiveMaterial",
                    {"noPo": po_id, "receiptDate": receipt_date.isoformat()},
                )

                job_queue_entry_id = (
                    job_queue_response.get("jobQueueEntryID")
                    or job_queue_response.get("JobQueueEntryID")
                    or job_queue_response.get("job_queue_entry_id")
                )

                job_status = {}
                if job_queue_entry_id and job_check_delay_seconds:
                    await asyncio.sleep(job_check_delay_seconds)
                    job_status = await self._post_purchase_operation(
                        "postPurchaseLine_checkForError",
                        {"jobQueueEntryID": job_queue_entry_id},
                    )

                if job_status.get("hasError") or job_status.get("error"):
                    raise ERPError(
                        "Business Central reported an error while posting the receipt",
                        context={
                            "po_id": po_id,
                            "job_queue_entry_id": job_queue_entry_id,
                            "job_status": job_status,
                        },
                    )

                purchase_order = await self.get_purchase_order(po_id)
                vendor_id = purchase_order.get("Buy_from_Vendor_No", "") if purchase_order else ""
                vendor_name = purchase_order.get("Buy_from_Vendor_Name", "") if purchase_order else ""

                receipt_identifier = (
                    job_status.get("documentNo")
                    or job_status.get("DocumentNo")
                    or job_queue_response.get("documentNo")
                    or f"RCPT-{po_id}-{job_queue_entry_id or int(datetime.now(UTC).timestamp())}"
                )

                return {
                    "receipt_id": receipt_identifier,
                    "po_id": po_id,
                    "vendor_id": vendor_id,
                    "vendor_name": vendor_name,
                    "receipt_date": receipt_date.isoformat(),
                    "posting_date": receipt_date.isoformat(),
                    "status": "posted",
                    "notes": notes or job_queue_entry_id,
                    "created_by": settings.bc_api_username,
                    "created_at": datetime.now(UTC).isoformat(),
                    "job_queue_entry_id": job_queue_entry_id,
                    "job_status": job_status,
                }

            except Exception as e:
                logfire.error(f"Error creating receipt for PO {po_id}: {e}")
                raise

    async def _post_purchase_operation(self, endpoint: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self._custom_odata_base:
            raise ERPError(
                "ERP base URL is not configured for purchase receipt operations",
                context={"endpoint": endpoint},
            )
        url = f"{self._custom_odata_base}/{endpoint.lstrip('/')}"
        try:
            response = await self.http_client.post(url, json=payload)
            try:
                response.raise_for_status()
                if not response.content:
                    return {}
                try:
                    return response.json()
                except ValueError:
                    return {}
            finally:
                await response.aclose()
        except httpx.HTTPStatusError as exc:
            logfire.error(
                "Business Central receipt operation failed",
                endpoint=endpoint,
                status_code=exc.response.status_code,
                response_text=exc.response.text[:500],
            )
            raise ERPError(
                f"Business Central receipt operation failed: {exc.response.status_code}",
                context={"endpoint": endpoint, "po_id": payload.get("noPo")},
            )
    
    async def create_return(
        self,
        receipt_id: str,
        lines: List[Dict[str, Any]],
        return_date: date,
        reason: str
    ) -> str:
        """
        Create a purchase return order in Business Central.
        
        Args:
            receipt_id: Posted receipt identifier used as source document
            lines: Enriched line payloads with item and quantity information
            return_date: Requested return posting date
            reason: Free-form reason for the return
        
        Returns:
            Newly created return order number
        """
        with logfire.span(
            "ERP create_return",
            receipt_id=receipt_id,
            line_count=len(lines)
        ):
            try:
                receipt_header = await self._get_posted_purchase_receipt(receipt_id)
                if not receipt_header:
                    raise ERPNotFound("Posted Purchase Receipt", receipt_id)

                vendor_no = (
                    receipt_header.get("Buy_from_Vendor_No")
                    or receipt_header.get("Vendor_No")
                )
                if not vendor_no:
                    raise ERPError(
                        "Receipt is missing vendor information",
                        context={"receipt_id": receipt_id},
                    )

                header_payload: Dict[str, Any] = {
                    "Buy_from_Vendor_No": vendor_no,
                    "Vendor_Order_No": receipt_header.get("Order_No")
                    or receipt_header.get("Purch_Order_No"),
                    "Location_Code": receipt_header.get("Location_Code"),
                    "Document_Date": return_date.isoformat(),
                    "Posting_Date": return_date.isoformat(),
                    "External_Document_No": receipt_id,
                }

                response = await self.http_client.post(
                    "PurchaseReturnOrderHeaders",
                    json={k: v for k, v in header_payload.items() if v},
                )
                try:
                    response.raise_for_status()
                    created_header = response.json()
                finally:
                    await response.aclose()
                return_no = created_header.get("No") or created_header.get("no")
                if not return_no:
                    raise ERPError(
                        "Business Central did not return a return order number",
                        context={"receipt_id": receipt_id},
                    )

                for index, line in enumerate(lines, start=1):
                    payload = {
                        "Document_No": return_no,
                        "Line_No": line.get("line_no") or index * 10000,
                        "Type": line.get("type") or "Item",
                        "No": line.get("item_no"),
                        "Description": line.get("description"),
                        "Quantity": float(line.get("quantity", 0)),
                        "Unit_of_Measure_Code": line.get("unit_of_measure"),
                        "Location_Code": line.get("location_code"),
                        "Return_Reason_Code": line.get("return_reason_code"),
                        "Variant_Code": line.get("variant_code"),
                    }

                    if payload["Quantity"] <= 0:
                        raise ERPError(
                            "Return line quantity must be greater than zero",
                            context={"line": payload},
                        )

                    response = await self.http_client.post(
                        "PurchaseReturnOrderLines",
                        json={k: v for k, v in payload.items() if v not in (None, "")},
                    )
                    try:
                        response.raise_for_status()
                    finally:
                        await response.aclose()

                # Optionally update reason at header level if supported
                if reason:
                    try:
                        response = await self.http_client.patch(
                            f"PurchaseReturnOrderHeaders('{return_no}')",
                            json={"Comments": reason[:250]},
                        )
                        try:
                            response.raise_for_status()
                        finally:
                            await response.aclose()
                    except httpx.HTTPStatusError:
                        # Non-critical; log but do not fail creation
                        logfire.warning(
                            "Failed to update return order comments",
                            return_no=return_no,
                        )

                return return_no

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                logfire.error(
                    "Business Central return creation failed",
                    receipt_id=receipt_id,
                    status_code=status_code,
                    response_text=exc.response.text[:500] if exc.response else None,
                )
                if status_code == 404:
                    raise ERPNotFound(
                        "Business Central endpoint",
                        "PurchaseReturnOrderHeaders",
                    )
                raise ERPError(
                    "Purchase return creation failed",
                    context={
                        "receipt_id": receipt_id,
                        "status_code": status_code,
                    },
                )
            except Exception as e:
                logfire.error(f"Error creating return for receipt {receipt_id}: {e}")
                raise

    async def get_purchase_return_order(self, return_no: str) -> Optional[Dict[str, Any]]:
        """Retrieve a purchase return order header from Business Central."""
        with logfire.span("ERP get_purchase_return_order", return_no=return_no):
            try:
                response = await self.http_client.get(
                    f"PurchaseReturnOrderHeaders?$filter=No eq '{return_no}'"
                )
                try:
                    response.raise_for_status()
                    data = response.json().get("value", [])
                    return data[0] if data else None
                finally:
                    await response.aclose()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                if status_code == 404:
                    return None
                logfire.error(
                    "Failed to fetch purchase return order",
                    return_no=return_no,
                    status_code=status_code,
                    response_text=exc.response.text[:500] if exc.response else None,
                )
                raise ERPError(
                    "Failed to retrieve purchase return order",
                    context={"return_no": return_no, "status_code": status_code},
                )
            except Exception as exc:
                logfire.error(
                    "Unexpected error fetching purchase return order",
                    return_no=return_no,
                    error=str(exc),
                )
                raise ERPError(
                    "Failed to retrieve purchase return order",
                    context={"return_no": return_no},
                )

    async def get_purchase_return_order_lines(self, return_no: str) -> List[Dict[str, Any]]:
        """Retrieve lines for a purchase return order."""
        with logfire.span("ERP get_purchase_return_order_lines", return_no=return_no):
            try:
                response = await self.http_client.get(
                    f"PurchaseReturnOrderLines?$filter=Document_No eq '{return_no}'"
                )
                try:
                    response.raise_for_status()
                    return response.json().get("value", [])
                finally:
                    await response.aclose()
            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                if status_code == 404:
                    return []
                logfire.error(
                    "Failed to fetch purchase return order lines",
                    return_no=return_no,
                    status_code=status_code,
                    response_text=exc.response.text[:500] if exc.response else None,
                )
                raise ERPError(
                    "Failed to retrieve purchase return order lines",
                    context={"return_no": return_no, "status_code": status_code},
                )
            except Exception as exc:
                logfire.error(
                    "Unexpected error fetching return order lines",
                    return_no=return_no,
                    error=str(exc),
                )
                raise ERPError(
                    "Failed to retrieve purchase return order lines",
                    context={"return_no": return_no},
                )

    async def _get_posted_purchase_receipt(self, receipt_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a posted purchase receipt header."""
        try:
            response = await self.http_client.get(
                f"PostedPurchaseReceiptHeaders?$filter=No eq '{receipt_id}'"
            )
            try:
                response.raise_for_status()
                data = response.json().get("value", [])
                return data[0] if data else None
            finally:
                await response.aclose()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else None
            if status_code == 404:
                return None
            logfire.error(
                "Failed to fetch posted receipt header",
                receipt_id=receipt_id,
                status_code=status_code,
                response_text=exc.response.text[:500] if exc.response else None,
            )
            raise ERPError(
                "Failed to retrieve posted receipt header",
                context={"receipt_id": receipt_id, "status_code": status_code},
            )

    async def get_posted_purchase_receipt_lines(self, receipt_id: str) -> List[Dict[str, Any]]:
        """Fetch posted receipt lines for a given receipt."""
        try:
            response = await self.http_client.get(
                f"PostedPurchaseReceiptLines?$filter=Document_No eq '{receipt_id}'"
            )
            try:
                response.raise_for_status()
                return response.json().get("value", [])
            finally:
                await response.aclose()
        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code if exc.response else None
            if status_code == 404:
                return []
            logfire.error(
                "Failed to fetch posted receipt lines",
                receipt_id=receipt_id,
                status_code=status_code,
                response_text=exc.response.text[:500] if exc.response else None,
            )
            raise ERPError(
                "Failed to retrieve posted receipt lines",
                context={"receipt_id": receipt_id, "status_code": status_code},
            )

    async def get_posted_sales_invoices(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve posted sales invoices with remaining amount > 0, optionally filtered by Due_Date."""
        filters = ["Remaining_Amount gt 0"]
        if start_date:
            filters.append(f"Due_Date ge {start_date.isoformat()}")
        if end_date:
            filters.append(f"Due_Date le {end_date.isoformat()}")
        resource = "PostedSalesInvoiceHeaders?$filter=" + " and ".join(filters)
        return await self._fetch_odata_collection(resource)

    async def get_job_planning_lines(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve job planning lines for billing.
        Filtering by Job Task No '6.FACTURATION' as specified.
        """
        filters = ["Job_Task_No eq '6.FACTURATION'"]
        # Planning_Date is the base date for projection in our service.
        if start_date:
            filters.append(f"Planning_Date ge {start_date.isoformat()}")
        if end_date:
            filters.append(f"Planning_Date le {end_date.isoformat()}")
        resource = "JobPlanningLines?$filter=" + " and ".join(filters)
        return await self._fetch_odata_collection(resource)

    async def get_open_purchase_invoices(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve open purchase invoices, optionally filtered by Due_Date (preferred) or Document_Date."""
        if not start_date and not end_date:
            return await self._fetch_odata_collection("PurchaseInvoices")
        filters: List[str] = []
        if start_date:
            # Prefer Due_Date since that's the payment schedule field in BC.
            filters.append(f"Due_Date ge {start_date.isoformat()}")
        if end_date:
            filters.append(f"Due_Date le {end_date.isoformat()}")
        resource = "PurchaseInvoices?$filter=" + " and ".join(filters)
        return await self._fetch_odata_collection(resource)

    async def get_posted_purchase_invoices(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve posted purchase invoices with remaining amount > 0, optionally filtered by Due_Date."""
        filters = ["Remaining_Amount gt 0"]
        if start_date:
            filters.append(f"Due_Date ge {start_date.isoformat()}")
        if end_date:
            filters.append(f"Due_Date le {end_date.isoformat()}")
        resource = "PostedPurchaseInvoiceHeaders?$filter=" + " and ".join(filters)
        return await self._fetch_odata_collection(resource)

    async def get_continia_invoices(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve Continia invoices.

        Important: Schema differs from standard BC entities (e.g. may not have Document_Date),
        so we avoid server-side date filtering here and instead filter client-side.

        Fail-closed requirement: if the endpoint is missing (404), raise an error.
        """
        _ = (start_date, end_date)  # filtered client-side in service
        # Force smaller pages to reduce load / timeouts; pagination will follow @odata.nextLink.
        return await self._fetch_odata_collection("Continia?$top=1000", fail_on_404=True)

    async def get_customer_payment_terms(self) -> List[Dict[str, Any]]:
        """Retrieve customer payment terms mappings."""
        return await self._fetch_odata_collection("Customers?$select=No,Payment_Terms_Code")

    async def get_vendor_payment_terms(self) -> List[Dict[str, Any]]:
        """Retrieve vendor payment terms mappings."""
        # Include Currency_Code so downstream cashflow can map payables to the correct bank account.
        return await self._fetch_odata_collection("Vendors?$select=No,Payment_Terms_Code,Currency_Code")

    async def get_payment_terms_definitions(self) -> List[Dict[str, Any]]:
        """Retrieve payment terms definitions (e.g. Due Date Calculation)."""
        return await self._fetch_odata_collection("PaymentTerms")

    async def get_job(self, job_no: str) -> Optional[Dict[str, Any]]:
        """Retrieve a single job header (used to resolve customer/payment terms for job planning lines)."""
        if not job_no:
            return None
        sanitized = job_no.replace("'", "''")
        rows = await self._fetch_odata_collection(f"Jobs?$filter=No eq '{sanitized}'")
        return rows[0] if rows else None

    async def get_open_po_lines(
        self, start_date: Optional[date] = None, end_date: Optional[date] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve open purchase order lines (to be received).
        Using Gilbert_PurchaseOrderLines as requested.
        Filtering for outstanding quantity > 0 to get only what is yet to be received/invoiced.
        """
        # Assuming Outstanding_Quantity is available or we filter by Quantity > Quantity_Received
        # Note: In BC OData, calculated fields like Outstanding_Quantity might not always be filterable 
        # depending on the page type. If this fails, we might need to fetch more and filter in python,
        # but let's try a standard filter first or just fetch recent ones.
        # For safety/performance, let's try to filter where Quantity > 0.
        # The user said "you'll get the BuyFromVendor in that endpoint".
        # Prefer Quantity_Invoiced to represent "not invoiced yet" remaining.
        filters = ["Quantity gt 0", "Quantity_Invoiced lt Quantity"]
        # Use Expected_Receipt_Date for date scoping (when present).
        if start_date:
            filters.append(f"Expected_Receipt_Date ge {start_date.isoformat()}")
        if end_date:
            filters.append(f"Expected_Receipt_Date le {end_date.isoformat()}")
        resource = "Gilbert_PurchaseOrderLines?$filter=" + " and ".join(filters)
        return await self._fetch_odata_collection(resource)
