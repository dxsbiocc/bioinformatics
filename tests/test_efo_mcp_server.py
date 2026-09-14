from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "efo" / "server.py"
SPEC = importlib.util.spec_from_file_location("efo_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
efo = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = efo
SPEC.loader.exec_module(efo)


class FakeClient:
    def __init__(self) -> None:
        self.config = efo.EfoConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint.startswith("ontologies/efo/terms/") and endpoint.endswith("/children"):
            return CHILDREN, {"content-type": "application/json"}
        if endpoint.startswith("ontologies/efo/terms/") and endpoint.endswith("/descendants"):
            return DESCENDANTS, {"content-type": "application/json"}
        if endpoint.startswith("ontologies/efo/terms/"):
            return EFO_TERM, {"content-type": "application/json"}
        if endpoint == "search":
            return SEARCH, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


EFO_TERM = {
    "iri": "http://www.ebi.ac.uk/efo/EFO_0000270",
    "description": ["A bronchial disease that is characterized by chronic inflammation."],
    "synonyms": ["Bronchial asthma", "Asthma"],
    "annotation": {
        "database_cross_reference": ["DOID:2841", "MESH:D001249"],
        "term replaced by": ["http://purl.obolibrary.org/obo/MONDO_0004979"],
    },
    "label": "obsolete_asthma",
    "ontology_name": "efo",
    "ontology_prefix": "EFO",
    "is_obsolete": True,
    "term_replaced_by": "http://purl.obolibrary.org/obo/MONDO_0004979",
    "is_defining_ontology": True,
    "has_children": False,
    "short_form": "EFO_0000270",
    "obo_id": "EFO:0000270",
    "type": "class",
    "obo_xref": [
        {"database": "DOID", "id": "2841", "url": "http://purl.obolibrary.org/obo/DOID_2841"},
        {"database": "MESH", "id": "D001249", "url": "http://id.nlm.nih.gov/mesh/D001249"},
    ],
    "_links": {"self": {"href": "https://www.ebi.ac.uk/ols4/api/ontologies/efo/terms/example"}},
}


SEARCH = {
    "response": {
        "docs": [
            {
                "iri": "http://purl.obolibrary.org/obo/MONDO_0004979",
                "ontology_name": "efo",
                "ontology_prefix": "EFO",
                "short_form": "MONDO_0004979",
                "description": ["A bronchial disease."],
                "narrow_synonyms": ["exercise induced asthma"],
                "label": "asthma",
                "obo_id": "MONDO:0004979",
                "type": "class",
            },
            {
                "iri": "http://purl.obolibrary.org/obo/HP_0002099",
                "ontology_name": "efo",
                "ontology_prefix": "EFO",
                "short_form": "HP_0002099",
                "description": ["Asthma phenotype."],
                "exact_synonyms": ["Bronchial asthma"],
                "label": "Asthma",
                "obo_id": "HP:0002099",
                "type": "class",
            },
        ],
        "numFound": 42,
        "start": 0,
    }
}


CHILDREN = {
    "_embedded": {
        "terms": [
            {
                "iri": "http://purl.obolibrary.org/obo/MONDO_0004979",
                "label": "asthma",
                "short_form": "MONDO_0004979",
                "obo_id": "MONDO:0004979",
                "description": ["A bronchial disease."],
                "type": "class",
            }
        ]
    },
    "page": {"size": 1, "totalElements": 1, "totalPages": 1, "number": 0},
}


DESCENDANTS = {
    "_embedded": {
        "terms": [
            {
                "iri": "http://purl.obolibrary.org/obo/MONDO_0004979",
                "label": "asthma",
                "short_form": "MONDO_0004979",
                "obo_id": "MONDO:0004979",
                "description": ["A bronchial disease."],
                "type": "class",
            },
            {
                "iri": "http://purl.obolibrary.org/obo/MONDO_0005401",
                "label": "allergic asthma",
                "short_form": "MONDO_0005401",
                "obo_id": "MONDO:0005401",
                "description": ["An asthma subtype."],
                "type": "class",
            },
        ]
    },
    "page": {"size": 2, "totalElements": 2, "totalPages": 1, "number": 0},
}


class EfoMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = efo.EfoMcpServer(self.client)

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

    def test_tools_list_exposes_efo_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {"efo_parameter_domains", "efo_term_lookup", "efo_term_search", "efo_term_children", "efo_term_descendants", "efo_status"},
        )

    def test_term_lookup_returns_frontend_compatible_ontology_record(self) -> None:
        result = self.call_tool("efo_term_lookup", {"term_id": "EFO:0000270"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "xref_groups", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["id"], "EFO:0000270")
        self.assertTrue(record["data"]["is_obsolete"])
        self.assertEqual(record["data"]["replaced_by"], "http://purl.obolibrary.org/obo/MONDO_0004979")

    def test_term_search_returns_bounded_ontology_records(self) -> None:
        result = self.call_tool("efo_term_search", {"query": "asthma", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "text"},
            min_records=2,
        )
        self.assertEqual(result["total"], 42)
        self.assertEqual(self.client.calls[-1][1]["ontology"], "efo")
        record = result["records"][0]
        self.assertIn("http%253A%252F%252Fpurl.obolibrary.org%252Fobo%252FMONDO_0004979", record["data"]["api_url"])

    def test_children_returns_relation_records(self) -> None:
        result = self.call_tool("efo_term_children", {"term_id": "EFO:0000270", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "network", "text"},
        )
        self.assertEqual(result["records"][0]["data"]["parent_id"], "EFO:0000270")

    def test_descendants_returns_relation_records(self) -> None:
        result = self.call_tool("efo_term_descendants", {"term_id": "MONDO:0004979", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "network", "text"},
            min_records=2,
        )
        self.assertEqual(result["total"], 2)

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("efo_status", {})
        self.assertEqual(result["server"], "efo")
        self.assertIn("efo_term_lookup", result["available_tools"])
        self.assertIn("ontology_term", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("efo_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_id"], "EFO:0000270")
        self.assertEqual(result["network_check"]["example_label"], "obsolete_asthma")

    def test_client_parses_json_payload(self) -> None:
        client = efo.EfoClient(opener=lambda request, timeout: (json.dumps(EFO_TERM), {"content-type": "application/json"}))
        payload, headers = client.request_json_with_headers("ontologies/efo/terms/example", {})
        self.assertEqual(payload["obo_id"], "EFO:0000270")
        self.assertEqual(headers["content-type"], "application/json")


if __name__ == "__main__":
    unittest.main()
