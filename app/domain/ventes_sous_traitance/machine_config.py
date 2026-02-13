from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import yaml
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.cedule_repository import get_cedule_engine


DEFAULT_MACHINE_CONFIG_PATH = Path("config/ventes_sous_traitance_machine_groups.yml")


def load_machine_groups_config() -> dict[str, Any]:
    """
    Load machine group config from Cedule SQL (preferred) or disk fallback.

    Returns a minimal structure when no source is available.
    """
    db_config = _load_machine_groups_from_db()
    if db_config is not None:
        return db_config
    return _load_machine_groups_from_yaml()


def _load_machine_groups_from_db() -> dict[str, Any] | None:
    engine = get_cedule_engine()
    if not engine:
        return None

    groups_stmt = text(
        """
        SELECT [machine_group_id], [name], [process_families_json], [config_json], [updated_at]
        FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_groups]
        ORDER BY [name]
        """
    )
    machines_stmt = text(
        """
        SELECT
            [machine_id], [machine_code], [machine_name], [machine_group_id], [is_active],
            [default_setup_time_min], [default_runtime_min],
            [envelope_x_mm], [envelope_y_mm], [envelope_z_mm], [max_part_weight_kg], [notes]
        FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machines]
        WHERE [is_active] = 1
        ORDER BY [machine_name]
        """
    )
    capabilities_stmt = text(
        """
        SELECT [machine_id], [capability_code], [capability_value], [numeric_value], [bool_value], [unit]
        FROM [Cedule].[dbo].[40_VENTES_SOUSTRAITANCE_machine_capabilities]
        ORDER BY [capability_code]
        """
    )
    try:
        with engine.connect() as conn:
            group_rows = conn.execute(groups_stmt).mappings().all()
            machine_rows = conn.execute(machines_stmt).mappings().all()
            capability_rows = conn.execute(capabilities_stmt).mappings().all()
    except SQLAlchemyError:
        return None

    if not group_rows and not machine_rows:
        return None

    capabilities_by_machine: dict[str, dict[str, Any]] = {}
    for row in capability_rows:
        machine_id = str(row.get("machine_id") or "")
        if not machine_id:
            continue
        code = str(row.get("capability_code") or "").strip().lower()
        if not code:
            continue
        value: Any = row.get("capability_value")
        if value is None and row.get("numeric_value") is not None:
            value = float(row.get("numeric_value"))
        if value is None and row.get("bool_value") is not None:
            value = bool(row.get("bool_value"))
        capabilities_by_machine.setdefault(machine_id, {})[code] = value

    groups: dict[str, dict[str, Any]] = {}
    for row in group_rows:
        group_id = str(row.get("machine_group_id") or "").strip()
        if not group_id:
            continue
        process_families = _safe_json_loads(row.get("process_families_json"), default=[])
        config_json = _safe_json_loads(row.get("config_json"), default={})
        groups[group_id] = {
            "id": group_id,
            "name": str(row.get("name") or group_id),
            "process_families": process_families if isinstance(process_families, list) else [],
            "envelope_mm": None,
            "max_part_weight_kg": None,
            "capabilities": {},
            "limits": config_json.get("limits") if isinstance(config_json, dict) else {},
            "quality": config_json.get("quality") if isinstance(config_json, dict) else {},
            "materials": config_json.get("materials") if isinstance(config_json, dict) else {},
            "time_defaults": {},
            "setup_model": config_json.get("setup_model") if isinstance(config_json, dict) else {},
            "time_model": config_json.get("time_model") if isinstance(config_json, dict) else {},
            "machine_defaults": [],
            "machines": [],
        }

    for row in machine_rows:
        group_id = str(row.get("machine_group_id") or "").strip()
        if not group_id:
            continue
        if group_id not in groups:
            groups[group_id] = {
                "id": group_id,
                "name": group_id.replace("_", " ").title(),
                "process_families": [],
                "envelope_mm": None,
                "max_part_weight_kg": None,
                "capabilities": {},
                "limits": {},
                "quality": {},
                "materials": {},
                "time_defaults": {},
                "setup_model": {},
                "time_model": {},
                "machine_defaults": [],
                "machines": [],
            }
        machine_id = str(row.get("machine_id"))
        machine_payload = {
            "machine_id": machine_id,
            "machine_code": row.get("machine_code"),
            "machine_name": row.get("machine_name"),
            "default_setup_time_min": float(row.get("default_setup_time_min") or 0),
            "default_runtime_min": float(row.get("default_runtime_min") or 0),
            "envelope_mm": {
                "x": float(row.get("envelope_x_mm")) if row.get("envelope_x_mm") is not None else None,
                "y": float(row.get("envelope_y_mm")) if row.get("envelope_y_mm") is not None else None,
                "z": float(row.get("envelope_z_mm")) if row.get("envelope_z_mm") is not None else None,
            },
            "max_part_weight_kg": float(row.get("max_part_weight_kg")) if row.get("max_part_weight_kg") is not None else None,
            "capabilities": capabilities_by_machine.get(machine_id, {}),
            "notes": row.get("notes"),
        }
        groups[group_id]["machines"].append(machine_payload)
        groups[group_id]["machine_defaults"].append(
            {
                "machine_code": row.get("machine_code"),
                "default_setup_time_min": machine_payload["default_setup_time_min"],
                "default_runtime_min": machine_payload["default_runtime_min"],
            }
        )

        group_envelope = groups[group_id].get("envelope_mm")
        machine_envelope = machine_payload["envelope_mm"]
        if not group_envelope or not isinstance(group_envelope, dict):
            groups[group_id]["envelope_mm"] = machine_envelope
        else:
            groups[group_id]["envelope_mm"] = {
                axis: max(
                    float(group_envelope.get(axis) or 0),
                    float(machine_envelope.get(axis) or 0),
                )
                for axis in ("x", "y", "z")
            }

        max_weight = machine_payload.get("max_part_weight_kg")
        if max_weight is not None:
            current = groups[group_id].get("max_part_weight_kg")
            groups[group_id]["max_part_weight_kg"] = max(float(current or 0), float(max_weight))

    for group in groups.values():
        defaults = group.get("machine_defaults", [])
        if defaults:
            setup_avg = sum(float(item.get("default_setup_time_min") or 0) for item in defaults) / len(defaults)
            runtime_avg = sum(float(item.get("default_runtime_min") or 0) for item in defaults) / len(defaults)
            group["time_defaults"] = {
                "default_setup_time_min": round(setup_avg, 2),
                "default_runtime_min": round(runtime_avg, 2),
            }

    return {
        "version": 2,
        "source": "sql",
        "units": {"length": "mm", "weight": "kg", "time": "min"},
        "machine_groups": list(groups.values()),
    }


def _safe_json_loads(value: Any, default: Any) -> Any:
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(str(value))
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _load_machine_groups_from_yaml() -> dict[str, Any]:
    if not DEFAULT_MACHINE_CONFIG_PATH.exists():
        return {"version": 1, "units": {"length": "mm", "weight": "kg", "time": "min"}, "machine_groups": []}

    with DEFAULT_MACHINE_CONFIG_PATH.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        return {"version": 1, "units": {"length": "mm", "weight": "kg", "time": "min"}, "machine_groups": []}
    raw.setdefault("version", 1)
    raw.setdefault("source", "yaml")
    raw.setdefault("units", {"length": "mm", "weight": "kg", "time": "min"})
    raw.setdefault("machine_groups", [])
    return raw


def compact_machine_groups_context(config: dict[str, Any]) -> str:
    """
    Build a compact JSON string with only routing-relevant fields for prompts.
    """
    groups: list[dict[str, Any]] = []
    for group in config.get("machine_groups", []) or []:
        if not isinstance(group, dict):
            continue
        groups.append(
            {
                "id": group.get("id"),
                "name": group.get("name"),
                "process_families": group.get("process_families", []),
                "envelope_mm": group.get("envelope_mm"),
                "max_part_weight_kg": group.get("max_part_weight_kg"),
                "capabilities": group.get("capabilities", {}),
                "limits": group.get("limits", {}),
                "quality": group.get("quality", {}),
                "materials": group.get("materials", {}),
                "time_defaults": group.get("time_defaults", {}),
                "machine_defaults": group.get("machine_defaults", []),
                "machines": group.get("machines", []),
                "setup_model": group.get("setup_model", {}),
                "time_model": group.get("time_model", {}),
            }
        )
    return json.dumps({"version": config.get("version", 1), "machine_groups": groups}, ensure_ascii=True)
