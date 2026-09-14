from __future__ import annotations

import importlib.util
import inspect
import json
import pathlib
import sys
import unittest
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]


EXPECTED_MCP_SERVERS = {
    "alphafold",
    "biorxiv",
    "biostudies",
    "cbioportal",
    "cellxgene",
    "chebi",
    "chembl",
    "clinvar",
    "efo",
    "encode",
    "ensembl",
    "gnomad",
    "gwas",
    "hmdb",
    "hpa",
    "kegg",
    "metabolights",
    "mgnify",
    "ncbi",
    "opentargets",
    "pride",
    "pubchem",
    "quickgo",
    "rcsb",
    "reactome",
    "rnacentral",
    "string",
    "uniprot",
    "visualization",
}


MANIFEST_TERMS = {
    "alphafold": "alphafold",
    "biorxiv": "biorxiv",
    "biostudies": "biostudies",
    "cbioportal": "cbioportal",
    "cellxgene": "cellxgene",
    "chebi": "chebi",
    "chembl": "chembl",
    "clinvar": "clinvar",
    "efo": "efo",
    "encode": "encode",
    "ensembl": "ensembl",
    "gnomad": "gnomad",
    "gwas": "gwas",
    "hmdb": "hmdb",
    "hpa": "human protein atlas",
    "kegg": "kegg",
    "metabolights": "metabolights",
    "mgnify": "mgnify",
    "ncbi": "ncbi",
    "opentargets": "open targets",
    "pride": "pride",
    "pubchem": "pubchem",
    "quickgo": "quickgo",
    "rcsb": "rcsb",
    "reactome": "reactome",
    "rnacentral": "rnacentral",
    "string": "string",
    "uniprot": "uniprot",
    "visualization": "visualization",
}


def mcp_config() -> dict[str, Any]:
    payload = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))
    return payload["mcpServers"]


def load_server_module(server_name: str, server_path: pathlib.Path) -> Any:
    module_name = f"inventory_{server_name}_server"
    spec = importlib.util.spec_from_file_location(module_name, server_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def server_instance(module: Any) -> Any:
    server_classes = [
        cls
        for name, cls in vars(module).items()
        if inspect.isclass(cls) and name.endswith("McpServer")
    ]
    client_classes = [
        cls
        for name, cls in vars(module).items()
        if inspect.isclass(cls) and name.endswith("Client")
    ]
    config_classes = [
        cls
        for name, cls in vars(module).items()
        if inspect.isclass(cls) and name.endswith("Config")
    ]
    if len(server_classes) != 1:
        raise AssertionError(f"expected one MCP server class, found {server_classes!r}")
    if client_classes:
        if len(client_classes) != 1 or len(config_classes) != 1:
            raise AssertionError("client-backed MCP servers must expose one Client and one Config class")
        return server_classes[0](client_classes[0](config_classes[0]()))
    return server_classes[0]()


def handle(server: Any, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = server.handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
    assert response is not None
    return response


class McpInventoryContractTests(unittest.TestCase):
    def test_mcp_config_declares_expected_server_entrypoints(self) -> None:
        config = mcp_config()
        self.assertEqual(EXPECTED_MCP_SERVERS, set(config))
        for server_name, entry in config.items():
            with self.subTest(server=server_name):
                self.assertEqual(entry["command"], "python3")
                self.assertEqual(entry["cwd"], ".")
                self.assertIsInstance(entry.get("env_vars"), list)
                self.assertEqual(len(entry["args"]), 1)
                server_path = ROOT / entry["args"][0]
                self.assertTrue(server_path.exists(), server_path)
                self.assertEqual(server_path.name, "server.py")

    def test_tool_definitions_handlers_and_status_inventory_stay_aligned(self) -> None:
        for server_name, entry in mcp_config().items():
            with self.subTest(server=server_name):
                module = load_server_module(server_name, ROOT / entry["args"][0])
                server = server_instance(module)
                response = handle(server, "tools/list")
                tools = response["result"]["tools"]
                tool_names = [tool["name"] for tool in tools]
                self.assertTrue(tool_names)
                self.assertEqual(len(tool_names), len(set(tool_names)))
                self.assertTrue(all(isinstance(tool.get("inputSchema"), dict) for tool in tools))

                handlers = getattr(module, "TOOL_HANDLERS", None)
                self.assertIsInstance(handlers, dict)
                self.assertEqual(set(tool_names), set(handlers))

                parameter_tools = [name for name in tool_names if name.endswith("_parameter_domains")]
                self.assertEqual(1, len(parameter_tools))

                status_tool = (
                    "omics_visualization_status"
                    if server_name == "visualization"
                    else f"{server_name}_status"
                )
                self.assertIn(status_tool, tool_names)
                status_response = handle(
                    server,
                    "tools/call",
                    {"name": status_tool, "arguments": {"check_network": False}},
                )
                status = status_response["result"]["structuredContent"]
                self.assertEqual(set(tool_names), set(status["available_tools"]))

    def test_manifest_capabilities_cover_each_declared_mcp_server(self) -> None:
        manifest = json.loads((ROOT / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
        manifest_text = json.dumps(manifest["interface"], ensure_ascii=False).lower()
        for server_name in sorted(EXPECTED_MCP_SERVERS):
            with self.subTest(server=server_name):
                self.assertIn(MANIFEST_TERMS[server_name], manifest_text)


if __name__ == "__main__":
    unittest.main()
