from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "uniprot" / "server.py"
SPEC = importlib.util.spec_from_file_location("uniprot_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
uniprot = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = uniprot
SPEC.loader.exec_module(uniprot)


class FakeClient:
    def __init__(self) -> None:
        self.config = uniprot.UniProtConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "uniprotkb/search":
            return {"results": [UNIPROT_ENTRY]}
        if endpoint == "uniprotkb/P04637":
            return UNIPROT_ENTRY
        raise AssertionError(f"unexpected JSON endpoint: {endpoint}")

    def request_json_with_headers(self, endpoint, params):
        payload = self.request_json(endpoint, params)
        return payload, {
            "x-total-results": "2",
            "x-uniprot-release": "2026_03",
            "x-uniprot-release-date": "02-September-2026",
            "link": (
                "<https://rest.uniprot.org/uniprotkb/search?"
                "query=gene%3ATP53&cursor=abc123&size=1>; rel=\"next\""
            ),
        }

    def request_text(self, endpoint, params, *, accept="text/plain"):
        text, _headers = self.request_text_with_headers(
            endpoint,
            params,
            accept=accept,
        )
        return text

    def request_text_with_headers(self, endpoint, params, *, accept="text/plain"):
        self.calls.append((endpoint, params, accept))
        if endpoint == "uniprotkb/P04637.fasta":
            return FASTA, {
                "x-uniprot-release": "2026_03",
                "x-uniprot-release-date": "02-September-2026",
            }
        raise AssertionError(f"unexpected text endpoint: {endpoint}")


UNIPROT_ENTRY = {
    "primaryAccession": "P04637",
    "uniProtkbId": "P53_HUMAN",
    "entryType": "UniProtKB reviewed (Swiss-Prot)",
    "proteinDescription": {
        "recommendedName": {
            "fullName": {
                "value": "Cellular tumor antigen p53",
            }
        }
    },
    "genes": [
        {
            "geneName": {"value": "TP53"},
            "synonyms": [{"value": "P53"}],
        }
    ],
    "organism": {
        "scientificName": "Homo sapiens",
        "commonName": "Human",
        "taxonId": 9606,
    },
    "sequence": {
        "length": 393,
        "molWeight": 43653,
    },
    "comments": [
        {
            "commentType": "FUNCTION",
            "texts": [{"value": "Acts as a tumor suppressor."}],
        },
        {
            "commentType": "SUBCELLULAR LOCATION",
            "subcellularLocations": [
                {"location": {"value": "Nucleus"}},
            ],
        }
    ],
    "features": [
        {
            "type": "Chain",
            "description": "Cellular tumor antigen p53",
            "location": {
                "start": {"value": 1, "modifier": "EXACT"},
                "end": {"value": 393, "modifier": "EXACT"},
            },
            "featureId": "PRO_0000185703",
        },
        {
            "type": "DNA binding",
            "description": "",
            "location": {
                "start": {"value": 102, "modifier": "EXACT"},
                "end": {"value": 292, "modifier": "EXACT"},
            },
        },
    ],
    "keywords": [
        {"id": "KW-0002", "category": "Technical term", "name": "3D-structure"},
        {"id": "KW-0010", "category": "Molecular function", "name": "Activator"},
    ],
    "uniProtKBCrossReferences": [
        {"database": "GeneID", "id": "7157"},
        {"database": "AlphaFoldDB", "id": "P04637"},
        {"database": "PDB", "id": "1TUP"},
        {"database": "Reactome", "id": "R-HSA-6798695"},
        {"database": "PubMed", "id": "20421139"},
        {"database": "STRING", "id": "9606.ENSP00000269305"},
    ],
    "references": [
        {
            "citation": {
                "title": "A p53 reference",
                "authors": ["Ada Lovelace"],
                "journal": "Test Journal",
                "publicationDate": "2026",
                "citationCrossReferences": [
                    {"database": "PubMed", "id": "20421139"},
                ],
            }
        }
    ],
}

FASTA = """>sp|P04637|P53_HUMAN Cellular tumor antigen p53 OS=Homo sapiens
MEEPQSDPSVEPPLSQETFSDLWKLLPEN
"""


class UniProtMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = uniprot.UniProtMcpServer(self.client)

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

    def test_tools_list_exposes_uniprot_tools(self) -> None:
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
                "uniprot_search",
                "uniprot_lookup",
                "uniprot_fasta",
                "uniprot_status",
            },
        )

    def test_search_returns_frontend_compatible_protein_records(self) -> None:
        result = self.call_tool(
            "uniprot_search",
            {
                "query": "gene:TP53",
                "organism": "9606",
                "reviewed": True,
                "max_results": 1,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein"},
            required_preview_kinds={
                "sequence",
                "feature_track",
                "structure_3d",
                "network",
                "citation_list",
                "xref_groups",
            },
        )
        self.assertEqual(result["schema_version"], "bioinformatics.uniprot.result.v1")
        self.assertEqual(result["normalized_query"], "(gene:TP53) AND (organism_id:9606) AND (reviewed:true)")
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["pagination"]["total"], 2)
        self.assertEqual(result["pagination"]["next_cursor"], "abc123")
        self.assertEqual(result["provenance"]["release"], "2026_03")
        self.assertEqual(result["entries"][0]["feature_summary"]["total"], 2)
        self.assertEqual(result["entries"][0]["feature_summary"]["returned"], 0)
        record = result["records"][0]
        self.assertEqual(record["stable_id"], "UniProtKB:P04637")
        self.assertEqual(record["display"]["component"], "protein")
        self.assertEqual(record["identifiers"]["taxonomy"]["label"], "TaxID:9606")
        self.assertEqual(record["related"]["gene_ids"], ["7157"])
        self.assertEqual(record["related"]["alphafold_ids"], ["P04637"])
        self.assertEqual(record["related"]["string_ids"], ["9606.ENSP00000269305"])
        self.assertEqual(record["related"]["reactome_ids"], ["R-HSA-6798695"])
        self.assertEqual(record["related"]["pubmed_ids"], ["20421139"])
        section_keys = {section["key"] for section in record["display"]["sections"]}
        self.assertIn("cross_references", section_keys)
        preview_kinds = {preview["kind"] for preview in record["display"]["previews"]}
        self.assertIn("sequence", preview_kinds)
        self.assertIn("feature_track", preview_kinds)
        self.assertIn("structure_3d", preview_kinds)
        self.assertIn("network", preview_kinds)
        self.assertIn("citation_list", preview_kinds)
        self.assertIn("xref_groups", preview_kinds)
        network_preview = next(
            preview
            for preview in record["display"]["previews"]
            if preview["kind"] == "network"
        )
        self.assertEqual(network_preview["provider"], "STRING")
        self.assertEqual(network_preview["url"], "https://string-db.org/network/9606.ENSP00000269305")
        self.assertIn("https://www.uniprot.org/uniprotkb/P04637/entry", record["url"])

    def test_lookup_fetches_accession_json(self) -> None:
        result = self.call_tool(
            "uniprot_lookup",
            {"accession": "P04637", "feature_types": ["DNA binding"]},
        )
        self.assertEqual(result["returned"], 1)
        self.assertEqual(self.client.calls[-1], ("uniprotkb/P04637", {"format": "json"}))
        self.assertEqual(result["records"][0]["title"], "Cellular tumor antigen p53")
        record = result["records"][0]
        self.assertEqual(record["data"]["feature_summary"]["matching"], 1)
        self.assertEqual(record["data"]["features"][0]["begin"], 102)
        self.assertEqual(record["data"]["features"][0]["end"], 292)
        self.assertEqual(record["data"]["feature_tracks"][0]["key"], "region")
        self.assertEqual(record["data"]["keywords"][0]["name"], "3D-structure")
        self.assertEqual(record["data"]["literature_references"][0]["cross_references"][0]["url"], "https://pubmed.ncbi.nlm.nih.gov/20421139/")
        structure_previews = [
            preview
            for preview in record["display"]["previews"]
            if preview["kind"] == "structure_3d"
        ]
        self.assertEqual(structure_previews[0]["provider"], "AlphaFold DB")
        self.assertEqual(
            structure_previews[0]["data"]["api_url"],
            "https://alphafold.ebi.ac.uk/api/prediction/P04637",
        )

    def test_fasta_returns_sequence_record_and_raw_fasta(self) -> None:
        result = self.call_tool("uniprot_fasta", {"accession": "P04637"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein"},
            required_preview_kinds={"sequence"},
        )
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["fasta"], FASTA)
        record = result["records"][0]
        self.assertEqual(record["record_type"], "uniprotkb_fasta")
        self.assertEqual(record["display"]["component"], "protein")
        self.assertEqual(record["data"]["length"], 29)
        self.assertEqual(record["links"][1]["kind"], "download")
        self.assertEqual(record["display"]["previews"][0]["kind"], "sequence")
        self.assertEqual(record["display"]["previews"][0]["data"]["sequence"], "MEEPQSDPSVEPPLSQETFSDLWKLLPEN")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("uniprot_status", {})
        self.assertEqual(result["server"], "uniprot")
        self.assertFalse(result["contact_configured"])
        self.assertIn("uniprot_lookup", result["available_tools"])
        self.assertIn("structure_3d", result["preview_kinds"])
        self.assertIn("features", result["detail_sections"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
