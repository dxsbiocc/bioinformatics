from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "rnacentral" / "server.py"
SPEC = importlib.util.spec_from_file_location("rnacentral_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
rnacentral = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rnacentral
SPEC.loader.exec_module(rnacentral)


class FakeClient:
    def __init__(self) -> None:
        self.config = rnacentral.RnaCentralConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "rna/URS000075C808/9606/":
            return RNA_ENTRY, {"content-type": "application/json"}
        if endpoint == "rna/":
            return {"count": 2, "next": None, "previous": None, "results": [RNA_SEARCH_ENTRY, RNA_SEARCH_ENTRY_2]}, {"content-type": "application/json"}
        if endpoint == "rna/URS000075C808/xrefs/":
            return {"count": 1, "next": None, "previous": None, "results": [XREF]}, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


RNA_ENTRY = {
    "rnacentral_id": "URS000075C808_9606",
    "sequence": "CCUCCAGGCCCUGCCUUCU",
    "length": 20,
    "description": "Homo sapiens (human) HOX transcript antisense RNA (HOTAIR)",
    "short_description": "HOX transcript antisense RNA (HOTAIR)",
    "species": "Homo sapiens",
    "taxid": 9606,
    "genes": [{"id": "HGNC:33510", "symbol": "HOTAIR"}],
    "publications": 1,
    "rna_type": "lncRNA",
    "is_active": True,
    "distinct_databases": "IntAct",
}

RNA_SEARCH_ENTRY = {
    "url": "https://rnacentral.org/api/v1/rna/URS0003C7548F",
    "rnacentral_id": "URS0003C7548F",
    "sequence": "AUACUCCCUCCGUCCCAUAA",
    "length": 21,
    "xrefs": "https://rnacentral.org/api/v1/rna/URS0003C7548F/xrefs",
    "publications": "https://rnacentral.org/api/v1/rna/URS0003C7548F/publications",
    "is_active": True,
    "description": "pre_miRNA from 0 species",
    "rna_type": "pre_miRNA",
    "count_distinct_organisms": 1,
    "distinct_databases": ["RFAM"],
}

RNA_SEARCH_ENTRY_2 = {**RNA_SEARCH_ENTRY, "rnacentral_id": "URS0003C7548E", "description": "tmRNA from 0 species", "rna_type": "tmRNA"}

XREF = {
    "upi": "URS000075C808",
    "database": "IntAct",
    "is_active": True,
    "first_seen": "2023-06-14 00:00:00",
    "last_seen": "2026-04-13 00:00:00",
    "taxid": 9606,
    "accession": {
        "url": "https://rnacentral.org/api/v1/accession/INTACT:URS000075C808_9606/info",
        "id": "INTACT:URS000075C808_9606",
        "external_id": "INTACT:URS000075C808_9606",
        "feature_start": 1,
        "feature_end": 2365,
        "feature_name": "ncRNA",
        "description": "Homo sapiens (human) HOX transcript antisense RNA (HOTAIR)",
        "species": "Homo sapiens",
        "rna_type": "lncRNA",
        "gene": "HOTAIR",
        "ena_url": "https://www.ebi.ac.uk/ena/browser/view/Non-coding:INTACT:URS000075C808_9606",
        "citations": "https://rnacentral.org/api/v1/accession/INTACT:URS000075C808_9606/citations",
        "biotype": "ncRNA",
    },
}


class RnaCentralMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = rnacentral.RnaCentralMcpServer(self.client)

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

    def test_tools_list_exposes_rnacentral_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "rnacentral_parameter_domains",
                "rnacentral_entry_lookup",
                "rnacentral_search",
                "rnacentral_xrefs",
                "rnacentral_status",
            },
        )

    def test_entry_lookup_returns_frontend_compatible_sequence_record(self) -> None:
        result = self.call_tool("rnacentral_entry_lookup", {"rnacentral_id": "URS000075C808", "taxid": 9606})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"genomic_feature"},
            required_preview_kinds={"sequence", "table", "xref_groups", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["display"]["primary_url"], "https://rnacentral.org/rna/URS000075C808/9606")
        self.assertEqual(record["data"]["rna_type"], "lncRNA")
        self.assertEqual(record["data"]["sequence"], "CCUCCAGGCCCUGCCUUCU")
        self.assertEqual(record["data"]["api_url"], "https://rnacentral.org/api/v1/rna/URS000075C808/9606/")
        self.assertEqual(record["data"]["publications_api_url"], "https://rnacentral.org/api/v1/rna/URS000075C808/publications/")

    def test_search_returns_bounded_frontend_records(self) -> None:
        result = self.call_tool("rnacentral_search", {"query": "HOTAIR", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"genomic_feature"},
            required_preview_kinds={"sequence", "table", "xref_groups", "text"},
            min_records=2,
        )
        self.assertEqual(self.client.calls[-1][0], "rna/")
        self.assertEqual(self.client.calls[-1][1]["q"], "HOTAIR")
        self.assertEqual(result["pagination"]["count"], 2)

    def test_xrefs_returns_frontend_compatible_mapping_record(self) -> None:
        result = self.call_tool("rnacentral_xrefs", {"rnacentral_id": "URS000075C808", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"identifier_conversion"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["xrefs"][0]["database"], "IntAct")
        self.assertEqual(record["data"]["xrefs"][0]["gene"], "HOTAIR")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("rnacentral_status", {})
        self.assertEqual(result["server"], "rnacentral")
        self.assertIn("rnacentral_entry_lookup", result["available_tools"])
        self.assertIn("genomic_feature", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("rnacentral_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_id"], "URS000075C808_9606")
        self.assertIn("HOTAIR", result["network_check"]["example_description"])

    def test_client_parses_json_payload(self) -> None:
        client = rnacentral.RnaCentralClient(opener=lambda request, timeout: (json.dumps(RNA_ENTRY), {"content-type": "application/json"}))
        payload, headers = client.request_json_with_headers("rna/URS000075C808/9606/", {})
        self.assertEqual(payload["rnacentral_id"], "URS000075C808_9606")
        self.assertEqual(headers["content-type"], "application/json")


if __name__ == "__main__":
    unittest.main()
