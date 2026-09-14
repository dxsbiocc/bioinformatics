from __future__ import annotations

import json
import pathlib
import struct
import subprocess
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
ROUTER = ROOT / "skills" / "omics-visualization" / "scripts" / "route_template.py"
QA = ROOT / "skills" / "omics-visualization" / "scripts" / "qa_single_plot.py"
VALIDATOR = ROOT / "skills" / "omics-visualization" / "scripts" / "validate_template_contracts.py"


class OmicsVisualizationRouterTests(unittest.TestCase):
    def run_router(self, table_text: str, query: str) -> dict:
        with tempfile.TemporaryDirectory() as tmpdir:
            table_path = pathlib.Path(tmpdir) / "input.tsv"
            table_path.write_text(table_text, encoding="utf-8")
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROUTER),
                    "--input",
                    str(table_path),
                    "--query",
                    query,
                    "--json",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
        return json.loads(proc.stdout)

    def test_generic_one_to_many_association_routes_to_scatter_one2many(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "focal_entity\trelated_entity\tclass\trho\tq_value",
                    "metabolite_A\tpathway_1\tlipid\t0.42\t0.001",
                    "metabolite_A\tpathway_2\tstress\t-0.31\t0.020",
                    "metabolite_A\tpathway_3\tstress\t0.18\t0.080",
                ]
            ),
            "center one-to-many association",
        )
        top = payload["recommendations"][0]
        self.assertEqual(top["id"], "scatter-one2many")
        self.assertEqual(top["confidence"], "high")
        self.assertEqual(top["role_mapping"]["target_entity"], "related_entity")
        self.assertEqual(top["role_mapping"]["signed_association"], "rho")
        self.assertIn("one_to_many_association", payload["input_profile"]["shapes"])

    def test_exact_template_id_can_override_shape_shortlist(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "focal_entity\trelated_entity\tclass\trho\tq_value",
                    "entity_A\titem_1\tA\t0.42\t0.001",
                    "entity_A\titem_2\tB\t-0.31\t0.020",
                ]
            ),
            "先用 heatmap-corr-bubble 看看效果",
        )
        top = payload["recommendations"][0]
        self.assertEqual(top["id"], "heatmap-corr-bubble")
        self.assertEqual(top["confidence"], "high")
        self.assertTrue(any("exact template id" in reason for reason in top["rationale"]))

    def test_focal_and_target_prefixes_do_not_collapse_to_same_entity(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "focal_feature\ttarget_feature\tfamily\trho",
                    "feature_A\titem_1\tA\t0.42",
                    "feature_A\titem_2\tB\t-0.31",
                ]
            ),
            "one-to-many focal association",
        )
        roles = payload["recommendations"][0]["role_mapping"]
        self.assertEqual(roles["focal_entity"], "focal_feature")
        self.assertEqual(roles["target_entity"], "target_feature")

    def test_feature_level_testing_routes_to_volcano(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "feature\tlog2FoldChange\tpadj",
                    "item_A\t1.3\t0.001",
                    "item_B\t-0.8\t0.020",
                    "item_C\t0.2\t0.400",
                ]
            ),
            "volcano differential expression adjusted p overview",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "scatter-volcano")
        self.assertIn("feature_level_testing", payload["input_profile"]["shapes"])

    def test_explicit_pair_axes_can_route_to_grouped_correlation_heatmap(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "var1\tvar2\tcategory\trho\tp_value",
                    "A\tB\tmodule_1\t0.42\t0.001",
                    "A\tC\tmodule_1\t-0.31\t0.020",
                    "B\tC\tmodule_2\t0.18\t0.080",
                ]
            ),
            "grouped correlation block heatmap",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "heatmap-corr-grouped")
        self.assertIn("grouped_correlation", payload["input_profile"]["shapes"])
        self.assertIn("triangular_correlation", payload["input_profile"]["shapes"])

    def test_source_target_value_routes_to_sankey_when_flow_is_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "source\ttarget\tvalue",
                    "A\tB\t10",
                    "A\tC\t5",
                    "B\tD\t3",
                ]
            ),
            "sankey flow source target value",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "sankey-basic")
        self.assertIn("flow_table", payload["input_profile"]["shapes"])

    def test_parent_child_table_routes_to_tree_when_hierarchy_is_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "parent\tname\tvalue",
                    "root\tcell_cycle\t10",
                    "root\tcell_death\t8",
                    "cell_cycle\tmitosis\t3",
                ]
            ),
            "tree hierarchy parent child",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "tree-basic")
        self.assertIn("hierarchy_edges", payload["input_profile"]["shapes"])

    def test_time_value_table_routes_to_line_when_trend_is_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "time\tvalue",
                    "1\t0.2",
                    "2\t0.4",
                    "3\t0.3",
                ]
            ),
            "line trend over time",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "line-basic")
        self.assertIn("time_series", payload["input_profile"]["shapes"])

    def test_exact_doughnut_request_routes_to_doughnut(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "label\tvalue",
                    "A\t10",
                    "B\t8",
                    "C\t3",
                ]
            ),
            "pie-doughnut composition",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "pie-doughnut")
        self.assertIn("part_to_whole", payload["input_profile"]["shapes"])

    def test_grouped_category_value_routes_to_grouped_bar(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "category\tgroup\tvalue",
                    "A\tg1\t1.0",
                    "A\tg2\t2.0",
                    "B\tg1\t3.0",
                    "B\tg2\t4.0",
                ]
            ),
            "grouped bar chart",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "bar-group")
        self.assertIn("grouped_category_value", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["secondary_category"], "group")

    def test_grouped_distribution_routes_to_grouped_boxplot(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "condition\tclass\tmeasurement",
                    "A\tcontrol\t1.0",
                    "A\tcase\t2.0",
                    "A\tcase\t2.4",
                    "B\tcontrol\t3.0",
                    "B\tcontrol\t3.3",
                    "B\tcase\t4.0",
                ]
            ),
            "grouped boxplot comparing measurement distributions by condition and class",
        )
        top = payload["recommendations"][0]
        self.assertEqual(top["id"], "boxplot-group")
        self.assertEqual(top["confidence"], "high")
        self.assertIn("grouped_distribution", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["category"], "condition")
        self.assertEqual(payload["input_profile"]["role_mapping"]["secondary_category"], "class")
        self.assertNotIn("paired_distribution", payload["input_profile"]["shapes"])

    def test_uncertainty_column_routes_to_errorbar_chart(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "category\tvalue\tse",
                    "A\t1.2\t0.10",
                    "B\t1.8\t0.20",
                    "C\t1.1\t0.15",
                ]
            ),
            "bar chart with error bars",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "bar-errorbar")
        self.assertIn("category_uncertainty", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["uncertainty"], "se")

    def test_paired_distribution_routes_to_paired_boxplot(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "subject\tcondition\tvalue",
                    "s1\tpre\t1.0",
                    "s1\tpost\t2.0",
                    "s2\tpre\t1.5",
                    "s2\tpost\t2.1",
                ]
            ),
            "paired boxplot before after",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "boxplot-paired")
        self.assertIn("paired_distribution", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["pair_id"], "subject")

    def test_grouped_xy_observations_route_to_grouped_scatter(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "x\ty\tgroup",
                    "1\t2\tA",
                    "2\t3\tA",
                    "3\t2\tB",
                ]
            ),
            "grouped scatter",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "scatter-group")
        self.assertIn("two_numeric_observation", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["category"], "group")

    def test_parallel_sets_table_routes_to_parallel_sets_template(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "tissue\tcluster\tresponse\tn",
                    "Liver\tC1\tR\t12",
                    "Liver\tC2\tNR\t8",
                    "Tumor\tC1\tR\t5",
                ]
            ),
            "parallel sets alluvial categorical axes",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "sankey-parallel-sets")
        self.assertIn("parallel_sets_table", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["count"], "n")

    def test_numeric_matrix_routes_to_dendrogram_when_tree_clustering_is_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "sample\tgroup\tf1\tf2\tf3",
                    "s1\tA\t1\t2\t3",
                    "s2\tA\t2\t1\t4",
                    "s3\tB\t5\t4\t3",
                ]
            ),
            "sample clustering dendrogram",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "tree-dendrogram")
        self.assertIn("dendrogram_matrix", payload["input_profile"]["shapes"])

    def test_hierarchy_with_values_routes_to_sunburst_when_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "parent\tname\tpath\tvalue",
                    "\troot\troot\t10",
                    "root\tA\troot/A\t4",
                    "root\tB\troot/B\t6",
                ]
            ),
            "sunburst concentric hierarchy",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "sunburst-basic")
        self.assertIn("hierarchy_area", payload["input_profile"]["shapes"])

    def test_enrichment_ratio_table_routes_to_enrichment_points_when_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "Description\tONTOLOGY\tGeneRatio\tqvalue",
                    "mitotic spindle\tBP\t0.31\t0.0004",
                    "apoptotic process\tBP\t0.24\t0.0020",
                    "DNA repair\tBP\t0.18\t0.0300",
                ]
            ),
            "enrichment bars with gene-ratio points",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "bar-enrichment-points")
        self.assertIn("enrichment_terms", payload["input_profile"]["shapes"])

    def test_average_abundance_fold_change_table_routes_to_ma_plot(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "symbol\tbaseMean\tlog2FoldChange\tpadj\tgroup",
                    "GENE_A\t132.4\t1.2\t0.001\tup",
                    "GENE_B\t48.1\t-0.8\t0.020\tdown",
                    "GENE_C\t9.5\t0.2\t0.600\tstable",
                ]
            ),
            "MA plot average abundance versus fold change",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "scatter-maplot")
        self.assertIn("mean_difference_table", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["average_abundance"], "baseMean")

    def test_three_nonnegative_components_route_to_ternary_when_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "EPI\tTE\tPrE\tGroup",
                    "0.20\t0.70\t0.10\tTE_like",
                    "0.60\t0.20\t0.20\tEPI_like",
                    "0.25\t0.20\t0.55\tPrE_like",
                ]
            ),
            "ternary composition scatter",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "scatter-ternary")
        self.assertIn("ternary_components", payload["input_profile"]["shapes"])

    def test_rank_series_routes_to_bump_chart_when_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "stage\titem\trank",
                    "T1\tA\t1",
                    "T1\tB\t2",
                    "T2\tA\t2",
                    "T2\tB\t1",
                ]
            ),
            "bump chart rank over time",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "line-bump")
        self.assertIn("rank_time_series", payload["input_profile"]["shapes"])

    def test_supplied_class_term_counts_route_to_tree_enrichment_ring(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "from\tto\tCount\tpvalue",
                    "Metabolism\tLipid metabolism\t12\t0.0008",
                    "Metabolism\tAmino acid metabolism\t8\t0.0040",
                    "Signaling\tMAPK pathway\t6\t0.0200",
                ]
            ),
            "classification tree enrichment ring",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "tree-enrichment-ring")
        self.assertIn("classification_enrichment_tree", payload["input_profile"]["shapes"])

    def test_supplied_embedding_with_tracks_routes_to_umap_circos_when_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "umap_1\tumap_2\tcelltype\ttimepoint\tcondition",
                    "1.0\t2.0\tT_cell\tD0\tcontrol",
                    "1.3\t2.2\tT_cell\tD1\ttreated",
                    "-0.4\t0.6\tB_cell\tD0\tcontrol",
                ]
            ),
            "UMAP circos with categorical tracks",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "scatter-umap-circos")
        self.assertIn("embedding_with_tracks", payload["input_profile"]["shapes"])

    def test_interval_timeline_routes_to_swimmer_when_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "patient\ttreatment\tstart\tend\tstatus",
                    "P1\tDrug A\t0\t42\tresponse",
                    "P1\tDrug B\t43\t80\tongoing",
                    "P2\tDrug A\t0\t35\tstop",
                ]
            ),
            "swimmer plot treatment lanes",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "bar-swimmer")
        self.assertIn("interval_timeline", payload["input_profile"]["shapes"])

    def test_flow_table_routes_to_chord_when_chord_is_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "from\tto\tvalue",
                    "DC\tCD4\t42",
                    "DC\tCD8\t36",
                    "Mono\tCD4\t22",
                ]
            ),
            "weighted chord flow graph-chord",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "graph-chord")
        self.assertIn("flow_table", payload["input_profile"]["shapes"])

    def test_node_table_uses_link_sidecar_for_node_link_graphs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            nodes = root / "nodes.tsv"
            nodes.write_text(
                "\n".join(
                    [
                        "name\tx\ty\tgroup",
                        "A\t0\t0\tmodule_1",
                        "B\t1\t1\tmodule_1",
                        "C\t2\t0\tmodule_2",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "links.tsv").write_text(
                "\n".join(
                    [
                        "source\ttarget\tvalue",
                        "A\tB\t1.0",
                        "A\tC\t0.5",
                    ]
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROUTER),
                    "--input",
                    str(nodes),
                    "--query",
                    "basic node-link network with supplied node coordinates",
                    "--json",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["recommendations"][0]["id"], "graph-basic")
        self.assertIn("node_link_sidecars", payload["input_profile"]["sidecar_shapes"])
        self.assertEqual(payload["input_profile"]["sidecar_role_mapping"]["source_entity"], "links.tsv:source")

    def test_signed_edge_table_routes_to_arc_when_arc_is_requested(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "from\tto\tcorr",
                    "A\tB\t0.60",
                    "A\tC\t-0.40",
                    "B\tC\t0.20",
                ]
            ),
            "linear arc diagram signed network",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "graph-arc")
        self.assertIn("signed_network_edges", payload["input_profile"]["shapes"])

    def test_oncoprint_event_table_routes_to_oncoprint(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "gene\tsample\talteration",
                    "TP53\tP01\tMUT",
                    "TP53\tP02\tAMP",
                    "CTNNB1\tP01\tDEL",
                ]
            ),
            "oncoprint gene sample alteration",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "heatmap-oncoprint")
        self.assertIn("oncoprint_events", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["alteration_type"], "alteration")

    def test_mutation_energy_matrix_routes_to_mutation_energy_heatmap(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "site\tA\tC\tD\tE\tF\tG\tH\tI\tK\tL",
                    "Y14\t0.1\t0.2\t-0.1\t0.3\t0.1\t0.2\t0.4\t0.1\t0.2\t0.3",
                    "F18\t-0.2\t0.1\t0.0\t0.2\t0.3\t0.1\t0.2\t0.2\t0.5\t0.4",
                ]
            ),
            "mutation energy heatmap ddG",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "heatmap-mutation-energy")
        self.assertIn("mutation_energy_matrix", payload["input_profile"]["shapes"])

    def test_group_split_matrix_routes_to_circos_split_heatmap(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "Gene\tGroup\tqval\tA\tB\tC\tD",
                    "G1\tUp\t0.001\t1\t2\t3\t4",
                    "G2\tDown\t0.020\t2\t3\t1\t2",
                    "G3\tUp\t0.010\t2\t1\t3\t1",
                ]
            ),
            "circos split heatmap q-value track",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "heatmap-circos-split")
        self.assertIn("group_split_matrix", payload["input_profile"]["shapes"])
        self.assertEqual(payload["input_profile"]["role_mapping"]["significance"], "qval")

    def test_expression_matrix_uses_enrichment_zoom_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            table = root / "expression.tsv"
            table.write_text(
                "\n".join(
                    [
                        "gene\tN1\tN2\tT1\tT2",
                        "G1\t1\t2\t5\t6",
                        "G2\t2\t1\t4\t5",
                        "G3\t5\t6\t1\t2",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "rowInfo.tsv").write_text("gene\tdirect\nG1\tUp\nG2\tUp\nG3\tDown\n", encoding="utf-8")
            (root / "colInfo.tsv").write_text("sample\tgroup\nN1\tNormal\nN2\tNormal\nT1\tTumor\nT2\tTumor\n", encoding="utf-8")
            (root / "enrichment.tsv").write_text(
                "database\tChange\tDescription\tp.adjust\nGO\tUp\tcell cycle\t0.001\nGO\tDown\tcell death\t0.02\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROUTER),
                    "--input",
                    str(table),
                    "--query",
                    "DE expression heatmap with aligned enrichment zooms",
                    "--json",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
        payload = json.loads(proc.stdout)
        self.assertEqual(payload["recommendations"][0]["id"], "heatmap-enrichment-zoom")
        self.assertIn("enrichment_zoom_sidecars", payload["input_profile"]["sidecar_shapes"])
        alignment = payload["input_profile"]["sidecar_alignment"]
        self.assertEqual(alignment["status"], "ok")
        self.assertEqual(
            {(check["sidecar"], check["relationship"]) for check in alignment["checks"]},
            {("colInfo.tsv", "matrix_columns"), ("rowInfo.tsv", "matrix_rows")},
        )

    def test_misaligned_expression_sidecars_reduce_route_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            table = root / "expression.tsv"
            table.write_text(
                "\n".join(
                    [
                        "gene\tN1\tN2\tT1\tT2",
                        "G1\t1\t2\t5\t6",
                        "G2\t2\t1\t4\t5",
                        "G3\t5\t6\t1\t2",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "rowInfo.tsv").write_text("gene\tdirect\nX1\tUp\nX2\tDown\n", encoding="utf-8")
            (root / "colInfo.tsv").write_text("sample\tgroup\nN1\tNormal\nX2\tOther\n", encoding="utf-8")
            (root / "enrichment.tsv").write_text(
                "database\tChange\tDescription\tp.adjust\nGO\tUp\tcell cycle\t0.001\nGO\tDown\tcell death\t0.02\n",
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROUTER),
                    "--input",
                    str(table),
                    "--query",
                    "DE expression heatmap with aligned enrichment zooms",
                    "--json",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
        payload = json.loads(proc.stdout)
        alignment = payload["input_profile"]["sidecar_alignment"]
        self.assertEqual(alignment["status"], "error")
        row_check = next(check for check in alignment["checks"] if check["sidecar"] == "rowInfo.tsv")
        self.assertEqual(row_check["status"], "error")
        self.assertEqual(row_check["overlap_count"], 0)
        top = payload["recommendations"][0]
        if top["id"] == "heatmap-enrichment-zoom":
            self.assertNotEqual(top["confidence"], "high")
            self.assertTrue(any("sidecar alignment" in risk for risk in top["risks"]))

    def test_node_link_sidecars_report_endpoint_alignment(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = pathlib.Path(tmpdir)
            nodes = root / "nodes.tsv"
            nodes.write_text(
                "\n".join(
                    [
                        "name\tx\ty\tgroup",
                        "A\t0\t0\tmodule_1",
                        "B\t1\t1\tmodule_1",
                        "C\t2\t0\tmodule_2",
                    ]
                ),
                encoding="utf-8",
            )
            (root / "links.tsv").write_text(
                "\n".join(
                    [
                        "source\ttarget\tvalue",
                        "A\tB\t1.0",
                        "A\tD\t0.5",
                    ]
                ),
                encoding="utf-8",
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROUTER),
                    "--input",
                    str(nodes),
                    "--query",
                    "basic node-link network with supplied node coordinates",
                    "--json",
                ],
                check=True,
                text=True,
                capture_output=True,
            )
        payload = json.loads(proc.stdout)
        alignment = payload["input_profile"]["sidecar_alignment"]
        self.assertEqual(alignment["status"], "warning")
        link_check = next(check for check in alignment["checks"] if check["sidecar"] == "links.tsv")
        self.assertEqual(link_check["relationship"], "node_link_endpoints")
        self.assertEqual(link_check["missing_count"], 1)
        self.assertEqual(link_check["missing_examples"], ["D"])

    def test_genomic_locus_table_routes_to_ideogram_loci(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "chr\tstart\tend\tgene\tcategory",
                    "chr1\t100\t200\tA\tkinase",
                    "chr2\t300\t420\tB\tTF",
                ]
            ),
            "gene loci on ideogram",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "ideogram-loci")
        self.assertIn("genomic_locus_table", payload["input_profile"]["shapes"])

    def test_protein_mutation_table_routes_to_ideogram_lollipop(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "aa\tclass\tn\tlabel",
                    "13\tMissense\t1\t",
                    "22\tTruncating\t2\tHotspot",
                ]
            ),
            "protein lollipop mutation",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "ideogram-lollipop")
        self.assertIn("protein_lollipop_table", payload["input_profile"]["shapes"])

    def test_synteny_block_table_routes_to_synteny_and_not_loci(self) -> None:
        payload = self.run_router(
            "\n".join(
                [
                    "chr1\tstart1\tend1\tchr2\tstart2\tend2\tgroup",
                    "Q1\t100\t200\tT1\t500\t610\tblockA",
                    "Q2\t300\t450\tT2\t700\t820\tblockB",
                ]
            ),
            "synteny circos",
        )
        self.assertEqual(payload["recommendations"][0]["id"], "ideogram-synteny")
        self.assertIn("synteny_blocks", payload["input_profile"]["shapes"])
        self.assertNotIn("genomic_locus_table", payload["input_profile"]["shapes"])

    def test_contract_batch_increases_catalog_coverage_without_catalog_errors(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--json"],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(proc.stdout)
        self.assertGreaterEqual(payload["coverage"]["contracted"], 152)
        self.assertEqual(payload["coverage"]["coverage_ratio"], 1.0)
        self.assertFalse(payload["errors"])


class OmicsVisualizationContractTests(unittest.TestCase):
    def test_template_contracts_validate_against_catalog_paths(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), "--json"],
            check=True,
            text=True,
            capture_output=True,
        )
        payload = json.loads(proc.stdout)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["template_count"], 152)
        self.assertEqual(payload["catalog_template_count"], 152)
        self.assertEqual(payload["coverage"]["catalog_total"], 152)
        self.assertEqual(payload["coverage"]["contracted"], 152)
        families = {row["family"] for row in payload["coverage"]["by_family"]}
        self.assertIn("scatter", families)
        self.assertIn("heatmap", families)

    def test_contract_validator_can_fail_on_required_coverage_floor(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            contracts_path = pathlib.Path(tmpdir) / "template_contracts.json"
            contracts = json.loads((ROOT / "skills" / "omics-visualization" / "references" / "template_contracts.json").read_text())
            contracts["templates"] = contracts["templates"][:-1]
            contracts_path.write_text(json.dumps(contracts), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(VALIDATOR), "--contracts", str(contracts_path), "--fail-under", "1.0", "--json"],
                check=False,
                text=True,
                capture_output=True,
            )
        payload = json.loads(proc.stdout)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(payload["ok"])
        self.assertTrue(any("below required" in error for error in payload["errors"]))


class OmicsVisualizationSinglePlotQATests(unittest.TestCase):
    def run_qa(self, path: pathlib.Path) -> dict:
        proc = subprocess.run(
            [sys.executable, str(QA), str(path), "--json"],
            check=True,
            text=True,
            capture_output=True,
        )
        return json.loads(proc.stdout)

    def test_png_dimensions_are_read_from_ihdr(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            png_path = pathlib.Path(tmpdir) / "plot.png"
            png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + struct.pack(">II", 120, 80))
            payload = self.run_qa(png_path)
        self.assertTrue(payload["ok"])
        dimensions = next(check for check in payload["checks"] if check["name"] == "format")
        self.assertEqual(dimensions["width"], 120)
        self.assertEqual(dimensions["height"], 80)

    def test_svg_dimensions_are_read_from_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            svg_path = pathlib.Path(tmpdir) / "plot.svg"
            svg_path.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="80"></svg>', encoding="utf-8")
            payload = self.run_qa(svg_path)
        self.assertTrue(payload["ok"])
        dimensions = next(check for check in payload["checks"] if check["name"] == "format")
        self.assertEqual(dimensions["width"], 100.0)
        self.assertEqual(dimensions["height"], 80.0)


if __name__ == "__main__":
    unittest.main()
