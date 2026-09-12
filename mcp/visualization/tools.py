"""MCP tool registry for local omics visualization routing."""

from __future__ import annotations

import time
import urllib.parse
import sys
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_TOP_RECOMMENDATIONS,
    MAX_TOP_RECOMMENDATIONS,
    RECORD_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .errors import McpError


PLUGIN_ROOT = Path(__file__).resolve().parents[2]
SKILL_ROOT = PLUGIN_ROOT / "skills" / "omics-visualization"
SCRIPT_DIR = SKILL_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from route_template import DEFAULT_CONTRACTS, build_profile, load_contracts, recommend
    from validate_template_contracts import validate_contracts
except ImportError as exc:  # pragma: no cover - exercised as MCP boundary data.
    raise RuntimeError(f"omics visualization scripts are unavailable under {SCRIPT_DIR}") from exc


ROUTE_TOOL = "omics_visualization_route"
COVERAGE_TOOL = "omics_visualization_contract_coverage"
STATUS_TOOL = "omics_visualization_status"
VALID_MODES = {"preview", "publication", "template-dev"}
LOCAL_ROUTE_BASE_URL = "https://codex.local/bioinformatics/visualization/routes"


def omics_visualization_route(args: JsonObject) -> JsonObject:
    """Profile a CSV/TSV result table and return template recommendations."""

    query = require_non_empty_string(args, "query")
    mode = optional_mode(args)
    top = optional_int(
        args,
        "top",
        default=DEFAULT_TOP_RECOMMENDATIONS,
        minimum=1,
        maximum=MAX_TOP_RECOMMENDATIONS,
    )
    include_profile = optional_bool(args, "include_profile", default=True)
    include_contract_coverage = optional_bool(args, "include_contract_coverage", default=False)
    table_path = resolve_table_path(
        require_non_empty_string(args, "table_path"),
        optional_string(args, "base_dir"),
    )
    contracts_path = resolve_contracts_path(optional_string(args, "contracts_path"))

    profile = build_profile(table_path)
    contracts = load_contracts(contracts_path)
    recommendations = recommend(profile, contracts, query, mode, top)
    selected = recommendations[0] if recommendations else None
    profile_summary = summarize_profile(profile)

    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "server": "visualization",
        "database": "bioinformatics.visualization",
        "tool": ROUTE_TOOL,
        "mode": mode,
        "query": query,
        "returned": len(recommendations),
        "selected": selected,
        "recommendations": recommendations,
        "input": {
            "table_path": str(table_path),
            "contracts_path": str(contracts_path),
        },
        "input_profile_summary": profile_summary,
        "next_steps": route_next_steps(selected),
        "source": source_info("route_template", {"table_path": str(table_path), "contracts_path": str(contracts_path)}),
    }
    response["provenance"] = response["source"]
    if include_profile:
        response["input_profile"] = profile
    if include_contract_coverage:
        response["contract_coverage"] = validate_contracts(contracts_path, SKILL_ROOT)["coverage"]
    response["records"] = [route_record(response)]
    return response


def omics_visualization_contract_coverage(args: JsonObject) -> JsonObject:
    """Validate the fast-route contracts and report catalog coverage."""

    contracts_path = resolve_contracts_path(optional_string(args, "contracts_path"))
    max_missing = optional_int(args, "max_missing_per_family", default=5, minimum=0, maximum=50)
    payload = validate_contracts(contracts_path, SKILL_ROOT)
    coverage = payload["coverage"]
    rows = coverage_rows(coverage, max_missing=max_missing)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "server": "visualization",
        "database": "bioinformatics.visualization",
        "tool": COVERAGE_TOOL,
        "ok": payload["ok"],
        "contracts": payload["contracts"],
        "template_count": payload["template_count"],
        "catalog_template_count": payload["catalog_template_count"],
        "coverage": coverage,
        "errors": payload["errors"],
        "warnings": payload["warnings"],
        "records": [coverage_record(payload, rows)],
        "source": source_info("validate_template_contracts", {"contracts_path": str(contracts_path)}),
    }
    response["provenance"] = response["source"]
    return response


def omics_visualization_status(args: JsonObject) -> JsonObject:
    """Return local visualization MCP capabilities and script availability."""

    include_coverage = optional_bool(args, "include_coverage", default=True)
    tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "server": "visualization",
        "version": "0.1.0",
        "database": "bioinformatics.visualization",
        "tool": STATUS_TOOL,
        "available_tool_count": len(tools),
        "available_tools": tools,
        "skill_root": str(SKILL_ROOT),
        "contracts_path": str(DEFAULT_CONTRACTS),
        "scripts": {
            "route_template": str(SCRIPT_DIR / "route_template.py"),
            "validate_template_contracts": str(SCRIPT_DIR / "validate_template_contracts.py"),
            "qa_single_plot": str(SCRIPT_DIR / "qa_single_plot.py"),
        },
        "script_files_available": {
            "route_template": (SCRIPT_DIR / "route_template.py").is_file(),
            "validate_template_contracts": (SCRIPT_DIR / "validate_template_contracts.py").is_file(),
            "qa_single_plot": (SCRIPT_DIR / "qa_single_plot.py").is_file(),
        },
        "frontend_components": ["dataset"],
        "preview_kinds": ["table"],
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "records": [],
        "source": source_info("visualization_status", {}),
    }
    if include_coverage:
        payload = validate_contracts(DEFAULT_CONTRACTS, SKILL_ROOT)
        status["contract_coverage"] = payload["coverage"]
        status["contracts_ok"] = payload["ok"]
        status["warnings"] = payload["warnings"]
        status["errors"] = payload["errors"]
    status["records"] = [status_record(status)]
    status["provenance"] = status["source"]
    return status


def resolve_table_path(value: str, base_dir: str = "") -> Path:
    raw = Path(value).expanduser()
    if raw.is_absolute():
        path = raw.resolve(strict=False)
    elif base_dir:
        path = (Path(base_dir).expanduser() / raw).resolve(strict=False)
    else:
        path = (Path.cwd() / raw).resolve(strict=False)
    if not path.exists():
        raise McpError(-32602, f"table_path does not exist: {path}")
    if not path.is_file():
        raise McpError(-32602, f"table_path must point to a file: {path}")
    return path


def resolve_contracts_path(value: str = "") -> Path:
    path = Path(value).expanduser().resolve(strict=False) if value else DEFAULT_CONTRACTS
    if not path.exists():
        raise McpError(-32602, f"contracts_path does not exist: {path}")
    if not path.is_file():
        raise McpError(-32602, f"contracts_path must point to a file: {path}")
    return path


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


def optional_mode(args: JsonObject) -> str:
    value = optional_string(args, "mode") or "preview"
    if value not in VALID_MODES:
        raise McpError(-32602, f"mode must be one of {', '.join(sorted(VALID_MODES))}")
    return value


def summarize_profile(profile: JsonObject) -> JsonObject:
    return {
        "path": profile.get("path"),
        "row_count": profile.get("row_count"),
        "sampled_rows": profile.get("sampled_rows"),
        "column_count": profile.get("column_count"),
        "columns": profile.get("columns", []),
        "shapes": profile.get("shapes", []),
        "role_mapping": profile.get("role_mapping", {}),
        "numeric_columns": profile.get("numeric_columns", []),
        "text_columns": profile.get("text_columns", []),
    }


def route_next_steps(selected: JsonObject | None) -> list[str]:
    if selected is None:
        return [
            "Inspect the full visualization catalog because no fast-route template was selected.",
            "Add or improve template contracts for this table shape if the catalog contains a suitable template.",
        ]
    steps = [
        f"Inspect {selected['source']} before rendering if this will be publication-facing.",
        "Use the reported role_mapping when preparing the template input table.",
        "Run qa_single_plot.py on the rendered PNG/SVG before presenting the figure.",
    ]
    if selected.get("confidence") != "high":
        steps.insert(0, "Review the full catalog because the fast-route confidence is not high.")
    return steps


def route_record(response: JsonObject) -> JsonObject:
    selected = response.get("selected") if isinstance(response.get("selected"), dict) else {}
    selected_id = str(selected.get("id") or "none")
    title = f"Visualization route: {selected_id}"
    rows = recommendation_rows(response.get("recommendations", []))
    profile = response.get("input_profile_summary", {})
    links = [
        {
            "label": "Selected template",
            "url": route_url(selected_id),
            "kind": "internal",
            "primary": True,
        }
    ]
    return dataset_record(
        record_type="omics_visualization_route",
        record_id=f"visualization-route:{selected_id}",
        title=title,
        description="Fast-route template recommendations from local result-table profiling.",
        chip_label="visualization route",
        subtitle=f"{len(rows)} recommendations | mode={response.get('mode')}",
        metadata=compact_fields(
            ("Selected", selected_id),
            ("Confidence", selected.get("confidence", "")),
            ("Score", selected.get("score", "")),
            ("Rows", profile.get("row_count", "")),
            ("Columns", profile.get("column_count", "")),
            ("Shapes", ", ".join(profile.get("shapes", []))),
        ),
        badges=compact_badges(
            ("Visualization", "source"),
            (str(response.get("mode") or ""), "mode"),
            (str(selected.get("confidence") or ""), "confidence"),
        ),
        links=links,
        previews=[
            {
                "kind": "table",
                "title": "Template recommendations",
                "section_key": "recommendations",
                "data": {
                    "columns": ["rank", "template_id", "family", "confidence", "score", "matched_shapes", "role_mapping", "risks"],
                    "rows": rows,
                },
            }
        ],
        sections=[
            {"key": "overview", "title": "Overview", "kind": "table", "rows": compact_fields(("Query", response.get("query", "")), ("Input", profile.get("path", "")), ("Contracts", response.get("input", {}).get("contracts_path", "")))},
            {"key": "recommendations", "title": "Template recommendations", "kind": "table", "rows": rows},
        ],
        data={
            "selected": selected,
            "recommendations": response.get("recommendations", []),
            "input_profile_summary": profile,
            "next_steps": response.get("next_steps", []),
        },
    )


def coverage_record(payload: JsonObject, rows: list[JsonObject]) -> JsonObject:
    coverage = payload["coverage"]
    links = [
        {
            "label": "Contract coverage",
            "url": f"{LOCAL_ROUTE_BASE_URL}/contract-coverage",
            "kind": "internal",
            "primary": True,
        }
    ]
    return dataset_record(
        record_type="omics_visualization_contract_coverage",
        record_id="visualization-contract-coverage",
        title="Visualization contract coverage",
        description="Validation summary for fast-route template contracts.",
        chip_label="contract coverage",
        subtitle=f"{coverage['contracted']} / {coverage['catalog_total']} templates contracted",
        metadata=compact_fields(
            ("Contracts", coverage["contracted"]),
            ("Catalog templates", coverage["catalog_total"]),
            ("Coverage", f"{coverage['coverage_ratio']:.1%}"),
            ("Errors", len(payload["errors"])),
            ("Warnings", len(payload["warnings"])),
        ),
        badges=compact_badges(("Visualization", "source"), ("PASS" if payload["ok"] else "FAIL", "status")),
        links=links,
        previews=[
            {
                "kind": "table",
                "title": "Coverage by family",
                "section_key": "coverage_by_family",
                "data": {
                    "columns": ["family", "contracted", "catalog_total", "coverage_ratio", "missing_count", "missing_preview"],
                    "rows": rows,
                },
            }
        ],
        sections=[{"key": "coverage_by_family", "title": "Coverage by family", "kind": "table", "rows": rows}],
        data={"coverage": coverage, "errors": payload["errors"], "warnings": payload["warnings"]},
    )


def status_record(status: JsonObject) -> JsonObject:
    coverage = status.get("contract_coverage", {})
    rows = [
        {"name": key, "available": value}
        for key, value in status.get("script_files_available", {}).items()
    ]
    links = [
        {
            "label": "Visualization MCP status",
            "url": f"{LOCAL_ROUTE_BASE_URL}/status",
            "kind": "internal",
            "primary": True,
        }
    ]
    return dataset_record(
        record_type="omics_visualization_status",
        record_id="visualization-status",
        title="Omics visualization MCP status",
        description="Local script availability and frontend rendering contract status.",
        chip_label="visualization MCP",
        subtitle=f"{status['available_tool_count']} tools | {coverage.get('contracted', 0)} fast-route contracts",
        metadata=compact_fields(
            ("Tools", status["available_tool_count"]),
            ("Contracts OK", status.get("contracts_ok", "")),
            ("Contracted templates", coverage.get("contracted", "")),
            ("Catalog templates", coverage.get("catalog_total", "")),
            ("Skill root", status.get("skill_root", "")),
        ),
        badges=compact_badges(("Visualization", "source"), ("MCP", "server")),
        links=links,
        previews=[
            {
                "kind": "table",
                "title": "Script availability",
                "section_key": "scripts",
                "data": {"columns": ["name", "available"], "rows": rows},
            }
        ],
        sections=[{"key": "scripts", "title": "Script availability", "kind": "table", "rows": rows}],
        data={
            "available_tools": status["available_tools"],
            "scripts": status["scripts"],
            "frontend_components": status["frontend_components"],
            "preview_kinds": status["preview_kinds"],
        },
    )


def dataset_record(
    *,
    record_type: str,
    record_id: str,
    title: str,
    description: str,
    chip_label: str,
    subtitle: str,
    metadata: list[JsonObject],
    badges: list[JsonObject],
    links: list[JsonObject],
    previews: list[JsonObject],
    sections: list[JsonObject],
    data: JsonObject,
) -> JsonObject:
    url = route_url(record_id)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.visualization",
        "record_type": record_type,
        "database": "bioinformatics.visualization",
        "id": record_id,
        "stable_id": record_id,
        "label": chip_label,
        "title": title,
        "description": description,
        "url": url,
        "icon": "chart",
        "links": links,
        "display": {
            "component": "dataset",
            "chip_label": chip_label,
            "icon": "chart",
            "title": title,
            "subtitle": subtitle,
            "description": description,
            "metadata": metadata,
            "badges": badges,
            "actions": display_actions(links),
            "hover": {"title": title, "subtitle": subtitle, "icon": "chart", "fields": metadata},
            "primary_url": url,
            "sections": sections,
            "previews": previews,
        },
        "data": data,
    }


def recommendation_rows(recommendations: object) -> list[JsonObject]:
    rows: list[JsonObject] = []
    if not isinstance(recommendations, list):
        return rows
    for rank, item in enumerate(recommendations, start=1):
        if not isinstance(item, dict):
            continue
        role_mapping = item.get("role_mapping", {})
        rows.append(
            {
                "rank": rank,
                "template_id": item.get("id", ""),
                "family": item.get("family", ""),
                "confidence": item.get("confidence", ""),
                "score": item.get("score", ""),
                "matched_shapes": ", ".join(item.get("matched_shapes", [])),
                "role_mapping": ", ".join(f"{key}={value}" for key, value in sorted(role_mapping.items())),
                "risks": "; ".join(item.get("risks", [])),
            }
        )
    return rows


def coverage_rows(coverage: JsonObject, *, max_missing: int) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for row in coverage.get("by_family", []):
        missing = row.get("missing", [])
        if not isinstance(missing, list):
            missing = []
        rows.append(
            {
                "family": row.get("family", ""),
                "contracted": row.get("contracted", 0),
                "catalog_total": row.get("catalog_total", 0),
                "coverage_ratio": row.get("coverage_ratio", 0.0),
                "missing_count": len(missing),
                "missing_preview": ", ".join(str(item) for item in missing[:max_missing]),
            }
        )
    return rows


def compact_fields(*pairs: tuple[str, Any]) -> list[JsonObject]:
    fields: list[JsonObject] = []
    for label, value in pairs:
        if value is None or value == "":
            continue
        fields.append({"label": label, "value": value})
    return fields


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    return [{"label": label, "kind": kind} for label, kind in pairs if label]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [
        {"label": str(link["label"]), "url": str(link["url"])}
        for link in links
        if link.get("label") and link.get("url")
    ]


def route_url(identifier: str) -> str:
    return f"{LOCAL_ROUTE_BASE_URL}/{urllib.parse.quote(str(identifier), safe='')}"


def source_info(endpoint: str, params: JsonObject) -> JsonObject:
    return {
        "database": "bioinformatics.visualization",
        "endpoint": endpoint,
        "params": dict(params),
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def tool_definitions() -> list[JsonObject]:
    return [
        {
            "name": ROUTE_TOOL,
            "title": "Route omics visualization template",
            "description": "Profile a local CSV/TSV result table and return scored visualization template recommendations with data-shape and role-mapping rationale.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "table_path": {"type": "string", "description": "Local CSV/TSV result table to profile."},
                    "query": {"type": "string", "description": "User intent, figure purpose, or an exact template ID such as heatmap-corr-bubble."},
                    "base_dir": {"type": "string", "description": "Optional directory for resolving a relative table_path."},
                    "mode": {"type": "string", "enum": sorted(VALID_MODES), "default": "preview"},
                    "top": {"type": "integer", "minimum": 1, "maximum": MAX_TOP_RECOMMENDATIONS, "default": DEFAULT_TOP_RECOMMENDATIONS},
                    "contracts_path": {"type": "string", "description": "Optional local template_contracts.json override."},
                    "include_profile": {"type": "boolean", "default": True},
                    "include_contract_coverage": {"type": "boolean", "default": False},
                },
                "required": ["table_path", "query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
        {
            "name": COVERAGE_TOOL,
            "title": "Inspect visualization contract coverage",
            "description": "Validate fast-route template contracts against the local visualization catalog and report family-level coverage.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "contracts_path": {"type": "string", "description": "Optional local template_contracts.json override."},
                    "max_missing_per_family": {"type": "integer", "minimum": 0, "maximum": 50, "default": 5},
                },
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
        {
            "name": STATUS_TOOL,
            "title": "Inspect omics visualization MCP status",
            "description": "Return local visualization MCP tools, script paths, frontend record hints, and optional contract coverage.",
            "inputSchema": {
                "type": "object",
                "properties": {"include_coverage": {"type": "boolean", "default": True}},
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True, "openWorldHint": False},
        },
    ]


TOOL_HANDLERS = {
    ROUTE_TOOL: omics_visualization_route,
    COVERAGE_TOOL: omics_visualization_contract_coverage,
    STATUS_TOOL: omics_visualization_status,
}
