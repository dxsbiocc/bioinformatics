"""MCP tool registry for the gnomAD server."""

from __future__ import annotations

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
from .errors import GnomadError
from .records import gnomad_gene_record, gnomad_variant_record
from .utils import (
    optional_bool,
    optional_int,
    optional_string,
    require_non_empty_string,
    source_info,
)


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


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
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
    "gnomad_variant_lookup": gnomad_variant_lookup,
    "gnomad_gene_lookup": gnomad_gene_lookup,
    "gnomad_status": gnomad_status,
}

