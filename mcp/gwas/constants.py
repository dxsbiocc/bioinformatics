"""Shared constants for the GWAS Catalog MCP server."""

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
GWAS_REST_BASE_URL = "https://www.ebi.ac.uk/gwas/rest/api/v2"
GWAS_WEBSITE_BASE_URL = "https://www.ebi.ac.uk/gwas"
NCBI_PUBMED_BASE_URL = "https://pubmed.ncbi.nlm.nih.gov"
DEFAULT_TOOL_NAME = "codex-bioinformatics-gwas-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.gwas.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50

JsonObject = dict[str, Any]

