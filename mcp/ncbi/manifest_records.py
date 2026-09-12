"""Front-end record envelopes for download plans, sample sheets, and runtimes."""

from __future__ import annotations

from .constants import RECORD_SCHEMA_VERSION, JsonObject
from .previews import with_ncbi_previews
from .records import bioproject_url, biosample_url, sra_url
from .schemas import compact_badges, compact_fields, display_actions
from .utils import normalize_space


def download_plan_item_record(item: JsonObject) -> JsonObject:
    source = normalize_space(item.get("source")).lower() or normalize_space(
        item.get("database")
    ).lower()
    if source == "geo":
        return geo_download_plan_record(item)
    return sra_download_plan_item_record(item)


def sra_download_plan_item_record(item: JsonObject) -> JsonObject:
    run_accession = normalize_space(item.get("run_accession"))
    experiment_accession = normalize_space(item.get("experiment_accession"))
    study_accession = normalize_space(item.get("study_accession"))
    accession = run_accession or experiment_accession or study_accession
    title = normalize_space(item.get("title")) or f"{accession} download plan"
    organism = normalize_space(item.get("organism"))
    strategy = normalize_space(item.get("library_strategy"))
    layout = normalize_space(item.get("layout"))
    links = normalized_links(item.get("links"))
    primary_url = first_primary_url(links) or normalize_space(item.get("url"))
    commands = item.get("commands") if isinstance(item.get("commands"), dict) else {}

    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": "sra_download_plan_item",
        "database": "sra",
        "id": accession,
        "stable_id": accession,
        "label": accession,
        "title": title,
        "description": " | ".join(part for part in [strategy, layout, organism] if part),
        "url": primary_url,
        "icon": "download",
        "identifiers": sra_download_plan_identifiers(item),
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": accession,
            "icon": "download",
            "title": title,
            "subtitle": " | ".join(part for part in ["SRA", strategy, organism] if part),
            "description": "Metadata-only SRA download plan. No data transfer has been started.",
            "metadata": compact_fields(
                ("Run", run_accession),
                ("Experiment", experiment_accession),
                ("Study", study_accession),
                ("BioProject", normalize_space(item.get("bioproject"))),
                ("BioSample", normalize_space(item.get("biosample"))),
                ("Organism", organism),
                ("Strategy", strategy),
                ("Source", normalize_space(item.get("library_source"))),
                ("Selection", normalize_space(item.get("library_selection"))),
                ("Layout", layout),
                ("Platform", normalize_space(item.get("platform"))),
                ("Instrument", normalize_space(item.get("instrument"))),
                ("Total spots", normalize_space(item.get("total_spots"))),
                ("Total bases", normalize_space(item.get("total_bases"))),
                ("Total size", normalize_space(item.get("total_size"))),
                ("Prefetch", normalize_space(commands.get("prefetch"))),
                ("FASTQ", normalize_space(commands.get("fastq"))),
            ),
            "badges": compact_badges(
                ("NCBI SRA", "source"),
                (accession, "identifier"),
                ("download plan", "record_type"),
                (organism, "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": " | ".join(part for part in [strategy, organism] if part),
                "icon": "download",
                "fields": compact_fields(
                    ("Run", run_accession),
                    ("Experiment", experiment_accession),
                    ("BioProject", normalize_space(item.get("bioproject"))),
                    ("BioSample", normalize_space(item.get("biosample"))),
                    ("Organism", organism),
                    ("FASTQ command", normalize_space(commands.get("fastq"))),
                    ("URL", primary_url),
                ),
            },
            "primary_url": primary_url,
        },
        "related": sra_download_plan_related(item),
        "data": item,
    })


def geo_download_plan_record(plan: JsonObject) -> JsonObject:
    accession = normalize_space(plan.get("accession")).upper()
    title = normalize_space(plan.get("title")) or f"{accession} download plan"
    organism = normalize_space(plan.get("organism"))
    sample_count = plan.get("sample_count")
    links = normalized_links(plan.get("links") or plan.get("download_links"))
    primary_url = first_primary_url(links) or normalize_space(plan.get("url"))
    matrix_url = first_link_url(links, "Series matrix")

    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.download_plan",
        "record_type": "geo_download_plan",
        "database": "geo",
        "entrez_database": "gds",
        "id": accession,
        "stable_id": f"{accession}:download-plan" if accession else "GEO:download-plan",
        "label": accession or "GEO",
        "title": title,
        "description": " | ".join(
            part
            for part in [organism, count_text(sample_count, "sample", "samples")]
            if part
        ),
        "url": primary_url,
        "icon": "download",
        "identifiers": geo_download_plan_identifiers(plan),
        "links": links,
        "display": {
            "component": "download_plan",
            "chip_label": accession or "GEO",
            "icon": "download",
            "title": title,
            "subtitle": " | ".join(part for part in ["GEO", organism] if part),
            "description": "Metadata-only GEO download plan. No data transfer has been started.",
            "metadata": compact_fields(
                ("Series", accession),
                ("Organism", organism),
                ("Study type", normalize_space(plan.get("study_type"))),
                ("Samples", str(sample_count) if sample_count not in {None, ""} else ""),
                ("Platform", normalize_space(plan.get("platform_accession"))),
                ("BioProject", normalize_space(plan.get("bioproject"))),
                ("PubMed", ", ".join(str(pmid) for pmid in plan.get("pubmed_ids", []))),
                ("Series matrix", matrix_url),
            ),
            "badges": compact_badges(
                ("GEO", "source"),
                (accession, "identifier"),
                ("download plan", "record_type"),
                (organism, "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": " | ".join(part for part in [organism, normalize_space(plan.get("study_type"))] if part),
                "icon": "download",
                "fields": compact_fields(
                    ("Series", accession),
                    ("Organism", organism),
                    ("Samples", str(sample_count) if sample_count not in {None, ""} else ""),
                    ("Platform", normalize_space(plan.get("platform_accession"))),
                    ("BioProject", normalize_space(plan.get("bioproject"))),
                    ("URL", primary_url),
                ),
            },
            "primary_url": primary_url,
        },
        "related": {
            "samples": plan.get("samples", []),
            "pubmed_ids": plan.get("pubmed_ids", []),
            "bioproject": normalize_space(plan.get("bioproject")),
        },
        "data": plan,
    })


def sample_sheet_record(sheet: JsonObject) -> JsonObject:
    source = normalize_space(sheet.get("source")).lower() or "omics"
    query = normalize_space(sheet.get("query"))
    title = normalize_space(sheet.get("title")) or f"{query} sample sheet"
    rows = sheet.get("rows") if isinstance(sheet.get("rows"), list) else []
    columns = sheet.get("columns") if isinstance(sheet.get("columns"), list) else []
    links = normalized_links(sheet.get("links"))
    primary_url = first_primary_url(links) or normalize_space(sheet.get("url"))
    stable_id = f"{source}:{query}:sample-sheet" if query else f"{source}:sample-sheet"

    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.sample_sheet",
        "record_type": "omics_sample_sheet",
        "database": source,
        "id": query,
        "stable_id": stable_id,
        "label": f"{query} sample sheet" if query else "Sample sheet",
        "title": title,
        "description": f"{len(rows)} rows, {len(columns)} columns",
        "url": primary_url,
        "icon": "table",
        "identifiers": {
            "source_query": {
                "namespace": source,
                "id": query,
                "label": query,
                "url": primary_url,
            }
        },
        "links": links,
        "display": {
            "component": "sample_sheet",
            "chip_label": f"{query} samples" if query else "Samples",
            "icon": "table",
            "title": title,
            "subtitle": f"{source.upper()} | {len(rows)} rows",
            "description": "Front-end-ready sample metadata table.",
            "metadata": compact_fields(
                ("Source", source),
                ("Query", query),
                ("Rows", str(len(rows))),
                ("Columns", str(len(columns))),
                ("Primary key", normalize_space(sheet.get("primary_key"))),
            ),
            "badges": compact_badges(
                (source.upper(), "source"),
                ("sample sheet", "record_type"),
                (f"{len(rows)} rows", "count"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": f"{len(rows)} rows, {len(columns)} columns",
                "icon": "table",
                "fields": compact_fields(
                    ("Source", source),
                    ("Query", query),
                    ("Rows", str(len(rows))),
                    ("Columns", str(len(columns))),
                    ("URL", primary_url),
                ),
            },
            "primary_url": primary_url,
        },
        "data": sheet,
    })


def runtime_status_record(status: JsonObject) -> JsonObject:
    tool = normalize_space(status.get("tool"))
    available = bool(status.get("available"))
    path = normalize_space(status.get("path"))
    version = normalize_space(status.get("version"))
    title = f"{tool} runtime"

    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "runtime.tool",
        "record_type": "tool_runtime_status",
        "database": "local_runtime",
        "id": tool,
        "stable_id": f"runtime:{tool}",
        "label": tool,
        "title": title,
        "description": "available" if available else "missing",
        "url": "",
        "icon": "terminal",
        "identifiers": {
            "runtime_tool": {
                "namespace": "runtime_tool",
                "id": tool,
                "label": tool,
            }
        },
        "links": [],
        "display": {
            "component": "runtime_status",
            "chip_label": tool,
            "icon": "terminal",
            "title": title,
            "subtitle": "available" if available else "missing",
            "description": path or normalize_space(status.get("version_error")),
            "metadata": compact_fields(
                ("Tool", tool),
                ("Available", "yes" if available else "no"),
                ("Path", path),
                ("Version", version),
                ("Version check", normalize_space(status.get("version_error"))),
            ),
            "badges": compact_badges(
                ("local runtime", "source"),
                (tool, "identifier"),
                ("available" if available else "missing", "status"),
            ),
            "actions": [],
            "hover": {
                "title": title,
                "subtitle": "available" if available else "missing",
                "icon": "terminal",
                "fields": compact_fields(
                    ("Tool", tool),
                    ("Available", "yes" if available else "no"),
                    ("Path", path),
                    ("Version", version),
                    ("Version check", normalize_space(status.get("version_error"))),
                ),
            },
            "primary_url": "",
        },
        "data": status,
    })


def sra_download_plan_identifiers(item: JsonObject) -> JsonObject:
    identifiers: JsonObject = {}
    run_accession = normalize_space(item.get("run_accession"))
    experiment_accession = normalize_space(item.get("experiment_accession"))
    study_accession = normalize_space(item.get("study_accession"))
    bioproject = normalize_space(item.get("bioproject"))
    biosample = normalize_space(item.get("biosample"))
    if run_accession:
        identifiers["sra_run"] = {
            "namespace": "sra_run",
            "id": run_accession,
            "label": run_accession,
            "url": sra_url(run_accession),
        }
    if experiment_accession:
        identifiers["sra_experiment"] = {
            "namespace": "sra_experiment",
            "id": experiment_accession,
            "label": experiment_accession,
            "url": sra_url(experiment_accession),
        }
    if study_accession:
        identifiers["sra_study"] = {
            "namespace": "sra_study",
            "id": study_accession,
            "label": study_accession,
            "url": sra_url(study_accession),
        }
    if bioproject:
        identifiers["bioproject"] = {
            "namespace": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": bioproject_url(bioproject),
        }
    if biosample:
        identifiers["biosample"] = {
            "namespace": "biosample",
            "id": biosample,
            "label": biosample,
            "url": biosample_url(biosample),
        }
    return identifiers


def geo_download_plan_identifiers(plan: JsonObject) -> JsonObject:
    accession = normalize_space(plan.get("accession")).upper()
    identifiers: JsonObject = {}
    if accession:
        identifiers["geo"] = {
            "namespace": "geo",
            "id": accession,
            "label": accession,
            "url": normalize_space(plan.get("url")),
        }
    bioproject = normalize_space(plan.get("bioproject"))
    if bioproject:
        identifiers["bioproject"] = {
            "namespace": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": bioproject_url(bioproject),
        }
    return identifiers


def sra_download_plan_related(item: JsonObject) -> JsonObject:
    related: JsonObject = {}
    bioproject = normalize_space(item.get("bioproject"))
    biosample = normalize_space(item.get("biosample"))
    if bioproject:
        related["bioproject"] = {
            "type": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": bioproject_url(bioproject),
        }
    if biosample:
        related["biosample"] = {
            "type": "biosample",
            "id": biosample,
            "label": biosample,
            "url": biosample_url(biosample),
        }
    return related


def normalized_links(value: object) -> list[JsonObject]:
    if not isinstance(value, list):
        return []
    seen = set()
    links = []
    for item in value:
        if not isinstance(item, dict):
            continue
        url = normalize_space(item.get("url"))
        label = normalize_space(item.get("label")) or url
        if not url:
            continue
        key = (label, url)
        if key in seen:
            continue
        seen.add(key)
        links.append(
            {
                "label": label,
                "url": url,
                "kind": normalize_space(item.get("kind")) or "external",
                "primary": bool(item.get("primary")),
            }
        )
    return links


def first_primary_url(links: list[JsonObject]) -> str:
    for link in links:
        if link.get("primary"):
            return normalize_space(link.get("url"))
    for link in links:
        url = normalize_space(link.get("url"))
        if url:
            return url
    return ""


def first_link_url(links: list[JsonObject], label: str) -> str:
    wanted = normalize_space(label).lower()
    for link in links:
        if normalize_space(link.get("label")).lower() == wanted:
            return normalize_space(link.get("url"))
    return ""


def count_text(value: object, singular: str, plural: str) -> str:
    text = normalize_space(value)
    if not text:
        return ""
    return f"{text} {singular if text == '1' else plural}"
