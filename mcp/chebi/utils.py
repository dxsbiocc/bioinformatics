"""Input validation, URL, and provenance helpers for ChEBI."""

from __future__ import annotations

import re
import time
import urllib.parse
import html
from typing import Any

from .constants import CHEBI_WEBSITE_BASE_URL, DEFAULT_RESULTS, MAX_RESULTS, JsonObject
from .errors import McpError


CHEBI_RE = re.compile(r"^(?:CHEBI:)?\d+$", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"<[^>]+>")


def require_query(args: JsonObject, name: str = "query") -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_chebi_id(args: JsonObject, name: str = "chebi_id") -> str:
    value = args.get(name)
    if isinstance(value, int):
        value = str(value)
    if not isinstance(value, str) or not value.strip() or not CHEBI_RE.match(value.strip()):
        raise McpError(-32602, f"{name} must be a ChEBI identifier such as CHEBI:27732")
    return normalize_chebi_id(value)


def normalize_chebi_id(value: object) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    if text.upper().startswith("CHEBI:"):
        return f"CHEBI:{text.split(':', 1)[1]}"
    if text.isdigit():
        return f"CHEBI:{text}"
    return text


def chebi_numeric_id(value: object) -> str:
    text = normalize_chebi_id(value)
    if ":" in text:
        return text.split(":", 1)[1]
    return text


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
    text = html.unescape(str(value))
    text = HTML_TAG_RE.sub("", text)
    return " ".join(text.split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_dict(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def first_text(row: JsonObject, *keys: str) -> str:
    for key in keys:
        text = normalize_space(row.get(key))
        if text:
            return text
    return ""


def chebi_page_url(chebi_id: str, website_base_url: str = CHEBI_WEBSITE_BASE_URL) -> str:
    return f"{website_base_url.rstrip('/')}/searchId.do?chebiId={urllib.parse.quote(normalize_chebi_id(chebi_id), safe=':')}"


def chebi_image_url(chebi_id: str, website_base_url: str = CHEBI_WEBSITE_BASE_URL) -> str:
    return f"{website_base_url.rstrip('/')}/displayImage.do?defaultImage=true&imageIndex=0&chebiId={urllib.parse.quote(normalize_chebi_id(chebi_id), safe=':')}"


def source_info(endpoint: str, params: JsonObject, *, url: str = "") -> JsonObject:
    source: JsonObject = {
        "database": "chebi",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if url:
        source["url"] = url
    return source
