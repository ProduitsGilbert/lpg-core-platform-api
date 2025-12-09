"""File Share service for document management."""

from __future__ import annotations

import base64
import io
import logging
import tempfile
from typing import Any, Dict, Optional, List

import httpx
import logfire
from pypdf import PdfReader
from fillpdf import fillpdfs

from app.settings import settings

logger = logging.getLogger(__name__)


class FileShareService:
    """Service for interacting with the Gilbert Tech file share API."""

    def __init__(self) -> None:
        self._base_url = settings.file_share_base_url.rstrip("/")
        self._requester_id = (
            settings.file_share_requester_id
            or settings.bc_api_username
            or "system"
        )

    async def get_item_pdf(self, item_no: str) -> Optional[Dict[str, object]]:
        """Retrieve the PDF documentation for a specific item."""
        url = f"{self._base_url}/FileShare/GetItemPDFFile({item_no})"
        headers = {
            "accept": "*/*",
            "RequesterUserID": self._requester_id,
        }

        with logfire.span("file_share.get_item_pdf", item_no=item_no, url=url):
            try:
                async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                    response = await client.get(url, headers=headers)

                if response.status_code == 404:
                    logger.info("Item PDF not found", extra={"item_no": item_no})
                    return None

                response.raise_for_status()

                filename = self._extract_filename(response.headers) or f"{item_no}.pdf"
                content_type = response.headers.get("Content-Type", "application/pdf")
                content = response.content

                logfire.info(
                    "Retrieved item PDF from file share",
                    item_no=item_no,
                    filename=filename,
                    size=len(content),
                )

                return {
                    "content": content,
                    "filename": filename,
                    "size": len(content),
                    "content_type": content_type,
                    "metadata": {
                        "item_no": item_no,
                        "source": "file_share_api",
                        "requester": self._requester_id,
                    },
                }

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code if exc.response else None
                logger.error(
                    "File share API returned error",
                    extra={
                        "item_no": item_no,
                        "status_code": status_code,
                        "body": exc.response.text[:500] if exc.response else None,
                    },
                )
                raise
            except Exception as exc:
                logger.error("Error retrieving item PDF", exc_info=exc)
                raise

    async def read_technical_sheet(self, item_no: str) -> Dict[str, Any]:
        """
        Read technical sheet content, form fields, and vision fallback.
        
        Returns a dict with keys: success, data, error.
        """
        try:
            pdf_data = await self.get_item_pdf(item_no)
            if not pdf_data:
                return {
                    "success": False,
                    "data": None,
                    "error": f"PDF file not found for item '{item_no}'"
                }

            pdf_bytes = pdf_data["content"]
            
            # 1. Extract form fields
            fields_summary = "No form fields detected."
            fields_json = {}
            
            # Use fillpdfs to read form fields
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                tmp.flush()
                try:
                    fields = fillpdfs.get_form_fields(tmp.name)
                    if fields:
                        fields_summary = self._flatten_fields(fields)
                        fields_json = fields
                except Exception as exc:
                    fields_summary = f"Failed to read form fields: {exc}"
                    logger.warning(f"fillpdf error: {exc}")

            # 2. Extract text content
            text_content = ""
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                pages_text = []
                for i, page in enumerate(reader.pages):
                    if i >= 10:
                        pages_text.append(f"... (truncated after {i} pages)")
                        break
                    extracted = page.extract_text() or ""
                    if extracted.strip():
                        pages_text.append(f"[Page {i+1}]\n{extracted.strip()}")
                text_content = "\n\n".join(pages_text)
            except Exception as exc:
                text_content = f"Failed to extract text: {exc}"

            # 3. Vision fallback
            vision_fallback = {"available": False}
            if not text_content.strip() and (not fields_json):
                try:
                    reader = PdfReader(io.BytesIO(pdf_bytes))
                    if len(reader.pages) > 0:
                        page = reader.pages[0]
                        # Check for images in the first page
                        if hasattr(page, "images") and page.images:
                            images = page.images
                            if images:
                                largest_image = max(images, key=lambda img: len(img.data))
                                image_bytes = largest_image.data
                                
                                mime_type = "image/png"
                                if largest_image.name:
                                    name_lower = largest_image.name.lower()
                                    if name_lower.endswith((".jpg", ".jpeg")):
                                        mime_type = "image/jpeg"
                                
                                data_url = self._build_data_url(image_bytes, mime_type)
                                
                                vision_fallback = {
                                    "available": True,
                                    "data_url": data_url,
                                    "instructions": "Use vision capabilities to analyze this technical drawing."
                                }
                except Exception as exc:
                    vision_fallback = {
                        "available": False,
                        "error": f"Vision fallback failed: {exc}"
                    }

            return {
                "success": True,
                "data": {
                    "text_content": text_content,
                    "form_fields": fields_summary,
                    "fields_json": fields_json,
                    "vision_fallback": vision_fallback
                },
                "error": None
            }

        except Exception as exc:
            logger.error(f"Error reading technical sheet for {item_no}", exc_info=exc)
            return {
                "success": False,
                "data": None,
                "error": str(exc)
            }

    async def write_technical_sheet(self, item_no: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fill technical sheet form fields with provided data.
        
        Returns a dict similar to get_item_pdf result, containing the new PDF content.
        """
        try:
            pdf_data = await self.get_item_pdf(item_no)
            if not pdf_data:
                return {
                    "success": False,
                    "error": f"PDF file not found for item '{item_no}'"
                }

            original_pdf_bytes = pdf_data["content"]
            filename = pdf_data["filename"]
            
            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as input_tmp, \
                 tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as output_tmp:
                
                input_tmp.write(original_pdf_bytes)
                input_tmp.flush()
                
                # Fill PDF using fillpdfs
                # Note: fillpdfs.write_fillable_pdf takes file paths
                try:
                    fillpdfs.write_fillable_pdf(input_tmp.name, output_tmp.name, fields, flatten=False)
                    
                    # Read back the filled PDF
                    output_tmp.seek(0)
                    new_pdf_bytes = output_tmp.read()
                    
                    if not new_pdf_bytes:
                         return {
                            "success": False,
                            "error": "Generated PDF is empty"
                        }

                    return {
                        "success": True,
                        "content": new_pdf_bytes,
                        "filename": filename, # Keep original filename
                        "size": len(new_pdf_bytes),
                        "content_type": "application/pdf"
                    }

                except Exception as exc:
                    logger.error(f"Failed to fill PDF for {item_no}: {exc}")
                    return {
                        "success": False,
                        "error": f"Failed to fill PDF form: {str(exc)}"
                    }

        except Exception as exc:
            logger.error(f"Error writing technical sheet for {item_no}", exc_info=exc)
            return {
                "success": False,
                "error": str(exc)
            }

    @staticmethod
    def _extract_filename(headers: httpx.Headers) -> Optional[str]:
        disposition = headers.get("Content-Disposition")
        if not disposition:
            return None

        parts = [part.strip() for part in disposition.split(";")]
        for part in parts:
            if part.lower().startswith("filename="):
                value = part.split("=", 1)[1]
                return value.strip('"')
        return None

    @staticmethod
    def _flatten_fields(fields: Dict[str, Any]) -> str:
        """Render readable list of form fields."""
        lines = []
        for key, value in sorted(fields.items(), key=lambda kv: kv[0].lower()):
            if isinstance(value, dict):
                inner = "; ".join(f"{k}: {v}" for k, v in value.items())
                lines.append(f"- {key}: {inner}")
            elif isinstance(value, list):
                inner = "; ".join(str(item) for item in value)
                lines.append(f"- {key}: {inner}")
            else:
                lines.append(f"- {key}: {value}")
        return "\n".join(lines) if lines else "No fields found."

    @staticmethod
    def _build_data_url(content: bytes, mime_type: str) -> str:
        """Convert bytes to base64 data URL."""
        return f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"
