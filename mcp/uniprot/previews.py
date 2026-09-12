"""Front-end preview hints for UniProt records."""

from __future__ import annotations

from .constants import JsonObject
from .urls import (
    alphafold_prediction_api_url,
    cross_reference_url,
    uniprot_entry_url,
    uniprot_fasta_url,
)
from .utils import normalize_space


def protein_previews(normalized: JsonObject) -> list[JsonObject]:
    """Return high-level renderer hints backed by normalized UniProt data."""
    accession = normalize_space(normalized.get("accession"))
    if not accession:
        return []
    previews: list[JsonObject] = [
        sequence_preview(
            accession=accession,
            length=normalized.get("length"),
            primary=True,
        )
    ]
    feature_preview = protein_feature_preview(normalized)
    if feature_preview:
        previews.append(feature_preview)
    previews.extend(structure_previews(normalized))
    network_preview = string_network_preview(normalized)
    if network_preview:
        previews.append(network_preview)
    literature_preview = citation_list_preview(normalized)
    if literature_preview:
        previews.append(literature_preview)
    xref_preview = cross_reference_preview(normalized)
    if xref_preview:
        previews.append(xref_preview)
    return previews


def fasta_previews(accession: str, header: str, sequence: str, fasta_text: str) -> list[JsonObject]:
    preview = sequence_preview(
        accession=accession,
        length=len(sequence) if sequence else "",
        primary=True,
    )
    preview["data"] = {
        **preview.get("data", {}),
        "header": header,
        "sequence": sequence,
        "fasta": fasta_text,
    }
    return [preview]


def sequence_preview(*, accession: str, length: object, primary: bool = False) -> JsonObject:
    fasta_url = uniprot_fasta_url(accession)
    return {
        "kind": "sequence",
        "title": "Protein sequence",
        "provider": "UniProtKB",
        "id": accession,
        "url": fasta_url,
        "format": "fasta",
        "mime_type": "text/x-fasta",
        "length": length if length else "",
        "primary": primary,
        "section_key": "overview",
        "actions": compact_actions(
            preview_action("Open UniProtKB", uniprot_entry_url(accession), primary=True),
            preview_action("Download FASTA", fasta_url, kind="download"),
        ),
        "data": {
            "alphabet": "protein",
            "accession": accession,
            "entry_url": uniprot_entry_url(accession),
            "download_url": fasta_url,
        },
    }


def protein_feature_preview(normalized: JsonObject) -> JsonObject | None:
    feature_summary = normalized.get("feature_summary")
    if not isinstance(feature_summary, dict) or not feature_summary.get("total"):
        return None
    accession = normalize_space(normalized.get("accession"))
    return {
        "kind": "feature_track",
        "title": "Sequence features",
        "provider": "UniProtKB",
        "id": accession,
        "section_key": "features",
        "length": normalized.get("length") or "",
        "data": {
            "summary": feature_summary,
            "tracks": normalized.get("feature_tracks", []),
            "rows": normalized.get("features", []),
        },
    }


def structure_previews(normalized: JsonObject) -> list[JsonObject]:
    accession = normalize_space(normalized.get("accession"))
    previews: list[JsonObject] = []
    for alphafold_id in normalized.get("alphafold_ids", [])[:1]:
        alphafold_id = normalize_space(alphafold_id)
        if not alphafold_id:
            continue
        url = cross_reference_url("AlphaFoldDB", alphafold_id)
        previews.append(
            {
                "kind": "structure_3d",
                "title": "AlphaFold predicted structure",
                "provider": "AlphaFold DB",
                "id": alphafold_id,
                "url": url,
                "format": "alphafold_entry",
                "section_key": "cross_references",
                "actions": compact_actions(
                    preview_action("Open AlphaFold", url, primary=True),
                    preview_action(
                        "AlphaFold API",
                        alphafold_prediction_api_url(accession or alphafold_id),
                        kind="related",
                    ),
                ),
                "data": {
                    "source": "uniprot_cross_reference",
                    "accession": accession,
                    "api_url": alphafold_prediction_api_url(accession or alphafold_id),
                },
            }
        )
    for pdb_id in normalized.get("pdb_ids", [])[:1]:
        pdb_id = normalize_space(pdb_id)
        if not pdb_id:
            continue
        url = cross_reference_url("PDB", pdb_id)
        previews.append(
            {
                "kind": "structure_3d",
                "title": "Experimental 3D structure",
                "provider": "RCSB PDB",
                "id": pdb_id,
                "url": url,
                "format": "pdb_entry",
                "section_key": "cross_references",
                "actions": compact_actions(preview_action("Open RCSB PDB", url, primary=True)),
                "data": {
                    "source": "uniprot_cross_reference",
                    "pdb_ids": normalized.get("pdb_ids", [])[:12],
                },
            }
        )
    return previews


def string_network_preview(normalized: JsonObject) -> JsonObject | None:
    string_ids = normalized.get("string_ids")
    if not isinstance(string_ids, list) or not string_ids:
        return None
    string_id = normalize_space(string_ids[0])
    if not string_id:
        return None
    url = cross_reference_url("STRING", string_id)
    accession = normalize_space(normalized.get("accession"))
    return {
        "kind": "network",
        "title": "Protein interaction network",
        "provider": "STRING",
        "id": string_id,
        "url": url,
        "section_key": "cross_references",
        "actions": compact_actions(preview_action("Open STRING", url, primary=True)),
        "data": {
            "source": "uniprot_cross_reference",
            "seed": string_id,
            "accession": accession,
            "nodes": [
                {
                    "id": string_id,
                    "label": ", ".join(normalized.get("genes", [])[:1]) or accession,
                    "database": "STRING",
                }
            ],
            "edges": [],
        },
    }


def citation_list_preview(normalized: JsonObject) -> JsonObject | None:
    pubmed_ids = normalized.get("pubmed_ids")
    references = normalized.get("literature_references")
    if not isinstance(pubmed_ids, list):
        pubmed_ids = []
    if not isinstance(references, list):
        references = []
    if not pubmed_ids and not references:
        return None
    first_url = cross_reference_url("PubMed", str(pubmed_ids[0])) if pubmed_ids else ""
    return {
        "kind": "citation_list",
        "title": "Literature references",
        "provider": "UniProtKB/PubMed",
        "id": normalize_space(pubmed_ids[0]) if pubmed_ids else "",
        "url": first_url,
        "section_key": "literature",
        "actions": compact_actions(preview_action("Open PubMed", first_url, primary=True)),
        "data": {
            "pubmed_ids": pubmed_ids[:20],
            "references": references[:10],
            "count": max(len(pubmed_ids), len(references)),
        },
    }


def cross_reference_preview(normalized: JsonObject) -> JsonObject | None:
    summary = normalized.get("cross_reference_summary")
    groups = normalized.get("cross_reference_groups")
    if not isinstance(summary, dict) or not summary.get("total"):
        return None
    return {
        "kind": "xref_groups",
        "title": "Cross-reference groups",
        "provider": "UniProtKB",
        "id": normalize_space(normalized.get("accession")),
        "section_key": "cross_references",
        "data": {
            "summary": summary,
            "groups": groups if isinstance(groups, list) else [],
        },
    }


def preview_action(
    label: str,
    url: str,
    *,
    kind: str = "external",
    primary: bool = False,
) -> JsonObject:
    if not label or not url:
        return {}
    return {
        "label": label,
        "url": url,
        "kind": kind,
        "primary": primary,
    }


def compact_actions(*actions: JsonObject) -> list[JsonObject]:
    return [
        action
        for action in actions
        if normalize_space(action.get("label")) and normalize_space(action.get("url"))
    ]
