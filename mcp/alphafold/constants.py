"""Shared constants for the AlphaFold MCP server."""

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
ALPHAFOLD_API_BASE_URL = "https://alphafold.ebi.ac.uk/api"
ALPHAFOLD_WEBSITE_BASE_URL = "https://alphafold.ebi.ac.uk"
UNIPROT_WEBSITE_BASE_URL = "https://www.uniprot.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-alphafold-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.alphafold.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_MODELS = 100

JsonObject = dict[str, Any]

