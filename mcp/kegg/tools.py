"""MCP tool registry for the KEGG server."""

from __future__ import annotations

from typing import Callable

from mcp.dynamic_context import build_dynamic_context_response
from mcp.parameter_domains import make_parameter_domains_handler, parameter_domains_tool_definition

from .client import KeggClient
from .constants import (
    COMMON_DATABASES,
    COLOR_URL_FORMS,
    DEFAULT_MAX_RESULTS,
    FIND_OPTIONS,
    GET_OPTIONS,
    LINK_OPTIONS,
    MAX_COLOR_ITEMS,
    MAX_GET_ENTRIES,
    MAX_RESULTS,
    RESULT_SCHEMA_VERSION,
    JsonObject,
)
from .errors import McpError
from .parsers import parse_fasta, parse_flat_records, parse_link_rows, tsv_records
from .records import (
    kegg_conversion_record,
    kegg_colored_pathway_record,
    kegg_download_record,
    kegg_entry_record,
    kegg_info_record,
    kegg_linkset_record,
    kegg_sequence_record,
    kegg_tsv_record,
)
from .utils import (
    join_dbentries,
    optional_bool,
    optional_enum,
    optional_float,
    optional_max_results,
    optional_string,
    normalize_color_spec,
    normalize_entry_id,
    require_color_items,
    require_entry_ids,
    require_map_id,
    require_non_empty_string,
    source_info,
)


KEGG_CONTEXT_TYPES = ["all", "databases", "organisms", "pathways", "coloring"]
KEGG_CONTEXT_SCHEMA_VERSION = "bioinformatics.dynamic_context.v1"


def kegg_status(args: JsonObject, client: KeggClient) -> JsonObject:
    check_network = optional_bool(args, "check_network", default=False)
    available_tools = [tool["name"] for tool in tool_definitions()]
    status: JsonObject = {
        "server": "kegg",
        "version": "0.1.0",
        "base_url": client.config.base_url,
        "website_base_url": client.config.website_base_url,
        "tool": client.config.tool,
        "contact_configured": bool(client.config.contact),
        "rate_limit_requests_per_second": client.requests_per_second,
        "license_notice": "KEGG REST is intended for academic use and should be called at no more than 3 requests per second.",
        "available_tool_count": len(available_tools),
        "available_tools": available_tools,
        "available_databases": COMMON_DATABASES,
        "tool_groups": {
            "context": ["kegg_parameter_domains", "kegg_resolve_context"],
            "catalog": ["kegg_info", "kegg_list", "kegg_find"],
            "entry": ["kegg_get"],
            "mapping": ["kegg_conv", "kegg_link", "kegg_ddi"],
            "pathway_annotation": ["kegg_color_pathway_url", "kegg_color_pathway_from_table"],
            "status": ["kegg_status"],
        },
        "frontend_components": [
            "database",
            "dataset",
            "pathway",
            "gene",
            "compound",
            "protein",
            "identifier_conversion",
            "linkset",
        ],
        "preview_kinds": ["table", "xref_groups", "text", "sequence", "chemical_structure", "download_manifest", "network"],
        "record_schema_version": "bioinformatics.record.v1",
    }
    if check_network:
        text, headers, endpoint, url = client.request_text_with_headers("info", ["kegg"])
        status["network_check"] = {
            "ok": True,
            "endpoint": endpoint,
            "url": url,
            "content_type": headers.get("content-type"),
            "first_line": text.splitlines()[0] if text.splitlines() else "",
        }
    return status


def kegg_resolve_context(args: JsonObject, client: KeggClient) -> JsonObject:
    context_type = optional_enum(args, "context_type", allowed=KEGG_CONTEXT_TYPES, default="all")
    query = optional_string(args, "query", default="")
    organism = optional_string(args, "organism", default="hsa")
    map_id = optional_string(args, "map_id", default="")
    max_results = optional_max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    contexts: list[JsonObject] = []
    recommended_calls: list[JsonObject] = []
    diagnostics: list[JsonObject] = []
    sources: list[JsonObject] = []
    raw: JsonObject = {}

    if context_type in {"all", "databases"}:
        contexts.extend(kegg_database_context(database, client) for database in COMMON_DATABASES)
    if context_type in {"all", "coloring"}:
        contexts.extend(kegg_coloring_contexts(client, map_id=map_id or "hsa04110"))
        recommended_calls.extend(kegg_coloring_recommendations(map_id))

    should_fetch_organisms = context_type == "organisms" or (context_type == "all" and bool(query))
    if should_fetch_organisms:
        text, headers, endpoint, url = client.request_text_with_headers("list", ["organism"])
        rows = tsv_records(text, kind="organism")
        raw["organisms"] = text
        sources.append(source_with_headers(endpoint, {}, headers, url))
        contexts.extend(kegg_organism_context(row, client, source_endpoint=endpoint) for row in rows)

    should_fetch_pathways = context_type == "pathways" or (context_type == "all" and bool(query or map_id))
    if should_fetch_pathways:
        target_organism = organism or infer_organism_from_map_id(map_id) or "hsa"
        text, headers, endpoint, url = client.request_text_with_headers("list", ["pathway", target_organism])
        rows = tsv_records(text)
        raw["pathways"] = text
        sources.append(source_with_headers(endpoint, {"organism": target_organism}, headers, url))
        pathway_contexts = [kegg_pathway_context(row, client, source_endpoint=endpoint) for row in rows]
        contexts.extend(pathway_contexts)
        recommended_calls.extend(kegg_pathway_recommendations(pathway_contexts, map_id=map_id, query=query))

    filtered_contexts = [context for context in contexts if kegg_context_matches(context, query, map_id=map_id)]
    selected_contexts = filtered_contexts[:max_results]
    if context_type in {"pathways", "organisms"} and not selected_contexts:
        diagnostics.append(
            {
                "code": "kegg_context_no_matches",
                "severity": "info",
                "message": "No KEGG context candidates matched the supplied query and filters.",
                "recoverable": True,
                "suggested_action": "Try a broader query, a different organism code, or kegg_list directly.",
            }
        )

    return build_dynamic_context_response(
        schema_version=RESULT_SCHEMA_VERSION,
        context_schema_version=KEGG_CONTEXT_SCHEMA_VERSION,
        database="kegg",
        query={
            "context_type": context_type,
            "query": query,
            "organism": organism,
            "map_id": map_id,
        },
        contexts=filtered_contexts,
        recommended_calls=recommended_calls,
        max_results=max_results,
        fallback_source=source_info("resolve_context", {"context_type": context_type, "query": query}),
        sources=sources,
        raw=raw,
        summary_fields={
            "entities": lambda context: context.get("parameter_name") in {"database", "organism", "map_id"},
            "databases": lambda context: context.get("parameter_name") == "database",
            "organisms": lambda context: context.get("parameter_name") == "organism",
            "pathways": lambda context: context.get("parameter_name") == "map_id",
        },
        extra_fields={
            "license_notice": "KEGG REST is intended for academic use and should be called at no more than 3 requests per second.",
            **({"diagnostics": diagnostics} if diagnostics else {}),
        },
        include_raw=include_raw,
        dedupe_calls=False,
    )


def kegg_info(args: JsonObject, client: KeggClient) -> JsonObject:
    database = require_non_empty_string(args, "database")
    include_raw = optional_bool(args, "include_raw", default=False)
    text, headers, endpoint, url = client.request_text_with_headers("info", [database])
    record = kegg_info_record(database, text, website_base_url=client.config.website_base_url, api_url=url)
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "info",
        "query": database,
        "returned": 1,
        "records": [record],
        "database_info": record["data"],
        "source": source_with_headers(endpoint, {}, headers, url),
        "license_notice": "KEGG REST is intended for academic use and should be called at no more than 3 requests per second.",
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_list(args: JsonObject, client: KeggClient) -> JsonObject:
    database = require_non_empty_string(args, "database")
    option = optional_string(args, "option", default="")
    max_results = optional_max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    segments = [database] + ([option] if option else [])
    text, headers, endpoint, url = client.request_text_with_headers("list", segments)
    kind = "organism" if database == "organism" else ""
    rows = tsv_records(text, kind=kind)
    selected = rows[:max_results]
    records = [
        kegg_tsv_record(
            row,
            operation="list",
            database=database,
            website_base_url=client.config.website_base_url,
            api_url=url,
        )
        for row in selected
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "list",
        "query": database,
        "option": option,
        "returned": len(records),
        "total": len(rows),
        "entries": [entry_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, {"option": option} if option else {}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_find(args: JsonObject, client: KeggClient) -> JsonObject:
    database = require_non_empty_string(args, "database")
    query = require_non_empty_string(args, "query")
    option = optional_enum(args, "option", allowed=FIND_OPTIONS, default="")
    max_results = optional_max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    segments = [database, query] + ([option] if option else [])
    text, headers, endpoint, url = client.request_text_with_headers("find", segments)
    rows = tsv_records(text)
    selected = rows[:max_results]
    records = [
        kegg_tsv_record(
            row,
            operation="find",
            database=database,
            website_base_url=client.config.website_base_url,
            api_url=url,
        )
        for row in selected
    ]
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "find",
        "query": query,
        "target_database": database,
        "option": option,
        "returned": len(records),
        "total": len(rows),
        "entries": [entry_summary(record) for record in records],
        "records": records,
        "source": source_with_headers(endpoint, {"database": database, "query": query, "option": option}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_get(args: JsonObject, client: KeggClient) -> JsonObject:
    entry_ids = require_entry_ids(args)
    if len(entry_ids) > MAX_GET_ENTRIES:
        raise McpError(-32602, f"entry_ids supports at most {MAX_GET_ENTRIES} entries per call")
    option = optional_enum(args, "option", allowed=GET_OPTIONS, default="")
    include_raw = optional_bool(args, "include_raw", default=False)
    dbentries = join_dbentries(entry_ids)
    segments = [dbentries] + ([option] if option else [])
    endpoint_url = client.build_url("get", segments)
    if option in {"image", "image2x", "mol", "kcf", "conf", "kgml", "json"}:
        records = [
            kegg_download_record(
                entry_id,
                option=option,
                website_base_url=client.config.website_base_url,
                api_url=client.build_url("get", [entry_id, option]),
            )
            for entry_id in entry_ids
        ]
        response: JsonObject = {
            "schema_version": RESULT_SCHEMA_VERSION,
            "database": "kegg",
            "operation": "get",
            "query": dbentries,
            "option": option,
            "returned": len(records),
            "records": records,
            "source": source_info("get/" + "/".join(segments), {"option": option}, url=endpoint_url),
        }
        response["provenance"] = response["source"]
        return response

    text, headers, endpoint, url = client.request_text_with_headers("get", segments)
    if option in {"aaseq", "ntseq"}:
        alphabet = "protein" if option == "aaseq" else "dna"
        fasta_records = parse_fasta(text)
        records = [
            kegg_sequence_record(
                sequence,
                alphabet=alphabet,
                website_base_url=client.config.website_base_url,
                api_url=url,
            )
            for sequence in fasta_records
        ]
    else:
        entries = parse_flat_records(text)
        records = [
            kegg_entry_record(
                entry,
                website_base_url=client.config.website_base_url,
                api_url=url,
            )
            for entry in entries
        ]
    response = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "get",
        "query": dbentries,
        "option": option,
        "returned": len(records),
        "records": records,
        "entries": [entry_summary(record) for record in records],
        "source": source_with_headers(endpoint, {"option": option} if option else {}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_conv(args: JsonObject, client: KeggClient) -> JsonObject:
    target_db = require_non_empty_string(args, "target_db")
    source_db_or_entries = require_non_empty_string(args, "source_db_or_entries")
    max_results = optional_max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    text, headers, endpoint, url = client.request_text_with_headers("conv", [target_db, source_db_or_entries])
    rows = parse_link_rows(text)
    selected = rows[:max_results]
    record = kegg_conversion_record(
        selected,
        target_db=target_db,
        source_db_or_entries=source_db_or_entries,
        website_base_url=client.config.website_base_url,
        api_url=url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "conv",
        "query": source_db_or_entries,
        "target_db": target_db,
        "returned": len(selected),
        "total": len(rows),
        "rows": selected,
        "records": [record],
        "source": source_with_headers(endpoint, {}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_link(args: JsonObject, client: KeggClient) -> JsonObject:
    target_db = require_non_empty_string(args, "target_db")
    source_db_or_entries = require_non_empty_string(args, "source_db_or_entries")
    option = optional_enum(args, "option", allowed=LINK_OPTIONS, default="")
    max_results = optional_max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    segments = [target_db, source_db_or_entries] + ([option] if option else [])
    text, headers, endpoint, url = client.request_text_with_headers("link", segments)
    rows = parse_link_rows(text)
    selected = rows[:max_results]
    record = kegg_linkset_record(
        selected,
        target_db=target_db,
        source_db_or_entries=source_db_or_entries,
        operation="link",
        option=option,
        website_base_url=client.config.website_base_url,
        api_url=url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "link",
        "query": source_db_or_entries,
        "target_db": target_db,
        "option": option,
        "returned": len(selected),
        "total": len(rows),
        "rows": selected,
        "records": [record],
        "source": source_with_headers(endpoint, {"option": option} if option else {}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_ddi(args: JsonObject, client: KeggClient) -> JsonObject:
    drug_ids = require_entry_ids(args)
    target = optional_string(args, "target", default="")
    max_results = optional_max_results(args)
    include_raw = optional_bool(args, "include_raw", default=False)
    source = join_dbentries(drug_ids)
    segments = [source] + ([target] if target else [])
    text, headers, endpoint, url = client.request_text_with_headers("ddi", segments)
    rows = parse_link_rows(text)
    selected = rows[:max_results]
    record = kegg_linkset_record(
        selected,
        target_db=target or "drug",
        source_db_or_entries=source,
        operation="ddi",
        website_base_url=client.config.website_base_url,
        api_url=url,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "ddi",
        "query": source,
        "target": target,
        "returned": len(selected),
        "total": len(rows),
        "rows": selected,
        "records": [record],
        "source": source_with_headers(endpoint, {"target": target} if target else {}, headers, url),
    }
    response["provenance"] = response["source"]
    if include_raw:
        response["raw"] = text
    return response


def kegg_color_pathway_url_tool(args: JsonObject, client: KeggClient) -> JsonObject:
    map_id = require_map_id(args)
    items = require_color_items(args, max_items=MAX_COLOR_ITEMS)
    url_form = optional_enum(args, "url_form", allowed=COLOR_URL_FORMS, default="query")
    nocolor = optional_bool(args, "nocolor", default=False)
    default_bgcolor = optional_string(args, "default_bgcolor", default="")
    warnings = color_url_warnings(items, url_form=url_form, nocolor=nocolor, default_bgcolor=default_bgcolor)
    record = kegg_colored_pathway_record(
        map_id,
        items,
        website_base_url=client.config.website_base_url,
        url_form=url_form,
        nocolor=nocolor,
        default_bgcolor=default_bgcolor,
        generated_from="items",
        warnings=warnings,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "color_pathway_url",
        "query": map_id,
        "map_id": map_id,
        "returned": 1,
        "item_count": len(items),
        "multi_query": record["data"]["multi_query"],
        "url": record["url"],
        "records": [record],
        "source": source_info(
            "kegg-bin/show_pathway",
            {
                "map": map_id,
                "item_count": len(items),
                "url_form": url_form,
                "nocolor": nocolor,
                "default_bgcolor": default_bgcolor,
            },
            url=record["url"],
        ),
    }
    response["provenance"] = response["source"]
    if warnings:
        response["warnings"] = warnings
    return response


def kegg_color_pathway_from_table(args: JsonObject, client: KeggClient) -> JsonObject:
    map_id = require_map_id(args)
    rows = require_table_rows(args)
    id_column = optional_string(args, "id_column", default="kegg_id")
    value_column = optional_string(args, "value_column", default="log2fc")
    pvalue_column = optional_string(args, "pvalue_column", default="padj")
    label_column = optional_string(args, "label_column", default="")
    up_threshold = optional_float(args, "up_threshold", default=1.0)
    down_threshold = optional_float(args, "down_threshold", default=-1.0)
    pvalue_threshold = optional_float(args, "pvalue_threshold", default=0.05, minimum=0.0, maximum=1.0)
    up_color = optional_string(args, "up_color", default="#d73027")
    down_color = optional_string(args, "down_color", default="#4575b4")
    neutral_color = optional_string(args, "neutral_color", default="#d9d9d9")
    fgcolor = optional_string(args, "fgcolor", default="#000000")
    for color_name, color in [
        ("up_color", up_color),
        ("down_color", down_color),
        ("neutral_color", neutral_color),
        ("fgcolor", fgcolor),
    ]:
        try:
            normalize_color_spec(color)
        except McpError as exc:
            raise McpError(-32602, f"{color_name} is invalid: {exc.message}") from exc
    include_neutral = optional_bool(args, "include_neutral", default=False)
    url_form = optional_enum(args, "url_form", allowed=COLOR_URL_FORMS, default="query")
    nocolor = optional_bool(args, "nocolor", default=False)
    default_bgcolor = optional_string(args, "default_bgcolor", default="")

    items, skipped_rows = color_items_from_rows(
        rows,
        id_column=id_column,
        value_column=value_column,
        pvalue_column=pvalue_column,
        label_column=label_column,
        up_threshold=up_threshold,
        down_threshold=down_threshold,
        pvalue_threshold=pvalue_threshold,
        up_color=up_color,
        down_color=down_color,
        neutral_color=neutral_color,
        fgcolor=fgcolor,
        include_neutral=include_neutral,
    )
    if not items:
        raise McpError(-32602, "No rows could be converted to colored KEGG identifiers")
    warnings = color_url_warnings(items, url_form=url_form, nocolor=nocolor, default_bgcolor=default_bgcolor)
    if skipped_rows:
        warnings.append(f"Skipped {len(skipped_rows)} rows without usable KEGG IDs or numeric values")
    record = kegg_colored_pathway_record(
        map_id,
        items,
        website_base_url=client.config.website_base_url,
        url_form=url_form,
        nocolor=nocolor,
        default_bgcolor=default_bgcolor,
        generated_from="table",
        warnings=warnings,
    )
    response: JsonObject = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "database": "kegg",
        "operation": "color_pathway_from_table",
        "query": map_id,
        "map_id": map_id,
        "returned": 1,
        "input_rows": len(rows),
        "item_count": len(items),
        "skipped_row_count": len(skipped_rows),
        "multi_query": record["data"]["multi_query"],
        "url": record["url"],
        "records": [record],
        "source": source_info(
            "kegg-bin/show_pathway",
            {
                "map": map_id,
                "input_rows": len(rows),
                "item_count": len(items),
                "id_column": id_column,
                "value_column": value_column,
                "pvalue_column": pvalue_column,
            },
            url=record["url"],
        ),
    }
    response["provenance"] = response["source"]
    if warnings:
        response["warnings"] = warnings
    if skipped_rows:
        response["skipped_rows"] = skipped_rows[:50]
    return response


def require_table_rows(args: JsonObject) -> list[JsonObject]:
    rows = args.get("rows")
    if not isinstance(rows, list) or not rows:
        raise McpError(-32602, "rows is required and must be a non-empty array")
    if len(rows) > MAX_COLOR_ITEMS:
        raise McpError(-32602, f"rows supports at most {MAX_COLOR_ITEMS} rows")
    out: list[JsonObject] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise McpError(-32602, f"rows[{index}] must be an object")
        out.append(row)
    return out


def color_items_from_rows(
    rows: list[JsonObject],
    *,
    id_column: str,
    value_column: str,
    pvalue_column: str,
    label_column: str,
    up_threshold: float,
    down_threshold: float,
    pvalue_threshold: float,
    up_color: str,
    down_color: str,
    neutral_color: str,
    fgcolor: str,
    include_neutral: bool,
) -> tuple[list[JsonObject], list[JsonObject]]:
    items: list[JsonObject] = []
    skipped: list[JsonObject] = []
    seen: set[str] = set()
    for index, row in enumerate(rows):
        try:
            kegg_id = normalize_entry_id(row.get(id_column, ""))
        except McpError:
            skipped.append({"row_index": index, "reason": "invalid_id"})
            continue
        if not kegg_id:
            skipped.append({"row_index": index, "reason": "missing_id"})
            continue
        try:
            value = float(row.get(value_column))
        except (TypeError, ValueError):
            skipped.append({"row_index": index, "kegg_id": kegg_id, "reason": "non_numeric_value"})
            continue
        pvalue = None
        raw_pvalue = row.get(pvalue_column) if pvalue_column else None
        if raw_pvalue is not None and raw_pvalue != "":
            try:
                pvalue = float(raw_pvalue)
            except (TypeError, ValueError):
                skipped.append({"row_index": index, "kegg_id": kegg_id, "reason": "non_numeric_pvalue"})
                continue
        significant = pvalue is None or pvalue <= pvalue_threshold
        color = ""
        direction = "neutral"
        if significant and value >= up_threshold:
            color = up_color
            direction = "up"
        elif significant and value <= down_threshold:
            color = down_color
            direction = "down"
        elif include_neutral:
            color = neutral_color
        else:
            skipped.append({"row_index": index, "kegg_id": kegg_id, "reason": "neutral_or_not_significant"})
            continue
        if kegg_id in seen:
            skipped.append({"row_index": index, "kegg_id": kegg_id, "reason": "duplicate_id"})
            continue
        seen.add(kegg_id)
        color_item = {
            "kegg_id": kegg_id,
            "bgcolor": color,
            "fgcolor": fgcolor,
            "color": f"{color},{fgcolor}" if fgcolor else color,
            "label": str(row.get(label_column, "")).strip() if label_column else str(row.get(id_column, "")).strip(),
            "source_value": str(value),
            "direction": direction,
            "pvalue": pvalue if pvalue is not None else "",
        }
        items.append(color_item)
    return items, skipped


def color_url_warnings(
    items: list[JsonObject],
    *,
    url_form: str,
    nocolor: bool,
    default_bgcolor: str,
) -> list[str]:
    warnings: list[str] = []
    if url_form == "slash" and nocolor:
        warnings.append("nocolor is only supported by the query-form KEGG coloring URL")
    if url_form == "query" and default_bgcolor:
        warnings.append("default_bgcolor is only encoded in the slash-form KEGG coloring URL")
    if any(not item.get("color") for item in items):
        warnings.append("Some items have no explicit color; KEGG may apply its default coloring")
    return warnings


def kegg_database_context(database: str, client: KeggClient) -> JsonObject:
    return kegg_parameter_context(
        "database",
        database,
        label=f"KEGG {database}",
        description="KEGG REST database accepted by info, list, find, link, and conversion operations.",
        kind="database",
        url=client.build_url("info", [database]),
        source_endpoint="static:COMMON_DATABASES",
        metadata={"database": database, "tool_hint": "kegg_info"},
    )


def kegg_coloring_contexts(client: KeggClient, *, map_id: str) -> list[JsonObject]:
    examples = [
        ("items[].kegg_id", "hsa:7157", "KEGG gene ID, commonly produced by kegg_conv or organism-specific gene lists."),
        ("items[].kegg_id", "K00844", "KEGG Orthology identifier accepted by pathway coloring."),
        ("items[].kegg_id", "C00031", "KEGG compound identifier accepted by pathway coloring."),
        ("items[].kegg_id", "D00564", "KEGG drug identifier accepted by pathway coloring."),
        ("items[].color", "#d73027,#000000", "KEGG background,foreground color specification."),
        ("url_form", "query", "Official show_pathway query form with map and multi_query parameters."),
        ("url_form", "slash", "Official show_pathway slash form for map/dataset/default-color paths."),
        ("id_column", "kegg_id", "Table column used by kegg_color_pathway_from_table for KEGG identifiers."),
        ("value_column", "log2fc", "Numeric table column used for directional coloring."),
        ("pvalue_column", "padj", "Optional adjusted p-value column used to suppress non-significant rows."),
    ]
    contexts = [
        kegg_parameter_context(
            parameter_name,
            value,
            label=value,
            description=description,
            kind="pathway_coloring_parameter",
            url=f"{client.config.website_base_url.rstrip('/')}/kegg/webapp/color_url.html",
            source_endpoint="kegg/webapp/color_url.html",
            metadata={"map_id": map_id, "tool_hint": "kegg_color_pathway_url"},
        )
        for parameter_name, value, description in examples
    ]
    return contexts


def kegg_organism_context(row: JsonObject, client: KeggClient, *, source_endpoint: str) -> JsonObject:
    code = str(row.get("code") or "")
    description = str(row.get("description") or code)
    return kegg_parameter_context(
        "organism",
        code,
        label=description,
        description=str(row.get("lineage") or "KEGG organism code"),
        kind="organism",
        url=client.entry_url(code),
        source_endpoint=source_endpoint,
        metadata={
            "organism_code": code,
            "taxon_id": row.get("entry_id") or "",
            "lineage": row.get("lineage") or "",
            "tool_hint": "kegg_list",
        },
    )


def kegg_pathway_context(row: JsonObject, client: KeggClient, *, source_endpoint: str) -> JsonObject:
    entry_id = str(row.get("entry_id") or "")
    map_id = entry_id.split(":", 1)[1] if entry_id.startswith("path:") else entry_id
    description = str(row.get("description") or map_id)
    return kegg_parameter_context(
        "map_id",
        map_id,
        label=description,
        description="KEGG pathway map ID accepted by kegg_get and KEGG pathway coloring tools.",
        kind="pathway",
        url=client.entry_url(map_id),
        source_endpoint=source_endpoint,
        metadata={
            "entry_id": entry_id,
            "map_id": map_id,
            "organism": infer_organism_from_map_id(map_id),
            "tool_hint": "kegg_color_pathway_url",
        },
    )


def kegg_parameter_context(
    parameter_name: str,
    value: object,
    *,
    label: str,
    description: str,
    kind: str,
    url: str,
    source_endpoint: str,
    metadata: JsonObject | None = None,
) -> JsonObject:
    metadata = metadata or {}
    display_fields = [{"label": key.replace("_", " ").title(), "value": item} for key, item in metadata.items() if item not in ("", None, [], {})]
    if url:
        display_fields.append({"label": "URL", "value": url})
    return {
        "kind": kind,
        "parameter_name": parameter_name,
        "value": value,
        "label": label,
        "title": label,
        "description": description,
        "url": url,
        "source": source_endpoint,
        "metadata": metadata,
        "display": {
            "component": "dataset" if kind != "pathway" else "pathway",
            "chip_label": parameter_name,
            "icon": "kegg",
            "title": label,
            "subtitle": f"{parameter_name}: {value}",
            "description": description,
            "metadata": display_fields,
            "badges": [
                {"label": "KEGG", "kind": "source"},
                {"label": parameter_name, "kind": "parameter"},
            ],
            "actions": [{"label": "Open source", "url": url, "kind": "external", "primary": True}] if url else [],
            "hover": {"title": label, "subtitle": f"{parameter_name}: {value}", "icon": "kegg", "fields": display_fields},
            "primary_url": url,
        },
    }


def kegg_pathway_recommendations(contexts: list[JsonObject], *, map_id: str, query: str) -> list[JsonObject]:
    calls: list[JsonObject] = []
    selected = [context for context in contexts if kegg_context_matches(context, query, map_id=map_id)][:5]
    for context in selected:
        resolved_map_id = str(context.get("value") or "")
        entry_id = str(context.get("metadata", {}).get("entry_id") or f"path:{resolved_map_id}")
        calls.extend(
            [
                {
                    "tool_name": "kegg_get",
                    "arguments": {"entry_ids": [entry_id]},
                    "reason": "Fetch pathway details, genes, compounds, and cross-references before downstream interpretation.",
                },
                {
                    "tool_name": "kegg_color_pathway_url",
                    "arguments": {"map_id": resolved_map_id},
                    "requires": ["items"],
                    "reason": "Color this pathway after analysis rows have been mapped to KEGG IDs.",
                },
            ]
        )
    return calls


def kegg_coloring_recommendations(map_id: str) -> list[JsonObject]:
    if not map_id:
        return []
    return [
        {
            "tool_name": "kegg_color_pathway_url",
            "arguments": {"map_id": map_id},
            "requires": ["items"],
            "reason": "Build a clickable official KEGG colored-map URL after supplying KEGG IDs and colors.",
        },
        {
            "tool_name": "kegg_color_pathway_from_table",
            "arguments": {"map_id": map_id, "id_column": "kegg_id", "value_column": "log2fc", "pvalue_column": "padj"},
            "requires": ["rows"],
            "reason": "Color the pathway directly from result-table rows that already contain KEGG IDs.",
        },
    ]


def kegg_context_matches(context: JsonObject, query: str, *, map_id: str) -> bool:
    fields = [
        context.get("parameter_name"),
        context.get("value"),
        context.get("label"),
        context.get("title"),
        context.get("description"),
        context.get("kind"),
    ]
    metadata = context.get("metadata")
    if isinstance(metadata, dict):
        fields.extend(metadata.values())
    haystack = " ".join(str(field).lower() for field in fields if field not in (None, ""))
    if query and query.lower() not in haystack:
        return False
    if map_id:
        if str(context.get("parameter_name")) in {"items[].kegg_id", "items[].color", "url_form", "id_column", "value_column", "pvalue_column"}:
            return True
        return map_id.lower() in haystack
    return True


def infer_organism_from_map_id(map_id: str) -> str:
    letters = []
    for character in map_id:
        if character.isalpha():
            letters.append(character)
            continue
        break
    organism = "".join(letters)
    return "" if organism == "map" else organism


def source_with_headers(
    endpoint: str,
    params: JsonObject,
    headers: dict[str, str],
    url: str,
) -> JsonObject:
    source = source_info(endpoint, params, url=url)
    content_type = headers.get("content-type")
    if content_type:
        source["content_type"] = content_type
    return source


def entry_summary(record: JsonObject) -> JsonObject:
    data = record.get("data") if isinstance(record.get("data"), dict) else {}
    return {
        "entry_id": data.get("entry_id") or record.get("id"),
        "title": record.get("title"),
        "record_type": record.get("record_type"),
        "component": record.get("display", {}).get("component") if isinstance(record.get("display"), dict) else "",
        "url": record.get("url"),
    }


def tool_definitions() -> list[JsonObject]:
    read_only_annotations = {
        "readOnlyHint": True,
        "openWorldHint": True,
    }
    return [
        parameter_domains_tool_definition("kegg_parameter_domains"),
        {
            "name": "kegg_resolve_context",
            "title": "Resolve KEGG dynamic parameter context",
            "description": (
                "Resolve KEGG databases, organism codes, pathway map IDs, and coloring parameter hints before REST or pathway-coloring calls. "
                "Returns front-end-friendly context rows, source URLs, and recommended next calls."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "context_type": {
                        "type": "string",
                        "enum": KEGG_CONTEXT_TYPES,
                        "default": "all",
                        "description": "Context family to resolve. Use pathways for organism-specific map IDs and coloring for KEGG Color URL inputs.",
                    },
                    "query": {"type": "string", "description": "Optional text filter such as cell cycle, human, compound, or pathway."},
                    "organism": {"type": "string", "default": "hsa", "description": "KEGG organism code used when resolving pathway maps, for example hsa or mmu."},
                    "map_id": {"type": "string", "description": "Optional KEGG pathway map ID such as hsa04110 to validate and seed coloring calls."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_MAX_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_info",
            "title": "Inspect a KEGG database",
            "description": "Call KEGG REST info for one database and return a database record with text preview and links.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "KEGG database name, for example kegg, pathway, compound, drug, genome, hsa, or ko.",
                    },
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["database"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_list",
            "title": "List KEGG database entries",
            "description": "Call KEGG REST list and return app-renderable records for database entries or organisms.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "database": {
                        "type": "string",
                        "description": "Database, organism code, or dbentries segment accepted by KEGG list, for example pathway, hsa, organism, compound.",
                    },
                    "option": {
                        "type": "string",
                        "description": "Optional KEGG list second path segment, for example an organism code for pathway or a brite/genome option.",
                    },
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_MAX_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["database"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_find",
            "title": "Search KEGG entries",
            "description": "Call KEGG REST find for a database and query, with optional chemical search modes.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "database": {"type": "string", "description": "KEGG database, for example compound, drug, genes, pathway, or hsa."},
                    "query": {"type": "string", "description": "Text query or chemical formula/mass depending on option."},
                    "option": {"type": "string", "enum": FIND_OPTIONS, "description": "Optional chemical search mode supported by KEGG find."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_MAX_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["database", "query"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_get",
            "title": "Fetch KEGG entries",
            "description": "Call KEGG REST get for one or more entries and return flat-file, FASTA, or downloadable resource records.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entry_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": MAX_GET_ENTRIES,
                        "description": "KEGG entry identifiers, for example hsa:10458, C00002, path:hsa00010, or D01441.",
                    },
                    "dbentries": {
                        "type": "string",
                        "description": "Alternative KEGG dbentries path segment, for example hsa:10458+ece:Z5100.",
                    },
                    "option": {"type": "string", "enum": GET_OPTIONS, "description": "Optional KEGG get format such as aaseq, ntseq, kgml, image, mol, kcf, json."},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "anyOf": [{"required": ["entry_ids"]}, {"required": ["dbentries"]}],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_conv",
            "title": "Convert KEGG identifiers",
            "description": "Call KEGG REST conv to convert identifiers between KEGG and external databases.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_db": {"type": "string", "description": "Target database, for example ncbi-geneid, uniprot, pubchem, or compound."},
                    "source_db_or_entries": {"type": "string", "description": "Source database or dbentries segment, for example hsa, ncbi-geneid, uniprot, or hsa:10458."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_MAX_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["target_db", "source_db_or_entries"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_link",
            "title": "Link KEGG related entries",
            "description": "Call KEGG REST link to retrieve relationships between a source database or entries and a target database.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "target_db": {"type": "string", "description": "Target database, for example pathway, genes, compound, reaction, disease, or drug."},
                    "source_db_or_entries": {"type": "string", "description": "Source database or dbentries segment, for example hsa, hsa:10458, compound, or D01441."},
                    "option": {"type": "string", "enum": LINK_OPTIONS, "description": "Optional taxonomy/RDF option supported by KEGG link."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_MAX_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "required": ["target_db", "source_db_or_entries"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_ddi",
            "title": "Fetch KEGG drug-drug interactions",
            "description": "Call KEGG REST ddi for one or more KEGG drug IDs and return interaction rows with table/network previews.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "entry_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 1,
                        "maxItems": MAX_GET_ENTRIES,
                        "description": "KEGG drug IDs, for example D00564 or D00109.",
                    },
                    "dbentries": {
                        "type": "string",
                        "description": "Alternative KEGG drug dbentries path segment, for example D00564+D00109.",
                    },
                    "target": {"type": "string", "description": "Optional second KEGG ddi path segment, usually another drug ID."},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": MAX_RESULTS, "default": DEFAULT_MAX_RESULTS},
                    "include_raw": {"type": "boolean", "default": False},
                },
                "anyOf": [{"required": ["entry_ids"]}, {"required": ["dbentries"]}],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_color_pathway_url",
            "title": "Build a colored KEGG pathway URL",
            "description": (
                "Generate an official KEGG show_pathway coloring URL from KEGG identifiers and color specs. "
                "Returns a front-end-compatible pathway record with a clickable colored-map action, "
                "the exact multi_query text, and a table preview of colored objects."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "map_id": {
                        "type": "string",
                        "description": "KEGG pathway map ID, for example map00010 or hsa04110.",
                    },
                    "items": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_COLOR_ITEMS,
                        "items": {
                            "type": "object",
                            "properties": {
                                "kegg_id": {
                                    "type": "string",
                                    "description": "KEGG identifier to color, for example hsa:7157, K00844, 3.1.3.9, C00031, G00001, or D00564.",
                                },
                                "color": {
                                    "type": "string",
                                    "description": "Optional raw KEGG color specification such as red, ,purple, skyblue,blue, or skyblue pink.",
                                },
                                "bgcolor": {
                                    "type": "string",
                                    "description": "Optional background color name or hex color such as red or #ff0000.",
                                },
                                "fgcolor": {
                                    "type": "string",
                                    "description": "Optional foreground color name or hex color such as black or #000000.",
                                },
                                "label": {"type": "string"},
                                "source_value": {"type": "string"},
                            },
                            "required": ["kegg_id"],
                            "additionalProperties": False,
                        },
                    },
                    "url_form": {
                        "type": "string",
                        "enum": COLOR_URL_FORMS,
                        "default": "query",
                        "description": "Official KEGG URL form: query uses map=&multi_query=; slash uses ?mapid/dataset/default=.",
                    },
                    "nocolor": {
                        "type": "boolean",
                        "default": False,
                        "description": "Use uncolored KEGG diagrams when supported by the query URL form.",
                    },
                    "default_bgcolor": {
                        "type": "string",
                        "description": "Optional default background color encoded for the slash URL form.",
                    },
                },
                "required": ["map_id", "items"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_color_pathway_from_table",
            "title": "Build a colored KEGG pathway URL from table rows",
            "description": (
                "Generate a colored KEGG pathway URL from analysis rows that already contain KEGG IDs, "
                "for example differential-expression rows with kegg_id, log2fc, and padj columns. "
                "This tool does not resolve gene symbols to KEGG IDs."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "map_id": {"type": "string", "description": "KEGG pathway map ID, for example hsa04110."},
                    "rows": {
                        "type": "array",
                        "minItems": 1,
                        "maxItems": MAX_COLOR_ITEMS,
                        "items": {
                            "type": "object",
                            "additionalProperties": True,
                        },
                        "description": "Rows containing at least a KEGG ID column and a numeric value column.",
                    },
                    "id_column": {"type": "string", "default": "kegg_id"},
                    "value_column": {"type": "string", "default": "log2fc"},
                    "pvalue_column": {"type": "string", "default": "padj"},
                    "label_column": {"type": "string", "description": "Optional label column copied into the preview table."},
                    "up_threshold": {"type": "number", "default": 1.0},
                    "down_threshold": {"type": "number", "default": -1.0},
                    "pvalue_threshold": {"type": "number", "minimum": 0.0, "maximum": 1.0, "default": 0.05},
                    "up_color": {"type": "string", "default": "#d73027"},
                    "down_color": {"type": "string", "default": "#4575b4"},
                    "neutral_color": {"type": "string", "default": "#d9d9d9"},
                    "fgcolor": {"type": "string", "default": "#000000"},
                    "include_neutral": {"type": "boolean", "default": False},
                    "url_form": {"type": "string", "enum": COLOR_URL_FORMS, "default": "query"},
                    "nocolor": {"type": "boolean", "default": False},
                    "default_bgcolor": {"type": "string"},
                },
                "required": ["map_id", "rows"],
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
        {
            "name": "kegg_status",
            "title": "Inspect KEGG MCP status",
            "description": "Return configured KEGG MCP capabilities and optional network health.",
            "inputSchema": {
                "type": "object",
                "properties": {"check_network": {"type": "boolean", "default": False}},
                "additionalProperties": False,
            },
            "annotations": read_only_annotations,
        },
    ]


TOOL_HANDLERS: dict[str, Callable[[JsonObject, KeggClient], JsonObject]] = {
    "kegg_parameter_domains": make_parameter_domains_handler("kegg", "kegg_parameter_domains", tool_definitions),
    "kegg_resolve_context": kegg_resolve_context,
    "kegg_info": kegg_info,
    "kegg_list": kegg_list,
    "kegg_find": kegg_find,
    "kegg_get": kegg_get,
    "kegg_conv": kegg_conv,
    "kegg_link": kegg_link,
    "kegg_ddi": kegg_ddi,
    "kegg_color_pathway_url": kegg_color_pathway_url_tool,
    "kegg_color_pathway_from_table": kegg_color_pathway_from_table,
    "kegg_status": kegg_status,
}
