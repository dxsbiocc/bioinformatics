"""Front-end compatible record envelopes for KEGG REST results."""

from __future__ import annotations

import urllib.parse
from typing import Any

from .constants import KEGG_REST_BASE_URL, KEGG_WEBSITE_BASE_URL, RECORD_SCHEMA_VERSION, JsonObject
from .utils import normalize_space, unique_texts


def kegg_info_record(
    database: str,
    text: str,
    *,
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    summary = parse_info_text(text)
    database = normalize_space(database)
    title = summary.get("title") or f"KEGG {database}"
    url = kegg_database_url(database, website_base_url)
    links = compact_links(
        ("KEGG database", url, "external", True),
        ("KEGG REST", api_url, "external", False),
    )
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "database.catalog",
        "record_type": "kegg_database",
        "database": "kegg",
        "id": database,
        "stable_id": f"KEGG_DB:{database}",
        "label": database,
        "title": title,
        "description": summary.get("description") or "KEGG database information",
        "url": url,
        "icon": "kegg",
        "identifiers": {
            "kegg_database": {
                "namespace": "kegg.database",
                "id": database,
                "label": database,
                "url": url,
            }
        },
        "links": links,
        "display": base_display(
            component="database",
            chip_label=database,
            title=title,
            subtitle=summary.get("description", ""),
            description=summary.get("description", ""),
            metadata=compact_fields(
                ("Database", database),
                ("Release", summary.get("release", "")),
                ("Entries", summary.get("entries", "")),
            ),
            badges=compact_badges(("KEGG", "source"), (database, "database")),
            links=links,
            hover_fields=compact_fields(
                ("Database", database),
                ("Release", summary.get("release", "")),
                ("Entries", summary.get("entries", "")),
                ("URL", url),
            ),
            url=url,
            previews=[text_preview("KEGG info", text, links)],
        ),
        "data": {
            "database": database,
            "summary": summary,
            "text": text,
            "url": url,
            "api_url": api_url,
        },
    }


def kegg_tsv_record(
    row: JsonObject,
    *,
    operation: str,
    database: str = "",
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    entry_id = normalize_space(row.get("entry_id")) or normalize_space(row.get("source"))
    target = normalize_space(row.get("target"))
    description = normalize_space(row.get("description"))
    code = normalize_space(row.get("code"))
    lineage = normalize_space(row.get("lineage"))
    title = description or target or entry_id
    url = kegg_entry_url(entry_id, website_base_url)
    record_type = kegg_record_type(entry_id, database=database)
    component = component_for_record_type(record_type)
    links = compact_links(
        ("KEGG entry", url, "external", True),
        ("KEGG REST", api_url, "external", False),
    )
    normalized = {
        "entry_id": entry_id,
        "target": target,
        "description": description,
        "code": code,
        "lineage": lineage,
        "columns": row.get("columns") if isinstance(row.get("columns"), list) else [],
        "operation": operation,
        "database_name": database,
        "url": url,
        "api_url": api_url,
    }
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": type_for_component(component),
        "record_type": record_type,
        "database": "kegg",
        "id": entry_id or target or title,
        "stable_id": stable_id(entry_id or target),
        "label": entry_id or target or title,
        "title": title,
        "description": description or lineage or "KEGG tabular result",
        "url": url,
        "icon": "kegg",
        "identifiers": kegg_identifiers(entry_id, url),
        "links": links,
        "display": base_display(
            component=component,
            chip_label=entry_id or code or target or title,
            title=title,
            subtitle=tsv_subtitle(normalized),
            description=description or lineage,
            metadata=compact_fields(
                ("Entry", entry_id),
                ("Target", target),
                ("Code", code),
                ("Database", database),
                ("Operation", operation),
            ),
            badges=compact_badges(("KEGG", "source"), (entry_id, "identifier"), (database, "database")),
            links=links,
            hover_fields=compact_fields(
                ("Entry", entry_id),
                ("Description", description),
                ("Code", code),
                ("Lineage", lineage),
                ("URL", url),
            ),
            url=url,
            sections=[table_section("kegg_row", "KEGG row", [normalized])],
            previews=[table_preview("KEGG result row", [normalized], links), xref_preview(entry_id, [])],
        ),
        "data": normalized,
    }


def kegg_entry_record(
    entry: JsonObject,
    *,
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    entry_id = normalize_space(entry.get("entry_id"))
    name = normalize_space(entry.get("name"))
    description = normalize_space(entry.get("description") or entry.get("definition"))
    title = name or description or entry_id
    url = kegg_entry_url(entry_id, website_base_url)
    record_type = kegg_record_type(entry_id, entry=entry)
    component = component_for_record_type(record_type)
    links = entry_links(entry, url, api_url)
    normalized = dict(entry)
    normalized.update({"url": url, "api_url": api_url})
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": type_for_component(component),
        "record_type": record_type,
        "database": "kegg",
        "id": entry_id,
        "stable_id": stable_id(entry_id),
        "label": entry_id,
        "title": title,
        "description": description or "KEGG entry",
        "url": url,
        "icon": "kegg",
        "identifiers": kegg_identifiers(entry_id, url),
        "links": links,
        "display": base_display(
            component=component,
            chip_label=entry_id,
            title=title,
            subtitle=entry_subtitle(normalized),
            description=description,
            metadata=entry_metadata(normalized),
            badges=compact_badges(
                ("KEGG", "source"),
                (entry_id, "identifier"),
                (normalize_space(entry.get("entry_class")), "record_type"),
            ),
            links=links,
            hover_fields=compact_fields(
                ("Entry", entry_id),
                ("Name", name),
                ("Description", description),
                ("Organism", normalize_space(entry.get("organism"))),
                ("Pathways", len(entry.get("pathways", [])) if isinstance(entry.get("pathways"), list) else ""),
                ("DB links", len(entry.get("dblinks", [])) if isinstance(entry.get("dblinks"), list) else ""),
                ("URL", url),
            ),
            url=url,
            sections=entry_sections(normalized),
            previews=entry_previews(normalized, links),
        ),
        "related": {
            "pathways": entry.get("pathways", []),
            "modules": entry.get("module", []),
            "orthology": entry.get("orthology", []),
            "dblinks": entry.get("dblinks", []),
            "genes": entry.get("genes", []),
            "compounds": entry.get("compounds", []),
            "reactions": entry.get("reactions", []),
        },
        "data": normalized,
    }


def kegg_sequence_record(
    sequence: JsonObject,
    *,
    alphabet: str,
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    entry_id = normalize_space(sequence.get("entry_id"))
    header = normalize_space(sequence.get("header"))
    seq = normalize_space(sequence.get("sequence"))
    title = header or entry_id
    url = kegg_entry_url(entry_id, website_base_url)
    links = compact_links(
        ("KEGG entry", url, "external", True),
        ("KEGG REST", api_url, "external", False),
    )
    normalized = {
        "entry_id": entry_id,
        "header": header,
        "description": normalize_space(sequence.get("description")),
        "sequence": seq,
        "alphabet": alphabet,
        "length": len(seq),
        "url": url,
        "api_url": api_url,
    }
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "biological.sequence",
        "record_type": "kegg_sequence",
        "database": "kegg",
        "id": entry_id,
        "stable_id": stable_id(entry_id),
        "label": entry_id,
        "title": title,
        "description": normalize_space(sequence.get("description")) or f"{alphabet} sequence",
        "url": url,
        "icon": "kegg",
        "identifiers": kegg_identifiers(entry_id, url),
        "links": links,
        "display": base_display(
            component="protein" if alphabet == "protein" else "genomic_feature",
            chip_label=entry_id,
            title=title,
            subtitle=f"{alphabet} sequence | {len(seq)} residues" if alphabet == "protein" else f"{alphabet} sequence | {len(seq)} bases",
            description=normalize_space(sequence.get("description")),
            metadata=compact_fields(
                ("Entry", entry_id),
                ("Alphabet", alphabet),
                ("Length", len(seq)),
            ),
            badges=compact_badges(("KEGG", "source"), (entry_id, "identifier"), (alphabet, "sequence")),
            links=links,
            hover_fields=compact_fields(
                ("Entry", entry_id),
                ("Header", header),
                ("Length", len(seq)),
                ("URL", url),
            ),
            url=url,
            previews=[
                {
                    "kind": "sequence",
                    "title": "Sequence",
                    "provider": "KEGG",
                    "id": entry_id,
                    "format": "fasta",
                    "length": len(seq),
                    "actions": display_actions(links),
                    "data": {"alphabet": alphabet, "sequence": seq, "header": header},
                }
            ],
        ),
        "data": normalized,
    }


def kegg_download_record(
    entry_id: str,
    *,
    option: str,
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    entry_id = normalize_space(entry_id)
    url = kegg_entry_url(entry_id, website_base_url)
    title = f"{entry_id} {option}"
    links = compact_links(
        ("KEGG entry", url, "external", True),
        (f"Download {option}", api_url, "download", False),
    )
    normalized = {
        "entry_id": entry_id,
        "option": option,
        "url": url,
        "api_url": api_url,
        "download_links": [{"label": option, "url": api_url, "format": option}],
    }
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "dataset",
        "record_type": "kegg_download_resource",
        "database": "kegg",
        "id": f"{entry_id}:{option}",
        "stable_id": f"{stable_id(entry_id)}:{option}",
        "label": entry_id,
        "title": title,
        "description": f"KEGG {option} resource",
        "url": api_url or url,
        "icon": "kegg",
        "identifiers": kegg_identifiers(entry_id, url),
        "links": links,
        "display": base_display(
            component="dataset",
            chip_label=entry_id,
            title=title,
            subtitle=f"KEGG {option} resource",
            description=f"Download or preview the KEGG {option} resource.",
            metadata=compact_fields(("Entry", entry_id), ("Format", option)),
            badges=compact_badges(("KEGG", "source"), (entry_id, "identifier"), (option, "format")),
            links=links,
            hover_fields=compact_fields(("Entry", entry_id), ("Format", option), ("URL", api_url or url)),
            url=api_url or url,
            previews=[
                {
                    "kind": "download_manifest",
                    "title": "KEGG resource",
                    "provider": "KEGG",
                    "id": entry_id,
                    "actions": display_actions(links),
                    "data": {"links": normalized["download_links"]},
                }
            ],
        ),
        "data": normalized,
    }


def kegg_conversion_record(
    rows: list[JsonObject],
    *,
    target_db: str,
    source_db_or_entries: str,
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    title = f"KEGG conversion: {source_db_or_entries} to {target_db}"
    url = kegg_database_url(target_db, website_base_url)
    links = compact_links(
        ("KEGG target database", url, "external", True),
        ("KEGG REST", api_url, "external", False),
    )
    normalized = {
        "target_db": target_db,
        "source": source_db_or_entries,
        "rows": rows,
        "url": url,
        "api_url": api_url,
    }
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "identifier.mapping",
        "record_type": "kegg_identifier_conversion",
        "database": "kegg",
        "id": f"{source_db_or_entries}->{target_db}",
        "stable_id": f"KEGG_CONV:{source_db_or_entries}:{target_db}",
        "label": f"{source_db_or_entries} -> {target_db}",
        "title": title,
        "description": f"{len(rows)} identifier conversion rows",
        "url": url,
        "icon": "kegg",
        "identifiers": {
            "kegg_conversion": {
                "namespace": "kegg.conversion",
                "id": f"{source_db_or_entries}->{target_db}",
                "label": f"{source_db_or_entries} -> {target_db}",
                "url": url,
            }
        },
        "links": links,
        "display": base_display(
            component="identifier_conversion",
            chip_label=f"{source_db_or_entries} -> {target_db}",
            title=title,
            subtitle=f"{len(rows)} rows",
            description="Identifier conversion rows returned by KEGG conv.",
            metadata=compact_fields(("Source", source_db_or_entries), ("Target", target_db), ("Rows", len(rows))),
            badges=compact_badges(("KEGG", "source"), ("conv", "operation"), (target_db, "target")),
            links=links,
            hover_fields=compact_fields(("Source", source_db_or_entries), ("Target", target_db), ("Rows", len(rows))),
            url=url,
            sections=[table_section("conversion_rows", "Conversion rows", rows)],
            previews=[table_preview("Conversion table", rows, links)],
        ),
        "data": normalized,
    }


def kegg_linkset_record(
    rows: list[JsonObject],
    *,
    target_db: str,
    source_db_or_entries: str,
    operation: str,
    option: str = "",
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    api_url: str = "",
) -> JsonObject:
    title = f"KEGG {operation}: {source_db_or_entries} to {target_db}"
    url = kegg_database_url(target_db, website_base_url)
    links = compact_links(
        ("KEGG target database", url, "external", True),
        ("KEGG REST", api_url, "external", False),
    )
    normalized = {
        "target_db": target_db,
        "source": source_db_or_entries,
        "operation": operation,
        "option": option,
        "rows": rows,
        "nodes": network_nodes(rows),
        "edges": network_edges(rows),
        "url": url,
        "api_url": api_url,
    }
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "database.links",
        "record_type": "kegg_linkset",
        "database": "kegg",
        "id": f"{operation}:{source_db_or_entries}->{target_db}",
        "stable_id": f"KEGG_LINK:{operation}:{source_db_or_entries}:{target_db}",
        "label": f"{source_db_or_entries} -> {target_db}",
        "title": title,
        "description": f"{len(rows)} KEGG relationship rows",
        "url": url,
        "icon": "kegg",
        "identifiers": {
            "kegg_linkset": {
                "namespace": f"kegg.{operation}",
                "id": f"{source_db_or_entries}->{target_db}",
                "label": f"{source_db_or_entries} -> {target_db}",
                "url": url,
            }
        },
        "links": links,
        "display": base_display(
            component="linkset",
            chip_label=f"{source_db_or_entries} -> {target_db}",
            title=title,
            subtitle=f"{len(rows)} relationships",
            description=f"KEGG {operation} relationships.",
            metadata=compact_fields(("Source", source_db_or_entries), ("Target", target_db), ("Rows", len(rows)), ("Option", option)),
            badges=compact_badges(("KEGG", "source"), (operation, "operation"), (target_db, "target")),
            links=links,
            hover_fields=compact_fields(("Source", source_db_or_entries), ("Target", target_db), ("Rows", len(rows)), ("Option", option)),
            url=url,
            sections=[table_section("link_rows", "Link rows", rows)],
            previews=[
                table_preview("Link table", rows, links),
                {
                    "kind": "network",
                    "title": "Relationship network",
                    "provider": "KEGG",
                    "actions": display_actions(links),
                    "data": {"nodes": normalized["nodes"], "edges": normalized["edges"]},
                },
            ],
        ),
        "data": normalized,
    }


def kegg_colored_pathway_record(
    map_id: str,
    items: list[JsonObject],
    *,
    website_base_url: str = KEGG_WEBSITE_BASE_URL,
    url_form: str = "query",
    nocolor: bool = False,
    default_bgcolor: str = "",
    generated_from: str = "items",
    warnings: list[str] | None = None,
) -> JsonObject:
    map_id = normalize_space(map_id)
    normalized_items = normalize_color_items(items)
    multi_query = color_multi_query(normalized_items)
    url = kegg_color_pathway_url(
        map_id,
        normalized_items,
        website_base_url=website_base_url,
        url_form=url_form,
        nocolor=nocolor,
        default_bgcolor=default_bgcolor,
    )
    pathway_url = kegg_entry_url(f"path:{map_id}", website_base_url)
    links = compact_links(
        ("Open colored KEGG map", url, "external", True),
        ("KEGG pathway", pathway_url, "external", False),
        ("Map coloring URL docs", f"{website_base_url.rstrip('/')}/kegg/webapp/color_url.html", "external", False),
    )
    title = f"Colored KEGG pathway {map_id}"
    normalized = {
        "map_id": map_id,
        "items": normalized_items,
        "item_count": len(normalized_items),
        "multi_query": multi_query,
        "url": url,
        "pathway_url": pathway_url,
        "url_form": url_form,
        "nocolor": nocolor,
        "default_bgcolor": normalize_space(default_bgcolor),
        "generated_from": generated_from,
        "warnings": warnings or [],
    }
    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "pathway.annotation",
        "record_type": "kegg_colored_pathway",
        "database": "kegg",
        "id": map_id,
        "stable_id": f"KEGG_COLOR:{map_id}",
        "label": map_id,
        "title": title,
        "description": f"{len(normalized_items)} KEGG identifiers prepared for pathway coloring",
        "url": url,
        "icon": "kegg",
        "identifiers": {
            "kegg_pathway": {
                "namespace": "kegg.pathway",
                "id": map_id,
                "label": map_id,
                "url": pathway_url,
            }
        },
        "links": links,
        "display": base_display(
            component="pathway",
            chip_label=map_id,
            title=title,
            subtitle=f"{len(normalized_items)} colored identifiers",
            description="Open this URL in a browser to view the KEGG pathway with the supplied gene, KO, EC, compound, glycan, or drug coloring.",
            metadata=compact_fields(
                ("Map", map_id),
                ("Items", len(normalized_items)),
                ("URL form", url_form),
                ("Use uncolored diagram", nocolor),
                ("Default background", default_bgcolor),
                ("Generated from", generated_from),
            ),
            badges=compact_badges(("KEGG", "source"), (map_id, "pathway"), ("colored", "annotation")),
            links=links,
            hover_fields=compact_fields(
                ("Map", map_id),
                ("Items", len(normalized_items)),
                ("URL form", url_form),
                ("Use uncolored diagram", nocolor),
                ("URL", url),
            ),
            url=url,
            sections=[
                table_section("color_items", "Colored identifiers", normalized_items),
                {"key": "multi_query", "title": "KEGG multi_query", "kind": "text", "text": multi_query},
            ],
            previews=[
                table_preview("Colored identifiers", normalized_items, links),
                text_preview("KEGG multi_query", multi_query, links),
            ],
        ),
        "related": {"items": normalized_items, "warnings": warnings or []},
        "data": normalized,
    }


def normalize_color_items(items: list[JsonObject]) -> list[JsonObject]:
    normalized: list[JsonObject] = []
    for item in items:
        kegg_id = normalize_space(item.get("kegg_id") or item.get("id"))
        color = normalize_space(item.get("color"))
        bgcolor = normalize_space(item.get("bgcolor"))
        fgcolor = normalize_space(item.get("fgcolor"))
        normalized_item = {
            "kegg_id": kegg_id,
            "color": color,
            "bgcolor": bgcolor,
            "fgcolor": fgcolor,
            "label": normalize_space(item.get("label")),
            "source_value": normalize_space(item.get("source_value")),
        }
        for key in ["direction", "pvalue"]:
            value = item.get(key)
            if value not in {None, ""}:
                normalized_item[key] = value
        normalized.append(normalized_item)
    return normalized


def color_multi_query(items: list[JsonObject]) -> str:
    lines = []
    for item in items:
        kegg_id = normalize_space(item.get("kegg_id"))
        color = normalize_space(item.get("color"))
        if not kegg_id:
            continue
        lines.append(f"{kegg_id} {color}".rstrip())
    return "\n".join(lines)


def kegg_color_pathway_url(
    map_id: str,
    items: list[JsonObject],
    *,
    website_base_url: str,
    url_form: str,
    nocolor: bool,
    default_bgcolor: str,
) -> str:
    cgi = f"{website_base_url.rstrip('/')}/kegg-bin/show_pathway"
    if url_form == "slash":
        path_segments = [urllib.parse.quote(map_id, safe="")]
        for item in items:
            kegg_id = normalize_space(item.get("kegg_id"))
            color = normalize_space(item.get("color"))
            line = f"{kegg_id}\t{color}".rstrip()
            path_segments.append(urllib.parse.quote(line, safe=""))
        if default_bgcolor:
            path_segments.append(urllib.parse.quote(f"default={default_bgcolor}", safe=""))
        return f"{cgi}?{'/'.join(path_segments)}"

    query = {
        "map": map_id,
        "multi_query": color_multi_query(items),
    }
    if nocolor:
        query["nocolor"] = "1"
    encoded = "&".join(
        f"{urllib.parse.quote(key, safe='')}={urllib.parse.quote(value, safe='')}"
        for key, value in query.items()
    )
    return f"{cgi}?{encoded}"


def base_display(
    *,
    component: str,
    chip_label: str,
    title: str,
    subtitle: str = "",
    description: str = "",
    metadata: list[JsonObject],
    badges: list[JsonObject],
    links: list[JsonObject],
    hover_fields: list[JsonObject],
    url: str,
    sections: list[JsonObject] | None = None,
    previews: list[JsonObject] | None = None,
) -> JsonObject:
    display: JsonObject = {
        "component": component,
        "chip_label": chip_label or title,
        "icon": "kegg",
        "title": title,
        "subtitle": subtitle,
        "description": description,
        "metadata": metadata,
        "badges": badges,
        "actions": display_actions(links),
        "hover": {"title": title, "subtitle": subtitle, "icon": "kegg", "fields": hover_fields},
        "primary_url": url,
        "previews": previews or [],
    }
    if sections:
        display["sections"] = sections
    return display


def entry_metadata(entry: JsonObject) -> list[JsonObject]:
    return compact_fields(
        ("Entry", entry.get("entry_id")),
        ("Name", entry.get("name")),
        ("Class", entry.get("entry_class")),
        ("Organism", entry.get("organism")),
        ("Pathways", len(entry.get("pathways", [])) if isinstance(entry.get("pathways"), list) else ""),
        ("DB links", len(entry.get("dblinks", [])) if isinstance(entry.get("dblinks"), list) else ""),
    )


def entry_sections(entry: JsonObject) -> list[JsonObject]:
    sections = [
        {
            "key": "summary",
            "title": "Summary",
            "fields": compact_fields(
                ("Entry", entry.get("entry_id")),
                ("Name", entry.get("name")),
                ("Description", entry.get("description")),
                ("Definition", entry.get("definition")),
                ("Organism", entry.get("organism")),
            ),
        }
    ]
    for key, title in [
        ("pathways", "Pathways"),
        ("module", "Modules"),
        ("orthology", "Orthology"),
        ("genes", "Genes"),
        ("compounds", "Compounds"),
        ("reactions", "Reactions"),
    ]:
        rows = entry.get(key)
        if isinstance(rows, list) and rows:
            sections.append(table_section(key, title, rows))
    raw_text = normalize_space(entry.get("raw_text"))
    if raw_text:
        sections.append({"key": "raw_text", "title": "KEGG flat file", "kind": "text", "text": raw_text})
    return sections


def entry_previews(entry: JsonObject, links: list[JsonObject]) -> list[JsonObject]:
    previews = [
        table_preview("Entry summary", [entry_summary_row(entry)], links),
        xref_preview(normalize_space(entry.get("entry_id")), entry.get("dblinks", [])),
    ]
    record_type = kegg_record_type(normalize_space(entry.get("entry_id")), entry=entry)
    if record_type in {"kegg_compound", "kegg_drug", "kegg_glycan"}:
        entry_id = normalize_space(entry.get("entry_id"))
        previews.insert(
            0,
            {
                "kind": "chemical_structure",
                "title": "Chemical structure",
                "provider": "KEGG",
                "id": entry_id,
                "url": f"{KEGG_REST_BASE_URL}/get/{urllib.parse.quote(entry_id, safe=':._-')}/image",
                "actions": display_actions(links),
                "data": {"image_url": f"{KEGG_REST_BASE_URL}/get/{urllib.parse.quote(entry_id, safe=':._-')}/image"},
            },
        )
    if record_type == "kegg_pathway":
        rows = entry.get("genes") if isinstance(entry.get("genes"), list) else []
        previews.append(table_preview("Pathway genes", rows, links))
    raw_text = normalize_space(entry.get("raw_text"))
    if raw_text:
        previews.append(text_preview("KEGG flat file", raw_text, links))
    return [preview for preview in previews if preview]


def entry_summary_row(entry: JsonObject) -> JsonObject:
    return {
        "entry_id": entry.get("entry_id"),
        "name": entry.get("name"),
        "description": entry.get("description"),
        "definition": entry.get("definition"),
        "organism": entry.get("organism"),
    }


def entry_links(entry: JsonObject, url: str, api_url: str) -> list[JsonObject]:
    entry_id = normalize_space(entry.get("entry_id"))
    links = compact_links(
        ("KEGG entry", url, "external", True),
        ("KEGG REST", api_url, "external", False),
    )
    if entry_id:
        links.extend(
            compact_links(
                ("KEGG image", f"{KEGG_REST_BASE_URL}/get/{urllib.parse.quote(entry_id, safe=':._-')}/image", "external", False),
                ("KEGG JSON", f"{KEGG_REST_BASE_URL}/get/{urllib.parse.quote(entry_id, safe=':._-')}/json", "external", False),
            )
        )
    return links


def parse_info_text(text: str) -> JsonObject:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else ""
    release = ""
    entries = ""
    for line in lines:
        lowered = line.lower()
        if "release" in lowered:
            release = line
        if "entries" in lowered:
            entries = line
    return {
        "title": title,
        "description": lines[1] if len(lines) > 1 else "",
        "release": release,
        "entries": entries,
    }


def kegg_record_type(entry_id: str, *, database: str = "", entry: JsonObject | None = None) -> str:
    entry_id = normalize_space(entry_id)
    database = normalize_space(database).lower()
    entry_class = normalize_space((entry or {}).get("entry_class")).lower()
    if entry_id.startswith(("path:", "map", "ko", "hsa")) and ("pathway" in entry_class or database == "pathway"):
        return "kegg_pathway"
    prefix = entry_id.split(":", 1)[0].lower() if ":" in entry_id else database
    if prefix in {"cpd", "compound"} or entry_id.startswith("C"):
        return "kegg_compound"
    if prefix in {"dr", "drug"} or entry_id.startswith("D"):
        return "kegg_drug"
    if prefix in {"gl", "glycan"} or entry_id.startswith("G"):
        return "kegg_glycan"
    if prefix in {"hsa", "mmu", "rno", "sce", "eco", "ath", "dme"} or "gene" in entry_class:
        return "kegg_gene"
    if prefix in {"ko", "orthology"} or "ko" in entry_class:
        return "kegg_orthology"
    if prefix in {"rn", "reaction"} or entry_id.startswith("R"):
        return "kegg_reaction"
    if prefix in {"ec", "enzyme"}:
        return "kegg_enzyme"
    if prefix in {"ds", "disease"}:
        return "kegg_disease"
    if database == "pathway":
        return "kegg_pathway"
    return "kegg_entry"


def component_for_record_type(record_type: str) -> str:
    if record_type == "kegg_pathway":
        return "pathway"
    if record_type == "kegg_gene":
        return "gene"
    if record_type in {"kegg_compound", "kegg_drug", "kegg_glycan"}:
        return "compound"
    if record_type in {"kegg_orthology", "kegg_enzyme"}:
        return "protein"
    return "dataset"


def type_for_component(component: str) -> str:
    return {
        "pathway": "pathway",
        "gene": "gene",
        "compound": "chemical.compound",
        "protein": "protein",
        "database": "database.catalog",
        "identifier_conversion": "identifier.mapping",
        "linkset": "database.links",
    }.get(component, "dataset")


def entry_subtitle(entry: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalize_space(entry.get("entry_id")),
            normalize_space(entry.get("entry_class")),
            normalize_space(entry.get("organism")),
        ]
        if part
    )


def tsv_subtitle(row: JsonObject) -> str:
    return " | ".join(
        part
        for part in [
            normalize_space(row.get("entry_id")),
            normalize_space(row.get("code")),
            normalize_space(row.get("database_name")),
        ]
        if part
    )


def kegg_identifiers(entry_id: str, url: str) -> JsonObject:
    entry_id = normalize_space(entry_id)
    return {
        "kegg": {
            "namespace": "kegg",
            "id": entry_id or "unknown",
            "label": entry_id or "KEGG",
            "url": url,
        }
    }


def stable_id(entry_id: str) -> str:
    entry_id = normalize_space(entry_id)
    return f"KEGG:{entry_id}" if entry_id else "KEGG:unknown"


def kegg_entry_url(entry_id: str, website_base_url: str) -> str:
    entry_id = normalize_space(entry_id)
    if not entry_id:
        return f"{website_base_url.rstrip('/')}/kegg/"
    return f"{website_base_url.rstrip('/')}/entry/{urllib.parse.quote(entry_id, safe=':._-')}"


def kegg_database_url(database: str, website_base_url: str) -> str:
    database = normalize_space(database)
    if database:
        return f"{website_base_url.rstrip('/')}/kegg-bin/show_database?{urllib.parse.quote(database, safe='._-')}"
    return f"{website_base_url.rstrip('/')}/kegg/"


def table_section(key: str, title: str, rows: list[JsonObject]) -> JsonObject:
    return {"key": key, "title": title, "kind": "table", "rows": rows[:100]}


def table_preview(title: str, rows: list[JsonObject], links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "table",
        "title": title,
        "provider": "KEGG",
        "actions": display_actions(links),
        "data": {"rows": rows[:100]},
    }


def xref_preview(entry_id: str, groups: Any) -> JsonObject:
    normalized_groups = groups if isinstance(groups, list) else []
    if not normalized_groups:
        normalized_groups = [{"database": "KEGG", "items": [{"id": entry_id, "label": entry_id}]}]
    return {
        "kind": "xref_groups",
        "title": "Cross references",
        "provider": "KEGG",
        "data": {"groups": normalized_groups},
    }


def text_preview(title: str, text: str, links: list[JsonObject]) -> JsonObject:
    return {
        "kind": "text",
        "title": title,
        "provider": "KEGG",
        "actions": display_actions(links),
        "data": {"text": text},
    }


def compact_fields(*pairs: tuple[str, Any]) -> list[JsonObject]:
    fields: list[JsonObject] = []
    for label, value in pairs:
        if value is None or value == "":
            continue
        if isinstance(value, (list, dict)):
            if not value:
                continue
            rendered: Any = len(value)
        else:
            rendered = value
        fields.append({"label": label, "value": rendered})
    return fields


def compact_badges(*pairs: tuple[str, str]) -> list[JsonObject]:
    return [
        {"label": normalize_space(label), "kind": kind}
        for label, kind in pairs
        if normalize_space(label)
    ]


def compact_links(*items: tuple[str, str, str, bool]) -> list[JsonObject]:
    links: list[JsonObject] = []
    seen: set[str] = set()
    for label, url, kind, primary in items:
        url = normalize_space(url)
        if not url or not url.lower().startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        links.append({"label": label, "url": url, "kind": kind, "primary": primary})
    return links


def display_actions(links: list[JsonObject]) -> list[JsonObject]:
    actions: list[JsonObject] = []
    for link in links:
        label = normalize_space(link.get("label"))
        url = normalize_space(link.get("url"))
        if not label or not url:
            continue
        action = {"label": label, "url": url, "kind": normalize_space(link.get("kind")) or "external"}
        if bool(link.get("primary")):
            action["primary"] = True
        actions.append(action)
    return actions


def network_nodes(rows: list[JsonObject]) -> list[JsonObject]:
    ids = unique_texts(
        [
            value
            for row in rows
            for value in [row.get("source"), row.get("target")]
            if normalize_space(value)
        ]
    )
    return [{"id": item, "label": item} for item in ids[:200]]


def network_edges(rows: list[JsonObject]) -> list[JsonObject]:
    edges: list[JsonObject] = []
    for index, row in enumerate(rows[:500]):
        source = normalize_space(row.get("source"))
        target = normalize_space(row.get("target"))
        if source and target:
            edges.append({"id": f"edge-{index + 1}", "source": source, "target": target})
    return edges
