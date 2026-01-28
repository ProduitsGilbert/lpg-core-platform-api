"""Technical sheet extraction and filling utilities."""

from __future__ import annotations

import io
import logging
import re
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pdfrw
from fillpdf import fillpdfs
from pypdf import PdfReader

from app.domain.documents.file_share_service import FileShareService

logger = logging.getLogger(__name__)


class TechnicalSheetService:
    """Service for reading and filling technical sheet PDFs."""

    def __init__(
        self,
        *,
        file_share_service: Optional[FileShareService] = None,
        template_root: Optional[Path] = None,
    ) -> None:
        self._file_share_service = file_share_service or FileShareService()
        repo_root = template_root or Path(__file__).resolve().parents[3]
        self._templates: Dict[str, Path] = {
            "fiche-produit": repo_root / "docs" / "FicheProduit.pdf",
        }

    async def read_fiche_technique(self, item_no: str) -> Dict[str, Any]:
        """Fetch a technical sheet PDF and return extracted fields."""
        try:
            pdf_data = await self._file_share_service.get_item_pdf(item_no)
            if not pdf_data:
                return {
                    "success": False,
                    "error": f"PDF file not found for item '{item_no}'",
                    "error_code": "PDF_NOT_FOUND",
                }

            fields, field_map, source = self._extract_fields_from_pdf(
                pdf_bytes=pdf_data["content"],
            )

            if not fields:
                return {
                    "success": False,
                    "error": "No extractable fields found in the PDF",
                    "error_code": "NO_FIELDS",
                }

            return {
                "success": True,
                "data": {
                    "item_no": item_no,
                    "filename": pdf_data["filename"],
                    "source": source,
                    "field_count": len(fields),
                    "fields": fields,
                    "field_map": field_map,
                },
            }
        except Exception as exc:
            logger.error("Failed to read technical sheet", exc_info=exc)
            return {
                "success": False,
                "error": str(exc),
                "error_code": "PROCESSING_ERROR",
            }

    async def fill_fiche_technique(
        self,
        *,
        fields: Dict[str, Any],
        item_no: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Fill a technical sheet template with provided fields."""
        if not fields:
            return {
                "success": False,
                "error": "Fields payload is required",
                "error_code": "NO_FIELDS",
            }

        try:
            pdf_bytes, filename = await self._load_template(item_no=item_no, template_id=template_id)
        except FileNotFoundError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_code": "TEMPLATE_NOT_FOUND",
            }
        except ValueError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_code": "TEMPLATE_SOURCE_REQUIRED",
            }
        except Exception as exc:
            logger.error("Failed to load template", exc_info=exc)
            return {
                "success": False,
                "error": str(exc),
                "error_code": "PROCESSING_ERROR",
            }

    async def get_template_fields(
        self,
        *,
        item_no: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return suggested fields and options for a technical sheet template."""
        try:
            pdf_bytes, filename = await self._load_template(
                item_no=item_no,
                template_id=template_id,
            )
        except FileNotFoundError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_code": "TEMPLATE_NOT_FOUND",
            }
        except ValueError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_code": "TEMPLATE_SOURCE_REQUIRED",
            }
        except Exception as exc:
            logger.error("Failed to load template", exc_info=exc)
            return {
                "success": False,
                "error": str(exc),
                "error_code": "PROCESSING_ERROR",
            }

        try:
            template_fields = self._extract_form_fields(pdf_bytes)
            field_options = self._extract_form_options(pdf_bytes)
            normalized_fields, field_map = self._normalize_fields(template_fields)

            options_map: Dict[str, list[str]] = {}
            for raw_key, options in field_options.items():
                normalized_key = self._normalize_field_key(raw_key)
                if not normalized_key:
                    continue
                options_map[normalized_key] = self._clean_options(options)

            suggested_fields = sorted(normalized_fields.keys(), key=str.lower)
            fields_detail = []
            for key in suggested_fields:
                detail = {
                    "key": key,
                    "raw_key": field_map.get(key, key),
                    "input_type": "select" if key in options_map else "text",
                }
                if key in options_map:
                    detail["options"] = options_map[key]
                fields_detail.append(detail)

            return {
                "success": True,
                "data": {
                    "template_id": template_id or "fiche-produit",
                    "item_no": item_no,
                    "filename": filename,
                    "suggested_fields": suggested_fields,
                    "field_map": field_map,
                    "options": options_map,
                    "fields": fields_detail,
                },
            }
        except Exception as exc:
            logger.error("Failed to read template fields", exc_info=exc)
            return {
                "success": False,
                "error": str(exc),
                "error_code": "PROCESSING_ERROR",
            }

        try:
            template_fields = self._extract_form_fields(pdf_bytes)
            field_options = self._extract_form_options(pdf_bytes)
            mapped_fields, invalid_options = self._map_fill_fields(
                fields,
                template_fields,
                field_options,
            )
            if invalid_options:
                return {
                    "success": False,
                    "error": "One or more fields have invalid option values",
                    "error_code": "INVALID_OPTION",
                    "details": invalid_options,
                }
            if not mapped_fields:
                return {
                    "success": False,
                    "error": "No matching fields found for the template",
                    "error_code": "NO_FIELDS",
                }

            with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as input_tmp, \
                tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as output_tmp:
                input_tmp.write(pdf_bytes)
                input_tmp.flush()

                fillpdfs.write_fillable_pdf(
                    input_tmp.name,
                    output_tmp.name,
                    mapped_fields,
                    flatten=False,
                )

                output_tmp.seek(0)
                filled_bytes = output_tmp.read()

            if not filled_bytes:
                return {
                    "success": False,
                    "error": "Generated PDF is empty",
                    "error_code": "EMPTY_PDF",
                }

            return {
                "success": True,
                "content": filled_bytes,
                "filename": filename,
                "size": len(filled_bytes),
                "content_type": "application/pdf",
            }
        except Exception as exc:
            logger.error("Failed to fill technical sheet", exc_info=exc)
            return {
                "success": False,
                "error": str(exc),
                "error_code": "PROCESSING_ERROR",
            }

    async def _load_template(
        self,
        *,
        item_no: Optional[str],
        template_id: Optional[str],
    ) -> Tuple[bytes, str]:
        if item_no:
            pdf_data = await self._file_share_service.get_item_pdf(item_no)
            if not pdf_data:
                raise FileNotFoundError(f"PDF file not found for item '{item_no}'")
            return pdf_data["content"], pdf_data["filename"]

        selected_id = template_id or "fiche-produit"
        template_path = self._templates.get(selected_id)
        if not template_path:
            raise FileNotFoundError(f"Template '{selected_id}' not found")
        if not template_path.exists():
            raise FileNotFoundError(f"Template file missing at '{template_path}'")

        return template_path.read_bytes(), template_path.name

    def _extract_fields_from_pdf(self, *, pdf_bytes: bytes) -> Tuple[Dict[str, Any], Dict[str, str], str]:
        fields = self._extract_form_fields(pdf_bytes)
        if fields:
            normalized_fields, field_map = self._normalize_fields(fields)
            if normalized_fields:
                return normalized_fields, field_map, "form_fields"

        text_fields = self._extract_text_fields(pdf_bytes)
        normalized_text_fields, field_map = self._normalize_fields(text_fields)
        return normalized_text_fields, field_map, "text_extraction"

    @staticmethod
    def _extract_form_fields(pdf_bytes: bytes) -> Dict[str, Any]:
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            try:
                return fillpdfs.get_form_fields(tmp.name) or {}
            except Exception as exc:
                logger.warning("Failed to read form fields: %s", exc)
                return {}

    @staticmethod
    def _extract_form_options(pdf_bytes: bytes) -> Dict[str, list[str]]:
        options_by_field: Dict[str, list[str]] = {}
        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            try:
                pdf = pdfrw.PdfReader(tmp.name)
            except Exception as exc:
                logger.warning("Failed to read PDF options: %s", exc)
                return options_by_field

        for page in pdf.pages:
            annotations = page[fillpdfs.ANNOT_KEY]
            if not annotations:
                continue
            for annotation in annotations:
                if annotation[fillpdfs.SUBTYPE_KEY] != fillpdfs.WIDGET_SUBTYPE_KEY:
                    continue
                field_name = None
                if annotation[fillpdfs.ANNOT_FIELD_KEY]:
                    field_name = annotation[fillpdfs.ANNOT_FIELD_KEY][1:-1]
                elif annotation.get("/AP"):
                    if not annotation.get("/T"):
                        annotation = annotation.get("/Parent")
                    if annotation and annotation.get("/T"):
                        field_name = annotation["/T"].to_unicode()
                if not field_name:
                    continue
                if annotation[fillpdfs.ANNOT_FORM_options]:
                    options = annotation[fillpdfs.ANNOT_FORM_options]
                    decoded: list[str] = []
                    for option in options:
                        try:
                            decoded.append(pdfrw.objects.PdfString.decode(option))
                        except Exception:
                            decoded.append(str(option))
                    options_by_field[field_name] = decoded
        return options_by_field

    def _extract_text_fields(self, pdf_bytes: bytes) -> Dict[str, Any]:
        text = self._extract_text(pdf_bytes, max_pages=5)
        if not text:
            return {}

        fields: Dict[str, Any] = {}
        for line in text.splitlines():
            if ":" not in line:
                continue
            raw_key, raw_value = line.split(":", 1)
            key = self._normalize_field_key(raw_key)
            value = self._clean_text_value(raw_value)
            normalized_value = self._normalize_field_value(key, value)
            if normalized_value not in ("", None):
                fields[key] = normalized_value
        return fields

    @staticmethod
    def _extract_text(pdf_bytes: bytes, *, max_pages: int = 5) -> str:
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
        except Exception as exc:
            logger.warning("Failed to open PDF for text extraction: %s", exc)
            return ""

        parts: list[str] = []
        for index, page in enumerate(reader.pages):
            if index >= max_pages:
                break
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            if text.strip():
                parts.append(text)
        return "\n".join(parts)

    def _normalize_fields(self, fields: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, str]]:
        normalized: Dict[str, Any] = {}
        field_map: Dict[str, str] = {}
        for raw_key, raw_value in fields.items():
            key = self._normalize_field_key(raw_key)
            value = self._normalize_field_value(key, raw_value)
            if value in ("", None):
                continue
            normalized[key] = value
            field_map[key] = str(raw_key)
        return normalized, field_map

    @staticmethod
    def _normalize_field_key(raw_key: Any) -> str:
        key = str(raw_key or "").strip()
        if not key:
            return ""

        cleaned = key
        if "\\000" in cleaned:
            cleaned = cleaned.replace("\\000", "\x00")
        if "\x00" in cleaned or cleaned.startswith("þÿ"):
            try:
                cleaned = cleaned.encode("latin-1").decode("utf-16")
            except Exception:
                pass

        return " ".join(cleaned.split())

    def _normalize_field_value(self, key: str, raw_value: Any) -> Any:
        value = self._coerce_to_string(raw_value)
        value = value.replace("\x00", "").strip()
        if not value:
            return ""
        lowered = value.lower()
        if lowered in {"off", "false", "none"}:
            return ""
        if self._is_price_field(key):
            parsed = self._parse_price(value)
            return parsed if parsed is not None else value
        return value

    @staticmethod
    def _coerce_to_string(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, dict):
            if "value" in value and len(value) == 1:
                return str(value["value"])
            return "; ".join(f"{k}: {v}" for k, v in value.items())
        if isinstance(value, list):
            return "; ".join(str(item) for item in value)
        return str(value)

    @staticmethod
    def _is_price_field(key: str) -> bool:
        lowered = (key or "").lower()
        return "prix" in lowered or "price" in lowered

    @staticmethod
    def _parse_price(raw: str) -> Optional[float]:
        cleaned = re.sub(r"[^0-9,.-]", "", raw)
        if not cleaned:
            return None
        if cleaned.count(",") and cleaned.count("."):
            cleaned = cleaned.replace(",", "")
        elif cleaned.count(",") == 1 and cleaned.count(".") == 0:
            integer, fractional = cleaned.split(",", 1)
            if len(fractional) == 3:
                cleaned = integer + fractional
            else:
                cleaned = integer + "." + fractional
        try:
            return float(cleaned)
        except ValueError:
            return None

    @staticmethod
    def _clean_text_value(value: str) -> str:
        cleaned = re.sub(r"_+", "", value)
        return " ".join(cleaned.strip().split())

    def _map_fill_fields(
        self,
        fields: Dict[str, Any],
        template_fields: Dict[str, Any],
        field_options: Dict[str, list[str]],
    ) -> Tuple[Dict[str, Any], list[Dict[str, Any]]]:
        if not fields:
            return {}, []
        field_map = self._build_field_map(template_fields)
        mapped: Dict[str, Any] = {}
        invalid_options: list[Dict[str, Any]] = []
        for input_key, raw_value in fields.items():
            normalized_key = self._normalize_field_key(input_key)
            raw_key = input_key if input_key in template_fields else field_map.get(normalized_key)
            if not raw_key:
                continue
            value = self._coerce_to_string(raw_value).strip()
            if value:
                if raw_key in field_options:
                    selected = self._select_option(value, field_options[raw_key])
                    if selected is None:
                        invalid_options.append(
                            {
                                "field": normalized_key or str(input_key),
                                "value": value,
                                "options": field_options[raw_key],
                            }
                        )
                        continue
                    value = selected
                mapped[raw_key] = value
        return mapped, invalid_options

    @staticmethod
    def _select_option(value: str, options: list[str]) -> Optional[str]:
        normalized_value = TechnicalSheetService._normalize_option_value(value)
        for option in options:
            if TechnicalSheetService._normalize_option_value(option) == normalized_value:
                return option
        return None

    @staticmethod
    def _normalize_option_value(value: str) -> str:
        return " ".join(str(value or "").strip().split()).casefold()

    @staticmethod
    def _clean_options(options: list[str]) -> list[str]:
        cleaned = []
        for option in options:
            value = " ".join(str(option or "").strip().split())
            if value and value not in cleaned:
                cleaned.append(value)
        return cleaned

    def _build_field_map(self, template_fields: Dict[str, Any]) -> Dict[str, str]:
        field_map: Dict[str, str] = {}
        for raw_key in template_fields.keys():
            normalized = self._normalize_field_key(raw_key)
            if normalized and normalized not in field_map:
                field_map[normalized] = str(raw_key)
        return field_map
