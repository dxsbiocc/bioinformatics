"""Input validation, text cleanup, and provenance helpers for Reactome."""

from __future__ import annotations

import html
import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError

HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
REACTOME_STABLE_ID_PATTERN = re.compile(r"^R-[A-Z]{3}-\d+(?:\.\d+)?$", re.IGNORECASE)


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_stable_id(args: JsonObject, name: str = "stable_id") -> str:
    stable_id = require_non_empty_string(args, name)
    stable_id = stable_id.strip()
    if REACTOME_STABLE_ID_PATTERN.fullmatch(stable_id) is None:
        raise McpError(
            -32602,
            f"{name} must be a Reactome stable ID such as R-HSA-5633007",
        )
    return stable_id.upper()


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


def optional_string(args: JsonObject, name: str, *, default: str) -> str:
    value = args.get(name, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip() or default


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "reactome",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def clean_html(value: Any) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    text = re.sub(r"</?(p|br|div|li|ul|ol)[^>]*>", " ", text, flags=re.IGNORECASE)
    text = HTML_TAG_PATTERN.sub("", text)
    return normalize_space(html.unescape(text))


def first_text(value: Any) -> str:
    if isinstance(value, list):
        for item in value:
            text = clean_html(item)
            if text:
                return text
        return ""
    return clean_html(value)

