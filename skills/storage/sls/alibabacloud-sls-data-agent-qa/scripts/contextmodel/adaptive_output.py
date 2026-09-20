"""Recoverable catalog output budgets, matching the Go CLI projection."""

from copy import deepcopy

from slsmodel.errors import CatalogError
from slsmodel.element import member_name
from slsmodel.encoding import size

DEFAULT_MAX_BYTES = 28672
COMPACT_HINT = "Member names omitted. Use --sources to narrow the source selection or increase --max-bytes."
FOLD_HINT = ("Sources omitted. Use --sources to narrow the source selection or increase --max-bytes; "
             "if a single selected source is still omitted, increase --max-bytes.")
GET_HINT = "Member definitions omitted. Use --members to narrow the selection or increase --max-bytes."


def omit_suffix(payload, key, omitted_key, name_of, hint, max_bytes):
    """Find the longest fitting prefix in O(serialized input size), not O(n²)."""
    entries = payload[key]
    payload.update(truncated=True, hint=hint)
    current_size = size(payload)
    seen = set()
    keep = len(entries)
    while keep:
        entry = entries[keep - 1]
        current_size -= size(entry) + (1 if keep > 1 else 0)
        name = name_of(entry)
        if name and name not in seen:
            current_size += size(name) + (1 if seen else 0)
            seen.add(name)
        keep -= 1
        if current_size <= max_bytes:
            break
    payload[key] = entries[:keep]
    payload[omitted_key] = list(dict.fromkeys(name_of(e) for e in entries[keep:] if name_of(e)))
    # The required envelope may exceed the budget; never discard recovery names.
    return payload


def get_output(model, result, max_bytes=DEFAULT_MAX_BYTES):
    payload = {"model": model, **result, "truncated": False, "omittedMembers": []}
    if size(payload) <= max_bytes or not result["members"]:
        return payload
    return omit_suffix(payload, "members", "omittedMembers", member_name, GET_HINT, max_bytes)


def overview_output(model, result, sources=None, max_bytes=DEFAULT_MAX_BYTES):
    payload = {"model": model, **deepcopy(result), "truncated": False, "omittedSources": []}
    if sources is not None:
        known = {s["source"] for s in payload["sources"]}
        missing = [name for name in sources if name not in known]
        if missing:
            raise CatalogError("unknown_source", "Unknown source: " + ", ".join(missing))
        payload["sources"] = [s for s in payload["sources"] if s["source"] in set(sources)]
    if size(payload) <= max_bytes:
        return payload
    groups = list(payload["modelScope"]["terms"])
    for values in payload["unresolved"].values():
        groups.extend(values)
    for source in payload["sources"]:
        groups.append(source["schema"])
        for key in ("overviews", "metrics", "terms", "exampleQueries"):
            groups.extend(source[key])
    for group in groups:
        group.pop("members", None)
    if groups:
        payload.update(truncated=True, hint=COMPACT_HINT)
    if size(payload) <= max_bytes or not payload["sources"]:
        return payload
    return omit_suffix(payload, "sources", "omittedSources", lambda s: s["source"], FOLD_HINT, max_bytes)
