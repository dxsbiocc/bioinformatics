from __future__ import annotations

import json
import pathlib
import sys
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from frontend_contract_assertions import KNOWN_COMPONENTS, KNOWN_PREVIEW_KINDS


class FrontendContractFilesTests(unittest.TestCase):
    def test_record_schema_is_valid_json_and_names_core_shapes(self) -> None:
        schema_path = ROOT / "schemas" / "record.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$id"],
            "https://codex.local/bioinformatics/schemas/record.schema.json",
        )
        self.assertIn("record", schema["$defs"])
        self.assertIn("display", schema["$defs"])
        self.assertIn("citation", schema["$defs"])
        self.assertIn("displaySection", schema["$defs"])
        self.assertIn("preview", schema["$defs"])
        self.assertIn("stable_id", schema["$defs"]["record"]["required"])
        self.assertIn("display", schema["$defs"]["record"]["required"])
        self.assertIn("previews", schema["$defs"]["display"]["properties"])

    def test_dynamic_context_schema_is_valid_json_and_names_core_shapes(self) -> None:
        schema_path = ROOT / "schemas" / "dynamic-context.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["$id"],
            "https://codex.local/bioinformatics/schemas/dynamic-context.schema.json",
        )
        self.assertIn("context", schema["$defs"])
        self.assertIn("contextSummary", schema["$defs"])
        self.assertIn("recommendedCall", schema["$defs"])
        self.assertIn("diagnostic", schema["$defs"])
        self.assertIn("context_schema_version", schema["required"])
        self.assertEqual(
            schema["properties"]["context_schema_version"]["const"],
            "bioinformatics.dynamic_context.v1",
        )
        self.assertIn("contexts", schema["required"])
        self.assertIn("recommended_calls", schema["required"])

    def test_types_export_record_contract_helpers_and_known_components(self) -> None:
        types_path = ROOT / "types" / "record.ts"
        content = types_path.read_text(encoding="utf-8")
        for name in [
            "BioinformaticsRecord",
            "BioinformaticsResultEnvelope",
            "BioinformaticsDynamicContextResult",
            "BioinformaticsDynamicContext",
            "BioinformaticsRecommendedCall",
            "BioinformaticsDisplaySection",
            "BioinformaticsPreview",
            "BioinformaticsPreviewKind",
            "getBioinformaticsRecords",
            "getBioinformaticsDynamicContexts",
            "getDynamicContextEntities",
            "getDynamicContextRecommendedCalls",
            "getDynamicContextPrimaryUrl",
            "getRecordPrimaryUrl",
            "isSafeExternalUrl",
        ]:
            self.assertIn(name, content)
        for component in sorted(KNOWN_COMPONENTS):
            self.assertIn(f'"{component}"', content)

    def test_rendering_docs_point_to_schema_and_types(self) -> None:
        docs_path = ROOT / "docs" / "frontend-record-rendering.md"
        content = docs_path.read_text(encoding="utf-8")
        self.assertIn("schemas/record.schema.json", content)
        self.assertIn("schemas/dynamic-context.schema.json", content)
        self.assertIn("types/record.ts", content)
        self.assertIn("structuredContent.records", content)
        self.assertIn("structuredContent.contexts", content)
        self.assertIn("recommended_calls", content)
        self.assertIn("display.primary_url", content)
        self.assertIn("display.sections", content)
        self.assertIn("display.previews", content)
        self.assertIn("protein", content)

    def test_known_components_and_preview_kinds_are_documented(self) -> None:
        schema = json.loads((ROOT / "schemas" / "record.schema.json").read_text(encoding="utf-8"))
        schema_text = json.dumps(schema, sort_keys=True)
        docs = (ROOT / "docs" / "frontend-record-rendering.md").read_text(encoding="utf-8")
        types = (ROOT / "types" / "record.ts").read_text(encoding="utf-8")

        for component in sorted(KNOWN_COMPONENTS):
            self.assertIn(component, schema_text)
            self.assertIn(f"`{component}`", docs)
            self.assertIn(f'"{component}"', types)
        for preview_kind in sorted(KNOWN_PREVIEW_KINDS):
            self.assertIn(preview_kind, schema_text)
            self.assertIn(f"`{preview_kind}`", docs)
            self.assertIn(f'"{preview_kind}"', types)

    def test_frontend_fixture_records_cover_core_ncbi_components(self) -> None:
        fixture_path = ROOT / "fixtures" / "frontend" / "ncbi" / "core-records.json"
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        records = payload["records"]
        components = {record["display"]["component"] for record in records}
        record_types = {record["record_type"] for record in records}
        for component in [
            "citation",
            "download_plan",
            "sample_sheet",
            "runtime_status",
        ]:
            self.assertIn(component, components)
        self.assertIn("geo_download_plan", record_types)
        self.assertIn("sra_download_plan_item", record_types)
        for record in records:
            self.assertIn("schema_version", record)
            self.assertIn("stable_id", record)
            self.assertIn("display", record)
            self.assertIn("hover", record["display"])
            self.assertIn("actions", record["display"])
            self.assertIn("previews", record["display"])

    def test_ncbi_baseline_docs_and_examples_are_present(self) -> None:
        for path in [
            ROOT / "CHANGELOG.md",
            ROOT / "docs" / "ncbi-mcp-operations.md",
            ROOT / "examples" / "ncbi" / "README.md",
        ]:
            content = path.read_text(encoding="utf-8")
            self.assertIn("NCBI", content)
        examples = (ROOT / "examples" / "ncbi" / "README.md").read_text(encoding="utf-8")
        self.assertIn("geo_download_plan", examples)
        self.assertIn("sra_download_plan", examples)
        self.assertIn("omics_sample_sheet", examples)
        self.assertIn("tool_runtime_status", examples)

    def test_dependency_free_frontend_preview_is_not_packaged(self) -> None:
        for path in [
            ROOT / "frontend" / "ncbi-record-preview.html",
            ROOT / "frontend" / "ncbi-record-preview.js",
            ROOT / "frontend" / "record-consumer.js",
            ROOT / "frontend" / "ncbi-record-preview.css",
            ROOT / "frontend" / "package.json",
        ]:
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
