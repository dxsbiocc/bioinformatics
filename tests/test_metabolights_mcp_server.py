from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "metabolights" / "server.py"
SPEC = importlib.util.spec_from_file_location("metabolights_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
metabolights = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = metabolights
SPEC.loader.exec_module(metabolights)


class FakeClient:
    def __init__(self) -> None:
        self.config = metabolights.MetaboLightsConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_ws_json_with_headers(self, endpoint, params):
        self.calls.append(("ws", endpoint, params))
        if endpoint == "studies/MTBLS1":
            return MTBLS1_STUDY, {"content-type": "application/json"}
        if endpoint == "studies/MTBLS1/files":
            return MTBLS1_FILES, {"content-type": "application/json"}
        raise AssertionError(f"unexpected ws endpoint {endpoint}")

    def request_search_json_with_headers(self, endpoint, params):
        self.calls.append(("search", endpoint, params))
        if endpoint == "metabolights":
            return MTBLS_SEARCH, {"content-type": "application/json"}
        raise AssertionError(f"unexpected search endpoint {endpoint}")

    def build_ws_url(self, endpoint, params=None):
        url = f"{self.config.ws_base_url.rstrip('/')}/{endpoint}"
        if params:
            return f"{url}?include_raw_data=false"
        return url

    def build_search_url(self, endpoint, params=None):
        return f"{self.config.search_base_url.rstrip('/')}/{endpoint}?query=diabetes&format=json"


MTBLS1_FILES = {
    "study": [
        {
            "createdAt": "July 17 2026 16:20:03",
            "directory": False,
            "file": "a_MTBLS1_NMR_metabolite_profiling_NMR_spectroscopy.txt",
            "status": "active",
            "timestamp": "20260717162003",
            "type": "metadata_assay",
        },
        {
            "createdAt": "May 22 2026 06:58:18",
            "directory": False,
            "file": "m_MTBLS1_metabolite_profiling_NMR_spectroscopy_v2_maf.tsv",
            "status": "active",
            "timestamp": "20260522065818",
            "type": "metadata_maf",
        },
    ]
}


MTBLS1_STUDY = {
    "mtblsStudy": {
        "studyStatus": "Public",
        "studyHttpUrl": "http://ftp.ebi.ac.uk/pub/databases/metabolights/studies/public/MTBLS1",
        "studyGlobusUrl": "https://app.globus.org/file-manager?origin_id=example",
        "studyCategory": "nmr",
        "datasetLicense": "EMBL-EBI Terms of Use",
        "datasetLicenseUrl": "https://www.ebi.ac.uk/about/terms-of-use/",
        "modifiedTime": "2026-07-17T16:20:03.480273",
        "revisionDatetime": "2025-09-02T14:34:14.536288",
        "studyPermission": {"studyId": "MTBLS1", "studyStatus": "PUBLIC"},
    },
    "isaInvestigation": {
        "identifier": "MTBLS1",
        "title": "A metabolomic study of urinary changes in type 2 diabetes",
        "submissionDate": "2012-02-14",
        "publicReleaseDate": "2012-02-14",
        "studies": [
            {
                "identifier": "MTBLS1",
                "title": "A metabolomic study of urinary changes in type 2 diabetes in human compared to the control group",
                "description": "NMR-based metabolomic analysis of urinary metabolic changes.",
                "submissionDate": "2012-02-14",
                "publicReleaseDate": "2012-02-14",
                "comments": [{"name": "Study Category", "value": "nmr"}],
                "people": [
                    {
                        "firstName": "Reza",
                        "lastName": "Salek",
                        "email": "rms72@example.org",
                        "affiliation": "University of Cambridge",
                        "roles": [{"annotationValue": "principal investigator role"}],
                    }
                ],
                "studyDesignDescriptors": [
                    {"annotationValue": "diabetes mellitus"},
                    {"annotationValue": "nuclear magnetic resonance spectroscopy"},
                ],
                "publications": [
                    {
                        "title": "A metabolomic comparison of urinary changes in type 2 diabetes in mouse, rat, and human.",
                        "authorList": "Salek RM et al.",
                        "pubMedID": "17190852",
                        "doi": "10.1152/physiolgenomics.00194.2006",
                        "status": {"annotationValue": "published"},
                    }
                ],
                "factors": [{"factorName": "Gender", "factorType": {"annotationValue": "Gender"}}],
                "protocols": [
                    {
                        "name": "NMR spectroscopy",
                        "protocolType": {"annotationValue": "NMR spectroscopy"},
                        "description": "Spectra were acquired on a Bruker DRX700 NMR spectrometer.",
                    }
                ],
                "assays": [
                    {
                        "measurementType": {"annotationValue": "untargeted analysis"},
                        "technologyType": {"annotationValue": "NMR spectroscopy assay"},
                        "technologyPlatform": "Nuclear Magnetic Resonance (NMR) - Bruker",
                        "filename": "a_MTBLS1_NMR_metabolite_profiling_NMR_spectroscopy.txt",
                    }
                ],
            }
        ],
    },
}


MTBLS_SEARCH = {
    "hitCount": 147,
    "entries": [
        {
            "id": "MTBLS14089",
            "source": "metabolights",
            "fields": {
                "name": ["The accumulation of methylglyoxal and acrolein leads to arginine depletion"],
                "description": ["<p>Reactive carbonyl species in diabetes and renal abnormalities.</p>"],
                "organism": ["Danio rerio"],
                "study_design": ["targeted metabolite profiling", "Diabetes Mellitus"],
            },
        }
    ],
}


class MetaboLightsMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = metabolights.MetaboLightsMcpServer(self.client)

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

    def test_tools_list_exposes_metabolights_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "metabolights_parameter_domains",
                "metabolights_study_lookup",
                "metabolights_search",
                "metabolights_file_manifest",
                "metabolights_status",
            },
        )

    def test_study_lookup_returns_frontend_compatible_project_record(self) -> None:
        result = self.call_tool("metabolights_study_lookup", {"accession": "mtbls1", "max_files": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "citation_list", "download_manifest", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], "MTBLS1")
        self.assertEqual(record["data"]["category"], "nmr")
        self.assertEqual(record["data"]["publications"][0]["pmid"], "17190852")
        self.assertTrue(record["data"]["files"][0]["download_url"].startswith("https://ftp.ebi.ac.uk/"))
        self.assertEqual(result["file_source"]["url"], "https://www.ebi.ac.uk/metabolights/ws/studies/MTBLS1/files?include_raw_data=false")

    def test_search_returns_project_records_from_ebi_search(self) -> None:
        result = self.call_tool("metabolights_search", {"query": "diabetes", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["stable_id"], "MTBLS14089")
        self.assertEqual(record["data"]["organisms"], ["Danio rerio"])
        self.assertNotIn("<p>", record["description"])
        self.assertEqual(result["total"], 147)

    def test_file_manifest_returns_download_plan_record(self) -> None:
        result = self.call_tool("metabolights_file_manifest", {"accession": "MTBLS1", "max_files": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"download_plan"},
            required_preview_kinds={"download_manifest", "table"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], "MTBLS1")
        self.assertEqual(result["returned"], 2)
        self.assertIn("Open first file", {action["label"] for action in record["display"]["actions"]})

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("metabolights_status", {})
        self.assertEqual(result["server"], "metabolights")
        self.assertIn("metabolights_study_lookup", result["available_tools"])
        self.assertIn("project", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("metabolights_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_accession"], "MTBLS1")


if __name__ == "__main__":
    unittest.main()
