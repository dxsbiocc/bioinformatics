"""Shared constants for the ClinVar MCP server."""

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
CLINICAL_TABLES_URL = "https://clinicaltables.nlm.nih.gov/api/variants/v4/search"
EUTILS_BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
NCBI_WEBSITE_BASE_URL = "https://www.ncbi.nlm.nih.gov"
DEFAULT_TOOL_NAME = "codex-bioinformatics-clinvar-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.clinvar.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 25
MAX_IDS_PER_SUMMARY = 50

JsonObject = dict[str, Any]

