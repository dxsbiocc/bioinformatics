from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "clinvar" / "server.py"
SPEC = importlib.util.spec_from_file_location("clinvar_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
clinvar = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = clinvar
SPEC.loader.exec_module(clinvar)


class FakeClient:
    def __init__(self) -> None:
        self.config = clinvar.ClinvarConfig(email=None, api_key=None)
        self.requests_per_second = 3
        self.calls = []

    def request_clinical_tables_with_headers(self, params):
        self.calls.append(("clinical_tables", params))
        return CLINICAL_TABLES_SEARCH, {"content-type": "application/json"}

    def request_eutils_json_with_headers(self, endpoint, params):
        self.calls.append(("eutils", endpoint, params))
        if params.get("id") in {"37390", "4887763", "37390,4887763"}:
            return ESUMMARY_MULTI if "," in params.get("id", "") else ESUMMARY_SINGLE, {
                "content-type": "application/json"
            }
        raise AssertionError(f"unexpected ESummary request: {endpoint} {params}")


CLINVAR_SUMMARY = {
    "uid": "37390",
    "title": "NM_007294.4(BRCA1):c.1105G>A (p.Asp369Asn)",
    "accession": "VCV000037390",
    "accession_version": "VCV000037390.4",
    "obj_type": "single nucleotide variant",
    "germline_classification": {
        "description": "Uncertain significance",
        "last_evaluated": "2025/01/01 00:00",
        "review_status": "criteria provided, multiple submitters, no conflicts",
        "trait_set": [{"trait_name": "Hereditary breast ovarian cancer syndrome"}],
    },
    "variation_set": [
        {
            "variation_name": "NM_007294.4(BRCA1):c.1105G>A (p.Asp369Asn)",
            "cdna_change": "c.1105G>A",
            "variant_type": "single nucleotide variant",
            "canonical_spdi": "NC_000017.11:43094425:C:T",
            "variation_xrefs": [{"db_source": "dbSNP", "db_id": "56056711"}],
            "variation_loc": [
                {
                    "status": "current",
                    "assembly_name": "GRCh38",
                    "chr": "17",
                    "start": "43094426",
                    "stop": "43094426",
                    "display_start": "43094426",
                    "display_stop": "43094426",
                    "band": "17q21.31",
                    "assembly_acc_ver": "GCF_000001405.38",
                }
            ],
            "allele_freq_set": [{"source": "gnomAD", "value": "0.00002"}],
        }
    ],
    "genes": [{"symbol": "BRCA1", "geneid": "672", "strand": "-", "source": "submitted"}],
    "protein_change": "D369N",
    "supporting_submissions": {"scv": ["SCV000000001"], "rcv": ["RCV000000001"]},
}

CLINVAR_SUMMARY_2 = {
    **CLINVAR_SUMMARY,
    "uid": "4887763",
    "title": "NC_000017.10:g.(41234593_41242960)_(41243050_41243451)del",
    "accession": "VCV004887763",
    "accession_version": "VCV004887763.1",
    "germline_classification": {
        "description": "Pathogenic",
        "last_evaluated": "2026/06/22 00:00",
        "review_status": "criteria provided, single submitter",
        "trait_set": [{"trait_name": "Hereditary breast ovarian cancer syndrome"}],
    },
}

ESUMMARY_SINGLE = {
    "result": {
        "uids": ["37390"],
        "37390": CLINVAR_SUMMARY,
    }
}

ESUMMARY_MULTI = {
    "result": {
        "uids": ["37390", "4887763"],
        "37390": CLINVAR_SUMMARY,
        "4887763": CLINVAR_SUMMARY_2,
    }
}

CLINICAL_TABLES_SEARCH = [
    2,
    ["37390", "4887763"],
    None,
    [
        ["37390", "NM_007294.4(BRCA1):c.1105G>A (p.Asp369Asn)"],
        ["4887763", "NC_000017.10:g.(41234593_41242960)_(41243050_41243451)del"],
    ],
]


class ClinvarMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = clinvar.ClinvarMcpServer(self.client)

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

    def test_tools_list_exposes_clinvar_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(names, {"clinvar_parameter_domains", "clinvar_resolve_context", "clinvar_lookup", "clinvar_search", "clinvar_status"})

    def test_lookup_returns_frontend_compatible_variant_record(self) -> None:
        result = self.call_tool("clinvar_lookup", {"identifier": "VCV000037390"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"variant"},
            required_preview_kinds={"table", "xref_groups"},
        )
        self.assertEqual(result["variant"]["uid"], "37390")
        record = result["records"][0]
        self.assertEqual(record["stable_id"], "VCV000037390.4")
        self.assertEqual(record["display"]["component"], "variant")
        self.assertEqual(record["identifiers"]["ncbi_gene"][0]["id"], "672")
        self.assertEqual(record["identifiers"]["dbsnp"][0]["label"], "rs56056711")
        self.assertEqual(record["data"]["classification"], "Uncertain significance")

    def test_search_hydrates_top_hits(self) -> None:
        result = self.call_tool(
            "clinvar_search",
            {"terms": "BRCA1", "max_results": 2, "hydrate": True},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"variant"},
            required_preview_kinds={"table", "xref_groups"},
            min_records=2,
        )
        self.assertEqual(result["returned"], 2)
        self.assertEqual(self.client.calls[0][0], "clinical_tables")
        self.assertEqual(self.client.calls[1][2]["id"], "37390,4887763")
        self.assertEqual(result["records"][1]["data"]["classification"], "Pathogenic")

    def test_resolve_context_returns_variant_candidates_and_calls(self) -> None:
        result = self.call_tool(
            "clinvar_resolve_context",
            {"query": "BRCA1", "max_results": 2},
        )
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["variants"][0]["metadata"]["uid"], "37390")
        self.assertIn("clinvar/variation/37390", result["variants"][0]["url"])
        self.assertEqual(result["recommended_calls"][0]["tool_name"], "clinvar_lookup")
        self.assertEqual(result["recommended_calls"][0]["arguments"]["identifier"], "VCV000037390.4")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("clinvar_status", {})
        self.assertEqual(result["server"], "clinvar")
        self.assertIn("clinvar_lookup", result["available_tools"])
        self.assertIn("variant", result["frontend_components"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
