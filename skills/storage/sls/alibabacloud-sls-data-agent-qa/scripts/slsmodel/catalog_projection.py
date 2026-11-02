"""Pure overview attribution and grouping; maps to catalog_projection.go."""

from .element import ELEMENTS, SLOTS, bindings, member_name, members, metadata
from .errors import CatalogError

def group_add(groups, slot, name, items):
    group = groups.setdefault(slot, {}).setdefault(name, {"element": name, "memberCount": 0, "members": []})
    group["memberCount"] += len(items)
    group["members"].extend(member_name(m) for m in items if member_name(m))


def group_list(groups, slot):
    return [{**group, "members": sorted(group["members"])}
            for _, group in sorted(groups.get(slot, {}).items())]


def project_overview(rows, *, include_example_queries=True):
    elements = []
    for row in rows:
        try:
            meta = metadata(row.get("metadata", ""))
        except CatalogError:
            meta = dict.fromkeys(("domain", "description", "source", "runbook_type"), "")
            meta["name"] = row.get("metadata", "")
        for element_type, (kind, subtype, key) in ELEMENTS.items():
            if element_type == "exampleQuery" and not include_example_queries:
                continue
            if row.get("kind") == kind and (not subtype or subtype == meta["runbook_type"]):
                try:
                    items = members(row.get("spec", ""), key)
                except CatalogError:
                    items = []  # Discovery remains best-effort; get/resolve are strict.
                elements.append((element_type, meta, items))
                break
    source_groups, schema_source_tags, model_groups, unresolved_groups = {}, {}, {}, {}
    unresolved_schemas = []
    for element_type, meta, items in elements:
        if element_type != "schema":
            continue
        schema_group = {"element": meta["name"], "description": meta["description"],
                  "memberCount": len(items), "members": sorted(member_name(m) for m in items if member_name(m))}
        if meta["domain"] != "sls" or not meta["name"] or not meta["source"]:
            unresolved_schemas.append(schema_group)
            continue
        source_groups.setdefault(meta["source"], {"schema": schema_group, "groups": {}})
        schema_source_tags[("sls", "log_set", meta["name"])] = meta["source"]
    for element_type, meta, items in elements:
        if element_type == "schema":
            continue
        if element_type in ("overview", "metric"):
            target = source_groups[meta["source"]]["groups"] if meta["source"] in source_groups else unresolved_groups
            group_add(target, element_type, meta["name"], items)
            continue
        for member in items:
            bound = bindings(member, element_type)
            if bound == [] and element_type == "term":
                targets = [model_groups]
            elif not bound or any(i not in schema_source_tags for i in bound):
                targets = [unresolved_groups]
            else:
                targets = [source_groups[name]["groups"] for name in sorted({schema_source_tags[i] for i in bound})]
            for target in targets:
                group_add(target, element_type, meta["name"], [member])
    return {
        "modelScope": {"terms": group_list(model_groups, "term")},
        "sources": [{"source": name, "schema": source_group["schema"],
                     **{slot: group_list(source_group["groups"], typ) for typ, slot in SLOTS.items()}}
                    for name, source_group in sorted(source_groups.items())],
        "unresolved": {"schemas": sorted(unresolved_schemas, key=lambda s: s["element"]),
                       **{slot: group_list(unresolved_groups, typ) for typ, slot in SLOTS.items()}},
    }
