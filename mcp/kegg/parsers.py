"""Parsers for KEGG REST text formats."""

from __future__ import annotations

from .constants import JsonObject
from .utils import normalize_space, unique_texts


def parse_tsv(text: str) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        rows.append([cell.strip() for cell in line.split("\t")])
    return rows


def tsv_records(text: str, *, kind: str = "") -> list[JsonObject]:
    rows = parse_tsv(text)
    records: list[JsonObject] = []
    for row in rows:
        if kind == "organism" and len(row) >= 4:
            records.append(
                {
                    "entry_id": row[0],
                    "code": row[1],
                    "description": row[2],
                    "lineage": row[3],
                    "columns": row,
                }
            )
            continue
        if len(row) >= 2:
            records.append({"entry_id": row[0], "description": row[1], "columns": row})
        elif row:
            records.append({"entry_id": row[0], "description": "", "columns": row})
    return records


def parse_link_rows(text: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for cells in parse_tsv(text):
        if len(cells) < 2:
            continue
        rows.append({"source": cells[0], "target": cells[1], "columns": cells})
    return rows


def parse_flat_records(text: str) -> list[JsonObject]:
    records: list[JsonObject] = []
    current: JsonObject = {}
    current_field = ""
    raw_lines: list[str] = []
    for line in text.splitlines():
        if line.strip() == "///":
            if current or raw_lines:
                current["raw_text"] = "\n".join(raw_lines)
                records.append(normalize_flat_record(current))
            current = {}
            current_field = ""
            raw_lines = []
            continue
        if not line.strip():
            continue
        raw_lines.append(line)
        field = line[:12].strip()
        value = line[12:].rstrip()
        if field:
            current_field = field
            current.setdefault(field, []).append(value.strip())
        elif current_field:
            current.setdefault(current_field, []).append(value.strip())
    if current or raw_lines:
        current["raw_text"] = "\n".join(raw_lines)
        records.append(normalize_flat_record(current))
    return records


def normalize_flat_record(record: JsonObject) -> JsonObject:
    entry_line = first_field(record, "ENTRY")
    entry_parts = entry_line.split()
    entry_id = entry_parts[0] if entry_parts else ""
    entry_class = " ".join(entry_parts[1:]) if len(entry_parts) > 1 else ""
    names = parse_names(field_values(record, "NAME"))
    return {
        "entry_id": entry_id,
        "entry_class": entry_class,
        "names": names,
        "name": names[0] if names else "",
        "description": first_field(record, "DESCRIPTION"),
        "definition": first_field(record, "DEFINITION"),
        "organism": first_field(record, "ORGANISM"),
        "module": parse_id_label_lines(field_values(record, "MODULE")),
        "pathways": parse_id_label_lines(field_values(record, "PATHWAY")),
        "orthology": parse_id_label_lines(field_values(record, "ORTHOLOGY")),
        "diseases": parse_id_label_lines(field_values(record, "DISEASE")),
        "drugs": parse_id_label_lines(field_values(record, "DRUG")),
        "compounds": parse_id_label_lines(field_values(record, "COMPOUND")),
        "reactions": parse_id_label_lines(field_values(record, "REACTION")),
        "genes": parse_gene_lines(field_values(record, "GENE") or field_values(record, "GENES")),
        "dblinks": parse_dblinks(field_values(record, "DBLINKS")),
        "authors": field_values(record, "AUTHORS"),
        "journal": first_field(record, "JOURNAL"),
        "sequence": parse_sequence_block(field_values(record, "AASEQ") or field_values(record, "NTSEQ")),
        "fields": {key: value for key, value in record.items() if isinstance(value, list)},
        "raw_text": normalize_space(record.get("raw_text")),
    }


def parse_fasta(text: str) -> list[JsonObject]:
    records: list[JsonObject] = []
    header = ""
    chunks: list[str] = []
    for line in text.splitlines():
        if line.startswith(">"):
            if header or chunks:
                records.append(fasta_record(header, chunks))
            header = line[1:].strip()
            chunks = []
            continue
        if line.strip():
            chunks.append(line.strip())
    if header or chunks:
        records.append(fasta_record(header, chunks))
    return records


def fasta_record(header: str, chunks: list[str]) -> JsonObject:
    identifier = header.split()[0] if header else ""
    return {
        "entry_id": identifier,
        "header": header,
        "description": " ".join(header.split()[1:]) if header else "",
        "sequence": "".join(chunks),
    }


def field_values(record: JsonObject, field: str) -> list[str]:
    value = record.get(field)
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def first_field(record: JsonObject, field: str) -> str:
    values = field_values(record, field)
    return values[0] if values else ""


def parse_names(values: list[str]) -> list[str]:
    names: list[str] = []
    for value in values:
        for part in value.split(";"):
            text = normalize_space(part.strip(", "))
            if text:
                names.append(text)
    return unique_texts(names)


def parse_id_label_lines(values: list[str]) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for value in values:
        text = normalize_space(value)
        if not text:
            continue
        parts = text.split(maxsplit=1)
        entry_id = parts[0]
        label = parts[1] if len(parts) > 1 else ""
        rows.append({"id": entry_id, "label": label})
    return rows


def parse_gene_lines(values: list[str]) -> list[JsonObject]:
    rows: list[JsonObject] = []
    current_species = ""
    for value in values:
        text = normalize_space(value)
        if not text:
            continue
        if ":" in text and text.split(":", 1)[0].replace(".", "").isalnum():
            species, rest = text.split(":", 1)
            current_species = species
            gene_text = rest.strip()
        else:
            gene_text = text
        for chunk in gene_text.split(";"):
            chunk = normalize_space(chunk)
            if not chunk:
                continue
            parts = chunk.split(maxsplit=1)
            gene_id = parts[0].strip(",")
            label = parts[1].strip(",") if len(parts) > 1 else ""
            rows.append({"species": current_species, "id": gene_id, "label": label})
    return rows


def parse_dblinks(values: list[str]) -> list[JsonObject]:
    groups: list[JsonObject] = []
    current: JsonObject | None = None
    for value in values:
        text = normalize_space(value)
        if not text:
            continue
        if ":" in text:
            database, identifiers = text.split(":", 1)
            current = {"database": database.strip(), "items": []}
            groups.append(current)
            add_dblink_items(current, identifiers)
        elif current is not None:
            add_dblink_items(current, text)
    return groups


def add_dblink_items(group: JsonObject, text: str) -> None:
    items = group.setdefault("items", [])
    if not isinstance(items, list):
        return
    for item in text.split():
        identifier = normalize_space(item.strip(",;"))
        if identifier:
            items.append({"id": identifier, "label": identifier})


def parse_sequence_block(values: list[str]) -> JsonObject:
    if not values:
        return {}
    header = values[0]
    chunks = values[1:]
    return {
        "header": header,
        "sequence": "".join(part.replace(" ", "") for part in chunks),
    }

