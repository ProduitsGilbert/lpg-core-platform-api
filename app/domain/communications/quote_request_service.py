"""Service to send vendor quote requests via Front."""

from __future__ import annotations

import html
import json
from typing import Any, Dict, Iterable, List, Optional, Sequence, Type

import logfire

from app.adapters.front_client import FrontClient
from app.domain.communications.models import QuoteRequestResponse
from app.domain.erp.business_central_data_service import BusinessCentralODataService
from app.domain.erp.vendor_contact_service import VendorContactService, DEFAULT_VENDOR_EMAIL
from app.domain.toolkit.ai_service import AIService
from app.domain.toolkit.models import StandardAIRequest
from app.errors import CommunicationsConfigurationError, CommunicationsError
from app.ports import FrontClientProtocol
from app.settings import settings

_MAX_FRONT_ATTACHMENT_BYTES = 25 * 1024 * 1024


class QuoteRequestService:
    """Handle vendor quote request workflow."""

    def __init__(
        self,
        *,
        front_client_class: Type[FrontClientProtocol] = FrontClient,
        odata_service: Optional[BusinessCentralODataService] = None,
        ai_service: Optional[AIService] = None,
    ) -> None:
        self._front_client_class = front_client_class
        self._vendor_contact_service = VendorContactService(
            odata_service or BusinessCentralODataService()
        )
        self._ai_service = ai_service or AIService()

    def _client(self) -> FrontClientProtocol:
        return self._front_client_class()  # type: ignore[return-value]

    async def send_quote_request(
        self,
        *,
        vendor_id: str,
        subject: str,
        body: str,
        language_override: Optional[str],
        table_json: Optional[str],
        attachments: Optional[List[Dict[str, Any]]],
        dry_run: bool,
    ) -> QuoteRequestResponse:
        vendor_contact = await self._vendor_contact_service.get_vendor_contact(vendor_id)
        if vendor_contact.email == DEFAULT_VENDOR_EMAIL:
            raise CommunicationsError(
                detail="Vendor email not found for the requested vendor.",
                status_code=409,
                error_code="VENDOR_EMAIL_MISSING",
                context={"vendor_id": vendor_contact.vendor_id},
            )
        target_language = _normalize_language(
            language_override or vendor_contact.communication_language or vendor_contact.language
        )

        with logfire.span(
            "quote_request.translate",
            vendor_id=vendor_contact.vendor_id,
            language=target_language,
        ):
            subject_final = await self._translate_text(subject, target_language, is_html=False)
            body_final = await self._translate_text(body, target_language, is_html=True)

        table_html = _render_table_html(table_json)
        if table_html:
            body_final = f"{body_final}<br/>{table_html}"

        attachments_sent = [attachment["filename"] for attachment in attachments or []]
        payload = {
            "to": [vendor_contact.email],
            "subject": subject_final,
            "body": body_final,
        }

        if dry_run:
            return QuoteRequestResponse(
                status="dry_run",
                vendor_id=vendor_contact.vendor_id,
                vendor_email=vendor_contact.email,
                language=target_language,
                subject_final=subject_final,
                body_final_preview=body_final,
                attachments_sent=attachments_sent,
                dry_run=True,
            )

        channel_id = settings.front_purchasing_channel_id
        if not channel_id:
            raise CommunicationsConfigurationError(
                "FRONT_PURCHASING_CHANNEL_ID is not configured."
            )

        _validate_attachments(attachments or [])

        async with self._client() as client:
            response = await client.send_channel_message(
                channel_id,
                payload,
                attachments=attachments,
            )

        return QuoteRequestResponse(
            status="sent",
            vendor_id=vendor_contact.vendor_id,
            vendor_email=vendor_contact.email,
            language=target_language,
            subject_final=subject_final,
            body_final_preview=body_final,
            attachments_sent=attachments_sent,
            front_message_id=response.get("id"),
            front_conversation_id=response.get("conversation_id"),
            dry_run=False,
        )

    async def _translate_text(self, text: str, language: str, *, is_html: bool) -> str:
        if not settings.enable_ai_assistance or not settings.openai_api_key:
            raise CommunicationsConfigurationError(
                "Translation requires AI assistance to be enabled with OPENAI_API_KEY."
            )

        instructions = (
            f"Translate the user's text to {language}. "
            "Preserve meaning, punctuation, and formatting. "
            "Return only the translated text."
        )
        if is_html:
            instructions += " Preserve HTML tags and attributes. Translate only text nodes."

        request = StandardAIRequest(prompt=text, instructions=instructions, temperature=0.2)
        response = await self._ai_service.generate_standard_response(request)
        if response.stubbed:
            raise CommunicationsError("Translation service returned a stubbed response.")
        return response.output.strip()


def _normalize_language(value: str) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"fr", "fra", "fr-ca", "frca", "french", "francais"}:
        return "French"
    if normalized in {"en", "eng", "english"}:
        return "English"
    return value.strip() if value else "French"


def _render_table_html(table_json: Optional[str]) -> str:
    if not table_json:
        return ""
    try:
        rows = json.loads(table_json)
    except json.JSONDecodeError as exc:
        raise CommunicationsError(
            detail="Invalid table_json payload; must be valid JSON array of objects.",
            status_code=422,
            error_code="INVALID_TABLE_JSON",
        ) from exc

    if not isinstance(rows, list) or not rows:
        return ""

    normalized_rows: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise CommunicationsError(
                detail="table_json rows must be objects.",
                status_code=422,
                error_code="INVALID_TABLE_JSON",
            )
        normalized_rows.append(row)

    headers = _collect_table_headers(normalized_rows)
    if not headers:
        return ""

    header_html = "".join(f"<th>{html.escape(str(header))}</th>" for header in headers)
    body_html = []
    for row in normalized_rows:
        cells = "".join(
            f"<td>{html.escape(str(row.get(header, '')))}</td>" for header in headers
        )
        body_html.append(f"<tr>{cells}</tr>")

    return (
        "<table border=\"1\" cellspacing=\"0\" cellpadding=\"4\">"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(body_html)}</tbody>"
        "</table>"
    )


def _collect_table_headers(rows: Sequence[Dict[str, Any]]) -> List[str]:
    headers: List[str] = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(key)
    return headers


def _validate_attachments(attachments: Iterable[Dict[str, Any]]) -> None:
    for attachment in attachments:
        content = attachment.get("content", b"")
        if not isinstance(content, (bytes, bytearray)):
            raise CommunicationsError(
                detail="Attachment content must be bytes.",
                status_code=400,
                error_code="INVALID_ATTACHMENT",
            )
        if len(content) > _MAX_FRONT_ATTACHMENT_BYTES:
            raise CommunicationsError(
                detail="Attachment exceeds Front 25MB size limit.",
                status_code=400,
                error_code="ATTACHMENT_TOO_LARGE",
            )
