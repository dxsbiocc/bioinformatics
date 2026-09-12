"""Shared constants for the STRING MCP server."""

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
STRING_API_BASE_URL = "https://string-db.org/api"
STRING_WEBSITE_BASE_URL = "https://string-db.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-string-mcp"
DEFAULT_CALLER_IDENTITY = "codex-bioinformatics-string-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.string.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_IDENTIFIERS = 100
MAX_INTERACTIONS = 100

JsonObject = dict[str, Any]

