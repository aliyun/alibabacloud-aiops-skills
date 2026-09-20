"""Read-only resolve; maps to Go slsmodel/catalog_resolve.go."""

from .element import identity, metadata, object_cell
from .errors import CatalogError
from .query import QueryFunc, ReadMode, literal


def resolve(query: QueryFunc, schema):
    spl = (".umodel | where kind = 'storage_link' and json_extract_scalar(spec, '$.src.domain') = 'sls'"
           " and json_extract_scalar(spec, '$.src.kind') = 'log_set'"
           f" and json_extract_scalar(spec, '$.src.name') = '{literal(schema)}' | project spec")
    rows = query(spl, ReadMode.COMPLETE)
    if not rows:
        raise CatalogError("binding_missing", "No storage binding for " + schema)
    destinations = set()
    for row in rows:
        spec = object_cell(row.get("spec", ""), "InvalidStorageBinding")
        dest = identity(spec.get("dest"))
        if (identity(spec.get("src")) != ("sls", "log_set", schema) or not dest
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
    for row in query(spl, ReadMode.COMPLETE):
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
    return {"schema": schema, "datasources": [found[name] for name in sorted(found)]}
