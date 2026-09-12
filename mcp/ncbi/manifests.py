"""Metadata-only omics download plans, sample sheets, and runtime checks."""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess

from .client import NcbiClient
from .constants import RESULT_SCHEMA_VERSION, JsonObject
from .errors import McpError
from .geo import geo_accession_url, geo_series
from .manifest_records import (
    download_plan_item_record,
    runtime_status_record,
    sample_sheet_record,
)
from .records import (
    bioproject_url,
    biosample_url,
    sra_run_browser_url,
    sra_run_selector_url,
    sra_url,
    taxonomy_url,
)
from .sra import SRA_ACCESSION_RE, sra_lookup, sra_search
from .utils import normalize_space, optional_bool, optional_int, source_info


DEFAULT_RUNTIME_TOOLS = [
    "prefetch",
    "fasterq-dump",
    "vdb-validate",
    "fastqc",
    "multiqc",
    "salmon",
    "STAR",
    "hisat2",
    "samtools",
    "seqkit",
    "nextflow",
]

VERSION_FLAGS = {
    "prefetch": ["--version"],
    "fasterq-dump": ["--version"],
    "vdb-validate": ["--version"],
    "fastqc": ["--version"],
    "multiqc": ["--version"],
    "salmon": ["--version"],
    "STAR": ["--version"],
    "hisat2": ["--version"],
    "samtools": ["--version"],
    "seqkit": ["version"],
    "nextflow": ["-version"],
    "python": ["--version"],
    "python3": ["--version"],
    "R": ["--version"],
    "Rscript": ["--version"],
}


def sra_download_plan(args: JsonObject, client: NcbiClient) -> JsonObject:
    """Create a front-end-ready SRA Toolkit command plan without downloading."""

    query = require_query(args)
    max_results = optional_int(args, "max_results", default=20, minimum=1, maximum=100)
    threads = optional_int(args, "threads", default=8, minimum=1, maximum=128)
    prefetch_outdir = normalize_space(args.get("prefetch_outdir")) or "data/sra"
    fastq_outdir = normalize_space(args.get("fastq_outdir")) or "data/fastq"
    include_raw = optional_bool(args, "include_raw", default=False)

    lookup = resolve_sra_query(
        query,
        client,
        max_results=max_results,
        include_raw=include_raw,
    )
    experiments = [
        experiment
        for experiment in lookup.get("experiments", [])
        if isinstance(experiment, dict)
    ]
    items = [
        item
        for experiment in experiments
        for item in sra_download_items(
            experiment,
            threads=threads,
            prefetch_outdir=prefetch_outdir,
            fastq_outdir=fastq_outdir,
        )
    ]
    manifest: JsonObject = {
        "source": "sra",
        "query": query,
        "run_count": len(items),
        "experiment_count": len(experiments),
        "prefetch_outdir": prefetch_outdir,
        "fastq_outdir": fastq_outdir,
        "threads": threads,
        "columns": sra_download_plan_columns(),
        "items": items,
        "notes": [
            "This is a metadata-only plan; the MCP server did not download raw data.",
            "Run SRA Toolkit commands intentionally in the target project environment.",
        ],
    }
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": "sra_download_plan",
        "database": "sra",
        "query": query,
        "returned": len(items),
        "manifest": manifest,
        "runs": items,
        "experiments": experiments,
        "lookup": lookup,
        "records": [download_plan_item_record(item) for item in items],
        "source": lookup.get("summary_source") or lookup.get("source"),
    }
    response["provenance"] = response.get("source")
    return response


def geo_download_plan(args: JsonObject, client: NcbiClient) -> JsonObject:
    """Create a front-end-ready GEO download plan without downloading files."""

    accession = normalize_space(args.get("accession") or args.get("gse")).upper()
    if not re.fullmatch(r"GSE\d+", accession):
        raise McpError(-32602, "accession must be a GEO Series accession like GSE100")
    include_samples = optional_bool(args, "include_samples", default=True)
    include_raw = optional_bool(args, "include_raw", default=False)

    lookup = geo_series(
        {"accession": accession, "include_raw": include_raw},
        client,
    )
    series = lookup.get("series") if isinstance(lookup.get("series"), dict) else {}
    plan = geo_download_plan_payload(series, accession, include_samples=include_samples)
    records = [download_plan_item_record(plan)] if plan else []
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": "geo_download_plan",
        "database": "geo",
        "entrez_database": "gds",
        "accession": accession,
        "query": accession,
        "found": bool(series),
        "returned": len(records),
        "manifest": plan,
        "series": series,
        "lookup": lookup,
        "records": records,
        "source": lookup.get("summary_source") or lookup.get("source"),
    }
    response["provenance"] = response.get("source")
    return response


def omics_sample_sheet(args: JsonObject, client: NcbiClient) -> JsonObject:
    """Build a small, UI-ready sample metadata table from GEO or SRA metadata."""

    query = require_query(args)
    source = normalize_space(args.get("source") or "auto").lower()
    max_results = optional_int(args, "max_results", default=50, minimum=1, maximum=100)
    include_raw = optional_bool(args, "include_raw", default=False)
    if source == "auto":
        source = infer_sample_sheet_source(query)
    if source in {"geo", "gds", "gse"}:
        sheet, lookup = geo_sample_sheet(query, client, include_raw=include_raw)
        source = "geo"
    elif source == "sra":
        sheet, lookup = sra_sample_sheet(
            query,
            client,
            max_results=max_results,
            include_raw=include_raw,
        )
    else:
        raise McpError(-32602, "source must be one of: auto, geo, or sra")

    provenance = lookup.get("summary_source") or lookup.get("source")
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": "omics_sample_sheet",
        "sample_source": source,
        "database": source,
        "query": query,
        "returned": len(sheet.get("rows", [])),
        "columns": sheet.get("columns", []),
        "rows": sheet.get("rows", []),
        "sheet": sheet,
        "lookup": lookup,
        "records": [sample_sheet_record(sheet)],
        "source": provenance,
    }
    response["provenance"] = provenance
    return response


def tool_runtime_status(args: JsonObject, client: NcbiClient) -> JsonObject:
    """Inspect whether common omics command-line tools are discoverable on PATH."""

    del client
    tools = coerce_tools(args.get("tools"))
    check_versions = optional_bool(args, "check_versions", default=False)
    timeout_seconds = optional_int(
        args,
        "timeout_seconds",
        default=3,
        minimum=1,
        maximum=30,
    )
    statuses = [
        inspect_runtime_tool(
            tool,
            check_version=check_versions,
            timeout_seconds=timeout_seconds,
        )
        for tool in tools
    ]
    source = source_info(
        "local-runtime",
        {
            "db": "local_runtime",
            "tools": tools,
            "check_versions": check_versions,
        },
    )
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "tool": "tool_runtime_status",
        "database": "local_runtime",
        "returned": len(statuses),
        "tools": statuses,
        "records": [runtime_status_record(status) for status in statuses],
        "source": source,
        "provenance": source,
    }


def resolve_sra_query(
    query: str,
    client: NcbiClient,
    *,
    max_results: int,
    include_raw: bool,
) -> JsonObject:
    if re.fullmatch(r"\d+", query) or SRA_ACCESSION_RE.fullmatch(query):
        return sra_lookup(
            {
                "query": query,
                "max_results": min(max_results, 50),
                "include_raw": include_raw,
            },
            client,
        )
    return sra_search(
        {
            "query": sra_contextual_query(query),
            "max_results": max_results,
            "include_raw": include_raw,
        },
        client,
    )


def sra_contextual_query(query: str) -> str:
    normalized = normalize_space(query).upper()
    if re.fullmatch(r"PRJ[A-Z]{1,4}\d+", normalized):
        return f"{normalized}[BioProject]"
    if re.fullmatch(r"SAM[NED]\d+", normalized):
        return f"{normalized}[BioSample]"
    return query


def sra_download_items(
    experiment: JsonObject,
    *,
    threads: int,
    prefetch_outdir: str,
    fastq_outdir: str,
) -> list[JsonObject]:
    runs = experiment.get("runs") if isinstance(experiment.get("runs"), list) else []
    if not runs:
        runs = [{}]
    return [
        sra_download_item(
            experiment,
            run if isinstance(run, dict) else {},
            threads=threads,
            prefetch_outdir=prefetch_outdir,
            fastq_outdir=fastq_outdir,
        )
        for run in runs
    ]


def sra_download_item(
    experiment: JsonObject,
    run: JsonObject,
    *,
    threads: int,
    prefetch_outdir: str,
    fastq_outdir: str,
) -> JsonObject:
    run_accession = normalize_space(run.get("accession"))
    experiment_accession = nested_accession(experiment, "experiment")
    study_accession = nested_accession(experiment, "study")
    sample_accession = nested_accession(experiment, "sample")
    accession = run_accession or normalize_space(experiment.get("accession"))
    library = experiment.get("library") if isinstance(experiment.get("library"), dict) else {}
    platform = experiment.get("platform") if isinstance(experiment.get("platform"), dict) else {}
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    statistics = experiment.get("statistics") if isinstance(experiment.get("statistics"), dict) else {}
    bioproject = normalize_space(experiment.get("bioproject"))
    biosample = normalize_space(experiment.get("biosample"))
    links = sra_item_links(
        accession=accession,
        run_accession=run_accession,
        experiment_accession=experiment_accession,
        study_accession=study_accession,
        bioproject=bioproject,
        biosample=biosample,
    )
    return {
        "source": "sra",
        "database": "sra",
        "accession": accession,
        "run_accession": run_accession,
        "experiment_accession": experiment_accession,
        "study_accession": study_accession,
        "sample_accession": sample_accession,
        "bioproject": bioproject,
        "biosample": biosample,
        "title": normalize_space(experiment.get("title")) or accession,
        "organism": normalize_space(organism.get("scientific_name")),
        "taxid": normalize_space(organism.get("taxid")),
        "library_strategy": normalize_space(library.get("strategy")),
        "library_source": normalize_space(library.get("source")),
        "library_selection": normalize_space(library.get("selection")),
        "layout": normalize_space(library.get("layout")),
        "platform": normalize_space(platform.get("name")),
        "instrument": normalize_space(platform.get("instrument_model")),
        "total_spots": run.get("total_spots") or statistics.get("total_spots"),
        "total_bases": run.get("total_bases") or statistics.get("total_bases"),
        "total_size": run.get("total_size") or statistics.get("total_size"),
        "download_ready": bool(run_accession),
        "prefetch_outdir": prefetch_outdir,
        "fastq_outdir": fastq_outdir,
        "threads": threads,
        "commands": sra_commands(
            run_accession,
            threads=threads,
            prefetch_outdir=prefetch_outdir,
            fastq_outdir=fastq_outdir,
        ),
        "links": links,
        "url": sra_run_browser_url(run_accession) or sra_url(accession),
    }


def sra_item_links(
    *,
    accession: str,
    run_accession: str,
    experiment_accession: str,
    study_accession: str,
    bioproject: str,
    biosample: str,
) -> list[JsonObject]:
    links: list[JsonObject] = []
    if run_accession:
        links.append(
            {
                "label": "SRA Run Browser",
                "url": sra_run_browser_url(run_accession),
                "kind": "external",
                "primary": True,
            }
        )
        links.append(
            {
                "label": "SRA",
                "url": sra_url(run_accession),
                "kind": "external",
                "primary": False,
            }
        )
    elif accession:
        links.append(
            {
                "label": "SRA",
                "url": sra_url(accession),
                "kind": "external",
                "primary": True,
            }
        )
    selector_accession = bioproject or study_accession or experiment_accession or accession
    if selector_accession:
        links.append(
            {
                "label": "SRA Run Selector",
                "url": sra_run_selector_url(selector_accession),
                "kind": "external",
                "primary": False,
            }
        )
    if bioproject:
        links.append(
            {
                "label": "BioProject",
                "url": bioproject_url(bioproject),
                "kind": "external",
                "primary": False,
            }
        )
    if biosample:
        links.append(
            {
                "label": "BioSample",
                "url": biosample_url(biosample),
                "kind": "external",
                "primary": False,
            }
        )
    return unique_links(links)


def sra_commands(
    run_accession: str,
    *,
    threads: int,
    prefetch_outdir: str,
    fastq_outdir: str,
) -> JsonObject:
    if not run_accession:
        return {}
    run = shlex.quote(run_accession)
    prefetch_dir = shlex.quote(prefetch_outdir)
    fastq_dir = shlex.quote(fastq_outdir)
    return {
        "prefetch": f"prefetch {run} --output-directory {prefetch_dir}",
        "fastq": (
            f"fasterq-dump {run} --split-files --threads {threads} "
            f"--outdir {fastq_dir}"
        ),
        "validate": f"vdb-validate {run}",
    }


def sra_download_plan_columns() -> list[JsonObject]:
    return [
        {"key": "run_accession", "label": "Run"},
        {"key": "experiment_accession", "label": "Experiment"},
        {"key": "study_accession", "label": "Study"},
        {"key": "biosample", "label": "BioSample"},
        {"key": "bioproject", "label": "BioProject"},
        {"key": "organism", "label": "Organism"},
        {"key": "library_strategy", "label": "Strategy"},
        {"key": "layout", "label": "Layout"},
        {"key": "total_bases", "label": "Bases"},
        {"key": "download_ready", "label": "Ready"},
    ]


def geo_download_plan_payload(
    series: JsonObject,
    accession: str,
    *,
    include_samples: bool,
) -> JsonObject:
    if not series:
        return {}
    platform = series.get("platform") if isinstance(series.get("platform"), dict) else {}
    samples = series.get("samples") if isinstance(series.get("samples"), list) else []
    links = [
        {
            "label": "GEO",
            "url": geo_accession_url(accession),
            "kind": "external",
            "primary": True,
        },
        *[
            link
            for link in series.get("download_links", [])
            if isinstance(link, dict)
        ],
    ]
    return {
        "source": "geo",
        "database": "geo",
        "accession": accession,
        "title": normalize_space(series.get("title")),
        "summary": normalize_space(series.get("summary")),
        "organism": normalize_space(series.get("organism") or series.get("taxon")),
        "study_type": normalize_space(series.get("study_type")),
        "sample_count": series.get("sample_count"),
        "sample_accessions": [
            normalize_space(sample.get("accession"))
            for sample in samples
            if isinstance(sample, dict) and normalize_space(sample.get("accession"))
        ],
        "samples": samples if include_samples else [],
        "platform_accession": normalize_space(platform.get("accession")),
        "platform_title": normalize_space(platform.get("title")),
        "bioproject": normalize_space(series.get("bioproject")),
        "pubmed_ids": series.get("pubmed_ids", []),
        "geo2r": normalize_space(series.get("geo2r")),
        "download_links": series.get("download_links", []),
        "links": unique_links(links),
        "url": normalize_space(series.get("url")) or geo_accession_url(accession),
        "recommended_actions": [
            "Open the GEO browser page to inspect sample annotations.",
            "Use the series matrix for expression-matrix workflows when available.",
            "Use the supplementary directory for submitter-provided raw or processed files.",
        ],
        "notes": [
            "This is a metadata-only plan; the MCP server did not download GEO files.",
            "Supplementary files can be large and format-diverse, so download deliberately.",
        ],
    }


def geo_sample_sheet(
    query: str,
    client: NcbiClient,
    *,
    include_raw: bool,
) -> tuple[JsonObject, JsonObject]:
    accession = normalize_space(query).upper()
    lookup = geo_series({"accession": accession, "include_raw": include_raw}, client)
    series = lookup.get("series") if isinstance(lookup.get("series"), dict) else {}
    platform = series.get("platform") if isinstance(series.get("platform"), dict) else {}
    pubmed_ids = [
        normalize_space(pmid)
        for pmid in series.get("pubmed_ids", [])
        if normalize_space(pmid)
    ]
    rows = []
    for sample in series.get("samples", []):
        if not isinstance(sample, dict):
            continue
        sample_accession = normalize_space(sample.get("accession")).upper()
        if not sample_accession:
            continue
        rows.append(
            {
                "sample_accession": sample_accession,
                "sample_title": normalize_space(sample.get("title")),
                "series_accession": normalize_space(series.get("accession")).upper(),
                "series_title": normalize_space(series.get("title")),
                "organism": normalize_space(series.get("organism") or series.get("taxon")),
                "platform_accession": normalize_space(platform.get("accession")),
                "platform_title": normalize_space(platform.get("title")),
                "bioproject": normalize_space(series.get("bioproject")),
                "pubmed_ids": ",".join(pubmed_ids),
                "geo_url": geo_accession_url(sample_accession),
                "series_url": geo_accession_url(accession),
                "links": [
                    {
                        "label": "GEO sample",
                        "url": geo_accession_url(sample_accession),
                        "kind": "external",
                        "primary": True,
                    },
                    {
                        "label": "GEO series",
                        "url": geo_accession_url(accession),
                        "kind": "external",
                        "primary": False,
                    },
                ],
            }
        )
    sheet = {
        "source": "geo",
        "query": accession,
        "title": f"{accession} sample sheet",
        "primary_key": "sample_accession",
        "columns": geo_sample_sheet_columns(),
        "rows": rows,
        "links": [
            {
                "label": "GEO",
                "url": geo_accession_url(accession),
                "kind": "external",
                "primary": True,
            }
        ],
        "url": geo_accession_url(accession),
    }
    return sheet, lookup


def sra_sample_sheet(
    query: str,
    client: NcbiClient,
    *,
    max_results: int,
    include_raw: bool,
) -> tuple[JsonObject, JsonObject]:
    lookup = resolve_sra_query(
        query,
        client,
        max_results=max_results,
        include_raw=include_raw,
    )
    rows = [
        row
        for experiment in lookup.get("experiments", [])
        if isinstance(experiment, dict)
        for row in sra_sample_sheet_rows(experiment)
    ]
    sheet = {
        "source": "sra",
        "query": query,
        "title": f"{query} SRA sample sheet",
        "primary_key": "run_accession",
        "columns": sra_sample_sheet_columns(),
        "rows": rows,
        "links": sra_sheet_links(query, rows),
        "url": sra_run_selector_url(query) if not SRA_ACCESSION_RE.fullmatch(query) else sra_url(query),
    }
    return sheet, lookup


def sra_sample_sheet_rows(experiment: JsonObject) -> list[JsonObject]:
    items = sra_download_items(
        experiment,
        threads=8,
        prefetch_outdir="data/sra",
        fastq_outdir="data/fastq",
    )
    rows = []
    for item in items:
        run_accession = normalize_space(item.get("run_accession"))
        rows.append(
            {
                "run_accession": run_accession,
                "experiment_accession": normalize_space(item.get("experiment_accession")),
                "study_accession": normalize_space(item.get("study_accession")),
                "sample_accession": normalize_space(item.get("sample_accession")),
                "biosample": normalize_space(item.get("biosample")),
                "bioproject": normalize_space(item.get("bioproject")),
                "organism": normalize_space(item.get("organism")),
                "taxid": normalize_space(item.get("taxid")),
                "library_strategy": normalize_space(item.get("library_strategy")),
                "library_source": normalize_space(item.get("library_source")),
                "library_selection": normalize_space(item.get("library_selection")),
                "layout": normalize_space(item.get("layout")),
                "platform": normalize_space(item.get("platform")),
                "instrument": normalize_space(item.get("instrument")),
                "total_spots": item.get("total_spots"),
                "total_bases": item.get("total_bases"),
                "total_size": item.get("total_size"),
                "sra_url": sra_url(run_accession),
                "run_browser_url": sra_run_browser_url(run_accession),
                "run_selector_url": sra_run_selector_url(
                    normalize_space(item.get("bioproject"))
                    or normalize_space(item.get("study_accession"))
                    or run_accession
                ),
                "biosample_url": biosample_url(normalize_space(item.get("biosample"))),
                "bioproject_url": bioproject_url(normalize_space(item.get("bioproject"))),
                "taxonomy_url": taxonomy_url(normalize_space(item.get("taxid"))),
                "links": item.get("links", []),
            }
        )
    return rows


def geo_sample_sheet_columns() -> list[JsonObject]:
    return [
        {"key": "sample_accession", "label": "Sample"},
        {"key": "sample_title", "label": "Title"},
        {"key": "series_accession", "label": "Series"},
        {"key": "organism", "label": "Organism"},
        {"key": "platform_accession", "label": "Platform"},
        {"key": "bioproject", "label": "BioProject"},
        {"key": "pubmed_ids", "label": "PubMed IDs"},
        {"key": "geo_url", "label": "GEO URL"},
    ]


def sra_sample_sheet_columns() -> list[JsonObject]:
    return [
        {"key": "run_accession", "label": "Run"},
        {"key": "experiment_accession", "label": "Experiment"},
        {"key": "study_accession", "label": "Study"},
        {"key": "sample_accession", "label": "SRA sample"},
        {"key": "biosample", "label": "BioSample"},
        {"key": "bioproject", "label": "BioProject"},
        {"key": "organism", "label": "Organism"},
        {"key": "library_strategy", "label": "Strategy"},
        {"key": "library_source", "label": "Source"},
        {"key": "library_selection", "label": "Selection"},
        {"key": "layout", "label": "Layout"},
        {"key": "platform", "label": "Platform"},
        {"key": "instrument", "label": "Instrument"},
        {"key": "total_bases", "label": "Bases"},
        {"key": "run_browser_url", "label": "Run Browser URL"},
    ]


def sra_sheet_links(query: str, rows: list[JsonObject]) -> list[JsonObject]:
    links: list[JsonObject] = []
    if SRA_ACCESSION_RE.fullmatch(query):
        links.append(
            {
                "label": "SRA",
                "url": sra_url(query),
                "kind": "external",
                "primary": True,
            }
        )
    else:
        links.append(
            {
                "label": "SRA Run Selector",
                "url": sra_run_selector_url(query),
                "kind": "external",
                "primary": True,
            }
        )
    for row in rows[:5]:
        run_accession = normalize_space(row.get("run_accession"))
        if run_accession:
            links.append(
                {
                    "label": f"Run Browser {run_accession}",
                    "url": sra_run_browser_url(run_accession),
                    "kind": "external",
                    "primary": False,
                }
            )
    return unique_links(links)


def inspect_runtime_tool(
    tool: str,
    *,
    check_version: bool,
    timeout_seconds: int,
) -> JsonObject:
    path = shutil.which(tool)
    status: JsonObject = {
        "tool": tool,
        "available": bool(path),
        "path": path or "",
        "version": "",
        "version_error": "",
    }
    if not path or not check_version:
        return status

    flags = VERSION_FLAGS.get(tool)
    if not flags:
        status["version_error"] = "version check skipped for unknown tool"
        return status
    try:
        completed = subprocess.run(
            [path, *flags],
            capture_output=True,
            check=False,
            text=True,
            timeout=timeout_seconds,
        )
    except OSError as exc:
        status["version_error"] = str(exc)
        return status
    except subprocess.TimeoutExpired:
        status["version_error"] = f"version check timed out after {timeout_seconds}s"
        return status

    output_lines = (completed.stdout or completed.stderr).splitlines()
    version_text = normalize_space(output_lines[0] if output_lines else "")
    if version_text:
        status["version"] = version_text
    elif completed.returncode != 0:
        status["version_error"] = f"version command exited with {completed.returncode}"
    return status


def coerce_tools(value: object) -> list[str]:
    if value is None:
        raw_tools = DEFAULT_RUNTIME_TOOLS
    elif isinstance(value, str):
        raw_tools = re.split(r"[\s,;]+", value.strip())
    elif isinstance(value, list):
        raw_tools = value
    else:
        raise McpError(-32602, "tools must be a string, array, or omitted")

    tools = []
    seen = set()
    for item in raw_tools:
        tool = normalize_space(item)
        if not tool:
            continue
        if "/" in tool or "\x00" in tool:
            raise McpError(-32602, "tools must be command names, not paths")
        if tool not in seen:
            seen.add(tool)
            tools.append(tool)
    if not tools:
        raise McpError(-32602, "At least one tool name is required")
    if len(tools) > 100:
        raise McpError(-32602, "At most 100 tools may be checked")
    return tools


def infer_sample_sheet_source(query: str) -> str:
    if re.fullmatch(r"GSE\d+", normalize_space(query).upper()):
        return "geo"
    return "sra"


def require_query(args: JsonObject) -> str:
    query = normalize_space(args.get("query") or args.get("accession") or args.get("gse"))
    if not query:
        raise McpError(-32602, "query is required and must be a non-empty string")
    return query


def nested_accession(payload: JsonObject, key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, dict):
        return ""
    return normalize_space(value.get("accession"))


def unique_links(links: list[JsonObject]) -> list[JsonObject]:
    seen = set()
    unique = []
    for link in links:
        url = normalize_space(link.get("url"))
        label = normalize_space(link.get("label")) or url
        if not url:
            continue
        key = (label, url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "label": label,
                "url": url,
                "kind": normalize_space(link.get("kind")) or "external",
                "primary": bool(link.get("primary")),
            }
        )
    return unique
