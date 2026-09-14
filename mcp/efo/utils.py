"""Input validation, IRI, URL, and provenance helpers for EFO."""

from __future__ import annotations

import re
import time
import urllib.parse
from typing import Any

from .constants import DEFAULT_RESULTS, MAX_RESULTS, OLS4_API_BASE_URL, OLS4_WEBSITE_BASE_URL, JsonObject
from .errors import McpError

CURIE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*[:_][A-Za-z0-9_.-]+$")


def require_term(args: JsonObject, name: str = "term_id") -> str:
    value = require_non_empty_string(args, name)
    if not (value.startswith(("http://", "https://")) or CURIE_RE.match(value)):
        raise McpError(-32602, f"{name} must be a CURIE, underscore ID, or full IRI, for example EFO:0000270")
    return value.strip()


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


def term_input_to_iri(value: str) -> str:
    text = normalize_space(value)
    if text.startswith(("http://", "https://")):
        return text
    prefix = ""
    local = ""
    if ":" in text:
        prefix, local = text.split(":", 1)
    elif "_" in text:
        prefix, local = text.split("_", 1)
    prefix = prefix.upper()
    local = local.replace(":", "_")
    if prefix == "EFO":
        return f"http://www.ebi.ac.uk/efo/EFO_{local}"
    return f"http://purl.obolibrary.org/obo/{prefix}_{local}"


def double_encode_iri(iri: str) -> str:
    return urllib.parse.quote(urllib.parse.quote(iri, safe=""), safe="")


def term_endpoint(value: str) -> tuple[str, str]:
    iri = term_input_to_iri(value)
    return f"ontologies/efo/terms/{double_encode_iri(iri)}", iri


def ols_term_url(iri: str, website_base_url: str = OLS4_WEBSITE_BASE_URL) -> str:
    return f"{website_base_url.rstrip('/')}/ontologies/efo/classes?iri={urllib.parse.quote(iri, safe='')}"


def ols_api_url(endpoint: str, params: JsonObject | None = None, api_base_url: str = OLS4_API_BASE_URL) -> str:
    url = f"{api_base_url.rstrip('/')}/{endpoint.lstrip('/')}"
    if params:
        return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"
    return url


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "efo",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

