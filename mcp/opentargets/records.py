"""Front-end compatible record envelopes for Open Targets results."""

from __future__ import annotations

import urllib.parse

from .constants import (
    OPENTARGETS_GRAPHQL_URL,
    OPENTARGETS_WEBSITE_BASE_URL,
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .utils import normalize_space, safe_list

DATASOURCE_LABELS = {
    "cancer_biomarkers": "Cancer Biomarkers",
    "cancer_gene_census": "Cancer Gene Census",
    "chembl": "ChEMBL",
    "clingen": "ClinGen",
    "clinical_precedence": "Clinical Precedence",
    "crispr_screen": "CRISPR screens",
    "europepmc": "Europe PMC",
    "eva": "ClinVar germline",
    "eva_somatic": "ClinVar somatic",
    "expression_atlas": "Expression Atlas",
    "gene2phenotype": "Gene2Phenotype",
    "gene2phenotype_literature": "Gene2Phenotype literature",
    "gene_burden": "Gene burden",
    "genomics_england": "Genomics England PanelApp",
    "gwas_credible_sets": "GWAS credible sets",
    "impc": "IMPC",
    "intogen": "IntOGen",
    "orphanet": "Orphanet",
    "ot_genetics_portal": "Open Targets Genetics",
    "project_score": "Project Score",
    "reactome": "Reactome",
    "uniprot_literature": "UniProt literature",
    "uniprot_variants": "UniProt curated variants",
}


DATATYPE_LABELS = {
    "animal_model": "Animal model",
    "clinical": "Clinical",
    "genetic_association": "Genetic association",
    "genetic_literature": "Genetic literature",
    "literature": "Literature",
    "rna_expression": "RNA expression",
    "somatic_mutation": "Somatic mutation",
}


def opentargets_target_record(
    target: JsonObject,
    *,
    max_results: int,
    website_base_url: str = OPENTARGETS_WEBSITE_BASE_URL,
    graphql_url: str = OPENTARGETS_GRAPHQL_URL,
) -> JsonObject:
    normalized = normalize_target(
        target,
        max_results=max_results,
        website_base_url=website_base_url,
        graphql_url=graphql_url,
    )
    target_id = normalized["target_id"]
    title = normalized["symbol"] or target_id
    links = target_links(normalized)
    description = normalized["name"] or f"Open Targets target {target_id}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "gene",
        "record_type": "opentargets_target",
        "database": "opentargets",
        "id": target_id,
        "stable_id": f"OpenTargets:target:{target_id}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "opentargets",
        "identifiers": target_identifiers(normalized),
        "links": links,
        "display": {
            "component": "gene",
            "chip_label": title,
            "icon": "opentargets",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    target_id,
                    normalized["biotype"],
                    normalized["location"],
                    associated_count_label(normalized["total_associated_diseases"], "diseases"),
                ]
                if part
            ),
            "description": description,
            "metadata": target_metadata(normalized),
            "badges": compact_badges(
                ("Open Targets", "source"),
                ("target", "record_type"),
                (target_id, "identifier"),
                (associated_count_label(normalized["total_associated_diseases"], "diseases"), "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "opentargets",
                "fields": compact_fields(
                    ("Target ID", target_id),
                    ("Symbol", normalized["symbol"]),
                    ("Name", normalized["name"]),
                    ("Biotype", normalized["biotype"]),
                    ("Location", normalized["location"]),
                    ("Associated diseases", str(normalized["total_associated_diseases"])),
                    ("Top diseases", ", ".join(top_association_labels(normalized["associated_diseases"], "disease_name"))),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": target_sections(normalized),
            "previews": target_previews(normalized, links),
        },
        "related": {
            "associated_diseases": normalized["associated_diseases"],
            "datasource_scores": normalized["datasource_score_rows"],
            "datatype_scores": normalized["datatype_score_rows"],
        },
        "data": normalized,
    }


def opentargets_disease_record(
    disease: JsonObject,
    *,
    max_results: int,
    website_base_url: str = OPENTARGETS_WEBSITE_BASE_URL,
    graphql_url: str = OPENTARGETS_GRAPHQL_URL,
) -> JsonObject:
    normalized = normalize_disease(
        disease,
        max_results=max_results,
        website_base_url=website_base_url,
        graphql_url=graphql_url,
    )
    disease_id = normalized["disease_id"]
    title = normalized["name"] or disease_id
    links = disease_links(normalized)
    description = normalized["description"] or f"Open Targets disease {disease_id}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "opentargets_disease",
        "database": "opentargets",
        "id": disease_id,
        "stable_id": f"OpenTargets:disease:{disease_id}",
        "label": title,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "opentargets",
        "identifiers": disease_identifiers(normalized),
        "links": links,
        "display": {
            "component": "dataset",
            "chip_label": title,
            "icon": "opentargets",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    disease_id,
                    associated_count_label(normalized["total_associated_targets"], "targets"),
                    f"{len(normalized['db_xrefs'])} xrefs" if normalized["db_xrefs"] else "",
                ]
                if part
            ),
            "description": description,
            "metadata": disease_metadata(normalized),
            "badges": compact_badges(
                ("Open Targets", "source"),
                ("disease", "record_type"),
                (disease_id, "identifier"),
                (associated_count_label(normalized["total_associated_targets"], "targets"), "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "opentargets",
                "fields": compact_fields(
                    ("Disease ID", disease_id),
                    ("Name", normalized["name"]),
                    ("Associated targets", str(normalized["total_associated_targets"])),
                    ("Top targets", ", ".join(top_association_labels(normalized["associated_targets"], "symbol"))),
                    ("Cross-references", ", ".join(normalized["db_xrefs"][:5])),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": disease_sections(normalized),
            "previews": disease_previews(normalized, links),
        },
        "related": {
            "associated_targets": normalized["associated_targets"],
            "datasource_scores": normalized["datasource_score_rows"],
            "datatype_scores": normalized["datatype_score_rows"],
        },
        "data": normalized,
    }


def opentargets_search_record(
    *,
    query: str,
    search: JsonObject,
    entity_names: list[str],
    max_results: int,
    website_base_url: str = OPENTARGETS_WEBSITE_BASE_URL,
    graphql_url: str = OPENTARGETS_GRAPHQL_URL,
) -> JsonObject:
    normalized = normalize_search(
        query=query,
        search=search,
        entity_names=entity_names,
        max_results=max_results,
        website_base_url=website_base_url,
        graphql_url=graphql_url,
    )
    links = search_links(normalized)
    title = f"Open Targets search: {query}"
    description = f"{normalized['total_hits']} Open Targets hits for {query}"
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "identifier_conversion",
        "record_type": "opentargets_search",
        "database": "opentargets",
        "id": query,
        "stable_id": f"OpenTargets:search:{query}",
        "label": query,
        "title": title,
        "description": description,
        "url": normalized["url"],
        "icon": "opentargets",
        "identifiers": {
            "opentargets_search": {
                "namespace": "opentargets.search",
                "id": query,
                "label": query,
                "url": normalized["url"],
            }
        },
        "links": links,
        "display": {
            "component": "identifier_conversion",
            "chip_label": query,
            "icon": "opentargets",
            "title": title,
            "subtitle": description,
            "description": description,
            "metadata": compact_fields(
                ("Query", query),
                ("Entities", ", ".join(entity_names)),
                ("Hits", str(normalized["total_hits"])),
                ("Returned", str(len(normalized["hits"]))),
            ),
            "badges": compact_badges(
                ("Open Targets", "source"),
                ("search", "record_type"),
                (f"{normalized['total_hits']} hits", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": description,
                "icon": "opentargets",
                "fields": compact_fields(
                    ("Query", query),
                    ("Entities", ", ".join(entity_names)),
                    ("Hits", str(normalized["total_hits"])),
                    ("Top hit", normalized["hits"][0]["label"] if normalized["hits"] else ""),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": search_sections(normalized),
            "previews": search_previews(normalized, links),
        },
        "related": {"hits": normalized["hits"]},
        "data": normalized,
    }


def normalize_target(
    target: JsonObject,
    *,
    max_results: int,
    website_base_url: str,
    graphql_url: str,
) -> JsonObject:
    target_id = normalize_space(target.get("id"))
    location = normalize_genomic_location(target.get("genomicLocation"))
    associated = target.get("associatedDiseases") if isinstance(target.get("associatedDiseases"), dict) else {}
    rows = normalize_associated_diseases(
        safe_list(associated.get("rows")),
        max_results=max_results,
        website_base_url=website_base_url,
    )
    datasource_rows = score_detail_rows(rows, relation_key="disease_name", score_key="datasource_scores")
    datatype_rows = score_detail_rows(rows, relation_key="disease_name", score_key="datatype_scores")
    total = numeric_int(associated.get("count"), fallback=len(rows))
    return {
        "target_id": target_id,
        "symbol": normalize_space(target.get("approvedSymbol")),
        "name": normalize_space(target.get("approvedName")),
        "biotype": normalize_space(target.get("biotype")),
        "location": location,
        "associated_diseases": rows,
        "total_associated_diseases": total,
        "associated_diseases_truncated": total > len(rows),
        "datasource_score_rows": datasource_rows,
        "datatype_score_rows": datatype_rows,
        "url": opentargets_target_url(target_id, website_base_url),
        "api_url": graphql_url,
    }


def normalize_disease(
    disease: JsonObject,
    *,
    max_results: int,
    website_base_url: str,
    graphql_url: str,
) -> JsonObject:
    disease_id = normalize_space(disease.get("id"))
    associated = disease.get("associatedTargets") if isinstance(disease.get("associatedTargets"), dict) else {}
    rows = normalize_associated_targets(
        safe_list(associated.get("rows")),
        max_results=max_results,
        website_base_url=website_base_url,
    )
    datasource_rows = score_detail_rows(rows, relation_key="symbol", score_key="datasource_scores")
    datatype_rows = score_detail_rows(rows, relation_key="symbol", score_key="datatype_scores")
    total = numeric_int(associated.get("count"), fallback=len(rows))
    return {
        "disease_id": disease_id,
        "name": normalize_space(disease.get("name")),
        "description": normalize_space(disease.get("description")),
        "db_xrefs": [normalize_space(item) for item in safe_list(disease.get("dbXRefs")) if normalize_space(item)],
        "associated_targets": rows,
        "total_associated_targets": total,
        "associated_targets_truncated": total > len(rows),
        "datasource_score_rows": datasource_rows,
        "datatype_score_rows": datatype_rows,
        "url": opentargets_disease_url(disease_id, website_base_url),
        "api_url": graphql_url,
    }


def normalize_search(
    *,
    query: str,
    search: JsonObject,
    entity_names: list[str],
    max_results: int,
    website_base_url: str,
    graphql_url: str,
) -> JsonObject:
    hits = []
    for hit in safe_list(search.get("hits"))[:max_results]:
        if not isinstance(hit, dict):
            continue
        normalized = normalize_search_hit(hit, website_base_url=website_base_url)
        if normalized:
            hits.append(normalized)
    return {
        "query": query,
        "entity_names": entity_names,
        "hits": hits,
        "total_hits": numeric_int(search.get("total"), fallback=len(hits)),
        "hits_truncated": numeric_int(search.get("total"), fallback=len(hits)) > len(hits),
        "url": opentargets_search_url(query, website_base_url),
        "api_url": graphql_url,
    }


def normalize_associated_diseases(
    value: list[object],
    *,
    max_results: int,
    website_base_url: str,
) -> list[JsonObject]:
    rows = []
    for item in value[:max_results]:
        if not isinstance(item, dict):
            continue
        disease = item.get("disease") if isinstance(item.get("disease"), dict) else {}
        disease_id = normalize_space(disease.get("id"))
        disease_name = normalize_space(disease.get("name"))
        rows.append(
            {
                "disease_id": disease_id,
                "disease_name": disease_name,
                "score": numeric(item.get("score")),
                "url": opentargets_disease_url(disease_id, website_base_url),
                "datasource_scores": normalize_score_list(item.get("datasourceScores"), DATASOURCE_LABELS),
                "datatype_scores": normalize_score_list(item.get("datatypeScores"), DATATYPE_LABELS),
                "top_datasources": top_score_labels(item.get("datasourceScores"), DATASOURCE_LABELS),
                "top_datatypes": top_score_labels(item.get("datatypeScores"), DATATYPE_LABELS),
            }
        )
    return rows


def normalize_associated_targets(
    value: list[object],
    *,
    max_results: int,
    website_base_url: str,
) -> list[JsonObject]:
    rows = []
    for item in value[:max_results]:
        if not isinstance(item, dict):
            continue
        target = item.get("target") if isinstance(item.get("target"), dict) else {}
        target_id = normalize_space(target.get("id"))
        symbol = normalize_space(target.get("approvedSymbol"))
        rows.append(
            {
                "target_id": target_id,
                "symbol": symbol,
                "name": normalize_space(target.get("approvedName")),
                "score": numeric(item.get("score")),
                "url": opentargets_target_url(target_id, website_base_url),
                "datasource_scores": normalize_score_list(item.get("datasourceScores"), DATASOURCE_LABELS),
                "datatype_scores": normalize_score_list(item.get("datatypeScores"), DATATYPE_LABELS),
                "top_datasources": top_score_labels(item.get("datasourceScores"), DATASOURCE_LABELS),
                "top_datatypes": top_score_labels(item.get("datatypeScores"), DATATYPE_LABELS),
            }
        )
    return rows


def normalize_search_hit(hit: JsonObject, *, website_base_url: str) -> JsonObject | None:
    entity = normalize_space(hit.get("entity"))
    object_payload = hit.get("object") if isinstance(hit.get("object"), dict) else {}
    identifier = normalize_space(hit.get("id") or object_payload.get("id"))
    if not entity or not identifier:
        return None
    if entity == "target":
        label = normalize_space(object_payload.get("approvedSymbol")) or identifier
        description = normalize_space(object_payload.get("approvedName"))
        url = opentargets_target_url(identifier, website_base_url)
        xrefs: list[str] = []
    elif entity == "disease":
        label = normalize_space(object_payload.get("name")) or identifier
        description = normalize_space(object_payload.get("description"))
        url = opentargets_disease_url(identifier, website_base_url)
        xrefs = [normalize_space(item) for item in safe_list(object_payload.get("dbXRefs")) if normalize_space(item)]
    else:
        return None
    return {
        "id": identifier,
        "entity": entity,
        "label": label,
        "description": description,
        "score": numeric(hit.get("score")),
        "url": url,
        "biotype": normalize_space(object_payload.get("biotype")),
        "db_xrefs": xrefs,
    }


def target_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "associated_diseases",
            "title": "Associated diseases",
            "kind": "table",
            "rows": normalized["associated_diseases"],
            "summary": {
                "total": normalized["total_associated_diseases"],
                "shown": len(normalized["associated_diseases"]),
                "truncated": normalized["associated_diseases_truncated"],
            },
        }
    ]
    if normalized["datasource_score_rows"]:
        sections.append(score_section("datasource_scores", "Datasource scores", normalized["datasource_score_rows"]))
    if normalized["datatype_score_rows"]:
        sections.append(score_section("datatype_scores", "Datatype scores", normalized["datatype_score_rows"]))
    return sections


def disease_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "associated_targets",
            "title": "Associated targets",
            "kind": "table",
            "rows": normalized["associated_targets"],
            "summary": {
                "total": normalized["total_associated_targets"],
                "shown": len(normalized["associated_targets"]),
                "truncated": normalized["associated_targets_truncated"],
            },
        }
    ]
    if normalized["datasource_score_rows"]:
        sections.append(score_section("datasource_scores", "Datasource scores", normalized["datasource_score_rows"]))
    if normalized["datatype_score_rows"]:
        sections.append(score_section("datatype_scores", "Datatype scores", normalized["datatype_score_rows"]))
    return sections


def search_sections(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "key": "search_hits",
            "title": "Search hits",
            "kind": "table",
            "rows": normalized["hits"],
            "summary": {
                "total": normalized["total_hits"],
                "shown": len(normalized["hits"]),
                "truncated": normalized["hits_truncated"],
            },
        }
    ]


def target_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview(
            "associated_diseases",
            "Associated diseases",
            normalized["target_id"],
            normalized["url"],
            disease_association_columns(),
            normalized["associated_diseases"],
            actions=display_actions(links),
            total=normalized["total_associated_diseases"],
            truncated=normalized["associated_diseases_truncated"],
        )
    ]
    if normalized["datasource_score_rows"]:
        previews.append(
            table_preview(
                "datasource_scores",
                "Datasource evidence scores",
                normalized["target_id"],
                normalized["url"],
                score_columns("Disease"),
                normalized["datasource_score_rows"],
                actions=display_actions(links),
            )
        )
    previews.append(xref_preview(normalized["target_id"], normalized["url"], target_xref_groups(normalized), links))
    return previews


def disease_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview(
            "associated_targets",
            "Associated targets",
            normalized["disease_id"],
            normalized["url"],
            target_association_columns(),
            normalized["associated_targets"],
            actions=display_actions(links),
            total=normalized["total_associated_targets"],
            truncated=normalized["associated_targets_truncated"],
        )
    ]
    if normalized["datasource_score_rows"]:
        previews.append(
            table_preview(
                "datasource_scores",
                "Datasource evidence scores",
                normalized["disease_id"],
                normalized["url"],
                score_columns("Target"),
                normalized["datasource_score_rows"],
                actions=display_actions(links),
            )
        )
    previews.append(xref_preview(normalized["disease_id"], normalized["url"], disease_xref_groups(normalized), links))
    return previews


def search_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        table_preview(
            "search_hits",
            "Search hits",
            normalized["query"],
            normalized["url"],
            search_columns(),
            normalized["hits"],
            actions=display_actions(links),
            total=normalized["total_hits"],
            truncated=normalized["hits_truncated"],
        ),
        xref_preview(normalized["query"], normalized["url"], search_xref_groups(normalized), links),
    ]


def table_preview(
    section_key: str,
    title: str,
    identifier: str,
    url: str,
    columns: list[JsonObject],
    rows: list[JsonObject],
    *,
    actions: list[JsonObject],
    total: int | None = None,
    truncated: bool = False,
) -> JsonObject:
    return {
        "kind": "table",
        "title": title,
        "provider": "Open Targets",
        "id": identifier,
        "url": url,
        "section_key": section_key,
        "actions": actions,
        "data": {
            "columns": columns,
            "rows": rows,
            "total_rows": total if total is not None else len(rows),
            "shown_rows": len(rows),
            "truncated": truncated,
        },
    }


def xref_preview(identifier: str, url: str, groups: list[JsonObject], links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "xref_groups",
        "title": "Cross-reference groups",
        "provider": "Open Targets",
        "id": identifier,
        "url": url,
        "actions": display_actions(links),
        "data": {"groups": groups},
    }


def score_section(key: str, title: str, rows: list[JsonObject]) -> JsonObject:
    return {
        "key": key,
        "title": title,
        "kind": "table",
        "rows": rows,
        "summary": {"shown": len(rows)},
    }


def target_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in Open Targets", normalized["url"], primary=True),
        link("Open Targets GraphQL API", normalized["api_url"], kind="related"),
        link("Open in Ensembl", ensembl_gene_url(normalized["target_id"]), kind="related"),
    )


def disease_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in Open Targets", normalized["url"], primary=True),
        link("Open Targets GraphQL API", normalized["api_url"], kind="related"),
    )


def search_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open search in Open Targets", normalized["url"], primary=True),
        link("Open Targets GraphQL API", normalized["api_url"], kind="related"),
    )


def target_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "opentargets": {
            "namespace": "opentargets.target",
            "id": normalized["target_id"],
            "label": f"OpenTargets:{normalized['target_id']}",
            "url": normalized["url"],
        },
        "ensembl_gene": {
            "namespace": "ensembl_gene",
            "id": normalized["target_id"],
            "label": normalized["target_id"],
            "url": ensembl_gene_url(normalized["target_id"]),
        },
    }
    if normalized["symbol"]:
        identifiers["gene_symbol"] = {
            "namespace": "gene_symbol",
            "id": normalized["symbol"],
            "label": normalized["symbol"],
        }
    return identifiers


def disease_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "opentargets": {
            "namespace": "opentargets.disease",
            "id": normalized["disease_id"],
            "label": f"OpenTargets:{normalized['disease_id']}",
            "url": normalized["url"],
        }
    }
    for xref in normalized["db_xrefs"][:20]:
        prefix, _, value = xref.partition(":")
        if prefix and value:
            identifiers[f"xref_{prefix.lower()}_{len(identifiers)}"] = {
                "namespace": prefix,
                "id": value,
                "label": xref,
            }
    return identifiers


def target_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [
        {
            "database": "Open Targets",
            "items": [{"id": normalized["target_id"], "label": normalized["target_id"], "url": normalized["url"]}],
        },
        {
            "database": "Ensembl",
            "items": [
                {
                    "id": normalized["target_id"],
                    "label": normalized["target_id"],
                    "url": ensembl_gene_url(normalized["target_id"]),
                }
            ],
        },
    ]
    diseases = [
        {"id": row["disease_id"], "label": row["disease_name"], "url": row["url"]}
        for row in normalized["associated_diseases"][:10]
        if row.get("disease_id")
    ]
    if diseases:
        groups.append({"database": "Associated diseases", "items": diseases})
    return groups


def disease_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [
        {
            "database": "Open Targets",
            "items": [{"id": normalized["disease_id"], "label": normalized["name"], "url": normalized["url"]}],
        }
    ]
    ontology_groups: dict[str, list[JsonObject]] = {}
    for xref in normalized["db_xrefs"][:50]:
        prefix, _, value = xref.partition(":")
        if not prefix or not value:
            continue
        ontology_groups.setdefault(prefix, []).append({"id": value, "label": xref})
    for prefix, items in sorted(ontology_groups.items()):
        groups.append({"database": prefix, "items": items})
    targets = [
        {"id": row["target_id"], "label": row["symbol"] or row["target_id"], "url": row["url"]}
        for row in normalized["associated_targets"][:10]
        if row.get("target_id")
    ]
    if targets:
        groups.append({"database": "Associated targets", "items": targets})
    return groups


def search_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = []
    for entity in ["target", "disease"]:
        items = [
            {"id": row["id"], "label": row["label"], "url": row["url"]}
            for row in normalized["hits"]
            if row.get("entity") == entity
        ]
        if items:
            groups.append({"database": f"Open Targets {entity}s", "items": items})
    return groups


def target_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Target ID", normalized["target_id"]),
        ("Symbol", normalized["symbol"]),
        ("Name", normalized["name"]),
        ("Biotype", normalized["biotype"]),
        ("Location", normalized["location"]),
        ("Associated diseases", str(normalized["total_associated_diseases"])),
        ("Top diseases", ", ".join(top_association_labels(normalized["associated_diseases"], "disease_name"))),
    )


def disease_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Disease ID", normalized["disease_id"]),
        ("Name", normalized["name"]),
        ("Associated targets", str(normalized["total_associated_targets"])),
        ("Top targets", ", ".join(top_association_labels(normalized["associated_targets"], "symbol"))),
        ("Cross-references", ", ".join(normalized["db_xrefs"][:5])),
    )


def normalize_genomic_location(value: object) -> str:
    item = value if isinstance(value, dict) else {}
    chrom = normalize_space(item.get("chromosome"))
    start = normalize_space(item.get("start"))
    end = normalize_space(item.get("end"))
    if chrom and start and end:
        return f"{chrom}:{start}-{end}"
    return ""


def normalize_score_list(value: object, labels: dict[str, str]) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        score_id = normalize_space(item.get("id"))
        if not score_id:
            continue
        rows.append(
            {
                "id": score_id,
                "label": labels.get(score_id, prettify_score_id(score_id)),
                "score": numeric(item.get("score")),
            }
        )
    rows.sort(key=lambda row: (score_sort_value(row.get("score")), row["label"]))
    return rows


def score_detail_rows(rows: list[JsonObject], *, relation_key: str, score_key: str) -> list[JsonObject]:
    flat_rows = []
    for row in rows:
        relation = normalize_space(row.get(relation_key))
        relation_id = normalize_space(row.get("disease_id") or row.get("target_id"))
        relation_url = normalize_space(row.get("url"))
        for score in safe_list(row.get(score_key)):
            if not isinstance(score, dict):
                continue
            flat_rows.append(
                {
                    "entity": relation,
                    "entity_id": relation_id,
                    "score_id": score.get("id"),
                    "label": score.get("label"),
                    "score": score.get("score"),
                    "url": relation_url,
                }
            )
    return flat_rows


def top_score_labels(value: object, labels: dict[str, str]) -> str:
    rows = normalize_score_list(value, labels)[:3]
    return ", ".join(
        f"{row['label']} {format_score(row.get('score'))}".strip()
        for row in rows
        if row.get("label")
    )


def top_association_labels(rows: list[JsonObject], key: str) -> list[str]:
    labels = []
    for row in rows[:3]:
        label = normalize_space(row.get(key))
        if label:
            labels.append(label)
    return labels


def associated_count_label(total: int, entity: str) -> str:
    return f"{total} associated {entity}" if total else ""


def prettify_score_id(value: str) -> str:
    replacements = {
        "gwas": "GWAS",
        "pmc": "PMC",
        "crispr": "CRISPR",
        "impc": "IMPC",
        "rna": "RNA",
    }
    words = value.replace("-", "_").split("_")
    pieces = []
    for word in words:
        lower = word.lower()
        pieces.append(replacements.get(lower, word.capitalize()))
    return " ".join(pieces)


def numeric(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def numeric_int(value: object, *, fallback: int) -> int:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return fallback


def score_sort_value(value: object) -> float:
    return -float(value) if isinstance(value, (int, float)) else 0.0


def format_score(value: object) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.3g}"
    return ""


def opentargets_target_url(target_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/target/{urllib.parse.quote(target_id)}"


def opentargets_disease_url(disease_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/disease/{urllib.parse.quote(disease_id)}"


def opentargets_search_url(query: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/search?query={urllib.parse.quote(query)}"


def ensembl_gene_url(gene_id: str) -> str:
    return f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={urllib.parse.quote(gene_id)}" if gene_id else ""


def disease_association_columns() -> list[JsonObject]:
    return [
        {"key": "disease_name", "label": "Disease"},
        {"key": "disease_id", "label": "Disease ID"},
        {"key": "score", "label": "Overall score"},
        {"key": "top_datasources", "label": "Top datasources"},
        {"key": "top_datatypes", "label": "Top datatypes"},
    ]


def target_association_columns() -> list[JsonObject]:
    return [
        {"key": "symbol", "label": "Target"},
        {"key": "target_id", "label": "Target ID"},
        {"key": "name", "label": "Name"},
        {"key": "score", "label": "Overall score"},
        {"key": "top_datasources", "label": "Top datasources"},
        {"key": "top_datatypes", "label": "Top datatypes"},
    ]


def score_columns(entity_label: str) -> list[JsonObject]:
    return [
        {"key": "entity", "label": entity_label},
        {"key": "entity_id", "label": f"{entity_label} ID"},
        {"key": "label", "label": "Evidence source"},
        {"key": "score_id", "label": "Source ID"},
        {"key": "score", "label": "Score"},
    ]


def search_columns() -> list[JsonObject]:
    return [
        {"key": "entity", "label": "Entity"},
        {"key": "id", "label": "ID"},
        {"key": "label", "label": "Label"},
        {"key": "description", "label": "Description"},
        {"key": "score", "label": "Search score"},
    ]


def link(
    label: str,
    url: str,
    *,
    kind: str = "external",
    primary: bool = False,
) -> JsonObject:
    return {"label": label, "url": url, "kind": kind, "primary": primary} if url else {}


def compact_links(*links: JsonObject) -> list[JsonObject]:
    return [item for item in links if item.get("url")]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "label": item["label"],
            "url": item["url"],
            "kind": item.get("kind", "external"),
            "primary": bool(item.get("primary")),
        }
        for item in links
        if item.get("url")
    ]


def compact_fields(*pairs: tuple[str, object]) -> list[JsonObject]:
    rows = []
    for label_text, value in pairs:
        text = normalize_space(value)
        if text:
            rows.append({"label": label_text, "value": text})
    return rows


def compact_badges(*pairs: tuple[object, str]) -> list[JsonObject]:
    rows = []
    for label_value, badge_type in pairs:
        text = normalize_space(label_value)
        if text:
            rows.append({"label": text, "kind": badge_type})
    return rows
