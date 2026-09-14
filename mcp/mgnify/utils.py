"""Input validation and provenance helpers for MGnify."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError

MGYS_RE = re.compile(r"^MGYS\d+$", re.IGNORECASE)
SAMPLE_RE = re.compile(r"^[A-Z]+[A-Z0-9_.-]*\d+$", re.IGNORECASE)


def require_study_accession(args: JsonObject, name: str = "accession") -> str:
    value = require_non_empty_string(args, name).upper()
    if not MGYS_RE.match(value):
        raise McpError(-32602, f"{name} must look like MGYS00006862")
    return value


def require_sample_accession(args: JsonObject, name: str = "accession") -> str:
    value = require_non_empty_string(args, name)
    if not SAMPLE_RE.match(value):
        raise McpError(-32602, f"{name} must look like SRS10016989 or another MGnify sample accession")
    return value


def require_biome_id(args: JsonObject, name: str = "biome_id") -> str:
    value = require_non_empty_string(args, name)
    if not value.startswith("root"):
        raise McpError(-32602, f"{name} must start with root, for example root:Host-associated:Human")
    return value


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


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "mgnify",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

