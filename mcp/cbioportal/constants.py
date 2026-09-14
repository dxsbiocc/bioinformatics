"""Shared constants for the cBioPortal MCP server."""

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
CBIOPORTAL_API_BASE_URL = "https://www.cbioportal.org/api"
CBIOPORTAL_WEBSITE_BASE_URL = "https://www.cbioportal.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-cbioportal-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.cbioportal.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_RESULTS = 10
MAX_RESULTS = 50
DEFAULT_MUTATIONS = 25
MAX_MUTATIONS = 200
DEFAULT_MOLECULAR_ROWS = 100
MAX_MOLECULAR_ROWS = 500
DEFAULT_CLINICAL_IDS = 25
MAX_CLINICAL_IDS = 100
MAX_CLINICAL_ATTRIBUTES = 50
DEFAULT_SURVIVAL_PREFIXES = ["OS", "DFS"]
MAX_SURVIVAL_PREFIXES = 8

JsonObject = dict[str, Any]
