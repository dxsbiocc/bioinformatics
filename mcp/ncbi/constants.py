"""Shared constants for the NCBI MCP server."""

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
NCBI_EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
DEFAULT_TOOL_NAME = "codex-bioinformatics-ncbi-mcp"
MAX_PUBMED_IDS = 200
MAX_GEO_IDS = 200
RESULT_SCHEMA_VERSION = "bioinformatics.ncbi.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
CITATION_SCHEMA_VERSION = "bioinformatics.citation.v1"

JsonObject = dict[str, Any]
