"""Input validation and provenance helpers for Ensembl."""

from __future__ import annotations

import re
import time
from typing import Any

from .constants import JsonObject
from .errors import McpError


ENSEMBL_ID_PATTERN = re.compile(r"^ENS[A-Z]*[GTEPRFM]\d+(?:\.\d+)?$", re.IGNORECASE)
REGION_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+:\d+-\d+(?::[-1]+)?$")


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_ensembl_id(args: JsonObject, name: str = "ensembl_id") -> str:
    value = require_non_empty_string(args, name)
    if ENSEMBL_ID_PATTERN.fullmatch(value) is None:
        raise McpError(-32602, f"{name} must be an Ensembl stable ID")
    return value


def require_region(args: JsonObject, name: str = "region") -> str:
    value = require_non_empty_string(args, name)
    if REGION_PATTERN.fullmatch(value) is None:
        raise McpError(-32602, f"{name} must look like 17:7661779-7687546")
    return value


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


def optional_string_list(
    args: JsonObject,
    name: str,
    *,
    default: list[str],
    allowed: set[str] | None = None,
) -> list[str]:
    value = args.get(name, default)
    if isinstance(value, str):
        items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        items = []
        for item in value:
            if not isinstance(item, str):
                raise McpError(-32602, f"{name} must contain only strings")
            if item.strip():
                items.append(item.strip())
    else:
        raise McpError(-32602, f"{name} must be a string or string array")
    if allowed is not None:
        invalid = [item for item in items if item not in allowed]
        if invalid:
            raise McpError(-32602, f"{name} contains unsupported values: {', '.join(invalid)}")
    return items or list(default)


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "ensembl",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def species_label(species: object) -> str:
    text = normalize_space(species)
    if not text:
        return ""
    return text.replace("_", " ")


def ensembl_species_path(species: object) -> str:
    text = normalize_space(species) or "homo_sapiens"
    parts = [part for part in text.split("_") if part]
    if not parts:
        return "Homo_sapiens"
    return "_".join([parts[0].capitalize(), *[part.lower() for part in parts[1:]]])
