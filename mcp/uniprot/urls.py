"""URL builders for UniProt-adjacent records."""

from __future__ import annotations

from .constants import UNIPROT_REST_BASE_URL, UNIPROT_WEBSITE_BASE_URL


def uniprot_entry_url(accession: str) -> str:
    return f"{UNIPROT_WEBSITE_BASE_URL}/uniprotkb/{accession}/entry"


def uniprot_fasta_url(accession: str) -> str:
    return f"{UNIPROT_REST_BASE_URL}/uniprotkb/{accession}.fasta"


def uniprot_taxonomy_url(taxid: str) -> str:
    return f"{UNIPROT_WEBSITE_BASE_URL}/taxonomy/{taxid}"


def ncbi_gene_url(gene_id: str) -> str:
    return f"https://www.ncbi.nlm.nih.gov/gene/{gene_id}"


def alphafold_prediction_api_url(accession: str) -> str:
    return f"https://alphafold.ebi.ac.uk/api/prediction/{accession}"


def string_network_url(string_id: str) -> str:
    return f"https://string-db.org/network/{string_id}"


def cross_reference_url(database: str, ref_id: str) -> str:
    database_lower = database.lower()
    if database_lower == "geneid":
        return ncbi_gene_url(ref_id)
    if database_lower == "pdb":
        return f"https://www.rcsb.org/structure/{ref_id}"
    if database_lower == "reactome":
        return f"https://reactome.org/content/detail/{ref_id}"
    if database_lower == "pubmed":
        return f"https://pubmed.ncbi.nlm.nih.gov/{ref_id}/"
    if database_lower == "alphafolddb":
        return f"https://alphafold.ebi.ac.uk/entry/{ref_id}"
    if database_lower == "string":
        return string_network_url(ref_id)
    if database_lower == "go":
        return f"https://amigo.geneontology.org/amigo/term/{ref_id}"
    return ""
