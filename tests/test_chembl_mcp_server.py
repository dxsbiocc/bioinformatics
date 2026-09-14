from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "chembl" / "server.py"
SPEC = importlib.util.spec_from_file_location("chembl_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
chembl = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = chembl
SPEC.loader.exec_module(chembl)


class FakeClient:
    def __init__(self) -> None:
        self.config = chembl.ChemblConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "molecule/CHEMBL25.json":
            return CHEMBL25_MOLECULE, {"content-type": "application/json"}
        if endpoint == "molecule/search.json":
            return {
                "molecules": [CHEMBL941_MOLECULE, CHEMBL25_MOLECULE],
                "page_meta": {"total_count": 2},
            }, {"content-type": "application/json"}
        if endpoint == "target/CHEMBL1824.json":
            return CHEMBL1824_TARGET, {"content-type": "application/json"}
        if endpoint == "assay/CHEMBL1217643.json":
            return CHEMBL1217643_ASSAY, {"content-type": "application/json"}
        if endpoint == "document/CHEMBL1212834.json":
            return CHEMBL1212834_DOCUMENT, {"content-type": "application/json"}
        if endpoint == "activity.json":
            return CHEMBL_ACTIVITY_SEARCH, {"content-type": "application/json"}
        if endpoint == "mechanism.json":
            return CHEMBL_MECHANISM_SEARCH, {"content-type": "application/json"}
        if endpoint == "drug_indication.json":
            return CHEMBL_DRUG_INDICATIONS, {"content-type": "application/json"}
        if endpoint == "status.json":
            return CHEMBL_STATUS, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


CHEMBL25_MOLECULE = {
    "molecule_chembl_id": "CHEMBL25",
    "pref_name": "ASPIRIN",
    "molecule_type": "Small molecule",
    "max_phase": 4,
    "first_approval": 1950,
    "therapeutic_flag": 1,
    "molecule_properties": {
        "full_molformula": "C9H8O4",
        "full_mwt": "180.16",
        "alogp": "1.31",
        "psa": "63.60",
        "hba": 3,
        "hbd": 1,
        "rtb": 2,
        "aromatic_rings": 1,
        "heavy_atoms": 13,
        "num_ro5_violations": 0,
        "qed_weighted": "0.55",
    },
    "molecule_structures": {
        "canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O",
        "standard_inchi": "InChI=1S/C9H8O4/c1-6(10)13-8-5-3-2-4-7(8)9(11)12/h2-5H,1H3,(H,11,12)",
        "standard_inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
        "molfile": "aspirin molfile",
    },
    "molecule_synonyms": [
        {"molecule_synonym": "Aspirin", "syn_type": "TRADE_NAME"},
        {"molecule_synonym": "Acetylsalicylic acid", "syn_type": "OTHER"},
    ],
    "cross_references": [
        {"xref_id": "2244", "xref_name": "Aspirin", "xref_src": "PubChem"},
    ],
    "atc_classifications": ["B01AC06"],
}


CHEMBL941_MOLECULE = {
    "molecule_chembl_id": "CHEMBL941",
    "pref_name": "IMATINIB",
    "molecule_type": "Small molecule",
    "max_phase": 4,
    "first_approval": 2001,
    "molecule_properties": {"full_molformula": "C29H31N7O", "full_mwt": "493.62"},
    "molecule_structures": {
        "canonical_smiles": "Cc1ccc(NC(=O)c2ccc(CN3CCN(C)CC3)cc2)cc1Nc1nccc(-c2cccnc2)n1",
        "standard_inchi_key": "KTUFNOKKBVMGRW-UHFFFAOYSA-N",
    },
    "molecule_synonyms": [{"molecule_synonym": "Gleevec", "syn_type": "TRADE_NAME"}],
    "cross_references": [],
}


CHEMBL1824_TARGET = {
    "target_chembl_id": "CHEMBL1824",
    "pref_name": "Receptor tyrosine-protein kinase erbB-2",
    "target_type": "SINGLE PROTEIN",
    "organism": "Homo sapiens",
    "tax_id": 9606,
    "target_components": [
        {
            "accession": "P04626",
            "component_description": "Receptor tyrosine-protein kinase erbB-2",
            "component_type": "PROTEIN",
            "relationship": "SINGLE PROTEIN",
            "target_component_synonyms": [
                {"component_synonym": "ERBB2", "syn_type": "GENE_SYMBOL"}
            ],
            "target_component_xrefs": [
                {"xref_id": "ERBB2", "xref_name": "ERBB2", "xref_src_db": "HGNC Symbol"}
            ],
        }
    ],
}


CHEMBL1217643_ASSAY = {
    "assay_chembl_id": "CHEMBL1217643",
    "description": "Inhibition of human hERG",
    "assay_type": "B",
    "assay_type_description": "Binding",
    "assay_organism": "Homo sapiens",
    "assay_tax_id": 9606,
    "bao_format": "BAO_0000357",
    "bao_label": "single protein format",
    "confidence_score": 9,
    "confidence_description": "Direct single protein target assigned",
    "relationship_type": "D",
    "relationship_description": "Direct protein target assigned",
    "target_chembl_id": "CHEMBL240",
    "document_chembl_id": "CHEMBL1212834",
    "src_id": 1,
    "aidx": "CLD0",
    "assay_parameters": [
        {
            "standard_type": "Time",
            "standard_relation": "=",
            "standard_value": "30",
            "standard_units": "min",
        }
    ],
    "assay_classifications": [
        {
            "assay_class_type": "screening",
            "assay_classification": "ion channel assay",
            "description": "hERG channel assay",
        }
    ],
}


CHEMBL1212834_DOCUMENT = {
    "abstract": "TRPV1 antagonist discovery abstract.",
    "authors": "Hodgetts KJ, Blum CA, Caldwell T.",
    "chembl_release": {"chembl_release": "CHEMBL_9", "creation_date": "2011-01-20"},
    "doc_type": "PUBLICATION",
    "document_chembl_id": "CHEMBL1212834",
    "doi": "10.1016/j.bmcl.2010.06.069",
    "first_page": "4359",
    "issue": "15",
    "journal": "Bioorg Med Chem Lett",
    "journal_full_title": "Bioorganic & medicinal chemistry letters.",
    "last_page": "4363",
    "pubmed_id": 20615696,
    "src_id": 1,
    "title": "Pyrido[2,3-b]pyrazines, discovery of TRPV1 antagonists with reduced potential for the formation of reactive metabolites.",
    "volume": "20",
    "year": 2010,
}


CHEMBL_ACTIVITY_SEARCH = {
    "activities": [
        {
            "activity_id": 123,
            "molecule_chembl_id": "CHEMBL25",
            "molecule_pref_name": "ASPIRIN",
            "target_chembl_id": "CHEMBL1824",
            "target_pref_name": "Receptor tyrosine-protein kinase erbB-2",
            "target_organism": "Homo sapiens",
            "assay_chembl_id": "CHEMBL1111111",
            "assay_type": "B",
            "assay_description": "Inhibition assay",
            "standard_type": "IC50",
            "standard_relation": "=",
            "standard_value": "50",
            "standard_units": "nM",
            "pchembl_value": "7.30",
            "document_chembl_id": "CHEMBL112233",
            "document_journal": "J Med Chem",
            "document_year": 2020,
        }
    ],
    "page_meta": {"total_count": 42},
}


CHEMBL_MECHANISM_SEARCH = {
    "mechanisms": [
        {
            "mec_id": 1,
            "molecule_chembl_id": "CHEMBL25",
            "target_chembl_id": "CHEMBL1824",
            "mechanism_of_action": "Cyclooxygenase inhibitor",
            "action_type": "INHIBITOR",
            "max_phase": 4,
            "direct_interaction": 1,
            "disease_efficacy": 1,
            "molecular_mechanism": 1,
            "mechanism_refs": [
                {
                    "ref_id": "12345",
                    "ref_type": "PubMed",
                    "ref_url": "https://pubmed.ncbi.nlm.nih.gov/12345/",
                }
            ],
        }
    ],
    "page_meta": {"total_count": 7},
}


CHEMBL_DRUG_INDICATIONS = {
    "drug_indications": [
        {
            "drugind_id": 22717,
            "molecule_chembl_id": "CHEMBL25",
            "parent_molecule_chembl_id": "CHEMBL25",
            "efo_id": "HP:0001945",
            "efo_term": "Fever",
            "mesh_id": "D005334",
            "mesh_heading": "Fever",
            "max_phase_for_ind": "4.0",
            "indication_refs": [
                {
                    "ref_id": "N02BA01",
                    "ref_type": "ATC",
                    "ref_url": "https://www.whocc.no/atc_ddd_index/?code=N02BA01",
                },
                {
                    "ref_id": "1118dc27-0a9e-4a48-b86c-1338bf28fecc",
                    "ref_type": "DailyMed",
                    "ref_url": "https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=1118dc27-0a9e-4a48-b86c-1338bf28fecc",
                },
            ],
        }
    ],
    "page_meta": {"total_count": 167},
}


CHEMBL_STATUS = {
    "status": "UP",
    "chembl_db_version": "ChEMBL_37",
    "release_date": "2026-05-01",
    "api_version": "1.0",
}


class ChemblMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = chembl.ChemblMcpServer(self.client)

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

    def test_tools_list_exposes_chembl_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "chembl_parameter_domains",
                "chembl_resolve_context",
                "chembl_molecule_lookup",
                "chembl_molecule_search",
                "chembl_target_lookup",
                "chembl_assay_lookup",
                "chembl_document_lookup",
                "chembl_activity_search",
                "chembl_mechanism_search",
                "chembl_drug_indications",
                "chembl_status",
            },
        )

    def test_molecule_lookup_returns_frontend_compatible_compound_record(self) -> None:
        result = self.call_tool("chembl_molecule_lookup", {"molecule_chembl_id": "CHEMBL25"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"chemical_structure", "table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["canonical_smiles"], "CC(=O)Oc1ccccc1C(=O)O")
        self.assertEqual(record["data"]["standard_inchi_key"], "BSYNRYMUTXBXSQ-UHFFFAOYSA-N")

    def test_molecule_search_returns_multiple_compound_records(self) -> None:
        result = self.call_tool("chembl_molecule_search", {"query": "imatinib", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"compound"},
            required_preview_kinds={"chemical_structure", "table", "xref_groups"},
            min_records=2,
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["records"][0]["data"]["molecule_chembl_id"], "CHEMBL941")

    def test_resolve_context_returns_molecule_candidates_and_calls(self) -> None:
        result = self.call_tool(
            "chembl_resolve_context",
            {"query": "imatinib", "max_results": 8},
        )
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(result["entities"][0]["value"], "CHEMBL941")
        self.assertIn("chembl", result["entities"][0]["url"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("chembl_molecule_lookup", tool_names)
        self.assertIn("chembl_activity_search", tool_names)
        self.assertIn("chembl_drug_indications", tool_names)

    def test_target_lookup_returns_frontend_compatible_protein_record(self) -> None:
        result = self.call_tool("chembl_target_lookup", {"target_chembl_id": "CHEMBL1824"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"protein"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["components"][0]["accession"], "P04626")
        self.assertEqual(record["identifiers"]["uniprot"][0]["id"], "P04626")

    def test_assay_lookup_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool("chembl_assay_lookup", {"assay_chembl_id": "CHEMBL1217643"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["assay_type_description"], "Binding")
        self.assertEqual(record["data"]["target_chembl_id"], "CHEMBL240")
        self.assertEqual(record["data"]["parameters"][0]["value"], "30")
        self.assertEqual(result["assay"]["confidence_score"], "9")

    def test_document_lookup_returns_frontend_compatible_citation_record(self) -> None:
        result = self.call_tool("chembl_document_lookup", {"document_chembl_id": "CHEMBL1212834"})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"citation"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["pubmed_id"], "20615696")
        self.assertEqual(record["identifiers"]["pubmed"]["id"], "20615696")
        self.assertEqual(record["identifiers"]["doi"]["id"], "10.1016/j.bmcl.2010.06.069")
        self.assertEqual(record["display"]["primary_url"], "https://pubmed.ncbi.nlm.nih.gov/20615696/")
        self.assertIn("text", {preview["kind"] for preview in record["display"]["previews"]})
        self.assertEqual(result["document"]["journal"], "Bioorg Med Chem Lett")

    def test_activity_search_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool(
            "chembl_activity_search",
            {"molecule_chembl_id": "CHEMBL25", "max_results": 1},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["total_activities"], 42)
        self.assertEqual(record["data"]["activities"][0]["standard_type"], "IC50")
        xref_groups = record["display"]["previews"][1]["data"]["groups"]
        self.assertIn("Assays", {group["database"] for group in xref_groups})

    def test_mechanism_search_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool(
            "chembl_mechanism_search",
            {"molecule_chembl_id": "CHEMBL25", "max_results": 1},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["total_mechanisms"], 7)
        self.assertEqual(record["data"]["mechanisms"][0]["refs"][0]["id"], "12345")

    def test_drug_indications_return_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool(
            "chembl_drug_indications",
            {"molecule_chembl_id": "CHEMBL25", "max_results": 1},
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["total_indications"], 167)
        self.assertEqual(record["data"]["indications"][0]["term"], "Fever")
        self.assertEqual(record["data"]["indications"][0]["mesh_id"], "D005334")
        self.assertEqual(record["data"]["indications"][0]["refs"][0]["source"], "ATC")
        self.assertEqual(
            self.client.calls[-1],
            ("drug_indication.json", {"molecule_chembl_id": "CHEMBL25", "limit": 1}),
        )

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("chembl_status", {})
        self.assertEqual(result["server"], "chembl")
        self.assertIn("chembl_molecule_lookup", result["available_tools"])
        self.assertIn("chembl_assay_lookup", result["available_tools"])
        self.assertIn("chembl_document_lookup", result["available_tools"])
        self.assertIn("chembl_drug_indications", result["available_tools"])
        self.assertIn("compound", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("chembl_status", {"check_network": True})
        self.assertEqual(result["network_check"]["status"], "UP")
        self.assertEqual(result["network_check"]["chembl_db_version"], "ChEMBL_37")
        self.assertEqual(result["network_check"]["release_date"], "2026-05-01")


if __name__ == "__main__":
    unittest.main()
