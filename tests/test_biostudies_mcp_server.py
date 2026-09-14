from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "biostudies" / "server.py"
SPEC = importlib.util.spec_from_file_location("biostudies_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
biostudies = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = biostudies
SPEC.loader.exec_module(biostudies)


class FakeClient:
    def __init__(self) -> None:
        self.config = biostudies.BioStudiesConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "studies/E-MTAB-6701":
            return BIOSTUDIES_STUDY, {"content-type": "application/json"}
        if endpoint == "studies/E-MTAB-6701/info":
            return BIOSTUDIES_INFO, {"content-type": "application/json"}
        if endpoint == "studies/E-MTAB-6701/files":
            return BIOSTUDIES_FILES, {"content-type": "application/json"}
        if endpoint == "search":
            return BIOSTUDIES_SEARCH, {"content-type": "application/json"}
        if endpoint == "ArrayExpress/search":
            return ARRAYEXPRESS_SEARCH, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


BIOSTUDIES_INFO = {
    "files": 4,
    "httpLink": "https://ftp.ebi.ac.uk/biostudies/fire/E-MTAB-/701/E-MTAB-6701",
    "ftpLink": "ftp://ftp.ebi.ac.uk/biostudies/fire/E-MTAB-/701/E-MTAB-6701",
    "globusLink": "https://app.globus.org/file-manager?origin_id=example",
    "isPublic": True,
    "sections": ["processed-data", "mt-E-MTAB-6701"],
    "sectionFileCounts": {"processed-data": 2, "mt-E-MTAB-6701": 2},
}


BIOSTUDIES_FILES = {
    "items": [
        {
            "path": "meta_10x.txt",
            "Name": "meta_10x.txt",
            "Description": "Processed Data",
            "Size": 3011006,
            "Section": "processed-data",
            "Type": "file",
            "Format": "text/plain",
        },
        {
            "path": "E-MTAB-6701.sdrf.txt",
            "Name": "E-MTAB-6701.sdrf.txt",
            "Description": "Sample and Data Relationship Format",
            "Size": 36760,
            "Section": "mt-E-MTAB-6701",
            "Type": "SDRF File",
            "Format": "tab-delimited text",
        },
    ],
    "pagination": {"offset": 0, "limit": 25, "total": 2, "filtered": 2},
}


BIOSTUDIES_STUDY = {
    "accno": "E-MTAB-6701",
    "attributes": [
        {"name": "Title", "value": "Reconstructing the human first trimester fetal-maternal interface using single cell transcriptomics"},
        {"name": "ReleaseDate", "value": "2018-10-02"},
        {"name": "AttachTo", "value": "ArrayExpress"},
    ],
    "section": {
        "accno": "s-E-MTAB-6701",
        "type": "Study",
        "attributes": [
            {"name": "Title", "value": "Reconstructing the human first trimester fetal-maternal interface using single cell transcriptomics"},
            {"name": "Study type", "value": "RNA-seq of coding RNA from single cells"},
            {"name": "Organism", "value": "Homo sapiens"},
            {"name": "Description", "value": "10x single-cell RNA-seq from matched first trimester samples."},
        ],
        "links": [
            [
                {"url": "ERP110450", "attributes": [{"name": "Type", "value": "ENA"}]},
                {"url": "E-MTAB-6701", "attributes": [{"name": "Type", "value": "gxa-sc"}]},
            ]
        ],
        "subsections": [
            [
                {
                    "accno": "P-MTAB-73447",
                    "type": "Protocols",
                    "attributes": [
                        {"name": "Name", "value": "P-MTAB-73447"},
                        {"name": "Type", "value": "nucleic acid sequencing protocol"},
                        {"name": "Description", "value": "Sequenced on an Illumina HiSeq 4000."},
                        {"name": "Hardware", "value": "Illumina HiSeq 4000"},
                    ],
                }
            ],
            {"type": "Author", "attributes": [{"name": "Name", "value": "Roser Vento Tormo"}]},
            {
                "accno": "30429548",
                "type": "Publication",
                "attributes": [
                    {"name": "Title", "value": "Single-cell reconstruction of the early maternal-fetal interface in humans"},
                    {"name": "Authors", "value": "Roser Vento-Tormo et al."},
                    {"name": "DOI", "value": "10.1038/s41586-018-0698-6"},
                    {"name": "Status", "value": "published"},
                ],
            },
            {"type": "Samples", "attributes": [{"name": "Sample count", "value": "30"}]},
            {
                "type": "Assays and Data",
                "attributes": [{"name": "Assay count", "value": "30"}, {"name": "Technology", "value": "Sequencing assay"}],
                "subsections": [
                    {
                        "type": "Processed Data",
                        "files": [
                            [
                                {
                                    "path": "meta_10x.txt",
                                    "size": 3011006,
                                    "attributes": [{"name": "Description", "value": "Processed Data"}],
                                    "type": "file",
                                }
                            ]
                        ],
                    }
                ],
            },
        ],
    },
}


BIOSTUDIES_SEARCH = {
    "page": 1,
    "pageSize": 2,
    "totalHits": 2,
    "hits": [
        {
            "accession": "S-BSST123",
            "type": "study",
            "title": "Single cell proteomics study",
            "author": "Ada Example",
            "links": 1,
            "files": 2,
            "release_date": "2024-01-01",
            "isPublic": True,
            "content": "Compact BioStudies search hit.",
        }
    ],
}


ARRAYEXPRESS_SEARCH = {
    "page": 1,
    "pageSize": 2,
    "totalHits": 1,
    "hits": [
        {
            "accession": "E-MTAB-6701",
            "type": "study",
            "title": "Reconstructing the human first trimester fetal-maternal interface using single cell transcriptomics",
            "author": "Sarah Teichmann",
            "links": 2,
            "files": 4,
            "release_date": "2018-10-02",
            "isPublic": True,
            "content": "RNA-seq of coding RNA from single cells.",
        }
    ],
}


class BioStudiesMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = biostudies.BioStudiesMcpServer(self.client)

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

    def test_tools_list_exposes_biostudies_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "biostudies_parameter_domains",
                "biostudies_study_lookup",
                "biostudies_search",
                "arrayexpress_search",
                "biostudies_file_manifest",
                "biostudies_status",
            },
        )

    def test_study_lookup_returns_frontend_compatible_project_record(self) -> None:
        result = self.call_tool("biostudies_study_lookup", {"accession": "E-MTAB-6701"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "citation_list", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], "E-MTAB-6701")
        self.assertEqual(record["data"]["publications"][0]["pmid_url"], "https://pubmed.ncbi.nlm.nih.gov/30429548/")
        self.assertEqual(record["data"]["organisms"], ["Homo sapiens"])

    def test_study_lookup_can_include_file_manifest_preview(self) -> None:
        result = self.call_tool("biostudies_study_lookup", {"accession": "E-MTAB-6701", "include_files": True, "max_files": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "citation_list", "xref_groups", "download_manifest"},
        )
        file_row = result["records"][0]["data"]["files"][0]
        self.assertEqual(file_row["name"], "meta_10x.txt")
        self.assertEqual(
            file_row["download_url"],
            "https://ftp.ebi.ac.uk/biostudies/fire/E-MTAB-/701/E-MTAB-6701/meta_10x.txt",
        )

    def test_biostudies_search_returns_project_records(self) -> None:
        result = self.call_tool("biostudies_search", {"query": "single cell", "max_results": 1})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table"})
        self.assertEqual(result["records"][0]["data"]["accession"], "S-BSST123")

    def test_arrayexpress_search_returns_project_records(self) -> None:
        result = self.call_tool("arrayexpress_search", {"query": "single cell", "max_results": 1})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table"})
        self.assertEqual(result["records"][0]["data"]["repository"], "arrayexpress")

    def test_file_manifest_returns_download_plan_record(self) -> None:
        result = self.call_tool("biostudies_file_manifest", {"accession": "E-MTAB-6701", "max_files": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"download_plan"},
            required_preview_kinds={"download_manifest", "table"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["files"][1]["name"], "E-MTAB-6701.sdrf.txt")
        self.assertIn("https://ftp.ebi.ac.uk/biostudies/fire/E-MTAB-/701/E-MTAB-6701/", record["display"]["actions"][-1]["url"])

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("biostudies_status", {})
        self.assertEqual(result["server"], "biostudies")
        self.assertIn("arrayexpress_search", result["available_tools"])
        self.assertIn("project", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("biostudies_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_accession"], "E-MTAB-6701")
        self.assertEqual(result["network_check"]["files"], 4)


if __name__ == "__main__":
    unittest.main()
