"""Shared constants for the Ensembl MCP server."""

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
ENSEMBL_REST_BASE_URL = "https://rest.ensembl.org"
ENSEMBL_WEBSITE_BASE_URL = "https://www.ensembl.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-ensembl-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.ensembl.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
MAX_XREFS = 100
MAX_TRANSCRIPTS = 50

JsonObject = dict[str, Any]

