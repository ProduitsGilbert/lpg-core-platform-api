"""
Helpers for building dynamic OCR extraction models from JSON schema.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, Optional, Tuple, Type, Union, Literal

from pydantic import BaseModel, Field, create_model


_JSON_PRIMITIVES = {"string", "number", "integer", "boolean", "object", "array", "null"}


def build_pydantic_model_from_schema(
    schema: Dict[str, Any],
    *,
    model_name: str = "CustomExtraction",
) -> Type[BaseModel]:
    """
    Build a Pydantic model from a JSON schema (subset).

    Supported schema:
    - type: object, with properties and optional required
    - property types: string, number, integer, boolean, object, array
    - string formats: date, date-time
    - enum: list of values (string/number/bool)
    - array items: required, supports nested objects
    - nullable: type can include "null"
    """
    if not isinstance(schema, dict):
        raise ValueError("output_schema must be a JSON object")
    return _build_object_model(schema, model_name=model_name, model_cache={})


def _build_object_model(
    schema: Dict[str, Any],
    *,
    model_name: str,
    model_cache: Dict[str, Type[BaseModel]],
) -> Type[BaseModel]:
    schema_type = schema.get("type")
    if schema_type not in (None, "object"):
        raise ValueError("Root output_schema must be a JSON object schema")

    properties: Dict[str, Any] = schema.get("properties") or {}
    if not isinstance(properties, dict) or not properties:
        raise ValueError("output_schema.properties must be a non-empty object")

    required_fields_raw = schema.get("required") or []
    if not isinstance(required_fields_raw, list):
        raise ValueError("output_schema.required must be an array of field names")
    required_fields = set(required_fields_raw)

    fields: Dict[str, Tuple[Any, Any]] = {}
    for field_name, field_schema in properties.items():
        if not isinstance(field_schema, dict):
            raise ValueError(f"Schema for field '{field_name}' must be an object")

        field_type, allow_null = _build_field_type(
            field_schema,
            model_name=f"{model_name}_{_title_case(field_name)}",
            model_cache=model_cache,
        )

        is_required = field_name in required_fields
        if allow_null or not is_required:
            field_type = Optional[field_type]

        description = field_schema.get("description")
        default = field_schema.get("default", None if not is_required else ...)
        field_def = Field(default=default, description=description)
        fields[field_name] = (field_type, field_def)

    model = create_model(model_name, **fields)
    model_cache[model_name] = model
    return model


def _build_field_type(
    schema: Dict[str, Any],
    *,
    model_name: str,
    model_cache: Dict[str, Type[BaseModel]],
) -> tuple[Any, bool]:
    schema_type = schema.get("type")
    types = _normalize_types(schema_type)
    allow_null = "null" in types
    types = [t for t in types if t != "null"]

    if "enum" in schema:
        enum_values = schema.get("enum")
        if not isinstance(enum_values, list) or not enum_values:
            raise ValueError(f"enum for {model_name} must be a non-empty array")
        return (Literal[tuple(enum_values)], allow_null)

    if not types:
        return (Any, allow_null)

    if len(types) > 1:
        union_types: list[Any] = []
        for entry in types:
            union_types.append(
                _map_json_type(entry, schema, model_name=model_name, model_cache=model_cache)
            )
        return (Union[tuple(union_types)], allow_null)

    return (
        _map_json_type(types[0], schema, model_name=model_name, model_cache=model_cache),
        allow_null,
    )


def _map_json_type(
    schema_type: str,
    schema: Dict[str, Any],
    *,
    model_name: str,
    model_cache: Dict[str, Type[BaseModel]],
) -> Any:
    if schema_type not in _JSON_PRIMITIVES:
        raise ValueError(f"Unsupported schema type '{schema_type}' in {model_name}")

    if schema_type == "string":
        fmt = schema.get("format")
        if fmt == "date":
            return date
        if fmt in ("date-time", "datetime"):
            return datetime
        return str

    if schema_type == "integer":
        return int
    if schema_type == "number":
        return Decimal
    if schema_type == "boolean":
        return bool

    if schema_type == "array":
        items_schema = schema.get("items")
        if not isinstance(items_schema, dict):
            raise ValueError(f"Array schema for {model_name} must include 'items'")
        item_type, allow_null = _build_field_type(
            items_schema,
            model_name=f"{model_name}_Item",
            model_cache=model_cache,
        )
        if allow_null:
            item_type = Optional[item_type]
        return list[item_type]

    if schema_type == "object":
        if model_name in model_cache:
            return model_cache[model_name]
        return _build_object_model(schema, model_name=model_name, model_cache=model_cache)

    return Any


def _normalize_types(schema_type: Any) -> list[str]:
    if schema_type is None:
        return ["object"]
    if isinstance(schema_type, str):
        return [schema_type]
    if isinstance(schema_type, list):
        types = [entry for entry in schema_type if isinstance(entry, str)]
        if not types:
            raise ValueError("Schema type list must include string entries")
        return types
    raise ValueError("Schema type must be a string or array of strings")


def _title_case(value: str) -> str:
    return "".join(part.capitalize() for part in value.replace("-", "_").split("_") if part)
