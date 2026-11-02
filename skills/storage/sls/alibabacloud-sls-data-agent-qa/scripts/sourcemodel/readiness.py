"""Evaluate complete Source Model evidence without starting generation tasks."""

from slsmodel import CatalogError
from slsmodel.element import object_cell

STORAGE_SPL = ".umodel | where kind = 'sls_logstore' | project kind, metadata, spec"


def check_logstore_readiness(client, project, logstore, region, *, legacy_status=False):
    result = {"project": project, "logstore": logstore, "region": region, "available": False}
    status_missing = False
    try:
        status = client.get_generation_status(project)
    except Exception as error:
        if str(getattr(error, "code", "")) != "SourceModelNotExist":
            raise
        status_missing, status = True, None
    if not status_missing:
        count = status.get("elementCount") if isinstance(status, dict) else None
        if type(count) is not int or count < 0:
            raise CatalogError("InvalidSourceModelStatus", "elementCount must be a nonnegative integer")
        state = status.get("taskState")
        result["taskState"] = state
        result["elementCount"] = count
        if state in ("pending", "running", "failed"):
            return {**result, "reason": "generation_" + state}
        complete = state == "succeeded" or ("taskState" not in status and legacy_status and count > 0)
    else:
        complete = False
    try:
        rows = client.query_model(project, STORAGE_SPL)
    except Exception as error:
        if str(getattr(error, "code", "")) != "SourceModelNotExist":
            raise
        if status_missing:
            return {**result, "reason": "model_missing", "recommendation": "create"}
        return {**result, "reason": "inconsistent_model_status"}
    matches, conflict = [], False
    for row in rows:
        if row.get("kind") != "sls_logstore":
            raise CatalogError("InvalidSourceModelNode", "Unexpected storage node kind")
        spec = object_cell(row.get("spec"), "InvalidSourceModelNode")
        meta = object_cell(row.get("metadata"), "InvalidSourceModelNode")
        if not isinstance(spec.get("store"), str) or not spec["store"]:
            raise CatalogError("InvalidSourceModelNode", "Storage node has no Logstore")
        if spec["store"] != logstore:
            continue
        if any(spec.get(key) not in (None, "", expected) for key, expected in (("project", project), ("region", region))):
            conflict = True
            continue
        tags = meta.get("tags")
        matches.append(tags.get("generate_status") if isinstance(tags, dict) else None)
    if status_missing:
        return ({**result, "reason": "inconsistent_model_status"} if rows else
                {**result, "reason": "model_missing", "recommendation": "create"})
    if conflict or len(matches) > 1:
        return {**result, "reason": "ambiguous_storage_coordinates"}
    if not complete:
        return {**result, "reason": "project_generation_unconfirmed"}
    if not matches:
        return {**result, "reason": "logstore_model_missing", "recommendation": "regenerate"}
    if matches[0] != "finish":
        return {**result, "reason": "logstore_generation_unconfirmed", "nodeState": matches[0]}
    return {**result, "available": True, "reason": "ready", "nodeState": "finish"}
