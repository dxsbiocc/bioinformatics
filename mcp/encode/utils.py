"""Input validation and provenance helpers for ENCODE."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError


EXPERIMENT_RE = re.compile(r"^ENCSR[A-Z0-9]+$", re.IGNORECASE)
FILE_RE = re.compile(r"^ENCFF[A-Z0-9]+$", re.IGNORECASE)
BIOSAMPLE_RE = re.compile(r"^ENCBS[A-Z0-9]+$", re.IGNORECASE)


def require_experiment_accession(args: JsonObject, name: str = "accession") -> str:
    value = require_non_empty_string(args, name).upper()
    if not EXPERIMENT_RE.match(value):
        raise McpError(-32602, f"{name} must look like ENCSR000AEG or another ENCODE experiment accession")
    return value


def require_file_accession(args: JsonObject, name: str = "accession") -> str:
    value = require_non_empty_string(args, name).upper()
    if not FILE_RE.match(value):
        raise McpError(-32602, f"{name} must look like ENCFF789PHQ or another ENCODE file accession")
    return value


def require_biosample_accession(args: JsonObject, name: str = "accession") -> str:
    value = require_non_empty_string(args, name).upper()
    if not BIOSAMPLE_RE.match(value):
        raise McpError(-32602, f"{name} must look like ENCBS000AAA or another ENCODE biosample accession")
    return value


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def optional_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if value is None:
        return ""
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


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "encode",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
