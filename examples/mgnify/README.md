# MGnify MCP Examples

The `mgnify` MCP server exposes metadata-first microbiome and metagenomics
retrieval. It returns shared `project`, `sample`, and `taxonomy` records with
MGnify browser/API links, sample metadata tables, biome lineage previews, and
relationship links for samples, studies, analyses, downloads, and runs.

## Study Lookup

```json
{
  "name": "mgnify_study_lookup",
  "arguments": {
    "accession": "MGYS00006862"
  }
}
```

Use this when the MGnify `MGYS` study accession is known.

## Study Search

```json
{
  "name": "mgnify_study_search",
  "arguments": {
    "query": "human gut",
    "max_results": 5
  }
}
```

Use this for bounded microbiome or metagenomics study discovery.

## Sample Lookup

```json
{
  "name": "mgnify_sample_lookup",
  "arguments": {
    "accession": "SRS10016989"
  }
}
```

Sample records expose BioSample links, host/taxonomy metadata, related studies,
and MGnify run links when available.

## Biome Lookup

```json
{
  "name": "mgnify_biome_lookup",
  "arguments": {
    "biome_id": "root:Host-associated:Human:Digestive system:Large intestine"
  }
}
```

Biome records expose lineage, sample counts, and related study/sample/genome
links.
