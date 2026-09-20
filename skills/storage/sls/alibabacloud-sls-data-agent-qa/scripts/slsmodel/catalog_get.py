"""Read-only get; maps to Go slsmodel/catalog_get.go."""

from collections import Counter

from .element import ELEMENTS, member_name, members, metadata
from .errors import CatalogError
from .query import QueryFunc, ReadMode, literal


def get(query: QueryFunc, element_type, element, requested=None):
    kind, subtype, key = ELEMENTS[element_type]
    spl = (f".umodel | where kind = '{kind}' and json_extract_scalar(metadata, '$.domain') = 'sls'"
           f" and json_extract_scalar(metadata, '$.name') = '{literal(element)}'")
    if subtype:
        spl += f" and json_extract_scalar(metadata, '$.tags.runbook_type') = '{subtype}'"
    exact = []
    for row in query(spl + " | project kind, metadata, spec", ReadMode.COMPLETE):
        meta = metadata(row.get("metadata", ""))
        if (row.get("kind"), meta["domain"], meta["name"]) == (kind, "sls", element) and (
                not subtype or subtype == meta["runbook_type"]):
            exact.append((meta, row))
    if len(exact) != 1:
        raise CatalogError("element_not_found" if not exact else "element_ambiguous", f"Expected one {element_type} element: {element}")
    meta, row = exact[0]
    items = members(row.get("spec", ""), key)
    names = set(requested) if requested is not None else None
    selected = items if names is None else [m for m in items if member_name(m) in names]
    counts = Counter(member_name(m) for m in selected if member_name(m))
    if any(count > 1 for count in counts.values()):
        raise CatalogError("member_ambiguous", "Selected member names are not unique")
    present = {member_name(m) for m in items if member_name(m)}
    result = {"elementType": element_type, "element": element, "members": selected,
              "missingMembers": [name for name in (requested or []) if name not in present]}
    if element_type in ("overview", "metric") and meta["source"]:
        result["sourceSchema"] = meta["source"]
    return result
