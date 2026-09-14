"""Shared helpers for MCP dynamic context responses."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

JsonObject = dict[str, Any]


def build_dynamic_context_response(
    *,
    schema_version: str,
    context_schema_version: str,
    database: str,
    query: JsonObject,
    contexts: list[JsonObject],
    recommended_calls: list[JsonObject],
    max_results: int,
    fallback_source: JsonObject,
    sources: list[JsonObject],
    entity_groups: set[str] | None = None,
    raw: JsonObject | None = None,
    summary_fields: dict[str, Callable[[JsonObject], bool]] | None = None,
    extra_fields: JsonObject | None = None,
    include_raw: bool = False,
    prioritize_entities: bool = False,
    prioritize_same_server_calls: bool = False,
    dedupe_calls: bool = True,
    call_dedupe_include_server: bool = True,
) -> JsonObject:
    groups = entity_groups or set()
    ordered_contexts = prioritize_contexts(contexts, groups) if prioritize_entities and groups else list(contexts)
    selected_contexts = ordered_contexts[:max_results]
    prepared_calls = (
        dedupe_recommended_calls(
            recommended_calls,
            include_server=call_dedupe_include_server,
        )
        if dedupe_calls
        else list(recommended_calls)
    )
    if prioritize_same_server_calls:
        prepared_calls = prioritize_recommended_calls(prepared_calls)
    source = sources[0] if sources else fallback_source
    response: JsonObject = {
        "schema_version": schema_version,
        "context_schema_version": context_schema_version,
        "database": database,
        "operation": "resolve_context",
        "query": query,
        "returned": len(selected_contexts),
        "total": len(ordered_contexts),
        "contexts": selected_contexts,
        "entities": entity_summaries(ordered_contexts, groups, max_results) if groups else [],
        "recommended_calls": prepared_calls[:max_results],
        "source": source,
        "sources": sources,
        "provenance": source,
    }
    for field_name, predicate in (summary_fields or {}).items():
        response[field_name] = [
            context_summary(context)
            for context in selected_contexts
            if predicate(context)
        ]
    if extra_fields:
        response.update(extra_fields)
    if include_raw:
        response["raw"] = raw or {}
    return response


def dedupe_recommended_calls(calls: list[JsonObject], *, include_server: bool = True) -> list[JsonObject]:
    seen: set[str] = set()
    result: list[JsonObject] = []
    for call in calls:
        server_prefix = f"{call.get('server', '')}:" if include_server else ""
        key = f"{server_prefix}{call.get('tool_name')}:{call.get('arguments')}"
        if key in seen:
            continue
        seen.add(key)
        result.append(call)
    return result


def prioritize_recommended_calls(calls: list[JsonObject]) -> list[JsonObject]:
    return sorted(calls, key=lambda call: 1 if call.get("server") else 0)


def prioritize_contexts(contexts: list[JsonObject], entity_groups: set[str]) -> list[JsonObject]:
    return sorted(
        contexts,
        key=lambda context: (
            0 if is_entity_context(context, entity_groups) else 1,
            0 if context.get("url") else 1,
        ),
    )


def is_entity_context(context: JsonObject, entity_groups: set[str]) -> bool:
    return (
        context.get("group") in entity_groups
        and bool(context.get("url"))
        and not isinstance(context.get("value"), bool)
    )


def entity_summaries(contexts: list[JsonObject], entity_groups: set[str], limit: int) -> list[JsonObject]:
    return [context_summary(context) for context in contexts if is_entity_context(context, entity_groups)][:limit]


def context_summary(context: JsonObject) -> JsonObject:
    return {
        "parameter_name": context.get("parameter_name"),
        "value": context.get("value"),
        "label": context.get("label"),
        "kind": context.get("kind"),
        "url": context.get("url"),
        "metadata": context.get("metadata", {}),
    }
