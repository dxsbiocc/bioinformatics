"""Shared constants for the bioRxiv/medRxiv MCP server."""

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
BIORXIV_API_BASE_URL = "https://api.biorxiv.org"
BIORXIV_WEBSITE_BASE_URL = "https://www.biorxiv.org"
MEDRXIV_WEBSITE_BASE_URL = "https://www.medrxiv.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-biorxiv-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.biorxiv.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_RESULTS = 10
MAX_RESULTS = 30
DEFAULT_RECENT_DAYS = 7

SUPPORTED_SERVERS = {"biorxiv", "medrxiv"}

JsonObject = dict[str, Any]

