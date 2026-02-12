import pytest

from app.domain.edi.service import EDIService
from app.errors import InvalidPurchaseOrderError


class _FakeERPClient:
    """Minimal async stub that mimics the ERP client for EDI generation tests."""

    async def get_purchase_order_for_edi(self, po_number: str):
        return {
            "No": po_number,
            "Document_Date": "2025-12-01",
            "Payment_Terms_Code": "NET30",
            "Buy_from_Vendor_No": "VENDOR01",
            "Amount": "62.50",
            "Amount_Including_VAT": "71.88",
            "Ship_to_Name": "Gilbert Tech",
            "Ship_to_Address": "1840 Boul Marcotte",
            "Ship_to_City": "Roberval",
            "Ship_to_State": "QC",
            "Ship_to_Post_Code": "G8H 2P2",
        }

    async def get_purchase_order(self, po_number: str):
        return None

    async def get_purchase_order_lines_for_edi(self, po_number: str):
        return [
            {
                "Line_No": 10000,
                "Quantity": "5",
                "Unit_of_Measure_Code": "EA",
                "Direct_Unit_Cost": "12.50",
                "Vendor_Item_No": "V-100",
                "No": "ITEM-001",
                "Description": "Widget",
            },
            {
                # Empty/comment style line that should be filtered out
                "Line_No": 20000,
                "Quantity": "0",
                "Unit_of_Measure_Code": "",
                "Direct_Unit_Cost": "",
                "Vendor_Item_No": "",
                "No": "",
                "Description": "",
            },
        ]

    async def get_purchase_order_lines(self, po_number: str):
        return []

    async def get_vendor(self, vendor_code: str):
        return {
            "No": vendor_code,
            "Name": "Vendor Inc",
            "Address": "123 Main St",
            "City": "Townsville",
            "County": "QC",
            "Post_Code": "A1B2C3",
        }


class _FakeERPClientNoLines(_FakeERPClient):
    async def get_purchase_order_lines_for_edi(self, po_number: str):
        return [
            {
                "Line_No": 10000,
                "Quantity": "0",
                "Unit_of_Measure_Code": "",
                "Direct_Unit_Cost": "",
                "Vendor_Item_No": "",
                "No": "",
                "Description": "",
            }
        ]


@pytest.mark.asyncio
async def test_generate_purchase_order_850_populates_from_business_central_stub():
    service = EDIService(erp_client=_FakeERPClient(), sender_id="SENDERID")
    document, file_name = await service.generate_purchase_order_850("PO999")

    assert "ID|850|SENDERID|VENDOR01|" in document
    assert "HEAD|||" in document
    assert "ITEM|1|5.0000|EA|12.5000|VN|V-100" in document
    assert file_name.startswith("PO_PO999_")


@pytest.mark.asyncio
async def test_generate_purchase_order_850_requires_non_empty_lines():
    service = EDIService(erp_client=_FakeERPClientNoLines())

    with pytest.raises(InvalidPurchaseOrderError):
        await service.generate_purchase_order_850("POEMPTY")
