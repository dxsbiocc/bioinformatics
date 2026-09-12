"""PubMed tools and XML/JSON normalizers."""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any, Iterable

from .client import NcbiClient
from .constants import MAX_PUBMED_IDS, JsonObject
from .errors import McpError, NcbiError
from .schemas import with_pubmed_compat
from .utils import (
    element_text,
    normalize_space,
    optional_bool,
    optional_int,
    parse_count,
    require_date_like,
    require_non_empty_string,
    source_info,
    text_from_child,
)


def pubmed_search(args: JsonObject, client: NcbiClient) -> JsonObject:
    query = require_non_empty_string(args, "query")
    max_results = optional_int(args, "max_results", default=10, minimum=1, maximum=100)
    sort = normalize_pubmed_sort(args.get("sort", "relevance"))
    include_summaries = optional_bool(args, "include_summaries", default=True)

    params: JsonObject = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": max_results,
        "sort": sort,
    }
    add_pubmed_date_params(args, params)

    payload = client.request_json("esearch.fcgi", params)
    result = payload.get("esearchresult")
    if not isinstance(result, dict):
        raise NcbiError("PubMed search response is missing esearchresult")

    ids = [str(pmid) for pmid in result.get("idlist", [])]
    response: JsonObject = {
        "database": "pubmed",
        "query": query,
        "translated_query": result.get("querytranslation"),
        "count": parse_count(result.get("count")),
        "returned": len(ids),
        "pmids": ids,
        "source": source_info("esearch.fcgi", params),
    }
    if include_summaries and ids:
        response["articles"] = pubmed_summaries_for_ids(ids, client)["articles"]
    return with_pubmed_compat(response, ids=ids)


def pubmed_summaries(args: JsonObject, client: NcbiClient) -> JsonObject:
    ids = coerce_pmids(args.get("ids"))
    include_raw = optional_bool(args, "include_raw", default=False)
    return pubmed_summaries_for_ids(ids, client, include_raw=include_raw)


def pubmed_summaries_for_ids(
    ids: list[str],
    client: NcbiClient,
    *,
    include_raw: bool = False,
) -> JsonObject:
    if not ids:
        return with_pubmed_compat({
            "database": "pubmed",
            "pmids": [],
            "articles": [],
            "source": source_info("esummary.fcgi", {"db": "pubmed", "id": ""}),
        })

    params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "json",
    }
    payload = client.request_json("esummary.fcgi", params)
    result = payload.get("result")
    if not isinstance(result, dict):
        raise NcbiError("PubMed summary response is missing result")

    uids = result.get("uids", ids)
    articles = []
    for uid in uids:
        record = result.get(str(uid))
        if not isinstance(record, dict):
            continue
        normalized = normalize_pubmed_summary(record)
        if include_raw:
            normalized["raw"] = record
        articles.append(normalized)

    return with_pubmed_compat({
        "database": "pubmed",
        "pmids": ids,
        "returned": len(articles),
        "articles": articles,
        "source": source_info("esummary.fcgi", params),
    }, ids=ids)


def pubmed_articles(args: JsonObject, client: NcbiClient) -> JsonObject:
    ids = coerce_pmids(args.get("ids"))
    include_xml = optional_bool(args, "include_xml", default=False)
    params = {
        "db": "pubmed",
        "id": ",".join(ids),
        "retmode": "xml",
    }
    xml_text = client.request_text("efetch.fcgi", params)
    articles = parse_pubmed_xml(xml_text)
    response: JsonObject = {
        "database": "pubmed",
        "pmids": ids,
        "returned": len(articles),
        "articles": articles,
        "source": source_info("efetch.fcgi", params),
    }
    response = with_pubmed_compat(response, ids=ids)
    if include_xml:
        response["xml"] = xml_text
    return response


def pubmed_fetch(args: JsonObject, client: NcbiClient) -> JsonObject:
    ids = coerce_pmids(args.get("ids"))
    output_format = str(args.get("format", "abstract")).strip().lower()
    if output_format not in {"abstract", "medline", "xml"}:
        raise McpError(
            -32602,
            "format must be one of: abstract, medline, xml",
        )

    params: JsonObject = {
        "db": "pubmed",
        "id": ",".join(ids),
    }
    if output_format == "xml":
        params["retmode"] = "xml"
    elif output_format == "medline":
        params["rettype"] = "medline"
        params["retmode"] = "text"
    else:
        params["rettype"] = "abstract"
        params["retmode"] = "text"

    return with_pubmed_compat({
        "database": "pubmed",
        "pmids": ids,
        "format": output_format,
        "text": client.request_text("efetch.fcgi", params),
        "source": source_info("efetch.fcgi", params),
    }, ids=ids)

def normalize_pubmed_summary(record: JsonObject) -> JsonObject:
    article_ids = {
        str(item.get("idtype")): str(item.get("value"))
        for item in record.get("articleids", [])
        if isinstance(item, dict) and item.get("idtype") and item.get("value")
    }
    authors = [
        str(author.get("name"))
        for author in record.get("authors", [])
        if isinstance(author, dict) and author.get("name")
    ]
    pmid = str(record.get("uid") or record.get("pmid") or "")
    return {
        "pmid": pmid,
        "title": normalize_space(record.get("title")),
        "journal": normalize_space(
            record.get("fulljournalname") or record.get("source")
        ),
        "source": normalize_space(record.get("source")),
        "publication_date": normalize_space(
            record.get("pubdate") or record.get("epubdate")
        ),
        "authors": authors,
        "first_author": authors[0] if authors else None,
        "publication_types": record.get("pubtype", []),
        "doi": article_ids.get("doi"),
        "pmcid": article_ids.get("pmc"),
        "article_ids": article_ids,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
    }


def parse_pubmed_xml(xml_text: str) -> list[JsonObject]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise NcbiError("PubMed efetch returned invalid XML") from exc

    articles = []
    for pubmed_article in root.findall(".//PubmedArticle"):
        medline = pubmed_article.find("MedlineCitation")
        article = medline.find("Article") if medline is not None else None
        pubmed_data = pubmed_article.find("PubmedData")

        pmid = text_from_child(medline, "PMID")
        article_ids = parse_article_ids(pubmed_data)
        authors = parse_authors(article)
        journal = parse_journal(article)

        articles.append(
            {
                "pmid": pmid,
                "title": element_text(article.find("ArticleTitle"))
                if article is not None
                else "",
                "abstract": parse_abstract(article),
                "journal": journal,
                "authors": authors,
                "first_author": authors[0]["name"] if authors else None,
                "publication_types": [
                    element_text(node)
                    for node in article.findall(".//PublicationType")
                ]
                if article is not None
                else [],
                "doi": article_ids.get("doi"),
                "pmcid": article_ids.get("pmc"),
                "article_ids": article_ids,
                "mesh_terms": parse_mesh_terms(medline),
                "keywords": parse_keywords(medline),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None,
            }
        )
    return articles


def parse_article_ids(pubmed_data: ET.Element | None) -> dict[str, str]:
    ids: dict[str, str] = {}
    if pubmed_data is None:
        return ids
    for node in pubmed_data.findall("ArticleIdList/ArticleId"):
        id_type = node.attrib.get("IdType")
        value = element_text(node)
        if id_type and value:
            ids[id_type] = value
    return ids


def parse_authors(article: ET.Element | None) -> list[JsonObject]:
    if article is None:
        return []
    authors = []
    for node in article.findall(".//AuthorList/Author"):
        collective = text_from_child(node, "CollectiveName")
        last = text_from_child(node, "LastName")
        fore = text_from_child(node, "ForeName")
        initials = text_from_child(node, "Initials")
        name = collective or normalize_space(f"{fore} {last}".strip())
        if not name:
            continue
        authors.append(
            {
                "name": name,
                "last_name": last or None,
                "fore_name": fore or None,
                "initials": initials or None,
            }
        )
    return authors


def parse_journal(article: ET.Element | None) -> JsonObject:
    if article is None:
        return {}
    journal = article.find("Journal")
    if journal is None:
        return {}
    return {
        "title": text_from_child(journal, "Title"),
        "iso_abbreviation": text_from_child(journal, "ISOAbbreviation"),
        "issn": text_from_child(journal, "ISSN"),
        "publication_date": parse_pub_date(journal.find(".//PubDate")),
    }


def parse_pub_date(pub_date: ET.Element | None) -> str | None:
    if pub_date is None:
        return None
    year = text_from_child(pub_date, "Year")
    month = text_from_child(pub_date, "Month")
    day = text_from_child(pub_date, "Day")
    medline_date = text_from_child(pub_date, "MedlineDate")
    if year:
        return normalize_space(" ".join(part for part in [year, month, day] if part))
    return medline_date or None


def parse_abstract(article: ET.Element | None) -> JsonObject:
    if article is None:
        return {"text": "", "sections": []}
    sections = []
    for node in article.findall(".//Abstract/AbstractText"):
        label = node.attrib.get("Label") or node.attrib.get("NlmCategory")
        text = element_text(node)
        if text:
            sections.append({"label": label, "text": text})
    if not sections:
        return {"text": "", "sections": []}
    joined = " ".join(
        f"{section['label']}: {section['text']}"
        if section.get("label")
        else str(section["text"])
        for section in sections
    )
    return {"text": normalize_space(joined), "sections": sections}


def parse_mesh_terms(medline: ET.Element | None) -> list[str]:
    if medline is None:
        return []
    return [
        element_text(node)
        for node in medline.findall(".//MeshHeading/DescriptorName")
        if element_text(node)
    ]


def parse_keywords(medline: ET.Element | None) -> list[str]:
    if medline is None:
        return []
    return [
        element_text(node)
        for node in medline.findall(".//Keyword")
        if element_text(node)
    ]


def add_pubmed_date_params(args: JsonObject, params: JsonObject) -> None:
    date_from = args.get("date_from")
    date_to = args.get("date_to")
    if date_from or date_to:
        params["datetype"] = str(args.get("date_type", "pdat"))
    if date_from:
        params["mindate"] = require_date_like(date_from, "date_from")
    if date_to:
        params["maxdate"] = require_date_like(date_to, "date_to")


def normalize_pubmed_sort(value: Any) -> str:
    normalized = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    mapping = {
        "relevance": "relevance",
        "pub_date": "pub date",
        "publication_date": "pub date",
        "most_recent": "pub date",
        "journal": "journal",
        "title": "title",
        "author": "author",
        "first_author": "first author",
    }
    if normalized not in mapping:
        raise McpError(
            -32602,
            "sort must be one of: relevance, pub_date, journal, title, author, first_author",
        )
    return mapping[normalized]


def coerce_pmids(value: Any) -> list[str]:
    if isinstance(value, str):
        raw_ids: Iterable[Any] = re.split(r"[\s,;]+", value.strip())
    elif isinstance(value, list):
        raw_ids = value
    else:
        raise McpError(-32602, "ids must be a PMID string or an array of PMIDs")

    ids = []
    seen = set()
    for item in raw_ids:
        pmid = str(item).strip()
        if not pmid:
            continue
        if not re.fullmatch(r"\d+", pmid):
            raise McpError(-32602, f"Invalid PMID: {pmid}")
        if pmid not in seen:
            seen.add(pmid)
            ids.append(pmid)
    if not ids:
        raise McpError(-32602, "At least one PMID is required")
    if len(ids) > MAX_PUBMED_IDS:
        raise McpError(-32602, f"At most {MAX_PUBMED_IDS} PMIDs may be requested")
    return ids
