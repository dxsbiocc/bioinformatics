"""Input validation, URL, text cleanup, and provenance helpers for KEGG."""

from __future__ import annotations

import re
import time
import urllib.parse
from typing import Any

from .constants import DEFAULT_MAX_RESULTS, MAX_RESULTS, JsonObject
from .errors import McpError


ENTRY_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+(?::[A-Za-z0-9_.-]+)?$")
MAP_ID_PATTERN = re.compile(r"^[A-Za-z]{2,5}\d{5}$")
COLOR_TOKEN_PATTERN = re.compile(r"^(#[0-9A-Fa-f]{3}(?:[0-9A-Fa-f]{3})?|[A-Za-z][A-Za-z0-9_-]*)$")


def require_non_empty_string(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if not isinstance(value, str) or not value.strip():
        raise McpError(-32602, f"{name} is required and must be a non-empty string")
    return value.strip()


def require_map_id(args: JsonObject, name: str = "map_id") -> str:
    map_id = require_non_empty_string(args, name)
    if MAP_ID_PATTERN.fullmatch(map_id) is None:
        raise McpError(-32602, f"{name} must be a KEGG pathway map ID such as map00010 or hsa04110")
    return map_id


def optional_string(args: JsonObject, name: str, *, default: str = "") -> str:
    value = args.get(name, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip() or default


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


def optional_float(
    args: JsonObject,
    name: str,
    *,
    default: float,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    value = args.get(name, default)
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise McpError(-32602, f"{name} must be a number") from exc
    if minimum is not None and parsed < minimum:
        raise McpError(-32602, f"{name} must be at least {minimum}")
    if maximum is not None and parsed > maximum:
        raise McpError(-32602, f"{name} must be at most {maximum}")
    return parsed


def optional_enum(
    args: JsonObject,
    name: str,
    *,
    allowed: list[str],
    default: str = "",
) -> str:
    value = optional_string(args, name, default=default)
    if not value:
        return value
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def optional_max_results(args: JsonObject) -> int:
    return optional_int(
        args,
        "max_results",
        default=DEFAULT_MAX_RESULTS,
        minimum=1,
        maximum=MAX_RESULTS,
    )


def require_entry_ids(args: JsonObject) -> list[str]:
    values = args.get("entry_ids")
    dbentries = args.get("dbentries")
    entries: list[str] = []
    if isinstance(values, list):
        entries.extend(normalize_entry_id(item) for item in values)
    elif isinstance(values, str):
        entries.extend(split_dbentries(values))
    if isinstance(dbentries, str):
        entries.extend(split_dbentries(dbentries))
    entries = [entry for entry in unique_texts(entries) if entry]
    if not entries:
        raise McpError(-32602, "entry_ids or dbentries is required")
    return entries


def require_color_items(args: JsonObject, *, max_items: int) -> list[JsonObject]:
    values = args.get("items")
    if not isinstance(values, list) or not values:
        raise McpError(-32602, "items is required and must be a non-empty array")
    if len(values) > max_items:
        raise McpError(-32602, f"items supports at most {max_items} rows")
    items: list[JsonObject] = []
    for index, value in enumerate(values):
        if not isinstance(value, dict):
            raise McpError(-32602, f"items[{index}] must be an object")
        kegg_id = normalize_entry_id(value.get("kegg_id") or value.get("id"))
        if not kegg_id:
            raise McpError(-32602, f"items[{index}].kegg_id is required")
        raw_color = optional_item_string(value, "color")
        bgcolor = optional_item_string(value, "bgcolor")
        fgcolor = optional_item_string(value, "fgcolor")
        color = normalize_color_spec(raw_color, bgcolor=bgcolor, fgcolor=fgcolor)
        items.append(
            {
                "kegg_id": kegg_id,
                "color": color,
                "bgcolor": bgcolor,
                "fgcolor": fgcolor,
                "label": optional_item_string(value, "label"),
                "source_value": optional_item_string(value, "source_value"),
            }
        )
    return items


def optional_item_string(item: JsonObject, name: str) -> str:
    value = item.get(name, "")
    if value is None:
        return ""
    if not isinstance(value, (str, int, float)):
        raise McpError(-32602, f"{name} must be a string")
    return normalize_space(value)


def normalize_color_spec(raw_color: str, *, bgcolor: str = "", fgcolor: str = "") -> str:
    raw_color = normalize_space(raw_color)
    if raw_color:
        validate_color_spec(raw_color)
        return raw_color
    bgcolor = normalize_space(bgcolor)
    fgcolor = normalize_space(fgcolor)
    if bgcolor:
        validate_color_group(bgcolor, "bgcolor")
    if fgcolor:
        validate_color_group(fgcolor, "fgcolor")
    if bgcolor and fgcolor:
        return f"{bgcolor},{fgcolor}"
    if fgcolor:
        return f",{fgcolor}"
    return bgcolor


def validate_color_spec(value: str) -> None:
    for chunk in value.replace(",", " ").split():
        validate_color_group(chunk, "color")


def validate_color_group(value: str, name: str) -> None:
    for token in value.split("|"):
        # KEGG split coloring examples also accept whitespace-separated colors,
        # handled before this function. Pipes are useful for front-end callers
        # that need a separator inside one JSON string.
        for part in token.split():
            if COLOR_TOKEN_PATTERN.fullmatch(part) is None:
                raise McpError(-32602, f"{name} contains an invalid color token: {part}")


def split_dbentries(value: str) -> list[str]:
    parts = re.split(r"[+,\s]+", value.strip())
    return [normalize_entry_id(part) for part in parts if normalize_entry_id(part)]


def normalize_entry_id(value: Any) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    if ENTRY_PATTERN.fullmatch(text) is None:
        raise McpError(-32602, f"Invalid KEGG entry identifier: {text}")
    return text


def join_dbentries(entries: list[str]) -> str:
    return "+".join(entries)


def quote_segment(value: Any) -> str:
    return urllib.parse.quote(str(value), safe=":+._-")


def source_info(endpoint: str, params: JsonObject, *, url: str = "") -> JsonObject:
    source: JsonObject = {
        "database": "kegg",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if url:
        source["url"] = url
    return source


def normalize_space(value: Any) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def unique_texts(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out
