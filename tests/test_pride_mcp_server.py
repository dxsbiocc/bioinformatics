from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "pride" / "server.py"
SPEC = importlib.util.spec_from_file_location("pride_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
pride = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pride
SPEC.loader.exec_module(pride)


class FakeClient:
    def __init__(self) -> None:
        self.config = pride.PrideConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "projects/PXD001357":
            return PRIDE_PROJECT, {"content-type": "application/json"}
        if endpoint == "projects":
            return PRIDE_SEARCH, {"content-type": "application/json"}
        if endpoint == "projects/PXD001357/files":
            return PRIDE_FILES, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


PRIDE_PROJECT = {
    "accession": "PXD001357",
    "title": "Direct evidence of milk consumption from ancient human dental calculus",
    "projectDescription": "This study investigated milk product consumption using dental calculus proteins.",
    "sampleProcessingProtocol": "Tryptic peptides were extracted from dental calculus.",
    "dataProcessingProtocol": "Raw spectra were searched with Mascot.",
    "projectTags": ["Technical", "Metaproteomics"],
    "keywords": ["Human", "Dental calculus", "LC-MS/MS"],
    "doi": "10.6019/PXD001357",
    "submissionType": "COMPLETE",
    "license": "EBI terms of use",
    "submissionDate": "2014-10-15",
    "publicationDate": "2015-02-25",
    "submitters": [{"name": "Jessica Hendy", "affiliation": "University of York", "country": "United Kingdom"}],
    "labPIs": [{"name": "Matthew Collins", "affiliation": "University of York"}],
    "instruments": [{"cvLabel": "MS", "accession": "MS:1001911", "name": "Q Exactive"}],
    "softwares": [{"cvLabel": "MS", "accession": "MS:1001207", "name": "Mascot"}],
    "experimentTypes": [{"cvLabel": "PRIDE", "accession": "PRIDE:0000429", "name": "Shotgun proteomics"}],
    "quantificationMethods": [],
    "countries": ["United Kingdom"],
    "organisms": [{"cvLabel": "NEWT", "accession": "NEWT:9606", "name": "Homo sapiens (human)"}],
    "organismParts": [{"cvLabel": "BTO", "accession": "BTO:0000338", "name": "Dental plaque"}],
    "diseases": [],
    "references": [{"referenceLine": "Warinner C et al.", "pubmedID": 25429530, "doi": "10.1038/srep07104"}],
    "identifiedPTMStrings": [{"cvLabel": "UNIMOD", "accession": "UNIMOD:35", "name": "Oxidation"}],
    "totalFileDownloads": 29298,
    "otherOmicsLinks": ["px:PXD001360"],
}


PRIDE_SEARCH = [
    PRIDE_PROJECT,
    {
        **PRIDE_PROJECT,
        "accession": "PXD000035",
        "title": "Surface Proteins of Listeria monocytogenes",
        "doi": "10.6019/PXD000035",
        "organisms": [{"cvLabel": "NEWT", "accession": "NEWT:1639", "name": "Listeria monocytogenes"}],
    },
]


PRIDE_FILES = [
    {
        "projectAccessions": ["PXD001357"],
        "accession": "file-accession-1",
        "fileCategory": {
            "cvLabel": "PRIDE",
            "accession": "PRIDE:0000404",
            "name": "Associated raw file URI",
            "value": "RAW",
        },
        "checksum": "abc123",
        "publicFileLocations": [
            {
                "cvLabel": "PRIDE",
                "accession": "PRIDE:0000469",
                "name": "FTP Protocol",
                "value": "ftp://ftp.pride.ebi.ac.uk/pride/data/archive/2015/02/PXD001357/example.raw",
            },
            {
                "cvLabel": "PRIDE",
                "accession": "PRIDE:0000468",
                "name": "Aspera Protocol",
                "value": "prd_ascp@fasp.ebi.ac.uk:pride/data/archive/2015/02/PXD001357/example.raw",
            },
        ],
    }
]


class PrideMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = pride.PrideMcpServer(self.client)

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

    def test_tools_list_exposes_pride_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "pride_project_lookup",
                "pride_project_search",
                "pride_project_files",
                "pride_status",
            },
        )

    def test_project_lookup_returns_frontend_compatible_project_record(self) -> None:
        result = self.call_tool("pride_project_lookup", {"accession": "PXD001357"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "citation_list", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], "PXD001357")
        self.assertEqual(record["data"]["references"][0]["pmid_url"], "https://pubmed.ncbi.nlm.nih.gov/25429530/")

    def test_project_lookup_can_include_file_manifest_preview(self) -> None:
        result = self.call_tool("pride_project_lookup", {"accession": "PXD001357", "include_files": True, "max_files": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "download_manifest", "citation_list", "xref_groups"},
        )
        self.assertEqual(result["records"][0]["data"]["files"][0]["file_name"], "example.raw")

    def test_project_search_returns_project_records(self) -> None:
        result = self.call_tool("pride_project_search", {"query": "Listeria", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "citation_list", "xref_groups"},
            min_records=2,
        )
        self.assertEqual(result["records"][1]["data"]["accession"], "PXD000035")

    def test_project_files_returns_download_plan_record(self) -> None:
        result = self.call_tool("pride_project_files", {"accession": "PXD001357", "max_files": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"download_plan"},
            required_preview_kinds={"download_manifest", "table"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["files"][0]["download_url"], "https://ftp.pride.ebi.ac.uk/pride/data/archive/2015/02/PXD001357/example.raw")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("pride_status", {})
        self.assertEqual(result["server"], "pride")
        self.assertIn("pride_project_lookup", result["available_tools"])
        self.assertIn("project", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("pride_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_accession"], "PXD001357")
        self.assertIn("dental calculus", result["network_check"]["example_title"])


if __name__ == "__main__":
    unittest.main()
