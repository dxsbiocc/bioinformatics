"""Front-end compatible record envelopes for UniProtKB entries."""

from __future__ import annotations

from typing import Any

from .constants import (
    RECORD_SCHEMA_VERSION,
    JsonObject,
)
from .previews import fasta_previews, protein_previews
from .urls import (
    cross_reference_url,
    ncbi_gene_url,
    uniprot_entry_url,
    uniprot_fasta_url,
    uniprot_taxonomy_url,
)
from .utils import compact_strings, normalize_space

FEATURE_CATEGORY_LABELS = {
    "molecule": "Molecule",
    "region": "Domains and regions",
    "site": "Sites",
    "ptm": "PTM",
    "variant": "Variants",
    "secondary_structure": "Structure",
    "other": "Other features",
}

FEATURE_TYPE_CATEGORIES = {
    "chain": "molecule",
    "domain": "region",
    "region": "region",
    "repeat": "region",
    "motif": "region",
    "dna binding": "region",
    "zinc finger": "region",
    "topological domain": "region",
    "transmembrane": "region",
    "active site": "site",
    "binding site": "site",
    "site": "site",
    "modified residue": "ptm",
    "glycosylation": "ptm",
    "lipidation": "ptm",
    "disulfide bond": "ptm",
    "natural variant": "variant",
    "mutagenesis": "variant",
    "helix": "secondary_structure",
    "strand": "secondary_structure",
    "turn": "secondary_structure",
}


def uniprotkb_record(
    entry: JsonObject,
    *,
    include_raw: bool = False,
    include_features: bool = True,
    max_features: int = 40,
    feature_types: list[str] | None = None,
    max_comments: int = 8,
    max_cross_reference_ids: int = 12,
) -> JsonObject:
    normalized = normalize_uniprot_entry(
        entry,
        include_raw=include_raw,
        include_features=include_features,
        max_features=max_features,
        feature_types=feature_types,
        max_comments=max_comments,
        max_cross_reference_ids=max_cross_reference_ids,
    )
    accession = normalized["accession"]
    entry_name = normalized["entry_name"]
    title = normalized["protein_name"] or accession
    genes = normalized["genes"]
    organism = normalized["organism"]
    taxid = normalized["taxid"]
    reviewed_label = "Reviewed" if normalized["reviewed"] else "Unreviewed"
    links = uniprot_links(normalized)
    previews = protein_previews(normalized)
    subtitle = " | ".join(
        part for part in [", ".join(genes[:2]), organism, reviewed_label] if part
    )
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein",
        "record_type": "uniprotkb_entry",
        "database": "uniprotkb",
        "id": accession,
        "stable_id": f"UniProtKB:{accession}",
        "label": accession,
        "title": title,
        "description": normalized["function"],
        "url": uniprot_entry_url(accession),
        "icon": "uniprot",
        "identifiers": uniprot_identifiers(normalized),
        "links": links,
        "display": {
            "component": "protein",
            "chip_label": accession,
            "icon": "uniprot",
            "title": title,
            "subtitle": subtitle,
            "description": normalized["function"],
            "metadata": compact_fields(
                ("Accession", accession),
                ("Entry", entry_name),
                ("Gene", ", ".join(genes[:4])),
                ("Organism", organism),
                ("TaxID", str(taxid) if taxid else ""),
                ("Status", reviewed_label),
                ("Length", str(normalized["length"]) if normalized["length"] else ""),
                ("Mass", str(normalized["mass"]) if normalized["mass"] else ""),
                ("Features", str(normalized["feature_summary"]["total"])),
                ("Keywords", str(len(normalized["keywords"])) if normalized["keywords"] else ""),
                ("Cross references", str(normalized["cross_reference_summary"]["total"])),
            ),
            "badges": compact_badges(
                ("UniProtKB", "source"),
                (f"UniProtKB:{accession}", "identifier"),
                (reviewed_label, "status"),
                (organism, "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": subtitle,
                "icon": "uniprot",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Entry name", entry_name),
                    ("Protein", title),
                    ("Gene", ", ".join(genes[:6])),
                    ("Organism", organism),
                    ("TaxID", str(taxid) if taxid else ""),
                    ("Status", reviewed_label),
                    ("Length", str(normalized["length"]) if normalized["length"] else ""),
                    ("URL", uniprot_entry_url(accession)),
                ),
            },
            "primary_url": uniprot_entry_url(accession),
            "sections": protein_display_sections(normalized),
            "previews": previews,
        },
        "related": {
            "gene_ids": normalized["gene_ids"],
            "pdb_ids": normalized["pdb_ids"],
            "reactome_ids": normalized["reactome_ids"],
            "pubmed_ids": normalized["pubmed_ids"],
            "alphafold_ids": normalized["alphafold_ids"],
            "string_ids": normalized["string_ids"],
            "cross_reference_groups": normalized["cross_reference_groups"],
            "literature_references": normalized["literature_references"],
        },
        "data": normalized,
    }


def fasta_record(accession: str, fasta_text: str) -> JsonObject:
    header, sequence = parse_fasta(fasta_text)
    title = header or accession
    previews = fasta_previews(accession, header, sequence, fasta_text)
    links = [
        {
            "label": "UniProtKB",
            "url": uniprot_entry_url(accession),
            "kind": "external",
            "primary": True,
        },
        {
            "label": "FASTA",
            "url": uniprot_fasta_url(accession),
            "kind": "download",
        },
    ]
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "protein.sequence",
        "record_type": "uniprotkb_fasta",
        "database": "uniprotkb",
        "id": accession,
        "stable_id": f"UniProtKB:{accession}:FASTA",
        "label": accession,
        "title": title,
        "description": f"{len(sequence)} amino acids" if sequence else "",
        "url": uniprot_entry_url(accession),
        "icon": "uniprot",
        "identifiers": {
            "uniprot": {
                "namespace": "uniprotkb",
                "id": accession,
                "label": f"UniProtKB:{accession}",
                "url": uniprot_entry_url(accession),
            }
        },
        "links": links,
        "display": {
            "component": "protein",
            "chip_label": accession,
            "icon": "uniprot",
            "title": title,
            "subtitle": f"{len(sequence)} amino acids" if sequence else "FASTA",
            "description": "",
            "metadata": compact_fields(
                ("Accession", accession),
                ("Length", str(len(sequence)) if sequence else ""),
                ("FASTA", uniprot_fasta_url(accession)),
            ),
            "badges": compact_badges(
                ("UniProtKB", "source"),
                ("FASTA", "format"),
                (f"UniProtKB:{accession}", "identifier"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": f"{len(sequence)} amino acids" if sequence else "FASTA",
                "icon": "uniprot",
                "fields": compact_fields(
                    ("Accession", accession),
                    ("Length", str(len(sequence)) if sequence else ""),
                    ("URL", uniprot_entry_url(accession)),
                    ("FASTA", uniprot_fasta_url(accession)),
                ),
            },
            "primary_url": uniprot_entry_url(accession),
            "previews": previews,
        },
        "data": {
            "accession": accession,
            "header": header,
            "sequence": sequence,
            "length": len(sequence),
            "fasta": fasta_text,
        },
    }


def normalize_uniprot_entry(
    entry: JsonObject,
    *,
    include_raw: bool = False,
    include_features: bool = True,
    max_features: int = 40,
    feature_types: list[str] | None = None,
    max_comments: int = 8,
    max_cross_reference_ids: int = 12,
) -> JsonObject:
    accession = normalize_space(entry.get("primaryAccession"))
    entry_name = normalize_space(entry.get("uniProtkbId"))
    organism = entry.get("organism") if isinstance(entry.get("organism"), dict) else {}
    sequence = entry.get("sequence") if isinstance(entry.get("sequence"), dict) else {}
    cross_references = normalize_cross_references(entry)
    feature_payload = normalize_features(
        entry,
        include_items=include_features,
        max_features=max_features,
        feature_types=feature_types,
    )
    comment_payload = normalize_comments(entry, max_comments=max_comments)
    keyword_payload = normalize_keywords(entry)
    cross_reference_payload = group_cross_references(
        cross_references,
        max_ids=max_cross_reference_ids,
    )
    literature_references = normalize_literature_references(entry)
    pubmed_ids = compact_strings(
        cross_reference_ids(cross_references, "PubMed")
        + literature_pubmed_ids(literature_references)
    )
    entry_audit = entry.get("entryAudit") if isinstance(entry.get("entryAudit"), dict) else {}
    normalized: JsonObject = {
        "accession": accession,
        "secondary_accessions": [
            normalize_space(value)
            for value in entry.get("secondaryAccessions", [])
            if normalize_space(value)
        ]
        if isinstance(entry.get("secondaryAccessions"), list)
        else [],
        "entry_name": entry_name,
        "entry_type": normalize_space(entry.get("entryType")),
        "reviewed": is_reviewed(entry),
        "protein_name": protein_name(entry),
        "protein_existence": normalize_space(entry.get("proteinExistence")),
        "annotation_score": entry.get("annotationScore", ""),
        "genes": gene_names(entry),
        "organism": normalize_space(
            organism.get("scientificName") or organism.get("commonName")
        ),
        "organism_common_name": normalize_space(organism.get("commonName")),
        "taxid": organism.get("taxonId") if organism.get("taxonId") is not None else "",
        "length": sequence.get("length") if sequence.get("length") is not None else "",
        "mass": sequence.get("molWeight") if sequence.get("molWeight") is not None else "",
        "function": function_comment(entry),
        "gene_ids": cross_reference_ids(cross_references, "GeneID"),
        "pdb_ids": cross_reference_ids(cross_references, "PDB"),
        "reactome_ids": cross_reference_ids(cross_references, "Reactome"),
        "pubmed_ids": pubmed_ids,
        "alphafold_ids": cross_reference_ids(cross_references, "AlphaFoldDB"),
        "string_ids": cross_reference_ids(cross_references, "STRING"),
        "keywords": keyword_payload,
        "comments": comment_payload["comments"],
        "comment_summary": comment_payload["summary"],
        "features": feature_payload["features"],
        "feature_summary": feature_payload["summary"],
        "feature_tracks": feature_payload["tracks"],
        "cross_references": cross_references[:50],
        "cross_reference_summary": cross_reference_payload["summary"],
        "cross_reference_groups": cross_reference_payload["groups"],
        "literature_references": literature_references,
        "created": normalize_space(entry_audit.get("firstPublicDate")),
        "modified": normalize_space(entry_audit.get("lastAnnotationUpdateDate")),
        "url": uniprot_entry_url(accession),
        "fasta_url": uniprot_fasta_url(accession),
    }
    if include_raw:
        normalized["raw"] = entry
    return normalized


def protein_name(entry: JsonObject) -> str:
    description = entry.get("proteinDescription")
    if not isinstance(description, dict):
        return ""
    recommended = description.get("recommendedName")
    if isinstance(recommended, dict):
        name = full_name_value(recommended)
        if name:
            return name
    submissions = description.get("submissionNames")
    if isinstance(submissions, list):
        for submission in submissions:
            if isinstance(submission, dict):
                name = full_name_value(submission)
                if name:
                    return name
    alternatives = description.get("alternativeNames")
    if isinstance(alternatives, list):
        for alternative in alternatives:
            if isinstance(alternative, dict):
                name = full_name_value(alternative)
                if name:
                    return name
    return ""


def full_name_value(container: JsonObject) -> str:
    full_name = container.get("fullName")
    if isinstance(full_name, dict):
        return normalize_space(full_name.get("value"))
    return ""


def gene_names(entry: JsonObject) -> list[str]:
    genes = entry.get("genes")
    if not isinstance(genes, list):
        return []
    values: list[Any] = []
    for gene in genes:
        if not isinstance(gene, dict):
            continue
        for key in ["geneName", "orderedLocusNames", "orfNames", "synonyms"]:
            value = gene.get(key)
            if isinstance(value, dict):
                values.append(value.get("value"))
            elif isinstance(value, list):
                values.extend(item.get("value") for item in value if isinstance(item, dict))
    return compact_strings(values)


def normalize_features(
    entry: JsonObject,
    *,
    include_items: bool,
    max_features: int,
    feature_types: list[str] | None,
) -> JsonObject:
    raw_features = entry.get("features")
    if not isinstance(raw_features, list):
        raw_features = []
    normalized_all = [
        normalize_feature(feature)
        for feature in raw_features
        if isinstance(feature, dict)
    ]
    normalized_all = [feature for feature in normalized_all if feature["type"]]
    allowed_types = {feature_type.lower() for feature_type in feature_types or []}
    filtered = [
        feature
        for feature in normalized_all
        if not allowed_types or feature["type"].lower() in allowed_types
    ]
    by_type = counts_by_key(normalized_all, "type")
    returned = filtered[:max_features] if include_items and max_features > 0 else []
    summary: JsonObject = {
        "total": len(normalized_all),
        "matching": len(filtered),
        "returned": len(returned),
        "truncated": len(filtered) > len(returned),
        "by_type": [
            {"type": key, "count": count}
            for key, count in sorted(by_type.items(), key=lambda item: (-item[1], item[0]))
        ],
    }
    return {
        "summary": summary,
        "features": returned,
        "tracks": feature_tracks(returned),
    }


def normalize_feature(feature: JsonObject) -> JsonObject:
    feature_type = normalize_space(feature.get("type"))
    location = feature.get("location") if isinstance(feature.get("location"), dict) else {}
    start = feature_position(location.get("start"))
    end = feature_position(location.get("end"))
    return {
        "type": feature_type,
        "category": feature_category(feature_type),
        "description": normalize_space(feature.get("description")),
        "feature_id": normalize_space(feature.get("featureId")),
        "begin": start,
        "end": end,
        "length": feature_length(start, end),
        "evidences": normalize_evidences(feature.get("evidences")),
    }


def feature_position(value: Any) -> int | str:
    if isinstance(value, dict):
        raw = value.get("value")
        if raw is None:
            return normalize_space(value.get("modifier"))
        try:
            return int(raw)
        except (TypeError, ValueError):
            return normalize_space(raw)
    return ""


def feature_length(start: int | str, end: int | str) -> int | str:
    if isinstance(start, int) and isinstance(end, int) and end >= start:
        return end - start + 1
    return ""


def feature_category(feature_type: str) -> str:
    return FEATURE_TYPE_CATEGORIES.get(feature_type.lower(), "other")


def feature_tracks(features: list[JsonObject]) -> list[JsonObject]:
    grouped: dict[str, list[JsonObject]] = {}
    for feature in features:
        category = normalize_space(feature.get("category")) or "other"
        grouped.setdefault(category, []).append(feature)
    return [
        {
            "key": category,
            "title": FEATURE_CATEGORY_LABELS.get(category, category),
            "features": grouped[category],
        }
        for category in FEATURE_CATEGORY_LABELS
        if category in grouped
    ]


def normalize_evidences(value: Any) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    evidences = []
    for evidence in value[:10]:
        if not isinstance(evidence, dict):
            continue
        evidences.append(
            {
                "code": normalize_space(evidence.get("evidenceCode")),
                "source": normalize_space(evidence.get("source")),
                "id": normalize_space(evidence.get("id")),
            }
        )
    return evidences


def normalize_keywords(entry: JsonObject) -> list[JsonObject]:
    keywords = entry.get("keywords")
    if not isinstance(keywords, list):
        return []
    result = []
    for keyword in keywords:
        if not isinstance(keyword, dict):
            continue
        name = normalize_space(keyword.get("name"))
        if not name:
            continue
        result.append(
            {
                "id": normalize_space(keyword.get("id")),
                "category": normalize_space(keyword.get("category")),
                "name": name,
            }
        )
    return result


def normalize_comments(entry: JsonObject, *, max_comments: int) -> JsonObject:
    comments = entry.get("comments")
    if not isinstance(comments, list):
        comments = []
    normalized = []
    type_counts: dict[str, int] = {}
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        comment_type = normalize_space(comment.get("commentType"))
        if not comment_type:
            continue
        type_counts[comment_type] = type_counts.get(comment_type, 0) + 1
        text = comment_text(comment)
        if text and len(normalized) < max_comments:
            normalized.append({"type": comment_type, "text": text})
    return {
        "comments": normalized,
        "summary": {
            "total": len(comments),
            "returned": len(normalized),
            "truncated": len(comments) > len(normalized),
            "by_type": [
                {"type": key, "count": count}
                for key, count in sorted(type_counts.items(), key=lambda item: (-item[1], item[0]))
            ],
        },
    }


def comment_text(comment: JsonObject) -> str:
    texts = comment.get("texts")
    if isinstance(texts, list):
        values = [
            normalize_space(text.get("value"))
            for text in texts
            if isinstance(text, dict) and normalize_space(text.get("value"))
        ]
        if values:
            return " ".join(values)
    locations = comment.get("subcellularLocations")
    if isinstance(locations, list):
        values = []
        for location in locations:
            if not isinstance(location, dict):
                continue
            for key in ["location", "topology", "orientation"]:
                part = location.get(key)
                if isinstance(part, dict):
                    values.append(part.get("value"))
        compact = compact_strings(values)
        if compact:
            return "; ".join(compact)
    cofactors = comment.get("cofactors")
    if isinstance(cofactors, list):
        values = [
            cofactor.get("name")
            for cofactor in cofactors
            if isinstance(cofactor, dict)
        ]
        compact = compact_strings(values)
        if compact:
            return "; ".join(compact)
    return ""


def normalize_cross_references(entry: JsonObject) -> list[JsonObject]:
    refs = entry.get("uniProtKBCrossReferences")
    if not isinstance(refs, list):
        return []
    normalized = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        database = normalize_space(ref.get("database"))
        ref_id = normalize_space(ref.get("id"))
        if not database or not ref_id:
            continue
        normalized.append(
            {
                "database": database,
                "id": ref_id,
                "properties": ref.get("properties")
                if isinstance(ref.get("properties"), list)
                else [],
            }
        )
    return normalized


def group_cross_references(refs: list[JsonObject], *, max_ids: int) -> JsonObject:
    grouped: dict[str, list[JsonObject]] = {}
    for ref in refs:
        database = normalize_space(ref.get("database"))
        if not database:
            continue
        grouped.setdefault(database, []).append(ref)
    groups = []
    for database, values in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        id_items = []
        for ref in values[:max_ids]:
            ref_id = normalize_space(ref.get("id"))
            item: JsonObject = {"id": ref_id}
            url = cross_reference_url(database, ref_id)
            if url:
                item["url"] = url
            id_items.append(item)
        groups.append(
            {
                "database": database,
                "count": len(values),
                "ids": id_items,
                "truncated": len(values) > len(id_items),
            }
        )
    return {
        "summary": {
            "total": len(refs),
            "database_count": len(groups),
            "top_databases": [
                {"database": group["database"], "count": group["count"]}
                for group in groups[:12]
            ],
        },
        "groups": groups,
    }


def normalize_literature_references(entry: JsonObject, *, max_references: int = 20) -> list[JsonObject]:
    references = entry.get("references")
    if not isinstance(references, list):
        return []
    normalized = []
    for reference in references:
        if not isinstance(reference, dict):
            continue
        citation = reference.get("citation")
        if not isinstance(citation, dict):
            continue
        citation_refs = citation.get("citationCrossReferences")
        xrefs = []
        if isinstance(citation_refs, list):
            for citation_ref in citation_refs:
                if not isinstance(citation_ref, dict):
                    continue
                database = normalize_space(citation_ref.get("database"))
                ref_id = normalize_space(citation_ref.get("id"))
                if not database or not ref_id:
                    continue
                item: JsonObject = {
                    "database": database,
                    "id": ref_id,
                }
                url = cross_reference_url(database, ref_id)
                if url:
                    item["url"] = url
                xrefs.append(item)
        if not xrefs and not normalize_space(citation.get("title")):
            continue
        normalized.append(
            {
                "title": normalize_space(citation.get("title")),
                "authors": citation.get("authors")
                if isinstance(citation.get("authors"), list)
                else [],
                "journal": normalize_space(citation.get("journal")),
                "publication_date": normalize_space(citation.get("publicationDate")),
                "cross_references": xrefs,
            }
        )
        if len(normalized) >= max_references:
            break
    return normalized


def literature_pubmed_ids(references: list[JsonObject]) -> list[str]:
    ids: list[str] = []
    for reference in references:
        xrefs = reference.get("cross_references")
        if not isinstance(xrefs, list):
            continue
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            if normalize_space(xref.get("database")).lower() == "pubmed":
                ids.append(normalize_space(xref.get("id")))
    return [pubmed_id for pubmed_id in ids if pubmed_id]


def cross_reference_ids(refs: list[JsonObject], database: str) -> list[str]:
    return [
        normalize_space(ref.get("id"))
        for ref in refs
        if normalize_space(ref.get("database")).lower() == database.lower()
        and normalize_space(ref.get("id"))
    ]


def function_comment(entry: JsonObject) -> str:
    comments = entry.get("comments")
    if not isinstance(comments, list):
        return ""
    for comment in comments:
        if not isinstance(comment, dict):
            continue
        if normalize_space(comment.get("commentType")).upper() != "FUNCTION":
            continue
        texts = comment.get("texts")
        if isinstance(texts, list):
            values = [
                normalize_space(text.get("value"))
                for text in texts
                if isinstance(text, dict) and normalize_space(text.get("value"))
            ]
            return " ".join(values)
    return ""


def is_reviewed(entry: JsonObject) -> bool:
    return "reviewed" in normalize_space(entry.get("entryType")).lower()


def uniprot_identifiers(normalized: JsonObject) -> JsonObject:
    accession = normalize_space(normalized.get("accession"))
    identifiers: JsonObject = {
        "uniprot": {
            "namespace": "uniprotkb",
            "id": accession,
            "label": f"UniProtKB:{accession}",
            "url": uniprot_entry_url(accession),
        }
    }
    entry_name = normalize_space(normalized.get("entry_name"))
    if entry_name:
        identifiers["entry_name"] = {
            "namespace": "uniprotkb_entry_name",
            "id": entry_name,
            "label": entry_name,
        }
    taxid = normalized.get("taxid")
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": str(taxid),
            "label": f"TaxID:{taxid}",
            "url": uniprot_taxonomy_url(str(taxid)),
        }
    gene_ids = normalized.get("gene_ids")
    if isinstance(gene_ids, list) and gene_ids:
        identifiers["geneid"] = [
            {
                "namespace": "ncbi_gene",
                "id": str(gene_id),
                "label": f"GeneID:{gene_id}",
                "url": ncbi_gene_url(str(gene_id)),
            }
            for gene_id in gene_ids
        ]
    return identifiers


def uniprot_links(normalized: JsonObject) -> list[JsonObject]:
    accession = normalize_space(normalized.get("accession"))
    links: list[JsonObject] = [
        {
            "label": "UniProtKB",
            "url": uniprot_entry_url(accession),
            "kind": "external",
            "primary": True,
        },
        {
            "label": "FASTA",
            "url": uniprot_fasta_url(accession),
            "kind": "download",
        },
    ]
    taxid = normalized.get("taxid")
    if taxid:
        links.append(
            {
                "label": "Taxonomy",
                "url": uniprot_taxonomy_url(str(taxid)),
                "kind": "related",
            }
        )
    gene_ids = normalized.get("gene_ids")
    if isinstance(gene_ids, list):
        for gene_id in gene_ids[:5]:
            links.append(
                {
                    "label": f"GeneID:{gene_id}",
                    "url": ncbi_gene_url(str(gene_id)),
                    "kind": "related",
                }
            )
    for alphafold_id in normalized.get("alphafold_ids", [])[:2]:
        links.append(
            {
                "label": f"AlphaFold:{alphafold_id}",
                "url": cross_reference_url("AlphaFoldDB", str(alphafold_id)),
                "kind": "related",
            }
        )
    for pdb_id in normalized.get("pdb_ids", [])[:3]:
        links.append(
            {
                "label": f"PDB:{pdb_id}",
                "url": cross_reference_url("PDB", str(pdb_id)),
                "kind": "related",
            }
        )
    for reactome_id in normalized.get("reactome_ids", [])[:3]:
        links.append(
            {
                "label": f"Reactome:{reactome_id}",
                "url": cross_reference_url("Reactome", str(reactome_id)),
                "kind": "related",
            }
        )
    for pmid in normalized.get("pubmed_ids", [])[:3]:
        links.append(
            {
                "label": f"PMID:{pmid}",
                "url": cross_reference_url("PubMed", str(pmid)),
                "kind": "related",
            }
        )
    for string_id in normalized.get("string_ids", [])[:2]:
        links.append(
            {
                "label": f"STRING:{string_id}",
                "url": cross_reference_url("STRING", str(string_id)),
                "kind": "related",
            }
        )
    return links


def protein_display_sections(normalized: JsonObject) -> list[JsonObject]:
    sections: list[JsonObject] = [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": compact_fields(
                ("Accession", normalize_space(normalized.get("accession"))),
                ("Entry", normalize_space(normalized.get("entry_name"))),
                ("Protein", normalize_space(normalized.get("protein_name"))),
                ("Genes", ", ".join(normalized.get("genes", []))),
                ("Organism", normalize_space(normalized.get("organism"))),
                ("TaxID", str(normalized.get("taxid")) if normalized.get("taxid") else ""),
                ("Reviewed", "yes" if normalized.get("reviewed") else "no"),
                ("Protein existence", normalize_space(normalized.get("protein_existence"))),
                ("Annotation score", str(normalized.get("annotation_score"))),
                ("Created", normalize_space(normalized.get("created"))),
                ("Modified", normalize_space(normalized.get("modified"))),
            ),
        }
    ]
    function_text = normalize_space(normalized.get("function"))
    if function_text:
        sections.append(
            {
                "key": "function",
                "title": "Function",
                "kind": "text",
                "text": function_text,
            }
        )
    feature_summary = normalized.get("feature_summary")
    if isinstance(feature_summary, dict) and feature_summary.get("total"):
        sections.append(
            {
                "key": "features",
                "title": "Features",
                "kind": "feature_track",
                "summary": feature_summary,
                "tracks": normalized.get("feature_tracks", []),
                "rows": normalized.get("features", []),
            }
        )
    if normalized.get("keywords"):
        sections.append(
            {
                "key": "keywords",
                "title": "Keywords",
                "kind": "list",
                "items": normalized.get("keywords", []),
            }
        )
    comment_summary = normalized.get("comment_summary")
    if isinstance(comment_summary, dict) and comment_summary.get("total"):
        sections.append(
            {
                "key": "comments",
                "title": "Comments",
                "kind": "list",
                "summary": comment_summary,
                "items": normalized.get("comments", []),
            }
        )
    cross_reference_summary = normalized.get("cross_reference_summary")
    if isinstance(cross_reference_summary, dict) and cross_reference_summary.get("total"):
        sections.append(
            {
                "key": "cross_references",
                "title": "Cross references",
                "kind": "xref_groups",
                "summary": cross_reference_summary,
                "groups": normalized.get("cross_reference_groups", []),
            }
        )
    if normalized.get("literature_references"):
        sections.append(
            {
                "key": "literature",
                "title": "Literature",
                "kind": "references",
                "items": normalized.get("literature_references", []),
            }
        )
    return sections


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


def counts_by_key(values: list[JsonObject], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        label = normalize_space(value.get(key))
        if label:
            counts[label] = counts.get(label, 0) + 1
    return counts


def parse_fasta(fasta_text: str) -> tuple[str, str]:
    lines = [line.strip() for line in fasta_text.splitlines() if line.strip()]
    if not lines:
        return "", ""
    header = lines[0][1:] if lines[0].startswith(">") else lines[0]
    sequence = "".join(line for line in lines[1:] if not line.startswith(">"))
    return header, sequence

