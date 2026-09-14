from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "gnomad" / "server.py"
SPEC = importlib.util.spec_from_file_location("gnomad_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
gnomad = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gnomad
SPEC.loader.exec_module(gnomad)


class FakeClient:
    def __init__(self) -> None:
        self.config = gnomad.GnomadConfig(contact=None)
        self.requests_per_second = 1
        self.calls = []

    def request_graphql_with_headers(self, query, variables):
        self.calls.append((query, variables))
        if "variant(" in query:
            return {"data": {"variant": GNOMAD_VARIANT}}, {"content-type": "application/json"}
        if "gene(" in query:
            return {"data": {"gene": GNOMAD_GENE}}, {"content-type": "application/json"}
        if "meta" in query:
            return {"data": {"meta": {"clinvar_release_date": "2026-06-06"}}}, {"content-type": "application/json"}
        raise AssertionError("unexpected query")


GNOMAD_VARIANT = {
    "variantId": "1-230710048-A-G",
    "chrom": "1",
    "pos": 230710048,
    "ref": "A",
    "alt": "G",
    "genome": {
        "ac": 87993,
        "an": 152182,
        "af": 0.5782089866081402,
        "homozygote_count": 28034,
        "filters": [],
        "populations": [
            {"id": "afr", "ac": 34498, "an": 41542, "homozygote_count": 14363},
            {"id": "nfe", "ac": 28599, "an": 67976, "homozygote_count": 6054},
        ],
    },
    "exome": {
        "ac": 669469,
        "an": 1461692,
        "af": 0.45800962172605447,
        "homozygote_count": 163148,
        "filters": [],
        "populations": [
            {"id": "afr", "ac": 28371, "an": 33480, "homozygote_count": 12021},
            {"id": "nfe", "ac": 455815, "an": 1111932, "homozygote_count": 93363},
        ],
    },
    "transcript_consequences": [
        {
            "gene_id": "ENSG00000135744",
            "gene_symbol": "AGT",
            "transcript_id": "ENST00000366667",
            "consequence_terms": ["missense_variant"],
            "hgvsc": "c.776T>C",
            "hgvsp": "p.Met259Thr",
            "lof": None,
            "lof_filter": None,
            "lof_flags": None,
        }
    ],
}


GNOMAD_GENE = {
    "gene_id": "ENSG00000141510",
    "symbol": "TP53",
    "name": "tumor protein p53",
    "chrom": "17",
    "start": 7661779,
    "stop": 7687546,
    "strand": "-",
    "canonical_transcript_id": "ENST00000269305",
    "transcripts": [
        {"transcript_id": "ENST00000269305", "transcript_version": "9"},
        {"transcript_id": "ENST00000420246", "transcript_version": "6"},
    ],
    "gnomad_constraint": {
        "exp_syn": 265.4,
        "obs_syn": 258,
        "oe_syn": 0.972,
        "exp_mis": 514.2,
        "obs_mis": 213,
        "oe_mis": 0.414,
        "exp_lof": 45.1,
        "obs_lof": 5,
        "oe_lof": 0.111,
        "oe_lof_upper": 0.2,
        "pLI": 1.0,
    },
}


class GnomadMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = gnomad.GnomadMcpServer(self.client)

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

    def test_tools_list_exposes_gnomad_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "gnomad_parameter_domains",
                "gnomad_resolve_context",
                "gnomad_variant_lookup",
                "gnomad_gene_lookup",
                "gnomad_status",
            },
        )

    def test_variant_lookup_returns_frontend_compatible_variant_record(self) -> None:
        result = self.call_tool(
            "gnomad_variant_lookup",
            {"variant_id": "1-230710048-A-G", "dataset": "gnomad_r4", "max_populations": 4},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"variant"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["stable_id"], "gnomAD:gnomad_r4:1-230710048-A-G")
        self.assertEqual(record["display"]["component"], "variant")
        self.assertEqual(record["data"]["primary_gene"], "AGT")
        self.assertEqual(record["data"]["population_rows"][0]["af"], 34498 / 41542)

    def test_gene_lookup_returns_frontend_compatible_gene_record(self) -> None:
        result = self.call_tool(
            "gnomad_gene_lookup",
            {"gene_id": "ENSG00000141510", "reference_genome": "GRCh38"},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["display"]["component"], "gene")
        self.assertEqual(record["identifiers"]["ensembl_gene"]["id"], "ENSG00000141510")
        self.assertEqual(record["data"]["constraint"]["pLI"], 1.0)

    def test_resolve_context_returns_gene_candidate_and_calls(self) -> None:
        result = self.call_tool(
            "gnomad_resolve_context",
            {"gene_id": "ENSG00000141510", "max_results": 4},
        )
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["entities"][0]["value"], "ENSG00000141510")
        self.assertIn("/gene/ENSG00000141510", result["entities"][0]["url"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("gnomad_gene_lookup", tool_names)
        self.assertIn("ensembl_lookup", tool_names)

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("gnomad_status", {})
        self.assertEqual(result["server"], "gnomad")
        self.assertIn("gnomad_variant_lookup", result["available_tools"])
        self.assertIn("variant", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("gnomad_status", {"check_network": True})
        self.assertEqual(result["network_check"]["clinvar_release_date"], "2026-06-06")


if __name__ == "__main__":
    unittest.main()
