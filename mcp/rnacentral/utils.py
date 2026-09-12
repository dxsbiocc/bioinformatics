"""Input validation, normalization, URL, and provenance helpers for RNAcentral."""

from __future__ import annotations

import re
import time
import urllib.parse
from typing import Any

from .constants import DEFAULT_PAGE, DEFAULT_RESULTS, MAX_RESULTS, RNACENTRAL_API_BASE_URL, RNACENTRAL_WEBSITE_BASE_URL, JsonObject
from .errors import McpError


URN_RE = re.compile(r"^URS[0-9A-F]{10,}$", re.IGNORECASE)


def require_rnacentral_id(args: JsonObject, name: str = "rnacentral_id") -> str:
    value = require_non_empty_string(args, name)
    if "_" in value:
        value = value.split("_", 1)[0]
    value = value.upper()
    if not URN_RE.match(value):
        raise McpError(-32602, f"{name} must look like an RNAcentral URS identifier, for example URS000075C808")
    return value


def require_query(args: JsonObject, name: str = "query") -> str:
    return require_non_empty_string(args, name)


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def optional_string(args: JsonObject, name: str, *, default: str = "") -> str:
    value = args.get(name, default)
    if value is None:
        return default
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(value)
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
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


def optional_taxid(args: JsonObject, name: str = "taxid") -> int | None:
    value = args.get(name)
    if value in {None, ""}:
        raw_id = args.get("rnacentral_id")
        if isinstance(raw_id, str) and "_" in raw_id:
            suffix = raw_id.rsplit("_", 1)[1]
            if suffix.isdigit():
                return int(suffix)
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise McpError(-32602, f"{name} must be an integer TaxID") from exc
    if parsed <= 0:
        raise McpError(-32602, f"{name} must be a positive integer TaxID")
    return parsed


def max_results(args: JsonObject) -> int:
    return optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)


def page(args: JsonObject) -> int:
    return optional_int(args, "page", default=DEFAULT_PAGE, minimum=1, maximum=100000)


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def compact_strings(values: object) -> list[str]:
    if isinstance(values, str):
        return [normalize_space(values)] if normalize_space(values) else []
    if not isinstance(values, list):
        return []
    return [normalize_space(value) for value in values if normalize_space(value)]


def safe_dict(value: object) -> JsonObject:
    return value if isinstance(value, dict) else {}


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def rnacentral_website_url(rnacentral_id: str, taxid: int | str | None = None) -> str:
    identifier = normalize_space(rnacentral_id).upper()
    if not identifier:
        return RNACENTRAL_WEBSITE_BASE_URL
    if taxid:
        return f"{RNACENTRAL_WEBSITE_BASE_URL.rstrip('/')}/rna/{urllib.parse.quote(identifier)}/{taxid}"
    return f"{RNACENTRAL_WEBSITE_BASE_URL.rstrip('/')}/rna/{urllib.parse.quote(identifier)}"


def rnacentral_api_url(endpoint: str, params: JsonObject | None = None) -> str:
    endpoint = endpoint.lstrip("/")
    url = f"{RNACENTRAL_API_BASE_URL.rstrip('/')}/{endpoint}"
    if params:
        return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    return url


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "rnacentral",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

