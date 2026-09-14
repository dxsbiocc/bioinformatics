"""Input validation and provenance helpers for cBioPortal."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError

ID_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
GENE_SYMBOL_RE = re.compile(r"^[A-Za-z0-9_.-]+$")
CLINICAL_DATA_TYPES = {"SAMPLE", "PATIENT"}


def require_identifier(args: JsonObject, name: str, example: str) -> str:
    value = require_non_empty_string(args, name)
    if not ID_RE.match(value):
        raise McpError(-32602, f"{name} must look like {example}")
    return value


def require_study_id(args: JsonObject, name: str = "study_id") -> str:
    return require_identifier(args, name, "brca_tcga")


def require_profile_id(args: JsonObject, name: str = "molecular_profile_id") -> str:
    return require_identifier(args, name, "brca_tcga_mutations")


def require_sample_list_id(args: JsonObject, name: str = "sample_list_id") -> str:
    return require_identifier(args, name, "brca_tcga_all")


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
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


def optional_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip()


def optional_clinical_data_type(args: JsonObject, name: str = "clinical_data_type") -> str:
    value = optional_string(args, name).upper() or "SAMPLE"
    if value not in CLINICAL_DATA_TYPES:
        raise McpError(-32602, f"{name} must be SAMPLE or PATIENT")
    return value


def optional_identifier_list(args: JsonObject, name: str) -> list[str]:
    value = args.get(name)
    if value is None:
        return []
    if not isinstance(value, list):
        raise McpError(-32602, f"{name} must be a list of identifiers")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or not ID_RE.match(item.strip()):
            raise McpError(-32602, f"{name} must contain cBioPortal-style identifiers")
        result.append(item.strip())
    return result


def optional_int_list(args: JsonObject, name: str) -> list[int]:
    value = args.get(name)
    if value is None:
        return []
    if not isinstance(value, list):
        raise McpError(-32602, f"{name} must be a list of integers")
    result: list[int] = []
    for item in value:
        try:
            parsed = int(item)
        except (TypeError, ValueError) as exc:
            raise McpError(-32602, f"{name} must contain only integers") from exc
        result.append(parsed)
    return result


def optional_symbol_list(args: JsonObject, name: str) -> list[str]:
    value = args.get(name)
    if value is None:
        return []
    if not isinstance(value, list):
        raise McpError(-32602, f"{name} must be a list of gene symbols")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip() or not GENE_SYMBOL_RE.match(item.strip()):
            raise McpError(-32602, f"{name} must contain HUGO-style gene symbols")
        result.append(item.strip().upper())
    return result


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def source_info(endpoint: str, params: JsonObject, *, method: str = "GET", body: JsonObject | list[Any] | None = None) -> JsonObject:
    source: JsonObject = {
        "database": "cbioportal",
        "endpoint": endpoint,
        "method": method,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if body is not None:
        source["body"] = body
    return source
