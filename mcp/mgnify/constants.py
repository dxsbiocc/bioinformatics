"""Shared constants for the MGnify MCP server."""

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
MGNIFY_API_BASE_URL = "https://www.ebi.ac.uk/metagenomics/api/v1"
MGNIFY_WEBSITE_BASE_URL = "https://www.ebi.ac.uk/metagenomics"
DEFAULT_TOOL_NAME = "codex-bioinformatics-mgnify-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.mgnify.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 25
DEFAULT_RESULTS = 5

JsonObject = dict[str, Any]

