"""Front-end compatible record and citation envelopes."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import (
    CITATION_SCHEMA_VERSION,
    RECORD_SCHEMA_VERSION,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .previews import with_ncbi_previews
from .utils import normalize_space


def with_pubmed_compat(response: JsonObject, ids: list[str] | None = None) -> JsonObject:
    """Add stable front-end fields without removing legacy PubMed fields."""

    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    articles = response.get("articles")
    records: list[JsonObject]
    citations: list[JsonObject]
    if isinstance(articles, list) and articles:
        records = [
            pubmed_article_record(article)
            for article in articles
            if isinstance(article, dict)
        ]
        citations = [record["citation"] for record in records]
    else:
        pmids = ids or response.get("pmids") or []
        records = [pubmed_minimal_record(str(pmid)) for pmid in pmids]
        citations = [record["citation"] for record in records]

    response.setdefault("records", records)
    response.setdefault("citations", citations)
    return response


def pubmed_article_record(article: JsonObject) -> JsonObject:
    citation = pubmed_article_citation(article)
    links = pubmed_links(article)
    metadata = compact_fields(
        ("Journal", citation["journal"]),
        ("Journal abbreviation", citation["journal_abbreviation"]),
        ("Authors", format_authors(citation["authors"], limit=3)),
        ("Publication date", citation["publication_date"]),
        ("DOI", citation["doi"]),
        ("PMCID", citation["pmcid"]),
    )
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "literature.article",
        "record_type": "pubmed_article",
        "database": "pubmed",
        "id": citation["id"],
        "stable_id": citation["stable_id"],
        "label": citation["label"],
        "title": citation["title"],
        "description": citation["summary"],
        "url": citation["url"],
        "icon": "pubmed",
        "identifiers": pubmed_identifiers(article),
        "links": links,
        "display": {
            "component": "citation",
            "chip_label": citation["label"],
            "icon": "pubmed",
            "title": citation["title"],
            "subtitle": citation["hover"]["subtitle"],
            "description": citation["summary"],
            "metadata": metadata,
            "badges": compact_badges(
                ("PubMed", "source"),
                (citation["stable_id"], "identifier"),
                (citation["journal_abbreviation"] or citation["journal"], "context"),
            ),
            "actions": display_actions(links),
            "hover": citation["hover"],
            "primary_url": citation["url"],
        },
        "citation": citation,
        "data": article,
    })


def pubmed_minimal_record(pmid: str) -> JsonObject:
    article = {
        "pmid": pmid,
        "title": "",
        "authors": [],
        "journal": "",
        "publication_date": "",
        "article_ids": {"pubmed": pmid},
        "url": pubmed_url(pmid),
    }
    return pubmed_article_record(article)


def pubmed_article_citation(article: JsonObject) -> JsonObject:
    pmid = str(article.get("pmid") or article_id_value(article, "pubmed") or "")
    title = normalize_space(article.get("title"))
    authors = author_names(article)
    journal = journal_name(article)
    journal_abbreviation = journal_abbreviation_name(article)
    publication_date = normalize_space(
        article.get("publication_date") or journal_publication_date(article)
    )
    doi = normalize_space(article.get("doi") or article_id_value(article, "doi"))
    pmcid = normalize_space(
        article.get("pmcid")
        or article_id_value(article, "pmc")
        or article_id_value(article, "pmcid")
    )
    url = normalize_space(article.get("url")) or pubmed_url(pmid)
    label = f"PMID:{pmid}" if pmid else "PubMed"
    summary = citation_summary(authors, journal, publication_date)
    hover = citation_hover(
        label=label,
        title=title,
        authors=authors,
        journal=journal,
        publication_date=publication_date,
        doi=doi,
        pmcid=pmcid,
        url=url,
    )

    return {
        "schema_version": CITATION_SCHEMA_VERSION,
        "type": "citation",
        "citation_type": "article",
        "database": "pubmed",
        "id": pmid,
        "stable_id": label,
        "label": label,
        "title": title,
        "authors": authors,
        "first_author": authors[0] if authors else None,
        "journal": journal,
        "journal_abbreviation": journal_abbreviation,
        "publication_date": publication_date,
        "doi": doi or None,
        "pmcid": pmcid or None,
        "url": url,
        "icon": "pubmed",
        "summary": summary,
        "hover": hover,
        "tooltip": hover,
        "links": pubmed_links(article),
    }


def pubmed_identifiers(article: JsonObject) -> JsonObject:
    pmid = str(article.get("pmid") or article_id_value(article, "pubmed") or "")
    doi = normalize_space(article.get("doi") or article_id_value(article, "doi"))
    pmcid = normalize_space(
        article.get("pmcid")
        or article_id_value(article, "pmc")
        or article_id_value(article, "pmcid")
    )
    identifiers: JsonObject = {}
    if pmid:
        identifiers["pubmed"] = {
            "namespace": "pubmed",
            "id": pmid,
            "label": f"PMID:{pmid}",
            "url": pubmed_url(pmid),
        }
    if doi:
        identifiers["doi"] = {
            "namespace": "doi",
            "id": doi,
            "label": f"DOI:{doi}",
            "url": doi_url(doi),
        }
    if pmcid:
        identifiers["pmc"] = {
            "namespace": "pmc",
            "id": pmcid,
            "label": pmcid if pmcid.upper().startswith("PMC") else f"PMCID:{pmcid}",
            "url": pmc_url(pmcid),
        }
    return identifiers


def pubmed_links(article: JsonObject) -> list[JsonObject]:
    identifiers = pubmed_identifiers(article)
    links = []
    for key, label in [
        ("pubmed", "PubMed"),
        ("doi", "DOI"),
        ("pmc", "PMC"),
    ]:
        identifier = identifiers.get(key)
        if not identifier:
            continue
        links.append(
            {
                "label": label,
                "url": identifier["url"],
                "kind": "external",
                "primary": key == "pubmed",
            }
        )
    return links


def citation_hover(
    *,
    label: str,
    title: str,
    authors: list[str],
    journal: str,
    publication_date: str,
    doi: str,
    pmcid: str,
    url: str,
) -> JsonObject:
    subtitle_parts = [part for part in [journal, publication_date] if part]
    fields = compact_fields(
        ("Identifier", label),
        ("Journal", journal),
        ("Title", title),
        ("Authors", format_authors(authors, limit=6)),
        ("Publication date", publication_date),
        ("DOI", doi),
        ("PMCID", pmcid),
        ("URL", url),
    )
    return {
        "title": title or label,
        "subtitle": " | ".join(subtitle_parts),
        "icon": "pubmed",
        "fields": fields,
    }


def citation_summary(authors: list[str], journal: str, publication_date: str) -> str:
    parts = [
        format_authors(authors, limit=3),
        journal,
        publication_date,
    ]
    return ". ".join(part for part in parts if part)


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
    actions = []
    for link in links:
        if not isinstance(link, dict):
            continue
        url = normalize_space(link.get("url"))
        if not url:
            continue
        actions.append(
            {
                "label": normalize_space(link.get("label")) or "Open",
                "url": url,
                "kind": normalize_space(link.get("kind")) or "external",
                "primary": bool(link.get("primary")),
            }
        )
    return actions


def author_names(article: JsonObject) -> list[str]:
    authors = article.get("authors")
    if not isinstance(authors, list):
        return []
    names = []
    for author in authors:
        if isinstance(author, str):
            name = normalize_space(author)
        elif isinstance(author, dict):
            name = normalize_space(author.get("name"))
        else:
            name = ""
        if name:
            names.append(name)
    return names


def format_authors(authors: list[str], limit: int) -> str:
    if not authors:
        return ""
    if len(authors) <= limit:
        return ", ".join(authors)
    return ", ".join(authors[:limit]) + ", et al."


def journal_name(article: JsonObject) -> str:
    journal = article.get("journal")
    if isinstance(journal, str):
        return normalize_space(journal)
    if isinstance(journal, dict):
        return normalize_space(journal.get("title") or journal.get("iso_abbreviation"))
    return ""


def journal_abbreviation_name(article: JsonObject) -> str:
    journal = article.get("journal")
    if isinstance(journal, dict):
        return normalize_space(journal.get("iso_abbreviation"))
    return normalize_space(article.get("source"))


def journal_publication_date(article: JsonObject) -> str:
    journal = article.get("journal")
    if isinstance(journal, dict):
        return normalize_space(journal.get("publication_date"))
    return ""


def article_id_value(article: JsonObject, key: str) -> str:
    article_ids = article.get("article_ids")
    if not isinstance(article_ids, dict):
        return ""
    value = article_ids.get(key)
    return normalize_space(value)


def pubmed_url(pmid: str) -> str:
    return f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else ""


def doi_url(doi: str) -> str:
    return f"https://doi.org/{urllib.parse.quote(doi, safe='/')}" if doi else ""


def pmc_url(pmcid: str) -> str:
    if not pmcid:
        return ""
    clean = pmcid.strip()
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{urllib.parse.quote(clean)}/"


def with_geo_compat(response: JsonObject) -> JsonObject:
    """Add stable front-end fields for GEO records."""

    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    datasets = response.get("datasets")
    if not isinstance(datasets, list):
        series = response.get("series")
        datasets = [series] if isinstance(series, dict) else []

    records = [
        geo_dataset_record(dataset)
        for dataset in datasets
        if isinstance(dataset, dict)
    ]
    response.setdefault("records", records)
    return response


def geo_dataset_record(dataset: JsonObject) -> JsonObject:
    accession = normalize_space(dataset.get("accession")).upper()
    uid = normalize_space(dataset.get("uid"))
    label = accession or (f"GDS UID:{uid}" if uid else "GEO")
    title = normalize_space(dataset.get("title"))
    url = normalize_space(dataset.get("url")) or geo_accession_url(accession)
    entry_type = normalize_space(dataset.get("entry_type")).upper()
    organism = normalize_space(dataset.get("organism") or dataset.get("taxon"))
    links = geo_links(dataset)
    metadata = geo_display_metadata(dataset)
    hover = geo_hover(
        label=label,
        title=title,
        organism=organism,
        study_type=normalize_space(dataset.get("study_type")),
        sample_count=dataset.get("sample_count"),
        publication_date=normalize_space(dataset.get("publication_date")),
        url=url,
    )
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.dataset",
        "record_type": geo_record_type(dataset),
        "database": "geo",
        "entrez_database": "gds",
        "id": accession or uid,
        "uid": uid,
        "stable_id": accession or f"GDSUID:{uid}",
        "label": label,
        "title": title,
        "description": normalize_space(dataset.get("summary")),
        "url": url,
        "icon": "geo",
        "identifiers": geo_identifiers(dataset),
        "links": links,
        "display": {
            "component": "dataset",
            "chip_label": label,
            "icon": "geo",
            "title": title,
            "subtitle": hover["subtitle"],
            "description": normalize_space(dataset.get("summary")),
            "metadata": metadata,
            "badges": compact_badges(
                ("GEO", "source"),
                (label, "identifier"),
                (entry_type, "record_type"),
                (organism, "context"),
            ),
            "actions": display_actions(links),
            "hover": hover,
            "primary_url": url,
        },
        "related": geo_related(dataset),
        "data": dataset,
    })


def geo_record_type(dataset: JsonObject) -> str:
    entry_type = normalize_space(dataset.get("entry_type")).lower()
    if entry_type == "gse":
        return "geo_series"
    if entry_type == "gsm":
        return "geo_sample"
    if entry_type == "gpl":
        return "geo_platform"
    if entry_type == "gds":
        return "geo_dataset"
    return "geo_record"


def geo_identifiers(dataset: JsonObject) -> JsonObject:
    accession = normalize_space(dataset.get("accession")).upper()
    uid = normalize_space(dataset.get("uid"))
    identifiers: JsonObject = {}
    if accession:
        identifiers["geo"] = {
            "namespace": "geo",
            "id": accession,
            "label": accession,
            "url": geo_accession_url(accession),
        }
    if uid:
        identifiers["ncbi_gds_uid"] = {
            "namespace": "ncbi_gds_uid",
            "id": uid,
            "label": f"GDS UID:{uid}",
        }
    platform = dataset.get("platform")
    if isinstance(platform, dict):
        platform_accession = normalize_space(platform.get("accession")).upper()
        if platform_accession:
            identifiers["geo_platform"] = {
                "namespace": "geo",
                "id": platform_accession,
                "label": platform_accession,
                "url": geo_accession_url(platform_accession),
            }
    bioproject = normalize_space(dataset.get("bioproject"))
    if bioproject:
        identifiers["bioproject"] = {
            "namespace": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": (
                "https://www.ncbi.nlm.nih.gov/bioproject/"
                f"{urllib.parse.quote(bioproject)}"
            ),
        }
    return identifiers


def geo_links(dataset: JsonObject) -> list[JsonObject]:
    accession = normalize_space(dataset.get("accession")).upper()
    links: list[JsonObject] = []
    if accession:
        links.append(
            {
                "label": "GEO",
                "url": geo_accession_url(accession),
                "kind": "external",
                "primary": True,
            }
        )
    for link in dataset.get("download_links", []):
        if isinstance(link, dict) and link.get("url"):
            links.append(link)
    for pmid in dataset.get("pubmed_ids", []):
        if pmid:
            links.append(
                {
                    "label": f"PubMed {pmid}",
                    "url": pubmed_url(str(pmid)),
                    "kind": "external",
                    "primary": False,
                }
            )
    return links


def geo_display_metadata(dataset: JsonObject) -> list[JsonObject]:
    platform = dataset.get("platform")
    platform_accession = ""
    if isinstance(platform, dict):
        platform_accession = normalize_space(platform.get("accession"))
    return compact_fields(
        ("Organism", normalize_space(dataset.get("organism") or dataset.get("taxon"))),
        ("Study type", normalize_space(dataset.get("study_type"))),
        ("Samples", str(dataset.get("sample_count")) if dataset.get("sample_count") is not None else ""),
        ("Platform", platform_accession),
        ("Release date", normalize_space(dataset.get("publication_date"))),
        ("BioProject", normalize_space(dataset.get("bioproject"))),
        ("GEO2R", normalize_space(dataset.get("geo2r"))),
    )


def geo_related(dataset: JsonObject) -> JsonObject:
    related: JsonObject = {}
    samples = []
    for sample in dataset.get("samples", []):
        if not isinstance(sample, dict):
            continue
        accession = normalize_space(sample.get("accession")).upper()
        if not accession:
            continue
        samples.append(
            {
                "type": "geo_sample",
                "id": accession,
                "label": accession,
                "title": normalize_space(sample.get("title")),
                "url": normalize_space(sample.get("url")) or geo_accession_url(accession),
            }
        )
    if samples:
        related["samples"] = samples

    platform = dataset.get("platform")
    if isinstance(platform, dict):
        platform_accession = normalize_space(platform.get("accession")).upper()
        if platform_accession:
            related["platform"] = {
                "type": "geo_platform",
                "id": platform_accession,
                "label": platform_accession,
                "title": normalize_space(platform.get("title")),
                "organism": normalize_space(platform.get("organism")),
                "url": geo_accession_url(platform_accession),
            }

    literature = []
    for pmid in dataset.get("pubmed_ids", []):
        pmid_text = normalize_space(pmid)
        if pmid_text:
            literature.append(
                {
                    "type": "pubmed_article",
                    "id": pmid_text,
                    "label": f"PMID:{pmid_text}",
                    "url": pubmed_url(pmid_text),
                }
            )
    if literature:
        related["literature"] = literature

    bioproject = normalize_space(dataset.get("bioproject"))
    if bioproject:
        related["bioproject"] = {
            "type": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": f"https://www.ncbi.nlm.nih.gov/bioproject/{urllib.parse.quote(bioproject)}",
        }
    return related


def geo_hover(
    *,
    label: str,
    title: str,
    organism: str,
    study_type: str,
    sample_count: Any,
    publication_date: str,
    url: str,
) -> JsonObject:
    subtitle_parts = [part for part in [organism, study_type] if part]
    count_text = str(sample_count) if sample_count not in {None, ""} else ""
    fields = compact_fields(
        ("Identifier", label),
        ("Organism", organism),
        ("Study type", study_type),
        ("Samples", count_text),
        ("Release date", publication_date),
        ("Title", title),
        ("URL", url),
    )
    return {
        "title": title or label,
        "subtitle": " | ".join(subtitle_parts),
        "icon": "geo",
        "fields": fields,
    }


def geo_accession_url(accession: str) -> str:
    accession = normalize_space(accession).upper()
    if not accession:
        return ""
    return (
        "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc="
        f"{urllib.parse.quote(accession)}"
    )
