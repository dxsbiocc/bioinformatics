"""Shared constants for the PubChem MCP server."""

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
PUBCHEM_PUG_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"
PUBCHEM_WEBSITE_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov"
DEFAULT_TOOL_NAME = "codex-bioinformatics-pubchem-mcp"
RESULT_SCHEMA_VERSION = "bioinformatics.pubchem.result.v1"
RECORD_SCHEMA_VERSION = "bioinformatics.record.v1"
MAX_RESULTS = 20
MAX_SYNONYMS = 20
MAX_XREFS = 30

COMPOUND_PROPERTY_FIELDS = [
    "Title",
    "MolecularFormula",
    "MolecularWeight",
    "SMILES",
    "ConnectivitySMILES",
    "CanonicalSMILES",
    "IsomericSMILES",
    "InChI",
    "InChIKey",
    "IUPACName",
    "XLogP",
    "TPSA",
    "HBondDonorCount",
    "HBondAcceptorCount",
    "RotatableBondCount",
    "ExactMass",
    "MonoisotopicMass",
    "Charge",
]

JsonObject = dict[str, Any]
