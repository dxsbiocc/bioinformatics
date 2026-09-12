"""Front-end compatible record envelopes for common NCBI databases."""

from __future__ import annotations

import urllib.parse

from .constants import RECORD_SCHEMA_VERSION, RESULT_SCHEMA_VERSION, JsonObject
from .previews import with_ncbi_previews
from .schemas import (
    compact_badges,
    compact_fields,
    display_actions,
    doi_url,
    pubmed_url,
)
from .utils import normalize_space


def with_database_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    database_infos = response.get("database_infos")
    if not isinstance(database_infos, list):
        database_info = response.get("database_info")
        if isinstance(database_info, dict):
            database_infos = [database_info]
        else:
            database_infos = []

    databases = response.get("databases", [])
    records = [
        ncbi_database_record(info)
        for info in database_infos
        if isinstance(info, dict)
    ]
    if not records and isinstance(databases, list):
        records = [
            ncbi_database_record({"db_name": str(database)})
            for database in databases
            if database
        ]
    response.setdefault("records", records)
    return response


def ncbi_database_record(info: JsonObject) -> JsonObject:
    database = normalize_space(info.get("db_name") or info.get("database")).lower()
    title = normalize_space(info.get("menu_name") or database)
    description = normalize_space(info.get("description"))
    fields = info.get("fields") if isinstance(info.get("fields"), list) else []
    links_info = info.get("links") if isinstance(info.get("links"), list) else []
    links = [
        {
            "label": "NCBI database",
            "url": ncbi_database_url(database),
            "kind": "external",
            "primary": True,
        }
    ]
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "database.catalog",
        "record_type": "ncbi_database",
        "database": database,
        "id": database,
        "stable_id": f"NCBI_DB:{database}",
        "label": database,
        "title": title,
        "description": description,
        "url": ncbi_database_url(database),
        "icon": "ncbi",
        "identifiers": {
            "ncbi_database": {
                "namespace": "ncbi_database",
                "id": database,
                "label": database,
                "url": ncbi_database_url(database),
            }
        },
        "links": links,
        "display": {
            "component": "database",
            "chip_label": database,
            "icon": "ncbi",
            "title": title or database,
            "subtitle": description,
            "description": description,
            "metadata": compact_fields(
                ("Database", database),
                ("Build", normalize_space(info.get("build"))),
                ("Count", normalize_space(info.get("count"))),
                ("Last update", normalize_space(info.get("last_update"))),
                ("Search fields", str(len(fields)) if fields else ""),
                ("Link types", str(len(links_info)) if links_info else ""),
            ),
            "badges": compact_badges(("NCBI", "source"), (database, "identifier")),
            "actions": display_actions(links),
            "hover": {
                "title": title or database,
                "subtitle": description,
                "icon": "ncbi",
                "fields": compact_fields(
                    ("Database", database),
                    ("Build", normalize_space(info.get("build"))),
                    ("Count", normalize_space(info.get("count"))),
                    ("Last update", normalize_space(info.get("last_update"))),
                    ("URL", ncbi_database_url(database)),
                ),
            },
            "primary_url": ncbi_database_url(database),
        },
        "data": info,
    })


def with_entrez_links_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    linksets = response.get("linksets")
    records = []
    if isinstance(linksets, list):
        records = [
            entrez_link_record(linkset)
            for linkset in linksets
            if isinstance(linkset, dict)
        ]
    response.setdefault("records", records)
    return response


def entrez_link_record(linkset: JsonObject) -> JsonObject:
    source_database = normalize_space(linkset.get("source_database")).lower()
    source_id = normalize_space(linkset.get("source_id"))
    groups = linkset.get("target_groups")
    groups = groups if isinstance(groups, list) else []
    links = [
        link
        for group in groups
        if isinstance(group, dict)
        for link in group.get("links", [])
        if isinstance(link, dict)
    ]
    target_count = sum(
        int(group.get("count") or 0)
        for group in groups
        if isinstance(group, dict)
    )
    title = f"{source_database}:{source_id} linked records"
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "database.links",
        "record_type": "ncbi_entrez_linkset",
        "database": source_database,
        "id": source_id,
        "stable_id": f"{source_database}:{source_id}:links",
        "label": f"{source_database}:{source_id}",
        "title": title,
        "description": f"{target_count} linked records",
        "url": ncbi_record_url(source_database, source_id),
        "icon": "ncbi",
        "identifiers": {
            "source": {
                "namespace": source_database,
                "id": source_id,
                "label": f"{source_database}:{source_id}",
                "url": ncbi_record_url(source_database, source_id),
            }
        },
        "links": links,
        "display": {
            "component": "linkset",
            "chip_label": f"{source_database}:{source_id}",
            "icon": "ncbi",
            "title": title,
            "subtitle": f"{target_count} linked records",
            "description": "",
            "metadata": compact_fields(
                ("Source database", source_database),
                ("Source ID", source_id),
                ("Target groups", str(len(groups)) if groups else ""),
                ("Linked records", str(target_count)),
            ),
            "badges": compact_badges(
                ("NCBI", "source"),
                (source_database, "database"),
                (source_id, "identifier"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": f"{target_count} linked records",
                "icon": "ncbi",
                "fields": compact_fields(
                    ("Source database", source_database),
                    ("Source ID", source_id),
                    ("Linked records", str(target_count)),
                ),
            },
            "primary_url": ncbi_record_url(source_database, source_id),
        },
        "related": {"target_groups": groups},
        "data": linkset,
    })


def with_gene_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    genes = response.get("genes")
    records = []
    if isinstance(genes, list):
        records = [
            gene_record(gene)
            for gene in genes
            if isinstance(gene, dict)
        ]
    response.setdefault("records", records)
    return response


def gene_record(gene: JsonObject) -> JsonObject:
    gene_id = normalize_space(gene.get("gene_id"))
    symbol = normalize_space(gene.get("symbol"))
    description = normalize_space(gene.get("description"))
    organism = gene.get("organism") if isinstance(gene.get("organism"), dict) else {}
    organism_name = normalize_space(organism.get("scientific_name"))
    taxid = normalize_space(organism.get("taxid"))
    links = gene_links(gene)
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "gene",
        "record_type": "ncbi_gene",
        "database": "gene",
        "id": gene_id,
        "stable_id": f"GeneID:{gene_id}",
        "label": symbol or f"GeneID:{gene_id}",
        "title": symbol or description,
        "description": description,
        "url": gene_url(gene_id),
        "icon": "gene",
        "identifiers": gene_identifiers(gene),
        "links": links,
        "display": {
            "component": "gene",
            "chip_label": symbol or f"GeneID:{gene_id}",
            "icon": "gene",
            "title": symbol or description,
            "subtitle": " | ".join(
                part for part in [description, organism_name] if part
            ),
            "description": normalize_space(gene.get("summary")),
            "metadata": gene_display_metadata(gene),
            "badges": compact_badges(
                ("NCBI Gene", "source"),
                (f"GeneID:{gene_id}", "identifier"),
                (organism_name, "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": symbol or f"GeneID:{gene_id}",
                "subtitle": " | ".join(
                    part for part in [description, organism_name] if part
                ),
                "icon": "gene",
                "fields": compact_fields(
                    ("GeneID", gene_id),
                    ("Symbol", symbol),
                    ("Description", description),
                    ("Organism", organism_name),
                    ("TaxID", taxid),
                    ("Chromosome", normalize_space(gene.get("chromosome"))),
                    ("Map location", normalize_space(gene.get("map_location"))),
                    ("URL", gene_url(gene_id)),
                ),
            },
            "primary_url": gene_url(gene_id),
        },
        "related": gene_related(gene),
        "data": gene,
    })


def gene_identifiers(gene: JsonObject) -> JsonObject:
    gene_id = normalize_space(gene.get("gene_id"))
    organism = gene.get("organism") if isinstance(gene.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    identifiers: JsonObject = {}
    if gene_id:
        identifiers["gene"] = {
            "namespace": "gene",
            "id": gene_id,
            "label": f"GeneID:{gene_id}",
            "url": gene_url(gene_id),
        }
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "url": taxonomy_url(taxid),
        }
    mim_ids = gene.get("mim_ids")
    if isinstance(mim_ids, list) and mim_ids:
        identifiers["omim"] = [
            {
                "namespace": "omim",
                "id": normalize_space(mim_id),
                "label": f"OMIM:{normalize_space(mim_id)}",
                "url": omim_url(normalize_space(mim_id)),
            }
            for mim_id in mim_ids
            if normalize_space(mim_id)
        ]
    return identifiers


def gene_links(gene: JsonObject) -> list[JsonObject]:
    links = []
    gene_id = normalize_space(gene.get("gene_id"))
    if gene_id:
        links.append(
            {
                "label": "NCBI Gene",
                "url": gene_url(gene_id),
                "kind": "external",
                "primary": True,
            }
        )
    organism = gene.get("organism") if isinstance(gene.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    if taxid:
        links.append(
            {
                "label": f"Taxonomy {taxid}",
                "url": taxonomy_url(taxid),
                "kind": "external",
                "primary": False,
            }
        )
    for mim_id in gene.get("mim_ids", []):
        mim_text = normalize_space(mim_id)
        if mim_text:
            links.append(
                {
                    "label": f"OMIM {mim_text}",
                    "url": omim_url(mim_text),
                    "kind": "external",
                    "primary": False,
                }
            )
    return links


def gene_display_metadata(gene: JsonObject) -> list[JsonObject]:
    organism = gene.get("organism") if isinstance(gene.get("organism"), dict) else {}
    aliases = gene.get("aliases") if isinstance(gene.get("aliases"), list) else []
    return compact_fields(
        ("GeneID", normalize_space(gene.get("gene_id"))),
        ("Symbol", normalize_space(gene.get("symbol"))),
        ("Organism", normalize_space(organism.get("scientific_name"))),
        ("TaxID", normalize_space(organism.get("taxid"))),
        ("Chromosome", normalize_space(gene.get("chromosome"))),
        ("Map location", normalize_space(gene.get("map_location"))),
        ("Aliases", ", ".join(str(alias) for alias in aliases[:6])),
        ("Nomenclature status", normalize_space(gene.get("nomenclature_status"))),
    )


def gene_related(gene: JsonObject) -> JsonObject:
    related: JsonObject = {}
    organism = gene.get("organism") if isinstance(gene.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    if taxid:
        related["taxonomy"] = {
            "type": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "title": normalize_space(organism.get("scientific_name")),
            "url": taxonomy_url(taxid),
        }
    mim_ids = gene.get("mim_ids")
    if isinstance(mim_ids, list) and mim_ids:
        related["omim"] = [
            {
                "type": "omim",
                "id": normalize_space(mim_id),
                "label": f"OMIM:{normalize_space(mim_id)}",
                "url": omim_url(normalize_space(mim_id)),
            }
            for mim_id in mim_ids
            if normalize_space(mim_id)
        ]
    return related


def with_taxonomy_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    taxa = response.get("taxa")
    records = []
    if isinstance(taxa, list):
        records = [
            taxonomy_record(taxon)
            for taxon in taxa
            if isinstance(taxon, dict)
        ]
    response.setdefault("records", records)
    return response


def taxonomy_record(taxon: JsonObject) -> JsonObject:
    taxid = normalize_space(taxon.get("taxid"))
    scientific_name = normalize_space(taxon.get("scientific_name"))
    common_name = normalize_space(taxon.get("common_name"))
    links = taxonomy_links(taxon)
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "taxonomy.taxon",
        "record_type": "ncbi_taxonomy",
        "database": "taxonomy",
        "id": taxid,
        "stable_id": f"TaxID:{taxid}",
        "label": scientific_name or f"TaxID:{taxid}",
        "title": scientific_name or f"TaxID:{taxid}",
        "description": normalize_space(taxon.get("rank")),
        "url": taxonomy_url(taxid),
        "icon": "taxonomy",
        "identifiers": {
            "taxonomy": {
                "namespace": "taxonomy",
                "id": taxid,
                "label": f"TaxID:{taxid}",
                "url": taxonomy_url(taxid),
            }
        },
        "links": links,
        "display": {
            "component": "taxonomy",
            "chip_label": scientific_name or f"TaxID:{taxid}",
            "icon": "taxonomy",
            "title": scientific_name or f"TaxID:{taxid}",
            "subtitle": " | ".join(
                part
                for part in [common_name, normalize_space(taxon.get("rank"))]
                if part
            ),
            "description": normalize_space(taxon.get("division")),
            "metadata": taxonomy_display_metadata(taxon),
            "badges": compact_badges(
                ("NCBI Taxonomy", "source"),
                (f"TaxID:{taxid}", "identifier"),
                (normalize_space(taxon.get("rank")), "record_type"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": scientific_name or f"TaxID:{taxid}",
                "subtitle": common_name,
                "icon": "taxonomy",
                "fields": compact_fields(
                    ("TaxID", taxid),
                    ("Scientific name", scientific_name),
                    ("Common name", common_name),
                    ("Rank", normalize_space(taxon.get("rank"))),
                    ("Division", normalize_space(taxon.get("division"))),
                    ("Modified", normalize_space(taxon.get("modification_date"))),
                    ("URL", taxonomy_url(taxid)),
                ),
            },
            "primary_url": taxonomy_url(taxid),
        },
        "data": taxon,
    })


def taxonomy_links(taxon: JsonObject) -> list[JsonObject]:
    taxid = normalize_space(taxon.get("taxid"))
    if not taxid:
        return []
    return [
        {
            "label": "NCBI Taxonomy",
            "url": taxonomy_url(taxid),
            "kind": "external",
            "primary": True,
        }
    ]


def taxonomy_display_metadata(taxon: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("TaxID", normalize_space(taxon.get("taxid"))),
        ("Scientific name", normalize_space(taxon.get("scientific_name"))),
        ("Common name", normalize_space(taxon.get("common_name"))),
        ("Rank", normalize_space(taxon.get("rank"))),
        ("Division", normalize_space(taxon.get("division"))),
        ("GenBank division", normalize_space(taxon.get("genbank_division"))),
        ("Status", normalize_space(taxon.get("status"))),
        ("Modified", normalize_space(taxon.get("modification_date"))),
    )


def with_pmc_id_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    conversions = response.get("conversions")
    records = []
    if isinstance(conversions, list):
        records = [
            pmc_conversion_record(conversion)
            for conversion in conversions
            if isinstance(conversion, dict)
        ]
    response.setdefault("records", records)
    return response


def pmc_conversion_record(conversion: JsonObject) -> JsonObject:
    requested_id = normalize_space(conversion.get("requested_id"))
    pmid = normalize_space(conversion.get("pmid"))
    pmcid = normalize_space(conversion.get("pmcid"))
    doi = normalize_space(conversion.get("doi"))
    status = normalize_space(conversion.get("status")) or "ok"
    label = pmcid or (f"PMID:{pmid}" if pmid else requested_id)
    links = pmc_conversion_links(conversion)
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "literature.identifier",
        "record_type": "pmc_id_conversion",
        "database": "pmc",
        "id": label,
        "stable_id": label,
        "label": label,
        "title": f"PMC ID conversion for {requested_id or label}",
        "description": normalize_space(conversion.get("error")) or status,
        "url": pmc_article_url(pmcid) or pubmed_url(pmid) or doi_url(doi),
        "icon": "pmc",
        "identifiers": pmc_conversion_identifiers(conversion),
        "links": links,
        "display": {
            "component": "identifier_conversion",
            "chip_label": label,
            "icon": "pmc",
            "title": f"PMC ID conversion for {requested_id or label}",
            "subtitle": " | ".join(
                part for part in [pmcid, f"PMID:{pmid}" if pmid else "", doi] if part
            ),
            "description": normalize_space(conversion.get("error")) or status,
            "metadata": compact_fields(
                ("Requested ID", requested_id),
                ("PMCID", pmcid),
                ("PMID", pmid),
                ("DOI", doi),
                ("Status", status),
            ),
            "badges": compact_badges(("PMC", "source"), (label, "identifier")),
            "actions": display_actions(links),
            "hover": {
                "title": f"PMC ID conversion for {requested_id or label}",
                "subtitle": status,
                "icon": "pmc",
                "fields": compact_fields(
                    ("Requested ID", requested_id),
                    ("PMCID", pmcid),
                    ("PMID", pmid),
                    ("DOI", doi),
                    ("Status", status),
                ),
            },
            "primary_url": pmc_article_url(pmcid) or pubmed_url(pmid) or doi_url(doi),
        },
        "data": conversion,
    })


def pmc_conversion_identifiers(conversion: JsonObject) -> JsonObject:
    identifiers: JsonObject = {}
    pmid = normalize_space(conversion.get("pmid"))
    pmcid = normalize_space(conversion.get("pmcid"))
    doi = normalize_space(conversion.get("doi"))
    manuscript_id = normalize_space(conversion.get("manuscript_id"))
    if pmid:
        identifiers["pubmed"] = {
            "namespace": "pubmed",
            "id": pmid,
            "label": f"PMID:{pmid}",
            "url": pubmed_url(pmid),
        }
    if pmcid:
        identifiers["pmc"] = {
            "namespace": "pmc",
            "id": pmcid,
            "label": pmcid,
            "url": pmc_article_url(pmcid),
        }
    if doi:
        identifiers["doi"] = {
            "namespace": "doi",
            "id": doi,
            "label": f"DOI:{doi}",
            "url": doi_url(doi),
        }
    if manuscript_id:
        identifiers["manuscript"] = {
            "namespace": "nihms",
            "id": manuscript_id,
            "label": manuscript_id,
        }
    return identifiers


def pmc_conversion_links(conversion: JsonObject) -> list[JsonObject]:
    links = []
    pmcid = normalize_space(conversion.get("pmcid"))
    pmid = normalize_space(conversion.get("pmid"))
    doi = normalize_space(conversion.get("doi"))
    if pmcid:
        links.append(
            {
                "label": "PMC",
                "url": pmc_article_url(pmcid),
                "kind": "external",
                "primary": True,
            }
        )
    if pmid:
        links.append(
            {
                "label": "PubMed",
                "url": pubmed_url(pmid),
                "kind": "external",
                "primary": not bool(pmcid),
            }
        )
    if doi:
        links.append(
            {
                "label": "DOI",
                "url": doi_url(doi),
                "kind": "external",
                "primary": not bool(pmcid or pmid),
            }
        )
    return links


def ncbi_database_url(database: str) -> str:
    database = normalize_space(database).lower()
    if not database:
        return "https://www.ncbi.nlm.nih.gov/"
    return f"https://www.ncbi.nlm.nih.gov/{urllib.parse.quote(database)}/"


def ncbi_record_url(database: str, identifier: str) -> str:
    database = normalize_space(database).lower()
    identifier = normalize_space(identifier)
    if not database:
        return "https://www.ncbi.nlm.nih.gov/"
    if not identifier:
        return ncbi_database_url(database)
    if database == "pubmed":
        return pubmed_url(identifier)
    if database == "pmc":
        return f"https://www.ncbi.nlm.nih.gov/pmc/?term={urllib.parse.quote(identifier)}"
    if database == "gene":
        return gene_url(identifier)
    if database == "taxonomy":
        return taxonomy_url(identifier)
    if database == "bioproject":
        return bioproject_url(identifier)
    if database == "biosample":
        return biosample_url(identifier)
    if database == "sra":
        return sra_url(identifier)
    return (
        f"https://www.ncbi.nlm.nih.gov/{urllib.parse.quote(database)}/"
        f"?term={urllib.parse.quote(identifier)}"
    )


def gene_url(gene_id: str) -> str:
    gene_id = normalize_space(gene_id)
    if not gene_id:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/gene/{urllib.parse.quote(gene_id)}"


def taxonomy_url(taxid: str) -> str:
    taxid = normalize_space(taxid)
    if not taxid:
        return ""
    return (
        "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id="
        f"{urllib.parse.quote(taxid)}"
    )


def omim_url(mim_id: str) -> str:
    mim_id = normalize_space(mim_id)
    if not mim_id:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/omim/{urllib.parse.quote(mim_id)}"


def pmc_article_url(pmcid: str) -> str:
    pmcid = normalize_space(pmcid).upper()
    if not pmcid:
        return ""
    if not pmcid.startswith("PMC"):
        pmcid = f"PMC{pmcid}"
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{urllib.parse.quote(pmcid)}/"


def bioproject_url(identifier: str) -> str:
    identifier = normalize_space(identifier)
    if not identifier:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/bioproject/{urllib.parse.quote(identifier)}"


def biosample_url(identifier: str) -> str:
    identifier = normalize_space(identifier)
    if not identifier:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/biosample/{urllib.parse.quote(identifier)}"


def sra_url(identifier: str) -> str:
    identifier = normalize_space(identifier)
    if not identifier:
        return ""
    return f"https://www.ncbi.nlm.nih.gov/sra/{urllib.parse.quote(identifier)}"


def sra_run_browser_url(accession: str) -> str:
    accession = normalize_space(accession)
    if not accession:
        return ""
    return (
        "https://trace.ncbi.nlm.nih.gov/Traces/?view=run_browser&acc="
        f"{urllib.parse.quote(accession)}"
    )


def sra_run_selector_url(accession: str) -> str:
    accession = normalize_space(accession)
    if not accession:
        return ""
    return (
        "https://www.ncbi.nlm.nih.gov/Traces/study/?acc="
        f"{urllib.parse.quote(accession)}"
    )
