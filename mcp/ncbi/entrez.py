"""Common Entrez tools shared across NCBI databases."""

from __future__ import annotations

import re
from typing import Any, Iterable

from .client import NcbiClient
from .constants import JsonObject
from .errors import McpError, NcbiError
from .records import ncbi_record_url, with_database_compat, with_entrez_links_compat
from .utils import normalize_space, optional_bool, optional_int, parse_count, source_info


def ncbi_db_info(args: JsonObject, client: NcbiClient) -> JsonObject:
    database = normalize_database(args.get("database", ""))
    include_fields = optional_bool(args, "include_fields", default=False)
    include_links = optional_bool(args, "include_links", default=True)
    include_hidden = optional_bool(args, "include_hidden", default=False)
    max_fields = optional_int(args, "max_fields", default=50, minimum=1, maximum=500)
    max_links = optional_int(args, "max_links", default=100, minimum=1, maximum=500)

    params: JsonObject = {"retmode": "json"}
    if database:
        params["db"] = database
    payload = client.request_json("einfo.fcgi", params)
    result = payload.get("einforesult")
    if not isinstance(result, dict):
        raise NcbiError("NCBI EInfo response is missing einforesult")

    if not database:
        databases = [
            str(name)
            for name in result.get("dblist", [])
            if normalize_space(name)
        ]
        return with_database_compat(
            {
                "database": "entrez",
                "databases": databases,
                "returned": len(databases),
                "source": source_info("einfo.fcgi", {"db": "entrez", **params}),
            }
        )

    dbinfo = result.get("dbinfo")
    if not isinstance(dbinfo, list) or not dbinfo:
        raise NcbiError(f"NCBI EInfo returned no dbinfo for {database}")
    info = normalize_db_info(
        dbinfo[0],
        include_fields=include_fields,
        include_links=include_links,
        include_hidden=include_hidden,
        max_fields=max_fields,
        max_links=max_links,
    )
    return with_database_compat(
        {
            "database": "entrez",
            "query": database,
            "database_info": info,
            "database_infos": [info],
            "source": source_info("einfo.fcgi", params),
        }
    )


def ncbi_link(args: JsonObject, client: NcbiClient) -> JsonObject:
    db_from = require_database(args, "db_from")
    db_to = normalize_database(args.get("db_to", ""))
    ids = coerce_entrez_ids(args.get("ids"))
    max_links = optional_int(args, "max_links", default=50, minimum=1, maximum=500)
    link_name = normalize_space(args.get("link_name"))

    params: JsonObject = {
        "dbfrom": db_from,
        "id": ",".join(ids),
        "retmode": "json",
    }
    if db_to:
        params["db"] = db_to
    if link_name:
        params["linkname"] = link_name

    payload = client.request_json("elink.fcgi", params)
    raw_linksets = payload.get("linksets")
    if not isinstance(raw_linksets, list):
        raise NcbiError("NCBI ELink response is missing linksets")

    linksets = [
        normalize_linkset(linkset, db_from=db_from, max_links=max_links)
        for linkset in raw_linksets
        if isinstance(linkset, dict)
    ]
    return with_entrez_links_compat(
        {
            "database": "entrez",
            "source_database": db_from,
            "target_database": db_to or None,
            "ids": ids,
            "returned": len(linksets),
            "linksets": linksets,
            "source": source_info("elink.fcgi", params),
        }
    )


def ncbi_related_records(args: JsonObject, client: NcbiClient) -> JsonObject:
    database = require_database(args, "database")
    ids = coerce_entrez_ids(args.get("ids"))
    target_databases = coerce_database_list(
        args.get("target_databases") or args.get("targets")
    )
    max_links = optional_int(args, "max_links", default=50, minimum=1, maximum=500)

    if not target_databases:
        response = ncbi_link(
            {
                "db_from": database,
                "ids": ids,
                "max_links": max_links,
            },
            client,
        )
        response["tool"] = "ncbi_related_records"
        return response

    linksets = []
    sources = []
    for target_database in target_databases:
        linked = ncbi_link(
            {
                "db_from": database,
                "db_to": target_database,
                "ids": ids,
                "max_links": max_links,
            },
            client,
        )
        linksets.extend(linked.get("linksets", []))
        sources.append(linked.get("source"))

    return with_entrez_links_compat(
        {
            "tool": "ncbi_related_records",
            "database": "entrez",
            "source_database": database,
            "target_databases": target_databases,
            "ids": ids,
            "returned": len(linksets),
            "linksets": linksets,
            "sources": sources,
            "source": source_info(
                "elink.fcgi",
                {
                    "db": ",".join(target_databases),
                    "dbfrom": database,
                    "id": ",".join(ids),
                    "retmode": "json",
                },
            ),
        }
    )


def normalize_db_info(
    info: JsonObject,
    *,
    include_fields: bool,
    include_links: bool,
    include_hidden: bool,
    max_fields: int,
    max_links: int,
) -> JsonObject:
    fieldlist = info.get("fieldlist") if isinstance(info.get("fieldlist"), list) else []
    linklist = info.get("linklist") if isinstance(info.get("linklist"), list) else []

    fields = []
    if include_fields:
        for field in fieldlist:
            if not isinstance(field, dict):
                continue
            if not include_hidden and normalize_space(field.get("ishidden")) == "Y":
                continue
            fields.append(
                {
                    "name": normalize_space(field.get("name")),
                    "full_name": normalize_space(field.get("fullname")),
                    "description": normalize_space(field.get("description")),
                    "term_count": parse_count(field.get("termcount")),
                    "is_date": normalize_space(field.get("isdate")) == "Y",
                    "is_numerical": normalize_space(field.get("isnumerical")) == "Y",
                }
            )
            if len(fields) >= max_fields:
                break

    links = []
    if include_links:
        for link in linklist:
            if not isinstance(link, dict):
                continue
            links.append(
                {
                    "name": normalize_space(link.get("name")),
                    "menu": normalize_space(link.get("menu")),
                    "description": normalize_space(link.get("description")),
                    "database_to": normalize_space(link.get("dbto")),
                }
            )
            if len(links) >= max_links:
                break

    return {
        "db_name": normalize_space(info.get("dbname")),
        "menu_name": normalize_space(info.get("menuname")),
        "description": normalize_space(info.get("description")),
        "build": normalize_space(info.get("dbbuild")),
        "count": parse_count(info.get("count")),
        "last_update": normalize_space(info.get("lastupdate")),
        "fields": fields,
        "links": links,
        "field_count": len(fieldlist),
        "link_count": len(linklist),
    }


def normalize_linkset(
    linkset: JsonObject,
    *,
    db_from: str,
    max_links: int,
) -> JsonObject:
    source_ids = [
        str(source_id)
        for source_id in linkset.get("ids", [])
        if normalize_space(source_id)
    ]
    source_id = source_ids[0] if source_ids else ""
    groups = []
    for group in linkset.get("linksetdbs", []):
        if not isinstance(group, dict):
            continue
        target_database = normalize_database(group.get("dbto", ""))
        target_ids = [
            str(target_id)
            for target_id in group.get("links", [])
            if normalize_space(target_id)
        ]
        shown_ids = target_ids[:max_links]
        groups.append(
            {
                "target_database": target_database,
                "link_name": normalize_space(group.get("linkname")),
                "menu": normalize_space(group.get("menu")),
                "count": len(target_ids),
                "returned": len(shown_ids),
                "target_ids": shown_ids,
                "truncated": len(target_ids) > len(shown_ids),
                "links": [
                    {
                        "label": f"{target_database}:{target_id}",
                        "url": ncbi_record_url(target_database, target_id),
                        "kind": "external",
                        "primary": index == 0,
                    }
                    for index, target_id in enumerate(shown_ids)
                ],
            }
        )
    return {
        "source_database": normalize_database(linkset.get("dbfrom", db_from)),
        "source_id": source_id,
        "source_ids": source_ids,
        "target_groups": groups,
    }


def require_database(args: JsonObject, name: str) -> str:
    database = normalize_database(args.get(name, ""))
    if not database:
        raise McpError(-32602, f"{name} is required")
    return database


def normalize_database(value: Any) -> str:
    database = normalize_space(value).lower()
    if not database:
        return ""
    if not re.fullmatch(r"[a-z0-9_]+", database):
        raise McpError(-32602, f"Invalid Entrez database: {database}")
    return database


def coerce_entrez_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_ids: Iterable[Any] = re.split(r"[\s,;]+", value.strip())
    elif isinstance(value, list):
        raw_ids = value
    else:
        raise McpError(-32602, "ids must be an ID string or an array of IDs")

    ids = []
    seen = set()
    for item in raw_ids:
        identifier = normalize_space(item)
        if not identifier:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", identifier):
            raise McpError(-32602, f"Invalid Entrez ID: {identifier}")
        if identifier not in seen:
            seen.add(identifier)
            ids.append(identifier)
    if not ids:
        raise McpError(-32602, "At least one ID is required")
    return ids


def coerce_database_list(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        raw_databases: Iterable[Any] = re.split(r"[\s,;]+", value.strip())
    elif isinstance(value, list):
        raw_databases = value
    else:
        raise McpError(
            -32602,
            "target_databases must be a database string or an array of databases",
        )

    databases = []
    seen = set()
    for item in raw_databases:
        database = normalize_database(item)
        if not database or database in seen:
            continue
        seen.add(database)
        databases.append(database)
    return databases
