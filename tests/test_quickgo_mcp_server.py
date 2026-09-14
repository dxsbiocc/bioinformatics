from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "quickgo" / "server.py"
SPEC = importlib.util.spec_from_file_location("quickgo_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
quickgo = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = quickgo
SPEC.loader.exec_module(quickgo)


class FakeClient:
    def __init__(self) -> None:
        self.config = quickgo.QuickGoConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint in {"ontology/go/terms/GO:0006915", "ontology/go/terms/GO:0008150"}:
            return QUICKGO_TERM, {"content-type": "application/json"}
        if endpoint == "ontology/go/search":
            return QUICKGO_SEARCH, {"content-type": "application/json"}
        if endpoint == "annotation/search":
            return QUICKGO_ANNOTATIONS, {"content-type": "application/json"}
        if endpoint == "ontology/go/terms/GO:0006915/children":
            return QUICKGO_CHILDREN, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


QUICKGO_TERM = {
    "numberOfHits": 1,
    "results": [
        {
            "id": "GO:0006915",
            "isObsolete": False,
            "name": "apoptotic process",
            "definition": {
                "text": "A programmed cell death process.",
                "xrefs": [{"dbCode": "PMID", "dbId": "18846107"}],
            },
            "synonyms": [{"name": "apoptosis", "type": "narrow"}],
            "children": [{"id": "GO:0097194", "relation": "part_of"}],
            "ancestors": ["GO:0008150", "GO:0008219"],
            "aspect": "biological_process",
            "usage": "Unrestricted",
        }
    ],
    "pageInfo": None,
}


QUICKGO_SEARCH = {
    "numberOfHits": 2,
    "results": [
        {
            "id": "GO:0097194",
            "isObsolete": False,
            "name": "execution phase of apoptosis",
            "definition": {"text": "A stage of the apoptotic process."},
            "aspect": "biological_process",
        },
        {
            "id": "GO:0070227",
            "isObsolete": False,
            "name": "lymphocyte apoptotic process",
            "definition": {"text": "Any apoptotic process in a lymphocyte."},
            "aspect": "biological_process",
        },
    ],
    "pageInfo": {"resultsPerPage": 2, "current": 1, "total": 1},
}


QUICKGO_ANNOTATIONS = {
    "numberOfHits": 348,
    "results": [
        {
            "id": "UniProtKB:P04637!58679185",
            "geneProductId": "UniProtKB:P04637",
            "qualifier": "acts_upstream_of_negative_effect",
            "goId": "GO:1902749",
            "goEvidence": "IMP",
            "goAspect": "biological_process",
            "evidenceCode": "ECO:0000315",
            "reference": "PMID:10962037",
            "taxonId": 9606,
            "assignedBy": "UniProt",
            "symbol": "TP53",
            "date": "20210802",
        }
    ],
    "pageInfo": {"resultsPerPage": 1, "current": 1, "total": 348},
}


QUICKGO_CHILDREN = {
    "numberOfHits": 1,
    "results": [
        {
            "id": "GO:0006915",
            "name": "apoptotic process",
            "children": [
                {"id": "GO:0043276", "name": "anoikis", "relation": "is_a", "hasChildren": True},
                {"id": "GO:0097194", "name": "execution phase of apoptosis", "relation": "part_of", "hasChildren": True},
            ],
        }
    ],
    "pageInfo": None,
}


class QuickGoMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = quickgo.QuickGoMcpServer(self.client)

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

    def test_tools_list_exposes_quickgo_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "quickgo_parameter_domains",
                "quickgo_resolve_context",
                "quickgo_term_lookup",
                "quickgo_term_search",
                "quickgo_annotation_search",
                "quickgo_term_children",
                "quickgo_status",
            },
        )

    def test_term_lookup_returns_frontend_compatible_ontology_record(self) -> None:
        result = self.call_tool("quickgo_term_lookup", {"go_id": "GO:0006915"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "network", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["id"], "GO:0006915")
        self.assertEqual(record["data"]["aspect_label"], "biological process")

    def test_term_search_returns_bounded_ontology_records(self) -> None:
        result = self.call_tool("quickgo_term_search", {"query": "apoptosis", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table"},
            min_records=2,
        )
        self.assertEqual(result["total"], 2)

    def test_annotation_search_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool(
            "quickgo_annotation_search",
            {"gene_product_id": "UniProtKB:P04637", "taxon_id": 9606, "max_results": 1},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["annotations"][0]["symbol"], "TP53")
        self.assertEqual(record["data"]["annotations"][0]["reference_url"], "https://pubmed.ncbi.nlm.nih.gov/10962037/")

    def test_term_children_returns_child_ontology_records(self) -> None:
        result = self.call_tool("quickgo_term_children", {"go_id": "GO:0006915", "max_children": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table"},
            min_records=2,
        )
        self.assertEqual(result["records"][0]["data"]["parent_id"], "GO:0006915")
        self.assertEqual(result["records"][0]["data"]["relation"], "is_a")

    def test_resolve_context_returns_term_candidates_and_calls(self) -> None:
        result = self.call_tool(
            "quickgo_resolve_context",
            {"query": "apoptosis", "max_results": 2},
        )
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["terms"][0]["value"], "GO:0097194")
        self.assertIn("QuickGO/term/GO:0097194", result["terms"][0]["url"])
        self.assertEqual(result["recommended_calls"][0]["tool_name"], "quickgo_term_lookup")
        self.assertEqual(result["recommended_calls"][0]["arguments"]["go_id"], "GO:0097194")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("quickgo_status", {})
        self.assertEqual(result["server"], "quickgo")
        self.assertIn("quickgo_term_lookup", result["available_tools"])
        self.assertIn("ontology_term", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("quickgo_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_go_id"], "GO:0006915")
        self.assertEqual(result["network_check"]["example_name"], "apoptotic process")


if __name__ == "__main__":
    unittest.main()
