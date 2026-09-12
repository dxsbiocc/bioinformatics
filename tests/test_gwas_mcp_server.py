from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "gwas" / "server.py"
SPEC = importlib.util.spec_from_file_location("gwas_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
gwas = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gwas
SPEC.loader.exec_module(gwas)


class FakeClient:
    def __init__(self) -> None:
        self.config = gwas.GwasConfig(contact=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "metadata":
            return GWAS_METADATA, {"content-type": "application/json"}
        if endpoint == "single-nucleotide-polymorphisms/rs699":
            return GWAS_SNP, {"content-type": "application/json"}
        if endpoint == "associations" and params.get("rs_id") == "rs699":
            return associations_page(GWAS_VARIANT_ASSOCIATIONS, total=17), {"content-type": "application/json"}
        if endpoint == "associations" and params.get("mapped_gene") == "BRCA1":
            return associations_page(GWAS_GENE_ASSOCIATIONS, total=31), {"content-type": "application/json"}
        if endpoint == "associations" and params.get("efo_trait") == "asthma":
            return associations_page(GWAS_TRAIT_ASSOCIATIONS, total=3236), {"content-type": "application/json"}
        if endpoint == "studies" and params.get("efo_trait") == "asthma":
            return studies_page(GWAS_STUDIES, total=285), {"content-type": "application/json"}
        raise AssertionError(f"unexpected request: {endpoint} {params}")


GWAS_METADATA = {
    "title": "GWAS Catalog Rest API 2.0",
    "version": "2.0",
    "data_release_date": "2026-09-04",
    "api_release_date": "2025-08-01",
    "dbsnp_build": "156",
}

GWAS_SNP = {
    "rs_id": "rs699",
    "merged": 0,
    "functional_class": "missense_variant",
    "last_update_date": "2026-06-19T18:17:35.785+00:00",
    "locations": [
        {
            "chromosome_name": "1",
            "chromosome_position": 230710048,
            "region": {"name": "1q42.2"},
        }
    ],
    "alleles": "A/G (forward)",
    "most_severe_consequence": "missense_variant",
    "mapped_genes": ["AGT"],
    "_links": {
        "self": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/single-nucleotide-polymorphisms/rs699"}
    },
}

GWAS_VARIANT_ASSOCIATIONS = [
    {
        "association_id": 221332162,
        "risk_frequency": "NR",
        "p_value": 2.0e-12,
        "beta": "0.0387832 unit increase",
        "range": "[0.028-0.05]",
        "efo_traits": [{"efo_id": "OBA_2052006", "efo_trait": "amount of tenascin (human) in blood"}],
        "reported_trait": ["Circulating TNC levels"],
        "accession_id": "GCST90860463",
        "locations": ["1:230710048"],
        "mapped_genes": ["AGT"],
        "pubmed_id": "42097137",
        "first_author": "Koprulu M",
        "snp_allele": [{"rs_id": "rs699", "effect_allele": "?"}],
        "_links": {
            "self": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/associations/221332162"},
            "snp": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/single-nucleotide-polymorphisms/rs699"},
        },
    }
]

GWAS_GENE_ASSOCIATIONS = [
    {
        "association_id": 218086295,
        "risk_frequency": "NR",
        "p_value": 2.0e-24,
        "beta": "-",
        "range": "-",
        "efo_traits": [{"efo_id": "EFO_0004503", "efo_trait": "hematological measurement"}],
        "reported_trait": ["Hematological traits (multi-trait analysis)"],
        "accession_id": "GCST90838669",
        "locations": ["17:43100558"],
        "mapped_genes": ["BRCA1"],
        "pubmed_id": "38627641",
        "first_author": "Troubat L",
        "snp_allele": [{"rs_id": "rs10445316", "effect_allele": "?"}],
        "_links": {
            "self": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/associations/218086295"},
            "snp": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/single-nucleotide-polymorphisms/rs10445316"},
        },
    }
]

GWAS_TRAIT_ASSOCIATIONS = [
    {
        "association_id": 222835859,
        "risk_frequency": "NR",
        "p_value": 2.0e-14,
        "beta": "-",
        "range": "-",
        "efo_traits": [{"efo_id": "MONDO_0004979", "efo_trait": "asthma"}],
        "reported_trait": ["Asthma"],
        "accession_id": "GCST90984699",
        "locations": ["17:39924612"],
        "mapped_genes": ["ORMDL3"],
        "pubmed_id": "40610054",
        "first_author": "Liu KY",
        "snp_allele": [{"rs_id": "rs4065275", "effect_allele": "?"}],
        "_links": {
            "self": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/associations/222835859"},
            "snp": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/single-nucleotide-polymorphisms/rs4065275"},
        },
    }
]

GWAS_STUDIES = [
    {
        "initial_sample_size": "17,892 East Asian ancestry cases",
        "replication_sample_size": "NA",
        "accession_id": "GCST90984699",
        "full_summary_stats_available": False,
        "pubmed_id": 40610054,
        "disease_trait": "Asthma",
        "efo_traits": [{"efo_id": "MONDO_0004979", "efo_trait": "asthma"}],
        "full_summary_stats": "NA",
        "_links": {"self": {"href": "https://www.ebi.ac.uk/gwas/rest/api/v2/studies/GCST90984699"}},
    }
]


def associations_page(records, total):
    return {
        "_embedded": {"associations": records},
        "page": {"size": len(records), "totalElements": total, "totalPages": 1, "number": 0},
    }


def studies_page(records, total):
    return {
        "_embedded": {"studies": records},
        "page": {"size": len(records), "totalElements": total, "totalPages": 1, "number": 0},
    }


class GwasMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = gwas.GwasMcpServer(self.client)

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

    def test_tools_list_exposes_gwas_tools(self) -> None:
        response = self.server.handle(
            {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        )
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "gwas_variant_lookup",
                "gwas_gene_lookup",
                "gwas_trait_search",
                "gwas_status",
            },
        )

    def test_variant_lookup_returns_frontend_compatible_variant_record(self) -> None:
        result = self.call_tool("gwas_variant_lookup", {"rs_id": "rs699", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"variant"},
            required_preview_kinds={"table", "citation_list", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["display"]["component"], "variant")
        self.assertEqual(record["data"]["snp"]["location"], "1:230710048")
        self.assertEqual(record["data"]["associations"][0]["pubmed_id"], "42097137")

    def test_gene_lookup_returns_frontend_compatible_gene_record(self) -> None:
        result = self.call_tool("gwas_gene_lookup", {"gene": "BRCA1", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"table", "citation_list", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["display"]["component"], "gene")
        self.assertEqual(record["data"]["gene"], "BRCA1")
        self.assertEqual(record["data"]["total_associations"], 31)

    def test_trait_search_returns_frontend_compatible_dataset_record(self) -> None:
        result = self.call_tool("gwas_trait_search", {"trait": "asthma", "max_results": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"table", "citation_list", "xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(record["display"]["component"], "dataset")
        self.assertEqual(record["data"]["total_studies"], 285)
        self.assertEqual(record["data"]["studies"][0]["accession_id"], "GCST90984699")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("gwas_status", {})
        self.assertEqual(result["server"], "gwas")
        self.assertIn("gwas_variant_lookup", result["available_tools"])
        self.assertIn("dataset", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("gwas_status", {"check_network": True})
        self.assertEqual(result["network_check"]["data_release_date"], "2026-09-04")


if __name__ == "__main__":
    unittest.main()
