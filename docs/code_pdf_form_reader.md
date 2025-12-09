"""
Technical Sheet Reading Module
Extracts text, form fields, and provides vision fallback for technical drawings.
"""

import base64
import io
import json
import tempfile
from pathlib import Path
from typing import Any, Dict, Optional

import httpx
from pypdf import PdfReader

try:
    from fillpdf import fillpdfs
except ImportError:
    fillpdfs = None

# Configuration (adapt to your environment)
ERP_API_BASE_URL = "http://your-erp-api-url/api/v1"  # Set via environment
FILE_SHARE_SERVER = "your-server"
FILE_SHARE_SHARE = "share-name"

def _decode_base64_payload(encoded: str) -> bytes:
    """Decode base64 payload, handling data URLs."""
    cleaned = (encoded or "").strip()
    if not cleaned:
        raise ValueError("Base64 content is required.")
    if cleaned.lower().startswith("data:"):
        _, _, remainder = cleaned.partition(",")
        cleaned = remainder or ""
    try:
        return base64.b64decode(cleaned)
    except Exception as exc:
        raise ValueError(f"Invalid base64 content: {exc}") from exc

def _normalize_file_share_path(path: str) -> str:
    """Convert UNC or absolute paths to relative share paths."""
    cleaned = path.replace("\\", "/").strip("/")
    if not cleaned:
        return ""
    parts = cleaned.split("/")
    server = (FILE_SHARE_SERVER or "").lower().strip("\\/")
    share = (FILE_SHARE_SHARE or "").strip("\\/")
    short_server = server.split(".")[0] if server else ""

    def drop_prefix(parts: list[str]) -> list[str]:
        if len(parts) >= 2 and parts[0].lower() in {server, short_server} and parts[1].lower() == share.lower():
            return parts[2:]
        if len(parts) >= 1 and parts[0].lower() in {server, short_server}:
            return parts[1:]
        if len(parts) >= 1 and parts[0].lower() == share.lower():
            return parts[1:]
        return parts

    normalized_parts = drop_prefix(parts)
    return "/".join([part for part in normalized_parts if part not in {"", ".", ".."}])

def _guess_mime_type(filename: str, default: str = "application/octet-stream") -> str:
    """Guess MIME type from filename extension."""
    ext = Path(filename or "").suffix.lower()
    mapping = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }
    return mapping.get(ext, default)

def _build_data_url(content: bytes, mime_type: str) -> str:
    """Convert bytes to base64 data URL."""
    return f"data:{mime_type};base64,{base64.b64encode(content).decode('ascii')}"

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

def _load_file_bytes(
    *,
    base64_payload: Optional[str],
    file_share_path: Optional[str],
    # Note: In your API, you'll need to implement file share reading
) -> bytes:
    """Load PDF bytes from various sources."""
    if base64_payload:
        return _decode_base64_payload(base64_payload)
    if file_share_path:
        # Implement your file share reading logic here
        # For example: return file_share_connector.read_binary(file_share_path)
        raise NotImplementedError("File share reading not implemented in this export")
    raise ValueError("Provide either base64 content or a file_share_path.")

def read_technical_sheet(
    file_base64: str = "",
    file_share_path: str = "",
    part_number: str = "",
    erp_api_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Read technical sheet content.
    
    Returns dict with success, data, error keys.
    """
    pdf_bytes: Optional[bytes] = None
    
    try:
        if file_base64 or file_share_path:
            pdf_bytes = _load_file_bytes(
                base64_payload=file_base64,
                file_share_path=_normalize_file_share_path(file_share_path),
            )
        elif part_number:
            url = f"{erp_api_url or ERP_API_BASE_URL}/documents/file-share/items/{part_number}/pdf"
            with httpx.Client(timeout=30) as client:
                resp = client.get(url)
                resp.raise_for_status()
                pdf_bytes = resp.content
        else:
            return {
                "success": False,
                "data": None,
                "error": "Provide a PDF (base64 or file path) or a part_number to fetch via ERP."
            }
        
        if not pdf_bytes:
            return {
                "success": False,
                "data": None,
                "error": "No PDF content was loaded."
            }

        # 1. Extract form fields
        fields_summary = "Fillpdf not installed."
        fields_json = {}
        if fillpdfs:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(pdf_bytes)
                tmp.flush()
                try:
                    fields = fillpdfs.get_form_fields(tmp.name)
                    if fields:
                        fields_summary = _flatten_fields(fields)
                        fields_json = fields
                    else:
                        fields_summary = "No form fields detected."
                except Exception as exc:
                    fields_summary = f"Failed to read form fields: {exc}"

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
        if not text_content.strip() and "No form fields" in fields_summary:
            try:
                reader = PdfReader(io.BytesIO(pdf_bytes))
                if len(reader.pages) > 0:
                    page = reader.pages[0]
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
                            
                            data_url = _build_data_url(image_bytes, mime_type)
                            
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
        return {
            "success": False,
            "data": None,
            "error": str(exc)
        }