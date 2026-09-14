"""Shared constants for the ENCODE MCP server."""

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
ENCODE_BASE_URL = "https://www.encodeproject.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-encode-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.encode.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_RESULTS = 5
MAX_RESULTS = 25
DEFAULT_FILES = 10
MAX_FILES = 50

JsonObject = dict[str, Any]

