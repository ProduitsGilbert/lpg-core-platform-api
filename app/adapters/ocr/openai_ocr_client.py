"""
OpenAI-based OCR client for document extraction.

This adapter uses OpenAI's GPT models with structured output to extract
data from PDF and image documents.
"""

import base64
import io
import json
from typing import Dict, Any, Type, Optional
import time
import logfire
import openai
import httpx
from openai import OpenAI
from pydantic import BaseModel
from pypdf import PdfReader

from app.ports import OCRClientProtocol
from app.domain.ocr.models import (
    PurchaseOrderExtraction,
    InvoiceExtraction,
    SupplierAccountStatementExtraction,
    CustomerAccountStatementExtraction,
    SupplierInvoiceExtraction,
    VendorQuoteExtraction,
    OrderConfirmationExtraction,
    ShippingBillExtraction,
    CommercialInvoiceExtraction,
    ComplexDocumentExtraction,
    ComplexDocumentAnalysis,
)


class OpenAIOCRClient(OCRClientProtocol):
    """
    OpenAI implementation of OCR client.
    
    Uses OpenAI's GPT models with structured output parsing
    to extract data from corporate documents.
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5-2025-08-07",
        openrouter_api_key: Optional[str] = None,
        openrouter_model: str = "openrouter/auto",
        primary_provider: str = "openrouter",
    ):
        """
        Initialize OpenAI OCR client.
        
        Args:
            api_key: OpenAI API key
            model: Model to use for extraction (default: gpt-5-2025-08-07)
        """
        # Cap request latency to keep OCR responsive.
        self._default_timeout = 45.0
        self.client = OpenAI(api_key=api_key, timeout=self._default_timeout) if api_key else None
        self.model = model
        self._enabled = bool(api_key)
        self._supports_responses = bool(self.client) and hasattr(self.client, "responses")
        self._openrouter_key = openrouter_api_key
        self._openrouter_enabled = bool(openrouter_api_key)
        self._openrouter_model = openrouter_model
        self._openrouter_base_url = "https://openrouter.ai/api/v1"
        normalized_provider = (primary_provider or "openrouter").strip().lower()
        if normalized_provider not in ("openrouter", "openai"):
            logfire.warn(
                "Unknown OCR primary provider; defaulting to openrouter.",
                provider=normalized_provider,
            )
            normalized_provider = "openrouter"
        self._primary_provider = normalized_provider
        logfire.info(
            f"OpenAI OCR client initialized with model: {model} "
            f"(sdk: {getattr(openai, '__version__', 'unknown')})"
        )
        logfire.info("OCR primary provider configured", provider=self._primary_provider)
        if self._enabled and not self._supports_responses:
            logfire.warn(
                "OpenAI SDK lacks responses API; falling back to chat completions. "
                "Upgrade openai to >=1.58.1 for best results."
            )
        if self._openrouter_enabled:
            logfire.info(f"OpenRouter OCR fallback enabled (model: {openrouter_model})")
    
    @property
    def enabled(self) -> bool:
        """Whether the OCR client is enabled and available."""
        return self._enabled

    @staticmethod
    def _schema_instructions(response_model: Type[BaseModel]) -> str:
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        return (
            "Return ONLY valid JSON that matches this schema:\n"
            f"{schema_json}"
        )

    @staticmethod
    def _strip_code_fences(content: str) -> str:
        stripped = content.strip()
        if not stripped.startswith("```"):
            return stripped
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()

    @staticmethod
    def _parse_json_output(content: str, response_model: Type[BaseModel]) -> BaseModel:
        raw = OpenAIOCRClient._strip_code_fences(content or "")
        if not raw:
            raise ValueError("Empty response from model")

        try:
            return response_model.model_validate_json(raw)
        except Exception:
            candidates = [raw]
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidates.append(raw[start : end + 1])
            for candidate in candidates:
                try:
                    data = json.loads(candidate)
                except Exception:
                    continue
                return response_model.model_validate(data)
            raise

    @staticmethod
    def _extract_pdf_text(
        file_content: bytes,
        *,
        max_pages: int = 60,
        max_chars: int = 40000,
    ) -> str:
        reader = PdfReader(io.BytesIO(file_content))
        pages_text: list[str] = []
        for i, page in enumerate(reader.pages):
            if i >= max_pages:
                break
            extracted = page.extract_text() or ""
            if extracted.strip():
                pages_text.append(extracted.strip())
        combined = "\n\n".join(pages_text)
        return combined[:max_chars]

    @staticmethod
    def _has_meaningful_text(text: str, *, min_chars: int = 800, min_alnum_ratio: float = 0.2) -> bool:
        if not text:
            return False
        stripped = text.strip()
        if len(stripped) < min_chars:
            return False
        alnum = sum(1 for ch in stripped if ch.isalnum())
        ratio = alnum / max(len(stripped), 1)
        return ratio >= min_alnum_ratio

    @staticmethod
    def _supplier_statement_min_valid(statement: SupplierAccountStatementExtraction) -> bool:
        if not getattr(statement, "supplier_name", None):
            return False
        transactions = getattr(statement, "transactions", None)
        return bool(transactions)

    @staticmethod
    def _infer_image_mime(file_content: bytes, filename: str) -> str:
        lower = filename.lower()
        if lower.endswith(".png") or file_content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        if lower.endswith((".jpg", ".jpeg")) or file_content.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        if lower.endswith(".webp") or (
            file_content[:4] == b"RIFF" and file_content[8:12] == b"WEBP"
        ):
            return "image/webp"
        return "image/png"

    def _image_data_url(self, file_content: bytes, filename: str) -> str:
        mime = self._infer_image_mime(file_content, filename)
        encoded = base64.b64encode(file_content).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def _base64_file_input(self, file_content: bytes, filename: str, is_pdf: bool) -> Dict[str, Any]:
        if is_pdf:
            encoded = base64.b64encode(file_content).decode("ascii")
            return {
                "type": "input_file",
                "filename": filename,
                "file_data": encoded,
            }
        return {
            "type": "input_image",
            "image_url": {"url": self._image_data_url(file_content, filename)},
        }

    def _parse_with_chat_completions(
        self,
        *,
        messages: list[dict[str, Any]],
        response_model: Type[BaseModel],
    ) -> BaseModel:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
            timeout=self._default_timeout,
        )
        content = response.choices[0].message.content or ""
        return self._parse_json_output(content, response_model)

    @staticmethod
    def _extract_openrouter_content(content: Any) -> str:
        if isinstance(content, list):
            parts: list[str] = []
            for part in content:
                if isinstance(part, dict):
                    if "text" in part:
                        parts.append(str(part["text"]))
                    elif "content" in part:
                        parts.append(str(part["content"]))
                else:
                    parts.append(str(part))
            return "".join(parts)
        if content is None:
            return ""
        return str(content)

    def _openrouter_request(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        file_content: Optional[bytes] = None,
        filename: Optional[str] = None,
        is_pdf: bool = False,
    ) -> BaseModel:
        if not self._openrouter_enabled or not self._openrouter_key:
            raise RuntimeError("OpenRouter API key is not configured")

        system_with_schema = f"{system_prompt}\n\n{self._schema_instructions(response_model)}"
        content: list[dict[str, Any]] = [{"type": "text", "text": user_prompt}]

        if file_content is not None and filename:
            if is_pdf:
                encoded = base64.b64encode(file_content).decode("ascii")
                data_url = f"data:application/pdf;base64,{encoded}"
            else:
                data_url = self._image_data_url(file_content, filename)
            content.append(
                {
                    "type": "file",
                    "file": {
                        "filename": filename,
                        "file_data": data_url,
                    },
                }
            )

        payload = {
            "model": self._openrouter_model,
            "messages": [
                {"role": "system", "content": system_with_schema},
                {"role": "user", "content": content},
            ],
            "response_format": {"type": "json_object"},
        }
        if is_pdf:
            payload["plugins"] = [
                {
                    "id": "file-parser",
                    "pdf": {"engine": "pdf-text"},
                }
            ]

        headers = {
            "Authorization": f"Bearer {self._openrouter_key}",
            "Content-Type": "application/json",
        }

        timeout = httpx.Timeout(30.0, connect=10.0)
        response = httpx.post(
            f"{self._openrouter_base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        data = response.json()

        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"OpenRouter error: {data['error']}")

        try:
            message = data["choices"][0]["message"]["content"]
        except Exception as exc:
            raise RuntimeError(f"Unexpected OpenRouter response format: {data}") from exc

        text = self._extract_openrouter_content(message)
        return self._parse_json_output(text, response_model)

    def _upload_document(self, file_content: bytes, filename: str):
        """Upload a document for vision processing."""
        file_buffer = io.BytesIO(file_content)
        file_buffer.name = filename
        return self.client.files.create(
            file=file_buffer,
            purpose="assistants"
        )

    def _cleanup_document(self, file_id: str) -> None:
        """Attempt to delete an uploaded document; log failures only."""
        try:
            self.client.files.delete(file_id)
        except Exception as exc:  # pragma: no cover - cleanup is best effort
            logfire.warn(
                "Failed to delete uploaded file",
                file_id=file_id,
                error=str(exc),
            )

    def _extract_with_vision(
        self,
        file_content: bytes,
        filename: str,
        document_category: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
        prefer_vision: bool = False,
    ) -> BaseModel:
        """Shared helper that sends the document to a vision-capable model."""
        if not self.enabled:
            raise ValueError("OpenAI client is not enabled")

        is_pdf = file_content[:4] == b"%PDF" or filename.lower().endswith(".pdf")
        # Fast-path: if the PDF already contains meaningful text, avoid file upload to vision
        # and parse the text directly with the structured schema.
        if is_pdf and not prefer_vision:
            pdf_text = self._extract_pdf_text(
                file_content,
                max_pages=20,
                max_chars=15000,
            )
            if self._has_meaningful_text(pdf_text):
                logfire.info(
                    "Using text fast-path for OCR",
                    document_category=document_category,
                    filename=filename,
                    extracted_chars=len(pdf_text),
                )
                text_prompt = (
                    f"{user_prompt}\n\n--- BEGIN DOCUMENT TEXT ---\n"
                    f"{pdf_text}\n--- END DOCUMENT TEXT ---"
                )
                try:
                    parsed = self._extract_with_text(
                        document_category=document_category,
                        system_prompt=system_prompt,
                        user_prompt=text_prompt,
                        response_model=response_model,
                    )
                    # Minimal guard for supplier statements: ensure we got transactions.
                    if isinstance(parsed, SupplierAccountStatementExtraction) and not self._supplier_statement_min_valid(parsed):
                        logfire.warn(
                            "Text fast-path parsed but missing required supplier statement fields; using vision fallback.",
                            filename=filename,
                        )
                    else:
                        return parsed
                except Exception as exc:
                    logfire.warn(
                        "Text fast-path failed; using vision fallback.",
                        filename=filename,
                        error=str(exc),
                    )
        openrouter_attempted = False

        if self._openrouter_enabled and self._primary_provider == "openrouter":
            openrouter_attempted = True
            try:
                logfire.warn("Using OpenRouter as primary OCR provider.")
                return self._openrouter_request(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                    file_content=file_content,
                    filename=filename,
                    is_pdf=is_pdf,
                )
            except Exception as exc:
                logfire.error("OpenRouter OCR request failed", error=str(exc))

        if self._supports_responses:
            try:
                file_input = self._base64_file_input(file_content, filename, is_pdf=is_pdf)
                response = self.client.responses.parse(
                    model=self.model,
                    input=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "input_text",
                                    "text": user_prompt
                                },
                                file_input
                            ]
                        }
                    ],
                    text_format=response_model,
                    timeout=self._default_timeout,
                )

                return response.output_parsed
            except Exception as exc:
                logfire.error("OpenAI OCR vision request failed", error=str(exc))
                if "file_data" in str(exc).lower():
                    logfire.warn("Retrying OpenAI OCR with uploaded file.")
                    uploaded_file = self._upload_document(file_content, filename)
                    try:
                        file_input = {
                            "type": "input_file",
                            "file_id": uploaded_file.id,
                        }
                        try:
                            response = self.client.responses.parse(
                                model=self.model,
                                input=[
                                    {"role": "system", "content": system_prompt},
                                    {
                                        "role": "user",
                                        "content": [
                                            {"type": "input_text", "text": user_prompt},
                                            file_input,
                                        ],
                                    },
                                ],
                                text_format=response_model,
                                timeout=self._default_timeout,
                            )
                            return response.output_parsed
                        except Exception as inner_exc:
                            logfire.error(
                                "OpenAI OCR uploaded-file retry failed",
                                error=str(inner_exc),
                            )
                            if self._openrouter_enabled and not openrouter_attempted:
                                logfire.warn("Falling back to OpenRouter after uploaded-file retry.")
                                return self._openrouter_request(
                                    system_prompt=system_prompt,
                                    user_prompt=user_prompt,
                                    response_model=response_model,
                                    file_content=file_content,
                                    filename=filename,
                                    is_pdf=is_pdf,
                                )
                            raise
                    finally:
                        self._cleanup_document(uploaded_file.id)
                if self._openrouter_enabled and not openrouter_attempted:
                    logfire.warn("Falling back to OpenRouter for vision OCR.")
                    return self._openrouter_request(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_model=response_model,
                        file_content=file_content,
                        filename=filename,
                        is_pdf=is_pdf,
                    )
                raise

        logfire.warn(
            "OpenAI responses API unavailable; using chat completions fallback for vision OCR."
        )
        try:
            if is_pdf:
                extracted_text = self._extract_pdf_text(file_content)
                if extracted_text.strip():
                    fallback_prompt = (
                        f"{user_prompt}\n\n--- BEGIN DOCUMENT TEXT ---\n"
                        f"{extracted_text}\n--- END DOCUMENT TEXT ---"
                    )
                    return self._extract_with_text(
                        document_category=document_category,
                        system_prompt=system_prompt,
                        user_prompt=fallback_prompt,
                        response_model=response_model,
                    )
                raise RuntimeError(
                    "OpenAI SDK lacks responses API; cannot process scanned PDFs. "
                    "Upgrade openai to >=1.58.1 to enable vision OCR."
                )

            system_with_schema = f"{system_prompt}\n\n{self._schema_instructions(response_model)}"
            data_url = self._image_data_url(file_content, filename)
            messages = [
                {"role": "system", "content": system_with_schema},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_prompt},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ]
            return self._parse_with_chat_completions(
                messages=messages,
                response_model=response_model,
            )
        except Exception as exc:
            logfire.error("OpenAI OCR vision fallback failed", error=str(exc))
            if self._openrouter_enabled and not openrouter_attempted:
                logfire.warn("Falling back to OpenRouter for vision OCR.")
                return self._openrouter_request(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                    file_content=file_content,
                    filename=filename,
                    is_pdf=is_pdf,
                )
            raise

    @staticmethod
    def _truncate_text(text: Optional[str], limit: int) -> Optional[str]:
        if not text:
            return text
        if len(text) <= limit:
            return text
        return text[:limit] + "..."

    def _build_complex_analysis_payload(
        self,
        complex_data: ComplexDocumentExtraction,
        *,
        max_blocks: int = 120,
        max_text_chars: int = 800,
        max_rows: int = 25,
        max_cell_chars: int = 120,
    ) -> Dict[str, Any]:
        blocks = complex_data.blocks[:max_blocks]
        trimmed_blocks: list[dict[str, Any]] = []
        for block in blocks:
            block_payload: dict[str, Any] = {
                "block_id": block.block_id,
                "block_type": block.block_type,
                "page": block.page,
            }
            if block.text:
                block_payload["text"] = self._truncate_text(block.text, max_text_chars)
            if block.table:
                table = block.table
                trimmed_rows: list[list[str]] = []
                for row in table.rows[:max_rows]:
                    trimmed_row = [
                        self._truncate_text(cell, max_cell_chars) or ""
                        for cell in row
                    ]
                    trimmed_rows.append(trimmed_row)
                block_payload["table"] = {
                    "title": table.title,
                    "headers": [
                        self._truncate_text(header, max_cell_chars) or ""
                        for header in table.headers
                    ],
                    "rows": trimmed_rows,
                }
            if block.figure:
                figure = block.figure
                block_payload["figure"] = {
                    "title": figure.title,
                    "figure_type": figure.figure_type,
                    "description": figure.description,
                    "values": [value.model_dump() for value in figure.values],
                }
            trimmed_blocks.append(block_payload)
        return {
            "document_title": complex_data.document_title,
            "language": complex_data.language,
            "summary_markdown": complex_data.summary_markdown,
            "blocks": trimmed_blocks,
            "notes": {
                "total_blocks": len(complex_data.blocks),
                "blocks_included": len(trimmed_blocks),
                "truncated": len(complex_data.blocks) > len(trimmed_blocks),
            },
        }

    def _extract_with_text(
        self,
        document_category: str,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> BaseModel:
        """Shared helper that parses extracted document text (no vision/file upload)."""
        if not self.enabled:
            raise ValueError("OpenAI client is not enabled")

        openrouter_attempted = False
        if self._openrouter_enabled:
            openrouter_attempted = True
            try:
                logfire.info("Trying OpenRouter text OCR first.")
                return self._openrouter_request(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                )
            except Exception as exc:
                logfire.error("OpenRouter OCR request failed", error=str(exc))
                if self._primary_provider == "openrouter":
                    # Avoid hanging on OpenAI fallbacks when primary is OpenRouter.
                    raise

        system_with_schema = f"{system_prompt}\n\n{self._schema_instructions(response_model)}"
        messages = [
            {"role": "system", "content": system_with_schema},
            {"role": "user", "content": user_prompt},
        ]

        # Prefer chat completions with JSON response format (faster, reliable) before responses API.
        try:
            return self._parse_with_chat_completions(
                messages=messages,
                response_model=response_model,
            )
        except Exception as exc:
            logfire.error("OpenAI OCR chat-completions text request failed", error=str(exc))

        if self._supports_responses:
            try:
                response = self.client.responses.parse(
                    model=self.model,
                    input=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    text_format=response_model,
                    timeout=self._default_timeout,
                )
                return response.output_parsed
            except Exception as exc:
                logfire.error("OpenAI OCR text request failed", error=str(exc))
                if self._openrouter_enabled and not openrouter_attempted:
                    logfire.warn("Falling back to OpenRouter for text OCR.")
                    return self._openrouter_request(
                        system_prompt=system_prompt,
                        user_prompt=user_prompt,
                        response_model=response_model,
                    )
                raise

        logfire.warn(
            "OpenAI responses API unavailable; using chat completions fallback for text OCR."
        )
        try:
            return self._parse_with_chat_completions(
                messages=messages,
                response_model=response_model,
            )
        except Exception as exc:
            logfire.error("OpenAI OCR text fallback failed", error=str(exc))
            if self._openrouter_enabled and not openrouter_attempted:
                logfire.warn("Falling back to OpenRouter for text OCR.")
                return self._openrouter_request(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=response_model,
                )
            raise

    def extract_purchase_order(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from a Purchase Order document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            
        Returns:
            Structured PO data including header and lines
        """
        with logfire.span('openai_extract_purchase_order'):
            start_time = time.time()
            
            try:
                po_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="purchase_order",
                    system_prompt="""You are an expert at extracting structured data from Purchase Order documents.
                    Extract ALL information from the document including:
                    - PO header information (number, date, vendor details, buyer details)
                    - All line items with complete details (quantities, prices, dates)
                    - Payment and shipping terms
                    - Any special instructions or notes
                    Ensure all monetary amounts and quantities are accurately extracted as numbers.
                    For dates, use ISO format (YYYY-MM-DD).""",
                    user_prompt="Extract all purchase order information from this document. Include every line item with all details.",
                    response_model=PurchaseOrderExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted PO data in {processing_time}ms')
                
                # Convert to dict and add metadata
                result = po_data.model_dump()
                result["document_category"] = "purchase_order"
                result["confidence_score"] = 0.95  # OpenAI typically has high confidence
                result["processing_time_ms"] = processing_time
                
                return result
                
            except Exception as e:
                logfire.error(
                    "Failed to extract purchase order",
                    filename=filename,
                    error=str(e),
                )
                raise
    
    def extract_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """
        Extract structured data from an Invoice document.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            
        Returns:
            Structured invoice data including header and lines
        """
        with logfire.span('openai_extract_invoice'):
            start_time = time.time()
            
            try:
                invoice_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="invoice",
                    system_prompt="""You are an expert at extracting structured data from Invoice documents.
                    Extract ALL information from the document including:
                    - Invoice header (number, date, due date)
                    - Vendor/supplier information (name, address, tax ID)
                    - Customer/bill-to information
                    - All line items with complete details (descriptions, quantities, prices, discounts)
                    - Tax calculations and totals
                    - Payment terms and bank details
                    - Any reference to related Purchase Orders
                    Ensure all monetary amounts are accurately extracted as numbers.
                    For dates, use ISO format (YYYY-MM-DD).""",
                    user_prompt="Extract all invoice information from this document. Include every line item with all details, tax information, and payment terms.",
                    response_model=InvoiceExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted invoice data in {processing_time}ms')
                
                # Convert to dict and add metadata
                result = invoice_data.model_dump()
                result["document_category"] = "invoice"
                result["confidence_score"] = 0.95  # OpenAI typically has high confidence
                result["processing_time_ms"] = processing_time
                
                return result
                
            except Exception as e:
                logfire.error(
                    "Failed to extract invoice",
                    filename=filename,
                    error=str(e),
                )
                raise
    
    def extract_generic_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        output_model: Type[BaseModel],
        additional_instructions: Optional[str] = None,
    ) -> BaseModel:
        """
        Extract structured data from any document type using a custom model.
        
        Args:
            file_content: Binary content of the PDF/image file
            filename: Name of the file
            document_type: Type of document for prompt customization
            output_model: Pydantic model class defining expected output structure
            
        Returns:
            Extracted data in the specified model format
        """
        with logfire.span('openai_extract_generic_document'):
            start_time = time.time()
            
            try:
                field_descriptions = []
                for field_name, field_info in output_model.model_fields.items():
                    desc = field_info.description or field_name.replace("_", " ").title()
                    field_descriptions.append(f"- {desc}")

                fields_prompt = "\n".join(field_descriptions)

                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"

                extracted_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category=document_type,
                    system_prompt=f"""You are an expert at extracting structured data from {document_type} documents.
                    Extract ALL information from the document that matches these fields:
                    {fields_prompt}

                    Ensure all data is accurately extracted and properly formatted.
                    For dates, use ISO format (YYYY-MM-DD).
                    For monetary amounts, extract as decimal numbers without currency symbols.{extra}""",
                    user_prompt=(
                        f"Extract all relevant information from this {document_type} document according to the specified structure."
                        f"{extra}"
                    ),
                    response_model=output_model
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted {document_type} data in {processing_time}ms')
                
                # Add metadata if model supports it
                if hasattr(extracted_data, "confidence_score"):
                    extracted_data.confidence_score = 0.95
                if hasattr(extracted_data, "processing_time_ms"):
                    extracted_data.processing_time_ms = processing_time
                if hasattr(extracted_data, "document_category"):
                    extracted_data.document_category = document_type
                return extracted_data
                
            except Exception as e:
                logfire.error(
                    "Failed to extract document",
                    document_type=document_type,
                    filename=filename,
                    error=str(e),
                )
                raise

    def extract_generic_text(
        self,
        document_text: str,
        document_type: str,
        output_model: Type[BaseModel]
    ) -> BaseModel:
        """
        Extract structured data from plain text using a custom model.

        This is used as a fallback for large PDFs where uploading the whole document
        for vision processing would be inefficient or exceed provider limits.
        """
        with logfire.span('openai_extract_generic_text'):
            start_time = time.time()

            if not document_text or not document_text.strip():
                raise ValueError("document_text is empty")

            try:
                field_descriptions = []
                for field_name, field_info in output_model.model_fields.items():
                    desc = field_info.description or field_name.replace("_", " ").title()
                    field_descriptions.append(f"- {desc}")

                fields_prompt = "\n".join(field_descriptions)

                extracted_data = self._extract_with_text(
                    document_category=document_type,
                    system_prompt=f"""You are an expert at extracting structured data from {document_type} documents.
Extract ALL information from the provided text that matches these fields:
{fields_prompt}

Guidelines:
- Only use information that is present in the text.
- Preserve the exact meaning of payment terms and timing.
- For monetary amounts, extract decimal numbers without currency symbols.
- For percent values, use numbers from 0 to 100.
- If currency is present, return ISO 4217 codes (e.g., USD, CAD, EUR).""",
                    user_prompt=f"""Extract the required structured data from this document text:

--- BEGIN DOCUMENT TEXT ---
{document_text}
--- END DOCUMENT TEXT ---""",
                    response_model=output_model
                )

                processing_time = int((time.time() - start_time) * 1000)
                logfire.info(f'Successfully extracted {document_type} data from text in {processing_time}ms')

                # Add metadata if model supports it
                if hasattr(extracted_data, "confidence_score"):
                    extracted_data.confidence_score = 0.9
                if hasattr(extracted_data, "processing_time_ms"):
                    extracted_data.processing_time_ms = processing_time
                if hasattr(extracted_data, "document_category"):
                    extracted_data.document_category = document_type

                return extracted_data

            except Exception as e:
                logfire.error(
                    "Failed to extract document from text",
                    document_type=document_type,
                    error=str(e),
                )
                raise

    def extract_supplier_account_statement(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured data from a supplier account statement document."""
        with logfire.span('openai_extract_supplier_account_statement'):
            start_time = time.time()

            try:
                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"
                system_prompt = """You are an expert at extracting structured data from supplier account statements.
                    Capture the supplier identifiers, statement period, opening/closing balances, totals, and every transaction line.
                    Ensure debits, credits, and balances are returned as decimal numbers.
                    Dates must be formatted as ISO YYYY-MM-DD."""
                user_prompt = (
                    "Extract all supplier account statement details including summary balances and the full list of transactions."
                    f"{extra}"
                )

                statement_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="supplier_account_statement",
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    response_model=SupplierAccountStatementExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = statement_data.model_dump()
                result["document_category"] = "supplier_account_statement"
                result["confidence_score"] = 0.9
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract supplier account statement",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_customer_account_statement(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a customer account statement document."""
        with logfire.span('openai_extract_customer_account_statement'):
            start_time = time.time()

            try:
                statement_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="customer_account_statement",
                    system_prompt="""You are an expert at extracting structured data from customer account statements.
                    Capture the customer identifiers, statement dates, balances, credit limits, and every transaction line.
                    Debits, credits, and balances must be decimal numbers.
                    Dates must be returned using ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all customer account statement information including balances and detailed transactions.",
                    response_model=CustomerAccountStatementExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = statement_data.model_dump()
                result["document_category"] = "customer_account_statement"
                result["confidence_score"] = 0.9
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract customer account statement",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_supplier_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a supplier invoice document."""
        with logfire.span('openai_extract_supplier_invoice'):
            start_time = time.time()

            try:
                invoice_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="supplier_invoice",
                    system_prompt="""You are an expert at extracting structured data from supplier invoices for accounts payable processing.
                    Capture vendor and buyer information, invoice identifiers, dates, totals, taxes, payment instructions, references, and detailed line items.
                    Return all numeric values as decimal numbers without currency symbols.
                    Dates must use ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all supplier invoice information including summary amounts, payment info, and detailed line items.",
                    response_model=SupplierInvoiceExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = invoice_data.model_dump()
                result["document_category"] = "supplier_invoice"
                result["confidence_score"] = 0.92
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract supplier invoice",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_vendor_quote(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured data from a vendor quote document."""
        with logfire.span('openai_extract_vendor_quote'):
            start_time = time.time()

            try:
                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"

                quote_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="vendor_quote",
                    system_prompt="""You are an expert at extracting structured data from vendor quote documents.
                    Capture the quote number, quote date, supplier name, and every line item.
                    Line items must include item numbers (if present), vendor item numbers, descriptions, quantities,
                    unit prices, line totals, and estimated delivery time (as stated in the document).
                    Ensure all quantities and monetary amounts are returned as decimal numbers.
                    Dates must use ISO YYYY-MM-DD format.""",
                    user_prompt=(
                        "Extract vendor quote details including header information and all line items."
                        f"{extra}"
                    ),
                    response_model=VendorQuoteExtraction,
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = quote_data.model_dump()
                result["document_category"] = "vendor_quote"
                result["confidence_score"] = 0.92
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract vendor quote",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_order_confirmation(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Extract structured data from an order confirmation document."""
        with logfire.span('openai_extract_order_confirmation'):
            start_time = time.time()

            try:
                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"

                confirmation_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="order_confirmation",
                    system_prompt="""You are an expert at extracting structured data from order confirmation documents.
                    Capture the order confirmation number, confirmation date, supplier name, and the buyer PO reference number.
                    Line items must include item numbers (if present), vendor item numbers, descriptions, quantities,
                    unit prices, line totals, and expected delivery dates.
                    Ensure all quantities and monetary amounts are returned as decimal numbers.
                    Dates must use ISO YYYY-MM-DD format.""",
                    user_prompt=(
                        "Extract order confirmation details including header information and all line items."
                        f"{extra}"
                    ),
                    response_model=OrderConfirmationExtraction,
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = confirmation_data.model_dump()
                result["document_category"] = "order_confirmation"
                result["confidence_score"] = 0.92
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract order confirmation",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_shipping_bill(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a shipping bill document."""
        with logfire.span('openai_extract_shipping_bill'):
            start_time = time.time()

            try:
                shipping_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="shipping_bill",
                    system_prompt="""You are an expert at extracting structured data from shipping bills or bills of entry/export.
                    Capture exporter and consignee information, ports, transport details, incoterms, totals, and every declared line item with HS codes and customs values.
                    Return numeric amounts as decimals and dates using ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all shipping bill declaration details including header information and each declared line item.",
                    response_model=ShippingBillExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = shipping_data.model_dump()
                result["document_category"] = "shipping_bill"
                result["confidence_score"] = 0.88
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract shipping bill",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_commercial_invoice(
        self,
        file_content: bytes,
        filename: str
    ) -> Dict[str, Any]:
        """Extract structured data from a commercial invoice document."""
        with logfire.span('openai_extract_commercial_invoice'):
            start_time = time.time()

            try:
                commercial_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="commercial_invoice",
                    system_prompt="""You are an expert at extracting structured data from commercial export invoices.
                    Capture exporter and importer details, invoice identifiers, incoterms, payment terms, logistics information, totals, and each line item with HS codes and countries of origin/destination.
                    All monetary values must be decimals and dates in ISO YYYY-MM-DD format.""",
                    user_prompt="Extract all commercial invoice details including parties, totals, logistics information, and the detailed line item list.",
                    response_model=CommercialInvoiceExtraction
                )

                processing_time = int((time.time() - start_time) * 1000)
                result = commercial_data.model_dump()
                result["document_category"] = "commercial_invoice"
                result["confidence_score"] = 0.9
                result["processing_time_ms"] = processing_time
                return result

            except Exception as exc:
                logfire.error(
                    "Failed to extract commercial invoice",
                    filename=filename,
                    error=str(exc),
                )
                raise

    def extract_complex_document(
        self,
        file_content: bytes,
        filename: str,
        additional_instructions: Optional[str] = None,
    ) -> BaseModel:
        """Extract layout-aware content (text, tables, figures) from complex documents."""
        with logfire.span('openai_extract_complex_document'):
            start_time = time.time()

            try:
                extra = ""
                if additional_instructions and additional_instructions.strip():
                    extra = f"\n\nAdditional instructions:\n{additional_instructions.strip()}"

                complex_data = self._extract_with_vision(
                    file_content=file_content,
                    filename=filename,
                    document_category="complex_document",
                    system_prompt=(
                        "You are an expert at layout-aware OCR for complex documents. "
                        "Extract the document layout into ordered blocks and capture tables and figures. "
                        "Rules:\n"
                        "- Preserve reading order.\n"
                        "- For text blocks, return the verbatim text.\n"
                        "- For tables, return headers and rows exactly as shown.\n"
                        "- For figures/graphs, provide a short description and list only values explicitly shown. "
                        "Do not infer missing values.\n"
                        "- Use normalized bounding boxes (0-1) only when confident; otherwise omit.\n"
                        "- Keep summary_markdown concise and factual.\n"
                        "- Do not invent section titles or analysis; focus on extraction only.\n"
                    ),
                    user_prompt=(
                        "Extract layout blocks, tables, figures, and a concise markdown summary "
                        "from this document. Include any numeric values shown in graphs or diagrams."
                        f"{extra}"
                    ),
                    response_model=ComplexDocumentExtraction,
                    prefer_vision=True,
                )

                processing_time = int((time.time() - start_time) * 1000)

                # Fill top-level tables/figures from blocks if not provided.
                if getattr(complex_data, "tables", None) in (None, []):
                    complex_data.tables = [
                        block.table for block in complex_data.blocks if block.table is not None
                    ]
                if getattr(complex_data, "figures", None) in (None, []):
                    complex_data.figures = [
                        block.figure for block in complex_data.blocks if block.figure is not None
                    ]

                if hasattr(complex_data, "confidence_score"):
                    complex_data.confidence_score = 0.88
                if hasattr(complex_data, "processing_time_ms"):
                    complex_data.processing_time_ms = processing_time
                if hasattr(complex_data, "document_category"):
                    complex_data.document_category = "complex_document"

                # Second-pass analysis for sections, key fields, and report.
                try:
                    analysis_payload = self._build_complex_analysis_payload(complex_data)
                    analysis_prompt = (
                        "You are a technical document analyst. Use ONLY the provided JSON. "
                        "Do not infer missing values. When referencing data, cite block_id(s). "
                        "Provide:\n"
                        "- sections grouped by heading/flow with block_ids and page range\n"
                        "- key_fields (explicit key/value pairs only)\n"
                        "- table_insights and figure_insights based on visible values\n"
                        "- report_markdown as a complete report\n"
                        "If data is missing, leave the relevant list empty."
                    )
                    user_analysis_prompt = (
                        "Analyze the extracted layout JSON below.\n\n"
                        f"{json.dumps(analysis_payload, ensure_ascii=True)}"
                    )
                    if additional_instructions and additional_instructions.strip():
                        user_analysis_prompt += (
                            "\n\nAdditional instructions:\n"
                            f"{additional_instructions.strip()}"
                        )
                    analysis = self._extract_with_text(
                        document_category="complex_document_analysis",
                        system_prompt=analysis_prompt,
                        user_prompt=user_analysis_prompt,
                        response_model=ComplexDocumentAnalysis,
                    )
                    complex_data.sections = analysis.sections
                    complex_data.key_fields = analysis.key_fields
                    complex_data.table_insights = analysis.table_insights
                    complex_data.figure_insights = analysis.figure_insights
                    complex_data.report_markdown = analysis.report_markdown
                except Exception as exc:
                    logfire.warn(
                        "Complex document analysis step failed; returning layout-only extraction.",
                        filename=filename,
                        error=str(exc),
                    )

                return complex_data

            except Exception as exc:
                logfire.error(
                    "Failed to extract complex document",
                    filename=filename,
                    error=str(exc),
                )
                raise
