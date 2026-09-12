"""PMC API tools."""

from __future__ import annotations

import re
from typing import Any, Iterable

from .client import NcbiClient
from .constants import JsonObject
from .errors import McpError
from .records import with_pmc_id_compat
from .utils import normalize_space, optional_bool, source_info


PMC_ID_CONVERTER_URL = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"


def pmc_id_convert(args: JsonObject, client: NcbiClient) -> JsonObject:
    ids = coerce_pmc_ids(args.get("ids"))
    versions = optional_bool(args, "versions", default=False)
    show_aiid = optional_bool(args, "show_aiid", default=False)
    id_type = normalize_space(args.get("id_type")).lower()

    params: JsonObject = {
        "ids": ",".join(ids),
        "format": "json",
    }
    if versions:
        params["versions"] = "yes"
    if show_aiid:
        params["showaiid"] = "yes"
    if id_type:
        params["idtype"] = id_type

    payload = client.request_url_json(
        PMC_ID_CONVERTER_URL,
        params,
        label="pmc-id-converter",
    )
    records = payload.get("records", [])
    conversions = [
        normalize_pmc_conversion(record)
        for record in records
        if isinstance(record, dict)
    ]
    return with_pmc_id_compat(
        {
            "database": "pmc",
            "ids": ids,
            "returned": len(conversions),
            "conversions": conversions,
            "status": normalize_space(payload.get("status")),
            "response_date": normalize_space(payload.get("response-date")),
            "source": source_info("idconv", {"db": "pmc", **params}),
        }
    )


def normalize_pmc_conversion(record: JsonObject) -> JsonObject:
    manuscript_id = (
        normalize_space(record.get("mid"))
        or normalize_space(record.get("nihmsid"))
        or normalize_space(record.get("manuscript-id"))
    )
    return {
        "requested_id": normalize_space(record.get("requested-id")),
        "status": normalize_space(record.get("status")) or "ok",
        "error": normalize_space(record.get("errmsg")),
        "pmid": normalize_space(record.get("pmid")),
        "pmcid": normalize_space(record.get("pmcid")),
        "doi": normalize_space(record.get("doi")),
        "manuscript_id": manuscript_id,
        "versions": record.get("versions", []),
        "raw_status": normalize_space(record.get("status")),
    }


def coerce_pmc_ids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_ids: Iterable[Any] = re.split(r"[\s,;]+", value.strip())
    elif isinstance(value, list):
        raw_ids = value
    else:
        raise McpError(-32602, "ids must be an identifier string or an array")

    ids = []
    seen = set()
    for item in raw_ids:
        identifier = normalize_space(item)
        if not identifier:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.:/()-]+", identifier):
            raise McpError(-32602, f"Invalid identifier: {identifier}")
        if identifier not in seen:
            seen.add(identifier)
            ids.append(identifier)
    if not ids:
        raise McpError(-32602, "At least one identifier is required")
    if len(ids) > 200:
        raise McpError(-32602, "At most 200 identifiers may be requested")
    return ids
