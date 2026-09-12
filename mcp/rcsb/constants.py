"""Shared constants for the RCSB PDB MCP server."""

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
RCSB_DATA_API_BASE_URL = "https://data.rcsb.org/rest/v1"
RCSB_SEARCH_API_BASE_URL = "https://search.rcsb.org/rcsbsearch/v2"
RCSB_WEBSITE_BASE_URL = "https://www.rcsb.org"
RCSB_FILES_BASE_URL = "https://files.rcsb.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-rcsb-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.rcsb.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_SEARCH_RESULTS = 25
MAX_ENTITY_SUMMARIES = 20

JsonObject = dict[str, Any]

