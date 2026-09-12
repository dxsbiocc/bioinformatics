"""Front-end compatible record envelopes for Human Protein Atlas genes."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import HPA_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def hpa_gene_record(payload: JsonObject, *, base_url: str = HPA_BASE_URL) -> JsonObject:
    normalized = normalize_gene(payload, base_url=base_url)
    ensembl_id = normalized["ensembl"] or normalized["gene"]
    title = f"{normalized['gene']} - {normalized['description']}" if normalized["description"] else normalized["gene"]
    links = gene_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.gene",
        "record_type": "hpa_gene",
        "database": "hpa",
        "id": ensembl_id,
        "stable_id": ensembl_id,
        "label": normalized["gene"] or ensembl_id,
        "title": title or ensembl_id,
        "description": normalized["description"] or "Human Protein Atlas gene expression and protein evidence record",
        "url": normalized["url"],
        "icon": "human-protein-atlas",
        "identifiers": gene_identifiers(normalized),
        "links": links,
        "display": {
            "component": "gene",
            "chip_label": normalized["gene"] or ensembl_id,
            "icon": "human-protein-atlas",
            "title": title or ensembl_id,
            "subtitle": gene_subtitle(normalized),
            "description": normalized["description"] or "Human Protein Atlas gene record",
            "metadata": gene_metadata(normalized),
            "badges": compact_badges(
                ("HPA", "source"),
                (normalized["gene"], "identifier"),
                (normalized["evidence"], "status"),
                (normalized["rna_tissue_specificity"], "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title or ensembl_id,
                "subtitle": gene_subtitle(normalized),
                "icon": "human-protein-atlas",
                "fields": compact_fields(
                    ("Gene", normalized["gene"]),
                    ("Ensembl", normalized["ensembl"]),
                    ("UniProt", ", ".join(normalized["uniprot"][:5])),
                    ("Evidence", normalized["evidence"]),
                    ("Subcellular location", ", ".join(normalized["subcellular_location"][:5])),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": gene_sections(normalized),
            "previews": gene_previews(normalized, links),
        },
        "related": {
            "uniprot": normalized["uniprot"],
            "protein_classes": normalized["protein_classes"],
            "subcellular_location": normalized["subcellular_location"],
            "cancer_prognostics": normalized["cancer_prognostics"],
        },
        "data": normalized,
    }


def normalize_gene(payload: JsonObject, *, base_url: str) -> JsonObject:
    gene = normalize_space(payload.get("Gene"))
    ensembl = normalize_space(payload.get("Ensembl")).upper()
    uniprot = unique_texts(safe_list(payload.get("Uniprot")))
    url = hpa_gene_url(ensembl, gene, base_url)
    normalized: JsonObject = {
        "gene": gene,
        "synonyms": unique_texts(safe_list(payload.get("Gene synonym"))),
        "ensembl": ensembl,
        "description": normalize_space(payload.get("Gene description")),
        "uniprot": uniprot,
        "chromosome": normalize_space(payload.get("Chromosome")),
        "position": normalize_space(payload.get("Position")),
        "protein_classes": unique_texts(safe_list(payload.get("Protein class"))),
        "biological_process": unique_texts(safe_list(payload.get("Biological process"))),
        "molecular_function": unique_texts(safe_list(payload.get("Molecular function"))),
        "disease_involvement": unique_texts(safe_list(payload.get("Disease involvement"))),
        "evidence": normalize_space(payload.get("Evidence") or payload.get("HPA evidence")),
        "rna_tissue_specificity": normalize_space(payload.get("RNA tissue specificity")),
        "rna_tissue_distribution": normalize_space(payload.get("RNA tissue distribution")),
        "rna_single_cell_type_specificity": normalize_space(payload.get("RNA single cell type specificity")),
        "rna_single_cell_type_distribution": normalize_space(payload.get("RNA single cell type distribution")),
        "rna_cancer_specificity": normalize_space(payload.get("RNA cancer specificity")),
        "rna_cancer_distribution": normalize_space(payload.get("RNA cancer distribution")),
        "rna_blood_cell_specificity": normalize_space(payload.get("RNA blood cell specificity")),
        "rna_cell_line_specificity": normalize_space(payload.get("RNA cell line specificity")),
        "protein_tissue_specificity": normalize_space(payload.get("Protein tissue specificity")),
        "protein_tissue_distribution": normalize_space(payload.get("Protein tissue distribution")),
        "protein_cell_type_specificity": normalize_space(payload.get("Protein cell type specificity")),
        "protein_cell_type_distribution": normalize_space(payload.get("Protein cell type distribution")),
        "subcellular_location": unique_texts(safe_list(payload.get("Subcellular location"))),
        "subcellular_main_location": unique_texts(safe_list(payload.get("Subcellular main location"))),
        "subcellular_additional_location": unique_texts(safe_list(payload.get("Subcellular additional location"))),
        "antibodies": unique_texts(safe_list(payload.get("Antibody"))),
        "reliability_ih": normalize_space(payload.get("Reliability (IH)")),
        "reliability_if": normalize_space(payload.get("Reliability (IF)")),
        "interactions": int_or_zero(payload.get("Interactions")),
        "url": url,
        "api_url": f"{base_url.rstrip('/')}/{urllib.parse.quote(ensembl, safe='')}.json" if ensembl else "",
        "search_url": f"{base_url.rstrip('/')}/search/{urllib.parse.quote(gene or ensembl, safe='')}" if gene or ensembl else "",
        "cancer_prognostics": cancer_prognostics(payload),
    }
    return normalized


def cancer_prognostics(payload: JsonObject) -> list[JsonObject]:
    rows = []
    for key, value in payload.items():
        if not key.startswith("Cancer prognostics - ") or not isinstance(value, dict):
            continue
        rows.append(
            {
                "cancer": key.replace("Cancer prognostics - ", ""),
                "prognostic_type": normalize_space(value.get("prognostic type")),
                "prognostic": normalize_space(value.get("prognostic")),
                "is_prognostic": value.get("is_prognostic") if isinstance(value.get("is_prognostic"), bool) else None,
                "p_value": normalize_space(value.get("p_val")),
            }
        )
    return rows


def gene_sections(gene: JsonObject) -> list[JsonObject]:
    sections = [
        {"key": "overview", "title": "Overview", "kind": "table", "rows": gene_metadata(gene)},
        {"key": "expression", "title": "Expression summary", "kind": "table", "rows": expression_rows(gene)},
    ]
    if gene["cancer_prognostics"]:
        sections.append({"key": "cancer_prognostics", "title": "Cancer prognostics", "kind": "table", "rows": gene["cancer_prognostics"]})
    if gene["protein_classes"]:
        sections.append({"key": "protein_classes", "title": "Protein classes", "kind": "list", "items": gene["protein_classes"]})
    return sections


def gene_previews(gene: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "table",
            "title": "Expression summary",
            "section_key": "expression",
            "data": {"columns": ["label", "value"], "rows": expression_rows(gene)},
        }
    ]
    if gene["cancer_prognostics"]:
        previews.append(
            {
                "kind": "table",
                "title": "Cancer prognostics",
                "section_key": "cancer_prognostics",
                "data": {"columns": ["cancer", "prognostic", "prognostic_type", "p_value"], "rows": gene["cancer_prognostics"]},
            }
        )
    previews.append(
        {
            "kind": "xref_groups",
            "title": "Identifiers and HPA links",
            "actions": display_actions(links),
            "data": {"groups": xref_groups(gene)},
        }
    )
    return previews


def gene_links(gene: JsonObject) -> list[JsonObject]:
    links = [{"label": "Open Human Protein Atlas", "url": gene["url"], "kind": "external", "primary": True}]
    if gene["api_url"]:
        links.append({"label": "Open HPA JSON", "url": gene["api_url"], "kind": "external"})
    if gene["ensembl"]:
        links.append({"label": "Open Ensembl", "url": f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={gene['ensembl']}", "kind": "external"})
    for accession in gene["uniprot"][:3]:
        links.append({"label": f"Open UniProt {accession}", "url": f"https://www.uniprot.org/uniprotkb/{urllib.parse.quote(accession, safe='')}/entry", "kind": "external"})
    return links


def gene_identifiers(gene: JsonObject) -> JsonObject:
    identifiers: JsonObject = {}
    if gene["ensembl"]:
        identifiers["ensembl"] = {"namespace": "ensembl.gene", "id": gene["ensembl"], "label": gene["ensembl"], "url": gene["url"]}
    if gene["gene"]:
        identifiers["symbol"] = {"namespace": "hgnc.symbol", "id": gene["gene"], "label": gene["gene"], "url": gene["url"]}
    if gene["uniprot"]:
        identifiers["uniprot"] = {"namespace": "uniprot", "id": gene["uniprot"][0], "label": gene["uniprot"][0], "url": f"https://www.uniprot.org/uniprotkb/{gene['uniprot'][0]}/entry"}
    return identifiers


def gene_metadata(gene: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Gene", gene["gene"]),
        ("Ensembl", gene["ensembl"]),
        ("Description", gene["description"]),
        ("UniProt", ", ".join(gene["uniprot"][:5])),
        ("Chromosome", gene["chromosome"]),
        ("Position", gene["position"]),
        ("Evidence", gene["evidence"]),
        ("Interactions", str(gene["interactions"]) if gene["interactions"] else ""),
        ("Subcellular location", ", ".join(gene["subcellular_location"][:5])),
        ("Antibodies", ", ".join(gene["antibodies"][:5])),
        ("API", gene["api_url"]),
    )


def expression_rows(gene: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("RNA tissue specificity", gene["rna_tissue_specificity"]),
        ("RNA tissue distribution", gene["rna_tissue_distribution"]),
        ("RNA single-cell type specificity", gene["rna_single_cell_type_specificity"]),
        ("RNA single-cell type distribution", gene["rna_single_cell_type_distribution"]),
        ("RNA cancer specificity", gene["rna_cancer_specificity"]),
        ("RNA cancer distribution", gene["rna_cancer_distribution"]),
        ("RNA blood cell specificity", gene["rna_blood_cell_specificity"]),
        ("RNA cell-line specificity", gene["rna_cell_line_specificity"]),
        ("Protein tissue specificity", gene["protein_tissue_specificity"]),
        ("Protein tissue distribution", gene["protein_tissue_distribution"]),
        ("Protein cell-type specificity", gene["protein_cell_type_specificity"]),
        ("Protein cell-type distribution", gene["protein_cell_type_distribution"]),
        ("Reliability IH", gene["reliability_ih"]),
        ("Reliability IF", gene["reliability_if"]),
    )


def xref_groups(gene: JsonObject) -> list[JsonObject]:
    groups = []
    if gene["ensembl"]:
        groups.append({"source": "Ensembl", "items": [{"label": gene["ensembl"], "id": gene["ensembl"], "url": f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={gene['ensembl']}"}]})
    if gene["uniprot"]:
        groups.append({"source": "UniProt", "items": [{"label": item, "id": item, "url": f"https://www.uniprot.org/uniprotkb/{item}/entry"} for item in gene["uniprot"]]})
    if gene["protein_classes"]:
        groups.append({"source": "Protein classes", "items": [{"label": item, "id": item, "url": ""} for item in gene["protein_classes"]]})
    if gene["subcellular_location"]:
        groups.append({"source": "Subcellular location", "items": [{"label": item, "id": item, "url": ""} for item in gene["subcellular_location"]]})
    return groups


def gene_subtitle(gene: JsonObject) -> str:
    parts = ["Human Protein Atlas"]
    if gene["evidence"]:
        parts.append(gene["evidence"])
    if gene["rna_tissue_specificity"]:
        parts.append(gene["rna_tissue_specificity"])
    return " | ".join(parts)


def hpa_gene_url(ensembl: str, gene: str, base_url: str) -> str:
    if ensembl:
        return f"{base_url.rstrip('/')}/{urllib.parse.quote(ensembl, safe='')}-{urllib.parse.quote(gene, safe='')}" if gene else f"{base_url.rstrip('/')}/{urllib.parse.quote(ensembl, safe='')}"
    return f"{base_url.rstrip('/')}/search/{urllib.parse.quote(gene, safe='')}"


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    fields = []
    for label, value in pairs:
        text = normalize_space(value)
        if text:
            fields.append({"label": label, "value": text})
    return fields


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    badges = []
    for label, kind in pairs:
        text = normalize_space(label)
        if text:
            badges.append({"label": text, "kind": kind})
    return badges


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    actions = []
    for link in links:
        url = normalize_space(link.get("url"))
        label = normalize_space(link.get("label"))
        if url.startswith(("http://", "https://")) and label:
            actions.append({"label": label, "url": url, "kind": normalize_space(link.get("kind") or "external")})
    return actions


def unique_texts(values: list[Any]) -> list[str]:
    seen = set()
    out = []
    for value in values:
        text = normalize_space(value)
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
