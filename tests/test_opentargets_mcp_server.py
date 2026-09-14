from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "opentargets" / "server.py"
SPEC = importlib.util.spec_from_file_location("opentargets_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
opentargets = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = opentargets
SPEC.loader.exec_module(opentargets)


class FakeClient:
    def __init__(self) -> None:
        self.config = opentargets.OpenTargetsConfig(contact=None)
        self.requests_per_second = 1
        self.calls = []

    def request_graphql_with_headers(self, query, variables):
        self.calls.append((query, variables))
        if "target(ensemblId" in query:
            return {"data": {"target": OPENTARGETS_TARGET}}, {"content-type": "application/json"}
        if "disease(efoId" in query:
            return {"data": {"disease": OPENTARGETS_DISEASE}}, {"content-type": "application/json"}
        if "search(queryString" in query:
            return {"data": {"search": OPENTARGETS_SEARCH}}, {"content-type": "application/json"}
        if "meta" in query:
            return {"data": {"meta": OPENTARGETS_META}}, {"content-type": "application/json"}
        raise AssertionError("unexpected query")


OPENTARGETS_TARGET = {
    "id": "ENSG00000141510",
    "approvedSymbol": "TP53",
    "approvedName": "tumor protein p53",
    "biotype": "protein_coding",
    "genomicLocation": {"chromosome": "17", "start": 7661779, "end": 7687546, "strand": -1},
    "associatedDiseases": {
        "count": 5638,
        "rows": [
            {
                "score": 0.8763216350824885,
                "disease": {"id": "MONDO_0018875", "name": "Li-Fraumeni syndrome"},
                "datasourceScores": [
                    {"id": "uniprot_variants", "score": 0.9919541334408821},
                    {"id": "eva", "score": 0.9692366283939332},
                    {"id": "genomics_england", "score": 0.9580964074361958},
                ],
                "datatypeScores": [
                    {"id": "genetic_literature", "score": 0.8539007869518103},
                    {"id": "genetic_association", "score": 0.9564326867319108},
                ],
            }
        ],
    },
}


OPENTARGETS_DISEASE = {
    "id": "MONDO_0004979",
    "name": "asthma",
    "description": "A bronchial disease characterized by chronic inflammation and narrowing of the airways.",
    "dbXRefs": ["DOID:2841", "HP:0002099", "MESH:D001249"],
    "associatedTargets": {
        "count": 7403,
        "rows": [
            {
                "score": 0.7445012088296152,
                "target": {
                    "id": "ENSG00000143631",
                    "approvedSymbol": "FLG",
                    "approvedName": "filaggrin",
                },
                "datasourceScores": [
                    {"id": "gene_burden", "score": 0.9749891144166852},
                    {"id": "gwas_credible_sets", "score": 0.9677755884992927},
                    {"id": "europepmc", "score": 0.3471725113721895},
                ],
                "datatypeScores": [
                    {"id": "literature", "score": 0.3471725113721895},
                    {"id": "genetic_association", "score": 0.9735464092332068},
                ],
            }
        ],
    },
}


OPENTARGETS_SEARCH = {
    "total": 5976,
    "hits": [
        {
            "id": "ENSG00000141510",
            "entity": "target",
            "score": 5563.35,
            "object": {
                "id": "ENSG00000141510",
                "approvedSymbol": "TP53",
                "approvedName": "tumor protein p53",
                "biotype": "protein_coding",
            },
        },
        {
            "id": "MONDO_0018875",
            "entity": "disease",
            "score": 477.58652,
            "object": {
                "id": "MONDO_0018875",
                "name": "Li-Fraumeni syndrome",
                "description": "An autosomal dominant cancer predisposition disorder.",
                "dbXRefs": ["OMIM:151623", "Orphanet:524"],
            },
        },
    ],
}


OPENTARGETS_META = {
    "name": "Open Targets GraphQL & REST API Beta",
    "product": "platform",
    "dataPrefix": "platform2606",
    "apiVersion": {"x": "26", "y": "6", "z": "3", "suffix": None},
    "dataVersion": {"year": "26", "month": "06", "iteration": None},
}


class OpenTargetsMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = opentargets.OpenTargetsMcpServer(self.client)

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

    def test_tools_list_exposes_opentargets_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "opentargets_parameter_domains",
                "opentargets_resolve_context",
                "opentargets_target_lookup",
                "opentargets_disease_lookup",
                "opentargets_search",
                "opentargets_status",
            },
        )

    def test_target_lookup_returns_frontend_compatible_gene_record(self) -> None:
        result = self.call_tool(
            "opentargets_target_lookup",
            {"ensembl_id": "ENSG00000141510", "max_results": 2},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["symbol"], "TP53")
        self.assertEqual(record["data"]["associated_diseases"][0]["disease_name"], "Li-Fraumeni syndrome")
        self.assertEqual(record["data"]["datasource_score_rows"][0]["label"], "UniProt curated variants")

    def test_disease_lookup_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool(
            "opentargets_disease_lookup",
            {"efo_id": "MONDO_0004979", "max_results": 2},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["name"], "asthma")
        self.assertEqual(record["data"]["associated_targets"][0]["symbol"], "FLG")
        self.assertIn("DOID:2841", record["data"]["db_xrefs"])

    def test_search_returns_frontend_compatible_identifier_record(self) -> None:
        result = self.call_tool("opentargets_search", {"query": "TP53", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"identifier_conversion"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["hits"][0]["label"], "TP53")
        self.assertEqual(record["data"]["hits"][1]["entity"], "disease")

    def test_resolve_context_returns_search_entities_and_calls(self) -> None:
        result = self.call_tool(
            "opentargets_resolve_context",
            {"query": "TP53", "max_results": 2},
        )
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["entities"][0]["value"], "ENSG00000141510")
        self.assertIn("/target/ENSG00000141510", result["entities"][0]["url"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("opentargets_target_lookup", tool_names)
        self.assertIn("opentargets_disease_lookup", tool_names)

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("opentargets_status", {})
        self.assertEqual(result["server"], "opentargets")
        self.assertIn("opentargets_target_lookup", result["available_tools"])
        self.assertIn("gene", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("opentargets_status", {"check_network": True})
        self.assertEqual(result["network_check"]["data_prefix"], "platform2606")
        self.assertEqual(result["network_check"]["api_version"], "26.6.3")
        self.assertEqual(result["network_check"]["data_version"], "26.06")


if __name__ == "__main__":
    unittest.main()
