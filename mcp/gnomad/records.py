"""Front-end compatible record envelopes for gnomAD results."""

from __future__ import annotations

from .constants import GNOMAD_GRAPHQL_URL, GNOMAD_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, safe_list


def gnomad_variant_record(
    variant: JsonObject,
    *,
    dataset: str,
    max_populations: int,
    max_transcripts: int,
    website_base_url: str = GNOMAD_WEBSITE_BASE_URL,
    graphql_url: str = GNOMAD_GRAPHQL_URL,
) -> JsonObject:
    normalized = normalize_variant(
        variant,
        dataset=dataset,
        max_populations=max_populations,
        max_transcripts=max_transcripts,
        website_base_url=website_base_url,
        graphql_url=graphql_url,
    )
    variant_id = normalized["variant_id"]
    links = variant_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "genomic.variant",
        "record_type": "gnomad_variant",
        "database": "gnomad",
        "id": variant_id,
        "stable_id": f"gnomAD:{dataset}:{variant_id}",
        "label": variant_id,
        "title": variant_id,
        "description": variant_description(normalized),
        "url": normalized["url"],
        "icon": "gnomad",
        "identifiers": variant_identifiers(normalized),
        "links": links,
        "display": {
            "component": "variant",
            "chip_label": variant_id,
            "icon": "gnomad",
            "title": variant_id,
            "subtitle": variant_subtitle(normalized),
            "description": variant_description(normalized),
            "metadata": variant_metadata(normalized),
            "badges": compact_badges(
                ("gnomAD", "source"),
                (dataset, "dataset"),
                (normalized["location"], "location"),
                (normalized["top_consequence"], "consequence"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": variant_id,
                "subtitle": variant_description(normalized),
                "icon": "gnomad",
                "fields": compact_fields(
                    ("Variant", variant_id),
                    ("Dataset", dataset),
                    ("Location", normalized["location"]),
                    ("Alleles", normalized["alleles"]),
                    ("Genome AF", frequency_label(normalized["genome"])),
                    ("Exome AF", frequency_label(normalized["exome"])),
                    ("Top consequence", normalized["top_consequence"]),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": variant_sections(normalized),
            "previews": variant_previews(normalized, links),
        },
        "related": {
            "genes": normalized["genes"],
            "transcripts": normalized["transcript_consequences"],
            "population_frequencies": normalized["population_rows"],
        },
        "data": normalized,
    }


def gnomad_gene_record(
    gene: JsonObject,
    *,
    reference_genome: str,
    max_transcripts: int,
    website_base_url: str = GNOMAD_WEBSITE_BASE_URL,
    graphql_url: str = GNOMAD_GRAPHQL_URL,
) -> JsonObject:
    normalized = normalize_gene(
        gene,
        reference_genome=reference_genome,
        max_transcripts=max_transcripts,
        website_base_url=website_base_url,
        graphql_url=graphql_url,
    )
    gene_id = normalized["gene_id"]
    title = normalized["symbol"] or gene_id
    links = gene_links(normalized)
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "gene",
        "record_type": "gnomad_gene",
        "database": "gnomad",
        "id": gene_id,
        "stable_id": f"gnomAD:{reference_genome}:{gene_id}",
        "label": title,
        "title": title,
        "description": normalized["name"],
        "url": normalized["url"],
        "icon": "gnomad",
        "identifiers": gene_identifiers(normalized),
        "links": links,
        "display": {
            "component": "gene",
            "chip_label": title,
            "icon": "gnomad",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    gene_id,
                    normalized["reference_genome"],
                    normalized["location"],
                ]
                if part
            ),
            "description": normalized["name"],
            "metadata": gene_metadata(normalized),
            "badges": compact_badges(
                ("gnomAD", "source"),
                (reference_genome, "reference_genome"),
                (gene_id, "identifier"),
                (normalized["symbol"], "symbol"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": normalized["name"],
                "icon": "gnomad",
                "fields": compact_fields(
                    ("Gene ID", gene_id),
                    ("Symbol", normalized["symbol"]),
                    ("Name", normalized["name"]),
                    ("Reference genome", reference_genome),
                    ("Location", normalized["location"]),
                    ("Canonical transcript", normalized["canonical_transcript_id"]),
                    ("pLI", normalize_space(normalized["constraint"].get("pLI"))),
                    ("LOF oe upper", normalize_space(normalized["constraint"].get("oe_lof_upper"))),
                    ("URL", normalized["url"]),
                ),
            },
            "primary_url": normalized["url"],
            "sections": gene_sections(normalized),
            "previews": gene_previews(normalized, links),
        },
        "related": {
            "transcripts": normalized["transcripts"],
            "constraint": normalized["constraint"],
        },
        "data": normalized,
    }


def normalize_variant(
    variant: JsonObject,
    *,
    dataset: str,
    max_populations: int,
    max_transcripts: int,
    website_base_url: str,
    graphql_url: str,
) -> JsonObject:
    variant_id = normalize_space(variant.get("variantId") or variant.get("variant_id"))
    chrom = normalize_space(variant.get("chrom"))
    pos = normalize_space(variant.get("pos"))
    ref = normalize_space(variant.get("ref"))
    alt = normalize_space(variant.get("alt"))
    genome = normalize_frequency(variant.get("genome"), "genome")
    exome = normalize_frequency(variant.get("exome"), "exome")
    transcripts = normalize_transcript_consequences(
        variant.get("transcript_consequences"),
        max_transcripts=max_transcripts,
    )
    population_rows, population_rows_truncated = normalize_population_rows(
        variant,
        max_populations=max_populations,
    )
    genes = variant_genes(transcripts)
    return {
        "variant_id": variant_id,
        "dataset": dataset,
        "chrom": chrom,
        "pos": pos,
        "ref": ref,
        "alt": alt,
        "alleles": f"{ref}>{alt}" if ref and alt else "",
        "location": f"{chrom}:{pos}" if chrom and pos else "",
        "genome": genome,
        "exome": exome,
        "frequency_rows": [item for item in [genome, exome] if item.get("an") or item.get("ac")],
        "population_rows": population_rows,
        "population_rows_truncated": population_rows_truncated,
        "transcript_consequences": transcripts,
        "transcript_consequences_truncated": len(safe_list(variant.get("transcript_consequences"))) > len(transcripts),
        "genes": genes,
        "primary_gene": genes[0]["symbol"] if genes else "",
        "top_consequence": top_consequence(transcripts),
        "url": gnomad_variant_url(variant_id, dataset, website_base_url),
        "api_url": graphql_url,
    }


def normalize_gene(
    gene: JsonObject,
    *,
    reference_genome: str,
    max_transcripts: int,
    website_base_url: str,
    graphql_url: str,
) -> JsonObject:
    gene_id = normalize_space(gene.get("gene_id"))
    chrom = normalize_space(gene.get("chrom"))
    start = normalize_space(gene.get("start"))
    stop = normalize_space(gene.get("stop"))
    transcripts = normalize_gene_transcripts(gene.get("transcripts"), max_transcripts=max_transcripts)
    return {
        "gene_id": gene_id,
        "symbol": normalize_space(gene.get("symbol")),
        "name": normalize_space(gene.get("name")),
        "chrom": chrom,
        "start": start,
        "stop": stop,
        "strand": normalize_space(gene.get("strand")),
        "reference_genome": reference_genome,
        "location": f"{chrom}:{start}-{stop}" if chrom and start and stop else "",
        "canonical_transcript_id": normalize_space(gene.get("canonical_transcript_id")),
        "transcripts": transcripts,
        "transcripts_truncated": len(safe_list(gene.get("transcripts"))) > len(transcripts),
        "constraint": normalize_constraint(gene.get("gnomad_constraint")),
        "url": gnomad_gene_url(gene_id, website_base_url),
        "api_url": graphql_url,
    }


def normalize_frequency(value: object, cohort: str) -> JsonObject:
    item = value if isinstance(value, dict) else {}
    ac = numeric(item.get("ac"))
    an = numeric(item.get("an"))
    af_value = item.get("af")
    af = numeric(af_value) if af_value is not None else calculate_af(ac, an)
    return {
        "cohort": cohort,
        "ac": ac,
        "an": an,
        "af": af,
        "homozygote_count": numeric(item.get("homozygote_count")),
        "filters": [normalize_space(entry) for entry in safe_list(item.get("filters")) if normalize_space(entry)],
    }


def normalize_population_rows(variant: JsonObject, *, max_populations: int) -> tuple[list[JsonObject], bool]:
    rows = []
    for cohort in ["genome", "exome"]:
        source = variant.get(cohort)
        populations = safe_list(source.get("populations") if isinstance(source, dict) else None)
        for item in populations:
            if not isinstance(item, dict):
                continue
            ac = numeric(item.get("ac"))
            an = numeric(item.get("an"))
            rows.append(
                {
                    "cohort": cohort,
                    "population": normalize_space(item.get("id")),
                    "ac": ac,
                    "an": an,
                    "af": calculate_af(ac, an),
                    "homozygote_count": numeric(item.get("homozygote_count")),
                }
            )
    rows.sort(key=population_sort_key)
    return rows[:max_populations], len(rows) > max_populations


def normalize_transcript_consequences(value: object, *, max_transcripts: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value)[:max_transcripts]:
        if not isinstance(item, dict):
            continue
        consequences = [normalize_space(entry) for entry in safe_list(item.get("consequence_terms")) if normalize_space(entry)]
        rows.append(
            {
                "gene_id": normalize_space(item.get("gene_id")),
                "gene_symbol": normalize_space(item.get("gene_symbol")),
                "transcript_id": normalize_space(item.get("transcript_id")),
                "consequence": ", ".join(consequences),
                "hgvsc": normalize_space(item.get("hgvsc")),
                "hgvsp": normalize_space(item.get("hgvsp")),
                "lof": normalize_space(item.get("lof")),
                "lof_filter": normalize_space(item.get("lof_filter")),
                "lof_flags": normalize_space(item.get("lof_flags")),
            }
        )
    return rows


def normalize_gene_transcripts(value: object, *, max_transcripts: int) -> list[JsonObject]:
    rows = []
    for item in safe_list(value)[:max_transcripts]:
        if not isinstance(item, dict):
            continue
        transcript_id = normalize_space(item.get("transcript_id") or item.get("transcriptId"))
        rows.append(
            {
                "transcript_id": transcript_id,
                "transcript_version": normalize_space(item.get("transcript_version")),
            }
        )
    return rows


def normalize_constraint(value: object) -> JsonObject:
    item = value if isinstance(value, dict) else {}
    keys = [
        "exp_syn",
        "obs_syn",
        "oe_syn",
        "exp_mis",
        "obs_mis",
        "oe_mis",
        "exp_lof",
        "obs_lof",
        "oe_lof",
        "oe_lof_upper",
        "pLI",
    ]
    return {key: item.get(key) for key in keys if item.get(key) is not None}


def variant_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "frequencies",
            "title": "Allele frequencies",
            "kind": "table",
            "rows": normalized["frequency_rows"],
            "summary": {"dataset": normalized["dataset"]},
        }
    ]
    if normalized["population_rows"]:
        sections.append(
            {
                "key": "populations",
                "title": "Population frequencies",
                "kind": "table",
                "rows": normalized["population_rows"],
                "summary": {
                    "shown": len(normalized["population_rows"]),
                    "truncated": normalized["population_rows_truncated"],
                },
            }
        )
    if normalized["transcript_consequences"]:
        sections.append(
            {
                "key": "transcript_consequences",
                "title": "Transcript consequences",
                "kind": "table",
                "rows": normalized["transcript_consequences"],
                "summary": {
                    "shown": len(normalized["transcript_consequences"]),
                    "truncated": normalized["transcript_consequences_truncated"],
                },
            }
        )
    return sections


def gene_sections(normalized: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "constraint",
            "title": "Constraint metrics",
            "kind": "table",
            "rows": constraint_rows(normalized["constraint"]),
            "summary": {"reference_genome": normalized["reference_genome"]},
        }
    ]
    if normalized["transcripts"]:
        sections.append(
            {
                "key": "transcripts",
                "title": "Transcripts",
                "kind": "table",
                "rows": normalized["transcripts"],
                "summary": {
                    "shown": len(normalized["transcripts"]),
                    "truncated": normalized["transcripts_truncated"],
                },
            }
        )
    return sections


def variant_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview(
            "frequencies",
            "Allele frequencies",
            normalized["variant_id"],
            normalized["url"],
            frequency_columns(),
            normalized["frequency_rows"],
            actions=display_actions(links),
        )
    ]
    if normalized["population_rows"]:
        previews.append(
            table_preview(
                "populations",
                "Population frequencies",
                normalized["variant_id"],
                normalized["url"],
                population_columns(),
                normalized["population_rows"],
                actions=display_actions(links),
                truncated=normalized["population_rows_truncated"],
            )
        )
    if normalized["transcript_consequences"]:
        previews.append(
            table_preview(
                "transcript_consequences",
                "Transcript consequences",
                normalized["variant_id"],
                normalized["url"],
                transcript_columns(),
                normalized["transcript_consequences"],
                actions=display_actions(links),
                truncated=normalized["transcript_consequences_truncated"],
            )
        )
    previews.append(xref_preview(normalized["variant_id"], normalized["url"], variant_xref_groups(normalized), links))
    return previews


def gene_previews(normalized: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview(
            "constraint",
            "Constraint metrics",
            normalized["gene_id"],
            normalized["url"],
            constraint_columns(),
            constraint_rows(normalized["constraint"]),
            actions=display_actions(links),
        )
    ]
    if normalized["transcripts"]:
        previews.append(
            table_preview(
                "transcripts",
                "Transcripts",
                normalized["gene_id"],
                normalized["url"],
                transcript_id_columns(),
                normalized["transcripts"],
                actions=display_actions(links),
                truncated=normalized["transcripts_truncated"],
            )
        )
    previews.append(xref_preview(normalized["gene_id"], normalized["url"], gene_xref_groups(normalized), links))
    return previews


def table_preview(
    section_key: str,
    title: str,
    identifier: str,
    url: str,
    columns: list[JsonObject],
    rows: list[JsonObject],
    *,
    actions: list[JsonObject],
    truncated: bool = False,
) -> JsonObject:
    return {
        "kind": "table",
        "title": title,
        "provider": "gnomAD",
        "id": identifier,
        "url": url,
        "section_key": section_key,
        "actions": actions,
        "data": {
            "columns": columns,
            "rows": rows,
            "total_rows": len(rows),
            "truncated": truncated,
        },
    }


def xref_preview(identifier: str, url: str, groups: list[JsonObject], links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "xref_groups",
        "title": "Cross-reference groups",
        "provider": "gnomAD",
        "id": identifier,
        "url": url,
        "actions": display_actions(links),
        "data": {"groups": groups},
    }


def variant_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in gnomAD", normalized["url"], primary=True),
        link("gnomAD GraphQL API", normalized["api_url"], kind="related"),
    )


def gene_links(normalized: JsonObject) -> list[JsonObject]:
    return compact_links(
        link("Open in gnomAD", normalized["url"], primary=True),
        link("gnomAD GraphQL API", normalized["api_url"], kind="related"),
    )


def variant_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "gnomad": {
            "namespace": "gnomad.variant",
            "id": normalized["variant_id"],
            "label": f"gnomAD:{normalized['variant_id']}",
            "url": normalized["url"],
        }
    }
    if normalized["primary_gene"]:
        identifiers["gene_symbol"] = {
            "namespace": "gene_symbol",
            "id": normalized["primary_gene"],
            "label": normalized["primary_gene"],
        }
    return identifiers


def gene_identifiers(normalized: JsonObject) -> JsonObject:
    identifiers: JsonObject = {
        "ensembl_gene": {
            "namespace": "ensembl_gene",
            "id": normalized["gene_id"],
            "label": normalized["gene_id"],
            "url": normalized["url"],
        },
        "gnomad": {
            "namespace": "gnomad.gene",
            "id": normalized["gene_id"],
            "label": f"gnomAD:{normalized['gene_id']}",
            "url": normalized["url"],
        },
    }
    if normalized["symbol"]:
        identifiers["gene_symbol"] = {
            "namespace": "gene_symbol",
            "id": normalized["symbol"],
            "label": normalized["symbol"],
        }
    return identifiers


def variant_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    groups = [
        {
            "database": "gnomAD",
            "items": [
                {
                    "id": normalized["variant_id"],
                    "label": f"gnomAD:{normalized['variant_id']}",
                    "url": normalized["url"],
                }
            ],
        }
    ]
    genes = []
    for gene in normalized["genes"]:
        genes.append(
            {
                "id": gene["gene_id"] or gene["symbol"],
                "label": gene["symbol"] or gene["gene_id"],
                "url": gnomad_gene_url(gene["gene_id"], GNOMAD_WEBSITE_BASE_URL) if gene["gene_id"] else "",
            }
        )
    if genes:
        groups.append({"database": "Genes", "items": genes})
    return groups


def gene_xref_groups(normalized: JsonObject) -> list[JsonObject]:
    return [
        {
            "database": "gnomAD",
            "items": [{"id": normalized["gene_id"], "label": normalized["gene_id"], "url": normalized["url"]}],
        },
        {
            "database": "Ensembl",
            "items": [{"id": normalized["gene_id"], "label": normalized["gene_id"], "url": ensembl_gene_url(normalized["gene_id"])}],
        },
    ]


def variant_metadata(normalized: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Variant", normalized["variant_id"]),
        ("Dataset", normalized["dataset"]),
        ("Location", normalized["location"]),
        ("Alleles", normalized["alleles"]),
        ("Genome AF", frequency_label(normalized["genome"])),
        ("Exome AF", frequency_label(normalized["exome"])),
        ("Primary gene", normalized["primary_gene"]),
        ("Top consequence", normalized["top_consequence"]),
    )


def gene_metadata(normalized: JsonObject) -> list[JsonObject]:
    constraint = normalized["constraint"]
    return compact_fields(
        ("Gene ID", normalized["gene_id"]),
        ("Symbol", normalized["symbol"]),
        ("Name", normalized["name"]),
        ("Reference genome", normalized["reference_genome"]),
        ("Location", normalized["location"]),
        ("Canonical transcript", normalized["canonical_transcript_id"]),
        ("pLI", normalize_space(constraint.get("pLI"))),
        ("LOF oe upper", normalize_space(constraint.get("oe_lof_upper"))),
    )


def variant_description(normalized: JsonObject) -> str:
    parts = [
        normalized["alleles"],
        normalized["location"],
        f"genome AF {frequency_label(normalized['genome'])}" if frequency_label(normalized["genome"]) else "",
        f"exome AF {frequency_label(normalized['exome'])}" if frequency_label(normalized["exome"]) else "",
    ]
    return " | ".join(part for part in parts if part)


def variant_subtitle(normalized: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalized["dataset"],
            normalized["location"],
            normalized["primary_gene"],
            normalized["top_consequence"],
        ]
        if part
    )


def frequency_label(item: JsonObject) -> str:
    af = item.get("af")
    if isinstance(af, (int, float)):
        return f"{af:.6g}"
    return ""


def constraint_rows(constraint: JsonObject) -> list[JsonObject]:
    rows = []
    labels = {
        "pLI": "pLI",
        "oe_lof": "LOF observed/expected",
        "oe_lof_upper": "LOF oe upper",
        "oe_mis": "Missense observed/expected",
        "oe_syn": "Synonymous observed/expected",
        "obs_lof": "Observed LOF",
        "exp_lof": "Expected LOF",
        "obs_mis": "Observed missense",
        "exp_mis": "Expected missense",
        "obs_syn": "Observed synonymous",
        "exp_syn": "Expected synonymous",
    }
    for key, label_text in labels.items():
        if constraint.get(key) is not None:
            rows.append({"metric": key, "label": label_text, "value": constraint[key]})
    return rows


def variant_genes(transcripts: list[JsonObject]) -> list[JsonObject]:
    genes = []
    seen: set[str] = set()
    for transcript in transcripts:
        gene_id = normalize_space(transcript.get("gene_id"))
        symbol = normalize_space(transcript.get("gene_symbol"))
        key = gene_id or symbol
        if not key or key in seen:
            continue
        seen.add(key)
        genes.append({"gene_id": gene_id, "symbol": symbol})
    return genes


def top_consequence(transcripts: list[JsonObject]) -> str:
    for transcript in transcripts:
        consequence = normalize_space(transcript.get("consequence"))
        if consequence:
            return consequence
    return ""


def numeric(value: object) -> int | float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    return None


def calculate_af(ac: int | float | None, an: int | float | None) -> float | None:
    if not isinstance(ac, (int, float)) or not isinstance(an, (int, float)) or not an:
        return None
    return float(ac) / float(an)


def population_sort_key(row: JsonObject) -> tuple[int, str, str]:
    population = normalize_space(row.get("population"))
    primary_order = ["afr", "amr", "asj", "eas", "fin", "mid", "nfe", "sas", "remaining", "XX", "XY"]
    cohort_order = {"genome": "0", "exome": "1"}
    try:
        rank = primary_order.index(population)
    except ValueError:
        rank = len(primary_order)
    return (rank, cohort_order.get(normalize_space(row.get("cohort")), "9"), population)


def gnomad_variant_url(variant_id: str, dataset: str, website_base_url: str) -> str:
    base = website_base_url.rstrip("/")
    return f"{base}/variant/{variant_id}?dataset={dataset}"


def gnomad_gene_url(gene_id: str, website_base_url: str) -> str:
    base = website_base_url.rstrip("/")
    return f"{base}/gene/{gene_id}"


def ensembl_gene_url(gene_id: str) -> str:
    return f"https://www.ensembl.org/Homo_sapiens/Gene/Summary?g={gene_id}" if gene_id else ""


def frequency_columns() -> list[JsonObject]:
    return [
        {"key": "cohort", "label": "Cohort"},
        {"key": "ac", "label": "AC"},
        {"key": "an", "label": "AN"},
        {"key": "af", "label": "AF"},
        {"key": "homozygote_count", "label": "Homozygotes"},
        {"key": "filters", "label": "Filters"},
    ]


def population_columns() -> list[JsonObject]:
    return [
        {"key": "cohort", "label": "Cohort"},
        {"key": "population", "label": "Population"},
        {"key": "ac", "label": "AC"},
        {"key": "an", "label": "AN"},
        {"key": "af", "label": "AF"},
        {"key": "homozygote_count", "label": "Homozygotes"},
    ]


def transcript_columns() -> list[JsonObject]:
    return [
        {"key": "gene_symbol", "label": "Gene"},
        {"key": "transcript_id", "label": "Transcript"},
        {"key": "consequence", "label": "Consequence"},
        {"key": "hgvsc", "label": "HGVSc"},
        {"key": "hgvsp", "label": "HGVSp"},
        {"key": "lof", "label": "LOF"},
    ]


def transcript_id_columns() -> list[JsonObject]:
    return [
        {"key": "transcript_id", "label": "Transcript"},
        {"key": "transcript_version", "label": "Version"},
    ]


def constraint_columns() -> list[JsonObject]:
    return [
        {"key": "metric", "label": "Metric"},
        {"key": "label", "label": "Label"},
        {"key": "value", "label": "Value"},
    ]


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


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    badges = []
    for label_text, kind in pairs:
        text = normalize_space(label_text)
        if text:
            badges.append({"label": text, "kind": kind})
    return badges
