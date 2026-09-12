from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "encode" / "server.py"
SPEC = importlib.util.spec_from_file_location("encode_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
encode = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = encode
SPEC.loader.exec_module(encode)


EXPERIMENT_ID = "ENCSR844TIU"
FILE_ID = "ENCFF789PHQ"
BIOSAMPLE_ID = "ENCBS000AAA"


class FakeClient:
    def __init__(self) -> None:
        self.config = encode.EncodeConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == f"experiments/{EXPERIMENT_ID}/":
            return EXPERIMENT, {"content-type": "application/json"}
        if endpoint == "search/":
            if params.get("type") == "Biosample":
                return BIOSAMPLE_SEARCH, {"content-type": "application/json"}
            return SEARCH, {"content-type": "application/json"}
        if endpoint == f"files/{FILE_ID}/":
            return FILE, {"content-type": "application/json"}
        if endpoint == f"biosamples/{BIOSAMPLE_ID}/":
            return BIOSAMPLE, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")

    def build_url(self, endpoint, params=None):
        url = f"{self.config.base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        pieces = [f"{key}={value}" for key, value in params.items()]
        return f"{url}?{'&'.join(pieces)}"


FILE = {
    "accession": FILE_ID,
    "file_format": "fastq",
    "file_type": "fastq",
    "output_type": "reads",
    "output_category": "raw data",
    "status": "released",
    "href": f"/files/{FILE_ID}/@@download/{FILE_ID}.fastq.gz",
    "dataset": f"/experiments/{EXPERIMENT_ID}/",
    "file_size": 740537844,
    "md5sum": "ffc5e74e3386b021f5290c6422f1ebf1",
    "cloud_metadata": {
        "url": f"https://encode-public.s3.amazonaws.com/example/{FILE_ID}.fastq.gz",
        "file_size": 740537844,
    },
    "s3_uri": f"s3://encode-public/example/{FILE_ID}.fastq.gz",
    "biological_replicates": [1],
    "technical_replicates": ["1_1"],
}


EXPERIMENT = {
    "accession": EXPERIMENT_ID,
    "assay_title": "ATAC-seq",
    "assay_term_name": "ATAC-seq",
    "assay_term_id": "OBI:0002039",
    "assay_slims": ["DNA accessibility"],
    "status": "released",
    "date_released": "2025-09-30",
    "biosample_ontology": {
        "term_name": "regulatory T cell",
        "term_id": "CL:0000815",
        "classification": "primary cell",
    },
    "organism": {"scientific_name": "Mus musculus"},
    "biosample_summary": "Mus musculus regulatory T cell",
    "lab": {"title": "Tim Reddy, Duke", "name": "tim-reddy"},
    "award": "/awards/UM1HG009428/",
    "assembly": ["mm10"],
    "dbxrefs": ["GEO:GSE321371"],
    "files": [
        FILE,
        {
            **FILE,
            "accession": "ENCFF574DTB",
            "href": "/files/ENCFF574DTB/@@download/ENCFF574DTB.fastq.gz",
            "technical_replicates": ["1_1"],
        },
        {
            **FILE,
            "accession": "ENCFF705NGT",
            "file_format": "bam",
            "file_type": "bam",
            "output_type": "alignments",
            "assembly": "mm10",
            "href": "/files/ENCFF705NGT/@@download/ENCFF705NGT.bam",
        },
    ],
}


SEARCH = {"total": 935, "@graph": [EXPERIMENT, {**EXPERIMENT, "accession": "ENCSR032RGS", "biosample_ontology": {"term_name": "A549"}}]}


BIOSAMPLE = {
    "accession": BIOSAMPLE_ID,
    "@id": f"/biosamples/{BIOSAMPLE_ID}/",
    "summary": "Homo sapiens MCF-7 cell line",
    "description": "mammary gland, adenocarcinoma",
    "biosample_ontology": {"term_name": "MCF-7", "term_id": "EFO:0001203", "classification": "cell line", "@id": "/biosample-types/cell_line_EFO_0001203/"},
    "organism": {"scientific_name": "Homo sapiens", "@id": "/organisms/human/"},
    "life_stage": "adult",
    "age": "69",
    "age_units": "year",
    "sex": "female",
    "donor": "/human-donors/ENCDO000AAE/",
    "source": "/sources/atcc/",
    "lab": "/labs/richard-myers/",
    "award": "/awards/U54HG004576/",
    "status": "released",
    "date_created": "2013-12-12T05:50:02.101495+00:00",
    "aliases": ["encode:MCF7"],
    "dbxrefs": ["UCSC-ENCODE-cv:MCF-7"],
    "treatments": [],
    "genetic_modifications": [],
}


BIOSAMPLE_SEARCH = {
    "total": 4211,
    "@graph": [
        {
            **BIOSAMPLE,
            "accession": "ENCBS031YPZ",
            "summary": "Homo sapiens K562 cell line expressing RNAi",
            "description": "K562 cells treated with a control shRNA.",
            "biosample_ontology": "/biosample-types/cell_line_EFO_0002067/",
            "dbxrefs": ["GEO:SAMN05896797"],
        },
        {
            **BIOSAMPLE,
            "accession": "ENCBS086JQA",
            "summary": "Homo sapiens K562 cell line expressing RNAi",
            "description": "K562 cells treated with a control shRNA.",
            "biosample_ontology": "/biosample-types/cell_line_EFO_0002067/",
            "dbxrefs": ["GEO:SAMN05896851"],
        },
    ],
}


class EncodeMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = encode.EncodeMcpServer(self.client)

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

    def test_tools_list_exposes_encode_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "encode_experiment_lookup",
                "encode_experiment_search",
                "encode_biosample_lookup",
                "encode_biosample_search",
                "encode_file_lookup",
                "encode_file_manifest",
                "encode_status",
            },
        )

    def test_experiment_lookup_returns_frontend_compatible_project_record(self) -> None:
        result = self.call_tool("encode_experiment_lookup", {"accession": EXPERIMENT_ID, "max_files": 2})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table", "xref_groups", "download_manifest"})
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], EXPERIMENT_ID)
        self.assertEqual(record["data"]["assay_title"], "ATAC-seq")
        self.assertEqual(len(record["data"]["files"]), 2)
        self.assertIn("geo", record["identifiers"])

    def test_experiment_search_returns_bounded_project_records(self) -> None:
        result = self.call_tool("encode_experiment_search", {"query": "ATAC-seq", "max_results": 2, "status": "released"})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table"}, min_records=2)
        self.assertEqual(result["total"], 935)
        self.assertEqual(self.client.calls[-1][1]["searchTerm"], "ATAC-seq")
        self.assertEqual(self.client.calls[-1][1]["status"], "released")

    def test_biosample_lookup_returns_frontend_compatible_sample_record(self) -> None:
        result = self.call_tool("encode_biosample_lookup", {"accession": BIOSAMPLE_ID})
        assert_result_frontend_contract(self, result, expected_components={"sample"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(record["data"]["accession"], BIOSAMPLE_ID)
        self.assertEqual(record["data"]["biosample_term_name"], "MCF-7")
        self.assertEqual(record["data"]["organism"], "Homo sapiens")
        self.assertEqual(result["biosample"]["biosample"], "MCF-7")

    def test_biosample_search_returns_bounded_sample_records(self) -> None:
        result = self.call_tool("encode_biosample_search", {"query": "K562", "max_results": 2, "status": "released", "organism": "Homo sapiens"})
        assert_result_frontend_contract(self, result, expected_components={"sample"}, required_preview_kinds={"table", "xref_groups"}, min_records=2)
        self.assertEqual(result["total"], 4211)
        self.assertEqual(self.client.calls[-1][1]["type"], "Biosample")
        self.assertEqual(self.client.calls[-1][1]["organism.scientific_name"], "Homo sapiens")

    def test_file_lookup_returns_download_plan_record(self) -> None:
        result = self.call_tool("encode_file_lookup", {"accession": FILE_ID})
        assert_result_frontend_contract(self, result, expected_components={"download_plan"}, required_preview_kinds={"download_manifest", "table"})
        record = result["records"][0]
        first = record["data"]["files"][0]
        self.assertEqual(first["accession"], FILE_ID)
        self.assertTrue(first["download_url"].endswith(f"{FILE_ID}.fastq.gz"))

    def test_file_manifest_can_filter_file_format(self) -> None:
        result = self.call_tool("encode_file_manifest", {"experiment_accession": EXPERIMENT_ID, "file_format": "bam"})
        assert_result_frontend_contract(self, result, expected_components={"download_plan"}, required_preview_kinds={"download_manifest", "table"})
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["files"][0]["file_format"], "bam")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("encode_status", {})
        self.assertEqual(result["server"], "encode")
        self.assertIn("encode_experiment_lookup", result["available_tools"])
        self.assertIn("encode_biosample_lookup", result["available_tools"])
        self.assertIn("project", result["frontend_components"])
        self.assertIn("sample", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("encode_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_accession"], EXPERIMENT_ID)


if __name__ == "__main__":
    unittest.main()
