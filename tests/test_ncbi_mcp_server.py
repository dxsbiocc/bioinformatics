from __future__ import annotations

import importlib.util
import json
import pathlib
import sys
import unittest
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from frontend_contract_assertions import assert_result_frontend_contract

SERVER_PATH = ROOT / "mcp" / "ncbi" / "server.py"
SPEC = importlib.util.spec_from_file_location("ncbi_mcp_server", SERVER_PATH)
assert SPEC is not None and SPEC.loader is not None
ncbi = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = ncbi
SPEC.loader.exec_module(ncbi)


class FakeClient:
    def __init__(self) -> None:
        self.config = ncbi.NcbiConfig(api_key=None, email=None)
        self.requests_per_second = 3
        self.calls = []

    def request_json(self, endpoint, params):
        self.calls.append((endpoint, params))
        if endpoint == "einfo.fcgi":
            if params.get("db") == "gene":
                return EINFO_GENE
            return {"einforesult": {"dblist": ["pubmed", "gene", "taxonomy", "gds"]}}
        if endpoint == "elink.fcgi":
            return ELINK_GENE_PUBMED
        if endpoint == "esearch.fcgi" and params.get("db") == "gene":
            return {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["7157"],
                    "querytranslation": 'TP53[Gene Name] AND "Homo sapiens"[Organism]',
                }
            }
        if endpoint == "esummary.fcgi" and params.get("db") == "gene":
            return GENE_SUMMARY
        if endpoint == "esearch.fcgi" and params.get("db") == "taxonomy":
            return {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["9606"],
                    "querytranslation": "Homo sapiens[Scientific Name]",
                }
            }
        if endpoint == "esummary.fcgi" and params.get("db") == "taxonomy":
            return TAXONOMY_SUMMARY
        if endpoint == "esearch.fcgi" and params.get("db") == "bioproject":
            return {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["450921"],
                    "querytranslation": "PRJNA450921[PRJA]",
                }
            }
        if endpoint == "esummary.fcgi" and params.get("db") == "bioproject":
            return BIOPROJECT_SUMMARY
        if endpoint == "esearch.fcgi" and params.get("db") == "biosample":
            return {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["8954945"],
                    "querytranslation": "SAMN08954945[ACCN]",
                }
            }
        if endpoint == "esummary.fcgi" and params.get("db") == "biosample":
            return BIOSAMPLE_SUMMARY
        if endpoint == "esearch.fcgi" and params.get("db") == "sra":
            return {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["5437876"],
                    "querytranslation": "SRR7039034[ACCN]",
                }
            }
        if endpoint == "esummary.fcgi" and params.get("db") == "sra":
            return SRA_SUMMARY
        if endpoint == "esearch.fcgi" and params.get("db") == "gds":
            return {
                "esearchresult": {
                    "count": "1",
                    "idlist": ["200000100"],
                    "querytranslation": "GSE100[ACCN] AND gse[ETYP]",
                }
            }
        if endpoint == "esummary.fcgi" and params.get("db") == "gds":
            return GEO_SUMMARY
        if endpoint == "esearch.fcgi":
            return {
                "esearchresult": {
                    "count": "2",
                    "idlist": ["123", "456"],
                    "querytranslation": "cancer[All Fields]",
                }
            }
        if endpoint == "esummary.fcgi":
            return {
                "result": {
                    "uids": ["123"],
                    "123": {
                        "uid": "123",
                        "title": "A test article.",
                        "source": "Test J",
                        "fulljournalname": "Test Journal",
                        "pubdate": "2026 Jan",
                        "authors": [{"name": "Ada Lovelace"}],
                        "pubtype": ["Journal Article"],
                        "articleids": [
                            {"idtype": "pubmed", "value": "123"},
                            {"idtype": "doi", "value": "10.1000/test"},
                        ],
                    },
                }
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    def request_url_json(self, url, params, *, label="request", include_api_key=False):
        self.calls.append((url, params, label, include_api_key))
        return PMC_ID_CONVERSION

    def request_text(self, endpoint, params):
        self.calls.append((endpoint, params))
        return PUBMED_XML


PUBMED_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation>
      <PMID>123</PMID>
      <Article>
        <Journal>
          <ISSN>0000-0000</ISSN>
          <JournalIssue>
            <PubDate><Year>2026</Year><Month>Jan</Month><Day>2</Day></PubDate>
          </JournalIssue>
          <Title>Test Journal</Title>
          <ISOAbbreviation>Test J</ISOAbbreviation>
        </Journal>
        <ArticleTitle>Structured PubMed parsing works.</ArticleTitle>
        <Abstract>
          <AbstractText Label="BACKGROUND">Background text.</AbstractText>
          <AbstractText Label="RESULTS">Result text.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author>
            <LastName>Lovelace</LastName>
            <ForeName>Ada</ForeName>
            <Initials>A</Initials>
          </Author>
        </AuthorList>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
        </PublicationTypeList>
      </Article>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Genomics</DescriptorName></MeshHeading>
      </MeshHeadingList>
      <KeywordList><Keyword>RNA-seq</Keyword></KeywordList>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="pubmed">123</ArticleId>
        <ArticleId IdType="doi">10.1000/test</ArticleId>
        <ArticleId IdType="pmc">PMC123</ArticleId>
      </ArticleIdList>
      <ReferenceList>
        <Reference>
          <ArticleIdList>
            <ArticleId IdType="pubmed">999</ArticleId>
            <ArticleId IdType="doi">10.1000/reference</ArticleId>
          </ArticleIdList>
        </Reference>
      </ReferenceList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""

GEO_SUMMARY = {
    "result": {
        "uids": ["200000100"],
        "200000100": {
            "uid": "200000100",
            "accession": "GSE100",
            "title": "zzMex67 co-IPed RNA vs. Total RNA",
            "summary": "Comparison of cDNA from RNA IPed with zzMex67.",
            "gpl": "221",
            "gse": "100",
            "taxon": "Saccharomyces cerevisiae",
            "entrytype": "GSE",
            "gdstype": "Expression profiling by array",
            "pdat": "2002/11/25",
            "samples": [
                {"accession": "GSM3006", "title": "sample one"},
                {"accession": "GSM3004", "title": "sample two"},
            ],
            "n_samples": 2,
            "platformtitle": "Yeast ORF array",
            "platformtaxa": "Saccharomyces cerevisiae",
            "pubmedids": ["12524544"],
            "ftplink": "ftp://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE100/",
            "geo2r": "yes",
            "bioproject": "PRJNA84467",
        },
    }
}

GENE_SUMMARY = {
    "result": {
        "uids": ["7157"],
        "7157": {
            "uid": "7157",
            "name": "TP53",
            "description": "tumor protein p53",
            "status": "",
            "currentid": "",
            "chromosome": "17",
            "geneticsource": "genomic",
            "maplocation": "17p13.1",
            "otheraliases": "BCC7, BMFS5, LFS1, P53, TRP53",
            "otherdesignations": "cellular tumor antigen p53|tumor protein 53",
            "nomenclaturesymbol": "TP53",
            "nomenclaturename": "tumor protein p53",
            "nomenclaturestatus": "Official",
            "mim": ["191170"],
            "genomicinfo": [
                {
                    "chrloc": "17",
                    "chraccver": "NC_000017.11",
                    "chrstart": 7687489,
                    "chrstop": 7668420,
                    "exoncount": 13,
                }
            ],
            "summary": "This gene encodes a tumor suppressor protein.",
            "organism": {
                "scientificname": "Homo sapiens",
                "commonname": "human",
                "taxid": 9606,
            },
        },
    }
}

TAXONOMY_SUMMARY = {
    "result": {
        "uids": ["9606"],
        "9606": {
            "uid": "9606",
            "status": "active",
            "rank": "species",
            "division": "primates",
            "scientificname": "Homo sapiens",
            "commonname": "human",
            "taxid": 9606,
            "modificationdate": "2024/09/10 00:00",
            "genbankdivision": "Primates",
        },
    }
}

EINFO_GENE = {
    "einforesult": {
        "dbinfo": [
            {
                "dbname": "gene",
                "menuname": "Gene",
                "description": "Gene database",
                "dbbuild": "Build260906-1425.1",
                "count": "99515628",
                "lastupdate": "2026/09/07 01:22",
                "fieldlist": [
                    {
                        "name": "GENE",
                        "fullname": "Gene Name",
                        "description": "Symbol or symbols of the gene",
                        "termcount": "147009358",
                        "isdate": "N",
                        "isnumerical": "N",
                        "ishidden": "N",
                    }
                ],
                "linklist": [
                    {
                        "name": "gene_pubmed",
                        "menu": "PubMed Links",
                        "description": "Link to related PubMed entry",
                        "dbto": "pubmed",
                    }
                ],
            }
        ]
    }
}

ELINK_GENE_PUBMED = {
    "linksets": [
        {
            "dbfrom": "gene",
            "ids": ["7157"],
            "linksetdbs": [
                {
                    "dbto": "pubmed",
                    "linkname": "gene_pubmed",
                    "links": ["12032546", "20937277", "99999999"],
                }
            ],
        }
    ]
}

PMC_ID_CONVERSION = {
    "status": "ok",
    "response-date": "2026-09-08 02:49:01",
    "records": [
        {
            "doi": "10.1186/s12967-023-04056-z",
            "pmcid": "PMC10044739",
            "pmid": 36973787,
            "requested-id": "36973787",
        }
    ],
}

BIOPROJECT_SUMMARY = {
    "result": {
        "uids": ["450921"],
        "450921": {
            "uid": "450921",
            "taxid": 9606,
            "project_id": 450921,
            "project_acc": "PRJNA450921",
            "project_type": "Primary submission",
            "project_data_type": "Transcriptome or Gene expression",
            "project_target_scope": "Multiisolate",
            "project_target_material": "Transcriptome",
            "project_target_capture": "Whole",
            "project_methodtype": "Sequencing",
            "project_objectives_list": [
                {
                    "project_objectivestype": "Raw Sequence Reads",
                    "project_objectives": "",
                }
            ],
            "registration_date": "2018/04/19 00:00",
            "project_name": "Homo sapiens",
            "project_title": "Human breast cancer xenograft RNA-Seq",
            "project_description": "RNA sequencing of human breast cancer xenografts.",
            "organism_name": "Homo sapiens",
            "sequencing_status": "SRA/Trace",
            "submitter_organization": "GEO",
            "submitter_organization_list": ["GEO"],
            "supergroup": "Eukaryota",
        },
    }
}

BIOSAMPLE_XML = """
<BioSample access="public" publication_date="2019-01-10T00:00:00.000"
  last_update="2019-01-10T01:38:33.163" submission_date="2018-04-19T06:56:04.800"
  id="8954945" accession="SAMN08954945">
  <Ids>
    <Id db="BioSample" is_primary="1">SAMN08954945</Id>
    <Id db="SRA">SRS3196552</Id>
    <Id db="GEO">GSM3104269</Id>
  </Ids>
  <Description>
    <Title>Human breast cancer xenograft 4913</Title>
    <Organism taxonomy_id="9606" taxonomy_name="Homo sapiens">
      <OrganismName>Homo sapiens</OrganismName>
    </Organism>
  </Description>
  <Owner>
    <Name>Department of Physiology and Biophysics, Weill Cornell Medical College</Name>
  </Owner>
  <Models><Model>Generic</Model></Models>
  <Package display_name="Generic">Generic.1.0</Package>
  <Attributes>
    <Attribute attribute_name="source_name" harmonized_name="source_name" display_name="source name">Human breast cancer xenograft</Attribute>
    <Attribute attribute_name="disease state" harmonized_name="disease" display_name="disease">Triple Negative Breast Cancer</Attribute>
    <Attribute attribute_name="tissue" harmonized_name="tissue" display_name="tissue">TNBC Patient Derived Xenograft (PDX)</Attribute>
  </Attributes>
  <Links>
    <Link type="url" label="GEO Sample GSM3104269">https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3104269</Link>
    <Link type="entrez" target="bioproject" label="PRJNA450921">450921</Link>
  </Links>
  <Status status="live" when="2019-01-10T00:50:04.537"/>
</BioSample>
"""

BIOSAMPLE_SUMMARY = {
    "result": {
        "uids": ["8954945"],
        "8954945": {
            "uid": "8954945",
            "title": "Human breast cancer xenograft 4913",
            "accession": "SAMN08954945",
            "date": "2019/01/10",
            "publicationdate": "2019/01/10",
            "modificationdate": "2019/01/10",
            "organization": "Department of Physiology and Biophysics, Weill Cornell Medical College",
            "taxonomy": "9606",
            "organism": "Homo sapiens",
            "sourcesample": "BioSample:SAMN08954945",
            "sampledata": BIOSAMPLE_XML,
            "identifiers": "BioSample: SAMN08954945; SRA: SRS3196552; GEO: GSM3104269",
            "infraspecies": "",
            "package": "Generic",
            "sortkey": 120190110,
        },
    }
}

SRA_EXPERIMENT_XML = """
<Summary>
  <Title>GSM3104269: Human breast cancer xenograft 4913; Homo sapiens; RNA-Seq</Title>
  <Platform instrument_model="Illumina HiSeq 2500">ILLUMINA</Platform>
  <Statistics total_runs="1" total_spots="27901420" total_bases="5608185420" total_size="3610386315" load_done="true" cluster_name="public"/>
</Summary>
<Submitter acc="SRA692814" center_name="GEO" contact_name="Gene Expression Omnibus"/>
<Experiment acc="SRX3971072" ver="1" status="public" name="GSM3104269"/>
<Study acc="SRP141118" name="Activating Transcription Factor 4 modulated TGFb-induced aggressiveness"/>
<Organism taxid="9606" ScientificName="Homo sapiens"/>
<Sample acc="SRS3196552" name=""/>
<Instrument ILLUMINA="Illumina HiSeq 2500"/>
<Library_descriptor>
  <LIBRARY_STRATEGY>RNA-Seq</LIBRARY_STRATEGY>
  <LIBRARY_SOURCE>TRANSCRIPTOMIC</LIBRARY_SOURCE>
  <LIBRARY_SELECTION>cDNA</LIBRARY_SELECTION>
  <LIBRARY_LAYOUT><PAIRED/></LIBRARY_LAYOUT>
  <LIBRARY_CONSTRUCTION_PROTOCOL>Total RNA was extracted from PDX samples.</LIBRARY_CONSTRUCTION_PROTOCOL>
</Library_descriptor>
<Bioproject>PRJNA450921</Bioproject>
<Biosample>SAMN08954945</Biosample>
"""

SRA_RUNS_XML = """
<Run acc="SRR7039034" total_spots="27901420" total_bases="5608185420"
  load_done="true" is_public="true" cluster_name="public" static_data_available="true"/>
"""

SRA_SUMMARY = {
    "result": {
        "uids": ["5437876"],
        "5437876": {
            "uid": "5437876",
            "expxml": SRA_EXPERIMENT_XML,
            "runs": SRA_RUNS_XML,
            "extlinks": "",
            "createdate": "2019/01/23",
            "updatedate": "2018/04/19",
        },
    }
}


class NcbiMcpServerTests(unittest.TestCase):
    def test_coerce_pmids_deduplicates_strings(self) -> None:
        self.assertEqual(ncbi.coerce_pmids("123, 456 123;789"), ["123", "456", "789"])

    def test_coerce_pmids_rejects_non_numeric_ids(self) -> None:
        with self.assertRaises(ncbi.McpError):
            ncbi.coerce_pmids(["123", "PMC123"])

    def test_parse_pubmed_xml_returns_structured_article(self) -> None:
        articles = ncbi.parse_pubmed_xml(PUBMED_XML)
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article["pmid"], "123")
        self.assertEqual(article["doi"], "10.1000/test")
        self.assertEqual(article["pmcid"], "PMC123")
        self.assertEqual(article["article_ids"]["pubmed"], "123")
        self.assertEqual(article["authors"][0]["name"], "Ada Lovelace")
        self.assertIn("BACKGROUND: Background text.", article["abstract"]["text"])
        self.assertEqual(article["journal"]["publication_date"], "2026 Jan 2")
        self.assertEqual(article["mesh_terms"], ["Genomics"])
        self.assertEqual(article["keywords"], ["RNA-seq"])

    def test_pubmed_search_attaches_summaries(self) -> None:
        result = ncbi.pubmed_search({"query": "cancer", "max_results": 2}, FakeClient())
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"citation"},
            required_preview_kinds={"citation_list"},
        )
        self.assertEqual(result["pmids"], ["123", "456"])
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["articles"][0]["doi"], "10.1000/test")
        self.assertEqual(result["schema_version"], "bioinformatics.ncbi.result.v1")
        self.assertEqual(result["provenance"], result["source"])
        self.assertEqual(result["records"][0]["stable_id"], "PMID:123")
        self.assertEqual(result["citations"][0]["label"], "PMID:123")
        self.assertEqual(result["citations"][0]["hover"]["fields"][0]["value"], "PMID:123")
        self.assertEqual(result["records"][0]["display"]["component"], "citation")
        self.assertEqual(result["records"][0]["links"][0]["url"], "https://pubmed.ncbi.nlm.nih.gov/123/")
        self.assertIn(
            {"label": "Journal", "value": "Test Journal"},
            result["records"][0]["display"]["metadata"],
        )
        self.assertIn(
            {"label": "PMID:123", "kind": "identifier"},
            result["records"][0]["display"]["badges"],
        )
        self.assertIn(
            {
                "label": "PubMed",
                "url": "https://pubmed.ncbi.nlm.nih.gov/123/",
                "kind": "external",
                "primary": True,
            },
            result["records"][0]["display"]["actions"],
        )

    def test_pubmed_search_without_summaries_returns_minimal_records(self) -> None:
        result = ncbi.pubmed_search(
            {
                "query": "cancer",
                "max_results": 2,
                "include_summaries": False,
            },
            FakeClient(),
        )
        self.assertNotIn("articles", result)
        self.assertEqual([record["label"] for record in result["records"]], ["PMID:123", "PMID:456"])
        self.assertEqual([citation["id"] for citation in result["citations"]], ["123", "456"])

    def test_stdio_style_tools_list_response(self) -> None:
        server = ncbi.NcbiMcpServer(client=FakeClient())
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/list",
                "params": {},
            }
        )
        self.assertIsNotNone(response)
        tools = response["result"]["tools"]
        tool_names = {tool["name"] for tool in tools}
        self.assertIn("ncbi_parameter_domains", tool_names)
        self.assertIn("ncbi_resolve_context", tool_names)
        self.assertIn("pubmed_search", tool_names)
        self.assertIn("geo_series", tool_names)
        self.assertIn("gene_lookup", tool_names)
        self.assertIn("taxonomy_lookup", tool_names)
        self.assertIn("pmc_id_convert", tool_names)
        self.assertIn("ncbi_db_info", tool_names)
        self.assertIn("ncbi_link", tool_names)
        self.assertIn("bioproject_lookup", tool_names)
        self.assertIn("biosample_lookup", tool_names)
        self.assertIn("sra_lookup", tool_names)
        self.assertIn("sra_search", tool_names)
        self.assertIn("ncbi_related_records", tool_names)
        self.assertIn("geo_download_plan", tool_names)
        self.assertIn("sra_download_plan", tool_names)
        self.assertIn("omics_sample_sheet", tool_names)
        self.assertIn("tool_runtime_status", tool_names)

    def test_resolve_context_reports_static_database_hints_without_network(self) -> None:
        client = FakeClient()
        result = ncbi.ncbi_resolve_context({"context_type": "databases", "max_results": 20}, client)
        self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
        self.assertEqual(client.calls, [])
        values = {context["value"] for context in result["contexts"]}
        self.assertIn("pubmed", values)
        self.assertIn("gds", values)
        self.assertIn("sra", values)

    def test_resolve_context_searches_pubmed_and_recommends_followups(self) -> None:
        result = ncbi.ncbi_resolve_context(
            {"context_type": "literature", "database": "pubmed", "query": "cancer", "max_results": 5},
            FakeClient(),
        )
        self.assertEqual(result["source"]["endpoint"], "esearch.fcgi")
        self.assertEqual([item["value"] for item in result["identifiers"][:2]], ["123", "456"])
        tool_names = {call["tool_name"] for call in result["recommended_calls"]}
        self.assertIn("pubmed_summaries", tool_names)
        self.assertIn("pubmed_articles", tool_names)

    def test_ncbi_client_adds_tool_email_and_api_key(self) -> None:
        captured_urls = []

        def opener(url, headers, timeout):
            captured_urls.append(url)
            return "{}"

        client = ncbi.NcbiClient(
            ncbi.NcbiConfig(api_key="secret", email="agent@example.test", tool="bio-test"),
            opener=opener,
            sleep=lambda _: None,
            monotonic=lambda: 1000.0,
        )
        client.request_text("esearch.fcgi", {"db": "pubmed", "term": "rna"})
        query = urllib.parse.parse_qs(urllib.parse.urlparse(captured_urls[0]).query)
        self.assertEqual(query["tool"], ["bio-test"])
        self.assertEqual(query["email"], ["agent@example.test"])
        self.assertEqual(query["api_key"], ["secret"])

    def test_tool_call_returns_structured_content(self) -> None:
        server = ncbi.NcbiMcpServer(client=FakeClient())
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "pubmed_summaries",
                    "arguments": {"ids": ["123"]},
                },
            }
        )
        self.assertEqual(response["id"], "call-1")
        payload = response["result"]["structuredContent"]
        self.assertEqual(payload["articles"][0]["pmid"], "123")
        self.assertEqual(payload["records"][0]["identifiers"]["doi"]["url"], "https://doi.org/10.1000/test")
        self.assertTrue(json.loads(response["result"]["content"][0]["text"]))

    def test_pubmed_articles_exposes_hover_and_external_links(self) -> None:
        result = ncbi.pubmed_articles({"ids": ["123"]}, FakeClient())
        record = result["records"][0]
        citation = result["citations"][0]
        self.assertEqual(record["record_type"], "pubmed_article")
        self.assertEqual(record["url"], "https://pubmed.ncbi.nlm.nih.gov/123/")
        self.assertEqual(citation["title"], "Structured PubMed parsing works.")
        self.assertEqual(citation["journal"], "Test Journal")
        self.assertEqual(citation["journal_abbreviation"], "Test J")
        self.assertEqual(citation["hover"]["icon"], "pubmed")
        self.assertEqual(record["display"]["previews"][0]["kind"], "citation_list")
        self.assertEqual(record["display"]["previews"][0]["data"]["pubmed_ids"], ["123"])
        self.assertIn(
            {"label": "PMC", "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC123/", "kind": "external", "primary": False},
            citation["links"],
        )

    def test_pubmed_fetch_keeps_text_and_adds_minimal_records(self) -> None:
        result = ncbi.pubmed_fetch({"ids": "123", "format": "xml"}, FakeClient())
        self.assertIn("PubmedArticleSet", result["text"])
        self.assertEqual(result["records"][0]["label"], "PMID:123")
        self.assertEqual(result["citations"][0]["url"], "https://pubmed.ncbi.nlm.nih.gov/123/")

    def test_geo_series_resolves_gse_accession(self) -> None:
        result = ncbi.geo_series({"accession": "gse100"}, FakeClient())
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"dataset"},
            required_preview_kinds={"xref_groups", "table", "citation_list"},
        )
        self.assertTrue(result["found"])
        self.assertEqual(result["accession"], "GSE100")
        self.assertEqual(result["series"]["uid"], "200000100")
        self.assertEqual(result["series"]["sample_accessions"], ["GSM3006", "GSM3004"])
        self.assertEqual(result["series"]["platform"]["accession"], "GPL221")
        self.assertEqual(result["records"][0]["record_type"], "geo_series")
        self.assertEqual(result["records"][0]["stable_id"], "GSE100")
        self.assertEqual(result["records"][0]["display"]["component"], "dataset")
        self.assertIn(
            {"label": "Platform", "value": "GPL221"},
            result["records"][0]["display"]["metadata"],
        )
        self.assertEqual(
            result["records"][0]["url"],
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE100",
        )
        self.assertIn(
            {
                "label": "Series matrix",
                "url": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE100/matrix/GSE100_series_matrix.txt.gz",
                "kind": "download",
                "primary": False,
            },
            result["records"][0]["links"],
        )
        self.assertIn(
            {
                "label": "GEO",
                "url": "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE100",
                "kind": "external",
                "primary": True,
            },
            result["records"][0]["display"]["actions"],
        )
        self.assertEqual(
            result["records"][0]["related"]["samples"][0]["url"],
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSM3006",
        )
        self.assertEqual(
            result["records"][0]["related"]["platform"]["url"],
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GPL221",
        )
        self.assertEqual(
            result["records"][0]["related"]["literature"][0]["url"],
            "https://pubmed.ncbi.nlm.nih.gov/12524544/",
        )
        self.assertEqual(
            result["records"][0]["related"]["bioproject"]["url"],
            "https://www.ncbi.nlm.nih.gov/bioproject/PRJNA84467",
        )
        preview_kinds = {preview["kind"] for preview in result["records"][0]["display"]["previews"]}
        self.assertEqual(preview_kinds, {"xref_groups", "table", "citation_list"})

    def test_geo_search_returns_frontend_records(self) -> None:
        result = ncbi.geo_search({"query": "yeast", "entry_type": "gse"}, FakeClient())
        self.assertEqual(result["uids"], ["200000100"])
        self.assertEqual(result["datasets"][0]["accession"], "GSE100")
        self.assertEqual(result["records"][0]["display"]["component"], "dataset")
        self.assertEqual(
            result["records"][0]["identifiers"]["bioproject"]["url"],
            "https://www.ncbi.nlm.nih.gov/bioproject/PRJNA84467",
        )

    def test_geo_download_plan_returns_frontend_manifest(self) -> None:
        result = ncbi.geo_download_plan({"accession": "GSE100"}, FakeClient())
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"download_plan"},
            required_preview_kinds={"download_manifest"},
        )
        record = result["records"][0]
        self.assertTrue(result["found"])
        self.assertEqual(result["manifest"]["accession"], "GSE100")
        self.assertEqual(result["manifest"]["sample_accessions"], ["GSM3006", "GSM3004"])
        self.assertEqual(record["record_type"], "geo_download_plan")
        self.assertEqual(record["stable_id"], "GSE100:download-plan")
        self.assertEqual(record["display"]["component"], "download_plan")
        self.assertEqual(record["display"]["previews"][0]["kind"], "download_manifest")
        self.assertEqual(record["display"]["previews"][0]["data"]["sample_count"], 2)
        self.assertIn(
            {
                "label": "Series matrix",
                "url": "https://ftp.ncbi.nlm.nih.gov/geo/series/GSEnnn/GSE100/matrix/GSE100_series_matrix.txt.gz",
                "kind": "download",
                "primary": False,
            },
            record["display"]["actions"],
        )

    def test_geo_series_rejects_non_gse_accessions(self) -> None:
        with self.assertRaises(ncbi.McpError):
            ncbi.geo_series({"accession": "GSM3006"}, FakeClient())

    def test_gene_lookup_returns_frontend_record(self) -> None:
        result = ncbi.gene_lookup(
            {"query": "TP53", "organism": "Homo sapiens"},
            FakeClient(),
        )
        assert_result_frontend_contract(
            self,
            result,
            expected_components={"gene"},
            required_preview_kinds={"xref_groups"},
        )
        record = result["records"][0]
        self.assertEqual(result["gene_ids"], ["7157"])
        self.assertEqual(result["genes"][0]["symbol"], "TP53")
        self.assertEqual(record["record_type"], "ncbi_gene")
        self.assertEqual(record["stable_id"], "GeneID:7157")
        self.assertEqual(record["url"], "https://www.ncbi.nlm.nih.gov/gene/7157")
        self.assertEqual(record["display"]["component"], "gene")
        self.assertIn("xref_groups", {preview["kind"] for preview in record["display"]["previews"]})
        self.assertIn({"label": "Chromosome", "value": "17"}, record["display"]["metadata"])
        self.assertEqual(
            record["related"]["taxonomy"]["url"],
            "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606",
        )
        self.assertEqual(
            record["identifiers"]["omim"][0]["url"],
            "https://www.ncbi.nlm.nih.gov/omim/191170",
        )

    def test_taxonomy_lookup_returns_frontend_record(self) -> None:
        result = ncbi.taxonomy_lookup({"query": "Homo sapiens"}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["taxids"], ["9606"])
        self.assertEqual(result["taxa"][0]["scientific_name"], "Homo sapiens")
        self.assertEqual(record["record_type"], "ncbi_taxonomy")
        self.assertEqual(record["stable_id"], "TaxID:9606")
        self.assertEqual(record["display"]["component"], "taxonomy")
        self.assertIn({"label": "Rank", "value": "species"}, record["display"]["metadata"])
        self.assertEqual(
            record["links"][0]["url"],
            "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606",
        )

    def test_pmc_id_convert_returns_clickable_identifier_record(self) -> None:
        result = ncbi.pmc_id_convert({"ids": "36973787"}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["conversions"][0]["pmcid"], "PMC10044739")
        self.assertEqual(record["record_type"], "pmc_id_conversion")
        self.assertEqual(record["stable_id"], "PMC10044739")
        self.assertEqual(record["display"]["component"], "identifier_conversion")
        self.assertIn(
            {
                "label": "PMC",
                "url": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10044739/",
                "kind": "external",
                "primary": True,
            },
            record["display"]["actions"],
        )
        self.assertEqual(
            record["identifiers"]["doi"]["url"],
            "https://doi.org/10.1186/s12967-023-04056-z",
        )

    def test_ncbi_db_info_returns_database_record(self) -> None:
        result = ncbi.ncbi_db_info({"database": "gene", "include_fields": True}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["database_info"]["db_name"], "gene")
        self.assertEqual(record["record_type"], "ncbi_database")
        self.assertEqual(record["stable_id"], "NCBI_DB:gene")
        self.assertEqual(record["display"]["component"], "database")
        self.assertIn({"label": "Search fields", "value": "1"}, record["display"]["metadata"])

    def test_ncbi_link_returns_frontend_linkset_record(self) -> None:
        result = ncbi.ncbi_link(
            {"db_from": "gene", "db_to": "pubmed", "ids": ["7157"], "max_links": 2},
            FakeClient(),
        )
        record = result["records"][0]
        group = result["linksets"][0]["target_groups"][0]
        self.assertEqual(group["count"], 3)
        self.assertEqual(group["returned"], 2)
        self.assertTrue(group["truncated"])
        self.assertEqual(record["record_type"], "ncbi_entrez_linkset")
        self.assertEqual(record["display"]["component"], "linkset")
        self.assertEqual(record["display"]["previews"][0]["kind"], "xref_groups")
        self.assertEqual(record["display"]["previews"][0]["data"]["group_count"], 1)
        self.assertEqual(
            record["display"]["actions"][0]["url"],
            "https://pubmed.ncbi.nlm.nih.gov/12032546/",
        )

    def test_bioproject_lookup_returns_project_record(self) -> None:
        result = ncbi.bioproject_lookup({"query": "PRJNA450921"}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["bioproject_ids"], ["450921"])
        self.assertEqual(result["projects"][0]["accession"], "PRJNA450921")
        self.assertEqual(record["record_type"], "ncbi_bioproject")
        self.assertEqual(record["stable_id"], "PRJNA450921")
        self.assertEqual(record["display"]["component"], "project")
        self.assertEqual(record["url"], "https://www.ncbi.nlm.nih.gov/bioproject/PRJNA450921")
        self.assertIn(
            {
                "label": "SRA Run Selector",
                "url": "https://www.ncbi.nlm.nih.gov/Traces/study/?acc=PRJNA450921",
                "kind": "external",
                "primary": False,
            },
            record["links"],
        )
        self.assertEqual(
            record["related"]["taxonomy"]["url"],
            "https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=9606",
        )

    def test_biosample_lookup_returns_sample_record(self) -> None:
        result = ncbi.biosample_lookup({"query": "SAMN08954945"}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["biosample_ids"], ["8954945"])
        self.assertEqual(result["samples"][0]["accession"], "SAMN08954945")
        self.assertEqual(result["samples"][0]["attributes"][1]["value"], "Triple Negative Breast Cancer")
        self.assertEqual(record["record_type"], "ncbi_biosample")
        self.assertEqual(record["stable_id"], "SAMN08954945")
        self.assertEqual(record["display"]["component"], "sample")
        self.assertEqual(record["identifiers"]["geo_sample"]["id"], "GSM3104269")
        self.assertEqual(record["identifiers"]["bioproject"]["id"], "PRJNA450921")
        self.assertEqual(
            record["related"]["sra_sample"]["url"],
            "https://www.ncbi.nlm.nih.gov/sra/SRS3196552",
        )
        self.assertEqual(
            record["related"]["bioproject"]["url"],
            "https://www.ncbi.nlm.nih.gov/bioproject/PRJNA450921",
        )

    def test_sra_lookup_returns_run_record(self) -> None:
        result = ncbi.sra_lookup({"query": "SRR7039034"}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["sra_ids"], ["5437876"])
        self.assertEqual(result["experiments"][0]["accession"], "SRR7039034")
        self.assertEqual(result["experiments"][0]["library"]["strategy"], "RNA-Seq")
        self.assertEqual(record["record_type"], "ncbi_sra")
        self.assertEqual(record["stable_id"], "SRR7039034")
        self.assertEqual(record["display"]["component"], "run")
        self.assertIn("table", {preview["kind"] for preview in record["display"]["previews"]})
        self.assertIn({"label": "Strategy", "value": "RNA-Seq"}, record["display"]["metadata"])
        self.assertEqual(
            record["related"]["biosample"]["url"],
            "https://www.ncbi.nlm.nih.gov/biosample/SAMN08954945",
        )
        self.assertEqual(
            record["related"]["runs"][0]["run_browser_url"],
            "https://trace.ncbi.nlm.nih.gov/Traces/?view=run_browser&acc=SRR7039034",
        )

    def test_sra_download_plan_returns_commands_and_links(self) -> None:
        result = ncbi.sra_download_plan(
            {"query": "SRR7039034", "threads": 4},
            FakeClient(),
        )
        run = result["runs"][0]
        record = result["records"][0]
        self.assertEqual(run["run_accession"], "SRR7039034")
        self.assertEqual(run["biosample"], "SAMN08954945")
        self.assertIn("prefetch SRR7039034", run["commands"]["prefetch"])
        self.assertIn("fasterq-dump SRR7039034", run["commands"]["fastq"])
        self.assertIn("--threads 4", run["commands"]["fastq"])
        self.assertEqual(record["record_type"], "sra_download_plan_item")
        self.assertEqual(record["display"]["component"], "download_plan")
        self.assertEqual(record["display"]["previews"][0]["kind"], "download_manifest")
        self.assertIn("fastq", record["display"]["previews"][0]["data"]["commands"])
        self.assertEqual(
            record["display"]["primary_url"],
            "https://trace.ncbi.nlm.nih.gov/Traces/?view=run_browser&acc=SRR7039034",
        )

    def test_sra_search_applies_omics_filters(self) -> None:
        client = FakeClient()
        result = ncbi.sra_search(
            {
                "query": "breast cancer",
                "organism": "Homo sapiens",
                "strategy": "RNA-Seq",
                "max_results": 1,
            },
            client,
        )
        search_call = client.calls[0]
        self.assertEqual(search_call[0], "esearch.fcgi")
        self.assertIn("Homo sapiens[Organism]", search_call[1]["term"])
        self.assertIn("RNA-Seq[Strategy]", search_call[1]["term"])
        self.assertEqual(result["records"][0]["display"]["component"], "run")

    def test_ncbi_status_lists_full_tool_inventory(self) -> None:
        result = ncbi.ncbi_status({}, FakeClient())
        tool_names = {tool["name"] for tool in ncbi.tool_definitions()}
        self.assertEqual(result["available_tool_count"], len(tool_names))
        self.assertEqual(set(result["available_tools"]), tool_names)
        self.assertIn("pubmed_search", result["tool_groups"]["literature"])
        self.assertIn("geo_download_plan", result["tool_groups"]["omics_datasets"])
        self.assertIn("sra_download_plan", result["tool_groups"]["omics_datasets"])
        self.assertIn("tool_runtime_status", result["tool_groups"]["runtime"])
        self.assertIn("download_plan", result["frontend_components"])
        self.assertIn("sample_sheet", result["frontend_components"])
        self.assertIn("runtime_status", result["frontend_components"])
        self.assertIn("download_manifest", result["preview_kinds"])
        self.assertIn("xref_groups", result["preview_kinds"])

    def test_omics_sample_sheet_builds_geo_table(self) -> None:
        result = ncbi.omics_sample_sheet({"query": "GSE100"}, FakeClient())
        record = result["records"][0]
        self.assertEqual(result["sample_source"], "geo")
        self.assertIsInstance(result["source"], dict)
        self.assertEqual(result["rows"][0]["sample_accession"], "GSM3006")
        self.assertEqual(result["columns"][0]["key"], "sample_accession")
        self.assertEqual(record["record_type"], "omics_sample_sheet")
        self.assertEqual(record["display"]["component"], "sample_sheet")
        self.assertEqual(record["display"]["previews"][0]["kind"], "table")
        self.assertEqual(record["display"]["previews"][0]["data"]["row_count"], 2)
        self.assertEqual(
            record["display"]["primary_url"],
            "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE100",
        )

    def test_omics_sample_sheet_builds_sra_table(self) -> None:
        result = ncbi.omics_sample_sheet(
            {"source": "sra", "query": "SRR7039034"},
            FakeClient(),
        )
        row = result["rows"][0]
        self.assertEqual(result["sample_source"], "sra")
        self.assertEqual(row["run_accession"], "SRR7039034")
        self.assertEqual(row["library_strategy"], "RNA-Seq")
        self.assertEqual(
            row["run_browser_url"],
            "https://trace.ncbi.nlm.nih.gov/Traces/?view=run_browser&acc=SRR7039034",
        )
        self.assertEqual(result["records"][0]["display"]["component"], "sample_sheet")

    def test_tool_runtime_status_returns_runtime_records(self) -> None:
        result = ncbi.tool_runtime_status(
            {"tools": ["python3", "definitely-not-a-real-tool-omx"]},
            FakeClient(),
        )
        self.assertEqual(result["returned"], 2)
        statuses = {status["tool"]: status for status in result["tools"]}
        self.assertTrue(statuses["python3"]["available"])
        self.assertFalse(statuses["definitely-not-a-real-tool-omx"]["available"])
        self.assertEqual(result["records"][0]["record_type"], "tool_runtime_status")
        self.assertEqual(result["records"][0]["display"]["component"], "runtime_status")
        self.assertEqual(result["records"][0]["display"]["previews"][0]["kind"], "text")

    def test_ncbi_related_records_wraps_elink(self) -> None:
        result = ncbi.ncbi_related_records(
            {
                "database": "gene",
                "ids": ["7157"],
                "target_databases": ["pubmed"],
                "max_links": 1,
            },
            FakeClient(),
        )
        self.assertEqual(result["tool"], "ncbi_related_records")
        self.assertEqual(result["target_databases"], ["pubmed"])
        self.assertEqual(result["records"][0]["display"]["component"], "linkset")
        self.assertEqual(
            result["records"][0]["display"]["actions"][0]["url"],
            "https://pubmed.ncbi.nlm.nih.gov/12032546/",
        )


if __name__ == "__main__":
    unittest.main()
