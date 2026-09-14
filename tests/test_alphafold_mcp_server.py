from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "alphafold" / "server.py"
SPEC = importlib.util.spec_from_file_location("alphafold_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
alphafold = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = alphafold
SPEC.loader.exec_module(alphafold)


class FakeClient:
    def __init__(self) -> None:
        self.config = alphafold.AlphaFoldConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_array_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "prediction/P04637":
            return ALPHAFOLD_PREDICTIONS, {
                "content-type": "application/json",
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")


ALPHAFOLD_PREDICTIONS = [
    {
        "entryId": "AF-P04637-F1",
        "uniprotAccession": "P04637",
        "uniprotId": "P53_HUMAN",
        "gene": "TP53",
        "uniprotDescription": "Cellular tumor antigen p53",
        "organismScientificName": "Homo sapiens",
        "taxId": 9606,
        "sequenceStart": 1,
        "sequenceEnd": 393,
        "globalMetricValue": 75.06,
        "fractionPlddtVeryHigh": 0.25,
        "fractionPlddtConfident": 0.45,
        "fractionPlddtLow": 0.2,
        "fractionPlddtVeryLow": 0.1,
        "latestVersion": 6,
        "allVersions": [1, 2, 3, 4, 5, 6],
        "modelCreatedDate": "2025-02-01",
        "sequenceVersionDate": "2024-01-01",
        "toolUsed": "AlphaFold Monomer v2.0",
        "isReviewed": True,
        "isUniProt": True,
        "isReferenceProteome": True,
        "isComplex": False,
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.pdb",
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.cif",
        "bcifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.bcif",
        "paeDocUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-predicted_aligned_error_v6.json",
        "paeImageUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-predicted_aligned_error_v6.png",
        "plddtDocUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-confidence_v6.json",
        "msaUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-msa_v6.a3m",
        "sequence": "MEEPQSDPSV",
    },
    {
        "entryId": "AF-P04637-2-F1",
        "uniprotAccession": "P04637-2",
        "uniprotId": "P53_HUMAN",
        "gene": "TP53",
        "organismScientificName": "Homo sapiens",
        "taxId": 9606,
        "sequenceStart": 1,
        "sequenceEnd": 341,
        "globalMetricValue": 76.94,
        "latestVersion": 6,
        "modelCreatedDate": "2025-02-01",
        "pdbUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-2-F1-model_v6.pdb",
        "cifUrl": "https://alphafold.ebi.ac.uk/files/AF-P04637-2-F1-model_v6.cif",
    },
]


class AlphaFoldMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = alphafold.AlphaFoldMcpServer(self.client)

    def call_tool(self, name, arguments):
        response = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments,
                },
            }
        )
        assert response is not None
        return response["result"]["structuredContent"]

    def test_tools_list_exposes_alphafold_tools(self) -> None:
        response = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, {"alphafold_parameter_domains", "alphafold_lookup", "alphafold_status"})

    def test_lookup_returns_frontend_compatible_structure_records(self) -> None:
        result = self.call_tool(
            "alphafold_lookup",
            {
                "accession": "P04637",
                "include_sequence": True,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein_structure"},
            required_preview_kinds={"structure_3d", "download_manifest", "sequence"},
        )
        self.assertEqual(result["schema_version"], "bioinformatics.alphafold.result.v1")
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["source"]["endpoint"], "prediction/P04637")
        record = result["records"][0]
        self.assertEqual(record["record_type"], "alphafold_prediction")
        self.assertEqual(record["stable_id"], "AlphaFold:AF-P04637-F1")
        self.assertEqual(record["display"]["component"], "protein_structure")
        self.assertEqual(record["identifiers"]["uniprot"]["label"], "UniProtKB:P04637")
        self.assertEqual(record["related"]["downloads"][0]["label"], "PDB")
        preview_kinds = {preview["kind"] for preview in record["display"]["previews"]}
        self.assertIn("structure_3d", preview_kinds)
        self.assertIn("download_manifest", preview_kinds)
        self.assertIn("sequence", preview_kinds)
        structure_preview = next(
            preview
            for preview in record["display"]["previews"]
            if preview["kind"] == "structure_3d"
        )
        self.assertEqual(structure_preview["provider"], "AlphaFold DB")
        self.assertEqual(
            structure_preview["data"]["pdb_url"],
            "https://alphafold.ebi.ac.uk/files/AF-P04637-F1-model_v6.pdb",
        )

    def test_lookup_can_filter_to_canonical_model(self) -> None:
        result = self.call_tool(
            "alphafold_lookup",
            {
                "accession": "P04637",
                "canonical_only": True,
            },
        )
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["matching"], 1)
        self.assertEqual(result["records"][0]["id"], "AF-P04637-F1")

    def test_status_reports_preview_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("alphafold_status", {})
        self.assertEqual(result["server"], "alphafold")
        self.assertIn("alphafold_lookup", result["available_tools"])
        self.assertIn("structure_3d", result["preview_kinds"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
