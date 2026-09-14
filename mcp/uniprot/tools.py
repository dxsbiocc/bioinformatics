"""MCP tool registry for the UniProt server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
import urllib.parse
from typing import Callable

from .client import UniProtClient
from .constants import (
    MAX_RESULTS,
    RESULT_SCHEMA_VERSION,
    UNIPROT_REST_BASE_URL,
    UNIPROT_WEBSITE_BASE_URL,
    JsonObject,
)
from .errors import McpError
from .records import fasta_record, normalize_uniprot_entry, uniprotkb_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    optional_string_list,
    require_accession,
    require_non_empty_string,
    source_info,
)


UNIPROT_CONTEXT_TYPES = ["all", "search", "accession", "organisms", "features", "xrefs"]
UNIPROT_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
UNIPROT_FEATURE_TYPES = ["Chain", "Domain", "Region", "DNA binding", "Modified residue", "Active site", "Binding site", "Transmembrane"]


def uniprot_status(args: JsonObject, client: UniProtClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "uniprot",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_url": UNIPROT_WEBSITE_BASE_URL,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["uniprotkb"],
        "tool_groups": {
            "context": ["uniprot_parameter_domains", "uniprot_resolve_context"],
            "protein": [
                "uniprot_search",
                "uniprot_lookup",
                "uniprot_fasta",
            ],
            "status": ["uniprot_status"],
        },
        "frontend_components": ["protein"],
        "preview_kinds": [
            "sequence",
            "feature_track",
            "structure_3d",
            "network",
            "citation_list",
            "xref_groups",
        ],
        "detail_sections": [
            "overview",
            "function",
            "features",
            "keywords",
            "comments",
            "cross_references",
            "literature",
        ],
        "pagination": {
            "search_total_header": "x-total-results",
            "next_link_rel": "next",
        },
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload = client.request_json(
            "uniprotkb/search",
            {
                "query": "accession:P04637",
                "format": "json",
                "size": 1,
            },
        )
        results = payload.get("results") if isinstance(payload.get("results"), list) else []
        status["network_check"] = {
            "ok": True,
            "returned": len(results),
        }
    return status


def uniprot_resolve_context(args: JsonObject, client: UniProtClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=UNIPROT_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query")
    accession = optional_string(args, "accession")
    organism = optional_string(args, "organism")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_RESULTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_uniprot_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if accession:
        accession = require_accession({"accession": accession})
        endpoint = f"uniprotkb/{urllib.parse.quote(accession, safe='')}"
        params: JsonObject = {"format": "json"}
        entry, headers = client.request_json_with_headers(endpoint, params)
        raw["entry"] = entry
        sources.append(source_with_release(endpoint, params, headers))
        contexts.append(uniprot_entry_context(entry))
        recommended_calls.extend(uniprot_recommended_calls(entry))

    if query:
        search_args: JsonObject = {"query": query}
        if organism:
            search_args["organism"] = organism
        if "reviewed" in args:
            search_args["reviewed"] = optional_bool(args, "reviewed", default=False)
        search_query = build_search_query(search_args, query)
        params = {"query": search_query, "format": "json", "size": max_results}
        payload, headers = client.request_json_with_headers("uniprotkb/search", params)
        raw["search"] = payload
        sources.append(source_with_release("uniprotkb/search", params, headers))
        entries = [entry for entry in payload.get("results", []) if isinstance(entry, dict)]
        contexts.extend(uniprot_entry_context(entry) for entry in entries[:max_results])
        for entry in entries[: min(max_results, 3)]:
            recommended_calls.extend(uniprot_recommended_calls(entry))

    filtered_contexts = [context for context in contexts if uniprot_context_matches(context, context_type=context_type, query=query or accession, organism=organism)]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=UNIPROT_CONTEXT_SCHEMA_VERSION,
        database="uniprotkb",
        query={
            "context_type": context_type,
            "query": query,
            "accession": accession,
            "organism": organism,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query, "accession": accession}),
        sources=sources,
        entity_groups={"accession"},
        raw=raw,
        summary_fields={"accessions": lambda context: context.get("parameter_name") == "accession"},
        include_raw=include_raw,
    )


def uniprot_search(args: JsonObject, client: UniProtClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(
        args,
        "max_results",
        default=10,
        minimum=1,
        maximum=MAX_RESULTS,
    )
    include_raw = optional_bool(args, "include_raw", default=False)
    include_features = optional_bool(args, "include_features", default=False)
    max_features = optional_int(
        args,
        "max_features",
        default=20 if include_features else 0,
        minimum=0,
        maximum=200,
    )
    max_comments = optional_int(
        args,
        "max_comments",
        default=3,
        minimum=0,
        maximum=50,
    )
    feature_types = optional_string_list(args, "feature_types")
    search_query = build_search_query(args, query)
    params: JsonObject = {
        "query": search_query,
        "format": "json",
        "size": max_results,
    }
    cursor = normalize_space(args.get("cursor"))
    if cursor:
        params["cursor"] = cursor
    payload, headers = client.request_json_with_headers("uniprotkb/search", params)
    raw_entries = [
        entry
        for entry in payload.get("results", [])
        if isinstance(entry, dict)
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "uniprotkb",
        "query": query,
        "normalized_query": search_query,
        "returned": len(raw_entries),
        "pagination": pagination_info(headers, size=max_results, returned=len(raw_entries)),
        "entries": [
            normalize_uniprot_entry(
                entry,
                include_raw=False,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
            for entry in raw_entries
        ],
        "records": [
            uniprotkb_record(
                entry,
                include_raw=include_raw,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
            for entry in raw_entries
        ],
        "source": source_with_release("uniprotkb/search", params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def uniprot_lookup(args: JsonObject, client: UniProtClient) -> JsonObject:
    accession = require_accession(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    include_features = optional_bool(args, "include_features", default=True)
    max_features = optional_int(
        args,
        "max_features",
        default=40,
        minimum=0,
        maximum=500,
    )
    max_comments = optional_int(
        args,
        "max_comments",
        default=8,
        minimum=0,
        maximum=100,
    )
    feature_types = optional_string_list(args, "feature_types")
    endpoint = f"uniprotkb/{urllib.parse.quote(accession, safe='')}"
    params: JsonObject = {"format": "json"}
    entry, headers = client.request_json_with_headers(endpoint, params)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "uniprotkb",
        "query": accession,
        "returned": 1,
        "entries": [
            normalize_uniprot_entry(
                entry,
                include_raw=False,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
        ],
        "records": [
            uniprotkb_record(
                entry,
                include_raw=include_raw,
                include_features=include_features,
                max_features=max_features,
                feature_types=feature_types,
                max_comments=max_comments,
            )
        ],
        "source": source_with_release(endpoint, params, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = entry
    return response


def uniprot_fasta(args: JsonObject, client: UniProtClient) -> JsonObject:
    accession = require_accession(args)
    endpoint = f"uniprotkb/{urllib.parse.quote(accession, safe='')}.fasta"
    fasta_text, headers = client.request_text_with_headers(
        endpoint,
        {},
        accept="text/x-fasta,text/plain",
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "uniprotkb",
        "query": accession,
        "returned": 1 if fasta_text.strip() else 0,
        "fasta": fasta_text,
        "records": [fasta_record(accession, fasta_text)] if fasta_text.strip() else [],
        "source": source_with_release(endpoint, {}, headers),
    }
    response["provenance"] = response["source"]
    return response


def build_search_query(args: JsonObject, query: str) -> str:
    clauses = [f"({query})"]
    organism = normalize_space(args.get("organism"))
    if organism:
        if organism.isdigit():
            clauses.append(f"(organism_id:{organism})")
        else:
            escaped = organism.replace('"', '\\"')
            clauses.append(f'(organism_name:"{escaped}")')
    if "reviewed" in args:
        reviewed = optional_bool(args, "reviewed", default=False)
        clauses.append(f"(reviewed:{str(reviewed).lower()})")
    return " AND ".join(clauses)


def pagination_info(
    headers: dict[str, str],
    *,
    size: int,
    returned: int,
) -> JsonObject:
    total = parse_optional_int(headers.get("x-total-results"))
    next_url = link_header_url(headers.get("link", ""), rel="next")
    info: JsonObject = {
        "size": size,
        "returned": returned,
        "total": total,
        "next_url": next_url,
        "next_cursor": cursor_from_url(next_url),
    }
    return {key: value for key, value in info.items() if value not in {"", None}}


def parse_optional_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def link_header_url(header: str, *, rel: str) -> str:
    for part in header.split(","):
        url_part, separator, meta = part.partition(";")
        if not separator:
            continue
        if f'rel="{rel}"' not in meta:
            continue
        url = url_part.strip()
        if url.startswith("<") and url.endswith(">"):
            return url[1:-1]
    return ""


def cursor_from_url(url: str) -> str:
    if not url:
        return ""
    parsed = urllib.parse.urlparse(url)
    values = urllib.parse.parse_qs(parsed.query).get("cursor", [])
    return values[0] if values else ""


def source_with_release(
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
) -> JsonObject:
    source = source_info(endpoint, params)
    release = normalize_space(headers.get("x-uniprot-release"))
    release_date = normalize_space(headers.get("x-uniprot-release-date"))
    api_deployment_date = normalize_space(headers.get("x-api-deployment-date"))
    if release:
        source["release"] = release
    if release_date:
        source["release_date"] = release_date
    if api_deployment_date:
        source["api_deployment_date"] = api_deployment_date
    return source


def optional_string(args: JsonObject, name: str, *, default: str = "") -> str:
    value = args.get(name, default)
    if value is None:
        return default
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip() or default


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_string(args, name, default=default)
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_uniprot_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        uniprot_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic UniProt context family to resolve before choosing a protein lookup, sequence, or downstream database call.",
            kind="enum",
            group="search",
            url="",
            metadata={"context_type": value},
        )
        for value in UNIPROT_CONTEXT_TYPES
    ]
    contexts.extend(
        [
            uniprot_parameter_context(
                "organism",
                "9606",
                label="Homo sapiens",
                description="Human NCBI TaxID commonly used with UniProt search.",
                kind="organism",
                group="organisms",
                url="https://www.uniprot.org/taxonomy/9606",
                metadata={"taxon_id": 9606, "scientific_name": "Homo sapiens"},
            ),
            uniprot_parameter_context(
                "reviewed",
                True,
                label="Reviewed Swiss-Prot",
                description="Restrict UniProt search to reviewed Swiss-Prot entries.",
                kind="boolean_filter",
                group="search",
                url="",
                metadata={"tool_hint": "uniprot_search"},
            ),
        ]
    )
    contexts.extend(
        uniprot_parameter_context(
            "feature_types",
            feature_type,
            label=feature_type,
            description="Sequence feature type accepted by uniprot_lookup and uniprot_search feature filtering.",
            kind="feature_type",
            group="features",
            url="",
            metadata={"tool_hint": "uniprot_lookup"},
        )
        for feature_type in UNIPROT_FEATURE_TYPES
    )
    contexts.extend(
        uniprot_parameter_context(
            "xref_database",
            value,
            label=value,
            description="Common UniProt cross-reference that can seed another MCP or front-end preview.",
            kind="xref_hint",
            group="xrefs",
            url="",
            metadata={"downstream": downstream},
        )
        for value, downstream in [
            ("AlphaFoldDB", "alphafold_lookup"),
            ("PDB", "rcsb_lookup"),
            ("STRING", "string_interactions"),
            ("Reactome", "reactome_lookup"),
            ("PubMed", "pubmed_articles"),
        ]
    )
    return contexts


def uniprot_entry_context(entry: JsonObject) -> JsonObject:
    normalized = normalize_uniprot_entry(entry, include_raw=False, include_features=False, max_features=0, feature_types=[], max_comments=1)
    accession = str(normalized.get("accession") or entry.get("primaryAccession") or "")
    genes = normalized.get("genes") if isinstance(normalized.get("genes"), list) else []
    gene = genes[0] if genes else ""
    title = str(normalized.get("protein_name") or accession)
    return uniprot_parameter_context(
        "accession",
        accession,
        label=title,
        description=f"UniProtKB accession for {gene or title}.",
        kind="accession",
        group="accession",
        url=f"{UNIPROT_WEBSITE_BASE_URL.rstrip('/')}/uniprotkb/{urllib.parse.quote(accession)}/entry",
        metadata={
            "accession": accession,
            "gene": gene,
            "organism": normalized.get("organism") or "",
            "taxon_id": normalized.get("taxid") or "",
            "reviewed": normalized.get("reviewed"),
        },
    )


def uniprot_parameter_context(
    parameter_name: str,
    value: object,
    *,
    label: str,
    description: str,
    kind: str,
    group: str,
    url: str,
    metadata: JsonObject,
) -> JsonObject:
    display_fields = [{"label": key.replace("_", " ").title(), "value": item} for key, item in metadata.items() if item not in ("", None, [], {})]
    if url:
        display_fields.append({"label": "URL", "value": url})
    return {
        "kind": kind,
        "group": group,
        "parameter_name": parameter_name,
        "value": value,
        "label": label,
        "title": label,
        "description": description,
        "url": url,
        "metadata": metadata,
        "display": {
            "component": "protein",
            "chip_label": parameter_name,
            "icon": "uniprot",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "UniProtKB", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "uniprot", "fields": display_fields},
            "primary_url": url,
        },
    }


def uniprot_recommended_calls(entry: JsonObject) -> list[JsonObject]:
    normalized = normalize_uniprot_entry(entry, include_raw=False, include_features=False, max_features=0, feature_types=[], max_comments=1)
    accession = str(normalized.get("accession") or entry.get("primaryAccession") or "")
    if not accession:
        return []
    calls: list[JsonObject] = [
        {"tool_name": "uniprot_lookup", "arguments": {"accession": accession}, "reason": "Fetch detailed UniProtKB metadata and feature/cross-reference previews."},
        {"tool_name": "uniprot_fasta", "arguments": {"accession": accession}, "reason": "Fetch the protein FASTA sequence."},
    ]
    xrefs = entry.get("uniProtKBCrossReferences")
    if isinstance(xrefs, list):
        for xref in xrefs:
            if not isinstance(xref, dict):
                continue
            database = str(xref.get("database") or "")
            value = str(xref.get("id") or "")
            if database == "AlphaFoldDB" and value:
                calls.append({"server": "alphafold", "tool_name": "alphafold_lookup", "arguments": {"accession": value}, "reason": "Open predicted 3D structure context for this UniProt accession."})
            elif database == "PDB" and value:
                calls.append({"server": "rcsb", "tool_name": "rcsb_lookup", "arguments": {"pdb_id": value}, "reason": "Open experimentally determined PDB structure context."})
            elif database == "STRING" and value:
                calls.append({"server": "string", "tool_name": "string_interactions", "arguments": {"identifiers": [value]}, "reason": "Inspect protein interaction partners."})
            elif database == "PubMed" and value:
                calls.append({"server": "ncbi", "tool_name": "pubmed_articles", "arguments": {"ids": [value]}, "reason": "Open supporting literature metadata."})
    return calls


def uniprot_context_matches(context: JsonObject, *, context_type: str, query: str, organism: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    metadata = context.get("metadata")
    if organism and isinstance(metadata, dict):
        org_text = f"{metadata.get('organism', '')} {metadata.get('taxon_id', '')}".lower()
        if context.get("group") == "accession" and organism.lower() not in org_text:
            return False
    if not query:
        return True
    haystack_values = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") == "accession"


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("uniprot_parameter_domains"),
        {
            "name": "uniprot_resolve_context",
            "title": "Resolve UniProt dynamic parameter context",
            "description": (
                "Resolve UniProt search/accession context before protein lookup or downstream structure/network calls. "
                "Returns front-end-friendly context rows, accession URLs, cross-reference hints, and recommended calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": UNIPROT_CONTEXT_TYPES,
                        "default": "all",
                    },
                    "query": {"type": "string", "description": "Optional UniProt query such as gene:TP53."},
                    "accession": {"type": "string", "description": "Optional UniProtKB accession such as P04637."},
                    "organism": {"type": "string", "description": "Optional organism name or TaxID, for example 9606."},
                    "reviewed": {"type": "boolean", "description": "Optional reviewed filter when query is provided."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": 10},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "uniprot_search",
            "title": "Search UniProtKB",
            "description": (
                "Search UniProtKB through the UniProt REST API and return "
                "front-end-compatible protein records with display previews."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "UniProt query string, for example gene:TP53.",
                    },
                    "organism": {
                        "type": "string",
                        "description": "Optional organism name or TaxID, for example 9606.",
                    },
                    "reviewed": {
                        "type": "boolean",
                        "description": "Optional Swiss-Prot reviewed filter.",
                    },
                    "max_results": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_RESULTS,
                        "default": 10,
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Optional UniProt pagination cursor from pagination.next_cursor.",
                    },
                    "include_features": {
                        "type": "boolean",
                        "default": False,
                        "description": "Return bounded sequence feature rows for richer detail rendering.",
                    },
                    "feature_types": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        ],
                        "description": "Optional feature type filter, for example Domain, Region, or Modified residue.",
                    },
                    "max_features": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 200,
                        "default": 0,
                    },
                    "max_comments": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 50,
                        "default": 3,
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "uniprot_lookup",
            "title": "Look up a UniProtKB entry",
            "description": (
                "Fetch one UniProtKB accession and return normalized protein, "
                "gene, organism, sequence length, cross-reference, preview, and URL metadata."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "UniProtKB accession, for example P04637.",
                    },
                    "include_raw": {
                        "type": "boolean",
                        "default": False,
                    },
                    "include_features": {
                        "type": "boolean",
                        "default": True,
                        "description": "Return bounded sequence feature rows for detail rendering.",
                    },
                    "feature_types": {
                        "oneOf": [
                            {"type": "string"},
                            {
                                "type": "array",
                                "items": {"type": "string"},
                            },
                        ],
                        "description": "Optional feature type filter, for example Domain, Region, or Modified residue.",
                    },
                    "max_features": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 500,
                        "default": 40,
                    },
                    "max_comments": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 100,
                        "default": 8,
                    },
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "uniprot_fasta",
            "title": "Fetch UniProtKB FASTA",
            "description": (
                "Fetch the FASTA sequence for one UniProtKB accession and return "
                "a protein sequence record plus the raw FASTA text."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "accession": {
                        "type": "string",
                        "description": "UniProtKB accession, for example P04637.",
                    }
                },
                "required": ["accession"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "uniprot_status",
            "title": "Inspect UniProt MCP status",
            "description": "Return configured UniProt MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "check_network": {
                        "type": "boolean",
                        "default": False,
                    }
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, UniProtClient], JsonObject]] = {
    "uniprot_parameter_domains": make_parameter_domains_handler("uniprot", "uniprot_parameter_domains", tool_definitions),
    "uniprot_resolve_context": uniprot_resolve_context,
    "uniprot_search": uniprot_search,
    "uniprot_lookup": uniprot_lookup,
    "uniprot_fasta": uniprot_fasta,
    "uniprot_status": uniprot_status,
}
