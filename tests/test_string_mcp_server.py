from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "stringdb" / "server.py"
SPEC = importlib.util.spec_from_file_location("string_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
stringdb = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = stringdb
SPEC.loader.exec_module(stringdb)


class FakeClient:
    def __init__(self) -> None:
        self.config = stringdb.StringDbConfig(contact=None)
        self.requests_per_second = 1
        self.calls = []

    def request_json_array_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "json/get_string_ids":
            return STRING_MAPPINGS, {
                "content-type": "application/json",
            }
        if endpoint == "json/interaction_partners":
            return STRING_INTERACTIONS, {
                "content-type": "application/json",
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")


STRING_MAPPINGS = [
    {
        "queryIndex": 0,
        "queryItem": "TP53",
        "stringId": "9606.ENSP00000269305",
        "ncbiTaxonId": 9606,
        "taxonName": "Homo sapiens",
        "preferredName": "TP53",
        "annotation": "Cellular tumor antigen p53.",
    }
]

STRING_INTERACTIONS = [
    {
        "stringId_A": "9606.ENSP00000269305",
        "stringId_B": "9606.ENSP00000258149",
        "preferredName_A": "TP53",
        "preferredName_B": "MDM2",
        "ncbiTaxonId": 9606,
        "score": 0.999,
        "nscore": 0,
        "fscore": 0,
        "pscore": 0,
        "ascore": 0.049,
        "escore": 0.999,
        "dscore": 0.9,
        "tscore": 0.998,
    },
    {
        "stringId_A": "9606.ENSP00000269305",
        "stringId_B": "9606.ENSP00000340989",
        "preferredName_A": "TP53",
        "preferredName_B": "SFN",
        "ncbiTaxonId": 9606,
        "score": 0.997,
        "escore": 0.981,
        "dscore": 0.75,
        "tscore": 0.859,
    },
]


class StringMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = stringdb.StringDbMcpServer(self.client)

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

    def test_tools_list_exposes_string_tools(self) -> None:
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
        self.assertEqual(names, {"string_parameter_domains", "string_resolve_context", "string_map", "string_interactions", "string_status"})

    def test_string_map_returns_frontend_compatible_mapping_records(self) -> None:
        result = self.call_tool(
            "string_map",
            {
                "identifiers": ["TP53"],
                "species": 9606,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"identifier_conversion"},
            required_preview_kinds={"xref_groups"},
        )
        self.assertEqual(result["schema_version"], "bioinformatics.string.result.v1")
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["source"]["endpoint"], "json/get_string_ids")
        record = result["records"][0]
        self.assertEqual(record["record_type"], "string_id_mapping")
        self.assertEqual(record["stable_id"], "STRING:9606.ENSP00000269305")
        self.assertEqual(record["display"]["component"], "identifier_conversion")
        self.assertEqual(record["identifiers"]["taxonomy"]["label"], "TaxID:9606")
        preview_kinds = {preview["kind"] for preview in record["display"]["previews"]}
        self.assertIn("xref_groups", preview_kinds)

    def test_resolve_context_maps_identifiers_and_recommends_interactions(self) -> None:
        result = self.call_tool("string_resolve_context", {"identifiers": "TP53", "species": 9606})
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["mappings"][0]["value"], "9606.ENSP00000269305")
        self.assertEqual(result["mappings"][0]["metadata"]["preferred_name"], "TP53")
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("string_map", tool_names)
        self.assertIn("string_interactions", tool_names)

    def test_string_interactions_returns_network_record(self) -> None:
        result = self.call_tool(
            "string_interactions",
            {
                "identifiers": "TP53",
                "species": 9606,
                "limit": 2,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein_network"},
            required_preview_kinds={"network", "table"},
        )
        self.assertEqual(result["schema_version"], "bioinformatics.string.result.v1")
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["mapping_count"], 1)
        self.assertEqual(result["edge_count"], 2)
        self.assertEqual(result["node_count"], 3)
        record = result["records"][0]
        self.assertEqual(record["record_type"], "string_interaction_network")
        self.assertEqual(record["display"]["component"], "protein_network")
        preview_kinds = {preview["kind"] for preview in record["display"]["previews"]}
        self.assertIn("network", preview_kinds)
        self.assertIn("table", preview_kinds)
        network_preview = next(
            preview
            for preview in record["display"]["previews"]
            if preview["kind"] == "network"
        )
        self.assertEqual(len(network_preview["data"]["nodes"]), 3)
        self.assertEqual(network_preview["data"]["edges"][0]["target_label"], "MDM2")
        self.assertEqual(
            network_preview["data"]["edges"][0]["evidence_scores"]["escore"],
            0.999,
        )
        self.assertTrue(record["display"]["primary_url"].startswith("https://string-db.org/network/"))

    def test_status_reports_preview_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("string_status", {})
        self.assertEqual(result["server"], "string")
        self.assertIn("string_interactions", result["available_tools"])
        self.assertIn("protein_network", result["frontend_components"])
        self.assertIn("network", result["preview_kinds"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
