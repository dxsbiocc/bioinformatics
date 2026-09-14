from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "mgnify" / "server.py"
SPEC = importlib.util.spec_from_file_location("mgnify_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
mgnify = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = mgnify
SPEC.loader.exec_module(mgnify)


STUDY_ID = "MGYS00006862"
SAMPLE_ID = "SRS10016989"
BIOME_ID = "root:Host-associated:Human:Digestive system:Large intestine"


class FakeClient:
    def __init__(self) -> None:
        self.config = mgnify.MgnifyConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == f"studies/{STUDY_ID}":
            return {"data": STUDY}, {"content-type": "application/vnd.api+json"}
        if endpoint == "studies":
            return STUDY_SEARCH, {"content-type": "application/vnd.api+json"}
        if endpoint == f"samples/{SAMPLE_ID}":
            return {"data": SAMPLE}, {"content-type": "application/vnd.api+json"}
        if endpoint == "biomes/root:Host-associated:Human:Digestive%20system:Large%20intestine":
            return {"data": BIOME}, {"content-type": "application/vnd.api+json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")

    def build_url(self, endpoint, params=None):
        url = f"{self.config.api_base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        if "search" in params:
            return f"{url}?search={params['search']}&page_size={params['page_size']}"
        return url


STUDY = {
    "type": "studies",
    "id": STUDY_ID,
    "attributes": {
        "samples-count": 84,
        "bioproject": "PRJEB92327",
        "accession": STUDY_ID,
        "is-private": False,
        "last-update": "2026-04-24T07:54:59",
        "secondary-accession": "ERP175206",
        "centre-name": "EMG",
        "study-abstract": "The Third Party Annotation assembly was derived from PRJNA715245.",
        "study-name": "Metagenome assembly of PRJNA715245 data set",
        "data-origination": "SUBMITTED",
    },
    "relationships": {
        "downloads": {"links": {"related": f"https://www.ebi.ac.uk/metagenomics/api/v1/studies/{STUDY_ID}/downloads"}},
        "analyses": {"links": {"related": f"https://www.ebi.ac.uk/metagenomics/api/v1/studies/{STUDY_ID}/analyses"}},
        "biomes": {
            "links": {"related": f"https://www.ebi.ac.uk/metagenomics/api/v1/studies/{STUDY_ID}/biomes"},
            "data": [{"type": "biomes", "id": BIOME_ID}],
        },
        "samples": {"links": {"related": f"https://www.ebi.ac.uk/metagenomics/api/v1/studies/{STUDY_ID}/samples"}},
    },
    "links": {"self": f"https://www.ebi.ac.uk/metagenomics/api/v1/studies/{STUDY_ID}"},
}


STUDY_SEARCH = {
    "data": [
        STUDY,
        {
            **STUDY,
            "id": "MGYS00006825",
            "attributes": {
                **STUDY["attributes"],
                "accession": "MGYS00006825",
                "samples-count": 197,
                "study-name": "EMG produced TPA metagenomics assembly",
            },
            "links": {"self": "https://www.ebi.ac.uk/metagenomics/api/v1/studies/MGYS00006825"},
        },
    ],
    "meta": {"pagination": {"count": 225, "page": 1, "pages": 113}},
}


SAMPLE = {
    "type": "samples",
    "id": SAMPLE_ID,
    "attributes": {
        "biosample": "SAMN21216536",
        "sample-metadata": [
            {"key": "collection date", "value": "not collected", "unit": None},
            {"key": "host scientific name", "value": "Homo sapiens", "unit": None},
        ],
        "accession": SAMPLE_ID,
        "collection-date": None,
        "geo-loc-name": None,
        "sample-desc": "Amox_7d_control",
        "sample-name": "SampleID-CA24bGut.fasta",
        "sample-alias": "SampleID-CA24bGut.fasta",
        "host-tax-id": 9606,
        "species": "Homo sapiens",
        "last-update": "2026-04-24T07:54:59",
    },
    "relationships": {
        "runs": {"links": {"related": f"https://www.ebi.ac.uk/metagenomics/api/v1/samples/{SAMPLE_ID}/runs"}},
        "biome": {"data": {"type": "biomes", "id": BIOME_ID}},
        "studies": {"data": [{"type": "studies", "id": STUDY_ID}]},
    },
    "links": {"self": f"https://www.ebi.ac.uk/metagenomics/api/v1/samples/{SAMPLE_ID}"},
}


BIOME = {
    "type": "biomes",
    "id": BIOME_ID,
    "attributes": {"samples-count": 3822, "biome-name": "Large intestine", "lineage": BIOME_ID},
    "relationships": {
        "studies": {"links": {"related": "https://www.ebi.ac.uk/metagenomics/api/v1/biomes/example/studies"}},
        "samples": {"links": {"related": "https://www.ebi.ac.uk/metagenomics/api/v1/biomes/example/samples"}},
    },
    "links": {"self": "https://www.ebi.ac.uk/metagenomics/api/v1/biomes/root:Host-associated:Human:Digestive%20system:Large%20intestine"},
}


class MgnifyMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = mgnify.MgnifyMcpServer(self.client)

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

    def test_tools_list_exposes_mgnify_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "mgnify_parameter_domains",
                "mgnify_study_lookup",
                "mgnify_study_search",
                "mgnify_sample_lookup",
                "mgnify_biome_lookup",
                "mgnify_status",
            },
        )

    def test_study_lookup_returns_frontend_compatible_project_record(self) -> None:
        result = self.call_tool("mgnify_study_lookup", {"accession": STUDY_ID})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], STUDY_ID)
        self.assertEqual(record["data"]["bioproject"], "PRJEB92327")
        self.assertIn(BIOME_ID, record["data"]["biomes"])

    def test_study_search_returns_bounded_project_records(self) -> None:
        result = self.call_tool("mgnify_study_search", {"query": "human gut", "max_results": 2})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table"}, min_records=2)
        self.assertEqual(result["total"], 225)
        self.assertEqual(self.client.calls[-1][1]["search"], "human gut")

    def test_sample_lookup_returns_frontend_compatible_sample_record(self) -> None:
        result = self.call_tool("mgnify_sample_lookup", {"accession": SAMPLE_ID})
        assert_result_frontend_contract(self, result, expected_components={"sample"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(record["data"]["biosample"], "SAMN21216536")
        self.assertEqual(record["data"]["studies"], [STUDY_ID])
        self.assertEqual(record["data"]["sample_metadata"][1]["value"], "Homo sapiens")

    def test_biome_lookup_returns_frontend_compatible_taxonomy_record(self) -> None:
        result = self.call_tool("mgnify_biome_lookup", {"biome_id": BIOME_ID})
        assert_result_frontend_contract(self, result, expected_components={"taxonomy"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(record["data"]["name"], "Large intestine")
        self.assertEqual(record["data"]["samples_count"], 3822)
        self.assertEqual(self.client.calls[-1][0], "biomes/root:Host-associated:Human:Digestive%20system:Large%20intestine")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("mgnify_status", {})
        self.assertEqual(result["server"], "mgnify")
        self.assertIn("mgnify_study_lookup", result["available_tools"])
        self.assertIn("project", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("mgnify_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_accession"], STUDY_ID)


if __name__ == "__main__":
    unittest.main()
