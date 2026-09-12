"""Shared constants for the HMDB MCP server."""

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
HMDB_BASE_URL = "https://hmdb.ca"
DEFAULT_TOOL_NAME = "codex-bioinformatics-hmdb-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.hmdb.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_RESULTS = 10
MAX_RESULTS = 30
SEARCH_PATH = "unearth/q"
HMDB_CATEGORIES = {"metabolites", "proteins", "diseases", "pathways"}

JsonObject = dict[str, Any]

