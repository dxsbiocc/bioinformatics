"""Front-end record envelopes for omics project, sample, and run metadata."""

from __future__ import annotations

from .constants import RECORD_SCHEMA_VERSION, RESULT_SCHEMA_VERSION, JsonObject
from .previews import with_ncbi_previews
from .records import (
    bioproject_url,
    biosample_url,
    sra_run_browser_url,
    sra_run_selector_url,
    sra_url,
    taxonomy_url,
)
from .schemas import compact_badges, compact_fields, display_actions, geo_accession_url
from .utils import normalize_space


def with_bioproject_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    projects = response.get("projects")
    records = []
    if isinstance(projects, list):
        records = [
            bioproject_record(project)
            for project in projects
            if isinstance(project, dict)
        ]
    response.setdefault("records", records)
    return response


def bioproject_record(project: JsonObject) -> JsonObject:
    accession = normalize_space(project.get("accession"))
    project_id = normalize_space(project.get("project_id") or project.get("uid"))
    stable_id = accession or f"BioProject:{project_id}"
    title = normalize_space(project.get("title") or project.get("name") or stable_id)
    organism = project.get("organism") if isinstance(project.get("organism"), dict) else {}
    organism_name = normalize_space(organism.get("scientific_name"))
    links = bioproject_links(project)
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.project",
        "record_type": "ncbi_bioproject",
        "database": "bioproject",
        "id": accession or project_id,
        "uid": normalize_space(project.get("uid")),
        "stable_id": stable_id,
        "label": stable_id,
        "title": title,
        "description": normalize_space(project.get("description")),
        "url": bioproject_url(accession or project_id),
        "icon": "bioproject",
        "identifiers": bioproject_identifiers(project),
        "links": links,
        "display": {
            "component": "project",
            "chip_label": stable_id,
            "icon": "bioproject",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    normalize_space(project.get("data_type")),
                    organism_name,
                    normalize_space(project.get("sequencing_status")),
                ]
                if part
            ),
            "description": normalize_space(project.get("description")),
            "metadata": bioproject_display_metadata(project),
            "badges": compact_badges(
                ("NCBI BioProject", "source"),
                (stable_id, "identifier"),
                (normalize_space(project.get("data_type")), "record_type"),
                (organism_name, "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": organism_name,
                "icon": "bioproject",
                "fields": compact_fields(
                    ("BioProject", stable_id),
                    ("Project ID", project_id),
                    ("Organism", organism_name),
                    ("TaxID", normalize_space(organism.get("taxid"))),
                    ("Data type", normalize_space(project.get("data_type"))),
                    ("Method", normalize_space(project.get("method_type"))),
                    ("Registered", normalize_space(project.get("registration_date"))),
                    ("URL", bioproject_url(accession or project_id)),
                ),
            },
            "primary_url": bioproject_url(accession or project_id),
        },
        "related": bioproject_related(project),
        "data": project,
    })


def bioproject_identifiers(project: JsonObject) -> JsonObject:
    accession = normalize_space(project.get("accession"))
    project_id = normalize_space(project.get("project_id") or project.get("uid"))
    organism = project.get("organism") if isinstance(project.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    identifiers: JsonObject = {}
    if accession or project_id:
        identifiers["bioproject"] = {
            "namespace": "bioproject",
            "id": accession or project_id,
            "label": accession or f"BioProject:{project_id}",
            "url": bioproject_url(accession or project_id),
        }
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "url": taxonomy_url(taxid),
        }
    return identifiers


def bioproject_links(project: JsonObject) -> list[JsonObject]:
    accession = normalize_space(project.get("accession"))
    project_id = normalize_space(project.get("project_id") or project.get("uid"))
    organism = project.get("organism") if isinstance(project.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    links: list[JsonObject] = []
    if accession or project_id:
        links.append(
            {
                "label": "BioProject",
                "url": bioproject_url(accession or project_id),
                "kind": "external",
                "primary": True,
            }
        )
        links.append(
            {
                "label": "SRA Run Selector",
                "url": sra_run_selector_url(accession or project_id),
                "kind": "external",
                "primary": False,
            }
        )
    if taxid:
        links.append(
            {
                "label": f"Taxonomy {taxid}",
                "url": taxonomy_url(taxid),
                "kind": "external",
                "primary": False,
            }
        )
    return unique_links(links)


def bioproject_display_metadata(project: JsonObject) -> list[JsonObject]:
    organism = project.get("organism") if isinstance(project.get("organism"), dict) else {}
    return compact_fields(
        ("BioProject", normalize_space(project.get("accession"))),
        ("Project ID", normalize_space(project.get("project_id") or project.get("uid"))),
        ("Title", normalize_space(project.get("title"))),
        ("Organism", normalize_space(organism.get("scientific_name"))),
        ("TaxID", normalize_space(organism.get("taxid"))),
        ("Data type", normalize_space(project.get("data_type"))),
        ("Project type", normalize_space(project.get("project_type"))),
        ("Scope", normalize_space(project.get("target_scope"))),
        ("Method", normalize_space(project.get("method_type"))),
        ("Sequencing status", normalize_space(project.get("sequencing_status"))),
        ("Registered", normalize_space(project.get("registration_date"))),
        ("Submitter", normalize_space(project.get("submitter_organization"))),
    )


def bioproject_related(project: JsonObject) -> JsonObject:
    organism = project.get("organism") if isinstance(project.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    related: JsonObject = {}
    if taxid:
        related["taxonomy"] = {
            "type": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "title": normalize_space(organism.get("scientific_name")),
            "url": taxonomy_url(taxid),
        }
    accession = normalize_space(project.get("accession"))
    if accession:
        related["sra_run_selector"] = {
            "type": "sra_run_selector",
            "id": accession,
            "label": "SRA Run Selector",
            "url": sra_run_selector_url(accession),
        }
    return related


def with_biosample_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    samples = response.get("samples")
    records = []
    if isinstance(samples, list):
        records = [
            biosample_record(sample)
            for sample in samples
            if isinstance(sample, dict)
        ]
    response.setdefault("records", records)
    return response


def biosample_record(sample: JsonObject) -> JsonObject:
    accession = normalize_space(sample.get("accession"))
    uid = normalize_space(sample.get("uid"))
    stable_id = accession or f"BioSample:{uid}"
    title = normalize_space(sample.get("title") or stable_id)
    organism = sample.get("organism") if isinstance(sample.get("organism"), dict) else {}
    organism_name = normalize_space(organism.get("scientific_name"))
    links = biosample_links(sample)
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.sample",
        "record_type": "ncbi_biosample",
        "database": "biosample",
        "id": accession or uid,
        "uid": uid,
        "stable_id": stable_id,
        "label": stable_id,
        "title": title,
        "description": organism_name,
        "url": biosample_url(accession or uid),
        "icon": "biosample",
        "identifiers": biosample_identifiers(sample),
        "links": links,
        "display": {
            "component": "sample",
            "chip_label": stable_id,
            "icon": "biosample",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    organism_name,
                    first_attribute_value(sample, ["tissue", "source_name", "disease"]),
                ]
                if part
            ),
            "description": first_attribute_value(
                sample,
                ["description", "source_name", "tissue", "disease"],
            ),
            "metadata": biosample_display_metadata(sample),
            "badges": compact_badges(
                ("NCBI BioSample", "source"),
                (stable_id, "identifier"),
                (organism_name, "context"),
                (normalize_space(sample.get("package")), "record_type"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": organism_name,
                "icon": "biosample",
                "fields": compact_fields(
                    ("BioSample", stable_id),
                    ("Organism", organism_name),
                    ("TaxID", normalize_space(organism.get("taxid"))),
                    ("Package", normalize_space(sample.get("package"))),
                    ("Organization", normalize_space(sample.get("organization"))),
                    ("Publication date", normalize_space(sample.get("publication_date"))),
                    ("URL", biosample_url(accession or uid)),
                ),
            },
            "primary_url": biosample_url(accession or uid),
        },
        "related": biosample_related(sample),
        "data": sample,
    })


def biosample_identifiers(sample: JsonObject) -> JsonObject:
    accession = normalize_space(sample.get("accession"))
    uid = normalize_space(sample.get("uid"))
    organism = sample.get("organism") if isinstance(sample.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    identifiers: JsonObject = {}
    if accession or uid:
        identifiers["biosample"] = {
            "namespace": "biosample",
            "id": accession or uid,
            "label": accession or f"BioSample:{uid}",
            "url": biosample_url(accession or uid),
        }
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "url": taxonomy_url(taxid),
        }
    for identifier in sample_source_identifiers(sample):
        namespace = normalize_space(identifier.get("namespace")).lower()
        value = normalize_space(identifier.get("id"))
        if not namespace or not value:
            continue
        key = biosample_identifier_key(namespace)
        identifiers.setdefault(
            key,
            {
                "namespace": key,
                "id": value,
                "label": normalize_space(identifier.get("label")) or value,
                "url": normalize_space(identifier.get("url")),
            },
        )
    for link in sample_links(sample):
        target = normalize_space(link.get("target")).lower()
        label = normalize_space(link.get("label"))
        value = normalize_space(link.get("value"))
        identifier = label or value
        if target and identifier:
            identifiers.setdefault(
                target,
                {
                    "namespace": target,
                    "id": identifier,
                    "label": label or identifier,
                    "url": normalize_space(link.get("url")),
                },
            )
    return identifiers


def biosample_links(sample: JsonObject) -> list[JsonObject]:
    accession = normalize_space(sample.get("accession") or sample.get("uid"))
    organism = sample.get("organism") if isinstance(sample.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    links: list[JsonObject] = []
    if accession:
        links.append(
            {
                "label": "BioSample",
                "url": biosample_url(accession),
                "kind": "external",
                "primary": True,
            }
        )
    if taxid:
        links.append(
            {
                "label": f"Taxonomy {taxid}",
                "url": taxonomy_url(taxid),
                "kind": "external",
                "primary": False,
            }
        )
    for identifier in sample_source_identifiers(sample):
        link = source_identifier_link(identifier)
        if link:
            links.append(link)
    for link in sample.get("links", []):
        if isinstance(link, dict) and normalize_space(link.get("url")):
            links.append(
                {
                    "label": normalize_space(link.get("label")) or "Related record",
                    "url": normalize_space(link.get("url")),
                    "kind": "external",
                    "primary": False,
                }
            )
    return unique_links(links)


def biosample_display_metadata(sample: JsonObject) -> list[JsonObject]:
    organism = sample.get("organism") if isinstance(sample.get("organism"), dict) else {}
    fields = compact_fields(
        ("BioSample", normalize_space(sample.get("accession"))),
        ("UID", normalize_space(sample.get("uid"))),
        ("Organism", normalize_space(organism.get("scientific_name"))),
        ("TaxID", normalize_space(organism.get("taxid"))),
        ("Package", normalize_space(sample.get("package"))),
        ("Model", ", ".join(sample.get("models", [])[:3]) if isinstance(sample.get("models"), list) else ""),
        ("Organization", normalize_space(sample.get("organization"))),
        ("Publication date", normalize_space(sample.get("publication_date"))),
        ("Modified", normalize_space(sample.get("modification_date"))),
        ("Status", normalize_space(sample.get("status", {}).get("status")) if isinstance(sample.get("status"), dict) else ""),
    )
    for attribute in sample_attributes(sample)[:8]:
        label = normalize_space(attribute.get("display_name") or attribute.get("name"))
        value = normalize_space(attribute.get("value"))
        if label and value:
            fields.append({"label": label, "value": value})
    return fields


def biosample_related(sample: JsonObject) -> JsonObject:
    related: JsonObject = {}
    organism = sample.get("organism") if isinstance(sample.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    if taxid:
        related["taxonomy"] = {
            "type": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "title": normalize_space(organism.get("scientific_name")),
            "url": taxonomy_url(taxid),
        }
    for identifier in sample_source_identifiers(sample):
        namespace = normalize_space(identifier.get("namespace")).lower()
        value = normalize_space(identifier.get("id"))
        if not namespace or not value:
            continue
        if namespace == "bioproject":
            related["bioproject"] = {
                "type": "bioproject",
                "id": value,
                "label": normalize_space(identifier.get("label")) or value,
                "url": normalize_space(identifier.get("url")) or bioproject_url(value),
            }
        elif namespace == "sra":
            related["sra_sample"] = {
                "type": "sra_sample",
                "id": value,
                "label": value,
                "url": normalize_space(identifier.get("url")) or sra_url(value),
            }
        elif namespace == "geo":
            related["geo_sample"] = {
                "type": "geo_sample",
                "id": value,
                "label": value,
                "url": normalize_space(identifier.get("url")) or geo_accession_url(value),
            }
    for link in sample_links(sample):
        target = normalize_space(link.get("target")).lower()
        label = normalize_space(link.get("label"))
        value = normalize_space(link.get("value"))
        identifier = label or value
        if target == "bioproject" and identifier:
            related["bioproject"] = {
                "type": "bioproject",
                "id": identifier,
                "label": label or identifier,
                "url": normalize_space(link.get("url")) or bioproject_url(identifier),
            }
    return related


def with_sra_compat(response: JsonObject) -> JsonObject:
    response.setdefault("schema_version", RESULT_SCHEMA_VERSION)
    response.setdefault("provenance", response.get("source"))

    experiments = response.get("experiments")
    records = []
    if isinstance(experiments, list):
        records = [
            sra_record(experiment)
            for experiment in experiments
            if isinstance(experiment, dict)
        ]
    response.setdefault("records", records)
    return response


def sra_record(experiment: JsonObject) -> JsonObject:
    accession = normalize_space(experiment.get("accession"))
    uid = normalize_space(experiment.get("uid"))
    stable_id = accession or f"SRA:{uid}"
    title = normalize_space(experiment.get("title") or stable_id)
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    organism_name = normalize_space(organism.get("scientific_name"))
    library = experiment.get("library") if isinstance(experiment.get("library"), dict) else {}
    links = sra_links(experiment)
    return with_ncbi_previews({
        "schema_version": RECORD_SCHEMA_VERSION,
        "type": "omics.run",
        "record_type": "ncbi_sra",
        "database": "sra",
        "id": accession or uid,
        "uid": uid,
        "stable_id": stable_id,
        "label": stable_id,
        "title": title,
        "description": " | ".join(
            part
            for part in [
                normalize_space(library.get("strategy")),
                normalize_space(library.get("source")),
                organism_name,
            ]
            if part
        ),
        "url": sra_url(accession or uid),
        "icon": "sra",
        "identifiers": sra_identifiers(experiment),
        "links": links,
        "display": {
            "component": "run",
            "chip_label": stable_id,
            "icon": "sra",
            "title": title,
            "subtitle": " | ".join(
                part
                for part in [
                    normalize_space(library.get("strategy")),
                    organism_name,
                    run_count_text(experiment),
                ]
                if part
            ),
            "description": normalize_space(library.get("construction_protocol")),
            "metadata": sra_display_metadata(experiment),
            "badges": compact_badges(
                ("NCBI SRA", "source"),
                (stable_id, "identifier"),
                (normalize_space(library.get("strategy")), "record_type"),
                (organism_name, "context"),
            ),
            "actions": display_actions(links),
            "hover": {
                "title": title,
                "subtitle": organism_name,
                "icon": "sra",
                "fields": compact_fields(
                    ("SRA accession", stable_id),
                    ("Study", nested_value(experiment, "study", "accession")),
                    ("Experiment", nested_value(experiment, "experiment", "accession")),
                    ("BioProject", normalize_space(experiment.get("bioproject"))),
                    ("BioSample", normalize_space(experiment.get("biosample"))),
                    ("Organism", organism_name),
                    ("Strategy", normalize_space(library.get("strategy"))),
                    ("Platform", nested_value(experiment, "platform", "name")),
                    ("URL", sra_url(accession or uid)),
                ),
            },
            "primary_url": sra_url(accession or uid),
        },
        "related": sra_related(experiment),
        "data": experiment,
    })


def sra_identifiers(experiment: JsonObject) -> JsonObject:
    uid = normalize_space(experiment.get("uid"))
    accession = normalize_space(experiment.get("accession"))
    identifiers: JsonObject = {}
    if uid:
        identifiers["sra_uid"] = {
            "namespace": "sra_uid",
            "id": uid,
            "label": f"SRA UID:{uid}",
        }
    if accession:
        identifiers["sra"] = {
            "namespace": "sra",
            "id": accession,
            "label": accession,
            "url": sra_url(accession),
        }
    for key in ["study", "experiment", "sample", "submitter"]:
        payload = experiment.get(key)
        if not isinstance(payload, dict):
            continue
        acc = normalize_space(payload.get("accession"))
        if acc:
            identifiers[f"sra_{key}"] = {
                "namespace": f"sra_{key}",
                "id": acc,
                "label": acc,
                "url": sra_url(acc),
            }
    bioproject = normalize_space(experiment.get("bioproject"))
    if bioproject:
        identifiers["bioproject"] = {
            "namespace": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": bioproject_url(bioproject),
        }
    biosample = normalize_space(experiment.get("biosample"))
    if biosample:
        identifiers["biosample"] = {
            "namespace": "biosample",
            "id": biosample,
            "label": biosample,
            "url": biosample_url(biosample),
        }
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    if taxid:
        identifiers["taxonomy"] = {
            "namespace": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "url": taxonomy_url(taxid),
        }
    runs = experiment.get("runs") if isinstance(experiment.get("runs"), list) else []
    run_ids = [
        {
            "namespace": "sra_run",
            "id": normalize_space(run.get("accession")),
            "label": normalize_space(run.get("accession")),
            "url": sra_url(normalize_space(run.get("accession"))),
        }
        for run in runs
        if isinstance(run, dict) and normalize_space(run.get("accession"))
    ]
    if run_ids:
        identifiers["sra_run"] = run_ids
    return identifiers


def sra_links(experiment: JsonObject) -> list[JsonObject]:
    accession = normalize_space(experiment.get("accession") or experiment.get("uid"))
    links: list[JsonObject] = []
    if accession:
        links.append(
            {
                "label": "SRA",
                "url": sra_url(accession),
                "kind": "external",
                "primary": True,
            }
        )
    runs = experiment.get("runs") if isinstance(experiment.get("runs"), list) else []
    for run in runs[:5]:
        if not isinstance(run, dict):
            continue
        run_acc = normalize_space(run.get("accession"))
        if run_acc:
            links.append(
                {
                    "label": f"Run Browser {run_acc}",
                    "url": sra_run_browser_url(run_acc),
                    "kind": "external",
                    "primary": False,
                }
            )
    study_acc = nested_value(experiment, "study", "accession")
    bioproject = normalize_space(experiment.get("bioproject"))
    selector_acc = bioproject or study_acc or accession
    if selector_acc:
        links.append(
            {
                "label": "SRA Run Selector",
                "url": sra_run_selector_url(selector_acc),
                "kind": "external",
                "primary": False,
            }
        )
    biosample = normalize_space(experiment.get("biosample"))
    if biosample:
        links.append(
            {
                "label": "BioSample",
                "url": biosample_url(biosample),
                "kind": "external",
                "primary": False,
            }
        )
    if bioproject:
        links.append(
            {
                "label": "BioProject",
                "url": bioproject_url(bioproject),
                "kind": "external",
                "primary": False,
            }
        )
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    if taxid:
        links.append(
            {
                "label": f"Taxonomy {taxid}",
                "url": taxonomy_url(taxid),
                "kind": "external",
                "primary": False,
            }
        )
    return unique_links(links)


def sra_display_metadata(experiment: JsonObject) -> list[JsonObject]:
    library = experiment.get("library") if isinstance(experiment.get("library"), dict) else {}
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    statistics = experiment.get("statistics") if isinstance(experiment.get("statistics"), dict) else {}
    return compact_fields(
        ("SRA accession", normalize_space(experiment.get("accession"))),
        ("Study", nested_value(experiment, "study", "accession")),
        ("Experiment", nested_value(experiment, "experiment", "accession")),
        ("Runs", ", ".join(sra_run_accessions(experiment)[:5])),
        ("BioProject", normalize_space(experiment.get("bioproject"))),
        ("BioSample", normalize_space(experiment.get("biosample"))),
        ("Organism", normalize_space(organism.get("scientific_name"))),
        ("TaxID", normalize_space(organism.get("taxid"))),
        ("Strategy", normalize_space(library.get("strategy"))),
        ("Source", normalize_space(library.get("source"))),
        ("Selection", normalize_space(library.get("selection"))),
        ("Layout", normalize_space(library.get("layout"))),
        ("Platform", nested_value(experiment, "platform", "name")),
        ("Instrument", nested_value(experiment, "platform", "instrument_model")),
        ("Total runs", normalize_space(statistics.get("total_runs"))),
        ("Total spots", normalize_space(statistics.get("total_spots"))),
        ("Total bases", normalize_space(statistics.get("total_bases"))),
        ("Total size", normalize_space(statistics.get("total_size"))),
        ("Created", normalize_space(experiment.get("create_date"))),
        ("Updated", normalize_space(experiment.get("update_date"))),
    )


def sra_related(experiment: JsonObject) -> JsonObject:
    related: JsonObject = {}
    bioproject = normalize_space(experiment.get("bioproject"))
    if bioproject:
        related["bioproject"] = {
            "type": "bioproject",
            "id": bioproject,
            "label": bioproject,
            "url": bioproject_url(bioproject),
        }
    biosample = normalize_space(experiment.get("biosample"))
    if biosample:
        related["biosample"] = {
            "type": "biosample",
            "id": biosample,
            "label": biosample,
            "url": biosample_url(biosample),
        }
    organism = experiment.get("organism") if isinstance(experiment.get("organism"), dict) else {}
    taxid = normalize_space(organism.get("taxid"))
    if taxid:
        related["taxonomy"] = {
            "type": "taxonomy",
            "id": taxid,
            "label": f"TaxID:{taxid}",
            "title": normalize_space(organism.get("scientific_name")),
            "url": taxonomy_url(taxid),
        }
    runs = [
        {
            "type": "sra_run",
            "id": normalize_space(run.get("accession")),
            "label": normalize_space(run.get("accession")),
            "url": sra_url(normalize_space(run.get("accession"))),
            "run_browser_url": sra_run_browser_url(normalize_space(run.get("accession"))),
        }
        for run in experiment.get("runs", [])
        if isinstance(run, dict) and normalize_space(run.get("accession"))
    ]
    if runs:
        related["runs"] = runs
    return related


def sample_source_identifiers(sample: JsonObject) -> list[JsonObject]:
    identifiers = sample.get("source_identifiers")
    return identifiers if isinstance(identifiers, list) else []


def sample_attributes(sample: JsonObject) -> list[JsonObject]:
    attributes = sample.get("attributes")
    return attributes if isinstance(attributes, list) else []


def sample_links(sample: JsonObject) -> list[JsonObject]:
    links = sample.get("links")
    return links if isinstance(links, list) else []


def first_attribute_value(sample: JsonObject, names: list[str]) -> str:
    wanted = {name.lower() for name in names}
    for attribute in sample_attributes(sample):
        if not isinstance(attribute, dict):
            continue
        keys = [
            normalize_space(attribute.get("name")).lower(),
            normalize_space(attribute.get("harmonized_name")).lower(),
            normalize_space(attribute.get("display_name")).lower(),
        ]
        if any(key in wanted for key in keys):
            value = normalize_space(attribute.get("value"))
            if value:
                return value
    return ""


def biosample_identifier_key(namespace: str) -> str:
    lowered = namespace.lower()
    if lowered == "sra":
        return "sra_sample"
    if lowered == "geo":
        return "geo_sample"
    return lowered


def source_identifier_link(identifier: JsonObject) -> JsonObject | None:
    namespace = normalize_space(identifier.get("namespace")).lower()
    value = normalize_space(identifier.get("id"))
    label = normalize_space(identifier.get("label")) or value
    url = normalize_space(identifier.get("url"))
    if not url:
        if namespace == "biosample":
            url = biosample_url(value)
        elif namespace == "sra":
            url = sra_url(value)
        elif namespace == "geo":
            url = geo_accession_url(value)
        elif namespace == "bioproject":
            url = bioproject_url(value)
    if not url:
        return None
    return {
        "label": label,
        "url": url,
        "kind": "external",
        "primary": False,
    }


def nested_value(payload: JsonObject, key: str, name: str) -> str:
    child = payload.get(key)
    if not isinstance(child, dict):
        return ""
    return normalize_space(child.get(name))


def sra_run_accessions(experiment: JsonObject) -> list[str]:
    runs = experiment.get("runs") if isinstance(experiment.get("runs"), list) else []
    return [
        normalize_space(run.get("accession"))
        for run in runs
        if isinstance(run, dict) and normalize_space(run.get("accession"))
    ]


def run_count_text(experiment: JsonObject) -> str:
    runs = sra_run_accessions(experiment)
    if not runs:
        return ""
    return f"{len(runs)} run" if len(runs) == 1 else f"{len(runs)} runs"


def unique_links(links: list[JsonObject]) -> list[JsonObject]:
    seen = set()
    unique = []
    for link in links:
        url = normalize_space(link.get("url"))
        label = normalize_space(link.get("label")) or url
        if not url:
            continue
        key = (label, url)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "label": label,
                "url": url,
                "kind": normalize_space(link.get("kind")) or "external",
                "primary": bool(link.get("primary")),
            }
        )
    return unique
