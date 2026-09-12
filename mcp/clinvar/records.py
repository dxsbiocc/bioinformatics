"""Front-end compatible record envelopes for ClinVar variation records."""

from __future__ import annotations

from .constants import NCBI_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def clinvar_variant_record(summary: JsonObject, *, search_label: str = "") -> JsonObject:
    normalized = normalize_summary(summary, search_label=search_label)
    uid = normalized["uid"]
    accession = normalized["accession"]
    title = normalized["title"] or accession or uid
    links = variant_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "genomic.variant",
        "record_type": "clinvar_variant",
        "database": "clinvar",
        "id": uid,
        "stable_id": accession or f"ClinVar:{uid}",
        "label": accession or uid,
        "title": title,
        "description": variant_description(normalized),
        "url": normalized["url"],
        "icon": "clinvar",
        "identifiers": variant_identifiers(normalized),
        "links": links,
        "display": {
            "component": "variant",
            "chip_label": accession or uid,
            "icon": "clinvar",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    normalized["classification"],
                    normalized["review_status"],
                    normalized["primary_gene"],
                    normalized["primary_location"],
                ]
                if part
            ),
            "description": variant_description(normalized),
            "metadata": variant_metadata(normalized),
            "badges": compact_badges(
                ("ClinVar", "source"),
                (accession or uid, "identifier"),
                (normalized["classification"], "clinical_significance"),
                (normalized["review_status"], "review_status"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": variant_description(normalized),
                "icon": "clinvar",
                "fields": compact_fields(
                    ("ClinVar UID", uid),
                    ("Accession", accession),
                    ("Classification", normalized["classification"]),
                    ("Review status", normalized["review_status"]),
                    ("Last evaluated", normalized["last_evaluated"]),
                    ("Gene", normalized["primary_gene"]),
                    ("Location", normalized["primary_location"]),
                    ("Variation type", normalized["variant_type"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": variant_sections(normalized),
            "previews": variant_previews(normalized, links),
        },
        "related": {
            "genes": normalized["genes"],
            "traits": normalized["traits"],
            "locations": normalized["locations"],
            "xrefs": normalized["xrefs"],
            "supporting_submissions": normalized["supporting_submissions"],
        },
        "data": normalized,
    }


def normalize_summary(summary: JsonObject, *, search_label: str) -> JsonObject:
    uid = normalize_space(summary.get("uid"))
    variation_set = safe_list(summary.get("variation_set"))
    primary_variation = variation_set[0] if variation_set and isinstance(variation_set[0], dict) else {}
    classification = normalize_classification(summary)
    genes = normalize_genes(summary.get("genes"))
    traits = normalize_traits(summary)
    locations = normalize_locations(primary_variation.get("variation_loc"))
    xrefs = normalize_variation_xrefs(primary_variation.get("variation_xrefs"))
    supporting_submissions = normalize_supporting_submissions(summary.get("supporting_submissions"))
    primary_location = first_location(locations)
    accession = normalize_space(summary.get("accession_version") or summary.get("accession"))
    return {
        "uid": uid,
        "accession": accession,
        "accession_root": normalize_space(summary.get("accession")),
        "title": normalize_space(summary.get("title")) or search_label,
        "object_type": normalize_space(summary.get("obj_type")),
        "classification": classification["description"],
        "review_status": classification["review_status"],
        "last_evaluated": classification["last_evaluated"],
        "fda_recognized_database": classification["fda_recognized_database"],
        "variant_type": normalize_space(primary_variation.get("variant_type") or summary.get("obj_type")),
        "variation_name": normalize_space(primary_variation.get("variation_name")),
        "cdna_change": normalize_space(primary_variation.get("cdna_change")),
        "canonical_spdi": normalize_space(primary_variation.get("canonical_spdi")),
        "common_name": normalize_space(primary_variation.get("common_name")),
        "protein_change": normalize_space(summary.get("protein_change")),
        "genes": genes,
        "primary_gene": genes[0]["symbol"] if genes else "",
        "traits": traits,
        "trait_names": [item["name"] for item in traits if item.get("name")],
        "locations": locations,
        "primary_location": primary_location,
        "xrefs": xrefs,
        "allele_frequencies": normalize_allele_frequencies(primary_variation.get("allele_freq_set")),
        "molecular_consequences": normalize_molecular_consequences(summary.get("molecular_consequence_list")),
        "supporting_submissions": supporting_submissions,
        "supporting_submission_count": len(supporting_submissions),
        "search_label": search_label,
        "url": clinvar_variation_url(uid),
        "api_url": clinvar_esummary_url(uid),
    }


def normalize_classification(summary: JsonObject) -> JsonObject:
    for key in [
        "germline_classification",
        "clinical_impact_classification",
        "oncogenicity_classification",
    ]:
        value = summary.get(key)
        if isinstance(value, dict) and normalize_space(value.get("description")):
            return {
                "description": normalize_space(value.get("description")),
                "review_status": normalize_space(value.get("review_status")),
                "last_evaluated": normalize_space(value.get("last_evaluated")),
                "fda_recognized_database": normalize_space(value.get("fda_recognized_database")),
                "trait_set": safe_list(value.get("trait_set")),
            }
    return {
        "description": "",
        "review_status": "",
        "last_evaluated": "",
        "fda_recognized_database": "",
        "trait_set": [],
    }


def normalize_traits(summary: JsonObject) -> list[JsonObject]:
    trait_sets: list[object] = []
    for key in [
        "germline_classification",
        "clinical_impact_classification",
        "oncogenicity_classification",
    ]:
        value = summary.get(key)
        if isinstance(value, dict):
            trait_sets.extend(safe_list(value.get("trait_set")))
    traits = []
    seen: set[str] = set()
    for item in trait_sets:
        if not isinstance(item, dict):
            continue
        name = normalize_space(item.get("trait_name"))
        if not name or name in seen:
            continue
        seen.add(name)
        traits.append(
            {
                "name": name,
                "xrefs": normalize_trait_xrefs(item.get("trait_xrefs")),
            }
        )
    return traits


def normalize_trait_xrefs(value: object) -> list[JsonObject]:
    refs = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        refs.append(
            {
                "database": normalize_space(item.get("db_source")),
                "id": normalize_space(item.get("db_id")),
            }
        )
    return refs


def normalize_genes(value: object) -> list[JsonObject]:
    genes = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        geneid = normalize_space(item.get("geneid"))
        genes.append(
            {
                "symbol": normalize_space(item.get("symbol")),
                "geneid": geneid,
                "strand": normalize_space(item.get("strand")),
                "source": normalize_space(item.get("source")),
                "url": gene_url(geneid),
            }
        )
    return genes


def normalize_locations(value: object) -> list[JsonObject]:
    locations = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        chr_name = normalize_space(item.get("chr"))
        start = normalize_space(item.get("display_start") or item.get("start"))
        stop = normalize_space(item.get("display_stop") or item.get("stop"))
        locations.append(
            {
                "status": normalize_space(item.get("status")),
                "assembly_name": normalize_space(item.get("assembly_name")),
                "chr": chr_name,
                "start": start,
                "stop": stop,
                "band": normalize_space(item.get("band")),
                "assembly_acc_ver": normalize_space(item.get("assembly_acc_ver")),
                "location": f"{chr_name}:{start}-{stop}" if chr_name and start and stop else "",
            }
        )
    return locations


def normalize_variation_xrefs(value: object) -> list[JsonObject]:
    refs = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        database = normalize_space(item.get("db_source"))
        db_id = normalize_space(item.get("db_id"))
        refs.append(
            {
                "database": database,
                "id": db_id,
                "label": xref_label(database, db_id),
                "url": xref_url(database, db_id),
            }
        )
    return refs


def normalize_allele_frequencies(value: object) -> list[JsonObject]:
    freqs = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        freqs.append(
            {
                "source": normalize_space(item.get("source")),
                "value": normalize_space(item.get("value")),
                "minor_allele": normalize_space(item.get("minor_allele")),
            }
        )
    return freqs


def normalize_molecular_consequences(value: object) -> list[JsonObject]:
    rows = []
    for item in safe_list(value):
        if not isinstance(item, dict):
            continue
        rows.append({str(key): normalize_space(val) for key, val in item.items()})
    return rows


def normalize_supporting_submissions(value: object) -> list[JsonObject]:
    if not isinstance(value, dict):
        return []
    rows = []
    for key in ["rcv", "scv"]:
        for accession in safe_list(value.get(key)):
            text = normalize_space(accession)
            if not text:
                continue
            rows.append(
                {
                    "accession": text,
                    "kind": key.upper(),
                    "url": clinvar_accession_url(text),
                }
            )
    return rows


def first_location(locations: list[JsonObject]) -> str:
    current = next((item for item in locations if item.get("status") == "current"), None)
    item = current or (locations[0] if locations else {})
    return normalize_space(item.get("location"))


def variant_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "clinvar": {
            "namespace": "clinvar",
            "id": normalized["uid"],
            "label": normalized["accession"] or f"ClinVar:{normalized['uid']}",
            "url": normalized["url"],
        }
    }
    genes = normalized.get("genes", [])
    if genes:
        identifiers["ncbi_gene"] = [
            {
                "namespace": "geneid",
                "id": gene["geneid"],
                "label": f"GeneID:{gene['geneid']}",
                "url": gene.get("url", ""),
            }
            for gene in genes
            if gene.get("geneid")
        ]
    dbsnp = [xref for xref in normalized.get("xrefs", []) if xref.get("database").lower() == "dbsnp"]
    if dbsnp:
        identifiers["dbsnp"] = [
            {
                "namespace": "dbsnp",
                "id": xref["id"],
                "label": xref["label"],
                "url": xref["url"],
            }
            for xref in dbsnp
        ]
    return identifiers


def variant_links(normalized: JsonObject) -> list[JsonObject]:
    links = [
        link("ClinVar", normalized["url"], primary=True),
        link("E-utilities JSON", normalized["api_url"], kind="related"),
    ]
    for gene in normalized.get("genes", [])[:3]:
        links.append(link(f"NCBI Gene {gene['symbol']}", gene.get("url", ""), kind="related"))
    for xref in normalized.get("xrefs", [])[:5]:
        links.append(link(xref.get("label", ""), xref.get("url", ""), kind="related"))
    return compact_links(*links)


def variant_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("ClinVar UID", normalized["uid"]),
        ("Accession", normalized["accession"]),
        ("Classification", normalized["classification"]),
        ("Review status", normalized["review_status"]),
        ("Last evaluated", normalized["last_evaluated"]),
        ("Gene", normalized["primary_gene"]),
        ("Location", normalized["primary_location"]),
        ("Variation type", normalized["variant_type"]),
        ("Canonical SPDI", normalized["canonical_spdi"]),
    )


def variant_sections(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "key": "overview",
            "title": "Overview",
            "kind": "fields",
            "fields": variant_metadata(normalized),
        },
        {
            "key": "traits",
            "title": "Conditions",
            "kind": "table",
            "rows": normalized.get("traits", []),
        },
        {
            "key": "locations",
            "title": "Locations",
            "kind": "table",
            "rows": normalized.get("locations", []),
        },
        {
            "key": "submissions",
            "title": "Supporting submissions",
            "kind": "table",
            "rows": normalized.get("supporting_submissions", []),
        },
        {
            "key": "xrefs",
            "title": "Cross-references",
            "kind": "table",
            "rows": normalized.get("xrefs", []),
        },
    ]


def variant_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "kind": "table",
            "title": "ClinVar locations",
            "provider": "ClinVar",
            "id": normalized["uid"],
            "url": normalized["url"],
            "section_key": "locations",
            "actions": display_actions(links),
            "data": {
                "columns": location_columns(),
                "rows": normalized.get("locations", []),
                "total_rows": len(normalized.get("locations", [])),
            },
        },
        {
            "kind": "table",
            "title": "Supporting submissions",
            "provider": "ClinVar",
            "id": normalized["uid"],
            "url": normalized["url"],
            "section_key": "submissions",
            "actions": display_actions(links),
            "data": {
                "columns": submission_columns(),
                "rows": normalized.get("supporting_submissions", []),
                "total_rows": len(normalized.get("supporting_submissions", [])),
            },
        },
        {
            "kind": "xref_groups",
            "title": "ClinVar identifiers",
            "provider": "ClinVar",
            "id": normalized["uid"],
            "url": normalized["url"],
            "section_key": "xrefs",
            "actions": display_actions(links),
            "data": {"groups": xref_groups(normalized)},
        },
    ]


def xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups: list[JsonObject] = [
        {
            "database": "ClinVar",
            "items": [
                {
                    "id": normalized["uid"],
                    "label": normalized["accession"] or f"ClinVar:{normalized['uid']}",
                    "url": normalized["url"],
                }
            ],
        }
    ]
    genes = [
        {"id": gene["geneid"], "label": gene["symbol"], "url": gene.get("url", "")}
        for gene in normalized.get("genes", [])
        if gene.get("geneid")
    ]
    if genes:
        groups.append({"database": "NCBI Gene", "items": genes})
    by_database: dict[str, list[JsonObject]] = {}
    for xref in normalized.get("xrefs", []):
        database = normalize_space(xref.get("database")) or "External"
        by_database.setdefault(database, []).append(
            {
                "id": xref.get("id", ""),
                "label": xref.get("label", "") or xref.get("id", ""),
                "url": xref.get("url", ""),
            }
        )
    for database, items in sorted(by_database.items()):
        groups.append({"database": database, "items": items})
    return groups


def variant_description(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalized["classification"],
            normalized["review_status"],
            normalized["primary_gene"],
            normalized["primary_location"],
        ]
        if part
    )


def compact_fields(*fields: tuple[str, str | None]) -> list[JsonObject]:
    return [{"label": label, "value": value} for label, value in fields if value]


def compact_badges(*badges: tuple[str | None, str]) -> list[JsonObject]:
    return [{"label": label, "kind": kind} for label, kind in badges if label]


def compact_links(*links: JsonObject) -> list[JsonObject]:
    return [
        item
        for item in links
        if normalize_space(item.get("label")) and normalize_space(item.get("url"))
    ]


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    return [
        {
            "label": normalize_space(item.get("label")),
            "url": normalize_space(item.get("url")),
            "kind": normalize_space(item.get("kind")) or "external",
            "primary": bool(item.get("primary")),
        }
        for item in links
        if normalize_space(item.get("label")) and normalize_space(item.get("url"))
    ]


def link(label: str, url: str, *, kind: str = "external", primary: bool = False) -> JsonObject:
    return {
        "label": label,
        "url": normalize_space(url),
        "kind": kind,
        "primary": primary,
    }


def location_columns() -> list[JsonObject]:
    return [
        {"key": "assembly_name", "label": "Assembly"},
        {"key": "location", "label": "Location"},
        {"key": "status", "label": "Status"},
        {"key": "band", "label": "Band"},
    ]


def submission_columns() -> list[JsonObject]:
    return [
        {"key": "accession", "label": "Accession"},
        {"key": "kind", "label": "Kind"},
        {"key": "url", "label": "URL"},
    ]


def xref_label(database: str, db_id: str) -> str:
    if database.lower() == "dbsnp":
        return f"rs{db_id}" if db_id and not db_id.lower().startswith("rs") else db_id
    return f"{database}:{db_id}" if database and db_id else db_id


def xref_url(database: str, db_id: str) -> str:
    if not db_id:
        return ""
    if database.lower() == "dbsnp":
        rsid = db_id if db_id.lower().startswith("rs") else f"rs{db_id}"
        return f"{NCBI_WEBSITE_BASE_URL}/snp/{rsid}"
    if database.lower() == "clingen":
        return f"https://reg.clinicalgenome.org/redmine/projects/registry/genboree_registry/by_caid?caid={db_id}"
    return ""


def gene_url(geneid: str) -> str:
    return f"{NCBI_WEBSITE_BASE_URL}/gene/{geneid}" if geneid else ""


def clinvar_variation_url(uid: str) -> str:
    return f"{NCBI_WEBSITE_BASE_URL}/clinvar/variation/{uid}/" if uid else f"{NCBI_WEBSITE_BASE_URL}/clinvar/"


def clinvar_accession_url(accession: str) -> str:
    return f"{NCBI_WEBSITE_BASE_URL}/clinvar/{accession}/" if accession else ""


def clinvar_esummary_url(uid: str) -> str:
    if not uid:
        return ""
    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
        f"?db=clinvar&id={uid}&retmode=json"
    )

