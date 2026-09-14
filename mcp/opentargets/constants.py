"""Shared constants for the Open Targets MCP server."""

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
OPENTARGETS_GRAPHQL_URL = "https://api.platform.opentargets.org/api/v4/graphql"
OPENTARGETS_WEBSITE_BASE_URL = "https://platform.opentargets.org"
DEFAULT_TOOL_NAME = "codex-bioinformatics-opentargets-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.opentargets.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 50
DEFAULT_ENTITY_NAMES = ["target", "disease"]

JsonObject = dict[str, Any]
