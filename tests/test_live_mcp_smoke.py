from __future__ import annotations

import importlib
import os
import unittest
from dataclasses import dataclass
from typing import Any

LIVE_SMOKE_ENV = "BIOINFORMATICS_LIVE_MCP_SMOKE"
SERVER_FILTER_ENV = "BIOINFORMATICS_LIVE_MCP_SERVERS"
TIMEOUT_ENV = "BIOINFORMATICS_LIVE_MCP_TIMEOUT"
RETRIES_ENV = "BIOINFORMATICS_LIVE_MCP_RETRIES"


@dataclass(frozen=True)
class LiveSmokeCase:
    server: str
    module: str
    server_class: str
    client_class: str
    config_class: str
    tool_name: str
    arguments: dict[str, Any]
    expected_database: str
    expected_entity_value: str | None = None
    expected_entity_value_prefix: str | None = None
    expected_entity_parameter: str | None = None


LIVE_SMOKE_CASES = [
    LiveSmokeCase(
        server="ncbi",
        module="mcp.ncbi.server",
        server_class="NcbiMcpServer",
        client_class="NcbiClient",
        config_class="NcbiConfig",
        tool_name="ncbi_resolve_context",
        arguments={"context_type": "entities", "database": "gene", "query": "7157[uid]", "max_results": 2},
        expected_database="ncbi",
        expected_entity_value="7157",
    ),
    LiveSmokeCase(
        server="uniprot",
        module="mcp.uniprot.server",
        server_class="UniProtMcpServer",
        client_class="UniProtClient",
        config_class="UniProtConfig",
        tool_name="uniprot_resolve_context",
        arguments={"accession": "P04637", "max_results": 2},
        expected_database="uniprotkb",
        expected_entity_value="P04637",
    ),
    LiveSmokeCase(
        server="string",
        module="mcp.stringdb.server",
        server_class="StringDbMcpServer",
        client_class="StringDbClient",
        config_class="StringDbConfig",
        tool_name="string_resolve_context",
        arguments={"identifiers": ["TP53"], "species": 9606, "limit": 1},
        expected_database="string",
        expected_entity_parameter="identifiers",
    ),
    LiveSmokeCase(
        server="rcsb",
        module="mcp.rcsb.server",
        server_class="RcsbMcpServer",
        client_class="RcsbClient",
        config_class="RcsbConfig",
        tool_name="rcsb_resolve_context",
        arguments={"pdb_id": "1TUP", "max_results": 2},
        expected_database="rcsb_pdb",
        expected_entity_value="1TUP",
    ),
    LiveSmokeCase(
        server="reactome",
        module="mcp.reactome.server",
        server_class="ReactomeMcpServer",
        client_class="ReactomeClient",
        config_class="ReactomeConfig",
        tool_name="reactome_resolve_context",
        arguments={"stable_id": "R-HSA-199420", "max_results": 2},
        expected_database="reactome",
        expected_entity_value="R-HSA-199420",
    ),
    LiveSmokeCase(
        server="quickgo",
        module="mcp.quickgo.server",
        server_class="QuickGoMcpServer",
        client_class="QuickGoClient",
        config_class="QuickGoConfig",
        tool_name="quickgo_resolve_context",
        arguments={"go_id": "GO:0006915", "max_results": 2},
        expected_database="quickgo",
        expected_entity_value="GO:0006915",
    ),
    LiveSmokeCase(
        server="chembl",
        module="mcp.chembl.server",
        server_class="ChemblMcpServer",
        client_class="ChemblClient",
        config_class="ChemblConfig",
        tool_name="chembl_resolve_context",
        arguments={"molecule_chembl_id": "CHEMBL25", "max_results": 2},
        expected_database="chembl",
        expected_entity_value="CHEMBL25",
    ),
    LiveSmokeCase(
        server="ensembl",
        module="mcp.ensembl.server",
        server_class="EnsemblMcpServer",
        client_class="EnsemblClient",
        config_class="EnsemblConfig",
        tool_name="ensembl_resolve_context",
        arguments={"ensembl_id": "ENSG00000141510", "max_results": 2},
        expected_database="ensembl",
        expected_entity_value="ENSG00000141510",
    ),
    LiveSmokeCase(
        server="clinvar",
        module="mcp.clinvar.server",
        server_class="ClinvarMcpServer",
        client_class="ClinvarClient",
        config_class="ClinvarConfig",
        tool_name="clinvar_resolve_context",
        arguments={"identifier": "VCV000037390", "max_results": 2},
        expected_database="clinvar",
        expected_entity_value_prefix="VCV000037390",
    ),
    LiveSmokeCase(
        server="opentargets",
        module="mcp.opentargets.server",
        server_class="OpenTargetsMcpServer",
        client_class="OpenTargetsClient",
        config_class="OpenTargetsConfig",
        tool_name="opentargets_resolve_context",
        arguments={"query": "TP53", "max_results": 2},
        expected_database="opentargets",
        expected_entity_value="ENSG00000141510",
    ),
    LiveSmokeCase(
        server="gwas",
        module="mcp.gwas.server",
        server_class="GwasMcpServer",
        client_class="GwasClient",
        config_class="GwasConfig",
        tool_name="gwas_resolve_context",
        arguments={"rs_id": "rs699", "max_results": 2},
        expected_database="gwas_catalog",
        expected_entity_value="rs699",
    ),
    LiveSmokeCase(
        server="gnomad",
        module="mcp.gnomad.server",
        server_class="GnomadMcpServer",
        client_class="GnomadClient",
        config_class="GnomadConfig",
        tool_name="gnomad_resolve_context",
        arguments={"gene_id": "ENSG00000141510", "max_results": 2},
        expected_database="gnomad",
        expected_entity_value="ENSG00000141510",
    ),
    LiveSmokeCase(
        server="pubchem",
        module="mcp.pubchem.server",
        server_class="PubChemMcpServer",
        client_class="PubChemClient",
        config_class="PubChemConfig",
        tool_name="pubchem_resolve_context",
        arguments={"query": "aspirin", "max_results": 2},
        expected_database="pubchem",
        expected_entity_value="2244",
    ),
    LiveSmokeCase(
        server="chebi",
        module="mcp.chebi.server",
        server_class="ChebiMcpServer",
        client_class="ChebiClient",
        config_class="ChebiConfig",
        tool_name="chebi_resolve_context",
        arguments={"chebi_id": "CHEBI:27732", "max_results": 2},
        expected_database="chebi",
        expected_entity_value="CHEBI:27732",
    ),
    LiveSmokeCase(
        server="cbioportal",
        module="mcp.cbioportal.server",
        server_class="CbioPortalMcpServer",
        client_class="CbioPortalClient",
        config_class="CbioPortalConfig",
        tool_name="cbioportal_resolve_context",
        arguments={"study_id": "brca_tcga", "max_results": 2},
        expected_database="cbioportal",
        expected_entity_value="brca_tcga",
    ),
    LiveSmokeCase(
        server="kegg",
        module="mcp.kegg.server",
        server_class="KeggMcpServer",
        client_class="KeggClient",
        config_class="KeggConfig",
        tool_name="kegg_resolve_context",
        arguments={"context_type": "pathways", "map_id": "hsa04110", "max_results": 2},
        expected_database="kegg",
        expected_entity_value="hsa04110",
    ),
]


def live_smoke_enabled() -> bool:
    return os.environ.get(LIVE_SMOKE_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def selected_servers() -> set[str]:
    raw = os.environ.get(SERVER_FILTER_ENV, "").strip()
    if not raw:
        return {case.server for case in LIVE_SMOKE_CASES}
    return {item.strip().lower() for item in raw.split(",") if item.strip()}


def configured_timeout() -> float:
    return float(os.environ.get(TIMEOUT_ENV, "12"))


def configured_retries() -> int:
    return int(os.environ.get(RETRIES_ENV, "0"))


def is_transient_live_error(exc: BaseException) -> bool:
    message = str(exc).lower()
    markers = (
        "timed out",
        "timeout",
        "could not reach",
        "temporarily unavailable",
        "temporary failure",
        "connection reset",
        "remote end closed",
        "too many requests",
        "http 429",
        "http 502",
        "http 503",
        "http 504",
        "bad gateway",
        "gateway timeout",
        "service unavailable",
    )
    return isinstance(exc, TimeoutError) or any(marker in message for marker in markers)


@unittest.skipUnless(
    live_smoke_enabled(),
    f"set {LIVE_SMOKE_ENV}=1 to run live MCP API smoke tests",
)
class LiveMcpSmokeTests(unittest.TestCase):
    def test_dynamic_context_tools_against_live_apis(self) -> None:
        wanted = selected_servers()
        unknown = wanted - {case.server for case in LIVE_SMOKE_CASES}
        self.assertFalse(
            unknown,
            f"unknown {SERVER_FILTER_ENV} entries: {', '.join(sorted(unknown))}",
        )

        for case in LIVE_SMOKE_CASES:
            if case.server not in wanted:
                continue
            with self.subTest(server=case.server, tool=case.tool_name):
                try:
                    result = self.call_live_tool(case)
                except Exception as exc:
                    if is_transient_live_error(exc):
                        self.skipTest(f"{case.server} live API transient failure: {exc}")
                    raise
                self.assertEqual(result["context_schema_version"], "bioinformatics.dynamic_context.v1")
                self.assertEqual(result["database"], case.expected_database)
                self.assertGreaterEqual(result["returned"], 1)
                entities = result.get("entities")
                self.assertIsInstance(entities, list)
                self.assertTrue(entities, "live context result should expose at least one entity")
                values = {str(entity.get("value")) for entity in entities if isinstance(entity, dict)}
                if case.expected_entity_value is not None:
                    self.assertIn(case.expected_entity_value, values)
                if case.expected_entity_value_prefix is not None:
                    self.assertTrue(
                        any(value.startswith(case.expected_entity_value_prefix) for value in values),
                        f"expected an entity value starting with {case.expected_entity_value_prefix!r}, got {sorted(values)!r}",
                    )
                if case.expected_entity_parameter is not None:
                    parameter_names = {
                        str(entity.get("parameter_name"))
                        for entity in entities
                        if isinstance(entity, dict)
                    }
                    self.assertIn(case.expected_entity_parameter, parameter_names)
                urls = [entity.get("url") for entity in entities if isinstance(entity, dict)]
                self.assertTrue(
                    any(isinstance(url, str) and url.startswith(("http://", "https://")) for url in urls),
                    "entity summaries should preserve real browser/API URLs",
                )
                self.assertTrue(result.get("recommended_calls"), "live context result should recommend next MCP calls")

    def call_live_tool(self, case: LiveSmokeCase) -> dict[str, Any]:
        module = importlib.import_module(case.module)
        config = getattr(module, case.config_class).from_env()
        config.timeout_seconds = configured_timeout()
        config.max_retries = configured_retries()
        client = getattr(module, case.client_class)(config)
        server = getattr(module, case.server_class)(client)
        response = server.handle(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": case.tool_name,
                    "arguments": case.arguments,
                },
            }
        )
        assert response is not None
        return response["result"]["structuredContent"]


if __name__ == "__main__":
    unittest.main()
