"""Input validation and provenance helpers for Open Targets."""

from __future__ import annotations

import time
from typing import Any

from .constants import DEFAULT_ENTITY_NAMES, JsonObject
from .errors import McpError


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def optional_bool(args: JsonObject, name: str, *, default: bool) -> bool:
    value = args.get(name, default)
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    raise McpError(-32602, f"{name} must be a boolean")


def optional_int(
    args: JsonObject,
    name: str,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    value = args.get(name, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise McpError(-32602, f"{name} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise McpError(-32602, f"{name} must be between {minimum} and {maximum}")
    return parsed


def optional_entity_names(args: JsonObject) -> list[str]:
    value = args.get("entity_names")
    if value is None:
        return list(DEFAULT_ENTITY_NAMES)
    if not isinstance(value, list):
        raise McpError(-32602, "entity_names must be a list of strings")
    allowed = set(DEFAULT_ENTITY_NAMES)
    names: list[str] = []
    for item in value:
        if not isinstance(item, str) or item.strip() not in allowed:
            raise McpError(-32602, "entity_names may only include target and disease")
        name = item.strip()
        if name not in names:
            names.append(name)
    if not names:
        raise McpError(-32602, "entity_names must include at least one entity")
    return names


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def source_info(operation: str, variables: JsonObject) -> JsonObject:
    return {
        "database": "opentargets",
        "endpoint": operation,
        "params": dict(variables),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
