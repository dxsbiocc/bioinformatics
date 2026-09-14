"""Shared constants for the omics visualization MCP server."""

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
RESULT_SCHEMA_VERSION = "bioinformatics.visualization.route.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
DEFAULT_TOP_RECOMMENDATIONS = 4
MAX_TOP_RECOMMENDATIONS = 12

JsonObject = dict[str, Any]

