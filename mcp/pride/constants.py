"""Shared constants for the PRIDE Archive MCP server."""

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
PRIDE_API_BASE_URL = "https://www.ebi.ac.uk/pride/ws/archive/v2"
PRIDE_WEBSITE_BASE_URL = "https://www.ebi.ac.uk/pride/archive"
DEFAULT_TOOL_NAME = "codex-bioinformatics-pride-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.pride.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
DEFAULT_RESULTS = 10
MAX_FILES = 100
DEFAULT_FILES = 20

JsonObject = dict[str, Any]

