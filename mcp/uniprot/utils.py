"""Input validation, provenance, and normalization helpers."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_accession(args: JsonObject, name: str = "accession") -> str:
    accession = require_non_empty_string(args, name).strip()
    if not re.fullmatch(r"[A-Za-z0-9_.:-]+", accession):
        raise McpError(-32602, f"{name} contains unsupported characters")
    return accession


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


def optional_string_list(args: JsonObject, name: str) -> list[str]:
    value = args.get(name)
    if value is None:
        return []
    if isinstance(value, str):
        return [
            normalize_space(item)
            for item in value.split(",")
            if normalize_space(item)
        ]
    if isinstance(value, list):
        result = []
        for item in value:
            if not isinstance(item, str):
                raise McpError(-32602, f"{name} items must be strings")
            text = normalize_space(item)
            if text:
                result.append(text)
        return result
    raise McpError(-32602, f"{name} must be a string or string array")


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "uniprotkb",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def compact_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = normalize_space(value)
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
