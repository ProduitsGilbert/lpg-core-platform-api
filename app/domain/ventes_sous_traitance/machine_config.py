from __future__ import annotations

from pathlib import Path
from typing import Any
import json

import yaml


DEFAULT_MACHINE_CONFIG_PATH = Path("config/ventes_sous_traitance_machine_groups.yml")


def load_machine_groups_config() -> dict[str, Any]:
    """
    Load machine group config from disk.

    Returns an empty structure when no config file exists so the pipeline can
    still run with reduced confidence.
    """
    if not DEFAULT_MACHINE_CONFIG_PATH.exists():
        return {"version": 1, "units": {"length": "mm", "weight": "kg", "time": "min"}, "machine_groups": []}

    with DEFAULT_MACHINE_CONFIG_PATH.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    if not isinstance(raw, dict):
        return {"version": 1, "units": {"length": "mm", "weight": "kg", "time": "min"}, "machine_groups": []}
    raw.setdefault("version", 1)
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
                "setup_model": group.get("setup_model", {}),
                "time_model": group.get("time_model", {}),
            }
        )
    return json.dumps({"version": config.get("version", 1), "machine_groups": groups}, ensure_ascii=True)

