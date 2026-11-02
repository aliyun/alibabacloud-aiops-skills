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


def get_output(identity_fields, result, max_bytes=DEFAULT_MAX_BYTES):
    payload = {**identity_fields, **result, "truncated": False, "omittedMembers": []}
    if size(payload) <= max_bytes or not result["members"]:
        return payload
    return omit_suffix(payload, "members", "omittedMembers", member_name, GET_HINT, max_bytes)


def overview_output(identity_fields, result, source_tags=None, max_bytes=DEFAULT_MAX_BYTES):
    payload = {**identity_fields, **deepcopy(result), "truncated": False, "omittedSources": []}
    if source_tags is not None:
        known = {s["source"] for s in payload["sources"]}
        missing = [name for name in source_tags if name not in known]
        if missing:
            raise CatalogError("CatalogSourceNotFound", "Unknown source: " + ", ".join(missing))
        payload["sources"] = [s for s in payload["sources"] if s["source"] in set(source_tags)]
    if size(payload) <= max_bytes:
        return payload
    groups = list(payload["modelScope"]["terms"])
    for values in payload["unresolved"].values():
        groups.extend(values)
    for source_group in payload["sources"]:
        groups.append(source_group["schema"])
        for key in ("overviews", "metrics", "terms", "exampleQueries"):
            groups.extend(source_group[key])
    for group in groups:
        group.pop("members", None)
    if groups:
        payload.update(truncated=True, hint=COMPACT_HINT)
    if size(payload) <= max_bytes or not payload["sources"]:
        return payload
    return omit_suffix(payload, "sources", "omittedSources", lambda s: s["source"], FOLD_HINT, max_bytes)


def search_output(identity_fields, result, max_bytes=DEFAULT_MAX_BYTES):
    candidates = result["candidates"]

    def render(retained):
        groups, hints = {}, []
        if result["structureIssues"]:
            hints.append("Some definitions have unresolved identities or bindings; inspect catalog overview/get.")
        if result["retrieval"]["limited"]:
            hints.append("Result limit reached; narrow the query or increase --limit.")
        if any(c["factual"] for c in candidates):
            hints.append("Some fields matched factual attributes only; verify unaccepted semantics before use.")
        if any(',' in member_name(c['member']) or member_name(c['member']).strip() != member_name(c['member']) for c in candidates):
            hints.append("Some Member names require reading the whole Element without --members.")
        for index, candidate in enumerate(candidates):
            key = (candidate["elementType"], candidate["element"])
            group = groups.setdefault(key, {"elementType": key[0], "element": key[1],
                                           "members": [], "truncated": False, "omittedMembers": []})
            if candidate["source"]:
                group["source"] = candidate["source"]
            if index in retained:
                group["members"].append(candidate["member"])
            else:
                group["truncated"] = True
                group["omittedMembers"].append(member_name(candidate["member"]))
        truncated = len(retained) < len(candidates)
        if truncated:
            hints.append("Definitions omitted; use catalog get with the Element selector and omittedMembers, or increase --max-bytes.")
        payload = {**identity_fields, "results": list(groups.values()), "retrieval": result["retrieval"], "truncated": truncated}
        if hints:
            payload["hint"] = " ".join(hints)
        return payload

    retained = set(range(len(candidates)))
    full = render(retained)
    if size(full) <= max_bytes:
        return full
    retained.clear()
    payload = render(retained)
    if size(payload) > max_bytes:
        raise CatalogError("InvalidOutputBudget", "Search recovery metadata exceeds --max-bytes; increase it or narrow the query/limit")
    for index in range(len(candidates)):
        retained.add(index)
        attempt = render(retained)
        if size(attempt) <= max_bytes:
            payload = attempt
        else:
            retained.remove(index)
    return payload
