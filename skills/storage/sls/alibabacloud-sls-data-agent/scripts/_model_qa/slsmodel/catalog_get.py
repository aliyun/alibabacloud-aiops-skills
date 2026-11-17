"""Read-only get; maps to Go slsmodel/catalog_get.go."""

from collections import Counter

from .element import ELEMENTS, member_name, members, metadata
from .errors import CatalogError
from .query import ModelQuery, ReadMode, literal


def get(query_model: ModelQuery, element_type, element_name, member_names=None):
    kind, subtype, key = ELEMENTS[element_type]
    spl = (f".umodel | where kind = '{kind}' and json_extract_scalar(metadata, '$.domain') = 'sls'"
           f" and json_extract_scalar(metadata, '$.name') = '{literal(element_name)}'")
    if subtype:
        spl += f" and json_extract_scalar(metadata, '$.tags.runbook_type') = '{subtype}'"
    exact = []
    for row in query_model(spl + " | project kind, metadata, spec", ReadMode.COMPLETE):
        meta = metadata(row.get("metadata", ""))
        if (row.get("kind"), meta["domain"], meta["name"]) == (kind, "sls", element_name) and (
                not subtype or subtype == meta["runbook_type"]):
            exact.append((meta, row))
    if len(exact) != 1:
        raise CatalogError("element_not_found" if not exact else "element_ambiguous", f"Expected one {element_type} element: {element_name}")
    meta, row = exact[0]
    items = members(row.get("spec", ""), key)
    names = set(member_names) if member_names is not None else None
    selected = items if names is None else [m for m in items if member_name(m) in names]
    counts = Counter(member_name(m) for m in selected if member_name(m))
    if any(count > 1 for count in counts.values()):
        raise CatalogError("member_ambiguous", "Selected member names are not unique")
    present = {member_name(m) for m in items if member_name(m)}
    result = {"elementType": element_type, "element": element_name, "members": selected,
              "missingMembers": [name for name in (member_names or []) if name not in present]}
    if element_type in ("schema", "overview", "metric") and meta["source"]:
        result["source"] = meta["source"]
    return result
