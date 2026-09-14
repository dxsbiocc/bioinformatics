from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "kegg" / "server.py"
SPEC = importlib.util.spec_from_file_location("kegg_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
kegg = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = kegg
SPEC.loader.exec_module(kegg)

from mcp.kegg.constants import FIND_OPTIONS, GET_OPTIONS


class FakeClient:
    def __init__(self) -> None:
        self.config = kegg.KeggConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_text_with_headers(self, operation, segments):
        self.calls.append((operation, segments))
        endpoint = "/".join([operation, *segments])
        url = self.build_url(operation, segments)
        if operation == "info" and segments == ["kegg"]:
            return KEGG_INFO, {"content-type": "text/plain"}, endpoint, url
        if operation == "list" and segments == ["pathway", "hsa"]:
            return KEGG_LIST, {"content-type": "text/plain"}, endpoint, url
        if operation == "list" and segments == ["organism"]:
            return KEGG_ORGANISMS, {"content-type": "text/plain"}, endpoint, url
        if operation == "find" and segments == ["compound", "glucose"]:
            return KEGG_FIND, {"content-type": "text/plain"}, endpoint, url
        if operation == "get" and segments == ["path:hsa00010"]:
            return KEGG_PATHWAY, {"content-type": "text/plain"}, endpoint, url
        if operation == "get" and segments == ["hsa:10458", "aaseq"]:
            return KEGG_FASTA, {"content-type": "text/plain"}, endpoint, url
        if operation == "conv" and segments == ["ncbi-geneid", "hsa:10458"]:
            return KEGG_CONV, {"content-type": "text/plain"}, endpoint, url
        if operation == "link" and segments == ["pathway", "hsa:10458"]:
            return KEGG_LINK, {"content-type": "text/plain"}, endpoint, url
        if operation == "ddi" and segments == ["D00564"]:
            return KEGG_DDI, {"content-type": "text/plain"}, endpoint, url
        raise AssertionError(f"unexpected request: {operation} {segments}")

    def build_url(self, operation, segments):
        suffix = "/".join([operation, *segments])
        return f"{self.config.base_url}/{suffix}"

    def entry_url(self, entry_id):
        return f"{self.config.website_base_url}/entry/{entry_id}"


KEGG_INFO = """kegg             Kyoto Encyclopedia of Genes and Genomes
Release 110.0+/09-01, Sep 24
KEGG is a database resource for understanding high-level functions and utilities.
"""

KEGG_LIST = """path:hsa00010\tGlycolysis / Gluconeogenesis - Homo sapiens (human)
path:hsa04110\tCell cycle - Homo sapiens (human)
"""

KEGG_ORGANISMS = """9606\thsa\tHomo sapiens (human)\tEukaryotes;Animals;Vertebrates;Mammals
10090\tmmu\tMus musculus (mouse)\tEukaryotes;Animals;Vertebrates;Mammals
"""

KEGG_FIND = """cpd:C00031\tD-Glucose; Grape sugar
cpd:C00221\tbeta-D-Glucose
"""

KEGG_PATHWAY = """ENTRY       hsa00010                    Pathway
NAME        Glycolysis / Gluconeogenesis - Homo sapiens (human)
DESCRIPTION Glycolysis / Gluconeogenesis
MODULE      hsa_M00001  Glycolysis (Embden-Meyerhof pathway), glucose => pyruvate
GENE        10327 HKDC1; hexokinase domain containing 1 [KO:K00844] [EC:2.7.1.1]
            226 ALDOA; aldolase, fructose-bisphosphate A [KO:K01623] [EC:4.1.2.13]
COMPOUND    C00031  D-Glucose
            C00022  Pyruvate
DBLINKS     GO: 0006096
///
"""

KEGG_FASTA = """>hsa:10458 BAIAP2; BAR/IMD domain containing adaptor protein 2
MAQSGEGEAAAPSADGPAE
"""

KEGG_CONV = """hsa:10458\tncbi-geneid:10458
"""

KEGG_LINK = """hsa:10458\tpath:hsa04810
hsa:10458\tpath:hsa04520
"""

KEGG_DDI = """dr:D00564\tdr:D00109
"""


class KeggMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = kegg.KeggMcpServer(self.client)

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

    def test_tools_list_exposes_kegg_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "kegg_parameter_domains",
                "kegg_resolve_context",
                "kegg_info",
                "kegg_list",
                "kegg_find",
                "kegg_get",
                "kegg_conv",
                "kegg_link",
                "kegg_ddi",
                "kegg_color_pathway_url",
                "kegg_color_pathway_from_table",
                "kegg_status",
            },
        )

    def test_info_returns_database_record(self) -> None:
        result = self.call_tool("kegg_info", {"database": "kegg"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"database"},
            required_preview_kinds={"text"},
        )
        self.assertEqual(result["database_info"]["database"], "kegg")
        self.assertIn("rest.kegg.jp/info/kegg", result["source"]["url"])

    def test_list_returns_pathway_records(self) -> None:
        result = self.call_tool("kegg_list", {"database": "pathway", "option": "hsa", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"table", "xref_groups"},
        )
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["records"][0]["data"]["entry_id"], "path:hsa00010")

    def test_find_returns_compound_records(self) -> None:
        result = self.call_tool("kegg_find", {"database": "compound", "query": "glucose", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"table", "xref_groups"},
        )
        self.assertEqual(result["records"][0]["record_type"], "kegg_compound")

    def test_get_parses_flat_file_pathway(self) -> None:
        result = self.call_tool("kegg_get", {"entry_ids": ["path:hsa00010"]})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"table", "xref_groups", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["entry_id"], "hsa00010")
        self.assertEqual(record["record_type"], "kegg_pathway")
        self.assertEqual(record["data"]["compounds"][0]["id"], "C00031")

    def test_get_parses_fasta_sequence(self) -> None:
        result = self.call_tool("kegg_get", {"entry_ids": ["hsa:10458"], "option": "aaseq"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein"},
            required_preview_kinds={"sequence"},
        )
        self.assertEqual(result["records"][0]["data"]["alphabet"], "protein")
        self.assertEqual(result["records"][0]["data"]["length"], 19)

    def test_get_download_option_returns_manifest_without_fetching_binary(self) -> None:
        result = self.call_tool("kegg_get", {"entry_ids": ["path:hsa00010"], "option": "image"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"download_manifest"},
        )
        self.assertEqual(self.client.calls, [])
        self.assertIn("/get/path:hsa00010/image", result["records"][0]["url"])

    def test_conv_returns_identifier_conversion_record(self) -> None:
        result = self.call_tool(
            "kegg_conv",
            {"target_db": "ncbi-geneid", "source_db_or_entries": "hsa:10458"},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"identifier_conversion"},
            required_preview_kinds={"table"},
        )
        self.assertEqual(result["rows"][0]["target"], "ncbi-geneid:10458")

    def test_link_returns_linkset_record_with_network_preview(self) -> None:
        result = self.call_tool(
            "kegg_link",
            {"target_db": "pathway", "source_db_or_entries": "hsa:10458"},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"linkset"},
            required_preview_kinds={"table", "network"},
        )
        self.assertEqual(result["total"], 2)

    def test_ddi_returns_linkset_record(self) -> None:
        result = self.call_tool("kegg_ddi", {"entry_ids": ["D00564"]})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"linkset"},
            required_preview_kinds={"table", "network"},
        )
        self.assertEqual(result["rows"][0]["source"], "dr:D00564")

    def test_color_pathway_url_returns_clickable_pathway_record(self) -> None:
        result = self.call_tool(
            "kegg_color_pathway_url",
            {
                "map_id": "hsa04110",
                "items": [
                    {"kegg_id": "hsa:7157", "bgcolor": "#d73027", "fgcolor": "#000000", "label": "TP53"},
                    {"kegg_id": "hsa:4609", "color": "#4575b4,#000000", "label": "MYC"},
                ],
                "nocolor": True,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"table", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["record_type"], "kegg_colored_pathway")
        self.assertIn("show_pathway?map=hsa04110", record["url"])
        self.assertIn("hsa%3A7157%20%23d73027%2C%23000000", record["url"])
        self.assertIn("nocolor=1", record["url"])
        self.assertEqual(record["data"]["items"][0]["label"], "TP53")
        self.assertEqual(self.client.calls, [])

    def test_color_pathway_from_table_auto_colors_directional_values(self) -> None:
        result = self.call_tool(
            "kegg_color_pathway_from_table",
            {
                "map_id": "hsa04110",
                "rows": [
                    {"kegg_id": "hsa:7157", "symbol": "TP53", "log2fc": 2.4, "padj": 0.001},
                    {"kegg_id": "hsa:4609", "symbol": "MYC", "log2fc": -1.7, "padj": 0.02},
                    {"kegg_id": "hsa:9999", "symbol": "NEUTRAL", "log2fc": 0.1, "padj": 0.5},
                ],
                "label_column": "symbol",
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"table", "text"},
        )
        record = result["records"][0]
        self.assertEqual(result["input_rows"], 3)
        self.assertEqual(result["item_count"], 2)
        self.assertEqual(result["skipped_row_count"], 1)
        self.assertEqual(record["data"]["items"][0]["direction"], "up")
        self.assertEqual(record["data"]["items"][1]["direction"], "down")
        self.assertIn("hsa:7157 #d73027,#000000", result["multi_query"])
        self.assertEqual(self.client.calls, [])

    def test_resolve_context_returns_coloring_hints_without_network(self) -> None:
        result = self.call_tool("kegg_resolve_context", {"context_type": "coloring", "map_id": "hsa04110"})
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(self.client.calls, [])
        parameter_names = {context["parameter_name"] for context in result["contexts"]}
        self.assertIn("items[].kegg_id", parameter_names)
        self.assertIn("url_form", parameter_names)
        calls = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("kegg_color_pathway_url", calls)
        self.assertIn("kegg_color_pathway_from_table", calls)

    def test_resolve_context_returns_pathway_candidates_and_recommended_calls(self) -> None:
        result = self.call_tool("kegg_resolve_context", {"context_type": "pathways", "organism": "hsa", "query": "cell", "max_results": 5})
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["pathways"][0]["value"], "hsa04110")
        tool_names = [call["tool_name"] for call in result["recommended_calls"]]
        self.assertIn("kegg_get", tool_names)
        self.assertIn("kegg_color_pathway_url", tool_names)
        color_call = [call for call in result["recommended_calls"] if call["tool_name"] == "kegg_color_pathway_url"][0]
        self.assertEqual(color_call["arguments"]["map_id"], "hsa04110")

    def test_resolve_context_returns_organism_candidates(self) -> None:
        result = self.call_tool("kegg_resolve_context", {"context_type": "organisms", "query": "human", "max_results": 5})
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["organisms"][0]["value"], "hsa")
        self.assertIn("rest.kegg.jp/list/organism", result["source"]["url"])

    def test_parameter_domains_reports_kegg_enums(self) -> None:
        result = self.call_tool("kegg_parameter_domains", {"parameter_name": "option", "domain_type": "enum"})
        self.assertGreaterEqual(result["returned"], 2)
        enums = {tuple(domain["enum"]) for domain in result["domains"]}
        self.assertIn(tuple(GET_OPTIONS), enums)
        self.assertIn(tuple(FIND_OPTIONS), enums)

    def test_status_reports_rate_limit_and_license_without_network(self) -> None:
        result = self.call_tool("kegg_status", {})
        self.assertEqual(result["server"], "kegg")
        self.assertEqual(result["rate_limit_requests_per_second"], 3)
        self.assertIn("license_notice", result)
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
