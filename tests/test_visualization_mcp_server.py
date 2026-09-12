from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "visualization" / "server.py"
SPEC = importlib.util.spec_from_file_location("visualization_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
visualization = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = visualization
SPEC.loader.exec_module(visualization)


class VisualizationMcpServerTests(unittest.TestCase):
    def call_tool(self, name: str, arguments: dict) -> dict:
        server = visualization.VisualizationMcpServer()
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {"name": name, "arguments": arguments},
            }
        )
        self.assertIsNotNone(response)
        self.assertNotIn("error", response)
        content = response["result"]["content"][0]["text"]
        self.assertEqual(json.loads(content), response["result"]["structuredContent"])
        return response["result"]["structuredContent"]

    def write_table(self, table_text: str, filename: str = "input.tsv") -> tuple[tempfile.TemporaryDirectory, pathlib.Path]:
        tmpdir = tempfile.TemporaryDirectory()
        table_path = pathlib.Path(tmpdir.name) / filename
        table_path.write_text(table_text, encoding="utf-8")
        return tmpdir, table_path

    def test_tools_list_includes_route_coverage_and_status(self) -> None:
        server = visualization.VisualizationMcpServer()
        response = server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        self.assertIsNotNone(response)
        tools = {tool["name"] for tool in response["result"]["tools"]}
        self.assertIn("omics_visualization_route", tools)
        self.assertIn("omics_visualization_contract_coverage", tools)
        self.assertIn("omics_visualization_status", tools)

    def test_route_tool_returns_frontend_compatible_one_to_many_recommendation(self) -> None:
        tmpdir, table_path = self.write_table(
            "\n".join(
                [
                    "focal_entity\trelated_entity\tclass\trho\tq_value",
                    "metabolite_A\tpathway_1\tlipid\t0.42\t0.001",
                    "metabolite_A\tpathway_2\tstress\t-0.31\t0.020",
                    "metabolite_A\tpathway_3\tstress\t0.18\t0.080",
                ]
            )
        )
        with tmpdir:
            payload = self.call_tool(
                "omics_visualization_route",
                {
                    "table_path": str(table_path),
                    "query": "center one-to-many association",
                    "top": 2,
                    "include_profile": False,
                },
            )
        self.assertEqual(payload["selected"]["id"], "scatter-one2many")
        self.assertEqual(payload["selected"]["confidence"], "high")
        self.assertEqual(payload["selected"]["role_mapping"]["target_entity"], "related_entity")
        self.assertIn("one_to_many_association", payload["input_profile_summary"]["shapes"])
        self.assertNotIn("input_profile", payload)
        assert_result_frontend_contract(
            self,
            payload,
            expected_components={"dataset"},
            required_preview_kinds={"table"},
        )

    def test_route_tool_supports_relative_path_and_exact_heatmap_request(self) -> None:
        tmpdir, table_path = self.write_table(
            "\n".join(
                [
                    "focal_entity\ttarget_entity\tcategory\tspearman_rho\tp_value",
                    "entity_A\tfeature_1\tprocess_alpha\t0.61\t0.0001",
                    "entity_A\tfeature_2\tprocess_alpha\t0.58\t0.0003",
                    "entity_A\tfeature_3\tprocess_beta\t-0.34\t0.0100",
                    "entity_A\tfeature_4\tprocess_beta\t-0.28\t0.0200",
                ]
            ),
            filename="association_grid.tsv",
        )
        with tmpdir:
            payload = self.call_tool(
                "omics_visualization_route",
                {
                    "base_dir": str(table_path.parent),
                    "table_path": table_path.name,
                    "query": "先用 heatmap-corr-bubble 看看效果",
                    "top": 3,
                },
            )
        self.assertEqual(payload["selected"]["id"], "heatmap-corr-bubble")
        self.assertEqual(payload["selected"]["confidence"], "high")
        self.assertEqual(payload["selected"]["role_mapping"]["x_category"], "target_entity")
        self.assertEqual(payload["selected"]["role_mapping"]["y_category"], "category")
        assert_result_frontend_contract(
            self,
            payload,
            expected_components={"dataset"},
            required_preview_kinds={"table"},
        )

    def test_contract_coverage_tool_reports_catalog_totals(self) -> None:
        payload = self.call_tool("omics_visualization_contract_coverage", {"max_missing_per_family": 2})
        self.assertTrue(payload["ok"])
        self.assertGreaterEqual(payload["template_count"], 17)
        self.assertEqual(payload["catalog_template_count"], 152)
        self.assertEqual(payload["coverage"]["catalog_total"], 152)
        self.assertGreaterEqual(payload["coverage"]["contracted"], 20)
        assert_result_frontend_contract(
            self,
            payload,
            expected_components={"dataset"},
            required_preview_kinds={"table"},
        )

    def test_status_tool_reports_local_scripts(self) -> None:
        payload = self.call_tool("omics_visualization_status", {})
        self.assertTrue(all(payload["script_files_available"].values()))
        self.assertIn("omics_visualization_route", payload["available_tools"])
        self.assertEqual(payload["frontend_components"], ["dataset"])
        assert_result_frontend_contract(
            self,
            payload,
            expected_components={"dataset"},
            required_preview_kinds={"table"},
        )

    def test_missing_table_path_returns_json_rpc_validation_error(self) -> None:
        server = visualization.VisualizationMcpServer()
        with self.assertRaises(visualization.McpError):
            server.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/call",
                    "params": {
                        "name": "omics_visualization_route",
                        "arguments": {"table_path": "/missing/nope.tsv", "query": "scatter"},
                    },
                }
            )


if __name__ == "__main__":
    unittest.main()
