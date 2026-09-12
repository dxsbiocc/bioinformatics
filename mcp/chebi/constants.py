"""Shared constants for the ChEBI MCP server."""

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
CHEBI_API_BASE_URL = "https://www.ebi.ac.uk"
CHEBI_WEBSITE_BASE_URL = "https://www.ebi.ac.uk/chebi"
DEFAULT_TOOL_NAME = "codex-bioinformatics-chebi-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.chebi.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_RESULTS = 10
MAX_RESULTS = 30
MAX_RELATIONS = 100
MAX_SYNONYMS = 25
MAX_XREFS = 50

JsonObject = dict[str, Any]

