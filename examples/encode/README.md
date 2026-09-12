# ENCODE MCP Examples

Example calls:

- `encode_experiment_search` with `{"query":"K562 RNA-seq","max_results":5}`.
- `encode_experiment_lookup` with `{"accession":"ENCSR844TIU","max_files":10}`.
- `encode_biosample_search` with
  `{"query":"K562","organism":"Homo sapiens","status":"released","max_results":5}`.
- `encode_biosample_lookup` with `{"accession":"ENCBS000AAA"}`.
- `encode_file_lookup` with `{"accession":"ENCFF789PHQ"}`.
- `encode_file_manifest` with `{"experiment_accession":"ENCSR844TIU","file_format":"fastq","max_files":10}`.

The biosample tools return metadata-only sample cards. The file tools return
metadata-only manifests with ENCODE portal/API links and download URLs. They do
not start downloads.
