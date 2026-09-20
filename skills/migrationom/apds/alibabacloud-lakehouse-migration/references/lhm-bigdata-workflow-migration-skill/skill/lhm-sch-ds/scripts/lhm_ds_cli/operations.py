"""Stateless single-step datasource operations for Agent-driven workflows.

Each function makes exactly ONE API call and returns a structured status
dict. There is NO internal looping, prompting, or file upload here — the Agent
(caller) is responsible for sequencing, asking the user for decisions, and
performing the OSS file upload via curl. State (parsed config, datasource name,
new id) is passed in via function arguments, never persisted internally.

Status values:
- "ok":        operation succeeded; payload carried in step-specific fields
- "exists":    datasource name already exists or is invalid (check-name step)
- "available": datasource name is free to use (check-name step)
- "empty":     no matching datasource found (check step)
- "match":     one or more matching datasources found (check step)
- "failed":    unrecoverable business / API error
"""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict

from lhm_ds_cli.client_helper import (
    create_client,
    request_id_of,
    safe_parse_json,
)


def _failed(err_code: str, err_message: str, request_id: str = "") -> Dict[str, Any]:
    """Build a 'failed' status dict."""
    return {
        "status": "failed",
        "err_code": err_code,
        "err_message": err_message,
        "request_id": request_id,
    }


def check_existing(
    config, ds_name: str, category_type: str, ds_type: str = None
) -> Dict[str, Any]:
    """Single step: query datasources by name (ListMetaDataComponentPage).

    Args:
        config: LHM configuration.
        ds_name: Target datasource name.
        category_type: Datasource category (e.g. "WORKFLOW").
        ds_type: Datasource technical type (e.g. "DolphinScheduler").
            None/'[]' is sent as an empty string "" (no type filter).

    Returns:
        Status dict. "empty" → no match, caller proceeds to create.
        "match" → carries `matches` list; caller asks the user to pick one.
        "failed" → API error, caller aborts.
    """
    # dsType 未指定时传空字符串（不按类型过滤）
    if ds_type is None or str(ds_type).strip() in ("", "[]"):
        ds_type_value = ""
    else:
        ds_type_value = ds_type

    client = create_client(config)
    request = {
        "categoryType": category_type,
        "dsName": ds_name,
        "dsType": ds_type_value,
    }
    body = client.list_meta_data_component_page(request).body

    if not getattr(body, "success", False):
        return _failed(
            getattr(body, "err_code", "UNKNOWN"),
            getattr(body, "err_message", "ListMetaDataComponentPage failed"),
            request_id_of(body),
        )

    matches = body.data or []
    if not matches:
        return {
            "status": "empty",
            "ds_name": ds_name,
            "request_id": request_id_of(body),
        }

    # Convert SDK response objects to plain dicts for JSON serialization
    serialized_matches = []
    for match in matches:
        serialized_matches.append({
            "id": getattr(match, "id", None),
            "ds_name": getattr(match, "ds_name", None),
            "ds_type": getattr(match, "ds_type", None),
            "category_type": getattr(match, "category_type", None),
            "ds_status": getattr(match, "ds_status", None),
        })

    return {
        "status": "match",
        "matches": serialized_matches,
        "match_count": len(serialized_matches),
        "ds_name": ds_name,
        "request_id": request_id_of(body),
    }


def check_name(config, ds_name: str) -> Dict[str, Any]:
    """Single step: validate datasource name uniqueness (ExecMetaDataComponentName).

    Args:
        config: LHM configuration.
        ds_name: Candidate datasource name.

    Returns:
        Status dict. "available" → name is free, caller proceeds.
        "exists" → name already exists or is invalid, caller asks the user for
        a new name and re-invokes. "failed" → API error.
    """
    client = create_client(config)
    request = {"dsName": ds_name}
    body = client.exec_meta_data_component_name(request).body

    name_taken = body.data is True or str(getattr(body, "data", "")).lower() == "true"
    if name_taken:
        return {
            "status": "exists",
            "ds_name": ds_name,
            "request_id": request_id_of(body),
        }

    return {
        "status": "available",
        "ds_name": ds_name,
        "request_id": request_id_of(body),
    }


def oss_key(config) -> Dict[str, Any]:
    """Single step: fetch OSS temporary credentials (GetMetaOssTempKey).

    Args:
        config: LHM configuration.

    Returns:
        Status dict. "ok" → carries `oss` with ak/policy/signature/security_token/
        dir/endpoint/bucket/expire and an `expired` flag the Agent must check
        before building the upload curl. "failed" → API error.
    """
    client = create_client(config)
    request = {}
    body = client.get_meta_oss_temp_key(request).body

    if not getattr(body, "success", False) or not body.data:
        return _failed(
            getattr(body, "err_code", "UNKNOWN"),
            getattr(body, "err_message", "GetMetaOssTempKey failed"),
            request_id_of(body),
        )

    cred = body.data
    expire = getattr(cred, "expire", 0)
    return {
        "status": "ok",
        "request_id": request_id_of(body),
        "expired": time.time() >= expire if expire else True,
        "oss": {
            "ak": getattr(cred, "ak", None),
            "endpoint": getattr(cred, "endpoint", None),
            "bucket": getattr(cred, "bucket", None),
            "policy": getattr(cred, "policy", None),
            "signature": getattr(cred, "signature", None),
            "expire": expire,
            "dir": getattr(cred, "dir", None),
            "security_token": getattr(cred, "security_token", None),
        },
    }


def _generate_oss_filename(local_file_path: str) -> str:
    """Build a timestamped, collision-safe OSS object filename.

    The local file is never renamed; only the OSS object key uses this name.
    """
    original_filename = os.path.basename(local_file_path)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"{timestamp}_{original_filename}"


def upload_file(config, local_file_path: str) -> Dict[str, Any]:
    """Single step: upload a local metadata file to OSS.

    Internally fetches STS credentials (GetMetaOssTempKey), generates a unique
    OSS object key ({YYYYMMDDHHmmss}_{basename}), and POSTs the file as
    multipart/form-data. The LOCAL file is NEVER renamed, moved, or modified —
    only the OSS object key uses the generated unique filename.

    Args:
        config: LHM configuration.
        local_file_path: Path to the local file to upload.

    Returns:
        Status dict. "ok" → carries `oss_filename` (the unique name the Agent
        must write back into dsConfig.source-file-path) and `oss_key` (the full
        object key). "failed" → credentials expired/invalid, file missing, or
        upload rejected by OSS.
    """
    import requests

    if not os.path.isfile(local_file_path):
        return _failed(
            "FILE_NOT_FOUND",
            f"Local file not found: {local_file_path}",
        )

    credential = oss_key(config)
    if credential.get("status") != "ok":
        return credential
    if credential.get("expired"):
        return _failed(
            "OSS_CREDENTIAL_EXPIRED",
            "OSS 临时凭证已过期，请重试",
            credential.get("request_id", ""),
        )

    oss = credential["oss"]
    oss_filename = _generate_oss_filename(local_file_path)
    oss_object_key = f"{oss['dir']}{oss_filename}"
    upload_url = f"https://{oss['bucket']}.{oss['endpoint']}/"

    form_fields = {
        "key": oss_object_key,
        "policy": oss["policy"],
        "OSSAccessKeyId": oss["ak"],
        "signature": oss["signature"],
        "x-oss-security-token": oss["security_token"],
    }

    try:
        with open(local_file_path, "rb") as file_handle:
            files = {"file": (os.path.basename(local_file_path), file_handle)}
            response = requests.post(
                upload_url, data=form_fields, files=files, timeout=300
            )
    except requests.RequestException as upload_error:
        return _failed("OSS_UPLOAD_ERROR", str(upload_error))

    if response.status_code not in (200, 204):
        return _failed(
            "OSS_UPLOAD_REJECTED",
            f"OSS upload failed with HTTP {response.status_code}: "
            f"{response.text[:500]}",
        )

    return {
        "status": "ok",
        "oss_filename": oss_filename,
        "oss_key": oss_object_key,
        "request_id": credential.get("request_id", ""),
    }


def create_datasource(
    config,
    ds_name: str,
    category_type: str,
    ds_type: str,
    ds_config: Dict[str, Any],
    ds_status: int = 0,
) -> Dict[str, Any]:
    """Single step: create a datasource (AddMetaDataComponent).

    The `ds_config` object is serialized to a JSON string here, as required by
    the API. Any OSS file upload and `source-file-path` rewrite must be done by
    the Agent BEFORE calling this step.

    Args:
        config: LHM configuration.
        ds_name: Datasource name.
        category_type: Datasource category (e.g. "WORKFLOW").
        ds_type: Datasource technical type.
        ds_config: dsConfig object (will be JSON-serialized).
        ds_status: Initial status code (default 0).

    Returns:
        Status dict. "ok" → carries `ds_id` (new datasource id).
        "failed" → API error.
    """
    client = create_client(config)
    request = {
        "dsName": ds_name,
        "categoryType": category_type,
        "dsType": ds_type,
        "dsConfig": json.dumps(ds_config, ensure_ascii=False),
        "dsStatus": ds_status,
    }
    body = client.add_meta_data_component(request).body

    if not getattr(body, "success", False):
        return _failed(
            getattr(body, "err_code", "UNKNOWN"),
            getattr(body, "err_message", "AddMetaDataComponent failed"),
            request_id_of(body),
        )

    return {
        "status": "ok",
        "ds_id": body.data,
        "ds_name": ds_name,
        "request_id": request_id_of(body),
    }


def test_connectivity(
    config,
    ds_name: str,
    ds_type: str,
    ds_version: str,
    ds_config: Dict[str, Any],
    ds_id: int = None,
) -> Dict[str, Any]:
    """Single step: test datasource connectivity (ExecWorkflowConnectivity).

    Args:
        config: LHM configuration.
        ds_name: Datasource name.
        ds_type: Datasource technical type.
        ds_version: Datasource version (dsConfig.dsVersion).
        ds_config: dsConfig object (will be JSON-serialized).
        ds_id: Optional datasource id to associate the check with.

    Returns:
        Status dict. "ok" → connectivity passed. "failed" → connectivity failed
        or API error (carries err_code / err_message).
    """
    client = create_client(config)
    request = {
        "dsName": ds_name,
        "dsConfig": json.dumps(ds_config, ensure_ascii=False),
        "dsType": ds_type,
        "dsVersion": ds_version,
    }
    if ds_id is not None:
        request["id"] = ds_id
    body = client.exec_workflow_connectivity(request).body

    if getattr(body, "success", False):
        return {"status": "ok", "ds_name": ds_name, "request_id": request_id_of(body)}

    return _failed(
        getattr(body, "err_code", "UNKNOWN"),
        getattr(body, "err_message", "Connectivity check failed"),
        request_id_of(body),
    )
