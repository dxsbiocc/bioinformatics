"""Shared constants for the Human Protein Atlas MCP server."""

from __future__ import annotations

from typing import Any

LATEST_PROTOCOL_VERSION = "2025-11-25"
SUPPORTED_PROTOCOL_VERSIONS = {
    LATEST_PROTOCOL_VERSION,
    "2025-06-18",
    "2025-03-26",
    "2024-11-05",
    "2024-10-07",
}

JSONRPC_VERSION = "2.0"
HPA_BASE_URL = "https://www.proteinatlas.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-hpa-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.hpa.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
DEFAULT_RESULTS = 10

JsonObject = dict[str, Any]

