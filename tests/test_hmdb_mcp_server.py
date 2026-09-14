from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "hmdb" / "server.py"
SPEC = importlib.util.spec_from_file_location("hmdb_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
hmdb = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = hmdb
SPEC.loader.exec_module(hmdb)


class FakeClient:
    def __init__(self) -> None:
        self.config = hmdb.HmdbConfig(contact=None)
        self.requests_per_second = 1
        self.calls = []

    def search_json_with_headers(self, query, category, max_results):
        self.calls.append((query, category, max_results))
        payload = {
            "metabolites": METABOLITES,
            "proteins": PROTEINS,
            "diseases": DISEASES,
            "pathways": PATHWAYS,
        }[category]
        return {category: payload, "total": len(payload)}, {"content-type": "application/json"}, f"https://hmdb.ca/unearth/q?query={query}&category={category}"


METABOLITES = [
    {
        "hmdb_id": "HMDB0000259",
        "name": "Serotonin",
        "description": "Serotonin is a monoamine neurotransmitter and human metabolite.",
        "chemical_formula": "C10H12N2O",
        "molecular_weight": "176.22",
        "smiles": "C1=CC2=C(C=C1O)C(=CN2)CCN",
        "inchi_key": "QZAYGJVTTNCVMB-UHFFFAOYSA-N",
        "class": "Indoles and derivatives",
        "synonyms": ["5-hydroxytryptamine", "5-HT"],
        "pubchem_cid": "5202",
        "chebi_id": "CHEBI:28790",
    }
]

PROTEINS = [
    {
        "protein_id": "HMDBP00001",
        "name": "Serum albumin",
        "description": "A transport protein associated with multiple metabolites.",
        "gene_name": "ALB",
        "uniprot_id": "P02768",
        "organism": "Homo sapiens",
        "sequence": "MKWVTFISLLLLFSSAYSRGVFRRDAHKSEVAHRFKDLGEENFKALVLIAFAQYLQQCPF",
    }
]

DISEASES = [
    {
        "disease_id": "HDB00001",
        "name": "Diabetes mellitus",
        "description": "A metabolic disease group characterized by chronic hyperglycemia.",
        "associated_pathways": ["Glucose metabolism"],
    }
]

PATHWAYS = [
    {
        "pathway_id": "SMP0000064",
        "name": "Glycolysis",
        "description": "A central carbohydrate metabolism pathway.",
        "associated_diseases": ["Diabetes mellitus"],
    }
]


class HmdbMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = hmdb.HmdbMcpServer(self.client)

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

    def test_tools_list_exposes_hmdb_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "hmdb_parameter_domains",
                "hmdb_search",
                "hmdb_metabolite_search",
                "hmdb_protein_search",
                "hmdb_disease_search",
                "hmdb_pathway_search",
                "hmdb_status",
            },
        )

    def test_metabolite_search_returns_frontend_compatible_compound_record(self) -> None:
        result = self.call_tool("hmdb_metabolite_search", {"query": "serotonin", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"table", "chemical_structure", "xref_groups", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["id"], "HMDB0000259")
        self.assertEqual(record["data"]["formula"], "C10H12N2O")

    def test_protein_search_returns_frontend_compatible_protein_record(self) -> None:
        result = self.call_tool("hmdb_protein_search", {"query": "albumin", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein"},
            required_preview_kinds={"table", "sequence", "xref_groups", "text"},
        )
        self.assertEqual(result["records"][0]["data"]["uniprot_id"], "P02768")

    def test_disease_search_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool("hmdb_disease_search", {"query": "diabetes", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "text"},
        )

    def test_pathway_search_returns_frontend_compatible_pathway_record(self) -> None:
        result = self.call_tool("hmdb_pathway_search", {"query": "glycolysis", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"table", "text"},
        )

    def test_generic_search_uses_requested_category(self) -> None:
        result = self.call_tool("hmdb_search", {"query": "glycolysis", "category": "pathways", "max_results": 1})
        self.assertEqual(result["category"], "pathways")
        self.assertEqual(self.client.calls[-1], ("glycolysis", "pathways", 1))

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("hmdb_status", {})
        self.assertEqual(result["server"], "hmdb")
        self.assertIn("hmdb_metabolite_search", result["available_tools"])
        self.assertIn("compound", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("hmdb_status", {"check_network": True})
        self.assertEqual(result["network_check"]["returned"], 1)
        self.assertEqual(result["network_check"]["content_type"], "application/json")

    def test_client_reports_cloudflare_challenge_as_hmdb_error(self) -> None:
        html = "<html><title>Just a moment...</title><script>window._cf_chl_opt={}</script></html>"
        client = hmdb.HmdbClient(opener=lambda request, timeout: (html, {"cf-mitigated": "challenge", "content-type": "text/html"}))
        with self.assertRaises(hmdb.HmdbError) as raised:
            client.search_json_with_headers("serotonin", "metabolites", 1)
        self.assertIn("Cloudflare challenge", str(raised.exception))


if __name__ == "__main__":
    unittest.main()

