from __future__ import annotations

import importlib.util
import pathlib
import sys
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "cellxgene" / "server.py"
SPEC = importlib.util.spec_from_file_location("cellxgene_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
cellxgene = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = cellxgene
SPEC.loader.exec_module(cellxgene)


COLLECTION_ID = "db468083-041c-41ca-8f6f-bf991a070adf"


class FakeClient:
    def __init__(self) -> None:
        self.config = cellxgene.CellxGeneConfig(contact=None)
        self.requests_per_second = 2
        self.calls = []

    def request_json_with_headers(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == f"collections/{COLLECTION_ID}":
            return CELLXGENE_COLLECTION, {"content-type": "application/json"}
        if endpoint == "collections":
            return [CELLXGENE_COLLECTION, OTHER_COLLECTION], {"content-type": "application/json"}
        raise AssertionError(f"unexpected endpoint {endpoint}")


CELLXGENE_COLLECTION = {
    "collection_id": COLLECTION_ID,
    "collection_url": f"https://cellxgene.cziscience.com/collections/{COLLECTION_ID}",
    "collection_version_id": "8908b77f-b332-41e4-8dea-cb1f8e3cf431",
    "consortia": ["CZI Cell Science"],
    "contact_email": "szhong@example.org",
    "contact_name": "Sheng Zhong",
    "created_at": "2026-06-09T22:18:02+00:00",
    "curator_name": "Jennifer Yu-Sheng Chien",
    "datasets": [
        {
            "assay": [{"label": "10x 3' v2", "ontology_term_id": "EFO:0009899"}],
            "assets": [{"filesize": 421893976, "filetype": "H5AD", "url": "https://datasets.cellxgene.cziscience.com/example-one.h5ad"}],
            "cell_count": 59605,
            "cell_type": [{"label": "endothelial cell of umbilical vein", "ontology_term_id": "CL:0002618"}],
            "citation": "Publication: https://doi.org/10.1038/s41467-020-18957-w",
            "dataset_id": "6cda3b13-7257-45b9-ac20-0a7e6697e4f2",
            "dataset_version_id": "aaeb9a19-a77c-49a8-bdfa-1949773738b0",
            "disease": [{"label": "normal", "ontology_term_id": "PATO:0000461"}],
            "explorer_url": "https://cellxgene.cziscience.com/e/6cda3b13-7257-45b9-ac20-0a7e6697e4f2.cxg/",
            "feature_count": 32383,
            "organism": [{"label": "Homo sapiens", "ontology_term_id": "NCBITaxon:9606"}],
            "primary_cell_count": 59605,
            "schema_version": "7.1.0",
            "suspension_type": ["cell"],
            "tissue": [{"label": "endothelial cell", "ontology_term_id": "CL:0000115", "tissue_type": "primary cell culture"}],
            "title": "scRNA-seq data analysis of HUVECs treated with high glucose and TNFα",
        },
        {
            "assay": [{"label": "10x 3' v3", "ontology_term_id": "EFO:0009922"}],
            "assets": [{"filesize": 122029606, "filetype": "H5AD", "url": "https://datasets.cellxgene.cziscience.com/example-two.h5ad"}],
            "cell_count": 11243,
            "cell_type": [{"label": "endothelial cell of artery", "ontology_term_id": "CL:1000413"}],
            "dataset_id": "42b6a476-c51d-4f8b-b68b-44941b3a11bf",
            "dataset_version_id": "9199a4c8-f8e9-4cc6-8c3b-bd9b6e5524d4",
            "disease": [{"label": "type 2 diabetes mellitus", "ontology_term_id": "MONDO:0005148"}],
            "explorer_url": "https://cellxgene.cziscience.com/e/42b6a476-c51d-4f8b-b68b-44941b3a11bf.cxg/",
            "organism": [{"label": "Homo sapiens", "ontology_term_id": "NCBITaxon:9606"}],
            "tissue": [{"label": "mesenteric artery", "ontology_term_id": "UBERON:0005616", "tissue_type": "tissue"}],
            "title": "scRNA-seq data analysis of endothelium-enriched mesenteric arterial tissues from human donors",
        },
    ],
    "description": "Stress-induced RNA chromatin interactions promote endothelial dysfunction in single-cell data.",
    "doi": "10.1038/s41467-020-18957-w",
    "is_pre_analysis": False,
    "links": [
        {"link_name": "GSE135357", "link_type": "RAW_DATA", "link_url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE135357"},
        {"link_name": "Code", "link_type": "OTHER", "link_url": "https://github.com/Zhong-Lab-UCSD/NCOMMS-19-24818"},
    ],
    "name": "Stress-induced RNA-chromatin interactions promote endothelial dysfunction",
    "published_at": "2021-05-06T16:41:21+00:00",
    "publisher_metadata": {
        "authors": [{"family": "Calandrelli", "given": "Riccardo"}, {"family": "Zhong", "given": "Sheng"}],
        "is_preprint": False,
        "journal": "Nat Commun",
        "published_year": 2020,
    },
    "revised_at": "2026-06-11T16:54:39+00:00",
    "visibility": "PUBLIC",
}


OTHER_COLLECTION = {
    **CELLXGENE_COLLECTION,
    "collection_id": "af893e86-8e9f-41f1-a474-ef05359b1fb7",
    "name": "Single-cell transcriptomic atlas for adult human retina",
    "description": "Healthy human retina single nucleus data.",
    "doi": "10.1016/j.xgen.2023.100298",
}


class CellxGeneMcpServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = FakeClient()
        self.server = cellxgene.CellxGeneMcpServer(self.client)

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

    def test_tools_list_exposes_cellxgene_tools(self) -> None:
        response = self.server.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        assert response is not None
        names = {tool["name"] for tool in response["result"]["tools"]}
        self.assertEqual(
            names,
            {
                "cellxgene_collection_lookup",
                "cellxgene_collections_search",
                "cellxgene_collection_assets",
                "cellxgene_status",
            },
        )

    def test_collection_lookup_returns_frontend_compatible_project_record(self) -> None:
        result = self.call_tool("cellxgene_collection_lookup", {"collection_id": COLLECTION_ID, "max_datasets": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"project"},
            required_preview_kinds={"table", "citation_list", "xref_groups", "download_manifest"},
        )
        record = result["records"][0]
        self.assertEqual(record["data"]["collection_id"], COLLECTION_ID)
        self.assertEqual(record["data"]["datasets"][0]["cell_count"], 59605)
        self.assertEqual(record["data"]["doi_url"], "https://doi.org/10.1038/s41467-020-18957-w")

    def test_collections_search_filters_public_collection_metadata(self) -> None:
        result = self.call_tool("cellxgene_collections_search", {"query": "retina", "max_results": 2, "max_datasets": 1})
        assert_result_frontend_contract(self, result, expected_components={"project"}, required_preview_kinds={"table"}, min_records=1)
        self.assertEqual(result["records"][0]["data"]["collection_id"], "af893e86-8e9f-41f1-a474-ef05359b1fb7")
        self.assertEqual(result["searched_collections"], 2)

    def test_collection_assets_returns_download_plan_record(self) -> None:
        result = self.call_tool("cellxgene_collection_assets", {"collection_id": COLLECTION_ID, "max_datasets": 2})
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"download_plan"},
            required_preview_kinds={"download_manifest", "table"},
        )
        record = result["records"][0]
        self.assertEqual(result["returned"], 2)
        self.assertEqual(record["data"]["assets"][0]["url"], "https://datasets.cellxgene.cziscience.com/example-one.h5ad")

    def test_status_reports_inventory_without_network_by_default(self) -> None:
        result = self.call_tool("cellxgene_status", {})
        self.assertEqual(result["server"], "cellxgene")
        self.assertIn("cellxgene_collection_lookup", result["available_tools"])
        self.assertIn("project", result["frontend_components"])
        self.assertNotIn("network_check", result)

    def test_status_can_run_small_network_check(self) -> None:
        result = self.call_tool("cellxgene_status", {"check_network": True})
        self.assertEqual(result["network_check"]["example_collection_id"], COLLECTION_ID)
        self.assertIn("endothelial", result["network_check"]["example_name"])


if __name__ == "__main__":
    unittest.main()
