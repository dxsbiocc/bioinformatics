from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "rcsb" / "server.py"
SPEC = importlib.util.spec_from_file_location("rcsb_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
rcsb = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rcsb
SPEC.loader.exec_module(rcsb)


class FakeClient:
    def __init__(self) -> None:
        self.config = rcsb.RcsbConfig(contact=None)
        self.requests_per_second = 2
        self.calls = []

    def request_data_json_with_headers(self, endpoint, params):
        self.calls.append(("data", endpoint, params))
        if endpoint == "core/entry/4HHB":
            return RCSB_ENTRY, {"content-type": "application/json"}
        if endpoint == "core/entry/2PGH":
            return {**RCSB_ENTRY, "rcsb_id": "2PGH"}, {"content-type": "application/json"}
        if endpoint == "core/polymer_entity/4HHB/1":
            return POLYMER_ENTITY_1, {"content-type": "application/json"}
        if endpoint == "core/polymer_entity/4HHB/2":
            return POLYMER_ENTITY_2, {"content-type": "application/json"}
        if endpoint == "core/nonpolymer_entity/4HHB/3":
            return NONPOLYMER_ENTITY_3, {"content-type": "application/json"}
        raise AssertionError(f"unexpected data endpoint: {endpoint}")

    def request_search_json_with_headers(self, endpoint, payload):
        self.calls.append(("search", endpoint, payload))
        if endpoint == "query":
            return RCSB_SEARCH, {"content-type": "application/json"}
        raise AssertionError(f"unexpected search endpoint: {endpoint}")

    def request_text_with_headers(self, url, *, label, accept="text/plain"):
        self.calls.append(("text", url, label, accept))
        if url.endswith("/fasta/entry/4HHB/download"):
            return FASTA, {"content-type": "text/plain"}
        raise AssertionError(f"unexpected text URL: {url}")


RCSB_ENTRY = {
    "rcsb_id": "4HHB",
    "struct": {
        "title": "THE CRYSTAL STRUCTURE OF HUMAN DEOXYHAEMOGLOBIN AT 1.74 ANGSTROMS RESOLUTION"
    },
    "exptl": [{"method": "X-RAY DIFFRACTION"}],
    "rcsb_entry_info": {
        "experimental_method": "X-ray",
        "molecular_weight": 64.74,
        "polymer_composition": "heteromeric protein",
        "selected_polymer_entity_types": "Protein (only)",
        "resolution_combined": [1.74],
        "nonpolymer_bound_components": ["HEM"],
    },
    "rcsb_accession_info": {
        "deposit_date": "1984-03-07T00:00:00.000+00:00",
        "initial_release_date": "1984-07-17T00:00:00.000+00:00",
        "revision_date": "2026-08-12T00:00:00.000+00:00",
        "status_code": "REL",
    },
    "rcsb_entry_container_identifiers": {
        "assembly_ids": ["1"],
        "entry_id": "4HHB",
        "non_polymer_entity_ids": ["3"],
        "polymer_entity_ids": ["1", "2"],
        "pubmed_id": 6726807,
        "rcsb_id": "4HHB",
    },
    "citation": [
        {
            "id": "primary",
            "pdbx_database_id_DOI": "10.1016/0022-2836(84)90472-8",
            "pdbx_database_id_PubMed": 6726807,
            "rcsb_authors": ["Fermi, G.", "Perutz, M.F."],
            "rcsb_is_primary": "Y",
            "rcsb_journal_abbrev": "J Mol Biol",
            "title": "The crystal structure of human deoxyhaemoglobin at 1.74 A resolution",
            "year": 1984,
        }
    ],
}

POLYMER_ENTITY_1 = {
    "rcsb_id": "4HHB_1",
    "entity_poly": {
        "pdbx_seq_one_letter_code_can": "VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTK",
        "rcsb_entity_polymer_type": "Protein",
        "rcsb_sample_sequence_length": 141,
        "type": "polypeptide(L)",
    },
    "rcsb_polymer_entity": {
        "formula_weight": 15.15,
        "pdbx_description": "Hemoglobin subunit alpha",
    },
    "rcsb_entity_source_organism": [
        {
            "scientific_name": "Homo sapiens",
            "ncbi_taxonomy_id": 9606,
            "rcsb_gene_name": [{"value": "HBA1"}, {"value": "HBA2"}],
        }
    ],
    "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["A", "C"],
        "entity_id": "1",
        "entry_id": "4HHB",
        "uniprot_ids": ["P69905"],
    },
}

POLYMER_ENTITY_2 = {
    "rcsb_id": "4HHB_2",
    "entity_poly": {
        "pdbx_seq_one_letter_code_can": "VHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQR",
        "rcsb_entity_polymer_type": "Protein",
        "rcsb_sample_sequence_length": 146,
    },
    "rcsb_polymer_entity": {
        "formula_weight": 15.89,
        "pdbx_description": "Hemoglobin subunit beta",
    },
    "rcsb_entity_source_organism": [
        {
            "scientific_name": "Homo sapiens",
            "ncbi_taxonomy_id": 9606,
            "rcsb_gene_name": [{"value": "HBB"}],
        }
    ],
    "rcsb_polymer_entity_container_identifiers": {
        "auth_asym_ids": ["B", "D"],
        "entity_id": "2",
        "entry_id": "4HHB",
        "uniprot_ids": ["P68871"],
    },
}

NONPOLYMER_ENTITY_3 = {
    "rcsb_id": "4HHB_3",
    "pdbx_entity_nonpoly": {
        "comp_id": "HEM",
        "entity_id": "3",
        "name": "PROTOPORPHYRIN IX CONTAINING FE",
    },
    "rcsb_nonpolymer_entity_container_identifiers": {
        "auth_asym_ids": ["A", "B", "C", "D"],
        "entity_id": "3",
        "entry_id": "4HHB",
        "nonpolymer_comp_id": "HEM",
    },
}

RCSB_SEARCH = {
    "query_id": "query-1",
    "result_type": "entry",
    "total_count": 9171,
    "result_set": [
        {"identifier": "4HHB", "score": 1.0},
        {"identifier": "2PGH", "score": 0.9},
    ],
}

FASTA = """>4HHB_1|Chains A,C|Hemoglobin subunit alpha
VLSPADKTNVKAAWGKVGAHAGEYGAEALERMFLSFPTTK
>4HHB_2|Chains B,D|Hemoglobin subunit beta
VHLTPEEKSAVTALWGKVNVDEVGGEALGRLLVVYPWTQR
"""


class RcsbMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = rcsb.RcsbMcpServer(self.client)

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

    def test_tools_list_exposes_rcsb_tools(self) -> None:
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
        self.assertEqual(names, {"rcsb_parameter_domains", "rcsb_resolve_context", "rcsb_lookup", "rcsb_search", "rcsb_fasta", "rcsb_status"})

    def test_lookup_returns_frontend_compatible_structure_record(self) -> None:
        result = self.call_tool("rcsb_lookup", {"pdb_id": "4hhb"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein_structure"},
            required_preview_kinds={"structure_3d", "download_manifest", "table", "citation_list"},
        )
        self.assertEqual(result["schema_version"], "bioinformatics.rcsb.result.v1")
        self.assertEqual(result["entry"]["pdb_id"], "4HHB")
        record = result["records"][0]
        self.assertEqual(record["record_type"], "rcsb_pdb_entry")
        self.assertEqual(record["stable_id"], "PDB:4HHB")
        self.assertEqual(record["display"]["component"], "protein_structure")
        self.assertEqual(record["identifiers"]["uniprot"][0]["label"], "UniProtKB:P68871")
        self.assertEqual(record["identifiers"]["taxonomy"][0]["label"], "TaxID:9606")
        self.assertEqual(record["related"]["downloads"][1]["label"], "mmCIF")
        self.assertEqual(record["data"]["ligand_ids"], ["HEM"])
        self.assertEqual(record["data"]["polymer_entities"][0]["chains"], ["A", "C"])
        self.assertEqual(record["data"]["polymer_entities"][1]["uniprot_ids"], ["P68871"])

    def test_search_uses_current_paginate_request_and_hydrates_records(self) -> None:
        result = self.call_tool(
            "rcsb_search",
            {
                "query": "hemoglobin",
                "max_results": 2,
            },
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein_structure"},
            required_preview_kinds={"structure_3d", "download_manifest", "citation_list"},
            min_records=2,
        )
        self.assertEqual(result["returned"], 2)
        search_call = self.client.calls[0]
        self.assertEqual(search_call[0], "search")
        self.assertIn("paginate", search_call[2]["request_options"])
        self.assertNotIn("pager", search_call[2]["request_options"])
        self.assertEqual(result["records"][0]["data"]["search_score"], 1.0)

    def test_resolve_context_returns_search_hits_and_recommended_calls(self) -> None:
        result = self.call_tool("rcsb_resolve_context", {"context_type": "entry", "query": "hemoglobin", "max_results": 2})
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual([entry["value"] for entry in result["entries"]], ["4HHB", "2PGH"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("rcsb_lookup", tool_names)
        self.assertIn("rcsb_fasta", tool_names)
        self.assertTrue(result["entries"][0]["url"].endswith("/structure/4HHB"))

    def test_fasta_returns_sequence_record(self) -> None:
        result = self.call_tool("rcsb_fasta", {"pdb_id": "4HHB"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein"},
            required_preview_kinds={"sequence"},
        )
        self.assertEqual(result["returned"], 1)
        self.assertEqual(result["records"][0]["record_type"], "rcsb_pdb_fasta")
        self.assertEqual(result["records"][0]["display"]["previews"][0]["data"]["sequence_count"], 2)

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("rcsb_status", {})
        self.assertEqual(result["server"], "rcsb")
        self.assertIn("rcsb_lookup", result["available_tools"])
        self.assertIn("protein_structure", result["frontend_components"])
        self.assertIn("structure_3d", result["preview_kinds"])
        self.assertNotIn("network_check", result)


if __name__ == "__main__":
    unittest.main()
