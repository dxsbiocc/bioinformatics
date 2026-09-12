from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "pubchem" / "server.py"
SPEC = importlib.util.spec_from_file_location("pubchem_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
pubchem = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = pubchem
SPEC.loader.exec_module(pubchem)

from mcp.pubchem.records import pubchem_compound_record


class FakeClient:
    def __init__(self) -> None:
        self.config = pubchem.PubChemConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "compound/name/aspirin/cids/JSON":
            return PUBCHEM_CIDS, {"content-type": "application/json"}
        if endpoint.startswith("compound/cid/2244/property/") or endpoint.startswith("compound/name/aspirin/property/"):
            return PUBCHEM_COMPOUND_PROPERTIES, {"content-type": "application/json"}
        if endpoint == "compound/cid/2244/description/JSON":
            return PUBCHEM_DESCRIPTION, {"content-type": "application/json"}
        if endpoint == "compound/cid/2244/synonyms/JSON":
            return PUBCHEM_SYNONYMS, {"content-type": "application/json"}
        if endpoint == "assay/aid/1706/summary/JSON":
            return PUBCHEM_ASSAY, {"content-type": "application/json"}
        if endpoint == "substance/sid/4594/JSON":
            return PUBCHEM_SUBSTANCE, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


PUBCHEM_COMPOUND_PROPERTIES = {
    "PropertyTable": {
        "Properties": [
            {
                "CID": 2244,
                "Title": "Aspirin",
                "MolecularFormula": "C9H8O4",
                "MolecularWeight": "180.16",
                "CanonicalSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "IsomericSMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "InChI": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
                "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
                "IUPACName": "2-acetyloxybenzoic acid",
                "XLogP": 1.2,
                "TPSA": 63.6,
                "HBondDonorCount": 1,
                "HBondAcceptorCount": 4,
                "RotatableBondCount": 3,
                "ExactMass": "180.04225873",
                "MonoisotopicMass": "180.04225873",
                "Charge": 0,
            }
        ]
    }
}


PUBCHEM_DESCRIPTION = {
    "InformationList": {
        "Information": [
            {"CID": 2244, "Title": "Aspirin"},
            {
                "CID": 2244,
                "Description": "Acetylsalicylic acid is a non-steroidal anti-inflammatory drug.",
                "DescriptionSourceName": "ChEBI",
                "DescriptionURL": "https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:15365",
            },
        ]
    }
}


PUBCHEM_SYNONYMS = {
    "InformationList": {
        "Information": [
            {
                "CID": 2244,
                "Synonym": ["aspirin", "ACETYLSALICYLIC ACID", "2-acetyloxybenzoic acid"],
            }
        ]
    }
}


PUBCHEM_CIDS = {"IdentifierList": {"CID": [2244]}}


PUBCHEM_ASSAY = {
    "AssaySummaries": {
        "AssaySummary": [
            {
                "AID": 1706,
                "Name": "qHTS assay for inhibitors",
                "SourceName": "The Scripps Research Institute Molecular Screening Center",
                "Description": "PubChem BioAssay summary for an inhibitor screen.",
                "AssayType": "confirmatory",
                "ActivityOutcomeMethod": "screening",
                "TargetName": "Example protein target",
                "TargetGeneID": 7157,
                "TargetTaxID": 9606,
                "ActiveCount": 12,
                "TestedCount": 1000,
            }
        ]
    }
}


PUBCHEM_SUBSTANCE = {
    "PC_Substances": [
        {
            "sid": {"id": 4594, "version": 10},
            "source": {"db": {"name": "KEGG", "source_id": "C01405"}},
            "synonyms": ["2-Acetoxybenzenecarboxylic acid", "50-78-2", "Aspirin"],
            "comment": ["Is a reactant of enzyme EC: 3.1.1.55"],
            "xref": [
                {"regid": "C01405"},
                {"rn": "50-78-2"},
                {"dburl": "http://www.genome.jp/kegg/"},
            ],
            "compound": [{"id": {"id": {"cid": 2244}}}],
        }
    ]
}


class PubChemMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = pubchem.PubChemMcpServer(self.client)

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

    def test_tools_list_exposes_pubchem_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "pubchem_compound_lookup",
                "pubchem_compound_search",
                "pubchem_assay_summary",
                "pubchem_substance_lookup",
                "pubchem_status",
            },
        )

    def test_compound_lookup_returns_frontend_compatible_compound_record(self) -> None:
        result = self.call_tool("pubchem_compound_lookup", {"cid": 2244})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"chemical_structure", "table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["cid"], "2244")
        self.assertEqual(record["data"]["inchi_key"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
        self.assertEqual(record["data"]["synonyms"][0], "aspirin")

    def test_compound_record_uses_current_pubchem_smiles_fields(self) -> None:
        record = pubchem_compound_record(
            {
                "CID": 2244,
                "Title": "Aspirin",
                "MolecularFormula": "C9H8O4",
                "MolecularWeight": "180.16",
                "SMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "ConnectivitySMILES": "CC(=O)OC1=CC=CC=C1C(=O)O",
                "InChIKey": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
            }
        )
        self.assertEqual(record["data"]["canonical_smiles"], "CC(=O)OC1=CC=CC=C1C(=O)O")
        self.assertIn("SMILES", [row["property"] for row in record["display"]["sections"][0]["rows"]])

    def test_compound_search_resolves_cids_and_hydrates_records(self) -> None:
        result = self.call_tool("pubchem_compound_search", {"query": "aspirin", "max_results": 1})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"chemical_structure", "table", "xref_groups"},
        )
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["records"][0]["data"]["cid"], "2244")

    def test_assay_summary_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool("pubchem_assay_summary", {"aid": 1706})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["aid"], "1706")
        self.assertEqual(record["data"]["target_gene_id"], "7157")

    def test_substance_lookup_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool("pubchem_substance_lookup", {"sid": 4594})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["sid"], "4594")
        self.assertEqual(record["data"]["compound_cids"], ["2244"])

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("pubchem_status", {})
        self.assertEqual(result["server"], "pubchem")
        self.assertIn("pubchem_compound_lookup", result["available_tools"])
        self.assertIn("compound", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("pubchem_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_cid"], 2244)
        self.assertEqual(result["network_check"]["example_title"], "Aspirin")


if __name__ == "__main__":
    unittest.main()
