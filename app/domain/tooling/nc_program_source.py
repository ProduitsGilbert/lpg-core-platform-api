from __future__ import annotations

from typing import Any

from app.settings import settings


def _parse_csv(value: str | None) -> set[str]:
    if not value:
        return set()
    return {token.strip() for token in value.split(",") if token.strip()}


def normalize_tool_source(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"fastems1", "f1", "1"}:
        return "fastems1"
    if normalized in {"fastems2", "f2", "2"}:
        return "fastems2"
    return None


def resolve_tool_source(work_center_no: str, requested_source: str | None = None) -> str:
    normalized = normalize_tool_source(requested_source)
    if normalized:
        return normalized
    if str(work_center_no).strip() in _parse_csv(settings.tooling_fastems2_work_centers):
        return "fastems2"
    return "fastems1"


def nc_program_base_url_for_source(tool_source: str) -> str | None:
    normalized = normalize_tool_source(tool_source) or "fastems1"
    if normalized == "fastems2":
        return settings.fastems2_nc_program_tool_base_url or settings.fastems1_nc_program_tool_base_url
    return settings.fastems1_nc_program_tool_base_url


def get_tool_id(tool: dict[str, Any]) -> str | None:
    value = tool.get("TOOL_ID") or tool.get("toolId") or tool.get("ToolCode")
    text = str(value or "").strip()
    return text or None


def get_tool_use_time_value(tool: dict[str, Any]) -> Any:
    return tool.get("USE_TIME") or tool.get("useTime") or tool.get("Usage")


def get_tool_description(tool: dict[str, Any]) -> str | None:
    value = tool.get("DESCRIPTION") or tool.get("description") or tool.get("Description")
    text = str(value or "").strip()
    return text or None
