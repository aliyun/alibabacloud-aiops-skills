"""Resolve Context Model storage mappings by Schema name or semantic source tag."""

from slsmodel.element import identity, metadata, object_cell
from slsmodel.errors import CatalogError
from slsmodel.query import ModelQuery, ReadMode, literal


def resolve_by_source_tag(query_model: ModelQuery, source_tag):
    """Resolve metadata.tags.source through its unique Schema; source is not a model type."""
    spl = (".umodel | where kind = 'log_set' and json_extract_scalar(metadata, '$.domain') = 'sls'"
           f" and json_extract_scalar(metadata, '$.tags.source') = '{literal(source_tag)}' | project kind, metadata")
    rows = query_model(spl, ReadMode.COMPLETE)
    if not rows:
        raise CatalogError("SourceSchemaNotFound", "No Schema for source tag: " + source_tag)
    names = []
    for row in rows:
        meta = metadata(row.get("metadata", ""))
        if (row.get("kind") != "log_set" or meta["domain"] != "sls" or not meta["name"].strip()
                or meta["source"] != source_tag):
            raise CatalogError("InvalidSourceSchema", "Invalid source to Schema association")
        literal(meta["name"])
        names.append(meta["name"])
    if len(names) != 1:
        raise CatalogError("AmbiguousSourceSchema", "Source tag must identify exactly one Schema: " + source_tag)
    return resolve_by_schema(query_model, names[0])


def resolve_by_schema(query_model: ModelQuery, schema_name):
    """Follow a Schema's storage_link bindings to physical SLS Logstores."""
    spl = (".umodel | where kind = 'storage_link' and json_extract_scalar(spec, '$.src.domain') = 'sls'"
           " and json_extract_scalar(spec, '$.src.kind') = 'log_set'"
           f" and json_extract_scalar(spec, '$.src.name') = '{literal(schema_name)}' | project spec")
    rows = query_model(spl, ReadMode.COMPLETE)
    if not rows:
        raise CatalogError("binding_missing", "No storage binding for " + schema_name)
    destinations = set()
    for row in rows:
        spec = object_cell(row.get("spec", ""), "InvalidStorageBinding")
        dest = identity(spec.get("dest"))
        if (identity(spec.get("src")) != ("sls", "log_set", schema_name) or not dest
                or dest[:2] != ("sls", "sls_logstore") or not dest[2].strip()):
            raise CatalogError("InvalidStorageBinding", "Storage link has an invalid source or destination")
        destinations.add(dest[2])
    try:
        names = ", ".join("'" + literal(name) + "'" for name in sorted(destinations))
    except CatalogError as exc:
        raise CatalogError("InvalidStorageDestination", str(exc)) from None
    spl = (".umodel | where kind = 'sls_logstore' and json_extract_scalar(metadata, '$.domain') = 'sls'"
           f" and json_extract_scalar(metadata, '$.name') in ({names}) | project kind, metadata, spec")
    found = {}
    for row in query_model(spl, ReadMode.COMPLETE):
        meta = metadata(row.get("metadata", ""))
        if row.get("kind") != "sls_logstore" or meta["domain"] != "sls" or not meta["name"]:
            raise CatalogError("InvalidCatalogMetadata", "Invalid storage identity")
        spec = object_cell(row.get("spec", ""), "InvalidCatalogDatasource")
        if "element" in spec or any(not isinstance(spec.get(k), str) or not spec[k].strip()
                                    for k in ("region", "project", "store")):
            raise CatalogError("InvalidCatalogDatasource", "Storage requires region, project, store and no reserved element key")
        if spec.get("search_filter") is not None and not isinstance(spec["search_filter"], str):
            raise CatalogError("InvalidCatalogDatasource", "search_filter must be a string or null")
        if meta["name"] not in destinations:
            raise CatalogError("IncompleteCatalogRead", "Unexpected storage in resolve response")
        if meta["name"] in found:
            raise CatalogError("InvalidStorageCardinality", "Multiple storage elements named " + meta["name"])
        found[meta["name"]] = {**spec, "element": meta["name"]}
    missing = destinations - found.keys()
    if missing:
        raise CatalogError("binding_broken", "Missing storage: " + ", ".join(sorted(missing)))
    return {"schema": schema_name, "datasources": [found[name] for name in sorted(found)]}
