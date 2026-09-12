"""Shared constants for the gnomAD MCP server."""

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
GNOMAD_GRAPHQL_URL = "https://gnomad.broadinstitute.org/api"
GNOMAD_WEBSITE_BASE_URL = "https://gnomad.broadinstitute.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-gnomad-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.gnomad.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_DATASET = "gnomad_r4"
DEFAULT_REFERENCE_GENOME = "GRCh38"
MAX_POPULATIONS = 100
MAX_TRANSCRIPTS = 100

JsonObject = dict[str, Any]

