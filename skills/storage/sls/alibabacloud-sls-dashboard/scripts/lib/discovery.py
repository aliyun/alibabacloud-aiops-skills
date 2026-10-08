"""Convert public SLS index and query results into skill-owned facts."""
from __future__ import annotations

from .common import SkillError, digest, schema_check, source_check


def index_fields(index, prefix=""):
    fields = {}
    for key, info in index.get("keys", {}).items():
        if not isinstance(info, dict):
            continue
        name = prefix + key
        if info.get("type") == "json":
            nested = {"keys": info.get("json_keys", {})}
            fields.update(index_fields(nested, name + "."))
        fields[name] = {"name": name, "type": str(info.get("type", "unknown")),
                        "indexed": True, "analytics": info.get("doc_value") is True, "inSample": False}
    return fields


def view_index_fields(index):
    """GetStoreViewIndex returns per-member indexes, not one combined index."""
    if not isinstance(index.get("indexes"), list):
        raise SkillError("StoreView index response requires indexes[]", "INVALID_RESPONSE")
    members, observed = [], {}
    for item in index["indexes"]:
        if not isinstance(item, dict) or not isinstance(item.get("index"), dict):
            raise SkillError("StoreView member index must be an object", "INVALID_RESPONSE")
        project, name = item.get("projectName"), item.get("logstore")
        if not isinstance(project, str) or not isinstance(name, str):
            raise SkillError("StoreView member requires projectName/logstore", "INVALID_RESPONSE")
        fields = index_fields(item["index"])
        members.append({"project": project, "name": name, "fields": list(fields.values())})
        for field in fields.values():
            observed.setdefault(field["name"], set()).add(field["type"])
    # Presence in a member is not evidence of uniform view-wide analytics.
    combined = {name: {"name": name, "type": next(iter(types)) if len(types) == 1 else "unknown",
                       "indexed": None, "analytics": None, "inSample": False}
                for name, types in observed.items()}
    failures = index.get("storeViewErrors") or []
    if not isinstance(failures, list) or any(not isinstance(item, dict) for item in failures):
        raise SkillError("StoreView member errors must be objects", "INVALID_RESPONSE")
    return combined, members, failures


def summarize(source, index=None, sample=None, metadata=None, metrics=None):
    source_check(source)
    evidence, warnings = [], []
    members, member_errors = [], []
    if index is not None and source["type"].endswith("_storeview"):
        fields, members, member_errors = view_index_fields(index)
    else:
        fields = index_fields(index) if index is not None else {}
    if index is not None:
        evidence.append({"kind": "api", "operation": "get-store-view-index" if source["type"].endswith("_storeview")
                         else "get-index", "sha256": digest(index)})
    if sample is not None:
        evidence.append({"kind": "query", "sha256": digest(sample),
                         "window": sample.get("window", {})})
        if not sample.get("complete"):
            warnings.append("Query progress is not Complete; sample evidence is partial.")
        if sample.get("limitReached") or sample.get("truncated"):
            warnings.append("Result limit reached; sample is not a full inventory.")
        for row in sample.get("rows", []):
            for name in row:
                field = fields.setdefault(name, {"name": name, "type": "unknown",
                                                 "indexed": None, "analytics": None, "inSample": True})
                field["inSample"] = True
    if metadata is not None:
        evidence.append({"kind": "api", "operation": "describe", "sha256": digest(metadata)})
    if source["type"].endswith("_storeview"):
        warnings.append("View facts do not imply identical schemas or permissions across all members.")
        if member_errors:
            warnings.append(f"{len(member_errors)} view member index requests failed; see memberErrors.")
    result = {"version": 1, "source": source, "metadata": metadata or {},
              "fields": sorted(fields.values(), key=lambda field: field["name"]),
              "metrics": [{"name": name} for name in (metrics or {}).get("metrics", [])],
              "evidence": evidence, "warnings": warnings}
    if source["type"].endswith("_storeview"):
        result["members"] = members
        result["memberErrors"] = member_errors
    if sample is not None:
        result["sample"] = sample.get("rows", [])[:20]
    if metrics is not None:
        evidence.append({"kind": metrics.get("evidenceKind", "query"), "sha256": digest(metrics),
                         "window": metrics.get("window", {})})
        if metrics.get("evidenceKind") == "user":
            warnings.append("Metric names were supplied explicitly; this is not a discovered catalog.")
        elif not metrics.get("complete") or metrics.get("limitReached"):
            warnings.append("Metric catalog is partial or bounded.")
    schema_check(result, "source-facts")
    return result
