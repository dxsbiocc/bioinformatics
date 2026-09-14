"""Shared constants for the RNAcentral MCP server."""

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
RNACENTRAL_API_BASE_URL = "https://rnacentral.org/api/v1"
RNACENTRAL_WEBSITE_BASE_URL = "https://rnacentral.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-rnacentral-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.rnacentral.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_RESULTS = 10
MAX_RESULTS = 30
DEFAULT_PAGE = 1

JsonObject = dict[str, Any]

