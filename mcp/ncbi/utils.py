"""Input validation, provenance, and XML text helpers."""

from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from typing import Any

from .constants import JsonObject
from .errors import McpError


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_date_like(value: Any, name: str) -> str:
    text = str(value).strip()
    if not re.fullmatch(r"\d{4}([/-]\d{1,2}([/-]\d{1,2})?)?", text):
        raise McpError(
            -32602,
            f"{name} must look like YYYY, YYYY/MM, YYYY/MM/DD, YYYY-MM, or YYYY-MM-DD",
        )
    return text.replace("-", "/")


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
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y"}:
            return True
        if lowered in {"0", "false", "no", "n"}:
            return False
    raise McpError(-32602, f"{name} must be a boolean")


def parse_count(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    safe_params = {
        key: value
        for key, value in params.items()
        if key not in {"api_key", "email"}
    }
    return {
        "database": safe_params.get("db", "pubmed"),
        "endpoint": endpoint,
        "params": safe_params,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

def element_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return normalize_space("".join(node.itertext()))


def text_from_child(node: ET.Element | None, child_name: str) -> str:
    if node is None:
        return ""
    return element_text(node.find(child_name))


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())
