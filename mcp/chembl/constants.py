"""Shared constants for the ChEMBL MCP server."""

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
CHEMBL_REST_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"
CHEMBL_WEBSITE_BASE_URL = "https://www.ebi.ac.uk/chembl"
DEFAULT_TOOL_NAME = "codex-bioinformatics-chembl-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.chembl.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
MAX_SYNONYMS = 20
MAX_XREFS = 30

JsonObject = dict[str, Any]
