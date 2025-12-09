import os

import pytest

from app.domain.edi.service import EDIService
from app.errors import InvalidPurchaseOrderError
from migration.edi import SFTPSendResult


class StubERPClient:
    def __init__(self, *, vendor_available: bool = True):
        self.vendor_available = vendor_available

    async def get_purchase_order(self, po_number: str):
        return {
            "No": po_number,
            "Document_Date": "2024-05-01",
            "Amount": "100.00",
            "Amount_Including_VAT": "115.00",
            "Buy_from_Vendor_No": "VEND01",
        }

    async def get_purchase_order_lines(self, po_number: str):
        return [
            {
                "Line_No": 10000,
                "Quantity": "2",
                "Unit_of_Measure_Code": "EA",
                "Direct_Unit_Cost": "50.00",
                "Vendor_Item_No": "VI-100",
                "No": "ITEM-100",
                "Description": "Sample Item",
            }
        ]

    async def get_vendor(self, vendor_id: str):
        if not self.vendor_available:
            return None
        return {
            "No": vendor_id,
            "Name": "Vendor Inc",
            "Address": "123 Main",
            "City": "Townsville",
            "County": "QC",
            "Post_Code": "A1B2C3",
        }


@pytest.fixture
def fake_paths(tmp_path):
    send_root = tmp_path / "edi" / "send"
    recv_root = tmp_path / "edi" / "receive"

    def _get_paths():
        return str(send_root), str(recv_root)

    return _get_paths


@pytest.mark.asyncio
async def test_send_purchase_order_850_success(monkeypatch, fake_paths):
    sent_paths = {}

    monkeypatch.setattr("app.domain.edi.service.get_edi_paths", fake_paths)

    def fake_send_file(path, **kwargs):
        sent_paths["path"] = path
        return SFTPSendResult(success=True, remote_path="EMISSION/850/TEST.edi")

    monkeypatch.setattr("app.domain.edi.service.send_file", fake_send_file)

    service = EDIService(erp_client=StubERPClient())
    result = await service.send_purchase_order_850("PO123")

    assert result.sent is True
    assert result.remote_path == "EMISSION/850/TEST.edi"
    assert result.po_number == "PO123"
    assert os.path.basename(sent_paths["path"]).startswith("PO_PO123_")
    assert os.path.exists(sent_paths["path"]) is True


@pytest.mark.asyncio
async def test_send_purchase_order_850_missing_vendor(monkeypatch, fake_paths):
    monkeypatch.setattr("app.domain.edi.service.get_edi_paths", fake_paths)
    monkeypatch.setattr(
        "app.domain.edi.service.send_file",
        lambda path: SFTPSendResult(success=True, remote_path=""),
    )

    service = EDIService(erp_client=StubERPClient(vendor_available=False))

    with pytest.raises(InvalidPurchaseOrderError):
        await service.send_purchase_order_850("PO999")
