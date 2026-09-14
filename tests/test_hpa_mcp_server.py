from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "hpa" / "server.py"
SPEC = importlib.util.spec_from_file_location("hpa_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
hpa = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = hpa
SPEC.loader.exec_module(hpa)


class FakeClient:
    def __init__(self) -> None:
        self.config = hpa.HpaConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "ENSG00000141510.json":
            return HPA_TP53, {"content-type": "application/json"}
        if endpoint == "api/search_download.php":
            return HPA_SEARCH, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


HPA_TP53 = {
    "Gene": "TP53",
    "Gene synonym": ["BCC7", "LFS1", "P53"],
    "Ensembl": "ENSG00000141510",
    "Gene description": "tumor protein p53",
    "Uniprot": ["P04637"],
    "Chromosome": "17",
    "Position": "17p13.1",
    "Protein class": ["Disease related genes", "Transcription factors"],
    "Biological process": ["Apoptosis"],
    "Molecular function": ["DNA-binding transcription factor activity"],
    "Disease involvement": ["Cancer-related genes"],
    "Evidence": "Evidence at protein level",
    "RNA tissue specificity": "Low tissue specificity",
    "RNA tissue distribution": "Detected in all",
    "RNA single cell type specificity": "Cell type enhanced",
    "RNA single cell type distribution": "Detected in many",
    "RNA cancer specificity": "Low cancer specificity",
    "RNA cancer distribution": "Detected in all",
    "Protein tissue specificity": "Low tissue specificity",
    "Protein tissue distribution": "Detected in many",
    "Protein cell type specificity": "Low cell type specificity",
    "Protein cell type distribution": "Detected in many",
    "Subcellular location": ["Nucleoplasm"],
    "Subcellular main location": ["Nucleoplasm"],
    "Antibody": ["CAB000009"],
    "Reliability (IH)": "Supported",
    "Reliability (IF)": "Supported",
    "Interactions": 162,
    "Cancer prognostics - renal cancer": {
        "prognostic type": "unfavorable",
        "prognostic": "unfavorable",
        "is_prognostic": True,
        "p_val": "0.00012",
    },
}


HPA_SEARCH = [
    {
        "Gene": "TP53",
        "Gene synonym": ["P53"],
        "Ensembl": "ENSG00000141510",
        "Gene description": "tumor protein p53",
        "Uniprot": ["P04637"],
        "Evidence": "Evidence at protein level",
    },
    {
        "Gene": "TP53TG1",
        "Gene synonym": ["TP53 target 1"],
        "Ensembl": "ENSG00000232348",
        "Gene description": "TP53 target 1",
        "Uniprot": [],
        "Evidence": "Evidence at transcript level",
    },
]


class HpaMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = hpa.HpaMcpServer(self.client)

    def call_tool(self, name, arguments):
        response = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        assert response is not None
        return response["result"]["structuredContent"]

    def test_tools_list_exposes_hpa_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, {"hpa_parameter_domains", "hpa_gene_lookup", "hpa_search", "hpa_status"})

    def test_gene_lookup_returns_frontend_compatible_gene_record(self) -> None:
        result = self.call_tool("hpa_gene_lookup", {"ensembl_id": "ensg00000141510"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["gene"], "TP53")
        self.assertEqual(record["data"]["ensembl"], "ENSG00000141510")
        self.assertNotIn("raw", record["data"])
        self.assertEqual(record["related"]["cancer_prognostics"][0]["cancer"], "renal cancer")
        self.assertEqual(result["source"]["url"], "https://www.proteinatlas.org/ENSG00000141510.json")
        action_urls = {action["url"] for action in record["display"]["actions"]}
        self.assertIn("https://www.proteinatlas.org/ENSG00000141510.json", action_urls)
        self.assertIn("https://www.uniprot.org/uniprotkb/P04637/entry", action_urls)

    def test_gene_lookup_can_include_raw_payload_explicitly(self) -> None:
        result = self.call_tool("hpa_gene_lookup", {"ensembl_id": "ENSG00000141510", "include_raw": True})
        self.assertEqual(result["raw"]["Gene"], "TP53")
        self.assertNotIn("raw", result["records"][0]["data"])

    def test_search_returns_bounded_frontend_compatible_gene_records(self) -> None:
        result = self.call_tool("hpa_search", {"query": "TP53", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"table", "xref_groups"},
            min_records=2,
        )
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["records"][0]["stable_id"], "ENSG00000141510")
        self.assertIn("api/search_download.php", result["source"]["url"])
        self.assertEqual(self.client.calls[-1][1]["columns"], "g,gs,eg,gd,up,pe")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("hpa_status", {})
        self.assertEqual(result["server"], "hpa")
        self.assertIn("hpa_gene_lookup", result["available_tools"])
        self.assertIn("gene", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("hpa_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_gene"], "TP53")
        self.assertEqual(result["network_check"]["example_ensembl"], "ENSG00000141510")


if __name__ == "__main__":
    unittest.main()
