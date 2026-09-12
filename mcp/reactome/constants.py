"""Shared constants for the Reactome MCP server."""

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
REACTOME_CONTENT_API_BASE_URL = "https://reactome.org/ContentService"
REACTOME_WEBSITE_BASE_URL = "https://reactome.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-reactome-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.reactome.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_SEARCH_RESULTS = 25
MAX_PARTICIPANTS = 100
MAX_PREVIEW_PARTICIPANTS = 40
MAX_REFERENCES = 25

JsonObject = dict[str, Any]

