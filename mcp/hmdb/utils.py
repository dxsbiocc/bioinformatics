"""Input validation, URL, and provenance helpers for HMDB."""

from __future__ import annotations

import time
import urllib.parse
from typing import Any

from .constants import DEFAULT_RESULTS, HMDB_BASE_URL, HMDB_CATEGORIES, MAX_RESULTS, JsonObject
from .errors import McpError


def require_query(args: JsonObject, name: str = "query") -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_category(args: JsonObject, *, default: str | None = None) -> str:
    value = args.get("category", default)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, "category is required")
    category = value.strip().lower()
    if category not in HMDB_CATEGORIES:
        allowed = ", ".join(sorted(HMDB_CATEGORIES))
        raise McpError(-32602, f"category must be one of: {allowed}")
    return category


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


def optional_int(args: JsonObject, name: str, *, default: int, minimum: int, maximum: int) -> int:
    value = args.get(name, default)
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise McpError(-32602, f"{name} must be an integer") from exc
    if parsed < minimum or parsed > maximum:
        raise McpError(-32602, f"{name} must be between {minimum} and {maximum}")
    return parsed


def max_results(args: JsonObject) -> int:
    return optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_dict(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def first_text(row: JsonObject, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if isinstance(value, list):
            for item in value:
                text = normalize_space(item)
                if text:
                    return text
        text = normalize_space(value)
        if text:
            return text
    return ""


def pick_list(row: JsonObject, *keys: str) -> list[str]:
    out: list[str] = []
    for key in keys:
        value = row.get(key)
        values = value if isinstance(value, list) else [value]
        for item in values:
            text = normalize_space(item)
            if text and text not in out:
                out.append(text)
    return out


def hmdb_record_url(category: str, identifier: str, *, base_url: str = HMDB_BASE_URL) -> str:
    if not identifier:
        return f"{base_url.rstrip('/')}/{category}"
    return f"{base_url.rstrip('/')}/{category}/{urllib.parse.quote(identifier, safe='')}"


def source_info(endpoint: str, params: JsonObject, *, url: str = "") -> JsonObject:
    source: JsonObject = {
        "database": "hmdb",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if url:
        source["url"] = url
    return source
