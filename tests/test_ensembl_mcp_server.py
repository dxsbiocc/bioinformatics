from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "ensembl" / "server.py"
SPEC = importlib.util.spec_from_file_location("ensembl_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
ensembl = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ensembl
SPEC.loader.exec_module(ensembl)


class FakeClient:
    def __init__(self) -> None:
        self.config = ensembl.EnsemblConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "lookup/id/ENSG00000141510":
            return ENSEMBL_GENE, {"content-type": "application/json"}
        if endpoint == "xrefs/id/ENSG00000141510":
            return ENSEMBL_XREFS, {"content-type": "application/json"}
        if endpoint == "overlap/region/homo_sapiens/17:7661779-7687546":
            return ENSEMBL_OVERLAP, {"content-type": "application/json"}
        if endpoint == "variation/homo_sapiens/rs699":
            return ENSEMBL_VARIANT, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint: {endpoint}")


ENSEMBL_GENE = {
    "id": "ENSG00000141510",
    "display_name": "TP53",
    "description": "tumor protein p53 [Source:HGNC Symbol;Acc:HGNC:11998]",
    "object_type": "Gene",
    "species": "homo_sapiens",
    "seq_region_name": "17",
    "start": 7661779,
    "end": 7687546,
    "strand": -1,
    "biotype": "protein_coding",
    "assembly_name": "GRCh38",
    "version": 21,
    "canonical_transcript": "ENST00000269305.9",
    "Transcript": [
        {
            "id": "ENST00000269305",
            "display_name": "TP53-201",
            "biotype": "protein_coding",
            "seq_region_name": "17",
            "start": 7661779,
            "end": 7687546,
            "strand": -1,
            "is_canonical": 1,
            "version": 9,
        }
    ],
}

ENSEMBL_XREFS = [
    {
        "dbname": "HGNC",
        "display_id": "TP53",
        "primary_id": "HGNC:11998",
        "description": "tumor protein p53",
        "info_type": "DIRECT",
        "synonyms": [],
        "version": "0",
    },
    {
        "dbname": "EntrezGene",
        "display_id": "TP53",
        "primary_id": "7157",
        "description": "tumor protein p53",
        "info_type": "DEPENDENT",
        "synonyms": [],
        "version": "0",
    },
]

ENSEMBL_OVERLAP = [
    {
        "id": "ENSG00000141510",
        "external_name": "TP53",
        "feature_type": "gene",
        "seq_region_name": "17",
        "start": 7661779,
        "end": 7687546,
        "strand": -1,
        "biotype": "protein_coding",
        "description": "tumor protein p53 [Source:HGNC Symbol;Acc:HGNC:11998]",
        "source": "ensembl_havana",
    },
    {
        "id": "rs889884213",
        "feature_type": "variation",
        "consequence_type": "intergenic_variant",
        "seq_region_name": "17",
        "start": 7668416,
        "end": 7668416,
        "strand": 1,
        "source": "dbSNP",
    },
]

ENSEMBL_VARIANT = {
    "name": "rs699",
    "source": "Variants imported from dbSNP",
    "var_class": "SNP",
    "MAF": None,
    "ambiguity": "R",
    "minor_allele": "G",
    "most_severe_consequence": "missense_variant",
    "clinical_significance": ["benign"],
    "evidence": ["Frequency", "1000Genomes", "Cited"],
    "synonyms": ["VAR_007096", "NM_000029.3:c.803T>C"],
    "mappings": [
        {
            "coord_system": "chromosome",
            "seq_region_name": "1",
            "location": "1:230710048-230710048",
            "start": 230710048,
            "assembly_name": "GRCh38",
            "end": 230710048,
            "strand": 1,
            "allele_string": "A/G",
            "ancestral_allele": "G",
        }
    ],
}


class EnsemblMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = ensembl.EnsemblMcpServer(self.client)

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

    def test_tools_list_exposes_ensembl_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "ensembl_parameter_domains",
                "ensembl_resolve_context",
                "ensembl_lookup",
                "ensembl_xrefs",
                "ensembl_overlap_region",
                "ensembl_variation",
                "ensembl_status",
            },
        )

    def test_lookup_returns_frontend_compatible_gene_record(self) -> None:
        result = self.call_tool(
            "ensembl_lookup",
            {"ensembl_id": "ENSG00000141510", "expand": True, "include_xrefs": True},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"table", "xref_groups"},
        )
        self.assertEqual(result["record"]["display_name"], "TP53")
        record = result["records"][0]
        self.assertEqual(record["stable_id"], "Ensembl:ENSG00000141510")
        self.assertEqual(record["display"]["component"], "gene")
        self.assertEqual(record["identifiers"]["hgnc"]["id"], "HGNC:11998")
        self.assertEqual(record["identifiers"]["ncbi_gene"]["id"], "7157")

    def test_xrefs_returns_identifier_conversion_record(self) -> None:
        result = self.call_tool(
            "ensembl_xrefs",
            {"ensembl_id": "ENSG00000141510", "all_levels": True, "max_results": 2},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"identifier_conversion"},
            required_preview_kinds={"table", "xref_groups"},
        )
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["records"][0]["data"]["total"], 2)

    def test_resolve_context_returns_stable_id_and_xref_calls(self) -> None:
        result = self.call_tool(
            "ensembl_resolve_context",
            {"ensembl_id": "ENSG00000141510", "max_results": 5},
        )
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["features"][0]["value"], "ENSG00000141510")
        self.assertIn("ensembl", result["features"][0]["url"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("ensembl_lookup", tool_names)
        self.assertIn("ensembl_xrefs", tool_names)
        self.assertEqual(self.client.calls[0][0], "lookup/id/ENSG00000141510")
        self.assertEqual(self.client.calls[1][0], "xrefs/id/ENSG00000141510")

    def test_overlap_region_returns_gene_and_variant_records(self) -> None:
        result = self.call_tool(
            "ensembl_overlap_region",
            {
                "species": "homo_sapiens",
                "region": "17:7661779-7687546",
                "features": ["gene", "variation"],
                "max_results": 2,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene", "variant"},
            required_preview_kinds={"table", "xref_groups"},
            min_records=2,
        )
        self.assertEqual(result["returned"], 2)
        self.assertEqual(result["records"][1]["record_type"], "ensembl_variant")

    def test_variation_returns_variant_record(self) -> None:
        result = self.call_tool(
            "ensembl_variation",
            {"species": "homo_sapiens", "variant_id": "rs699"},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"variant"},
            required_preview_kinds={"table", "xref_groups"},
        )
        self.assertEqual(result["variant"]["id"], "rs699")
        record = result["records"][0]
        self.assertEqual(record["display"]["component"], "variant")
        self.assertEqual(record["data"]["primary_location"], "1:230710048-230710048")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("ensembl_status", {})
        self.assertEqual(result["server"], "ensembl")
        self.assertIn("ensembl_lookup", result["available_tools"])
        self.assertIn("variant", result["frontend_components"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
