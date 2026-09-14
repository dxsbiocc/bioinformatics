"""Input validation and provenance helpers for bioRxiv/medRxiv."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import DEFAULT_RECENT_DAYS, DEFAULT_RESULTS, MAX_RESULTS, SUPPORTED_SERVERS, JsonObject
from .errors import McpError

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def require_server(args: JsonObject, name: str = "server") -> str:
    value = optional_string(args, name, default="biorxiv").lower()
    if value not in SUPPORTED_SERVERS:
        raise McpError(-32602, f"{name} must be one of: biorxiv, medrxiv")
    return value


def require_doi(args: JsonObject, name: str = "doi") -> str:
    value = require_non_empty_string(args, name)
    if "/" not in value:
        raise McpError(-32602, f"{name} must look like a DOI, for example 10.1101/2020.09.09.20191205")
    return value


def date_interval_or_recent_days(args: JsonObject) -> tuple[str, JsonObject]:
    start_date = optional_string(args, "start_date")
    end_date = optional_string(args, "end_date")
    if start_date or end_date:
        if not start_date or not end_date:
            raise McpError(-32602, "start_date and end_date must be provided together")
        if not DATE_RE.match(start_date) or not DATE_RE.match(end_date):
            raise McpError(-32602, "start_date and end_date must use YYYY-MM-DD")
        return f"{start_date}/{end_date}", {"start_date": start_date, "end_date": end_date}
    recent_days = optional_int(args, "recent_days", default=DEFAULT_RECENT_DAYS, minimum=1, maximum=365)
    return f"{recent_days}d", {"recent_days": recent_days}


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


def max_results(args: JsonObject) -> int:
    return optional_int(args, "max_results", default=DEFAULT_RESULTS, minimum=1, maximum=MAX_RESULTS)


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def split_authors(value: object) -> list[str]:
    text = normalize_space(value)
    if not text:
        return []
    separator = ";" if ";" in text else ","
    return [normalize_space(part) for part in text.split(separator) if normalize_space(part)]


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "biorxiv",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
