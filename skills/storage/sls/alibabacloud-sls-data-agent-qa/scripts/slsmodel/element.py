"""Element identities, metadata and members; maps to Go slsmodel/element.go."""

import json
from decimal import Decimal

from .errors import CatalogError

# kind, runbook discriminator, collection; insertion order is part of the query.
ELEMENTS = {
    "schema": ("log_set", "", "fields"),
    "overview": ("runbook_set", "overview", "skills"),
    "metric": ("metric_set", "", "metrics"),
    "term": ("runbook_set", "terms", "terms"),
    "exampleQuery": ("runbook_set", "queries", "queries"),
}
SLOTS = {"overview": "overviews", "metric": "metrics", "term": "terms",
         "exampleQuery": "exampleQueries"}

def object_cell(cell, code):
    try:
        value = json.loads(cell, parse_float=Decimal)
    except (ValueError, TypeError):
        raise CatalogError(code, "Expected a JSON object in the catalog response") from None
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise CatalogError(code, "Expected a JSON object in the catalog response")
    return value


def metadata(cell):
    raw = object_cell(cell, "InvalidCatalogMetadata")
    result = {}
    for group in ("description", "tags"):
        if raw.get(group) is not None and not isinstance(raw[group], dict):
            raise CatalogError("InvalidCatalogMetadata", "Invalid metadata " + group)
    values = {"domain": raw.get("domain"), "name": raw.get("name"),
              "description": (raw.get("description") or {}).get("universal"),
              "source": (raw.get("tags") or {}).get("source"),
              "runbook_type": (raw.get("tags") or {}).get("runbook_type")}
    for key, value in values.items():
        if value is not None and not isinstance(value, str):
            raise CatalogError("InvalidCatalogMetadata", "Invalid metadata " + key)
        result[key] = value or ""
    return result


def members(cell, key):
    value = object_cell(cell, "InvalidCatalogSpec").get(key)
    if value is None:
        return []
    if not isinstance(value, list):
        raise CatalogError("InvalidCatalogSpec", "Member collection must be an array")
    return value


def identity(value):
    if not isinstance(value, dict):
        return None
    fields = tuple(value.get(key) for key in ("domain", "kind", "name"))
    return fields if all(isinstance(v, str) for v in fields) else None


def bindings(member, element_type):
    # None is invalid, [] is model-scoped, nonempty is schema-scoped.
    if member is None and element_type == "term":
        return []  # Go decodes JSON null into a nil map.
    if not isinstance(member, dict):
        return None
    raw = member.get("model_bindings", []) if element_type == "term" else [member.get("model_binding")]
    if not isinstance(raw, list):
        return None
    result = []
    for value in raw:
        item = identity(value)
        if not item or item[:2] != ("sls", "log_set") or not item[2] or item in result:
            return None
        result.append(item)
    return result


def member_name(member):
    name = member.get("name") if isinstance(member, dict) else None
    return name if isinstance(name, str) else ""
