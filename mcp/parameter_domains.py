"""Shared MCP parameter-domain discovery helpers."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

JsonObject = dict[str, Any]

RESULT_SCHEMA_VERSION = "bioinformatics.parameter_domains.v1"


def parameter_domains_tool_definition(tool_name: str) -> JsonObject:
    return {
        "name": tool_name,
        "title": "Search MCP parameter domains",
        "description": (
            "Search this MCP server's tool parameter domains, including required "
            "fields, enum values, boolean flags, numeric ranges, array item types, "
            "defaults, and dynamic-value hints derived from tool schemas."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Optional text to match tool names, parameter names, descriptions, enum values, or titles.",
                },
                "tool_name": {
                    "type": "string",
                    "description": "Optional exact or partial tool name filter.",
                },
                "parameter_name": {
                    "type": "string",
                    "description": "Optional exact or partial parameter name filter.",
                },
                "domain_type": {
                    "type": "string",
                    "enum": ["enum", "boolean", "integer_range", "number_range", "string", "array", "object", "one_of", "all"],
                    "default": "all",
                    "description": "Filter by normalized parameter-domain type.",
                },
                "include_status_tools": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include status/parameter-domain tools in the returned parameter domains.",
                },
                "include_schema": {
                    "type": "boolean",
                    "default": False,
                    "description": "Include the original JSON Schema fragment for each matched parameter.",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "default": 100,
                },
            },
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True, "openWorldHint": False},
    }


def make_parameter_domains_handler(
    server_name: str,
    tool_name: str,
    tool_definitions: Callable[[], list[JsonObject]],
) -> Callable[[JsonObject, Any], JsonObject]:
    def handler(args: JsonObject, _client: Any) -> JsonObject:
        return parameter_domains_response(
            server_name=server_name,
            parameter_tool_name=tool_name,
            tool_definitions=tool_definitions(),
            args=args,
        )

    return handler


def parameter_domains_response(
    *,
    server_name: str,
    parameter_tool_name: str,
    tool_definitions: list[JsonObject],
    args: JsonObject,
) -> JsonObject:
    query = normalize_text(args.get("query"))
    tool_filter = normalize_text(args.get("tool_name"))
    parameter_filter = normalize_text(args.get("parameter_name"))
    domain_filter = normalize_text(args.get("domain_type")) or "all"
    include_status_tools = bool(args.get("include_status_tools", False))
    include_schema = bool(args.get("include_schema", False))
    max_results = bounded_int(args.get("max_results"), default=100, minimum=1, maximum=500)

    domains: list[JsonObject] = []
    searched_tools: list[str] = []
    for tool in tool_definitions:
        name = str(tool.get("name") or "")
        if not name or name == parameter_tool_name:
            continue
        if not include_status_tools and is_status_tool(name):
            continue
        if tool_filter and tool_filter not in name.lower():
            continue
        searched_tools.append(name)
        for domain in domains_for_tool(tool, include_schema=include_schema):
            haystack = domain_haystack(domain)
            if parameter_filter and parameter_filter not in str(domain.get("parameter_name", "")).lower():
                continue
            if domain_filter != "all" and domain.get("domain_type") != domain_filter:
                continue
            if query and query not in haystack:
                continue
            domains.append(domain)
            if len(domains) >= max_results:
                break
        if len(domains) >= max_results:
            break

    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "server": server_name,
        "database": server_name,
        "query": {
            "query": query,
            "tool_name": tool_filter,
            "parameter_name": parameter_filter,
            "domain_type": domain_filter,
            "include_status_tools": include_status_tools,
        },
        "returned": len(domains),
        "total_tools": len([tool for tool in tool_definitions if tool.get("name") != parameter_tool_name]),
        "searched_tools": searched_tools,
        "domains": domains,
        "tools": summarize_tools(domains),
        "usage_hints": [
            "Use enum and boolean domains directly in tool calls.",
            "Use integer_range/number_range minimum and maximum values to bound numeric arguments.",
            "For open string IDs, call the same server's search, lookup, list, or status tools first when available.",
            "If a fetch returns no data, inspect structuredContent.warnings and diagnostics before retrying.",
        ],
    }


def domains_for_tool(tool: JsonObject, *, include_schema: bool) -> list[JsonObject]:
    schema = tool.get("inputSchema")
    if not isinstance(schema, dict):
        return []
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return []
    required = {str(item) for item in schema.get("required", []) if isinstance(item, str)}
    tool_name = str(tool.get("name") or "")
    tool_title = str(tool.get("title") or "")
    tool_description = str(tool.get("description") or "")
    domains: list[JsonObject] = []
    for parameter_name, parameter_schema in properties.items():
        if not isinstance(parameter_name, str) or not isinstance(parameter_schema, dict):
            continue
        domain = describe_schema(parameter_schema)
        domain.update(
            {
                "tool_name": tool_name,
                "tool_title": tool_title,
                "tool_description": tool_description,
                "parameter_name": parameter_name,
                "required": parameter_name in required,
                "description": str(parameter_schema.get("description") or ""),
                "domain_source": domain_source(domain),
                "dynamic_value_hint": dynamic_value_hint(parameter_name, parameter_schema),
            }
        )
        if "default" in parameter_schema:
            domain["default"] = parameter_schema["default"]
        if include_schema:
            domain["schema"] = parameter_schema
        domains.append(domain)
    return domains


def describe_schema(schema: JsonObject) -> JsonObject:
    if "enum" in schema and isinstance(schema["enum"], list):
        return {"domain_type": "enum", "type": schema.get("type", "string"), "enum": schema["enum"]}
    if "oneOf" in schema and isinstance(schema["oneOf"], list):
        variants = [describe_schema(variant) for variant in schema["oneOf"] if isinstance(variant, dict)]
        enum_values: list[Any] = []
        for variant in variants:
            if isinstance(variant.get("enum"), list):
                enum_values.extend(variant["enum"])
        result: JsonObject = {"domain_type": "one_of", "variants": variants}
        if enum_values:
            result["enum"] = enum_values
        return result
    schema_type = schema.get("type")
    if schema_type == "boolean":
        return {"domain_type": "boolean", "type": "boolean", "enum": [True, False]}
    if schema_type == "integer":
        return numeric_domain(schema, "integer_range")
    if schema_type == "number":
        return numeric_domain(schema, "number_range")
    if schema_type == "array":
        result = {"domain_type": "array", "type": "array"}
        items = schema.get("items")
        if isinstance(items, dict):
            result["items"] = describe_schema(items)
        for key in ("minItems", "maxItems"):
            if key in schema:
                result[key] = schema[key]
        return result
    if schema_type == "object":
        return {"domain_type": "object", "type": "object"}
    return {"domain_type": "string", "type": schema_type or "string"}


def numeric_domain(schema: JsonObject, domain_type: str) -> JsonObject:
    result: JsonObject = {"domain_type": domain_type, "type": schema.get("type")}
    for key in ("minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf"):
        if key in schema:
            result[key] = schema[key]
    return result


def domain_source(domain: JsonObject) -> str:
    if domain.get("domain_type") == "enum":
        return "closed_enum"
    if domain.get("domain_type") in {"boolean", "integer_range", "number_range"}:
        return "schema_constraint"
    if domain.get("domain_type") == "one_of" and domain.get("enum"):
        return "union_with_enum"
    return "open_value"


def dynamic_value_hint(parameter_name: str, schema: JsonObject) -> str:
    text = f"{parameter_name} {schema.get('description', '')}".lower()
    if "id" in parameter_name.lower() or "accession" in text or "identifier" in text:
        return "Identifier-like value; use search/list/lookup tools from this MCP first when the exact value is unknown."
    if "query" in parameter_name.lower() or "term" in parameter_name.lower():
        return "Free-text search expression; use database-specific syntax described in this parameter description."
    if "date" in parameter_name.lower():
        return "Date-like value; follow the format in the parameter description."
    if "path" in parameter_name.lower():
        return "Local path value; verify file existence before calling tools that read files."
    return ""


def summarize_tools(domains: list[JsonObject]) -> list[JsonObject]:
    by_tool: dict[str, JsonObject] = {}
    for domain in domains:
        tool = by_tool.setdefault(
            str(domain["tool_name"]),
            {
                "tool_name": domain["tool_name"],
                "tool_title": domain.get("tool_title", ""),
                "matched_parameters": [],
            },
        )
        tool["matched_parameters"].append(
            {
                "name": domain["parameter_name"],
                "domain_type": domain["domain_type"],
                "required": domain["required"],
            }
        )
    return list(by_tool.values())


def is_status_tool(tool_name: str) -> bool:
    return tool_name.endswith("_status") or tool_name.endswith("_parameter_domains")


def domain_haystack(domain: JsonObject) -> str:
    values = [
        domain.get("tool_name"),
        domain.get("tool_title"),
        domain.get("tool_description"),
        domain.get("parameter_name"),
        domain.get("description"),
        domain.get("domain_type"),
        domain.get("domain_source"),
        domain.get("dynamic_value_hint"),
    ]
    enum_values = domain.get("enum")
    if isinstance(enum_values, list):
        values.extend(str(item) for item in enum_values)
    return " ".join(str(value) for value in values if value is not None).lower()


def normalize_text(value: Any) -> str:
    return str(value or "").strip().lower()


def bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return min(max(parsed, minimum), maximum)
