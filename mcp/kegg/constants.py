"""Shared constants for the KEGG MCP server."""

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
KEGG_REST_BASE_URL = "https://rest.kegg.jp"
KEGG_WEBSITE_BASE_URL = "https://www.kegg.jp"
DEFAULT_TOOL_NAME = "codex-bioinformatics-kegg-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.kegg.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"

MAX_RESULTS = 500
DEFAULT_MAX_RESULTS = 25
MAX_GET_ENTRIES = 10
MAX_COLOR_ITEMS = 500

FIND_OPTIONS = ["formula", "exact_mass", "mol_weight", "nop"]
GET_OPTIONS = [
    "aaseq",
    "ntseq",
    "mol",
    "kcf",
    "image",
    "image2x",
    "conf",
    "kgml",
    "json",
]
LINK_OPTIONS = [
    "species",
    "genus",
    "family",
    "order",
    "class",
    "phylum",
    "turtle",
    "n-triple",
]
COLOR_URL_FORMS = ["query", "slash"]

COMMON_DATABASES = [
    "pathway",
    "brite",
    "module",
    "ko",
    "genome",
    "genes",
    "compound",
    "glycan",
    "reaction",
    "rclass",
    "enzyme",
    "network",
    "variant",
    "disease",
    "drug",
    "dgroup",
    "environ",
]

JsonObject = dict[str, Any]
