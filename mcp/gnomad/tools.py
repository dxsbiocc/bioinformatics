"""MCP tool registry for the gnomAD server."""

from __future__ import annotations

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition
from typing import Callable

from .client import GnomadClient
from .constants import (
    DEFAULT_DATASET,
    DEFAULT_REFERENCE_GENOME,
    MAX_POPULATIONS,
    MAX_TRANSCRIPTS,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .errors import GnomadError, McpError
from .records import gnomad_gene_record, gnomad_variant_record
from .utils import (
    normalize_space,
    optional_bool,
    optional_int,
    optional_string,
    require_non_empty_string,
    source_info,
)


GNOMAD_CONTEXT_TYPES = ["all", "variants", "genes", "datasets", "reference_genomes"]
GNOMAD_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"
GNOMAD_DATASET_HINTS = ["gnomad_r4", "gnomad_r3", "gnomad_r2_1"]
GNOMAD_REFERENCE_GENOME_HINTS = ["GRCh38", "GRCh37"]


VARIANT_QUERY = """
query Variant($variantId: String!, $dataset: DatasetId!) {
  variant(variantId: $variantId, dataset: $dataset) {
    variantId
    chrom
    pos
    ref
    alt
    genome {
      ac
      an
      af
      homozygote_count
      filters
      populations {
        id
        ac
        an
        homozygote_count
      }
    }
    exome {
      ac
      an
      af
      homozygote_count
      filters
      populations {
        id
        ac
        an
        homozygote_count
      }
    }
    transcript_consequences {
      gene_id
      gene_symbol
      transcript_id
      consequence_terms
      hgvsc
      hgvsp
      lof
      lof_filter
      lof_flags
    }
  }
}
"""


GENE_QUERY = """
query Gene($geneId: String!, $referenceGenome: ReferenceGenomeId!) {
  gene(gene_id: $geneId, reference_genome: $referenceGenome) {
    gene_id
    symbol
    name
    chrom
    start
    stop
    strand
    canonical_transcript_id
    transcripts {
      transcript_id
      transcript_version
    }
    gnomad_constraint {
      exp_syn
      obs_syn
      oe_syn
      exp_mis
      obs_mis
      oe_mis
      exp_lof
      obs_lof
      oe_lof
      oe_lof_upper
      pLI
    }
  }
}
"""


META_QUERY = "query { meta { clinvar_release_date } }"


def gnomad_status(args: JsonObject, client: GnomadClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "gnomad",
        "version": "0.1.0",
        "graphql_url": client.config.graphql_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": ["gnomad"],
        "tool_groups": {
            "context": ["gnomad_parameter_domains", "gnomad_resolve_context"],
            "variant": ["gnomad_variant_lookup"],
            "gene": ["gnomad_gene_lookup"],
            "status": ["gnomad_status"],
        },
        "frontend_components": ["variant", "gene"],
        "preview_kinds": ["table", "xref_groups"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        payload, _headers = client.request_graphql_with_headers(META_QUERY, {})
        ensure_no_graphql_errors(payload)
        meta = payload.get("data", {}).get("meta", {}) if isinstance(payload.get("data"), dict) else {}
        status["network_check"] = {
            "ok": True,
            "clinvar_release_date": meta.get("clinvar_release_date"),
        }
    return status


def gnomad_resolve_context(args: JsonObject, client: GnomadClient) -> JsonObject:
    context_type = optional_context_type(args, "context_type", allowed=GNOMAD_CONTEXT_TYPES, default="all")
    variant_id = optional_text(args, "variant_id")
    gene_id = optional_text(args, "gene_id")
    dataset = optional_text(args, "dataset") or DEFAULT_DATASET
    reference_genome = optional_text(args, "reference_genome") or DEFAULT_REFERENCE_GENOME
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=MAX_TRANSCRIPTS)
    max_populations = optional_int(args, "max_populations", default=24, minimum=1, maximum=MAX_POPULATIONS)
    max_transcripts = optional_int(args, "max_transcripts", default=20, minimum=1, maximum=MAX_TRANSCRIPTS)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts = static_gnomad_contexts()
    recommended_calls: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if variant_id:
        result = gnomad_variant_lookup(
            {
                "variant_id": variant_id,
                "dataset": dataset,
                "max_populations": max_populations,
                "max_transcripts": max_transcripts,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(gnomad_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(gnomad_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["variant"] = result["raw"]

    if gene_id:
        result = gnomad_gene_lookup(
            {
                "gene_id": gene_id,
                "reference_genome": reference_genome,
                "max_transcripts": max_transcripts,
                "include_raw": include_raw,
            },
            client,
        )
        records = [record for record in result.get("records", []) if isinstance(record, dict)]
        contexts.extend(gnomad_record_context(record) for record in records)
        for record in records:
            recommended_calls.extend(gnomad_recommended_calls(record))
        source = result.get("source")
        if isinstance(source, dict):
            sources.append(source)
        if include_raw and "raw" in result:
            raw["gene"] = result["raw"]

    query_text = variant_id or gene_id or dataset or reference_genome
    filtered_contexts = [
        context
        for context in contexts
        if gnomad_context_matches(context, context_type=context_type, query=query_text)
    ]
    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=GNOMAD_CONTEXT_SCHEMA_VERSION,
        database="gnomad",
        query={
            "context_type": context_type,
            "variant_id": variant_id,
            "gene_id": gene_id,
            "dataset": dataset,
            "reference_genome": reference_genome,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "variant_id": variant_id, "gene_id": gene_id}),
        sources=sources,
        entity_groups={"variants", "genes"},
        raw=raw,
        include_raw=include_raw,
        prioritize_entities=True,
        prioritize_same_server_calls=True,
    )


def gnomad_variant_lookup(args: JsonObject, client: GnomadClient) -> JsonObject:
    variant_id = require_non_empty_string(args, "variant_id")
    dataset = optional_string(args, "dataset", default=DEFAULT_DATASET)
    include_raw = optional_bool(args, "include_raw", default=False)
    max_populations = optional_int(
        args,
        "max_populations",
        default=24,
        minimum=1,
        maximum=MAX_POPULATIONS,
    )
    max_transcripts = optional_int(
        args,
        "max_transcripts",
        default=20,
        minimum=1,
        maximum=MAX_TRANSCRIPTS,
    )
    variables: JsonObject = {"variantId": variant_id, "dataset": dataset}
    payload, headers = client.request_graphql_with_headers(VARIANT_QUERY, variables)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    variant = data.get("variant") if isinstance(data, dict) else None
    if not isinstance(variant, dict):
        ensure_no_graphql_errors(payload)
        raise GnomadError(f"gnomAD variant not found for {variant_id} in {dataset}")
    record = gnomad_variant_record(
        variant,
        dataset=dataset,
        max_populations=max_populations,
        max_transcripts=max_transcripts,
        website_base_url=client.config.website_base_url,
        graphql_url=client.config.graphql_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "gnomad",
        "query": variant_id,
        "dataset": dataset,
        "returned": 1,
        "variant": variant_summary(record),
        "records": [record],
        "source": source_with_headers("variant", variables, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def gnomad_gene_lookup(args: JsonObject, client: GnomadClient) -> JsonObject:
    gene_id = require_non_empty_string(args, "gene_id")
    reference_genome = optional_string(args, "reference_genome", default=DEFAULT_REFERENCE_GENOME)
    include_raw = optional_bool(args, "include_raw", default=False)
    max_transcripts = optional_int(
        args,
        "max_transcripts",
        default=20,
        minimum=1,
        maximum=MAX_TRANSCRIPTS,
    )
    variables: JsonObject = {"geneId": gene_id, "referenceGenome": reference_genome}
    payload, headers = client.request_graphql_with_headers(GENE_QUERY, variables)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    gene = data.get("gene") if isinstance(data, dict) else None
    if not isinstance(gene, dict):
        ensure_no_graphql_errors(payload)
        raise GnomadError(f"gnomAD gene not found for {gene_id} on {reference_genome}")
    record = gnomad_gene_record(
        gene,
        reference_genome=reference_genome,
        max_transcripts=max_transcripts,
        website_base_url=client.config.website_base_url,
        graphql_url=client.config.graphql_url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "gnomad",
        "query": gene_id,
        "reference_genome": reference_genome,
        "returned": 1,
        "gene": gene_summary(record),
        "records": [record],
        "source": source_with_headers("gene", variables, headers),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = payload
    return response


def ensure_no_graphql_errors(payload: JsonObject) -> None:
    errors = payload.get("errors")
    if isinstance(errors, list) and errors:
        messages = []
        for item in errors:
            if isinstance(item, dict) and item.get("message"):
                messages.append(str(item["message"]))
            else:
                messages.append(str(item))
        raise GnomadError("; ".join(messages))


def variant_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "variant_id": data.get("variant_id"),
        "dataset": data.get("dataset"),
        "location": data.get("location"),
        "alleles": data.get("alleles"),
        "genome_af": data.get("genome", {}).get("af") if isinstance(data.get("genome"), dict) else None,
        "exome_af": data.get("exome", {}).get("af") if isinstance(data.get("exome"), dict) else None,
        "url": data.get("url"),
    }


def gene_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "gene_id": data.get("gene_id"),
        "symbol": data.get("symbol"),
        "name": data.get("name"),
        "reference_genome": data.get("reference_genome"),
        "location": data.get("location"),
        "url": data.get("url"),
    }


def source_with_headers(operation: str, variables: JsonObject, headers: dict[str, str]) -> JsonObject:
    source = source_info(operation, variables)
    content_type = headers.get("content-type")
    if content_type:
        source["content_type"] = content_type
    return source


def optional_text(args: JsonObject, name: str) -> str:
    value = args.get(name)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise McpError(-32602, f"{name} must be a string")
    return value.strip()


def optional_context_type(args: JsonObject, name: str, *, allowed: list[str], default: str) -> str:
    value = optional_text(args, name) or default
    if value not in allowed:
        raise McpError(-32602, f"{name} must be one of: {', '.join(allowed)}")
    return value


def static_gnomad_contexts() -> list[JsonObject]:
    contexts: list[JsonObject] = [
        gnomad_parameter_context(
            "context_type",
            value,
            label=value,
            description="Dynamic gnomAD context family to resolve before variant or gene calls.",
            kind="enum",
            group="context_types",
            url="",
            metadata={"context_type": value},
        )
        for value in GNOMAD_CONTEXT_TYPES
    ]
    contexts.extend(
        gnomad_parameter_context(
            "dataset",
            dataset,
            label=dataset,
            description="gnomAD dataset ID accepted by gnomad_variant_lookup.",
            kind="dataset",
            group="datasets",
            url="https://gnomad.broadinstitute.org/",
            metadata={"dataset": dataset},
        )
        for dataset in GNOMAD_DATASET_HINTS
    )
    contexts.extend(
        gnomad_parameter_context(
            "reference_genome",
            reference,
            label=reference,
            description="Reference genome accepted by gnomad_gene_lookup.",
            kind="reference_genome",
            group="reference_genomes",
            url="https://gnomad.broadinstitute.org/",
            metadata={"reference_genome": reference},
        )
        for reference in GNOMAD_REFERENCE_GENOME_HINTS
    )
    return contexts


def gnomad_record_context(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "gnomad_gene":
        parameter_name, group, value = "gene_id", "genes", normalize_space(data.get("gene_id") or record.get("id"))
    else:
        parameter_name, group, value = "variant_id", "variants", normalize_space(data.get("variant_id") or record.get("id"))
    return gnomad_parameter_context(
        parameter_name,
        value,
        label=normalize_space(record.get("title") or record.get("label") or value),
        description=normalize_space(record.get("description") or data.get("name") or f"gnomAD {group.rstrip('s')} context."),
        kind=record_type or group.rstrip("s"),
        group=group,
        url=normalize_space(record.get("url") or data.get("url")),
        metadata={
            "id": value,
            "dataset": data.get("dataset", ""),
            "reference_genome": data.get("reference_genome", ""),
            "symbol": data.get("symbol", ""),
            "location": data.get("location", ""),
            "primary_gene": data.get("primary_gene", ""),
        },
    )


def gnomad_parameter_context(
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
    component = "variant" if group == "variants" else "gene"
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
            "component": component,
            "chip_label": parameter_name,
            "icon": "gnomad",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [{"label": "gnomAD", "kind": "source"}, {"label": parameter_name, "kind": "parameter"}],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "gnomad", "fields": display_fields},
            "primary_url": url,
        },
    }


def gnomad_recommended_calls(record: JsonObject) -> list[JsonObject]:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    record_type = normalize_space(record.get("record_type"))
    if record_type == "gnomad_gene":
        gene_id = normalize_space(data.get("gene_id") or record.get("id"))
        return [
            {"tool_name": "gnomad_gene_lookup", "arguments": {"gene_id": gene_id, "reference_genome": data.get("reference_genome") or DEFAULT_REFERENCE_GENOME}, "reason": "Fetch gnomAD gene constraint and transcript context."},
            {"server": "ensembl", "tool_name": "ensembl_lookup", "arguments": {"ensembl_id": gene_id}, "reason": "Open Ensembl gene metadata for this gene."},
        ]
    variant_id = normalize_space(data.get("variant_id") or record.get("id"))
    return [
        {"tool_name": "gnomad_variant_lookup", "arguments": {"variant_id": variant_id, "dataset": data.get("dataset") or DEFAULT_DATASET}, "reason": "Fetch gnomAD allele frequencies and transcript consequences for this variant."},
        {"server": "clinvar", "tool_name": "clinvar_search", "arguments": {"terms": variant_id}, "reason": "Search ClinVar for clinical interpretation of this variant."},
    ]


def gnomad_context_matches(context: JsonObject, *, context_type: str, query: str) -> bool:
    if context_type != "all" and context.get("group") != context_type:
        return False
    if not query:
        return True
    metadata = context.get("metadata")
    haystack_values = [context.get("parameter_name"), context.get("value"), context.get("label"), context.get("description"), context.get("kind")]
    if isinstance(metadata, dict):
        haystack_values.extend(metadata.values())
    haystack = " ".join(str(item).lower() for item in haystack_values if item not in ("", None))
    return query.lower() in haystack or context.get("group") in {"variants", "genes"}


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("gnomad_parameter_domains"),
        {
            "name": "gnomad_resolve_context",
            "title": "Resolve gnomAD dynamic parameter context",
            "description": (
                "Resolve gnomAD variant IDs, gene IDs, dataset IDs, and reference genome hints before lookup calls. "
                "Returns app-renderable context rows, gnomAD URLs, and recommended follow-up calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {"type": "string", "enum": GNOMAD_CONTEXT_TYPES, "default": "all"},
                    "variant_id": {"type": "string", "description": "Optional gnomAD variant ID such as 1-230710048-A-G."},
                    "gene_id": {"type": "string", "description": "Optional Ensembl gene ID such as ENSG00000141510."},
                    "dataset": {"type": "string", "default": DEFAULT_DATASET},
                    "reference_genome": {"type": "string", "default": DEFAULT_REFERENCE_GENOME},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_TRANSCRIPTS, "default": 10},
                    "max_populations": {"type": "integer", "minimum": 1, "maximum": MAX_POPULATIONS, "default": 24},
                    "max_transcripts": {"type": "integer", "minimum": 1, "maximum": MAX_TRANSCRIPTS, "default": 20},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gnomad_variant_lookup",
            "title": "Look up a gnomAD variant",
            "description": (
                "Fetch one gnomAD variant by variant ID such as 1-230710048-A-G "
                "and return a front-end-compatible variant record with frequencies."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "variant_id": {
                        "type": "string",
                        "description": "gnomAD variant ID, for example 1-230710048-A-G.",
                    },
                    "dataset": {
                        "type": "string",
                        "default": DEFAULT_DATASET,
                        "description": "gnomAD dataset ID, for example gnomad_r4.",
                    },
                    "max_populations": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_POPULATIONS,
                        "default": 24,
                    },
                    "max_transcripts": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TRANSCRIPTS,
                        "default": 20,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["variant_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gnomad_gene_lookup",
            "title": "Look up a gnomAD gene constraint record",
            "description": (
                "Fetch one gnomAD gene by Ensembl gene ID and return a gene record "
                "with constraint metrics and transcript previews."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "gene_id": {
                        "type": "string",
                        "description": "Ensembl gene ID, for example ENSG00000141510.",
                    },
                    "reference_genome": {
                        "type": "string",
                        "default": DEFAULT_REFERENCE_GENOME,
                        "description": "Reference genome for the gene query, for example GRCh38.",
                    },
                    "max_transcripts": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": MAX_TRANSCRIPTS,
                        "default": 20,
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["gene_id"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "gnomad_status",
            "title": "Inspect gnomAD MCP status",
            "description": "Return configured gnomAD MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, GnomadClient], JsonObject]] = {
    "gnomad_parameter_domains": make_parameter_domains_handler("gnomad", "gnomad_parameter_domains", tool_definitions),
    "gnomad_resolve_context": gnomad_resolve_context,
    "gnomad_variant_lookup": gnomad_variant_lookup,
    "gnomad_gene_lookup": gnomad_gene_lookup,
    "gnomad_status": gnomad_status,
}
