from __future__ import annotations

import re
from typing import Any
from unittest import TestCase

SAFE_HTTP_URL = re.compile(r"^https?://", re.IGNORECASE)
RENDERABLE_SCALAR_TYPES = (str, int, float, bool)

KNOWN_COMPONENTS = {
    "citation",
    "dataset",
    "compound",
    "protein",
    "protein_structure",
    "protein_network",
    "pathway",
    "ontology_term",
    "gene",
    "genomic_feature",
    "variant",
    "taxonomy",
    "identifier_conversion",
    "database",
    "linkset",
    "project",
    "sample",
    "run",
    "download_plan",
    "sample_sheet",
    "runtime_status",
}

KNOWN_PREVIEW_KINDS = {
    "sequence",
    "feature_track",
    "structure_3d",
    "chemical_structure",
    "network",
    "survival_curve",
    "heatmap_matrix",
    "citation_list",
    "xref_groups",
    "download_manifest",
    "table",
    "text",
}


def assert_result_frontend_contract(
    testcase: TestCase,
    result: dict[str, Any],
    *,
    expected_components: set[str] | None = None,
    required_preview_kinds: set[str] | None = None,
    min_records: int = 1,
) -> None:
    """Assert the shared MCP record contract front-end renderers rely on."""
    testcase.assertIsInstance(result.get("schema_version"), str)
    records = result.get("records")
    testcase.assertIsInstance(records, list)
    testcase.assertGreaterEqual(len(records), min_records)

    components: set[str] = set()
    preview_kinds: set[str] = set()
    for record in records:
        assert_record_frontend_contract(testcase, record)
        components.add(record["display"]["component"])
        preview_kinds.update(preview["kind"] for preview in record["display"]["previews"])

    if expected_components is not None:
        testcase.assertTrue(
            expected_components.issubset(components),
            f"missing components: {expected_components - components}",
        )
    if required_preview_kinds is not None:
        testcase.assertTrue(
            required_preview_kinds.issubset(preview_kinds),
            f"missing preview kinds: {required_preview_kinds - preview_kinds}",
        )


def assert_record_frontend_contract(testcase: TestCase, record: dict[str, Any]) -> None:
    for key in [
        "schema_version",
        "type",
        "record_type",
        "database",
        "id",
        "stable_id",
        "label",
        "title",
        "url",
        "icon",
        "display",
    ]:
        testcase.assertIn(key, record)
    assert_non_empty_string(testcase, record["schema_version"], "record.schema_version")
    assert_non_empty_string(testcase, record["type"], "record.type")
    assert_non_empty_string(testcase, record["record_type"], "record.record_type")
    assert_non_empty_string(testcase, record["database"], "record.database")
    assert_non_empty_string(testcase, record["id"], "record.id")
    assert_non_empty_string(testcase, record["stable_id"], "record.stable_id")
    assert_non_empty_string(testcase, record["label"], "record.label")
    assert_non_empty_string(testcase, record["title"], "record.title")
    assert_safe_url(testcase, record["url"], "record.url")
    assert_non_empty_string(testcase, record["icon"], "record.icon")

    if "identifiers" in record:
        assert_identifiers_contract(testcase, record["identifiers"], "record.identifiers")
    if "links" in record:
        testcase.assertIsInstance(record["links"], list, "record.links")
        for index, link in enumerate(record["links"]):
            assert_action_contract(testcase, link, f"record.links[{index}]")

    display = record["display"]
    testcase.assertIsInstance(display, dict)
    for key in [
        "component",
        "chip_label",
        "icon",
        "title",
        "metadata",
        "badges",
        "actions",
        "hover",
        "primary_url",
        "previews",
    ]:
        testcase.assertIn(key, display)
    assert_non_empty_string(testcase, display["component"], "display.component")
    testcase.assertIn(display["component"], KNOWN_COMPONENTS)
    assert_non_empty_string(testcase, display["chip_label"], "display.chip_label")
    assert_non_empty_string(testcase, display["icon"], "display.icon")
    assert_non_empty_string(testcase, display["title"], "display.title")
    assert_safe_url(testcase, display["primary_url"], "display.primary_url")
    testcase.assertIsInstance(display["metadata"], list)
    for index, field in enumerate(display["metadata"]):
        assert_display_field_contract(testcase, field, f"display.metadata[{index}]")
    testcase.assertIsInstance(display["badges"], list)
    for index, badge in enumerate(display["badges"]):
        assert_badge_contract(testcase, badge, f"display.badges[{index}]")

    actions = display["actions"]
    testcase.assertIsInstance(actions, list)
    testcase.assertGreater(
        len(actions),
        0,
        "display.actions must expose at least one clickable target",
    )
    for index, action in enumerate(actions):
        assert_action_contract(testcase, action, f"display.actions[{index}]")

    hover = display["hover"]
    testcase.assertIsInstance(hover, dict)
    assert_non_empty_string(testcase, hover.get("title"), "display.hover.title")
    testcase.assertIsInstance(hover.get("fields"), list)
    for index, field in enumerate(hover.get("fields", [])):
        assert_display_field_contract(testcase, field, f"display.hover.fields[{index}]")

    if "sections" in display:
        assert_sections_contract(testcase, display["sections"], "display.sections")

    previews = display["previews"]
    testcase.assertIsInstance(previews, list)
    testcase.assertGreater(
        len(previews),
        0,
        "display.previews must include at least one renderer hint",
    )
    for index, preview in enumerate(previews):
        assert_preview_contract(testcase, preview, f"display.previews[{index}]")


def assert_action_contract(
    testcase: TestCase,
    action: dict[str, Any],
    label: str,
) -> None:
    testcase.assertIsInstance(action, dict)
    assert_non_empty_string(testcase, action.get("label"), f"{label}.label")
    assert_safe_url(testcase, action.get("url"), f"{label}.url")


def assert_display_field_contract(
    testcase: TestCase,
    field: dict[str, Any],
    label: str,
) -> None:
    testcase.assertIsInstance(field, dict, label)
    assert_non_empty_string(testcase, field.get("label"), f"{label}.label")
    testcase.assertIn("value", field, f"{label}.value")
    assert_renderable_scalar(testcase, field.get("value"), f"{label}.value")


def assert_badge_contract(
    testcase: TestCase,
    badge: dict[str, Any],
    label: str,
) -> None:
    testcase.assertIsInstance(badge, dict, label)
    assert_non_empty_string(testcase, badge.get("label"), f"{label}.label")
    assert_non_empty_string(testcase, badge.get("kind"), f"{label}.kind")


def assert_identifiers_contract(
    testcase: TestCase,
    identifiers: Any,
    label: str,
) -> None:
    testcase.assertIsInstance(identifiers, dict, label)
    for key, value in identifiers.items():
        assert_non_empty_string(testcase, key, f"{label} key")
        values = value if isinstance(value, list) else [value]
        testcase.assertIsInstance(values, list, f"{label}.{key}")
        for index, identifier in enumerate(values):
            item_label = f"{label}.{key}[{index}]"
            testcase.assertIsInstance(identifier, dict, item_label)
            assert_non_empty_string(testcase, identifier.get("namespace"), f"{item_label}.namespace")
            assert_non_empty_string(testcase, identifier.get("id"), f"{item_label}.id")
            assert_non_empty_string(testcase, identifier.get("label"), f"{item_label}.label")
            assert_optional_safe_url(testcase, identifier.get("url"), f"{item_label}.url")


def assert_sections_contract(
    testcase: TestCase,
    sections: Any,
    label: str,
) -> None:
    testcase.assertIsInstance(sections, list, label)
    for index, section in enumerate(sections):
        section_label = f"{label}[{index}]"
        testcase.assertIsInstance(section, dict, section_label)
        assert_non_empty_string(testcase, section.get("key"), f"{section_label}.key")
        assert_non_empty_string(testcase, section.get("title"), f"{section_label}.title")
        if section.get("kind") is not None:
            assert_non_empty_string(testcase, section.get("kind"), f"{section_label}.kind")
        for field_index, field in enumerate(section.get("fields", [])):
            assert_display_field_contract(testcase, field, f"{section_label}.fields[{field_index}]")
        for rows_key in ["rows", "items", "groups", "tracks"]:
            if rows_key in section:
                testcase.assertIsInstance(section[rows_key], list, f"{section_label}.{rows_key}")
        if "summary" in section:
            testcase.assertIsInstance(section["summary"], dict, f"{section_label}.summary")
        if "text" in section:
            testcase.assertIsInstance(section["text"], str, f"{section_label}.text")


def assert_preview_contract(
    testcase: TestCase,
    preview: dict[str, Any],
    label: str,
) -> None:
    testcase.assertIsInstance(preview, dict)
    assert_non_empty_string(testcase, preview.get("kind"), f"{label}.kind")
    testcase.assertIn(preview["kind"], KNOWN_PREVIEW_KINDS, f"{label}.kind")
    assert_non_empty_string(testcase, preview.get("title"), f"{label}.title")
    if preview.get("url"):
        assert_safe_url(testcase, preview.get("url"), f"{label}.url")
    for index, action in enumerate(preview.get("actions", [])):
        assert_action_contract(testcase, action, f"{label}.actions[{index}]")

    data = preview.get("data")
    if data is not None:
        testcase.assertIsInstance(data, dict)
    if preview["kind"] == "network":
        testcase.assertIsInstance(data, dict)
        testcase.assertIsInstance(data.get("nodes"), list)
        testcase.assertIsInstance(data.get("edges"), list)
        assert_network_items_contract(testcase, data.get("nodes", []), f"{label}.data.nodes")
        assert_network_items_contract(testcase, data.get("edges", []), f"{label}.data.edges")
    if preview["kind"] == "structure_3d":
        testcase.assertTrue(
            preview.get("url") or data,
            f"{label} must include a URL or provider-specific structure data",
        )
    if preview["kind"] == "sequence":
        testcase.assertIsInstance(data, dict)
        testcase.assertIn("alphabet", data)
        assert_non_empty_string(testcase, data.get("alphabet"), f"{label}.data.alphabet")
    if preview["kind"] == "table":
        testcase.assertIsInstance(data, dict)
        testcase.assertIn("rows", data)
        testcase.assertIsInstance(data.get("rows"), list)
        if "columns" in data:
            assert_columns_contract(testcase, data["columns"], f"{label}.data.columns")
    if preview["kind"] == "feature_track":
        testcase.assertIsInstance(data, dict)
        testcase.assertTrue(
            any(key in data for key in ["summary", "tracks", "rows"]),
            f"{label}.data must include summary, tracks, or rows",
        )
        if "summary" in data:
            testcase.assertIsInstance(data["summary"], dict, f"{label}.data.summary")
        for key in ["tracks", "rows"]:
            if key in data:
                testcase.assertIsInstance(data[key], list, f"{label}.data.{key}")
    if preview["kind"] == "chemical_structure":
        testcase.assertIsInstance(data, dict)
        testcase.assertTrue(
            preview.get("url")
            or any(
                data.get(key)
                for key in [
                    "smiles",
                    "canonical_smiles",
                    "isomeric_smiles",
                    "inchi",
                    "inchi_key",
                    "image_url",
                    "svg_url",
                    "molfile",
                    "cid",
                    "chembl_id",
                ]
            ),
            f"{label} must include a URL or chemical structure identifiers",
        )
    if preview["kind"] == "citation_list":
        testcase.assertIsInstance(data, dict)
        testcase.assertTrue(
            any(key in data for key in ["pubmed_ids", "citations", "references", "items", "publications"]),
            f"{label}.data must include pubmed_ids, citations, references, items, or publications",
        )
        for key in ["pubmed_ids", "citations", "references", "items", "publications"]:
            if key in data:
                testcase.assertIsInstance(data[key], list, f"{label}.data.{key}")
    if preview["kind"] == "xref_groups":
        testcase.assertIsInstance(data, dict)
        testcase.assertIn("groups", data)
        assert_xref_groups_contract(testcase, data.get("groups"), f"{label}.data.groups")
    if preview["kind"] == "download_manifest":
        testcase.assertIsInstance(data, dict)
        testcase.assertTrue(
            any(key in data for key in ["links", "files", "rows", "commands", "samples"]),
            f"{label}.data must include links, files, rows, commands, or samples",
        )
        for key in ["links", "files", "rows", "samples"]:
            if key in data:
                testcase.assertIsInstance(data[key], list, f"{label}.data.{key}")
        if "commands" in data:
            testcase.assertIsInstance(data["commands"], dict, f"{label}.data.commands")
    if preview["kind"] == "survival_curve":
        testcase.assertIsInstance(data, dict)
        testcase.assertIn("rows", data)
        testcase.assertIsInstance(data.get("rows"), list)
    if preview["kind"] == "heatmap_matrix":
        testcase.assertIsInstance(data, dict)
        testcase.assertIn("rows", data)
        testcase.assertIsInstance(data.get("rows"), list)
        for key in ["columns", "column_ids"]:
            if key in data:
                testcase.assertIsInstance(data[key], list, f"{label}.data.{key}")
        if "row_id" in data:
            assert_non_empty_string(testcase, data.get("row_id"), f"{label}.data.row_id")
        if "value_key" in data:
            assert_non_empty_string(testcase, data.get("value_key"), f"{label}.data.value_key")
    if preview["kind"] == "text" and data is not None and "text" in data:
        assert_renderable_scalar(testcase, data["text"], f"{label}.data.text")


def assert_columns_contract(testcase: TestCase, columns: Any, label: str) -> None:
    testcase.assertIsInstance(columns, list, label)
    for index, column in enumerate(columns):
        item_label = f"{label}[{index}]"
        if isinstance(column, str):
            assert_non_empty_string(testcase, column, item_label)
        else:
            testcase.assertIsInstance(column, dict, item_label)
            testcase.assertTrue(
                column.get("key") or column.get("label"),
                f"{item_label} must include key or label",
            )


def assert_xref_groups_contract(testcase: TestCase, groups: Any, label: str) -> None:
    testcase.assertIsInstance(groups, list, label)
    for group_index, group in enumerate(groups):
        group_label = f"{label}[{group_index}]"
        testcase.assertIsInstance(group, dict, group_label)
        testcase.assertTrue(
            group.get("database") or group.get("source") or group.get("label") or group.get("name"),
            f"{group_label} must include database, source, label, or name",
        )
        items = group.get("items", [])
        testcase.assertIsInstance(items, list, f"{group_label}.items")
        for item_index, item in enumerate(items):
            item_label = f"{group_label}.items[{item_index}]"
            if isinstance(item, str):
                assert_non_empty_string(testcase, item, item_label)
                continue
            testcase.assertIsInstance(item, dict, item_label)
            testcase.assertTrue(
                item.get("id") or item.get("label") or item.get("url"),
                f"{item_label} must include id, label, or url",
            )
            assert_optional_safe_url(testcase, item.get("url"), f"{item_label}.url")


def assert_network_items_contract(testcase: TestCase, items: Any, label: str) -> None:
    testcase.assertIsInstance(items, list, label)
    for index, item in enumerate(items):
        item_label = f"{label}[{index}]"
        testcase.assertIsInstance(item, dict, item_label)
        testcase.assertTrue(
            item.get("id") or item.get("source") or item.get("target"),
            f"{item_label} must include id or source/target",
        )


def assert_non_empty_string(
    testcase: TestCase,
    value: Any,
    label: str,
) -> None:
    testcase.assertIsInstance(value, str, label)
    testcase.assertTrue(value.strip(), f"{label} must be non-empty")


def assert_renderable_scalar(testcase: TestCase, value: Any, label: str) -> None:
    testcase.assertIsInstance(value, RENDERABLE_SCALAR_TYPES, label)
    if isinstance(value, str):
        testcase.assertTrue(value.strip(), f"{label} must be non-empty")


def assert_optional_safe_url(testcase: TestCase, value: Any, label: str) -> None:
    if value in (None, ""):
        return
    assert_safe_url(testcase, value, label)


def assert_safe_url(testcase: TestCase, value: Any, label: str) -> None:
    testcase.assertIsInstance(value, str, label)
    testcase.assertRegex(value, SAFE_HTTP_URL, f"{label} must be http(s)")
