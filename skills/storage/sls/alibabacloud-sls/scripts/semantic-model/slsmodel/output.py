"""Recoverable byte budgets for local lexical search results."""

from slsmodel.errors import CatalogError
from slsmodel.element import member_name
from slsmodel.encoding import size

DEFAULT_MAX_BYTES = 28672


def search_output(identity_fields, result, max_bytes=DEFAULT_MAX_BYTES):
    candidates = result["candidates"]

    def render(retained):
        groups, hints = {}, []
        if result["structureIssues"]:
            hints.append(
                "Some definitions have unresolved identities or bindings; inspect catalog overview/get."
            )
        if result["retrieval"]["limited"]:
            hints.append("Result limit reached; narrow the query or increase --limit.")
        if any(c["factual"] for c in candidates):
            hints.append(
                "Some fields matched factual attributes only; verify unaccepted semantics before use."
            )
        if any(
            "," in member_name(c["member"])
            or member_name(c["member"]).strip() != member_name(c["member"])
            for c in candidates
        ):
            hints.append("Some Member names require reading the whole Element without --members.")
        for index, candidate in enumerate(candidates):
            key = (candidate["elementType"], candidate["element"])
            group = groups.setdefault(
                key,
                {
                    "elementType": key[0],
                    "element": key[1],
                    "members": [],
                    "truncated": False,
                    "omittedMembers": [],
                },
            )
            if candidate["source"]:
                group["source"] = candidate["source"]
            if index in retained:
                group["members"].append(candidate["member"])
            else:
                group["truncated"] = True
                group["omittedMembers"].append(member_name(candidate["member"]))
        truncated = len(retained) < len(candidates)
        if truncated:
            hints.append(
                "Definitions omitted; use catalog get with the Element selector and omittedMembers, or increase --max-bytes."
            )
        payload = {
            **identity_fields,
            "results": list(groups.values()),
            "retrieval": result["retrieval"],
            "truncated": truncated,
        }
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
        raise CatalogError(
            "InvalidOutputBudget",
            "Search recovery metadata exceeds --max-bytes; increase it or narrow the query/limit",
        )
    for index in range(len(candidates)):
        retained.add(index)
        attempt = render(retained)
        if size(attempt) <= max_bytes:
            payload = attempt
        else:
            retained.remove(index)
    return payload
