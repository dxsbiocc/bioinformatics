from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "reactome" / "server.py"
SPEC = importlib.util.spec_from_file_location("reactome_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
reactome = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = reactome
SPEC.loader.exec_module(reactome)


class FakeClient:
    def __init__(self) -> None:
        self.config = reactome.ReactomeConfig(contact=None)
        self.requests_per_second = 2
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "data/query/R-HSA-5633007":
            return REACTOME_PATHWAY, {"content-type": "application/json"}
        if endpoint == "data/participants/R-HSA-5633007":
            return REACTOME_PARTICIPANTS, {"content-type": "application/json"}
        if endpoint == "search/query":
            return REACTOME_SEARCH, {"content-type": "application/json"}
        if endpoint == "data/mapping/UniProt/P04637/pathways":
            return REACTOME_MAPPING, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint: {endpoint}")


REACTOME_PATHWAY = {
    "dbId": 5633007,
    "stId": "R-HSA-5633007",
    "stIdVersion": "R-HSA-5633007.6",
    "displayName": "Regulation of TP53 Activity",
    "schemaClass": "Pathway",
    "speciesName": "Homo sapiens",
    "hasDiagram": True,
    "hasEHLD": True,
    "isInDisease": False,
    "releaseDate": "2014-09-09",
    "lastUpdatedDate": "2026-06-12",
    "summation": [
        {
            "text": "<p>Protein stability and transcriptional activity of TP53 are regulated.</p>"
        }
    ],
    "literatureReference": [
        {
            "dbId": 6806099,
            "displayName": "Modes of p53 regulation",
            "title": "Modes of p53 regulation",
            "journal": "Cell",
            "pages": "609-22",
            "pubMedIdentifier": 19450511,
            "volume": 137,
            "year": 2009,
            "url": "http://www.ncbi.nlm.nih.gov/pubmed/19450511",
        }
    ],
    "hasEvent": [
        {
            "dbId": 6804754,
            "stId": "R-HSA-6804754",
            "displayName": "Regulation of TP53 Expression",
            "schemaClass": "Pathway",
        }
    ],
}

REACTOME_PARTICIPANTS = [
    {
        "peDbId": 3221973,
        "displayName": "BANP [nucleoplasm]",
        "schemaClass": "EntityWithAccessionedSequence",
        "refEntities": [
            {
                "dbId": 219883,
                "stId": "uniprot:Q8N9N5",
                "identifier": "Q8N9N5",
                "schemaClass": "ReferenceGeneProduct",
                "displayName": "UniProt:Q8N9N5 BANP",
                "icon": "EntityWithAccessionedSequence",
                "url": "http://purl.uniprot.org/uniprot/Q8N9N5",
            }
        ],
    },
    {
        "peDbId": 12345,
        "displayName": "TP53 Tetramer [nucleoplasm]",
        "schemaClass": "Complex",
        "refEntities": [
            {
                "dbId": 111,
                "stId": "uniprot:P04637",
                "identifier": "P04637",
                "schemaClass": "ReferenceGeneProduct",
                "displayName": "UniProt:P04637 TP53",
                "url": "http://purl.uniprot.org/uniprot/P04637",
            }
        ],
    },
]

REACTOME_SEARCH = {
    "results": [
        {
            "entries": [
                {
                    "dbId": 5633007,
                    "stId": "R-HSA-5633007",
                    "name": "<span class=\"highlighting\">Regulation</span> of TP53 Activity",
                    "type": "Pathway",
                    "exactType": "Pathway",
                    "species": ["Homo sapiens"],
                    "summation": "<p>TP53 pathway summary</p>",
                    "hasDiagram": True,
                    "hasEHLD": True,
                    "isDisease": False,
                    "score": 0.92,
                }
            ]
        }
    ]
}

REACTOME_MAPPING = [
    {
        "dbId": 111448,
        "stId": "R-HSA-111448",
        "displayName": "Activation of NOXA and translocation to mitochondria",
        "schemaClass": "Pathway",
        "speciesName": "Homo sapiens",
        "hasDiagram": True,
        "hasEHLD": True,
    },
    {
        "dbId": 139915,
        "stId": "R-HSA-139915",
        "displayName": "Activation of PUMA and translocation to mitochondria",
        "schemaClass": "Pathway",
        "speciesName": "Homo sapiens",
    },
]


class ReactomeMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = reactome.ReactomeMcpServer(self.client)

    def call_tool(self, name, arguments):
        response = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": name,
                    "arguments": arguments,
                },
            }
        )
        assert response is not None
        return response["result"]["structuredContent"]

    def test_tools_list_exposes_reactome_tools(self) -> None:
        response = self.server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "reactome_lookup",
                "reactome_search",
                "reactome_pathways_for_identifier",
                "reactome_status",
            },
        )

    def test_lookup_returns_frontend_compatible_pathway_record(self) -> None:
        result = self.call_tool("reactome_lookup", {"stable_id": "R-HSA-5633007"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"network", "table", "citation_list", "xref_groups"},
        )
        self.assertEqual(result["schema_version"], "bioinformatics.reactome.result.v1")
        self.assertEqual(result["event"]["stable_id"], "R-HSA-5633007")
        record = result["records"][0]
        self.assertEqual(record["record_type"], "reactome_pathway")
        self.assertEqual(record["stable_id"], "Reactome:R-HSA-5633007")
        self.assertEqual(record["display"]["component"], "pathway")
        self.assertEqual(record["data"]["participants"][0]["reference_identifier"], "Q8N9N5")
        self.assertEqual(record["data"]["references"][0]["pmid"], "19450511")
        self.assertIn("Protein stability", record["display"]["description"])

    def test_search_strips_html_and_returns_pathway_records(self) -> None:
        result = self.call_tool(
            "reactome_search",
            {
                "query": "TP53",
                "species": "Homo sapiens",
                "types": "Pathway",
                "max_results": 1,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"network", "table", "xref_groups"},
        )
        self.assertEqual(result["returned"], 1)
        record = result["records"][0]
        self.assertEqual(record["title"], "Regulation of TP53 Activity")
        self.assertNotIn("<span", record["title"])
        self.assertEqual(self.client.calls[0][0], "search/query")
        self.assertEqual(self.client.calls[0][1]["types"], "Pathway")

    def test_pathways_for_identifier_uses_mapping_api(self) -> None:
        result = self.call_tool(
            "reactome_pathways_for_identifier",
            {
                "resource": "UniProt",
                "identifier": "P04637",
                "species": "9606",
                "max_results": 2,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"pathway"},
            required_preview_kinds={"network", "table", "xref_groups"},
            min_records=2,
        )
        self.assertEqual(result["returned"], 2)
        self.assertEqual(
            self.client.calls[0],
            ("data/mapping/UniProt/P04637/pathways", {"species": "9606"}),
        )
        self.assertEqual(result["records"][0]["data"]["mapping"]["identifier"], "P04637")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("reactome_status", {})
        self.assertEqual(result["server"], "reactome")
        self.assertIn("reactome_lookup", result["available_tools"])
        self.assertIn("pathway", result["frontend_components"])
        self.assertIn("network", result["preview_kinds"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
