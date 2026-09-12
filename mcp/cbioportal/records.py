"""Front-end compatible record envelopes for cBioPortal API records."""

from __future__ import annotations

import re
import urllib.parse
from typing import Any

from .constants import CBIOPORTAL_API_BASE_URL, CBIOPORTAL_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def cbioportal_study_record(
    study: JsonObject,
    *,
    profiles: list[JsonObject] | None = None,
    sample_lists: list[JsonObject] | None = None,
    api_base_url: str = CBIOPORTAL_API_BASE_URL,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    normalized = normalize_study(study, profiles=profiles or [], sample_lists=sample_lists or [], api_base_url=api_base_url, website_base_url=website_base_url)
    links = study_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "cbioportal_study",
        "database": "cbioportal",
        "id": normalized["study_id"],
        "stable_id": normalized["study_id"],
        "label": normalized["study_id"],
        "title": normalized["name"] or normalized["study_id"],
        "description": normalized["description"] or "cBioPortal cancer genomics study",
        "url": normalized["url"],
        "icon": "cbioportal",
        "identifiers": study_identifiers(normalized),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": normalized["study_id"],
            "icon": "cbioportal",
            "title": normalized["name"] or normalized["study_id"],
            "subtitle": study_subtitle(normalized),
            "description": normalized["description"] or "cBioPortal study record",
            "metadata": study_metadata(normalized),
            "badges": compact_badges(
                ("cBioPortal", "source"),
                (normalized["study_id"], "identifier"),
                (normalized["cancer_type_id"], "context"),
                ("public" if normalized["public_study"] else "", "status"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": normalized["name"] or normalized["study_id"],
                "subtitle": study_subtitle(normalized),
                "icon": "cbioportal",
                "fields": compact_fields(
                    ("Study ID", normalized["study_id"]),
                    ("Cancer type", normalized["cancer_type_id"]),
                    ("Samples", normalized["all_sample_count"]),
                    ("Sequenced samples", normalized["sequenced_sample_count"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": study_sections(normalized),
            "previews": study_previews(normalized, links),
        },
        "related": {"profiles": normalized["profiles"], "sample_lists": normalized["sample_lists"], "pmid": normalized["pmid"]},
        "data": normalized,
    }


def cbioportal_profile_record(
    profile: JsonObject,
    *,
    api_base_url: str = CBIOPORTAL_API_BASE_URL,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    normalized = normalize_profile(profile, api_base_url=api_base_url, website_base_url=website_base_url)
    links = profile_links(normalized)
    return dataset_record(
        record_type="cbioportal_molecular_profile",
        record_id=normalized["molecular_profile_id"],
        title=normalized["name"] or normalized["molecular_profile_id"],
        description=normalized["description"] or "cBioPortal molecular profile",
        url=normalized["url"],
        chip_label=normalized["molecular_profile_id"],
        subtitle=profile_subtitle(normalized),
        metadata=profile_metadata(normalized),
        badges=compact_badges(("cBioPortal", "source"), (normalized["molecular_profile_id"], "identifier"), (normalized["molecular_alteration_type"], "record_type")),
        links=links,
        data=normalized,
        previews=[
            {"kind": "table", "title": "Molecular profile", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": profile_metadata(normalized)}},
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": profile_xref_groups(normalized)}},
        ],
    )


def cbioportal_sample_list_record(
    sample_list: JsonObject,
    *,
    api_base_url: str = CBIOPORTAL_API_BASE_URL,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    normalized = normalize_sample_list(sample_list, api_base_url=api_base_url, website_base_url=website_base_url)
    links = sample_list_links(normalized)
    return dataset_record(
        record_type="cbioportal_sample_list",
        record_id=normalized["sample_list_id"],
        title=normalized["name"] or normalized["sample_list_id"],
        description=normalized["description"] or "cBioPortal sample list",
        url=normalized["url"],
        chip_label=normalized["sample_list_id"],
        subtitle=sample_list_subtitle(normalized),
        metadata=sample_list_metadata(normalized),
        badges=compact_badges(("cBioPortal", "source"), (normalized["sample_list_id"], "identifier"), (normalized["category"], "record_type")),
        links=links,
        data=normalized,
        previews=[
            {"kind": "table", "title": "Sample list", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": sample_list_metadata(normalized)}},
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": sample_list_xref_groups(normalized)}},
        ],
    )


def cbioportal_clinical_attributes_record(
    *,
    study_id: str,
    attributes: list[JsonObject],
    api_url: str,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    rows = [normalize_clinical_attribute(item) for item in attributes]
    url = study_url(study_id, website_base_url)
    patient_count = sum(1 for row in rows if row["patient_attribute"])
    sample_count = len(rows) - patient_count
    links = [
        {"label": "Open cBioPortal study", "url": url, "kind": "external", "primary": True},
        {"label": "Open clinical attributes API", "url": api_url, "kind": "external"},
    ]
    metadata = compact_fields(
        ("Study ID", study_id),
        ("Attributes", len(rows)),
        ("Patient attributes", patient_count),
        ("Sample attributes", sample_count),
        ("API", api_url),
    )
    data = {
        "study_id": study_id,
        "attributes": rows,
        "attribute_count": len(rows),
        "patient_attribute_count": patient_count,
        "sample_attribute_count": sample_count,
        "url": url,
        "api_url": api_url,
    }
    return dataset_record(
        record_type="cbioportal_clinical_attributes",
        record_id=f"{study_id}:clinical_attributes",
        title=f"{study_id} clinical attributes",
        description=f"{len(rows)} cBioPortal clinical attribute definitions for {study_id}.",
        url=url,
        chip_label="clinical attributes",
        subtitle=f"cBioPortal clinical metadata | {study_id} | {len(rows)} attributes",
        metadata=metadata,
        badges=compact_badges(("cBioPortal", "source"), (study_id, "identifier"), ("clinical attributes", "record_type")),
        links=links,
        data=data,
        previews=[
            {
                "kind": "table",
                "title": "Clinical attributes",
                "section_key": "attributes",
                "data": {
                    "columns": ["clinical_attribute_id", "display_name", "datatype", "patient_attribute", "description"],
                    "rows": rows,
                },
            },
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": clinical_xref_groups(data)}},
        ],
        sections=[{"key": "overview", "title": "Overview", "kind": "table", "rows": metadata}, {"key": "attributes", "title": "Clinical attributes", "kind": "table", "rows": rows}],
    )


def cbioportal_clinical_data_record(
    *,
    study_id: str,
    clinical_data_type: str,
    ids: list[str],
    sample_list_id: str,
    attribute_ids: list[str],
    values: list[JsonObject],
    api_url: str,
    sample_ids_api_url: str,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    rows = [normalize_clinical_value(item) for item in values]
    matrix_rows = clinical_matrix(rows, clinical_data_type, attribute_ids)
    entity_label = "sample" if clinical_data_type == "SAMPLE" else "patient"
    url = study_url(study_id, website_base_url)
    links = [
        {"label": "Open cBioPortal study", "url": url, "kind": "external", "primary": True},
        {"label": "Open clinical data API", "url": api_url, "kind": "external"},
    ]
    if sample_ids_api_url:
        links.append({"label": "Open sample IDs API", "url": sample_ids_api_url, "kind": "external"})
    metadata = compact_fields(
        ("Study ID", study_id),
        ("Clinical data type", clinical_data_type),
        ("Sample list", sample_list_id),
        ("Requested IDs", len(ids)),
        ("Attributes", ", ".join(attribute_ids)),
        ("Returned values", len(rows)),
        ("API", api_url),
    )
    matrix_columns = matrix_column_order(clinical_data_type, attribute_ids)
    data = {
        "study_id": study_id,
        "clinical_data_type": clinical_data_type,
        "sample_list_id": sample_list_id,
        "ids": ids,
        "clinical_attribute_ids": attribute_ids,
        "values": rows,
        "matrix": matrix_rows,
        "url": url,
        "api_url": api_url,
        "sample_ids_api_url": sample_ids_api_url,
    }
    return dataset_record(
        record_type="cbioportal_clinical_data_table",
        record_id=f"{study_id}:{clinical_data_type.lower()}:{sample_list_id or ','.join(ids[:3])}:clinical_data",
        title=f"{study_id} {entity_label} clinical data",
        description=f"{len(matrix_rows)} {entity_label} rows and {len(rows)} clinical values. No bulk data download has been started.",
        url=url,
        chip_label=f"{clinical_data_type.lower()} clinical data",
        subtitle=f"cBioPortal clinical data | {study_id} | {len(matrix_rows)} {entity_label}s",
        metadata=metadata,
        badges=compact_badges(("cBioPortal", "source"), (study_id, "identifier"), ("clinical data", "record_type")),
        links=links,
        data=data,
        previews=[
            {
                "kind": "table",
                "title": "Clinical data matrix",
                "section_key": "clinical_matrix",
                "data": {"columns": matrix_columns, "rows": matrix_rows},
            },
            {
                "kind": "table",
                "title": "Clinical data values",
                "section_key": "clinical_values",
                "data": {"columns": ["sample_id", "patient_id", "clinical_attribute_id", "value"], "rows": rows},
            },
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": clinical_xref_groups(data)}},
        ],
        sections=[
            {"key": "overview", "title": "Overview", "kind": "table", "rows": metadata},
            {"key": "clinical_matrix", "title": "Clinical data matrix", "kind": "table", "rows": matrix_rows},
            {"key": "clinical_values", "title": "Clinical data values", "kind": "table", "rows": rows},
        ],
    )


def cbioportal_survival_data_record(
    *,
    study_id: str,
    sample_list_id: str,
    sample_ids: list[str],
    patient_ids: list[str],
    survival_prefixes: list[str],
    samples: list[JsonObject],
    values: list[JsonObject],
    api_url: str,
    sample_ids_api_url: str,
    samples_fetch_api_url: str,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    clinical_rows = [normalize_clinical_value(item) for item in values]
    sample_rows = [normalize_sample(item) for item in samples]
    attribute_ids = survival_attribute_ids(survival_prefixes)
    matrix_rows = clinical_matrix(clinical_rows, "PATIENT", attribute_ids)
    curve_rows = survival_curve_rows(matrix_rows, sample_rows, survival_prefixes, study_id=study_id)
    url = study_url(study_id, website_base_url)
    links = [
        {"label": "Open cBioPortal study", "url": url, "kind": "external", "primary": True},
        {"label": "Open clinical data API", "url": api_url, "kind": "external"},
    ]
    if sample_ids_api_url:
        links.append({"label": "Open sample IDs API", "url": sample_ids_api_url, "kind": "external"})
    if samples_fetch_api_url:
        links.append({"label": "Open samples fetch API", "url": samples_fetch_api_url, "kind": "external"})
    metadata = compact_fields(
        ("Study ID", study_id),
        ("Sample list", sample_list_id),
        ("Samples", len(sample_ids)),
        ("Patients", len(patient_ids)),
        ("Survival endpoints", ", ".join(survival_prefixes)),
        ("Returned clinical values", len(clinical_rows)),
        ("Curve rows", len(curve_rows)),
        ("API", api_url),
    )
    data = {
        "study_id": study_id,
        "sample_list_id": sample_list_id,
        "sample_ids": sample_ids,
        "patient_ids": patient_ids,
        "survival_prefixes": survival_prefixes,
        "samples": sample_rows,
        "clinical_values": clinical_rows,
        "clinical_matrix": matrix_rows,
        "survival_rows": curve_rows,
        "url": url,
        "api_url": api_url,
        "sample_ids_api_url": sample_ids_api_url,
        "samples_fetch_api_url": samples_fetch_api_url,
    }
    return dataset_record(
        record_type="cbioportal_survival_table",
        record_id=f"{study_id}:{sample_list_id or ','.join(patient_ids[:3])}:survival",
        title=f"{study_id} survival data",
        description=f"{len(curve_rows)} survival rows across {len(patient_ids)} patients. Data are bounded clinical metadata rows, not a bulk export.",
        url=url,
        chip_label="survival",
        subtitle=f"cBioPortal survival | {study_id} | {len(patient_ids)} patients",
        metadata=metadata,
        badges=compact_badges(("cBioPortal", "source"), (study_id, "identifier"), ("survival", "record_type")),
        links=links,
        data=data,
        previews=[
            {
                "kind": "survival_curve",
                "title": "Survival curve data",
                "section_key": "survival_rows",
                "data": {"time_unit": "months", "endpoints": survival_prefixes, "rows": curve_rows},
            },
            {
                "kind": "table",
                "title": "Survival rows",
                "section_key": "survival_rows",
                "data": {"columns": ["patient_id", "endpoint", "time_months", "event_observed", "status"], "rows": curve_rows},
            },
            {
                "kind": "table",
                "title": "Survival clinical matrix",
                "section_key": "clinical_matrix",
                "data": {"columns": matrix_column_order("PATIENT", attribute_ids), "rows": matrix_rows},
            },
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": clinical_xref_groups(data)}},
        ],
        sections=[
            {"key": "overview", "title": "Overview", "kind": "table", "rows": metadata},
            {"key": "survival_rows", "title": "Survival rows", "kind": "table", "rows": curve_rows},
            {"key": "clinical_matrix", "title": "Survival clinical matrix", "kind": "table", "rows": matrix_rows},
            {"key": "samples", "title": "Samples", "kind": "table", "rows": sample_rows},
        ],
    )


def cbioportal_molecular_data_record(
    *,
    molecular_profile_id: str,
    sample_list_id: str,
    sample_ids: list[str],
    values: list[JsonObject],
    gene_map: dict[int, str],
    requested_genes: list[str],
    api_url: str,
    upstream_returned: int,
    api_base_url: str = CBIOPORTAL_API_BASE_URL,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    rows = [normalize_molecular_value(item, gene_map=gene_map) for item in values]
    matrix_rows, matrix_columns = molecular_matrix(rows, value_key="value")
    study_id = infer_study_id(molecular_profile_id, sample_list_id) or first_row_value(rows, "study_id")
    title_gene = ", ".join(requested_genes) if requested_genes else ", ".join(sorted({row["gene"] for row in rows if row["gene"]}))
    sample_context = sample_list_id or f"{len(sample_ids)} samples"
    title = f"{title_gene or 'Gene'} molecular data in {sample_context}"
    url = study_url(study_id, website_base_url) if study_id else website_base_url.rstrip()
    links = [
        {"label": "Open cBioPortal study", "url": url, "kind": "external", "primary": True},
        {"label": "Open molecular data API", "url": api_url, "kind": "external"},
    ]
    metadata = compact_fields(
        ("Molecular profile", molecular_profile_id),
        ("Sample list", sample_list_id),
        ("Sample IDs", len(sample_ids) if sample_ids else ""),
        ("Requested genes", title_gene),
        ("Returned values", len(rows)),
        ("Upstream values", upstream_returned),
        ("API", api_url),
    )
    data = {
        "molecular_profile_id": molecular_profile_id,
        "sample_list_id": sample_list_id,
        "sample_ids": sample_ids,
        "study_id": study_id,
        "requested_genes": requested_genes,
        "values": rows,
        "matrix": matrix_rows,
        "matrix_columns": matrix_columns,
        "upstream_returned": upstream_returned,
        "truncated": upstream_returned > len(rows),
        "url": url,
        "api_url": api_url,
    }
    return dataset_record(
        record_type="cbioportal_molecular_data_matrix",
        record_id=f"{molecular_profile_id}:{sample_context}:{title_gene or 'molecular_data'}",
        title=title,
        description=f"{len(rows)} bounded cBioPortal molecular data values arranged into {len(matrix_rows)} sample rows.",
        url=url,
        chip_label=title_gene or molecular_profile_id,
        subtitle=f"cBioPortal molecular data | {molecular_profile_id} | {len(matrix_rows)} samples",
        metadata=metadata,
        badges=compact_badges(("cBioPortal", "source"), (molecular_profile_id, "identifier"), ("molecular data", "record_type")),
        links=links,
        data=data,
        previews=[
            {
                "kind": "heatmap_matrix",
                "title": "Molecular data heatmap",
                "section_key": "molecular_matrix",
                "data": {
                    "scale": "continuous",
                    "row_id": "sample_id",
                    "column_ids": [column for column in matrix_columns if column not in {"sample_id", "patient_id", "study_id"}],
                    "value_key": "value",
                    "columns": matrix_columns,
                    "rows": matrix_rows,
                    "truncated": data["truncated"],
                },
            },
            {
                "kind": "table",
                "title": "Molecular data values",
                "section_key": "molecular_values",
                "data": {"columns": ["sample_id", "patient_id", "gene", "entrez_gene_id", "value"], "rows": rows},
            },
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": molecular_xref_groups(data)}},
        ],
        sections=[
            {"key": "overview", "title": "Overview", "kind": "table", "rows": metadata},
            {"key": "molecular_matrix", "title": "Molecular data matrix", "kind": "table", "rows": matrix_rows},
            {"key": "molecular_values", "title": "Molecular data values", "kind": "table", "rows": rows},
        ],
    )


def cbioportal_discrete_cna_record(
    *,
    molecular_profile_id: str,
    sample_list_id: str,
    sample_ids: list[str],
    event_type: str,
    values: list[JsonObject],
    gene_map: dict[int, str],
    requested_genes: list[str],
    api_url: str,
    upstream_returned: int,
    api_base_url: str = CBIOPORTAL_API_BASE_URL,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    rows = [normalize_discrete_cna_value(item, gene_map=gene_map) for item in values]
    matrix_rows, matrix_columns = molecular_matrix(rows, value_key="alteration")
    study_id = infer_study_id(molecular_profile_id, sample_list_id) or first_row_value(rows, "study_id")
    title_gene = ", ".join(requested_genes) if requested_genes else ", ".join(sorted({row["gene"] for row in rows if row["gene"]}))
    sample_context = sample_list_id or f"{len(sample_ids)} samples"
    title = f"{title_gene or 'Gene'} copy-number calls in {sample_context}"
    url = study_url(study_id, website_base_url) if study_id else website_base_url.rstrip()
    links = [
        {"label": "Open cBioPortal study", "url": url, "kind": "external", "primary": True},
        {"label": "Open discrete copy-number API", "url": api_url, "kind": "external"},
    ]
    metadata = compact_fields(
        ("Molecular profile", molecular_profile_id),
        ("Sample list", sample_list_id),
        ("Sample IDs", len(sample_ids) if sample_ids else ""),
        ("Requested genes", title_gene),
        ("Event filter", event_type),
        ("Returned calls", len(rows)),
        ("Upstream calls", upstream_returned),
        ("API", api_url),
    )
    data = {
        "molecular_profile_id": molecular_profile_id,
        "sample_list_id": sample_list_id,
        "sample_ids": sample_ids,
        "study_id": study_id,
        "requested_genes": requested_genes,
        "event_type": event_type,
        "values": rows,
        "matrix": matrix_rows,
        "matrix_columns": matrix_columns,
        "alteration_labels": cna_alteration_labels(),
        "upstream_returned": upstream_returned,
        "truncated": upstream_returned > len(rows),
        "url": url,
        "api_url": api_url,
    }
    return dataset_record(
        record_type="cbioportal_discrete_cna_matrix",
        record_id=f"{molecular_profile_id}:{sample_context}:{event_type}:{title_gene or 'discrete_cna'}",
        title=title,
        description=f"{len(rows)} bounded cBioPortal discrete copy-number calls arranged into {len(matrix_rows)} sample rows.",
        url=url,
        chip_label=title_gene or molecular_profile_id,
        subtitle=f"cBioPortal discrete CNA | {molecular_profile_id} | {len(matrix_rows)} samples",
        metadata=metadata,
        badges=compact_badges(("cBioPortal", "source"), (molecular_profile_id, "identifier"), ("discrete CNA", "record_type")),
        links=links,
        data=data,
        previews=[
            {
                "kind": "heatmap_matrix",
                "title": "Discrete CNA heatmap",
                "section_key": "cna_matrix",
                "data": {
                    "scale": "discrete",
                    "row_id": "sample_id",
                    "column_ids": [column for column in matrix_columns if column not in {"sample_id", "patient_id", "study_id"}],
                    "value_key": "alteration",
                    "value_labels": data["alteration_labels"],
                    "columns": matrix_columns,
                    "rows": matrix_rows,
                    "truncated": data["truncated"],
                },
            },
            {
                "kind": "table",
                "title": "Discrete CNA values",
                "section_key": "cna_values",
                "data": {"columns": ["sample_id", "patient_id", "gene", "entrez_gene_id", "alteration", "alteration_label"], "rows": rows},
            },
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": molecular_xref_groups(data)}},
        ],
        sections=[
            {"key": "overview", "title": "Overview", "kind": "table", "rows": metadata},
            {"key": "cna_matrix", "title": "Discrete CNA matrix", "kind": "table", "rows": matrix_rows},
            {"key": "cna_values", "title": "Discrete CNA values", "kind": "table", "rows": rows},
        ],
    )


def cbioportal_mutations_record(
    *,
    molecular_profile_id: str,
    sample_list_id: str,
    mutations: list[JsonObject],
    gene_map: dict[int, str],
    requested_genes: list[str],
    api_url: str,
    api_base_url: str = CBIOPORTAL_API_BASE_URL,
    website_base_url: str = CBIOPORTAL_WEBSITE_BASE_URL,
) -> JsonObject:
    rows = [normalize_mutation(item, gene_map=gene_map) for item in mutations]
    study_id = infer_study_id(molecular_profile_id, sample_list_id)
    title_gene = ", ".join(requested_genes) if requested_genes else ", ".join(sorted({row["gene"] for row in rows if row["gene"]}))
    title = f"{title_gene or 'Gene'} mutations in {sample_list_id}"
    url = study_url(study_id, website_base_url) if study_id else website_base_url.rstrip()
    links = [
        {"label": "Open cBioPortal study", "url": url, "kind": "external", "primary": True},
        {"label": "Open mutation fetch API", "url": api_url, "kind": "external"},
    ]
    metadata = compact_fields(
        ("Molecular profile", molecular_profile_id),
        ("Sample list", sample_list_id),
        ("Requested genes", title_gene),
        ("Returned mutations", len(rows)),
        ("API", api_url),
    )
    data = {
        "molecular_profile_id": molecular_profile_id,
        "sample_list_id": sample_list_id,
        "study_id": study_id,
        "requested_genes": requested_genes,
        "mutations": rows,
        "url": url,
        "api_url": api_url,
    }
    return dataset_record(
        record_type="cbioportal_mutation_table",
        record_id=f"{molecular_profile_id}:{sample_list_id}:{title_gene or 'mutations'}",
        title=title,
        description=f"{len(rows)} cBioPortal mutation rows. No bulk data download has been started.",
        url=url,
        chip_label=title_gene or molecular_profile_id,
        subtitle=f"cBioPortal | {molecular_profile_id} | {len(rows)} rows",
        metadata=metadata,
        badges=compact_badges(("cBioPortal", "source"), (molecular_profile_id, "identifier"), ("mutations", "record_type")),
        links=links,
        data=data,
        previews=[
            {
                "kind": "table",
                "title": "Mutations",
                "section_key": "mutations",
                "data": {
                    "columns": ["sample_id", "patient_id", "gene", "protein_change", "mutation_type", "variant_type", "chromosome", "start_position"],
                    "rows": rows,
                },
            },
            {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": mutation_xref_groups(data)}},
        ],
        sections=[{"key": "overview", "title": "Overview", "kind": "table", "rows": metadata}, {"key": "mutations", "title": "Mutations", "kind": "table", "rows": rows}],
    )


def dataset_record(
    *,
    record_type: str,
    record_id: str,
    title: str,
    description: str,
    url: str,
    chip_label: str,
    subtitle: str,
    metadata: list[JsonObject],
    badges: list[JsonObject],
    links: list[JsonObject],
    data: JsonObject,
    previews: list[JsonObject],
    sections: list[JsonObject] | None = None,
) -> JsonObject:
    sections = sections or [{"key": "overview", "title": "Overview", "kind": "table", "rows": metadata}]
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.dataset",
        "record_type": record_type,
        "database": "cbioportal",
        "id": record_id,
        "stable_id": record_id,
        "label": chip_label,
        "title": title,
        "description": description,
        "url": url,
        "icon": "cbioportal",
        "identifiers": {"cbioportal": {"namespace": record_type, "id": record_id, "label": chip_label, "url": url}},
        "links": links,
        "display": {
            "component": "dataset",
            "chip_label": chip_label,
            "icon": "cbioportal",
            "title": title,
            "subtitle": subtitle,
            "description": description,
            "metadata": metadata,
            "badges": badges,
            "actions": display_actions(links),
            "hover": {"title": title, "subtitle": subtitle, "icon": "cbioportal", "fields": metadata[:8]},
            "primary_url": url,
            "sections": sections,
            "previews": previews,
        },
        "related": {},
        "data": data,
    }


def normalize_study(
    study: JsonObject,
    *,
    profiles: list[JsonObject],
    sample_lists: list[JsonObject],
    api_base_url: str,
    website_base_url: str,
) -> JsonObject:
    study_id = normalize_space(study.get("studyId"))
    return {
        "study_id": study_id,
        "name": normalize_space(study.get("name")),
        "description": strip_html(study.get("description")),
        "cancer_type_id": normalize_space(study.get("cancerTypeId")),
        "all_sample_count": int_or_zero(study.get("allSampleCount")),
        "sequenced_sample_count": int_or_zero(study.get("sequencedSampleCount")),
        "cna_sample_count": int_or_zero(study.get("cnaSampleCount")),
        "mrna_rnaseq_sample_count": int_or_zero(study.get("mrnaRnaSeqSampleCount")),
        "pmid": normalize_space(study.get("pmid")),
        "citation": normalize_space(study.get("citation")),
        "groups": normalize_space(study.get("groups")),
        "public_study": bool(study.get("publicStudy", True)),
        "read_permission": bool(study.get("readPermission", True)),
        "profiles": [normalize_profile(item, api_base_url=api_base_url, website_base_url=website_base_url) for item in profiles],
        "sample_lists": [normalize_sample_list(item, api_base_url=api_base_url, website_base_url=website_base_url) for item in sample_lists],
        "url": study_url(study_id, website_base_url),
        "api_url": api_url_for(f"studies/{study_id}", api_base_url, {"projection": "DETAILED"}),
        "profiles_api_url": api_url_for(f"studies/{study_id}/molecular-profiles", api_base_url, {"projection": "SUMMARY"}),
        "sample_lists_api_url": api_url_for(f"studies/{study_id}/sample-lists", api_base_url, {"projection": "SUMMARY"}),
    }


def normalize_profile(profile: JsonObject, *, api_base_url: str, website_base_url: str) -> JsonObject:
    profile_id = normalize_space(profile.get("molecularProfileId"))
    study_id = normalize_space(profile.get("studyId"))
    return {
        "molecular_profile_id": profile_id,
        "study_id": study_id,
        "stable_id": normalize_space(profile.get("stableId")),
        "name": normalize_space(profile.get("name")),
        "description": strip_html(profile.get("description")),
        "molecular_alteration_type": normalize_space(profile.get("molecularAlterationType")),
        "datatype": normalize_space(profile.get("datatype")),
        "show_profile_in_analysis_tab": bool(profile.get("showProfileInAnalysisTab", False)),
        "url": study_url(study_id, website_base_url) if study_id else website_base_url.rstrip(),
        "api_url": api_url_for(f"molecular-profiles/{profile_id}", api_base_url, {"projection": "DETAILED"}),
    }


def normalize_sample_list(sample_list: JsonObject, *, api_base_url: str, website_base_url: str) -> JsonObject:
    sample_list_id = normalize_space(sample_list.get("sampleListId"))
    study_id = normalize_space(sample_list.get("studyId"))
    return {
        "sample_list_id": sample_list_id,
        "study_id": study_id,
        "name": normalize_space(sample_list.get("name")),
        "description": strip_html(sample_list.get("description")),
        "category": normalize_space(sample_list.get("category")),
        "sample_count": int_or_zero(sample_list.get("sampleCount")),
        "url": study_url(study_id, website_base_url) if study_id else website_base_url.rstrip(),
        "api_url": api_url_for(f"sample-lists/{sample_list_id}", api_base_url, {"projection": "DETAILED"}),
    }


def normalize_mutation(mutation: JsonObject, *, gene_map: dict[int, str]) -> JsonObject:
    entrez_gene_id = int_or_zero(mutation.get("entrezGeneId"))
    gene = normalize_space(mutation.get("hugoGeneSymbol")) or gene_map.get(entrez_gene_id, str(entrez_gene_id) if entrez_gene_id else "")
    return {
        "sample_id": normalize_space(mutation.get("sampleId")),
        "patient_id": normalize_space(mutation.get("patientId")),
        "gene": gene,
        "entrez_gene_id": entrez_gene_id,
        "protein_change": normalize_space(mutation.get("proteinChange")),
        "mutation_type": normalize_space(mutation.get("mutationType")),
        "variant_type": normalize_space(mutation.get("variantType")),
        "chromosome": normalize_space(mutation.get("chr")),
        "start_position": int_or_zero(mutation.get("startPosition")),
        "end_position": int_or_zero(mutation.get("endPosition")),
        "reference_allele": normalize_space(mutation.get("referenceAllele")),
        "variant_allele": normalize_space(mutation.get("variantAllele")),
    }


def normalize_molecular_value(value: JsonObject, *, gene_map: dict[int, str]) -> JsonObject:
    entrez_gene_id = int_or_zero(value.get("entrezGeneId"))
    gene = gene_label(value, entrez_gene_id, gene_map)
    numeric_value = float_or_none(value.get("value"))
    return {
        "sample_id": normalize_space(value.get("sampleId")),
        "patient_id": normalize_space(value.get("patientId")),
        "study_id": normalize_space(value.get("studyId")),
        "molecular_profile_id": normalize_space(value.get("molecularProfileId")),
        "gene": gene,
        "entrez_gene_id": entrez_gene_id,
        "value": numeric_value if numeric_value is not None else value.get("value"),
    }


def normalize_discrete_cna_value(value: JsonObject, *, gene_map: dict[int, str]) -> JsonObject:
    entrez_gene_id = int_or_zero(value.get("entrezGeneId"))
    alteration = int_or_none(value.get("alteration"))
    gene = gene_label(value, entrez_gene_id, gene_map)
    return {
        "sample_id": normalize_space(value.get("sampleId")),
        "patient_id": normalize_space(value.get("patientId")),
        "study_id": normalize_space(value.get("studyId")),
        "molecular_profile_id": normalize_space(value.get("molecularProfileId")),
        "gene": gene,
        "entrez_gene_id": entrez_gene_id,
        "alteration": alteration,
        "alteration_label": cna_alteration_label(alteration),
    }


def gene_label(value: JsonObject, entrez_gene_id: int, gene_map: dict[int, str]) -> str:
    gene = value.get("gene")
    gene_symbol = ""
    if isinstance(gene, dict):
        gene_symbol = normalize_space(gene.get("hugoGeneSymbol"))
    return normalize_space(value.get("hugoGeneSymbol")) or gene_symbol or gene_map.get(entrez_gene_id, str(entrez_gene_id) if entrez_gene_id else "")


def normalize_clinical_attribute(attribute: JsonObject) -> JsonObject:
    return {
        "clinical_attribute_id": normalize_space(attribute.get("clinicalAttributeId")),
        "display_name": normalize_space(attribute.get("displayName")),
        "description": strip_html(attribute.get("description")),
        "datatype": normalize_space(attribute.get("datatype")),
        "patient_attribute": bool(attribute.get("patientAttribute", False)),
        "priority": normalize_space(attribute.get("priority")),
        "study_id": normalize_space(attribute.get("studyId")),
    }


def normalize_clinical_value(value: JsonObject) -> JsonObject:
    return {
        "sample_id": normalize_space(value.get("sampleId")),
        "patient_id": normalize_space(value.get("patientId")),
        "study_id": normalize_space(value.get("studyId")),
        "clinical_attribute_id": normalize_space(value.get("clinicalAttributeId")),
        "value": normalize_space(value.get("value")),
    }


def normalize_sample(sample: JsonObject) -> JsonObject:
    return {
        "sample_id": normalize_space(sample.get("sampleId")),
        "patient_id": normalize_space(sample.get("patientId")),
        "study_id": normalize_space(sample.get("studyId")),
        "sample_type": normalize_space(sample.get("sampleType")),
        "sequenced": bool(sample.get("sequenced", False)),
        "copy_number_segment_present": bool(sample.get("copyNumberSegmentPresent", False)),
    }


def clinical_matrix(rows: list[JsonObject], clinical_data_type: str, attribute_ids: list[str]) -> list[JsonObject]:
    key_field = "sample_id" if clinical_data_type == "SAMPLE" else "patient_id"
    grouped: dict[str, JsonObject] = {}
    for row in rows:
        key = row.get(key_field) or row.get("sample_id") or row.get("patient_id")
        if not key:
            continue
        entry = grouped.setdefault(str(key), {key_field: key})
        if clinical_data_type == "SAMPLE" and row.get("patient_id"):
            entry["patient_id"] = row["patient_id"]
        attribute_id = row.get("clinical_attribute_id")
        if attribute_id:
            entry[str(attribute_id)] = row.get("value", "")
    ordered_rows: list[JsonObject] = []
    for key in sorted(grouped):
        entry = grouped[key]
        ordered_rows.append({column: entry.get(column, "") for column in matrix_column_order(clinical_data_type, attribute_ids)})
    return ordered_rows


def molecular_matrix(rows: list[JsonObject], *, value_key: str) -> tuple[list[JsonObject], list[str]]:
    gene_columns: list[str] = []
    grouped: dict[str, JsonObject] = {}
    for row in rows:
        sample_id = normalize_space(row.get("sample_id"))
        gene = normalize_space(row.get("gene"))
        if not sample_id or not gene:
            continue
        if gene not in gene_columns:
            gene_columns.append(gene)
        entry = grouped.setdefault(
            sample_id,
            {
                "sample_id": sample_id,
                "patient_id": normalize_space(row.get("patient_id")),
                "study_id": normalize_space(row.get("study_id")),
            },
        )
        entry[gene] = row.get(value_key)
    columns = ["sample_id", "patient_id", "study_id"] + gene_columns
    matrix_rows = [{column: grouped[key].get(column, "") for column in columns} for key in sorted(grouped)]
    return matrix_rows, columns


def first_row_value(rows: list[JsonObject], key: str) -> str:
    return next((normalize_space(row.get(key)) for row in rows if normalize_space(row.get(key))), "")


def matrix_column_order(clinical_data_type: str, attribute_ids: list[str]) -> list[str]:
    base = ["sample_id", "patient_id"] if clinical_data_type == "SAMPLE" else ["patient_id"]
    return base + [attribute_id for attribute_id in attribute_ids if attribute_id not in base]


def survival_attribute_ids(prefixes: list[str]) -> list[str]:
    attributes: list[str] = []
    for prefix in prefixes:
        attributes.extend([f"{prefix}_STATUS", f"{prefix}_MONTHS"])
    return attributes


def survival_curve_rows(matrix_rows: list[JsonObject], sample_rows: list[JsonObject], prefixes: list[str], *, study_id: str) -> list[JsonObject]:
    samples_by_patient: dict[str, list[str]] = {}
    for sample in sample_rows:
        patient_id = normalize_space(sample.get("patient_id"))
        sample_id = normalize_space(sample.get("sample_id"))
        if patient_id and sample_id:
            samples_by_patient.setdefault(patient_id, []).append(sample_id)
    rows: list[JsonObject] = []
    for matrix_row in matrix_rows:
        patient_id = normalize_space(matrix_row.get("patient_id"))
        if not patient_id:
            continue
        for prefix in prefixes:
            status = normalize_space(matrix_row.get(f"{prefix}_STATUS"))
            months = float_or_none(matrix_row.get(f"{prefix}_MONTHS"))
            if not status and months is None:
                continue
            event_code, event_label, event_observed = parse_event_status(status)
            rows.append(
                {
                    "study_id": study_id,
                    "patient_id": patient_id,
                    "sample_ids": sorted(samples_by_patient.get(patient_id, [])),
                    "endpoint": prefix,
                    "time_months": months,
                    "status": status,
                    "event_code": event_code,
                    "event_label": event_label,
                    "event_observed": event_observed,
                }
            )
    return rows


def parse_event_status(status: str) -> tuple[int | None, str, bool | None]:
    if not status:
        return None, "", None
    if ":" not in status:
        return None, status, None
    code_text, label = status.split(":", 1)
    try:
        code = int(code_text)
    except ValueError:
        return None, label, None
    return code, label, code == 1


def float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def cna_alteration_label(value: int | None) -> str:
    return cna_alteration_labels().get(str(value), "") if value is not None else ""


def cna_alteration_labels() -> JsonObject:
    return {"-2": "HOMDEL", "-1": "HETLOSS", "0": "DIPLOID", "1": "GAIN", "2": "AMP"}


def study_sections(study: JsonObject) -> list[JsonObject]:
    sections = [{"key": "overview", "title": "Overview", "kind": "table", "rows": study_metadata(study)}]
    if study["profiles"]:
        sections.append({"key": "profiles", "title": "Molecular profiles", "kind": "table", "rows": study["profiles"]})
    if study["sample_lists"]:
        sections.append({"key": "sample_lists", "title": "Sample lists", "kind": "table", "rows": study["sample_lists"]})
    return sections


def study_previews(study: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {"kind": "table", "title": "Study summary", "section_key": "overview", "data": {"columns": ["label", "value"], "rows": study_metadata(study)}},
        {"kind": "xref_groups", "title": "cBioPortal links", "actions": display_actions(links), "data": {"groups": study_xref_groups(study)}},
    ]
    if study["profiles"]:
        previews.insert(1, {"kind": "table", "title": "Molecular profiles", "section_key": "profiles", "data": {"rows": study["profiles"]}})
    if study["sample_lists"]:
        previews.insert(1, {"kind": "table", "title": "Sample lists", "section_key": "sample_lists", "data": {"rows": study["sample_lists"]}})
    return previews


def study_metadata(study: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Study ID", study["study_id"]),
        ("Cancer type", study["cancer_type_id"]),
        ("Samples", study["all_sample_count"]),
        ("Sequenced samples", study["sequenced_sample_count"]),
        ("CNA samples", study["cna_sample_count"]),
        ("RNA-seq samples", study["mrna_rnaseq_sample_count"]),
        ("Groups", study["groups"]),
        ("PMID", study["pmid"]),
        ("Citation", study["citation"]),
        ("API", study["api_url"]),
    )


def profile_metadata(profile: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Molecular profile", profile["molecular_profile_id"]),
        ("Study ID", profile["study_id"]),
        ("Alteration type", profile["molecular_alteration_type"]),
        ("Datatype", profile["datatype"]),
        ("Name", profile["name"]),
        ("API", profile["api_url"]),
    )


def sample_list_metadata(sample_list: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Sample list", sample_list["sample_list_id"]),
        ("Study ID", sample_list["study_id"]),
        ("Category", sample_list["category"]),
        ("Samples", sample_list["sample_count"]),
        ("Name", sample_list["name"]),
        ("API", sample_list["api_url"]),
    )


def study_links(study: JsonObject) -> list[JsonObject]:
    links = [
        {"label": "Open cBioPortal study", "url": study["url"], "kind": "external", "primary": True},
        {"label": "Open study API", "url": study["api_url"], "kind": "external"},
        {"label": "Open molecular profiles API", "url": study["profiles_api_url"], "kind": "external"},
        {"label": "Open sample lists API", "url": study["sample_lists_api_url"], "kind": "external"},
    ]
    if study["pmid"]:
        links.append({"label": f"Open PubMed {study['pmid']}", "url": f"https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}/", "kind": "external"})
    return links


def profile_links(profile: JsonObject) -> list[JsonObject]:
    return [
        {"label": "Open cBioPortal study", "url": profile["url"], "kind": "external", "primary": True},
        {"label": "Open molecular profile API", "url": profile["api_url"], "kind": "external"},
    ]


def sample_list_links(sample_list: JsonObject) -> list[JsonObject]:
    return [
        {"label": "Open cBioPortal study", "url": sample_list["url"], "kind": "external", "primary": True},
        {"label": "Open sample list API", "url": sample_list["api_url"], "kind": "external"},
    ]


def study_identifiers(study: JsonObject) -> JsonObject:
    identifiers: JsonObject = {"cbioportal": {"namespace": "cbioportal.study", "id": study["study_id"], "label": study["study_id"], "url": study["url"]}}
    if study["pmid"]:
        identifiers["pubmed"] = {"namespace": "pubmed", "id": study["pmid"], "label": f"PMID:{study['pmid']}", "url": f"https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}/"}
    return identifiers


def study_xref_groups(study: JsonObject) -> list[JsonObject]:
    groups = [{"source": "cBioPortal", "items": [{"label": study["study_id"], "id": study["study_id"], "url": study["url"]}]}]
    if study["pmid"]:
        groups.append({"source": "PubMed", "items": [{"label": f"PMID:{study['pmid']}", "id": study["pmid"], "url": f"https://pubmed.ncbi.nlm.nih.gov/{study['pmid']}/"}]})
    return groups


def profile_xref_groups(profile: JsonObject) -> list[JsonObject]:
    return [{"source": "cBioPortal", "items": [{"label": profile["molecular_profile_id"], "id": profile["molecular_profile_id"], "url": profile["api_url"]}]}]


def sample_list_xref_groups(sample_list: JsonObject) -> list[JsonObject]:
    return [{"source": "cBioPortal", "items": [{"label": sample_list["sample_list_id"], "id": sample_list["sample_list_id"], "url": sample_list["api_url"]}]}]


def mutation_xref_groups(data: JsonObject) -> list[JsonObject]:
    return [
        {
            "source": "cBioPortal",
            "items": [
                {"label": data["molecular_profile_id"], "id": data["molecular_profile_id"], "url": data["api_url"]},
                {"label": data["sample_list_id"], "id": data["sample_list_id"], "url": data["url"]},
            ],
        }
    ]


def molecular_xref_groups(data: JsonObject) -> list[JsonObject]:
    items = []
    if data.get("molecular_profile_id"):
        items.append({"label": data["molecular_profile_id"], "id": data["molecular_profile_id"], "url": data["api_url"]})
    if data.get("sample_list_id"):
        items.append({"label": data["sample_list_id"], "id": data["sample_list_id"], "url": data["url"]})
    if data.get("study_id"):
        items.append({"label": data["study_id"], "id": data["study_id"], "url": data["url"]})
    return [{"source": "cBioPortal", "items": items}]


def clinical_xref_groups(data: JsonObject) -> list[JsonObject]:
    items = [{"label": data["study_id"], "id": data["study_id"], "url": data["url"]}]
    if data.get("api_url"):
        items.append({"label": "clinical API", "id": "clinical-data", "url": data["api_url"]})
    if data.get("sample_ids_api_url"):
        items.append({"label": "sample IDs API", "id": "sample-ids", "url": data["sample_ids_api_url"]})
    if data.get("samples_fetch_api_url"):
        items.append({"label": "samples API", "id": "samples", "url": data["samples_fetch_api_url"]})
    return [{"source": "cBioPortal", "items": items}]


def study_subtitle(study: JsonObject) -> str:
    parts = [study["cancer_type_id"], f"{study['all_sample_count']} samples" if study["all_sample_count"] else "", study["groups"]]
    return "cBioPortal | " + " | ".join(part for part in parts if part)


def profile_subtitle(profile: JsonObject) -> str:
    parts = [profile["study_id"], profile["molecular_alteration_type"], profile["datatype"]]
    return "cBioPortal molecular profile | " + " | ".join(part for part in parts if part)


def sample_list_subtitle(sample_list: JsonObject) -> str:
    parts = [sample_list["study_id"], sample_list["category"]]
    return "cBioPortal sample list | " + " | ".join(part for part in parts if part)


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [{"label": link["label"], "url": link["url"], "kind": link.get("kind", "external")} for link in links if str(link.get("url", "")).startswith(("http://", "https://"))]


def compact_fields(*pairs: tuple[str, Any]) -> list[JsonObject]:
    fields: list[JsonObject] = []
    for label, value in pairs:
        text = normalize_space(value)
        if text:
            fields.append({"label": label, "value": text})
    return fields


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    return [{"label": label, "kind": kind} for label, kind in pairs if normalize_space(label)]


def strip_html(value: Any) -> str:
    return normalize_space(re.sub(r"<[^>]+>", " ", normalize_space(value)))


def int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def study_url(study_id: str, website_base_url: str) -> str:
    return f"{website_base_url.rstrip('/')}/study/summary?id={urllib.parse.quote(study_id)}"


def api_url_for(endpoint: str, api_base_url: str, params: JsonObject) -> str:
    endpoint = endpoint.lstrip("/")
    url = f"{api_base_url.rstrip('/')}/{endpoint}"
    if not params:
        return url
    return f"{url}?{urllib.parse.urlencode(params, doseq=True)}"


def infer_study_id(molecular_profile_id: str, sample_list_id: str) -> str:
    if molecular_profile_id.endswith("_mutations"):
        return molecular_profile_id[: -len("_mutations")]
    if sample_list_id.endswith("_all"):
        return sample_list_id[: -len("_all")]
    return sample_list_id.rsplit("_", 1)[0] if "_" in sample_list_id else ""
