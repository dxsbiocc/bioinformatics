from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "chebi" / "server.py"
SPEC = importlib.util.spec_from_file_location("chebi_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
chebi = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = chebi
SPEC.loader.exec_module(chebi)


class FakeClient:
    def __init__(self) -> None:
        self.config = chebi.ChebiConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "chebi/backend/api/public/es_search/":
            return SEARCH, {"content-type": "application/json"}, "https://www.ebi.ac.uk/chebi/backend/api/public/es_search/?query=caffeine&size=2"
        if endpoint == "chebi/backend/api/public/compound/CHEBI:27732/":
            return CAFFEINE, {"content-type": "application/json"}, "https://www.ebi.ac.uk/chebi/backend/api/public/compound/CHEBI:27732/"
        if endpoint == "chebi/backend/api/public/ontology/children/CHEBI:27732/":
            return CHILDREN, {"content-type": "application/json"}, "https://www.ebi.ac.uk/chebi/backend/api/public/ontology/children/CHEBI:27732/"
        if endpoint == "chebi/backend/api/public/ontology/parents/CHEBI:27732/":
            return PARENTS, {"content-type": "application/json"}, "https://www.ebi.ac.uk/chebi/backend/api/public/ontology/parents/CHEBI:27732/"
        raise AssertionError(f"unexpected endpoint {endpoint}")


SEARCH = {
    "results": [
        {
            "_id": "27732",
            "_score": 10.2,
            "_source": {
                "chebi_accession": "CHEBI:27732",
                "name": "caffeine",
                "ascii_name": "caffeine",
                "stars": 3,
                "definition": "A trimethylxanthine in which the three methyl groups are located at positions 1, 3 and 7.",
                "mass": 194.194,
                "formula": "C8H10N4O2",
                "charge": 0,
                "monoisotopicmass": 194.08038,
                "smiles": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
                "inchi": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
                "inchikey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
                "structures": [12345],
            },
        },
        {
            "_id": "15365",
            "_source": {
                "chebi_accession": "CHEBI:15365",
                "name": "hypoxanthine",
                "definition": "A purine derivative.",
                "formula": "C5H4N4O",
                "mass": 136.112,
                "smiles": "O=c1[nH]cnc2[nH]cnc12",
            },
        },
    ],
    "total": 2,
    "number_pages": 1,
}


CAFFEINE = {
    "id": 27732,
    "chebi_accession": "CHEBI:27732",
    "name": "caffeine",
    "stars": 3,
    "definition": "A trimethylxanthine in which the three methyl groups are located at positions 1, 3 and 7.",
    "ascii_name": "caffeine",
    "names": {
        "SYNONYM": [{"name": "1,3,7-trimethylxanthine", "source": "ChEBI"}],
        "IUPAC NAME": [{"name": "1,3,7-trimethylpurine-2,6-dione", "source": "ChEBI"}],
        "BRAND NAME": [{"name": "Vivarin", "source": "ChEBI"}],
    },
    "chemical_data": {"formula": "C8H10N4O2", "charge": 0, "mass": "194.194", "monoisotopic_mass": "194.08038"},
    "smiles": "Cn1cnc2c1c(=O)n(C)c(=O)n2C",
    "inchi": "InChI=1S/C8H10N4O2/c1-10-4-9-6-5(10)7(13)12(3)8(14)11(6)2/h4H,1-3H3",
    "inchikey": "RYYVLZVUVIJVGH-UHFFFAOYSA-N",
    "secondary_ids": ["CHEBI:41472"],
    "default_structure": 12345,
    "compound_origins": [{"species_text": "Theobroma cacao", "source_type": "biological", "component_text": "seed"}],
    "ontology_relations": {"outgoing_relations": [{"relation_type": "has role", "final_id": 35705, "final_name": "immunosuppressive agent"}]},
    "database_accessions": {
        "CAS": [{"accession_number": "58-08-2", "source_name": "CAS Registry Number", "url": "https://commonchemistry.cas.org/detail?cas_rn=58-08-2"}],
        "MANUAL_X_REF": [{"accession_number": "2519", "source_name": "PubChem", "url": "https://pubchem.ncbi.nlm.nih.gov/compound/2519"}],
        "CITATION": [{"accession_number": "PMID:123456", "source_name": "PubMed", "url": "https://pubmed.ncbi.nlm.nih.gov/123456/"}],
    },
    "is_released": True,
}


CHILDREN = {
    "id": 27732,
    "chebi_accession": "CHEBI:27732",
    "ontology_relations": {
        "incoming_relations": [
            {"init_id": 53115, "init_name": "8-(3-chlorostyryl)caffeine", "relation_type": "has functional parent", "final_id": 27732, "final_name": "caffeine"}
        ]
    },
}


PARENTS = {
    "id": 27732,
    "chebi_accession": "CHEBI:27732",
    "ontology_relations": {
        "outgoing_relations": [
            {"init_id": 27732, "init_name": "caffeine", "relation_type": "has role", "final_id": 35705, "final_name": "immunosuppressive agent"}
        ]
    },
}


class ChebiMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = chebi.ChebiMcpServer(self.client)

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

    def test_tools_list_exposes_chebi_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "chebi_parameter_domains",
                "chebi_resolve_context",
                "chebi_compound_search",
                "chebi_compound_lookup",
                "chebi_ontology_children",
                "chebi_ontology_parents",
                "chebi_status",
            },
        )

    def test_compound_lookup_returns_frontend_compatible_compound_record(self) -> None:
        result = self.call_tool("chebi_compound_lookup", {"chebi_id": "CHEBI:27732"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"table", "chemical_structure", "xref_groups", "citation_list", "text"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["id"], "CHEBI:27732")
        self.assertEqual(record["data"]["formula"], "C8H10N4O2")
        self.assertEqual(record["display"]["primary_url"], "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:27732")

    def test_compound_search_returns_bounded_compound_records(self) -> None:
        result = self.call_tool("chebi_compound_search", {"query": "caffeine", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"table", "chemical_structure", "text"},
            min_records=2,
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(self.client.calls[-1][1]["size"], 2)

    def test_resolve_context_returns_compound_candidate_and_calls(self) -> None:
        result = self.call_tool("chebi_resolve_context", {"query": "caffeine", "max_results": 2})
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["entities"][0]["value"], "CHEBI:27732")
        self.assertIn("CHEBI:27732", result["entities"][0]["url"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("chebi_compound_lookup", tool_names)
        self.assertIn("chebi_ontology_children", tool_names)

    def test_children_returns_ontology_relation_network_preview(self) -> None:
        result = self.call_tool("chebi_ontology_children", {"chebi_id": "27732", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "network"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["id"], "CHEBI:53115")
        self.assertEqual(record["data"]["edge"]["target"], "CHEBI:27732")

    def test_parents_returns_ontology_relation_network_preview(self) -> None:
        result = self.call_tool("chebi_ontology_parents", {"chebi_id": "CHEBI:27732", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"ontology_term"},
            required_preview_kinds={"table", "network"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["id"], "CHEBI:35705")
        self.assertEqual(record["data"]["edge"]["source"], "CHEBI:27732")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("chebi_status", {})
        self.assertEqual(result["server"], "chebi")
        self.assertIn("chebi_compound_lookup", result["available_tools"])
        self.assertIn("compound", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("chebi_status", {"check_network": True})
        self.assertEqual(result["network_check"]["returned"], 1)
        self.assertEqual(result["network_check"]["content_type"], "application/json")

    def test_client_parses_json_and_reports_url(self) -> None:
        client = chebi.ChebiClient(opener=lambda request, timeout: (json.dumps({"ok": True}), {"content-type": "application/json"}))
        payload, headers, url = client.request_json_with_headers("chebi/backend/api/public/es_search/", {"query": "caffeine", "size": 1})
        self.assertEqual(payload, {"ok": True})
        self.assertEqual(headers["content-type"], "application/json")
        self.assertIn("query=caffeine", url)


if __name__ == "__main__":
    unittest.main()
