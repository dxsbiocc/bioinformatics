"""Front-end compatible record envelopes for AlphaFold predictions."""

from __future__ import annotations

from .constants import (
    ALPHAFOLD_WEBSITE_BASE_URL,
    RECORD_SCHEMA_VERSION,
    UNIPROT_WEBSITE_BASE_URL,
    JsonObject,
)
from .utils import normalize_space


def alphafold_record(prediction: JsonObject, *, include_sequence: bool = False) -> JsonObject:
    normalized = normalize_prediction(prediction, include_sequence=include_sequence)
    entry_id = normalized["entry_id"]
    accession = normalized["uniprot_accession"]
    gene = normalized["gene"]
    title = " ".join(part for part in [gene or accession, "AlphaFold structure"] if part)
    links = alphafold_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein.structure",
        "record_type": "alphafold_prediction",
        "database": "alphafold",
        "id": entry_id,
        "stable_id": f"AlphaFold:{entry_id}",
        "label": entry_id,
        "title": title,
        "description": structure_description(normalized),
        "url": normalized["url"],
        "icon": "alphafold",
        "identifiers": alphafold_identifiers(normalized),
        "links": links,
        "display": {
            "component": "protein_structure",
            "chip_label": entry_id,
            "icon": "alphafold",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    accession,
                    normalized["organism"],
                    confidence_label(normalized.get("global_metric_value")),
                ]
                if part
            ),
            "description": normalize_space(normalized.get("uniprot_description")),
            "metadata": structure_metadata(normalized),
            "badges": compact_badges(
                ("AlphaFold DB", "source"),
                (entry_id, "identifier"),
                (accession, "context"),
                ("predicted structure", "record_type"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": " | ".join(
                    part
                    for part in [
                        normalized["organism"],
                        confidence_label(normalized.get("global_metric_value")),
                    ]
                    if part
                ),
                "icon": "alphafold",
                "fields": compact_fields(
                    ("AlphaFold ID", entry_id),
                    ("UniProt", accession),
                    ("Gene", gene),
                    ("Organism", normalized["organism"]),
                    ("TaxID", str(normalized["taxid"]) if normalized["taxid"] else ""),
                    ("Region", region_text(normalized)),
                    ("Mean pLDDT", numeric_text(normalized.get("global_metric_value"))),
                    ("Version", str(normalized["latest_version"]) if normalized["latest_version"] else ""),
                    ("Created", normalized["model_created_date"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": structure_sections(normalized),
            "previews": structure_previews(normalized),
        },
        "related": {
            "uniprot_accession": accession,
            "taxid": normalized["taxid"],
            "downloads": file_links(normalized),
        },
        "data": normalized,
    }


def normalize_prediction(prediction: JsonObject, *, include_sequence: bool) -> JsonObject:
    accession = normalize_space(prediction.get("uniprotAccession"))
    entry_id = normalize_space(prediction.get("entryId"))
    normalized: JsonObject = {
        "entry_id": entry_id,
        "uniprot_accession": accession,
        "uniprot_id": normalize_space(prediction.get("uniprotId")),
        "gene": normalize_space(prediction.get("gene")),
        "uniprot_description": normalize_space(prediction.get("uniprotDescription")),
        "organism": normalize_space(prediction.get("organismScientificName")),
        "taxid": prediction.get("taxId") if prediction.get("taxId") is not None else "",
        "sequence_start": prediction.get("sequenceStart") if prediction.get("sequenceStart") is not None else "",
        "sequence_end": prediction.get("sequenceEnd") if prediction.get("sequenceEnd") is not None else "",
        "uniprot_start": prediction.get("uniprotStart") if prediction.get("uniprotStart") is not None else "",
        "uniprot_end": prediction.get("uniprotEnd") if prediction.get("uniprotEnd") is not None else "",
        "sequence_length": sequence_length(prediction),
        "global_metric_value": prediction.get("globalMetricValue") if prediction.get("globalMetricValue") is not None else "",
        "fraction_plddt_very_high": prediction.get("fractionPlddtVeryHigh") if prediction.get("fractionPlddtVeryHigh") is not None else "",
        "fraction_plddt_confident": prediction.get("fractionPlddtConfident") if prediction.get("fractionPlddtConfident") is not None else "",
        "fraction_plddt_low": prediction.get("fractionPlddtLow") if prediction.get("fractionPlddtLow") is not None else "",
        "fraction_plddt_very_low": prediction.get("fractionPlddtVeryLow") if prediction.get("fractionPlddtVeryLow") is not None else "",
        "latest_version": prediction.get("latestVersion") if prediction.get("latestVersion") is not None else "",
        "all_versions": prediction.get("allVersions") if isinstance(prediction.get("allVersions"), list) else [],
        "model_created_date": normalize_space(prediction.get("modelCreatedDate")),
        "sequence_version_date": normalize_space(prediction.get("sequenceVersionDate")),
        "tool_used": normalize_space(prediction.get("toolUsed")),
        "is_reviewed": bool(prediction.get("isReviewed")),
        "is_uniprot": bool(prediction.get("isUniProt")),
        "is_reference_proteome": bool(prediction.get("isReferenceProteome")),
        "is_complex": bool(prediction.get("isComplex")),
        "url": alphafold_entry_url(accession or entry_id),
        "api_url": alphafold_prediction_api_url(accession or entry_id),
        "pdb_url": normalize_space(prediction.get("pdbUrl")),
        "cif_url": normalize_space(prediction.get("cifUrl")),
        "bcif_url": normalize_space(prediction.get("bcifUrl")),
        "pae_doc_url": normalize_space(prediction.get("paeDocUrl")),
        "pae_image_url": normalize_space(prediction.get("paeImageUrl")),
        "plddt_doc_url": normalize_space(prediction.get("plddtDocUrl")),
        "msa_url": normalize_space(prediction.get("msaUrl")),
        "provider_id": normalize_space(prediction.get("providerId")),
    }
    if include_sequence:
        normalized["sequence"] = normalize_space(prediction.get("sequence"))
        normalized["uniprot_sequence"] = normalize_space(prediction.get("uniprotSequence"))
    return normalized


def alphafold_identifiers(normalized: JsonObject) -> JsonObject:
    entry_id = normalize_space(normalized.get("entry_id"))
    accession = normalize_space(normalized.get("uniprot_accession"))
    identifiers: JsonObject = {
        "alphafold": {
            "namespace": "alphafold",
            "id": entry_id,
            "label": entry_id,
            "url": normalize_space(normalized.get("url")),
        }
    }
    if accession:
        identifiers["uniprot"] = {
            "namespace": "uniprotkb",
            "id": accession,
            "label": f"UniProtKB:{accession}",
            "url": uniprot_entry_url(accession),
        }
    taxid = normalized.get("taxid")
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": str(taxid),
            "label": f"TaxID:{taxid}",
            "url": taxonomy_url(str(taxid)),
        }
    return identifiers


def alphafold_links(normalized: JsonObject) -> list[JsonObject]:
    links: list[JsonObject] = [
        {
            "label": "AlphaFold DB",
            "url": normalize_space(normalized.get("url")),
            "kind": "external",
            "primary": True,
        }
    ]
    accession = normalize_space(normalized.get("uniprot_accession"))
    if accession:
        links.append(
            {
                "label": "UniProtKB",
                "url": uniprot_entry_url(accession),
                "kind": "related",
                "primary": False,
            }
        )
    for link in file_links(normalized):
        links.append(link)
    return [link for link in links if normalize_space(link.get("url"))]


def file_links(normalized: JsonObject) -> list[JsonObject]:
    return [
        link
        for link in [
            file_link("PDB", normalized.get("pdb_url"), "download"),
            file_link("mmCIF", normalized.get("cif_url"), "download"),
            file_link("BinaryCIF", normalized.get("bcif_url"), "download"),
            file_link("PAE JSON", normalized.get("pae_doc_url"), "download"),
            file_link("PAE image", normalized.get("pae_image_url"), "external"),
            file_link("pLDDT data", normalized.get("plddt_doc_url"), "download"),
            file_link("MSA", normalized.get("msa_url"), "download"),
        ]
        if link
    ]


def file_link(label: str, url: object, kind: str) -> JsonObject:
    url_text = normalize_space(url)
    if not url_text:
        return {}
    return {
        "label": label,
        "url": url_text,
        "kind": kind,
        "primary": False,
    }


def structure_previews(normalized: JsonObject) -> list[JsonObject]:
    previews: list[JsonObject] = [
        {
            "kind": "structure_3d",
            "title": "AlphaFold predicted structure",
            "provider": "AlphaFold DB",
            "id": normalize_space(normalized.get("entry_id")),
            "url": normalize_space(normalized.get("url")),
            "format": "alphafold_entry",
            "section_key": "overview",
            "actions": display_actions(alphafold_links(normalized)),
            "data": {
                "entry_id": normalize_space(normalized.get("entry_id")),
                "uniprot_accession": normalize_space(normalized.get("uniprot_accession")),
                "pdb_url": normalize_space(normalized.get("pdb_url")),
                "cif_url": normalize_space(normalized.get("cif_url")),
                "bcif_url": normalize_space(normalized.get("bcif_url")),
                "pae_doc_url": normalize_space(normalized.get("pae_doc_url")),
                "pae_image_url": normalize_space(normalized.get("pae_image_url")),
                "global_metric_value": normalized.get("global_metric_value", ""),
                "latest_version": normalized.get("latest_version", ""),
                "model_created_date": normalize_space(normalized.get("model_created_date")),
                "sequence_start": normalized.get("sequence_start", ""),
                "sequence_end": normalized.get("sequence_end", ""),
            },
        },
        {
            "kind": "download_manifest",
            "title": "Structure files",
            "provider": "AlphaFold DB",
            "id": normalize_space(normalized.get("entry_id")),
            "url": normalize_space(normalized.get("url")),
            "section_key": "downloads",
            "actions": display_actions(file_links(normalized)),
            "data": {
                "files": file_links(normalized),
            },
        },
    ]
    sequence = normalize_space(normalized.get("sequence"))
    if sequence:
        previews.append(
            {
                "kind": "sequence",
                "title": "Model sequence",
                "provider": "AlphaFold DB",
                "id": normalize_space(normalized.get("entry_id")),
                "length": len(sequence),
                "section_key": "sequence",
                "data": {
                    "alphabet": "protein",
                    "sequence": sequence,
                },
            }
        )
    return previews


def structure_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": structure_metadata(normalized),
        },
        {
            "key": "confidence",
            "title": "Confidence",
            "kind": "fields",
            "fields": compact_fields(
                ("Mean pLDDT", numeric_text(normalized.get("global_metric_value"))),
                ("Very high", numeric_text(normalized.get("fraction_plddt_very_high"))),
                ("Confident", numeric_text(normalized.get("fraction_plddt_confident"))),
                ("Low", numeric_text(normalized.get("fraction_plddt_low"))),
                ("Very low", numeric_text(normalized.get("fraction_plddt_very_low"))),
            ),
        },
        {
            "key": "downloads",
            "title": "Downloads",
            "kind": "table",
            "rows": file_links(normalized),
        },
    ]
    sequence = normalize_space(normalized.get("sequence"))
    if sequence:
        sections.append(
            {
                "key": "sequence",
                "title": "Sequence",
                "kind": "text",
                "summary": {
                    "length": len(sequence),
                    "alphabet": "protein",
                },
                "text": sequence,
            }
        )
    return sections


def structure_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("AlphaFold ID", normalize_space(normalized.get("entry_id"))),
        ("UniProt accession", normalize_space(normalized.get("uniprot_accession"))),
        ("UniProt ID", normalize_space(normalized.get("uniprot_id"))),
        ("Gene", normalize_space(normalized.get("gene"))),
        ("Description", normalize_space(normalized.get("uniprot_description"))),
        ("Organism", normalize_space(normalized.get("organism"))),
        ("TaxID", str(normalized.get("taxid")) if normalized.get("taxid") else ""),
        ("Region", region_text(normalized)),
        ("Length", str(normalized.get("sequence_length")) if normalized.get("sequence_length") else ""),
        ("Mean pLDDT", numeric_text(normalized.get("global_metric_value"))),
        ("Version", str(normalized.get("latest_version")) if normalized.get("latest_version") else ""),
        ("Created", normalize_space(normalized.get("model_created_date"))),
        ("Sequence version date", normalize_space(normalized.get("sequence_version_date"))),
        ("Tool", normalize_space(normalized.get("tool_used"))),
        ("Reviewed", "yes" if normalized.get("is_reviewed") else "no"),
    )


def compact_fields(*fields: tuple[str, str | None]) -> list[JsonObject]:
    return [
        {"label": label, "value": value}
        for label, value in fields
        if value
    ]


def compact_badges(*badges: tuple[str | None, str]) -> list[JsonObject]:
    return [
        {"label": label, "kind": kind}
        for label, kind in badges
        if label
    ]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "label": normalize_space(link.get("label")),
            "url": normalize_space(link.get("url")),
            "kind": normalize_space(link.get("kind")) or "external",
            "primary": bool(link.get("primary")),
        }
        for link in links
        if normalize_space(link.get("label")) and normalize_space(link.get("url"))
    ]


def sequence_length(prediction: JsonObject) -> int | str:
    start = prediction.get("sequenceStart")
    end = prediction.get("sequenceEnd")
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return end - start + 1
    sequence = normalize_space(prediction.get("sequence"))
    return len(sequence) if sequence else ""


def region_text(normalized: JsonObject) -> str:
    start = normalized.get("sequence_start")
    end = normalized.get("sequence_end")
    if start and end:
        return f"{start}-{end}"
    return ""


def structure_description(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalize_space(normalized.get("organism")),
            region_text(normalized),
            confidence_label(normalized.get("global_metric_value")),
        ]
        if part
    )


def confidence_label(value: object) -> str:
    text = numeric_text(value)
    return f"mean pLDDT {text}" if text else ""


def numeric_text(value: object) -> str:
    if value in {"", None}:
        return ""
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return normalize_space(value)


def alphafold_entry_url(accession_or_entry_id: str) -> str:
    value = normalize_space(accession_or_entry_id)
    return f"{ALPHAFOLD_WEBSITE_BASE_URL}/entry/{value}" if value else ""


def alphafold_prediction_api_url(accession_or_entry_id: str) -> str:
    value = normalize_space(accession_or_entry_id)
    return f"{ALPHAFOLD_WEBSITE_BASE_URL}/api/prediction/{value}" if value else ""


def uniprot_entry_url(accession: str) -> str:
    accession = normalize_space(accession)
    return f"{UNIPROT_WEBSITE_BASE_URL}/uniprotkb/{accession}/entry" if accession else ""


def taxonomy_url(taxid: str) -> str:
    taxid = normalize_space(taxid)
    return (
        "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id="
        f"{taxid}"
    ) if taxid else ""
