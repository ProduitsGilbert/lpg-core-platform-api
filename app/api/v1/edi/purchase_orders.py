"""EDI purchase order endpoints."""

from fastapi import APIRouter, status
import logfire

from app.api.v1.models import SingleResponse
from app.domain.edi import EDIService
from .models import PurchaseOrder850Request, PurchaseOrder850Response

router = APIRouter(prefix="/edi", tags=["EDI"])

edi_service = EDIService()


@router.post(
    "/purchase-orders/850/send",
    response_model=SingleResponse[PurchaseOrder850Response],
    status_code=status.HTTP_200_OK,
    summary="Send Purchase Order via EDI 850",
    description="Generate an EDI 850 document for the specified purchase order and transmit it to the trading partner via SFTP.",
)
async def send_purchase_order_850(request: PurchaseOrder850Request) -> SingleResponse[PurchaseOrder850Response]:
    with logfire.span("edi.send_purchase_order_850", po_number=request.po_number):
        result = edi_service.send_purchase_order_850(request.po_number)

    response = PurchaseOrder850Response(
        po_number=result.po_number,
        file_name=result.file_name,
        sent=result.sent,
        generated_at=result.generated_at,
        remote_path=result.remote_path,
        message=result.message,
    )

    return SingleResponse(data=response)
