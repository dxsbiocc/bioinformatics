from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "biorxiv" / "server.py"
SPEC = importlib.util.spec_from_file_location("biorxiv_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
biorxiv = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = biorxiv
SPEC.loader.exec_module(biorxiv)


class FakeClient:
    def __init__(self) -> None:
        self.config = biorxiv.BioRxivConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "details/biorxiv/10.1101/2020.09.09.20191205/na/json":
            return {"collection": [PREPRINT]}, {"content-type": "application/json"}
        if endpoint == "details/medrxiv/2026-09-01/2026-09-07/0/json":
            return {"collection": [MEDRXIV_PREPRINT, {**MEDRXIV_PREPRINT, "doi": "10.1101/2026.09.02.22222222", "title": "Second medRxiv preprint"}]}, {"content-type": "application/json"}
        if endpoint == "pubs/biorxiv/10.1101/2020.09.09.20191205/na/json":
            return {"collection": [PUBLICATION_LINK]}, {"content-type": "application/json"}
        if endpoint == "pubs/biorxiv/7d/0":
            return {"collection": [PUBLICATION_LINK]}, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


PREPRINT = {
    "doi": "10.1101/2020.09.09.20191205",
    "title": "A SARS-CoV-2 protein interaction map",
    "authors": "Gordon DE; Jang GM; Bouhaddou M",
    "author_corresponding": "David E. Gordon",
    "author_corresponding_institution": "UCSF",
    "date": "2020-09-11",
    "version": "1",
    "type": "new results",
    "license": "cc_by_nc_nd",
    "category": "bioinformatics",
    "jatsxml": "https://www.biorxiv.org/content/10.1101/2020.09.09.20191205v1.source.xml",
    "abstract": "We describe a protein interaction map for SARS-CoV-2.",
    "funding": "NIH",
    "published": "10.1038/s41586-020-2286-9",
    "server": "biorxiv",
}


MEDRXIV_PREPRINT = {
    **PREPRINT,
    "server": "medrxiv",
    "doi": "10.1101/2026.09.01.11111111",
    "title": "Clinical preprint example",
    "category": "epidemiology",
    "published": "",
}


PUBLICATION_LINK = {
    "biorxiv_doi": "10.1101/2020.09.09.20191205",
    "published_doi": "10.1038/s41586-020-2286-9",
    "published_journal": "Nature",
    "published_date": "2020-04-30",
    "preprint_platform": "biorxiv",
    "preprint_title": "A SARS-CoV-2 protein interaction map",
    "preprint_authors": "Gordon DE; Jang GM; Bouhaddou M",
    "preprint_category": "bioinformatics",
    "preprint_date": "2020-09-11",
    "preprint_abstract": "We describe a protein interaction map for SARS-CoV-2.",
}


class BioRxivMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = biorxiv.BioRxivMcpServer(self.client)

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

    def test_tools_list_exposes_biorxiv_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "biorxiv_parameter_domains",
                "biorxiv_preprint_lookup",
                "biorxiv_preprint_interval",
                "biorxiv_publication_lookup",
                "biorxiv_publication_interval",
                "biorxiv_status",
            },
        )

    def test_preprint_lookup_returns_frontend_compatible_citation_record(self) -> None:
        result = self.call_tool("biorxiv_preprint_lookup", {"server": "biorxiv", "doi": "10.1101/2020.09.09.20191205"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"citation"},
            required_preview_kinds={"citation_list", "table", "xref_groups", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["identifiers"]["published_doi"]["url"], "https://doi.org/10.1038/s41586-020-2286-9")
        self.assertEqual(record["display"]["primary_url"], "https://www.biorxiv.org/content/10.1101/2020.09.09.20191205v1")

    def test_preprint_interval_returns_bounded_medrxiv_records(self) -> None:
        result = self.call_tool(
            "biorxiv_preprint_interval",
            {"server": "medrxiv", "start_date": "2026-09-01", "end_date": "2026-09-07", "max_results": 2},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"citation"},
            required_preview_kinds={"citation_list", "table", "xref_groups", "text"},
            min_records=2,
        )
        self.assertEqual(self.client.calls[-1][0], "details/medrxiv/2026-09-01/2026-09-07/0/json")
        self.assertEqual(result["records"][0]["url"], "https://www.medrxiv.org/content/10.1101/2026.09.01.11111111v1")

    def test_publication_lookup_returns_frontend_compatible_citation_record(self) -> None:
        result = self.call_tool("biorxiv_publication_lookup", {"server": "biorxiv", "doi": "10.1101/2020.09.09.20191205"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"citation"},
            required_preview_kinds={"citation_list", "table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["published_journal"], "Nature")
        self.assertEqual(record["display"]["primary_url"], "https://doi.org/10.1038/s41586-020-2286-9")

    def test_publication_interval_uses_recent_day_endpoint(self) -> None:
        result = self.call_tool("biorxiv_publication_interval", {"server": "biorxiv", "recent_days": 7, "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"citation"},
            required_preview_kinds={"citation_list", "table", "xref_groups"},
        )
        self.assertEqual(self.client.calls[-1][0], "pubs/biorxiv/7d/0")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("biorxiv_status", {})
        self.assertEqual(result["server"], "biorxiv")
        self.assertIn("biorxiv_preprint_lookup", result["available_tools"])
        self.assertIn("citation", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("biorxiv_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_doi"], "10.1101/2020.09.09.20191205")
        self.assertIn("protein interaction", result["network_check"]["example_title"])

    def test_client_treats_empty_json_body_as_empty_collection(self) -> None:
        client = biorxiv.BioRxivClient(opener=lambda request, timeout: "")
        payload, _headers = client.request_json_with_headers("details/biorxiv/1d/0/json", {})
        self.assertEqual(payload, {"collection": []})


if __name__ == "__main__":
    unittest.main()
