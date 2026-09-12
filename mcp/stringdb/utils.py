"""Input validation and provenance helpers for STRING."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import MAX_IDENTIFIERS, JsonObject
from .errors import McpError


def require_identifiers(args: JsonObject, name: str = "identifiers") -> list[str]:
    value = args.get(name)
    values: list[str] = []
    if isinstance(value, str):
        values = split_identifier_text(value)
    elif isinstance(value, list):
        for item in value:
            if not isinstance(item, str):
                raise McpError(-32602, f"{name} entries must be strings")
            values.extend(split_identifier_text(item))
    else:
        raise McpError(-32602, f"{name} is required as a string or string array")

    identifiers = dedupe_preserving_order(values)
    if not identifiers:
        raise McpError(-32602, f"{name} must contain at least one identifier")
    if len(identifiers) > MAX_IDENTIFIERS:
        raise McpError(-32602, f"{name} supports at most {MAX_IDENTIFIERS} identifiers")
    for identifier in identifiers:
        if len(identifier) > 200:
            raise McpError(-32602, f"{name} contains an identifier longer than 200 characters")
        if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", identifier):
            raise McpError(-32602, f"{name} contains unsupported control characters")
    return identifiers


def split_identifier_text(value: str) -> list[str]:
    return [
        item.strip()
        for item in re.split(r"[\r\n,;]+", value)
        if item.strip()
    ]


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


def dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        key = value.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(value)
    return deduped


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "string",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def normalize_score(value: Any) -> float | str:
    if value in {"", None}:
        return ""
    if isinstance(value, (int, float)):
        return round(float(value), 4)
    try:
        return round(float(str(value)), 4)
    except ValueError:
        return normalize_space(value)

