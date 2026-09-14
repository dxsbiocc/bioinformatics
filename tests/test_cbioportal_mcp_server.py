from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "cbioportal" / "server.py"
SPEC = importlib.util.spec_from_file_location("cbioportal_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
cbioportal = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cbioportal
SPEC.loader.exec_module(cbioportal)


STUDY_ID = "brca_tcga"
PROFILE_ID = "brca_tcga_mutations"
EXPRESSION_PROFILE_ID = "brca_tcga_rna_seq_v2_mrna_median_Zscores"
MISSING_EXPRESSION_PROFILE_ID = "brca_tcga_missing_expression"
DATALESS_EXPRESSION_PROFILE_ID = "brca_tcga_empty_expression"
CNA_PROFILE_ID = "brca_tcga_gistic"
SAMPLE_LIST_ID = "brca_tcga_all"
MISMATCHED_SAMPLE_LIST_ID = "luad_tcga_all"


class FakeClient:
    def __init__(self) -> None:
        self.config = cbioportal.CbioPortalConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params=None, *, method="GET", json_body=None):
        params = params or {}
        self.calls.append((endpoint, params, method, json_body))
        if endpoint == "studies":
            return [STUDY, {**STUDY, "studyId": "luad_tcga", "name": "Lung Adenocarcinoma"}], {"content-type": "application/json"}
        if endpoint == f"studies/{STUDY_ID}":
            return STUDY, {"content-type": "application/json"}
        if endpoint == f"studies/{STUDY_ID}/molecular-profiles":
            return PROFILES, {"content-type": "application/json"}
        if endpoint == f"studies/{STUDY_ID}/sample-lists":
            return SAMPLE_LISTS, {"content-type": "application/json"}
        if endpoint.startswith("molecular-profiles/") and endpoint.count("/") == 1:
            profile_id = endpoint.split("/", 1)[1]
            for profile in PROFILES:
                if profile["molecularProfileId"] == profile_id:
                    return profile, {"content-type": "application/json"}
            raise cbioportal.CbioPortalError(
                f"cBioPortal {endpoint} returned HTTP 404: {{\"message\":\"Molecular profile not found\"}}",
                status_code=404,
                endpoint=endpoint,
                response_body='{"message":"Molecular profile not found"}',
            )
        if endpoint.startswith("sample-lists/") and endpoint.count("/") == 1:
            sample_list_id = endpoint.split("/", 1)[1]
            for sample_list in SAMPLE_LISTS:
                if sample_list["sampleListId"] == sample_list_id:
                    return sample_list, {"content-type": "application/json"}
            raise cbioportal.CbioPortalError(
                f"cBioPortal {endpoint} returned HTTP 404: {{\"message\":\"Sample list not found\"}}",
                status_code=404,
                endpoint=endpoint,
                response_body='{"message":"Sample list not found"}',
            )
        if endpoint == "genes/fetch":
            requested = set(json_body or [])
            return [gene for gene in GENES if gene["hugoGeneSymbol"] in requested], {"content-type": "application/json"}
        if endpoint == f"molecular-profiles/{PROFILE_ID}/mutations/fetch":
            return MUTATIONS, {"content-type": "application/json"}
        if endpoint == f"molecular-profiles/{EXPRESSION_PROFILE_ID}/molecular-data/fetch":
            if json_body and json_body.get("sampleListId") == MISMATCHED_SAMPLE_LIST_ID:
                return [], {"content-type": "application/json"}
            return MOLECULAR_DATA, {"content-type": "application/json"}
        if endpoint == f"molecular-profiles/{DATALESS_EXPRESSION_PROFILE_ID}/molecular-data/fetch":
            raise cbioportal.CbioPortalError(
                "cBioPortal molecular-data/fetch returned HTTP 404: {\"message\":\"No molecular data found\"}",
                status_code=404,
                endpoint=endpoint,
                response_body='{"message":"No molecular data found"}',
            )
        if endpoint == f"molecular-profiles/{MISSING_EXPRESSION_PROFILE_ID}/molecular-data/fetch":
            raise cbioportal.CbioPortalError(
                "cBioPortal molecular-data/fetch returned HTTP 404: {\"message\":\"Molecular profile not found\"}",
                status_code=404,
                endpoint=endpoint,
                response_body='{"message":"Molecular profile not found"}',
            )
        if endpoint == f"molecular-profiles/{CNA_PROFILE_ID}/discrete-copy-number/fetch":
            return CNA_DATA, {"content-type": "application/json"}
        if endpoint == f"studies/{STUDY_ID}/clinical-attributes":
            return CLINICAL_ATTRIBUTES, {"content-type": "application/json"}
        if endpoint == f"sample-lists/{SAMPLE_LIST_ID}/sample-ids":
            return ["TCGA-A1-A0SB-01", "TCGA-A1-A0SI-01"], {"content-type": "application/json"}
        if endpoint == "samples/fetch":
            return SAMPLES, {"content-type": "application/json"}
        if endpoint == f"studies/{STUDY_ID}/clinical-data/fetch":
            if json_body and "OS_STATUS" in json_body.get("attributeIds", []):
                return SURVIVAL_VALUES, {"content-type": "application/json"}
            return CLINICAL_VALUES, {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")

    def build_url(self, endpoint, params=None):
        url = f"{self.config.api_base_url.rstrip('/')}/{endpoint}"
        if not params:
            return url
        return f"{url}?{'&'.join(f'{key}={value}' for key, value in params.items())}"


STUDY = {
    "studyId": STUDY_ID,
    "name": "Breast Invasive Carcinoma (TCGA, Firehose Legacy)",
    "description": "TCGA Breast Invasive Carcinoma.",
    "cancerTypeId": "brca",
    "allSampleCount": 1108,
    "sequencedSampleCount": 982,
    "cnaSampleCount": 1080,
    "mrnaRnaSeqSampleCount": 0,
    "groups": "PUBLIC",
    "publicStudy": True,
    "readPermission": True,
}


PROFILES = [
    {
        "molecularProfileId": PROFILE_ID,
        "name": "Mutations",
        "description": "Mutation data from whole exome sequencing.",
        "molecularAlterationType": "MUTATION_EXTENDED",
        "datatype": "MAF",
        "studyId": STUDY_ID,
        "showProfileInAnalysisTab": True,
    },
    {
        "molecularProfileId": CNA_PROFILE_ID,
        "name": "Putative copy-number alterations from GISTIC",
        "molecularAlterationType": "COPY_NUMBER_ALTERATION",
        "datatype": "DISCRETE",
        "studyId": STUDY_ID,
    },
    {
        "molecularProfileId": EXPRESSION_PROFILE_ID,
        "name": "mRNA expression z-scores relative to diploid samples (RNA Seq V2 RSEM)",
        "molecularAlterationType": "MRNA_EXPRESSION",
        "datatype": "Z-SCORE",
        "studyId": STUDY_ID,
    },
    {
        "molecularProfileId": DATALESS_EXPRESSION_PROFILE_ID,
        "name": "Empty expression profile fixture",
        "molecularAlterationType": "MRNA_EXPRESSION",
        "datatype": "Z-SCORE",
        "studyId": STUDY_ID,
    },
]


SAMPLE_LISTS = [
    {
        "sampleListId": SAMPLE_LIST_ID,
        "name": "All samples",
        "description": "All samples (1108 samples)",
        "category": "all_cases_in_study",
        "sampleCount": 1108,
        "studyId": STUDY_ID,
    },
    {
        "sampleListId": "brca_tcga_cnaseq",
        "name": "Samples with mutation and CNA data",
        "category": "all_cases_with_mutation_and_cna_data",
        "sampleCount": 963,
        "studyId": STUDY_ID,
    },
    {
        "sampleListId": MISMATCHED_SAMPLE_LIST_ID,
        "name": "LUAD all samples",
        "category": "all_cases_in_study",
        "sampleCount": 585,
        "studyId": "luad_tcga",
    },
]


GENES = [
    {"entrezGeneId": 7157, "hugoGeneSymbol": "TP53", "type": "protein-coding"},
    {"entrezGeneId": 672, "hugoGeneSymbol": "BRCA1", "type": "protein-coding"},
    {"entrezGeneId": 9001, "hugoGeneSymbol": "GENE3", "type": "protein-coding"},
]


MUTATIONS = [
    {
        "sampleId": "TCGA-A1-A0SI-01",
        "patientId": "TCGA-A1-A0SI",
        "entrezGeneId": 7157,
        "proteinChange": "R175H",
        "mutationType": "Missense_Mutation",
        "variantType": "SNP",
        "chr": "17",
        "startPosition": 7578406,
        "endPosition": 7578406,
    },
    {
        "sampleId": "TCGA-A1-A0SP-01",
        "patientId": "TCGA-A1-A0SP",
        "entrezGeneId": 7157,
        "proteinChange": "S183*",
        "mutationType": "Nonsense_Mutation",
        "variantType": "SNP",
        "chr": "17",
        "startPosition": 7578382,
        "endPosition": 7578382,
    },
]


MOLECULAR_DATA = [
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "molecularProfileId": EXPRESSION_PROFILE_ID,
        "entrezGeneId": 7157,
        "value": -0.45,
    },
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "molecularProfileId": EXPRESSION_PROFILE_ID,
        "entrezGeneId": 672,
        "value": 1.2,
    },
    {
        "sampleId": "TCGA-A1-A0SI-01",
        "patientId": "TCGA-A1-A0SI",
        "studyId": STUDY_ID,
        "molecularProfileId": EXPRESSION_PROFILE_ID,
        "entrezGeneId": 7157,
        "value": 0.77,
    },
]


CNA_DATA = [
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "molecularProfileId": CNA_PROFILE_ID,
        "entrezGeneId": 7157,
        "alteration": -1,
    },
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "molecularProfileId": CNA_PROFILE_ID,
        "entrezGeneId": 672,
        "alteration": 2,
    },
    {
        "sampleId": "TCGA-A1-A0SI-01",
        "patientId": "TCGA-A1-A0SI",
        "studyId": STUDY_ID,
        "molecularProfileId": CNA_PROFILE_ID,
        "entrezGeneId": 7157,
        "alteration": 0,
    },
]


CLINICAL_ATTRIBUTES = [
    {
        "clinicalAttributeId": "CANCER_TYPE",
        "displayName": "Cancer Type",
        "description": "Cancer type label.",
        "datatype": "STRING",
        "patientAttribute": False,
        "priority": "1",
        "studyId": STUDY_ID,
    },
    {
        "clinicalAttributeId": "AGE",
        "displayName": "Diagnosis Age",
        "description": "Age at diagnosis.",
        "datatype": "NUMBER",
        "patientAttribute": True,
        "priority": "1",
        "studyId": STUDY_ID,
    },
]


CLINICAL_VALUES = [
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "CANCER_TYPE",
        "value": "Breast Cancer",
    },
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "SAMPLE_TYPE",
        "value": "Primary",
    },
    {
        "sampleId": "TCGA-A1-A0SI-01",
        "patientId": "TCGA-A1-A0SI",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "CANCER_TYPE",
        "value": "Breast Cancer",
    },
]


SAMPLES = [
    {
        "sampleId": "TCGA-A1-A0SB-01",
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "sampleType": "Primary Solid Tumor",
        "sequenced": True,
    },
    {
        "sampleId": "TCGA-A1-A0SI-01",
        "patientId": "TCGA-A1-A0SI",
        "studyId": STUDY_ID,
        "sampleType": "Primary Solid Tumor",
        "sequenced": True,
    },
]


SURVIVAL_VALUES = [
    {
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "OS_STATUS",
        "value": "0:LIVING",
    },
    {
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "OS_MONTHS",
        "value": "8.51",
    },
    {
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "DFS_STATUS",
        "value": "0:DiseaseFree",
    },
    {
        "patientId": "TCGA-A1-A0SB",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "DFS_MONTHS",
        "value": "8.51",
    },
    {
        "patientId": "TCGA-A1-A0SI",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "OS_STATUS",
        "value": "1:DECEASED",
    },
    {
        "patientId": "TCGA-A1-A0SI",
        "studyId": STUDY_ID,
        "clinicalAttributeId": "OS_MONTHS",
        "value": "20.86",
    },
]


class CbioPortalMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = cbioportal.CbioPortalMcpServer(self.client)

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

    def test_tools_list_exposes_cbioportal_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "cbioportal_parameter_domains",
                "cbioportal_resolve_context",
                "cbioportal_study_search",
                "cbioportal_study_lookup",
                "cbioportal_molecular_profiles",
                "cbioportal_sample_lists",
                "cbioportal_mutations_fetch",
                "cbioportal_molecular_data_fetch",
                "cbioportal_discrete_cna_fetch",
                "cbioportal_clinical_attributes",
                "cbioportal_clinical_data_fetch",
                "cbioportal_survival_data_fetch",
                "cbioportal_status",
            },
        )

    def test_study_search_returns_frontend_project_records(self) -> None:
        result = self.call_tool("cbioportal_study_search", {"query": "breast", "max_results": 2})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table", "xref_groups"}, min_records=2)
        self.assertEqual(result["records"][0]["data"]["study_id"], STUDY_ID)

    def test_study_lookup_includes_profile_and_sample_list_previews(self) -> None:
        result = self.call_tool("cbioportal_study_lookup", {"study_id": STUDY_ID, "max_related": 2})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(len(record["data"]["profiles"]), 2)
        self.assertEqual(len(record["data"]["sample_lists"]), 2)

    def test_molecular_profiles_returns_dataset_records(self) -> None:
        result = self.call_tool("cbioportal_molecular_profiles", {"study_id": STUDY_ID, "max_results": 2})
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups"}, min_records=2)
        self.assertEqual(result["records"][0]["data"]["molecular_profile_id"], PROFILE_ID)

    def test_sample_lists_returns_dataset_records(self) -> None:
        result = self.call_tool("cbioportal_sample_lists", {"study_id": STUDY_ID, "max_results": 2})
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups"}, min_records=2)
        self.assertEqual(result["records"][0]["data"]["sample_list_id"], SAMPLE_LIST_ID)

    def test_mutations_fetch_resolves_symbols_and_returns_table_record(self) -> None:
        result = self.call_tool(
            "cbioportal_mutations_fetch",
            {"molecular_profile_id": PROFILE_ID, "sample_list_id": SAMPLE_LIST_ID, "hugo_gene_symbols": ["TP53"], "max_records": 2},
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(result["returned"], 2)
        self.assertEqual(record["data"]["mutations"][0]["gene"], "TP53")
        self.assertEqual(self.client.calls[-1][3]["entrezGeneIds"], [7157])

    def test_molecular_data_fetch_returns_heatmap_matrix_record(self) -> None:
        result = self.call_tool(
            "cbioportal_molecular_data_fetch",
            {
                "molecular_profile_id": EXPRESSION_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["TP53", "BRCA1"],
                "max_records": 3,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        record = result["records"][0]
        self.assertEqual(result["returned"], 3)
        self.assertEqual(record["data"]["values"][0]["gene"], "TP53")
        self.assertEqual(record["data"]["matrix"][0]["TP53"], -0.45)
        self.assertEqual(record["data"]["matrix"][0]["BRCA1"], 1.2)
        self.assertEqual(self.client.calls[-1][3]["entrezGeneIds"], [672, 7157])

    def test_molecular_data_fetch_resolves_hugo_symbol(self) -> None:
        result = self.call_tool(
            "cbioportal_molecular_data_fetch",
            {
                "molecular_profile_id": EXPRESSION_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["GENE3"],
                "max_records": 1,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        self.assertEqual(self.client.calls[-1][3]["entrezGeneIds"], [9001])
        self.assertNotIn("warnings", result)

    def test_molecular_data_fetch_classifies_missing_profile_on_fetch_404(self) -> None:
        result = self.call_tool(
            "cbioportal_molecular_data_fetch",
            {
                "molecular_profile_id": MISSING_EXPRESSION_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["GENE3"],
                "max_records": 3,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        self.assertEqual(result["returned"], 0)
        self.assertEqual(result["upstream_returned"], 0)
        self.assertEqual(result["molecular_values"], [])
        self.assertEqual(result["warnings"][0]["code"], "cbioportal_profile_not_found")
        self.assertEqual(result["warnings"][0]["status_code"], 404)
        self.assertEqual(result["diagnostics"][0]["status"], "profile_not_found")
        self.assertEqual(result["records"][0]["data"]["diagnostics"][0]["status"], "profile_not_found")

    def test_molecular_data_fetch_classifies_study_mismatch_on_empty_fetch(self) -> None:
        result = self.call_tool(
            "cbioportal_molecular_data_fetch",
            {
                "molecular_profile_id": EXPRESSION_PROFILE_ID,
                "sample_list_id": MISMATCHED_SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["GENE3"],
                "max_records": 3,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        self.assertEqual(result["returned"], 0)
        self.assertEqual(result["warnings"][0]["code"], "cbioportal_profile_sample_list_study_mismatch")
        self.assertEqual(result["diagnostics"][0]["status"], "study_mismatch")
        self.assertFalse(result["diagnostics"][0]["study_match"])

    def test_molecular_data_fetch_classifies_valid_context_with_no_fetch_data(self) -> None:
        result = self.call_tool(
            "cbioportal_molecular_data_fetch",
            {
                "molecular_profile_id": DATALESS_EXPRESSION_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["GENE3"],
                "max_records": 3,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        self.assertEqual(result["returned"], 0)
        self.assertEqual(result["warnings"][0]["code"], "cbioportal_fetch_context_not_found")
        self.assertEqual(result["diagnostics"][0]["status"], "fetch_context_not_found")
        self.assertTrue(result["diagnostics"][0]["study_match"])

    def test_molecular_data_fetch_skips_when_symbols_do_not_resolve(self) -> None:
        result = self.call_tool(
            "cbioportal_molecular_data_fetch",
            {
                "molecular_profile_id": EXPRESSION_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["NOTREAL"],
                "max_records": 3,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        self.assertEqual(result["returned"], 0)
        self.assertEqual(result["warnings"][0]["code"], "unresolved_gene_symbols")
        self.assertEqual(result["warnings"][1]["code"], "no_resolved_entrez_gene_ids")
        self.assertEqual(self.client.calls[-1][0], "genes/fetch")

    def test_discrete_cna_fetch_returns_heatmap_matrix_record(self) -> None:
        result = self.call_tool(
            "cbioportal_discrete_cna_fetch",
            {
                "molecular_profile_id": CNA_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "hugo_gene_symbols": ["TP53", "BRCA1"],
                "discrete_copy_number_event_type": "ALL",
                "max_records": 3,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups", "heatmap_matrix"})
        record = result["records"][0]
        self.assertEqual(result["returned"], 3)
        self.assertEqual(record["data"]["values"][0]["alteration_label"], "HETLOSS")
        self.assertEqual(record["data"]["matrix"][0]["TP53"], -1)
        self.assertEqual(record["data"]["matrix"][0]["BRCA1"], 2)
        self.assertEqual(record["data"]["alteration_labels"]["2"], "AMP")

    def test_clinical_attributes_returns_table_record(self) -> None:
        result = self.call_tool("cbioportal_clinical_attributes", {"study_id": STUDY_ID, "max_results": 2})
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(result["returned"], 2)
        self.assertEqual(record["data"]["attributes"][0]["clinical_attribute_id"], "CANCER_TYPE")
        self.assertEqual(record["data"]["patient_attribute_count"], 1)

    def test_resolve_context_lists_compatible_study_parameters(self) -> None:
        result = self.call_tool("cbioportal_resolve_context", {"study_id": STUDY_ID, "context_type": "fetch_context", "max_results": 20})
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        context_names = {context["parameter_name"] for context in result["contexts"]}
        self.assertIn("molecular_profile_id", context_names)
        self.assertIn("sample_list_id", context_names)
        self.assertIn("clinical_attribute_ids", context_names)
        self.assertTrue(any(context["value"] == EXPRESSION_PROFILE_ID for context in result["contexts"]))
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("cbioportal_molecular_profiles", tool_names)
        self.assertIn("cbioportal_sample_lists", tool_names)

    def test_resolve_context_prioritizes_entities_for_small_context_window(self) -> None:
        result = self.call_tool("cbioportal_resolve_context", {"study_id": STUDY_ID, "max_results": 2})
        self.assertEqual(result["contexts"][0]["parameter_name"], "study_id")
        self.assertEqual(result["contexts"][0]["group"], "studies")
        self.assertTrue(result["entities"])
        entity_values = {entity["value"] for entity in result["entities"]}
        self.assertIn(STUDY_ID, entity_values)

    def test_resolve_context_recommends_fetch_for_compatible_profile_and_sample_list(self) -> None:
        result = self.call_tool(
            "cbioportal_resolve_context",
            {
                "study_id": STUDY_ID,
                "molecular_profile_id": EXPRESSION_PROFILE_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "context_type": "fetch_context",
                "max_results": 20,
            },
        )
        self.assertTrue(result["resolved"]["compatible"])
        self.assertEqual(result["resolved"]["profile_type"], "MRNA_EXPRESSION")
        self.assertIn("recommended_calls", result)
        fetch_calls = [call for call in result["recommended_calls"] if call["tool_name"] == "cbioportal_molecular_data_fetch"]
        self.assertEqual(fetch_calls[0]["arguments"]["molecular_profile_id"], EXPRESSION_PROFILE_ID)
        self.assertEqual(fetch_calls[0]["arguments"]["sample_list_id"], SAMPLE_LIST_ID)
        self.assertIn("hugo_gene_symbols or entrez_gene_ids", fetch_calls[0]["requires"])

    def test_resolve_context_reports_profile_sample_list_mismatch(self) -> None:
        result = self.call_tool(
            "cbioportal_resolve_context",
            {
                "molecular_profile_id": EXPRESSION_PROFILE_ID,
                "sample_list_id": MISMATCHED_SAMPLE_LIST_ID,
                "context_type": "fetch_context",
            },
        )
        self.assertFalse(result["resolved"]["compatible"])
        codes = {diagnostic["code"] for diagnostic in result["diagnostics"]}
        self.assertIn("cbioportal_profile_sample_list_study_mismatch", codes)

    def test_clinical_data_fetch_returns_matrix_record_from_sample_list(self) -> None:
        result = self.call_tool(
            "cbioportal_clinical_data_fetch",
            {
                "study_id": STUDY_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "clinical_attribute_ids": ["CANCER_TYPE", "SAMPLE_TYPE"],
                "max_ids": 2,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(result["returned"], 3)
        self.assertEqual(record["data"]["matrix"][0]["sample_id"], "TCGA-A1-A0SB-01")
        self.assertEqual(record["data"]["matrix"][0]["CANCER_TYPE"], "Breast Cancer")
        self.assertEqual(self.client.calls[-1][3]["ids"], ["TCGA-A1-A0SB-01", "TCGA-A1-A0SI-01"])

    def test_survival_data_fetch_returns_chart_ready_rows_from_sample_list(self) -> None:
        result = self.call_tool(
            "cbioportal_survival_data_fetch",
            {
                "study_id": STUDY_ID,
                "sample_list_id": SAMPLE_LIST_ID,
                "survival_prefixes": ["OS", "DFS"],
                "max_ids": 2,
            },
        )
        assert_result_frontend_contract(self, result, expected_components={"dataset"}, required_preview_kinds={"table", "xref_groups"})
        record = result["records"][0]
        self.assertEqual(result["returned"], 3)
        self.assertEqual(record["data"]["survival_rows"][0]["endpoint"], "OS")
        self.assertEqual(record["data"]["survival_rows"][0]["event_observed"], False)
        self.assertIn("survival_curve", {preview["kind"] for preview in record["display"]["previews"]})
        self.assertEqual(self.client.calls[-1][3]["ids"], ["TCGA-A1-A0SB", "TCGA-A1-A0SI"])

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("cbioportal_status", {})
        self.assertEqual(result["server"], "cbioportal")
        self.assertIn("cbioportal_study_lookup", result["available_tools"])
        self.assertIn("cbioportal_molecular_data_fetch", result["available_tools"])
        self.assertIn("heatmap_matrix", result["preview_kinds"])
        self.assertIn("dataset", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("cbioportal_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_study_id"], STUDY_ID)


if __name__ == "__main__":
    unittest.main()
