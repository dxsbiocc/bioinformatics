# bioRxiv/medRxiv MCP Server

This MCP server wraps the public bioRxiv API for metadata-first preprint and
publication-link retrieval.

## Tools

- `biorxiv_preprint_lookup`: fetch one bioRxiv or medRxiv preprint by DOI.
- `biorxiv_preprint_interval`: fetch bounded preprint metadata by date range or
  recent-day interval.
- `biorxiv_publication_lookup`: fetch the formal-publication linkage for one
  preprint DOI.
- `biorxiv_publication_interval`: fetch bounded publication-linkage rows by
  date range or recent-day interval.
- `biorxiv_status`: inspect local configuration and optional network health.

## API Basis

The implementation uses the documented bioRxiv API paths:

- `details/<server>/<start>/<end>/<cursor>/json`
- `details/<server>/<doi>/na/json`
- `pubs/<server>/<start>/<end>/<cursor>`
- `pubs/<server>/<doi>/na/json`

`server` is `biorxiv` or `medrxiv`. The server returns metadata and links only;
it does not download article files or open external pages.

## Front-end Contract

Records use the shared `citation` component with:

- DOI, preprint-site, JATS XML, and published-DOI links when present.
- `citation_list`, `table`, `xref_groups`, and optional `text` previews.
- Hover metadata with title, authors, date, version, category, and URL.

## Environment

- `BIORXIV_API_BASE_URL`: override the API base URL.
- `BIORXIV_CONTACT` or `MEDRXIV_CONTACT`: optional contact shown in the user
  agent.
- `BIORXIV_TOOL`: optional tool name for the user agent.

