"""Front-end compatible record envelopes for GWAS Catalog results."""

from __future__ import annotations

import urllib.parse

from .constants import (
    GWAS_REST_BASE_URL,
    GWAS_WEBSITE_BASE_URL,
    NCBI_PUBMED_BASE_URL,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import normalize_space, safe_list


def gwas_variant_record(
    *,
    rs_id: str,
    snp: JsonObject,
    associations: list[JsonObject],
    total: int,
    max_results: int,
    website_base_url: str = GWAS_WEBSITE_BASE_URL,
    api_base_url: str = GWAS_REST_BASE_URL,
) -> JsonObject:
    normalized = {
        "rs_id": rs_id,
        "snp": normalize_snp(snp, rs_id, api_base_url=api_base_url),
        "associations": normalize_associations(associations, max_results=max_results),
        "total_associations": total,
        "truncated": total > len(associations),
        "url": gwas_search_url(rs_id, website_base_url),
        "api_url": f"{api_base_url.rstrip('/')}/single-nucleotide-polymorphisms/{urllib.parse.quote(rs_id)}",
    }
    links = shared_links(normalized["url"], normalized["api_url"])
    title = rs_id
    description = variant_description(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "genomic.variant",
        "record_type": "gwas_variant_associations",
        "database": "gwas_catalog",
        "id": rs_id,
        "stable_id": f"GWAS:{rs_id}",
        "label": rs_id,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "gwas-catalog",
        "identifiers": variant_identifiers(normalized),
        "links": links,
        "display": {
            "component": "variant",
            "chip_label": rs_id,
            "icon": "gwas-catalog",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    normalized["snp"].get("location"),
                    normalized["snp"].get("most_severe_consequence"),
                    f"{total} associations" if total else "",
                ]
                if part
            ),
            "description": description,
            "metadata": variant_metadata(normalized),
            "badges": compact_badges(
                ("GWAS Catalog", "source"),
                (rs_id, "identifier"),
                (normalized["snp"].get("most_severe_consequence"), "consequence"),
                (f"{total} associations" if total else "", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "gwas-catalog",
                "fields": compact_fields(
                    ("Variant", rs_id),
                    ("Location", normalized["snp"].get("location")),
                    ("Alleles", normalized["snp"].get("alleles")),
                    ("Mapped genes", ", ".join(normalized["snp"].get("mapped_genes", []))),
                    ("Most severe consequence", normalized["snp"].get("most_severe_consequence")),
                    ("Associations", str(total) if total else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": association_sections(normalized),
            "previews": association_previews(normalized, links, title="GWAS associations"),
        },
        "related": {
            "associations": normalized["associations"],
            "citations": citation_rows(normalized["associations"]),
        },
        "data": normalized,
    }


def gwas_gene_record(
    *,
    gene: str,
    associations: list[JsonObject],
    total: int,
    max_results: int,
    website_base_url: str = GWAS_WEBSITE_BASE_URL,
    api_base_url: str = GWAS_REST_BASE_URL,
) -> JsonObject:
    normalized = {
        "gene": gene,
        "associations": normalize_associations(associations, max_results=max_results),
        "total_associations": total,
        "truncated": total > len(associations),
        "url": gwas_search_url(gene, website_base_url),
        "api_url": f"{api_base_url.rstrip('/')}/associations?mapped_gene={urllib.parse.quote(gene)}",
    }
    links = shared_links(normalized["url"], normalized["api_url"])
    description = f"GWAS Catalog associations mapped to {gene}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "gene",
        "record_type": "gwas_gene_associations",
        "database": "gwas_catalog",
        "id": gene,
        "stable_id": f"GWAS:gene:{gene}",
        "label": gene,
        "title": gene,
        "description": description,
        "url": normalized["url"],
        "icon": "gwas-catalog",
        "identifiers": gene_identifiers(normalized),
        "links": links,
        "display": {
            "component": "gene",
            "chip_label": gene,
            "icon": "gwas-catalog",
            "title": gene,
            "subtitle": f"{total} GWAS associations" if total else "No associations returned",
            "description": description,
            "metadata": compact_fields(
                ("Gene", gene),
                ("Associations", str(total) if total else "0"),
                ("Top traits", ", ".join(top_traits(normalized["associations"]))),
            ),
            "badges": compact_badges(
                ("GWAS Catalog", "source"),
                (gene, "gene"),
                (f"{total} associations" if total else "", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": gene,
                "subtitle": description,
                "icon": "gwas-catalog",
                "fields": compact_fields(
                    ("Gene", gene),
                    ("Associations", str(total) if total else "0"),
                    ("Top traits", ", ".join(top_traits(normalized["associations"]))),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": association_sections(normalized),
            "previews": association_previews(normalized, links, title="Mapped-gene associations"),
        },
        "related": {
            "associations": normalized["associations"],
            "citations": citation_rows(normalized["associations"]),
        },
        "data": normalized,
    }


def gwas_trait_record(
    *,
    trait: str,
    associations: list[JsonObject],
    studies: list[JsonObject],
    association_total: int,
    study_total: int,
    max_results: int,
    website_base_url: str = GWAS_WEBSITE_BASE_URL,
    api_base_url: str = GWAS_REST_BASE_URL,
) -> JsonObject:
    normalized = {
        "trait": trait,
        "associations": normalize_associations(associations, max_results=max_results),
        "studies": normalize_studies(studies, max_results=max_results),
        "total_associations": association_total,
        "total_studies": study_total,
        "truncated_associations": association_total > len(associations),
        "truncated_studies": study_total > len(studies),
        "url": gwas_search_url(trait, website_base_url),
        "api_url": f"{api_base_url.rstrip('/')}/associations?efo_trait={urllib.parse.quote(trait)}",
    }
    links = shared_links(normalized["url"], normalized["api_url"])
    title = f"GWAS trait search: {trait}"
    description = f"{association_total} associations and {study_total} studies returned for {trait}"
    previews = association_previews(normalized, links, title="Trait associations")
    if normalized["studies"]:
        previews.append(studies_preview(normalized, links))
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "gwas_trait_search",
        "database": "gwas_catalog",
        "id": trait,
        "stable_id": f"GWAS:trait:{trait}",
        "label": trait,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "gwas-catalog",
        "identifiers": {
            "gwas_trait_query": {
                "namespace": "gwas_trait_query",
                "id": trait,
                "label": trait,
                "url": normalized["url"],
            }
        },
        "links": links,
        "display": {
            "component": "dataset",
            "chip_label": trait,
            "icon": "gwas-catalog",
            "title": title,
            "subtitle": description,
            "description": description,
            "metadata": compact_fields(
                ("Trait query", trait),
                ("Associations", str(association_total)),
                ("Studies", str(study_total)),
                ("Top traits", ", ".join(top_traits(normalized["associations"]))),
            ),
            "badges": compact_badges(
                ("GWAS Catalog", "source"),
                ("trait search", "record_type"),
                (f"{association_total} associations", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "gwas-catalog",
                "fields": compact_fields(
                    ("Trait query", trait),
                    ("Associations", str(association_total)),
                    ("Studies", str(study_total)),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": trait_sections(normalized),
            "previews": previews,
        },
        "related": {
            "associations": normalized["associations"],
            "studies": normalized["studies"],
            "citations": citation_rows(normalized["associations"]),
        },
        "data": normalized,
    }


def normalize_snp(snp: JsonObject, rs_id: str, *, api_base_url: str) -> JsonObject:
    locations = []
    for item in safe_list(snp.get("locations")):
        if not isinstance(item, dict):
            continue
        chrom = normalize_space(item.get("chromosome_name"))
        pos = normalize_space(item.get("chromosome_position"))
        region = item.get("region") if isinstance(item.get("region"), dict) else {}
        locations.append(
            {
                "chromosome": chrom,
                "position": pos,
                "region": normalize_space(region.get("name")),
                "location": f"{chrom}:{pos}" if chrom and pos else "",
            }
        )
    return {
        "rs_id": normalize_space(snp.get("rs_id")) or rs_id,
        "merged": snp.get("merged"),
        "functional_class": normalize_space(snp.get("functional_class")),
        "last_update_date": normalize_space(snp.get("last_update_date")),
        "alleles": normalize_space(snp.get("alleles")),
        "most_severe_consequence": normalize_space(snp.get("most_severe_consequence")),
        "mapped_genes": [normalize_space(item) for item in safe_list(snp.get("mapped_genes")) if normalize_space(item)],
        "locations": locations,
        "location": locations[0]["location"] if locations else "",
        "api_url": f"{api_base_url.rstrip('/')}/single-nucleotide-polymorphisms/{urllib.parse.quote(rs_id)}",
    }


def normalize_associations(value: object, *, max_results: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value)[:max_results]:
        if not isinstance(item, dict):
            continue
        rows.append(normalize_association(item))
    return rows


def normalize_association(item: JsonObject) -> JsonObject:
    association_id = normalize_space(item.get("association_id"))
    pubmed_id = normalize_space(item.get("pubmed_id"))
    accession_id = normalize_space(item.get("accession_id"))
    snp_alleles = normalize_snp_alleles(item.get("snp_allele"))
    return {
        "association_id": association_id,
        "accession_id": accession_id,
        "reported_trait": "; ".join(normalize_space(entry) for entry in safe_list(item.get("reported_trait")) if normalize_space(entry)),
        "efo_traits": normalize_efo_traits(item.get("efo_traits")),
        "mapped_genes": [normalize_space(entry) for entry in safe_list(item.get("mapped_genes")) if normalize_space(entry)],
        "locations": [normalize_space(entry) for entry in safe_list(item.get("locations")) if normalize_space(entry)],
        "rs_ids": [entry["rs_id"] for entry in snp_alleles if entry.get("rs_id")],
        "effect_alleles": [entry["effect_allele"] for entry in snp_alleles if entry.get("effect_allele")],
        "p_value": item.get("p_value"),
        "pvalue_description": normalize_space(item.get("pvalue_description")),
        "beta": normalize_space(item.get("beta")),
        "range": normalize_space(item.get("range")),
        "risk_frequency": normalize_space(item.get("risk_frequency")),
        "pubmed_id": pubmed_id,
        "first_author": normalize_space(item.get("first_author")),
        "association_url": link_href(item, "self"),
        "snp_url": link_href(item, "snp"),
        "pubmed_url": pubmed_url(pubmed_id),
    }


def normalize_snp_alleles(value: object) -> list[JsonObject]:
    alleles = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        alleles.append(
            {
                "rs_id": normalize_space(item.get("rs_id")),
                "effect_allele": normalize_space(item.get("effect_allele")),
            }
        )
    return alleles


def normalize_efo_traits(value: object) -> list[JsonObject]:
    traits = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        efo_id = normalize_space(item.get("efo_id"))
        traits.append(
            {
                "id": efo_id,
                "label": normalize_space(item.get("efo_trait")),
                "url": efo_url(efo_id),
            }
        )
    return traits


def normalize_studies(value: object, *, max_results: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value)[:max_results]:
        if not isinstance(item, dict):
            continue
        pubmed_id = normalize_space(item.get("pubmed_id"))
        accession = normalize_space(item.get("accession_id"))
        rows.append(
            {
                "accession_id": accession,
                "disease_trait": normalize_space(item.get("disease_trait")),
                "efo_traits": normalize_efo_traits(item.get("efo_traits")),
                "initial_sample_size": normalize_space(item.get("initial_sample_size")),
                "replication_sample_size": normalize_space(item.get("replication_sample_size")),
                "pubmed_id": pubmed_id,
                "full_summary_stats_available": item.get("full_summary_stats_available"),
                "full_summary_stats": normalize_space(item.get("full_summary_stats")),
                "study_url": link_href(item, "self"),
                "pubmed_url": pubmed_url(pubmed_id),
            }
        )
    return rows


def association_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "associations",
            "title": "GWAS associations",
            "kind": "table",
            "rows": normalized["associations"],
            "summary": {
                "total": normalized["total_associations"],
                "shown": len(normalized["associations"]),
                "truncated": normalized["truncated"],
            },
        }
    ]
    citations = citation_rows(normalized["associations"])
    if citations:
        sections.append(
            {
                "key": "citations",
                "title": "PubMed evidence",
                "kind": "table",
                "rows": citations,
                "summary": {"shown": len(citations)},
            }
        )
    return sections


def trait_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = association_sections(
        {
            "associations": normalized["associations"],
            "total_associations": normalized["total_associations"],
            "truncated": normalized["truncated_associations"],
        }
    )
    if normalized["studies"]:
        sections.append(
            {
                "key": "studies",
                "title": "GWAS studies",
                "kind": "table",
                "rows": normalized["studies"],
                "summary": {
                    "total": normalized["total_studies"],
                    "shown": len(normalized["studies"]),
                    "truncated": normalized["truncated_studies"],
                },
            }
        )
    return sections


def association_previews(normalized: JsonObject, links: list[JsonObject], *, title: str) -> list[JsonObject]:
    previews = [
        {
            "kind": "table",
            "title": title,
            "provider": "GWAS Catalog",
            "id": normalize_space(normalized.get("rs_id") or normalized.get("gene") or normalized.get("trait")),
            "url": normalized["url"],
            "section_key": "associations",
            "actions": display_actions(links),
            "data": {
                "columns": association_columns(),
                "rows": normalized["associations"],
                "total_rows": normalized["total_associations"],
                "truncated": normalized.get("truncated", normalized.get("truncated_associations", False)),
            },
        }
    ]
    citations = citation_rows(normalized["associations"])
    if citations:
        previews.append(
            {
                "kind": "citation_list",
                "title": "PubMed evidence",
                "provider": "GWAS Catalog",
                "id": normalize_space(normalized.get("rs_id") or normalized.get("gene") or normalized.get("trait")),
                "url": normalized["url"],
                "section_key": "citations",
                "actions": display_actions(links),
                "data": {"citations": citations},
            }
        )
    previews.append(xref_preview(normalized, links))
    return previews


def studies_preview(normalized: JsonObject, links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "table",
        "title": "GWAS studies",
        "provider": "GWAS Catalog",
        "id": normalized["trait"],
        "url": normalized["url"],
        "section_key": "studies",
        "actions": display_actions(links),
        "data": {
            "columns": study_columns(),
            "rows": normalized["studies"],
            "total_rows": normalized["total_studies"],
            "truncated": normalized["truncated_studies"],
        },
    }


def xref_preview(normalized: JsonObject, links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "xref_groups",
        "title": "Cross-reference groups",
        "provider": "GWAS Catalog",
        "id": normalize_space(normalized.get("rs_id") or normalized.get("gene") or normalized.get("trait")),
        "url": normalized["url"],
        "actions": display_actions(links),
        "data": {"groups": xref_groups(normalized)},
    }


def xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [
        {
            "database": "GWAS Catalog",
            "items": [{"id": normalize_space(normalized.get("rs_id") or normalized.get("gene") or normalized.get("trait")), "label": "GWAS Catalog search", "url": normalized["url"]}],
        }
    ]
    efo_items = {}
    pubmed_items = {}
    snp_items = {}
    gene_items = {}
    for association in normalized.get("associations", []):
        for trait in association.get("efo_traits", []):
            if trait.get("id"):
                efo_items[trait["id"]] = {"id": trait["id"], "label": trait.get("label", trait["id"]), "url": trait.get("url", "")}
        if association.get("pubmed_id"):
            pubmed_items[association["pubmed_id"]] = {"id": association["pubmed_id"], "label": f"PMID:{association['pubmed_id']}", "url": association.get("pubmed_url", "")}
        for rs_id in association.get("rs_ids", []):
            snp_items[rs_id] = {"id": rs_id, "label": rs_id, "url": gwas_snp_api_url(rs_id)}
        for gene in association.get("mapped_genes", []):
            gene_items[gene] = {"id": gene, "label": gene, "url": gwas_search_url(gene, GWAS_WEBSITE_BASE_URL)}
    if efo_items:
        groups.append({"database": "EFO traits", "items": list(efo_items.values())})
    if snp_items:
        groups.append({"database": "dbSNP / GWAS SNPs", "items": list(snp_items.values())})
    if gene_items:
        groups.append({"database": "Mapped genes", "items": list(gene_items.values())})
    if pubmed_items:
        groups.append({"database": "PubMed", "items": list(pubmed_items.values())})
    return groups


def citation_rows(associations: list[JsonObject]) -> list[JsonObject]:
    rows = []
    seen: set[str] = set()
    for association in associations:
        pmid = normalize_space(association.get("pubmed_id"))
        if not pmid or pmid in seen:
            continue
        seen.add(pmid)
        rows.append(
            {
                "pmid": pmid,
                "stable_id": f"PMID:{pmid}",
                "first_author": normalize_space(association.get("first_author")),
                "trait": normalize_space(association.get("reported_trait")),
                "accession_id": normalize_space(association.get("accession_id")),
                "url": pubmed_url(pmid),
            }
        )
    return rows


def variant_description(normalized: JsonObject) -> str:
    snp = normalized["snp"]
    parts = [
        snp.get("alleles"),
        snp.get("location"),
        ", ".join(snp.get("mapped_genes", [])),
        f"{normalized['total_associations']} GWAS associations" if normalized["total_associations"] else "",
    ]
    return " | ".join(part for part in parts if part)


def variant_metadata(normalized: JsonObject) -> list[JsonObject]:
    snp = normalized["snp"]
    return compact_fields(
        ("Variant", normalized["rs_id"]),
        ("Location", snp.get("location")),
        ("Alleles", snp.get("alleles")),
        ("Mapped genes", ", ".join(snp.get("mapped_genes", []))),
        ("Most severe consequence", snp.get("most_severe_consequence")),
        ("Associations", str(normalized["total_associations"]) if normalized["total_associations"] else "0"),
    )


def variant_identifiers(normalized: JsonObject) -> JsonObject:
    return {
        "dbsnp": {
            "namespace": "dbsnp",
            "id": normalized["rs_id"],
            "label": normalized["rs_id"],
            "url": normalized["api_url"],
        },
        "gwas_catalog": {
            "namespace": "gwas_catalog",
            "id": normalized["rs_id"],
            "label": f"GWAS:{normalized['rs_id']}",
            "url": normalized["url"],
        },
    }


def gene_identifiers(normalized: JsonObject) -> JsonObject:
    return {
        "gene_symbol": {
            "namespace": "gene_symbol",
            "id": normalized["gene"],
            "label": normalized["gene"],
            "url": normalized["url"],
        },
        "gwas_catalog": {
            "namespace": "gwas_catalog.gene_query",
            "id": normalized["gene"],
            "label": f"GWAS gene:{normalized['gene']}",
            "url": normalized["url"],
        },
    }


def top_traits(associations: list[JsonObject]) -> list[str]:
    traits = []
    seen: set[str] = set()
    for association in associations:
        for trait in association.get("efo_traits", []):
            label = normalize_space(trait.get("label"))
            if label and label not in seen:
                seen.add(label)
                traits.append(label)
        if len(traits) >= 5:
            break
    return traits


def association_columns() -> list[JsonObject]:
    return [
        {"key": "association_id", "label": "Association"},
        {"key": "rs_ids", "label": "SNPs"},
        {"key": "reported_trait", "label": "Reported trait"},
        {"key": "efo_traits", "label": "EFO traits"},
        {"key": "mapped_genes", "label": "Mapped genes"},
        {"key": "p_value", "label": "p-value"},
        {"key": "beta", "label": "Beta / OR"},
        {"key": "pubmed_id", "label": "PMID"},
    ]


def study_columns() -> list[JsonObject]:
    return [
        {"key": "accession_id", "label": "Study"},
        {"key": "disease_trait", "label": "Disease/Trait"},
        {"key": "initial_sample_size", "label": "Initial sample"},
        {"key": "replication_sample_size", "label": "Replication sample"},
        {"key": "pubmed_id", "label": "PMID"},
        {"key": "full_summary_stats_available", "label": "Summary stats"},
    ]


def link_href(item: JsonObject, name: str) -> str:
    links = item.get("_links") if isinstance(item.get("_links"), dict) else {}
    link = links.get(name) if isinstance(links, dict) else None
    return normalize_space(link.get("href")) if isinstance(link, dict) else ""


def shared_links(primary_url: str, api_url: str) -> list[JsonObject]:
    return compact_links(
        link("Open in GWAS Catalog", primary_url, primary=True),
        link("GWAS Catalog API", api_url, kind="related"),
    )


def gwas_search_url(query: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/search?query={urllib.parse.quote(query)}"


def gwas_snp_api_url(rs_id: str) -> str:
    return f"{GWAS_REST_BASE_URL}/single-nucleotide-polymorphisms/{urllib.parse.quote(rs_id)}"


def pubmed_url(pmid: str) -> str:
    return f"{NCBI_PUBMED_BASE_URL.rstrip('/')}/{pmid}/" if pmid else ""


def efo_url(efo_id: str) -> str:
    return f"https://www.ebi.ac.uk/ols4/ontologies/efo/classes/http%253A%252F%252Fwww.ebi.ac.uk%252Fefo%252F{urllib.parse.quote(efo_id)}" if efo_id.startswith("EFO_") else ""


def link(label: str, url: str, *, kind: str = "external", primary: bool = False) -> JsonObject:
    payload: JsonObject = {"label": label, "url": url, "kind": kind}
    if primary:
        payload["primary"] = True
    return payload


def compact_links(*links: JsonObject) -> list[JsonObject]:
    return [item for item in links if normalize_space(item.get("url"))]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [
        {"label": item["label"], "url": item["url"], "kind": item.get("kind", "external"), "primary": item.get("primary", False)}
        for item in links
        if item.get("url")
    ]


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    fields = []
    for label_text, value in pairs:
        text = normalize_space(value)
        if text:
            fields.append({"label": label_text, "value": text})
    return fields


def compact_badges(*pairs: tuple[object, str]) -> list[JsonObject]:
    badges = []
    for label_text, kind in pairs:
        text = normalize_space(label_text)
        if text:
            badges.append({"label": text, "kind": kind})
    return badges

