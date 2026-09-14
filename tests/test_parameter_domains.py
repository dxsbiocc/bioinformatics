from __future__ import annotations

import unittest

from mcp.parameter_domains import (
    make_parameter_domains_handler,
    parameter_domains_response,
    parameter_domains_tool_definition,
)


def demo_tool_definitions() -> list[dict]:
    return [
        parameter_domains_tool_definition("demo_parameter_domains"),
        {
            "name": "demo_search",
            "title": "Search demo records",
            "description": "Search demo records by query and category.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Free-text query."},
                    "category": {"type": "string", "enum": ["gene", "protein"], "default": "gene"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": {"readOnlyHint": True},
        },
        {
            "name": "demo_status",
            "title": "Inspect demo status",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
        },
    ]


class ParameterDomainTests(unittest.TestCase):
    def test_parameter_domains_searches_schema_domains(self) -> None:
        result = parameter_domains_response(
            server_name="demo",
            parameter_tool_name="demo_parameter_domains",
            tool_definitions=demo_tool_definitions(),
            args={"parameter_name": "category", "include_schema": True},
        )
        self.assertEqual(result["schema_version"], "bioinformatics.parameter_domains.v1")
        self.assertEqual(result["server"], "demo")
        self.assertEqual(result["returned"], 1)
        domain = result["domains"][0]
        self.assertEqual(domain["tool_name"], "demo_search")
        self.assertEqual(domain["parameter_name"], "category")
        self.assertEqual(domain["domain_type"], "enum")
        self.assertEqual(domain["enum"], ["gene", "protein"])
        self.assertEqual(domain["default"], "gene")
        self.assertIn("schema", domain)

    def test_parameter_domains_filters_numeric_ranges(self) -> None:
        result = parameter_domains_response(
            server_name="demo",
            parameter_tool_name="demo_parameter_domains",
            tool_definitions=demo_tool_definitions(),
            args={"domain_type": "integer_range"},
        )
        self.assertEqual(result["returned"], 1)
        domain = result["domains"][0]
        self.assertEqual(domain["parameter_name"], "max_results")
        self.assertEqual(domain["minimum"], 1)
        self.assertEqual(domain["maximum"], 50)

    def test_status_tools_are_excluded_by_default(self) -> None:
        result = parameter_domains_response(
            server_name="demo",
            parameter_tool_name="demo_parameter_domains",
            tool_definitions=demo_tool_definitions(),
            args={"parameter_name": "check_network"},
        )
        self.assertEqual(result["returned"], 0)
        with_status = parameter_domains_response(
            server_name="demo",
            parameter_tool_name="demo_parameter_domains",
            tool_definitions=demo_tool_definitions(),
            args={"parameter_name": "check_network", "include_status_tools": True},
        )
        self.assertEqual(with_status["returned"], 1)

    def test_make_handler_ignores_client_argument(self) -> None:
        handler = make_parameter_domains_handler("demo", "demo_parameter_domains", demo_tool_definitions)
        result = handler({"parameter_name": "query"}, object())
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["domains"][0]["dynamic_value_hint"], "Free-text search expression; use database-specific syntax described in this parameter description.")


if __name__ == "__main__":
    unittest.main()
