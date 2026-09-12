"""Shared constants for the CELLxGENE Discover MCP server."""

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
CELLXGENE_API_BASE_URL = "https://api.cellxgene.cziscience.com/curation/v1"
CELLXGENE_WEBSITE_BASE_URL = "https://cellxgene.cziscience.com"
DEFAULT_TOOL_NAME = "codex-bioinformatics-cellxgene-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.cellxgene.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
DEFAULT_RESULTS = 10
MAX_DATASETS = 100
DEFAULT_DATASETS = 20

JsonObject = dict[str, Any]

