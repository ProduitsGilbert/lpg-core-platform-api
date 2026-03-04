"""Client for external tool shortage prediction endpoint."""

from __future__ import annotations

from typing import Any, Optional
import logging

import httpx

from app.settings import settings

logger = logging.getLogger(__name__)


class ToolPredictionClient:
    """Thin async client around /predict/future-needs endpoint."""

    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        api_path: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ) -> None:
        self._base_url = (base_url or settings.tool_prediction_api_base_url or "").rstrip("/")
        self._api_path = (api_path or settings.tool_prediction_api_path or "/predict/future-needs").strip() or "/predict/future-needs"
        if not self._api_path.startswith("/"):
            self._api_path = f"/{self._api_path}"
        self._timeout = timeout_seconds or settings.tool_prediction_api_timeout_seconds

    @property
    def is_configured(self) -> bool:
        return bool(self._base_url)

    async def predict_rows(
        self,
        *,
        machine_center: str,
        rows: list[dict[str, Any]],
    ) -> dict[str, dict[str, Any]]:
        if not rows:
            return {}
        if not self._base_url:
            return self._heuristic_predictions(rows)

        payload = {
            "machine_center": machine_center,
            "rows": rows,
        }

        try:
            async with httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout, verify=False) as client:
                response = await client.post(self._api_path, json=payload)
                response.raise_for_status()
                body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            logger.warning(
                "Tool prediction endpoint call failed; falling back to heuristic scoring",
                extra={"machine_center": machine_center, "error": str(exc)},
            )
            return self._heuristic_predictions(rows)

        parsed = self._extract_predictions(body)
        if not parsed:
            logger.warning(
                "Tool prediction endpoint response had no usable rows; falling back to heuristic scoring",
                extra={"machine_center": machine_center},
            )
            return self._heuristic_predictions(rows)
        return parsed

    def _extract_predictions(self, body: Any) -> dict[str, dict[str, Any]]:
        if isinstance(body, list):
            rows = body
        elif isinstance(body, dict):
            candidate = body.get("predictions")
            if not isinstance(candidate, list):
                candidate = body.get("rows")
            if not isinstance(candidate, list):
                candidate = body.get("data")
            rows = candidate if isinstance(candidate, list) else []
        else:
            rows = []

        parsed: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            tool_id = _clean_tool_id(row.get("tool_id"))
            if not tool_id:
                continue
            probability = _pick_probability(row)
            label = _pick_label(row, probability)
            parsed[tool_id] = {
                "shortage_probability": probability,
                "shortage_label": label,
                "raw": row,
            }
        return parsed

    def _heuristic_predictions(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        predictions: dict[str, dict[str, Any]] = {}
        for row in rows:
            tool_id = _clean_tool_id(row.get("tool_id"))
            if not tool_id:
                continue
            future_24h = _safe_float(row.get("future_usage_minutes_24h"))
            remaining_life = max(_safe_float(row.get("total_remaining_life")), 0.0)
            available = _safe_int(row.get("available_instances"))

            if future_24h > 0 and available <= 0:
                probability = 1.0
            else:
                life_guard = remaining_life if remaining_life > 0 else 1.0
                probability = min(max(future_24h / life_guard, 0.0), 1.0)
            label = _label_for_probability(probability)

            predictions[tool_id] = {
                "shortage_probability": round(probability, 4),
                "shortage_label": label,
                "raw": {
                    "mode": "heuristic_fallback",
                    "future_usage_minutes_24h": future_24h,
                    "total_remaining_life": remaining_life,
                    "available_instances": available,
                },
            }
        return predictions


def _clean_tool_id(value: Any) -> Optional[str]:
    if value is None:
        return None
    cleaned = str(value).strip().upper()
    return cleaned or None


def _safe_float(value: Any) -> float:
    if value is None:
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _pick_probability(row: dict[str, Any]) -> float:
    for key in ("shortage_probability", "probability", "score", "risk_score"):
        value = row.get(key)
        if value is None:
            continue
        try:
            numeric = float(value)
            return min(max(numeric, 0.0), 1.0)
        except (TypeError, ValueError):
            continue
    return 0.0


def _pick_label(row: dict[str, Any], probability: float) -> str:
    for key in ("shortage_label", "prediction", "label", "risk_level"):
        value = row.get(key)
        if value is None:
            continue
        text_value = str(value).strip()
        if text_value:
            return text_value
    return _label_for_probability(probability)


def _label_for_probability(probability: float) -> str:
    if probability >= 0.7:
        return "HIGH"
    if probability >= 0.4:
        return "MEDIUM"
    return "LOW"
