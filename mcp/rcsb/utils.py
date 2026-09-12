"""Input validation and provenance helpers for RCSB PDB."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError


PDB_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{4}$")


def require_pdb_id(args: JsonObject, name: str = "pdb_id") -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    pdb_id = value.strip().upper()
    if PDB_ID_PATTERN.fullmatch(pdb_id) is None:
        raise McpError(-32602, f"{name} must be a 4-character PDB entry ID")
    return pdb_id


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


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "rcsb_pdb",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def first_value(values: Any) -> Any:
    if isinstance(values, list) and values:
        return values[0]
    return ""

