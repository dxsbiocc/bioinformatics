"""Shared constants for the QuickGO MCP server."""

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
QUICKGO_API_BASE_URL = "https://www.ebi.ac.uk/QuickGO/services"
QUICKGO_WEBSITE_BASE_URL = "https://www.ebi.ac.uk/QuickGO"
DEFAULT_TOOL_NAME = "codex-bioinformatics-quickgo-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.quickgo.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
DEFAULT_RESULTS = 10
MAX_RELATIONS = 100

JsonObject = dict[str, Any]

