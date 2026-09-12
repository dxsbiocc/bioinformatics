# MGnify MCP

The MGnify MCP exposes metadata-first retrieval for microbiome and
metagenomics studies, samples, and biome lineages through the MGnify JSON:API.

## Tools

- `mgnify_study_lookup`: fetch one MGnify study by `MGYS` accession.
- `mgnify_study_search`: search MGnify studies with bounded results.
- `mgnify_sample_lookup`: fetch one MGnify sample.
- `mgnify_biome_lookup`: fetch one MGnify biome lineage.
- `mgnify_status`: inspect server capabilities and optional network health.

Returned records follow `schemas/record.schema.json` and use the shared
front-end `project`, `sample`, and `taxonomy` components with table and
cross-reference previews.
