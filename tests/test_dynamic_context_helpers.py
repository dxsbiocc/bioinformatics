from __future__ import annotations

import unittest

from mcp.dynamic_context import (
    build_dynamic_context_response,
    dedupe_recommended_calls,
    entity_summaries,
    prioritize_contexts,
    prioritize_recommended_calls,
)


class DynamicContextHelperTests(unittest.TestCase):
    def test_prioritize_contexts_keeps_entities_before_static_hints(self) -> None:
        contexts = [
            {"group": "context_types", "value": "all", "label": "all", "kind": "enum", "metadata": {}},
            {
                "group": "genes",
                "parameter_name": "gene_id",
                "value": "ENSG00000141510",
                "label": "TP53",
                "kind": "gnomad_gene",
                "url": "https://gnomad.broadinstitute.org/gene/ENSG00000141510",
                "metadata": {"symbol": "TP53"},
            },
            {
                "group": "genes",
                "parameter_name": "include_relations",
                "value": True,
                "label": "Include relations",
                "kind": "boolean_filter",
                "url": "https://example.org/docs",
                "metadata": {},
            },
        ]

        ordered = prioritize_contexts(contexts, {"genes"})

        self.assertEqual(ordered[0]["value"], "ENSG00000141510")
        self.assertEqual(ordered[-1]["group"], "context_types")

    def test_entity_summaries_filter_static_and_boolean_contexts(self) -> None:
        contexts = [
            {"group": "context_types", "value": "all", "label": "all", "kind": "enum", "metadata": {}},
            {
                "group": "compounds",
                "parameter_name": "cid",
                "value": "2244",
                "label": "Aspirin",
                "kind": "pubchem_compound",
                "url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
                "metadata": {"title": "Aspirin"},
            },
            {
                "group": "compounds",
                "parameter_name": "include_raw",
                "value": True,
                "label": "include_raw",
                "kind": "boolean",
                "url": "https://example.org/docs",
                "metadata": {},
            },
        ]

        summaries = entity_summaries(contexts, {"compounds"}, 10)

        self.assertEqual(summaries, [
            {
                "parameter_name": "cid",
                "value": "2244",
                "label": "Aspirin",
                "kind": "pubchem_compound",
                "url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
                "metadata": {"title": "Aspirin"},
            }
        ])

    def test_recommended_calls_dedupe_and_prioritize_same_server_calls(self) -> None:
        calls = [
            {"server": "ensembl", "tool_name": "ensembl_lookup", "arguments": {"ensembl_id": "ENSG1"}},
            {"tool_name": "gnomad_gene_lookup", "arguments": {"gene_id": "ENSG1"}},
            {"tool_name": "gnomad_gene_lookup", "arguments": {"gene_id": "ENSG1"}},
        ]

        ordered = prioritize_recommended_calls(dedupe_recommended_calls(calls))

        self.assertEqual(len(ordered), 2)
        self.assertEqual(ordered[0]["tool_name"], "gnomad_gene_lookup")
        self.assertEqual(ordered[1]["tool_name"], "ensembl_lookup")

    def test_recommended_calls_can_dedupe_without_server_prefix(self) -> None:
        calls = [
            {"server": "alpha", "tool_name": "lookup", "arguments": {"id": "A"}},
            {"server": "beta", "tool_name": "lookup", "arguments": {"id": "A"}},
        ]

        self.assertEqual(len(dedupe_recommended_calls(calls)), 2)
        self.assertEqual(len(dedupe_recommended_calls(calls, include_server=False)), 1)

    def test_build_dynamic_context_response_keeps_frontend_contract(self) -> None:
        source = {"name": "PubChem", "url": "https://pubchem.ncbi.nlm.nih.gov/rest/pug"}
        response = build_dynamic_context_response(
            schema_version="bioinformatics.result.v1",
            context_schema_version="bioinformatics.dynamic_context.v1",
            database="pubchem",
            query={"query": "aspirin"},
            contexts=[
                {"group": "context_types", "value": "all", "label": "all", "kind": "enum"},
                {
                    "group": "compounds",
                    "parameter_name": "cid",
                    "value": "2244",
                    "label": "Aspirin",
                    "kind": "pubchem_compound",
                    "url": "https://pubchem.ncbi.nlm.nih.gov/compound/2244",
                    "metadata": {"title": "Aspirin"},
                },
            ],
            recommended_calls=[
                {"server": "chembl", "tool_name": "chembl_resolve_context", "arguments": {"query": "Aspirin"}},
                {"tool_name": "pubchem_compound_lookup", "arguments": {"cid": "2244"}},
                {"tool_name": "pubchem_compound_lookup", "arguments": {"cid": "2244"}},
            ],
            max_results=5,
            fallback_source={"name": "fallback"},
            sources=[source],
            entity_groups={"compounds"},
            raw={"compound_search": {"IdentifierList": {"CID": [2244]}}},
            include_raw=True,
            prioritize_entities=True,
            prioritize_same_server_calls=True,
        )

        self.assertEqual(response["operation"], "resolve_context")
        self.assertEqual(response["source"], source)
        self.assertEqual(response["provenance"], source)
        self.assertEqual(response["contexts"][0]["value"], "2244")
        self.assertEqual(response["entities"][0]["value"], "2244")
        self.assertEqual(response["recommended_calls"][0]["tool_name"], "pubchem_compound_lookup")
        self.assertEqual(len(response["recommended_calls"]), 2)
        self.assertEqual(response["raw"]["compound_search"]["IdentifierList"]["CID"], [2244])

    def test_build_dynamic_context_response_uses_fallback_source(self) -> None:
        fallback = {"name": "fallback", "url": "https://example.org/fallback"}
        response = build_dynamic_context_response(
            schema_version="bioinformatics.result.v1",
            context_schema_version="bioinformatics.dynamic_context.v1",
            database="test",
            query={},
            contexts=[],
            recommended_calls=[],
            max_results=1,
            fallback_source=fallback,
            sources=[],
        )

        self.assertEqual(response["source"], fallback)
        self.assertEqual(response["provenance"], fallback)
        self.assertNotIn("raw", response)

    def test_build_dynamic_context_response_preserves_extra_summary_fields(self) -> None:
        response = build_dynamic_context_response(
            schema_version="bioinformatics.result.v1",
            context_schema_version="bioinformatics.dynamic_context.v1",
            database="cbioportal",
            query={"study_id": "brca_tcga"},
            contexts=[
                {
                    "parameter_name": "study_id",
                    "value": "brca_tcga",
                    "label": "Breast invasive carcinoma",
                    "kind": "study",
                    "url": "https://www.cbioportal.org/study/summary?id=brca_tcga",
                    "metadata": {"cancer_type": "brca"},
                },
                {
                    "parameter_name": "molecular_profile_id",
                    "value": "brca_tcga_rna_seq_v2_mrna",
                    "label": "mRNA expression",
                    "kind": "profile",
                    "url": "https://www.cbioportal.org/",
                    "metadata": {"study_id": "brca_tcga"},
                },
            ],
            recommended_calls=[
                {"tool_name": "cbioportal_molecular_profiles", "arguments": {"study_id": "brca_tcga"}},
                {"tool_name": "cbioportal_molecular_profiles", "arguments": {"study_id": "brca_tcga"}},
            ],
            max_results=5,
            fallback_source={"name": "cBioPortal"},
            sources=[],
            summary_fields={
                "entities": lambda context: context.get("parameter_name") in {"study_id", "molecular_profile_id"},
                "studies": lambda context: context.get("parameter_name") == "study_id",
                "profiles": lambda context: context.get("parameter_name") == "molecular_profile_id",
            },
            extra_fields={"resolved": {"compatible": True}},
            dedupe_calls=False,
        )

        self.assertEqual(len(response["recommended_calls"]), 2)
        self.assertEqual(response["entities"][0]["value"], "brca_tcga")
        self.assertEqual(response["studies"][0]["value"], "brca_tcga")
        self.assertEqual(response["profiles"][0]["value"], "brca_tcga_rna_seq_v2_mrna")
        self.assertTrue(response["resolved"]["compatible"])


if __name__ == "__main__":
    unittest.main()
