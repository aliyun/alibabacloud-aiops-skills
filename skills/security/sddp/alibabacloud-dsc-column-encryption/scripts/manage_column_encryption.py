#!/usr/bin/env python3
"""Safely run the non-create write actions used by the DSC DE page.

The script targets Sddp 2026-01-20. Local dry-run is the default. Every
production write requires a fresh online preflight and its exact confirmation
token. A write is submitted once only; ambiguous outcomes are followed by
read-only verification and are never retried automatically.
"""

from __future__ import annotations

import argparse
import copy
import hmac
import json
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from create_column_encryption import (
    ALGORITHMS,
    API_VERSION,
    KEY_MODES,
    MAX_EXPIRE_TIME_MS,
    PRODUCT_IDS,
    REGION_PATTERN,
    ConfigError,
    CliProfile,
    bind_authentication,
    build_client,
    load_json_object,
    page_count,
    page_item_signature,
    parse_page_items,
    plan_token,
    resolve_profile,
    rpc,
    rpc_product as cli_rpc_product,
)
from aliyun_cli import print_safe_error_diagnostics, safe_error, safe_error_fields


DELETE_ACTION = "DeleteDataMaskingRule"
UPDATE_USERS_ACTION = "UpdateDataMaskingUsers"
UPDATE_ENCRYPTION_ACTION = "UpdateDataMaskingEncryptionAlgorithm"
SYNC_ASSETS_ACTION = "SyncDataAssets"
UPGRADE_KERNEL_ACTION = "UpgradeKernelVersion"

WRITE_ACTIONS = (
    DELETE_ACTION,
    UPDATE_USERS_ACTION,
    UPDATE_ENCRYPTION_ACTION,
    SYNC_ASSETS_ACTION,
    UPGRADE_KERNEL_ACTION,
)

CHECK_ACTION = "CheckDataMaskingInstance"
ATTRIBUTE_ACTION = "GetInstanceAttribute"
ALGORITHM_ACTION = "ListDataMaskingEncryptionAlgorithms"
KMS_KEYS_ACTION = "ListKmsKeys"
COLUMN_LIST_ACTION = "ListDataMaskingColumns"
INSTANCE_LIST_ACTION = "ListDataMaskingInstances"
ACCOUNT_LIST_ACTION = "ListDataAssetAccounts"
TEMPLATE_LIST_ACTION = "ListTemplates"
REGION_LIST_ACTION = "ListRegions"
KERNEL_LIST_ACTION = "ListMiniEngineVersions"

AUTH_ROLES = {"fullAccess", "restrictedAccess", "noneAccess"}
EXPIRY_OPERATIONS = {"PRESERVE", "CLEAR", "SET"}
UPGRADE_TIMES = {"Immediate", "MaintainTime", "SpecifyTime"}
FAILED_COLUMN_STATUSES = {"Failed", "DeleteFailed"}
DELETED_COLUMN_STATUSES = {"NotEncrypted", "NotVisible"}

LEGACY_OR_PRIVATE_FIELDS = {
    "ServiceRegionId",
    "BackendRegionId",
    "ResourceGroupId",
    "CooperationChannel",
}
COMMON_FIELDS = {"Action", "RegionId", "ProductCode"}
FIELDS_BY_ACTION = {
    DELETE_ACTION: COMMON_FIELDS
    | {"TemplateId", "ProductId", "InstanceId", "EngineType", "SubRuleList", "Lang"},
    UPDATE_USERS_ACTION: COMMON_FIELDS
    | {"ProductId", "AuthRole", "UserList", "Lang", "ExpireTimeOperation", "ExpireTime"},
    UPDATE_ENCRYPTION_ACTION: COMMON_FIELDS
    | {
        "ProductId",
        "InstanceId",
        "EncryptionAlgorithm",
        "EncryptionKeyMode",
        "EncryptionKeyId",
        "Lang",
    },
    # ProductId is private in the SyncDataAssets AMP contract.
    SYNC_ASSETS_ACTION: COMMON_FIELDS,
    UPGRADE_KERNEL_ACTION: COMMON_FIELDS
    | {"ProductId", "InstanceId", "UpgradeTime", "SwitchTime", "KernelVersion", "Lang"},
}
SUB_RULE_FIELDS = {"DbName", "TableName", "Columns"}
USER_FIELDS = {"AccountId", "InstanceId"}


def _require_nonblank(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{name} must be a non-empty string")
    return value.strip()


def _require_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"{name} must be an integer")
    return value


def _split_columns(value: Any, name: str) -> List[str]:
    if not isinstance(value, str):
        raise ConfigError(f"{name} must be a comma-separated string")
    result: List[str] = []
    seen = set()
    for raw in value.split(","):
        column = raw.strip()
        if column and column not in seen:
            seen.add(column)
            result.append(column)
    if not result:
        raise ConfigError(f"{name} must contain at least one column")
    return result


def _normalize_product(raw: Mapping[str, Any]) -> Tuple[str, Optional[int]]:
    product_code = _require_nonblank(raw.get("ProductCode"), "ProductCode")
    if product_code not in PRODUCT_IDS:
        raise ConfigError(f"ProductCode must be one of: {', '.join(PRODUCT_IDS)}")
    product_id = raw.get("ProductId")
    if product_id is not None:
        product_id = _require_int(product_id, "ProductId")
        expected = PRODUCT_IDS[product_code]
        if product_id != expected:
            raise ConfigError(
                f"ProductId {product_id} conflicts with ProductCode {product_code}; expected {expected}"
            )
    return product_code, product_id


def _normalize_sub_rules(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ConfigError("SubRuleList must be a non-empty array")
    grouped: Dict[Tuple[str, str], List[str]] = {}
    seen_by_table: Dict[Tuple[str, str], set[str]] = {}
    for index, item in enumerate(value):
        name = f"SubRuleList[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{name} must be an object")
        extra = set(item) - SUB_RULE_FIELDS
        if extra:
            raise ConfigError(f"{name} has unsupported fields: {', '.join(sorted(extra))}")
        db_name = _require_nonblank(item.get("DbName"), f"{name}.DbName")
        table_name = _require_nonblank(item.get("TableName"), f"{name}.TableName")
        columns = _split_columns(item.get("Columns"), f"{name}.Columns")
        key = (db_name, table_name)
        destination = grouped.setdefault(key, [])
        seen = seen_by_table.setdefault(key, set())
        for column in columns:
            if column not in seen:
                seen.add(column)
                destination.append(column)
    return [
        {"DbName": db, "TableName": table, "Columns": ",".join(columns)}
        for (db, table), columns in grouped.items()
    ]


def _normalize_users(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list) or not value:
        raise ConfigError("UserList must be a non-empty array")
    result: List[Dict[str, str]] = []
    seen = set()
    for index, item in enumerate(value):
        name = f"UserList[{index}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{name} must be an object")
        extra = set(item) - USER_FIELDS
        if extra:
            raise ConfigError(f"{name} has unsupported fields: {', '.join(sorted(extra))}")
        account_id = _require_nonblank(item.get("AccountId"), f"{name}.AccountId")
        instance_id = _require_nonblank(item.get("InstanceId"), f"{name}.InstanceId")
        key = (instance_id, account_id)
        if key not in seen:
            seen.add(key)
            result.append({"AccountId": account_id, "InstanceId": instance_id})
    return result


def normalize_config(raw: Mapping[str, Any], *, now_ms: Optional[int] = None) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConfigError("config must be a JSON object")
    action = _require_nonblank(raw.get("Action"), "Action")
    if action not in WRITE_ACTIONS:
        raise ConfigError(f"Action must be one of: {', '.join(WRITE_ACTIONS)}")

    unknown = set(raw) - FIELDS_BY_ACTION[action]
    legacy = unknown & LEGACY_OR_PRIVATE_FIELDS
    if legacy:
        raise ConfigError(
            "legacy/private fields are not allowed: " + ", ".join(sorted(legacy))
        )
    if unknown:
        if "TemplateId" in unknown:
            raise ConfigError(
                f"TemplateId does not scope {action}; it is only a query context for create/delete column selection"
            )
        if action == SYNC_ASSETS_ACTION and "ProductId" in unknown:
            raise ConfigError("ProductId is private for SyncDataAssets; use ProductCode")
        raise ConfigError(f"unsupported fields for {action}: {', '.join(sorted(unknown))}")

    region_id = _require_nonblank(raw.get("RegionId"), "RegionId")
    if not REGION_PATTERN.fullmatch(region_id):
        raise ConfigError("RegionId may contain only lowercase letters, digits, and hyphens")
    product_code, product_id = _normalize_product(raw)
    normalized: Dict[str, Any] = {
        "Action": action,
        "RegionId": region_id,
        "ProductCode": product_code,
    }
    if product_id is not None:
        normalized["ProductId"] = product_id
    if raw.get("Lang") is not None:
        normalized["Lang"] = _require_nonblank(raw.get("Lang"), "Lang")

    if action == DELETE_ACTION:
        normalized["InstanceId"] = _require_nonblank(raw.get("InstanceId"), "InstanceId")
        normalized["SubRuleList"] = _normalize_sub_rules(raw.get("SubRuleList"))
        if raw.get("EngineType") is not None:
            normalized["EngineType"] = _require_nonblank(raw.get("EngineType"), "EngineType")
        if raw.get("TemplateId") is not None:
            template_id = _require_int(raw.get("TemplateId"), "TemplateId")
            if template_id <= 0:
                raise ConfigError("TemplateId must be greater than zero")
            normalized["TemplateId"] = template_id

    elif action == UPDATE_USERS_ACTION:
        auth_role = _require_nonblank(raw.get("AuthRole"), "AuthRole")
        if auth_role not in AUTH_ROLES:
            raise ConfigError(f"AuthRole must be one of: {', '.join(sorted(AUTH_ROLES))}")
        normalized["AuthRole"] = auth_role
        normalized["UserList"] = _normalize_users(raw.get("UserList"))
        if auth_role != "fullAccess":
            if "ExpireTimeOperation" in raw or "ExpireTime" in raw:
                raise ConfigError(
                    "ExpireTimeOperation and ExpireTime must be omitted unless AuthRole is fullAccess"
                )
        else:
            operation = raw.get("ExpireTimeOperation", "PRESERVE")
            operation = _require_nonblank(operation, "ExpireTimeOperation").upper()
            if operation not in EXPIRY_OPERATIONS:
                raise ConfigError("ExpireTimeOperation must be PRESERVE, CLEAR, or SET")
            normalized["ExpireTimeOperation"] = operation
            expire_time = raw.get("ExpireTime")
            if operation == "SET":
                expire_time = _require_int(expire_time, "ExpireTime")
                expire_time = (expire_time // 1000) * 1000
                current_ms = int(time.time() * 1000) if now_ms is None else now_ms
                if expire_time <= current_ms:
                    raise ConfigError("ExpireTime must be in the future")
                if expire_time > MAX_EXPIRE_TIME_MS:
                    raise ConfigError("ExpireTime must not exceed 2038-01-01T10:10:10Z")
                normalized["ExpireTime"] = expire_time
            elif expire_time is not None:
                raise ConfigError(f"ExpireTime must be omitted when ExpireTimeOperation is {operation}")

    elif action == UPDATE_ENCRYPTION_ACTION:
        normalized["InstanceId"] = _require_nonblank(raw.get("InstanceId"), "InstanceId")
        algorithm = _require_nonblank(raw.get("EncryptionAlgorithm"), "EncryptionAlgorithm").upper()
        if algorithm not in ALGORITHMS:
            raise ConfigError(
                f"EncryptionAlgorithm must be one of: {', '.join(sorted(ALGORITHMS))}"
            )
        normalized["EncryptionAlgorithm"] = algorithm
        key_id = raw.get("EncryptionKeyId")
        if key_id is not None:
            key_id = _require_nonblank(key_id, "EncryptionKeyId")
        key_mode = raw.get("EncryptionKeyMode")
        if key_mode is None:
            key_mode = "kms_key" if key_id else "client_key"
        else:
            key_mode = _require_nonblank(key_mode, "EncryptionKeyMode").lower()
        if key_mode not in KEY_MODES:
            raise ConfigError("EncryptionKeyMode must be client_key or kms_key")
        if key_mode == "kms_key" and not key_id:
            raise ConfigError("EncryptionKeyId is required for kms_key")
        if key_mode == "client_key" and key_id:
            raise ConfigError("EncryptionKeyId must be omitted for client_key")
        normalized["EncryptionKeyMode"] = key_mode
        if key_id:
            normalized["EncryptionKeyId"] = key_id

    elif action == UPGRADE_KERNEL_ACTION:
        normalized["InstanceId"] = _require_nonblank(raw.get("InstanceId"), "InstanceId")
        requested_time = _require_nonblank(raw.get("UpgradeTime"), "UpgradeTime")
        canonical_times = {value.lower(): value for value in UPGRADE_TIMES}
        if requested_time.lower() not in canonical_times:
            raise ConfigError(f"UpgradeTime must be one of: {', '.join(sorted(UPGRADE_TIMES))}")
        upgrade_time = canonical_times[requested_time.lower()]
        normalized["UpgradeTime"] = upgrade_time
        normalized["KernelVersion"] = _require_nonblank(raw.get("KernelVersion"), "KernelVersion")
        switch_time = raw.get("SwitchTime")
        if upgrade_time == "SpecifyTime":
            switch_time = _require_int(switch_time, "SwitchTime")
            current_ms = int(time.time() * 1000) if now_ms is None else now_ms
            if switch_time <= current_ms:
                raise ConfigError("SwitchTime must be a future Unix millisecond timestamp")
            normalized["SwitchTime"] = switch_time
        elif switch_time is not None:
            raise ConfigError(f"SwitchTime must be omitted when UpgradeTime is {upgrade_time}")

    return normalized


def _items(response: Mapping[str, Any], field: str = "Items") -> List[Dict[str, Any]]:
    value = response.get(field, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for nested in value.values():
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.lower() == "true"


def _success_code(value: Any) -> bool:
    return isinstance(value, str) and value.lower() == "success"


def _available_algorithm(item: Mapping[str, Any]) -> bool:
    error_code = item.get("ErrorCode")
    return error_code in (None, "") or _success_code(error_code)


def _sanitize_error(exc: Exception, profile: CliProfile) -> str:
    return safe_error(exc)


def _clean(params: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in params.items() if value is not None and value != ""}


def _identity(config: Mapping[str, Any], instance_id: Optional[str] = None) -> Dict[str, Any]:
    return _clean(
        {
            "ProductCode": config["ProductCode"],
            "ProductId": config.get("ProductId"),
            "InstanceId": instance_id or config.get("InstanceId"),
            "Lang": config.get("Lang"),
        }
    )


def _paged_items(
    client: Any,
    region_id: str,
    action: str,
    params: Mapping[str, Any],
    *,
    page_size: int = 100,
    max_pages: int = 100,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    combined: List[Dict[str, Any]] = []
    request_ids: List[str] = []
    seen_item_signatures = set()
    total_count: Optional[int] = None
    server_page_size: Optional[int] = None
    pages = 0
    complete = False
    for page in range(1, max_pages + 1):
        response = rpc(
            client,
            region_id,
            action,
            {**_clean(params), "CurrentPage": page, "PageSize": page_size},
        )
        pages += 1
        try:
            reported_total = page_count(action, response)
            current = parse_page_items(action, response, reported_total)
            reported_size = page_count(action, response, "PageSize", minimum=1)
        except ConfigError as exc:
            raise RuntimeError(str(exc)) from exc
        if reported_total is not None:
            if total_count is not None and total_count != reported_total:
                raise RuntimeError(f"{action} changed TotalCount during pagination; repeat the read-only preflight")
            total_count = reported_total
        if reported_size is not None:
            if server_page_size is not None and server_page_size != reported_size:
                raise RuntimeError(f"{action} changed PageSize during pagination; the result is incomplete")
            server_page_size = reported_size
        item_signatures = {page_item_signature(action, item, params) for item in current}
        if len(item_signatures) != len(current) or seen_item_signatures.intersection(item_signatures):
            raise RuntimeError(f"{action} repeated a page or returned overlapping items; the result is incomplete")
        seen_item_signatures.update(item_signatures)
        combined.extend(current)
        if isinstance(response.get("RequestId"), str):
            request_ids.append(response["RequestId"])
        if total_count is not None:
            if len(combined) > total_count:
                raise RuntimeError(f"{action} returned more items than TotalCount; the result is incomplete")
            if len(combined) == total_count:
                complete = True
                break
        if not current and total_count is not None:
            raise RuntimeError(f"{action} ended before TotalCount; the result is incomplete")
        if total_count is None and (
            not current or (server_page_size is not None and len(current) < server_page_size)
        ):
            complete = True
            break
        time.sleep(0.02)
    if not complete:
        raise RuntimeError(f"{action} exceeded {max_pages} pages; the result is incomplete")
    return combined, {
        "Pages": pages,
        "ReturnedCount": len(combined),
        "TotalCount": total_count,
        "RequestIds": request_ids,
        "Complete": True,
    }


def _template_check(client: Any, config: Mapping[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    template_id = config.get("TemplateId")
    if template_id is None:
        return True, {"Skipped": True, "Reason": "TemplateId was not specified"}
    items, meta = _paged_items(
        client,
        config["RegionId"],
        TEMPLATE_LIST_ACTION,
        {"Lang": config.get("Lang")},
        page_size=50,
    )
    match = next((item for item in items if str(item.get("Id")) == str(template_id)), None)
    return match is not None, {
        **meta,
        "TemplateId": template_id,
        "Found": match is not None,
        "TemplateName": match.get("Name") if match else None,
    }


def _instance_checks(
    client: Any,
    config: Mapping[str, Any],
    instance_id: str,
    *,
    require_eligibility: bool,
) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any], Optional[str]]:
    region_id = config["RegionId"]
    base = _identity(config, instance_id)
    checks: Dict[str, Any] = {}
    if require_eligibility:
        eligibility = rpc(client, region_id, CHECK_ACTION, base)
        checks[CHECK_ACTION] = {
            "RequestId": eligibility.get("RequestId"),
            "ErrorCode": eligibility.get("ErrorCode"),
            "ErrorMessage": eligibility.get("ErrorMessage"),
        }
        if not _success_code(eligibility.get("ErrorCode")):
            return None, checks, f"{instance_id} did not pass CheckDataMaskingInstance"

    attribute = rpc(client, region_id, ATTRIBUTE_ACTION, base)
    public_attribute = {
        "RequestId": attribute.get("RequestId"),
        "Engine": attribute.get("Engine"),
        "EngineVersion": attribute.get("EngineVersion"),
        "CurrentKernelVersion": attribute.get("CurrentKernelVersion"),
        "Status": attribute.get("Status"),
        "KmsEncryptionSupported": attribute.get("KmsEncryptionSupported"),
        "MaintainStartTime": attribute.get("MaintainStartTime"),
        "MaintainEndTime": attribute.get("MaintainEndTime"),
        "ErrorCode": attribute.get("ErrorCode"),
        "ErrorMessage": attribute.get("ErrorMessage"),
    }
    checks[ATTRIBUTE_ACTION] = public_attribute
    error_code = attribute.get("ErrorCode")
    if error_code not in (None, "") and not _success_code(error_code):
        return None, checks, f"GetInstanceAttribute failed for {instance_id}"
    engine = attribute.get("Engine")
    if not isinstance(engine, str) or not engine.strip():
        return None, checks, f"GetInstanceAttribute did not return Engine for {instance_id}"
    return attribute, checks, None


def _target_columns(config: Mapping[str, Any]) -> List[Tuple[str, str, str]]:
    targets: List[Tuple[str, str, str]] = []
    for rule in config.get("SubRuleList", []):
        for column in _split_columns(rule["Columns"], "SubRuleList.Columns"):
            targets.append((rule["DbName"], rule["TableName"], column))
    return targets


def _query_column(
    client: Any,
    config: Mapping[str, Any],
    db_name: str,
    table_name: str,
    column_name: str,
) -> Dict[str, Any]:
    params = _clean(
        {
            "ProductCode": config["ProductCode"],
            "ProductId": config.get("ProductId"),
            "InstanceId": config["InstanceId"],
            "EngineType": config.get("EngineType"),
            "TemplateId": config.get("TemplateId"),
            "DbName": db_name,
            "TableName": table_name,
            "ColumnName": column_name,
            "Lang": config.get("Lang"),
        }
    )
    # ColumnName is a substring filter in SlsColumnServiceImpl. A target can
    # therefore be on a later page even with a fully specified database/table.
    items, meta = _paged_items(client, config["RegionId"], COLUMN_LIST_ACTION, params)
    exact = next(
        (
            item
            for item in items
            if item.get("DbName") == db_name
            and item.get("TableName") == table_name
            and item.get("Name") == column_name
        ),
        None,
    )
    if exact is None:
        if any(
            not isinstance(item.get(field), str) or not item[field].strip()
            for item in items
            for field in ("DbName", "TableName", "Name")
        ):
            raise RuntimeError(f"{COLUMN_LIST_ACTION} returned an incomplete column identity; absence is unverified")
        return {
            "DbName": db_name,
            "TableName": table_name,
            "ColumnName": column_name,
            "Status": "NotVisible",
            "Query": meta,
        }
    return {
        "DbName": db_name,
        "TableName": table_name,
        "ColumnName": column_name,
        "Status": exact.get("MaskingStatus") or "Unknown",
        "RuleId": exact.get("RuleId"),
        "RuleName": exact.get("RuleName"),
        "ErrorCode": exact.get("ErrorCode"),
        "ErrorMessage": exact.get("ErrorMessage"),
        "Query": meta,
    }


def _query_account(
    client: Any,
    config: Mapping[str, Any],
    instance_id: str,
    account_id: str,
) -> Dict[str, Any]:
    items, meta = _paged_items(
        client,
        config["RegionId"],
        ACCOUNT_LIST_ACTION,
        {
            "ProductCode": config["ProductCode"],
            "InstanceId": instance_id,
            "AccountName": account_id,
            "Lang": config.get("Lang"),
        },
    )
    exact = next(
        (
            item
            for item in items
            if item.get("AccountName") == account_id
            and item.get("InstanceId") in (None, "", instance_id)
        ),
        None,
    )
    if exact is None:
        return {
            "InstanceId": instance_id,
            "AccountId": account_id,
            "Found": False,
            "Query": meta,
        }
    return {
        "InstanceId": instance_id,
        "AccountId": account_id,
        "Found": True,
        "AuthRole": exact.get("AuthRole"),
        "ExpireTime": exact.get("ExpireTime"),
        "EncryptionKeyMode": exact.get("EncryptionKeyMode"),
        "EngineType": exact.get("EngineType"),
        "ProductCode": exact.get("ProductCode"),
        "Query": meta,
    }


def _instance_record(client: Any, config: Mapping[str, Any]) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    items, meta = _paged_items(
        client,
        config["RegionId"],
        INSTANCE_LIST_ACTION,
        {
            "ProductCode": config["ProductCode"],
            "ProductId": config.get("ProductId"),
            "InstanceId": config["InstanceId"],
            "TemplateId": config.get("TemplateId"),
            "Lang": config.get("Lang"),
        },
    )
    exact = next((item for item in items if item.get("InstanceId") == config["InstanceId"]), None)
    return exact, meta


def _active_rule_snapshot(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    request_ids: List[str] = []
    for status in ("Success", "Failed"):
        response = rpc(
            client,
            config["RegionId"],
            COLUMN_LIST_ACTION,
            {
                **_identity(config),
                "MaskingStatus": status,
                "CurrentPage": 1,
                "PageSize": 1,
            },
        )
        total = response.get("TotalCount")
        counts[status] = total if isinstance(total, int) else len(_items(response))
        if isinstance(response.get("RequestId"), str):
            request_ids.append(response["RequestId"])
    return {"Counts": counts, "RequestIds": request_ids, "HasActiveRule": any(counts.values())}


def _supported_roles(product_code: str, engine: str) -> set[str]:
    engine_key = engine.strip().lower()
    if product_code == "RDS" and engine_key == "mysql":
        return {"fullAccess", "restrictedAccess", "noneAccess"}
    if product_code == "RDS" and engine_key == "postgresql":
        return {"fullAccess", "restrictedAccess"}
    if product_code == "POLARDB" and engine_key in {"mysql", "postgresql", "oracle"}:
        return {"fullAccess", "restrictedAccess"}
    if product_code == "PolarDBX2":
        return {"fullAccess", "restrictedAccess"}
    return set()


def _supports_encryption_update(product_code: str, engine: str) -> bool:
    engine_key = engine.strip().lower()
    return (product_code == "RDS" and engine_key == "mysql") or product_code == "PolarDBX2"


def _rpc_product(
    client: Any,
    region_id: str,
    product: str,
    version: str,
    action: str,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    return cli_rpc_product(client, region_id, product, version, action, _clean(params))


def write_params(config: Mapping[str, Any]) -> Dict[str, Any]:
    action = config["Action"]
    names = {
        DELETE_ACTION: {
            "ProductId",
            "ProductCode",
            "InstanceId",
            "EngineType",
            "SubRuleList",
            "Lang",
        },
        UPDATE_USERS_ACTION: {
            "ProductId",
            "ProductCode",
            "AuthRole",
            "UserList",
            "Lang",
            "ExpireTimeOperation",
            "ExpireTime",
        },
        UPDATE_ENCRYPTION_ACTION: {
            "ProductId",
            "ProductCode",
            "InstanceId",
            "EncryptionAlgorithm",
            "EncryptionKeyId",
            "Lang",
        },
        SYNC_ASSETS_ACTION: {"ProductCode"},
        UPGRADE_KERNEL_ACTION: {
            "ProductId",
            "ProductCode",
            "InstanceId",
            "UpgradeTime",
            "SwitchTime",
            "KernelVersion",
            "Lang",
        },
    }[action]
    return {name: copy.deepcopy(config[name]) for name in names if name in config}


def _base_plan(config: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "Action": config["Action"],
        "ApiVersion": API_VERSION,
        "Endpoint": f"sddp.{config['RegionId']}.aliyuncs.com",
        "RegionId": config["RegionId"],
        "ProductCode": config["ProductCode"],
        "ProductId": config.get("ProductId", PRODUCT_IDS[config["ProductCode"]]),
    }


def _preflight_failure(
    config: Mapping[str, Any], checks: Mapping[str, Any], error: str
) -> Dict[str, Any]:
    return {
        "Mode": "PREFLIGHT",
        "Action": config["Action"],
        "Passed": False,
        "Checks": dict(checks),
        "Error": error,
    }


def _finish_preflight(
    config: Mapping[str, Any],
    checks: Mapping[str, Any],
    current_state: Any,
    effective_plan: Mapping[str, Any],
) -> Dict[str, Any]:
    material = {
        "Action": config["Action"],
        "RegionId": config["RegionId"],
        "WriteParameters": write_params(config),
        "QueryContext": {"TemplateId": config.get("TemplateId")},
        "CurrentState": current_state,
    }
    token = plan_token(material)
    return {
        "Mode": "PREFLIGHT",
        "Action": config["Action"],
        "Passed": True,
        "Checks": dict(checks),
        "EffectivePlan": dict(effective_plan),
        "WriteParameters": write_params(config),
        "ConfirmationToken": token,
        "_EffectiveConfig": dict(config),
        "_ConfirmationMaterial": material,
    }


def _preflight_delete(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    effective = copy.deepcopy(dict(config))
    checks: Dict[str, Any] = {}
    template_ok, template_check = _template_check(client, effective)
    checks[TEMPLATE_LIST_ACTION] = template_check
    if not template_ok:
        return _preflight_failure(effective, checks, "TemplateId was not returned by ListTemplates")

    attribute, instance_checks, error = _instance_checks(
        client, effective, effective["InstanceId"], require_eligibility=True
    )
    checks.update(instance_checks)
    if error:
        return _preflight_failure(effective, checks, error)
    assert attribute is not None
    actual_engine = str(attribute["Engine"]).strip()
    hint = effective.get("EngineType")
    if hint and hint.lower() != actual_engine.lower():
        return _preflight_failure(
            effective,
            checks,
            f"EngineType hint {hint} conflicts with actual engine {actual_engine}",
        )
    effective["EngineType"] = actual_engine

    columns = [
        _query_column(client, effective, db, table, column)
        for db, table, column in _target_columns(effective)
    ]
    checks[COLUMN_LIST_ACTION] = columns
    not_deletable = [item for item in columns if item.get("Status") != "Success"]
    if not_deletable:
        return _preflight_failure(
            effective,
            checks,
            "every exact delete target must currently have MaskingStatus=Success",
        )
    current_state = [
        {key: item.get(key) for key in ("DbName", "TableName", "ColumnName", "Status", "RuleId")}
        for item in columns
    ]
    plan = {
        **_base_plan(effective),
        "TemplateId": effective.get("TemplateId"),
        "InstanceId": effective["InstanceId"],
        "EngineType": actual_engine,
        "Targets": current_state,
        "UniqueColumnCount": len(columns),
        "DesiredState": "NotEncrypted or no longer visible",
        "Impact": "removes column-encryption rules for exactly the listed columns",
    }
    return _finish_preflight(effective, checks, current_state, plan)


def _desired_account_state(config: Mapping[str, Any], current: Mapping[str, Any]) -> Dict[str, Any]:
    if (config["AuthRole"] == "fullAccess"
            and config["ExpireTimeOperation"] == "PRESERVE"
            and current.get("AuthRole") == "unconfigured"):
        # The account API hides expiry without a visible masking rule, while
        # PRESERVE can retain a stored expiry from an older fullAccess grant.
        return {
            "InstanceId": current["InstanceId"],
            "AccountId": current["AccountId"],
            "AuthRole": "fullAccess",
            "ExpireTimeKnown": False,
            "VerificationNote": (
                "the original expiry is hidden for an unconfigured account; "
                "PRESERVE does not imply permanent access, and its preservation cannot be verified"
            ),
        }
    desired_expire: Optional[int]
    if config["AuthRole"] != "fullAccess":
        desired_expire = None
    else:
        operation = config["ExpireTimeOperation"]
        if operation == "SET":
            desired_expire = config["ExpireTime"]
        elif operation == "CLEAR":
            desired_expire = None
        else:
            desired_expire = current.get("ExpireTime")
    return {
        "InstanceId": current["InstanceId"],
        "AccountId": current["AccountId"],
        "AuthRole": config["AuthRole"],
        "ExpireTime": desired_expire,
    }


def _preflight_users(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    effective = copy.deepcopy(dict(config))
    checks: Dict[str, Any] = {CHECK_ACTION: {}, ATTRIBUTE_ACTION: {}, ACCOUNT_LIST_ACTION: []}
    engines: Dict[str, str] = {}
    encrypted_counts: Dict[str, int] = {}
    for instance_id in dict.fromkeys(item["InstanceId"] for item in effective["UserList"]):
        attribute, instance_checks, error = _instance_checks(
            client, effective, instance_id, require_eligibility=True
        )
        checks[CHECK_ACTION][instance_id] = instance_checks.get(CHECK_ACTION)
        checks[ATTRIBUTE_ACTION][instance_id] = instance_checks.get(ATTRIBUTE_ACTION)
        if error:
            return _preflight_failure(effective, checks, error)
        assert attribute is not None
        engine = str(attribute["Engine"]).strip()
        engines[instance_id] = engine
        supported = _supported_roles(effective["ProductCode"], engine)
        if effective["AuthRole"] not in supported:
            return _preflight_failure(
                effective,
                checks,
                f"{effective['AuthRole']} is not supported for {effective['ProductCode']} {engine}",
            )
        if effective["AuthRole"] == "noneAccess":
            # Account key mode alone also includes pending/failed initial
            # rules. The backend additionally requires an applied algorithm.
            # Its Success filter selects rules with current_enc_algorithm,
            # including still-encrypted columns after a failed modification.
            active = _active_rule_snapshot(client, {**effective, "InstanceId": instance_id})
            checks.setdefault(COLUMN_LIST_ACTION, {})[instance_id] = active
            encrypted_counts[instance_id] = active["Counts"]["Success"]
            if encrypted_counts[instance_id] <= 0:
                return _preflight_failure(
                    effective,
                    checks,
                    "noneAccess requires an already encrypted RDS MySQL client_key rule on every instance",
                )

    current_accounts: List[Dict[str, Any]] = []
    for user in effective["UserList"]:
        current = _query_account(
            client, effective, user["InstanceId"], user["AccountId"]
        )
        checks[ACCOUNT_LIST_ACTION].append(current)
        if not current["Found"]:
            return _preflight_failure(
                effective,
                checks,
                f"account {user['AccountId']} was not found on {user['InstanceId']}",
            )
        if current.get("ProductCode") not in (None, "", effective["ProductCode"]):
            return _preflight_failure(
                effective,
                checks,
                f"account {user['AccountId']} belongs to a different ProductCode",
            )
        if effective["AuthRole"] == "noneAccess" and current.get("EncryptionKeyMode") != "client_key":
            return _preflight_failure(
                effective,
                checks,
                "noneAccess requires an active RDS MySQL client_key column-encryption rule",
            )
        current_accounts.append(current)

    desired_accounts = [_desired_account_state(effective, current) for current in current_accounts]
    changes = [
        desired
        for current, desired in zip(current_accounts, desired_accounts)
        if current.get("AuthRole") != desired["AuthRole"]
        or current.get("ExpireTime") != desired.get("ExpireTime")
    ]
    if not changes:
        return _preflight_failure(effective, checks, "all selected accounts already have the desired state")

    current_state = [
        {
            "InstanceId": item["InstanceId"],
            "AccountId": item["AccountId"],
            "AuthRole": item.get("AuthRole"),
            "ExpireTime": item.get("ExpireTime"),
            **({"ExpireTimeVisible": False} if item.get("AuthRole") == "unconfigured" else {}),
            "EncryptionKeyMode": item.get("EncryptionKeyMode"),
            "EngineType": engines[item["InstanceId"]],
            **(
                {"ActiveEncryptedColumnCount": encrypted_counts[item["InstanceId"]]}
                if effective["AuthRole"] == "noneAccess" else {}
            ),
        }
        for item in current_accounts
    ]
    plan = {
        **_base_plan(effective),
        "Scope": "the exact (InstanceId, AccountId) pairs listed below",
        "AuthRole": effective["AuthRole"],
        "ExpireTimeOperation": effective.get("ExpireTimeOperation"),
        "ExpireTime": effective.get("ExpireTime"),
        "AccountsBefore": current_state,
        "AccountsAfter": desired_accounts,
        "ChangedAccountCount": len(changes),
        "Impact": "changes database account column-encryption visibility permissions",
        "VerificationLimitations": list(dict.fromkeys(
            item["VerificationNote"] for item in desired_accounts if item.get("VerificationNote")
        )),
    }
    return _finish_preflight(effective, checks, current_state, plan)


def _preflight_encryption(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    effective = copy.deepcopy(dict(config))
    checks: Dict[str, Any] = {}
    attribute, instance_checks, error = _instance_checks(
        client, effective, effective["InstanceId"], require_eligibility=True
    )
    checks.update(instance_checks)
    if error:
        return _preflight_failure(effective, checks, error)
    assert attribute is not None
    engine = str(attribute["Engine"]).strip()
    if not _supports_encryption_update(effective["ProductCode"], engine):
        return _preflight_failure(
            effective,
            checks,
            f"{effective['ProductCode']} {engine} does not support algorithm/key changes",
        )

    record, record_meta = _instance_record(client, effective)
    checks[INSTANCE_LIST_ACTION] = {"Query": record_meta, "ExactInstance": record}
    if record is None:
        return _preflight_failure(effective, checks, "the exact instance was not returned")
    active = _active_rule_snapshot(client, effective)
    checks[COLUMN_LIST_ACTION] = active
    if not active["HasActiveRule"]:
        return _preflight_failure(effective, checks, "the instance has no active Success/Failed rule to update")

    algorithms_response = rpc(
        client, effective["RegionId"], ALGORITHM_ACTION, _identity(effective)
    )
    algorithms = _items(algorithms_response, "Algorithms")
    checks[ALGORITHM_ACTION] = {
        "RequestId": algorithms_response.get("RequestId"),
        "Algorithms": [
            {
                "Name": item.get("Name"),
                "Available": _available_algorithm(item),
                "ErrorCode": item.get("ErrorCode"),
                "ErrorMessage": item.get("ErrorMessage"),
            }
            for item in algorithms
        ],
    }
    requested = effective["EncryptionAlgorithm"]
    if not any(item.get("Name") == requested and _available_algorithm(item) for item in algorithms):
        return _preflight_failure(
            effective, checks, f"{requested} is not currently available for this instance"
        )

    if effective["EncryptionKeyMode"] == "kms_key":
        if not _as_bool(attribute.get("KmsEncryptionSupported")):
            return _preflight_failure(effective, checks, "the instance does not support KMS encryption")
        key_response = rpc(client, effective["RegionId"], KMS_KEYS_ACTION, _identity(effective))
        key_id = effective["EncryptionKeyId"]
        matched = [item for item in _items(key_response) if item.get("KeyId") == key_id]
        checks[KMS_KEYS_ACTION] = {
            "RequestId": key_response.get("RequestId"),
            "RequestedKeyId": key_id,
            "Matched": bool(matched),
            "Aliases": sorted(
                {str(item.get("AliasName")) for item in matched if item.get("AliasName")}
            ),
        }
        if not matched:
            return _preflight_failure(effective, checks, "EncryptionKeyId was not returned by ListKmsKeys")
        detail = _rpc_product(
            client,
            effective["RegionId"],
            "kms",
            "2016-01-20",
            "DescribeKey",
            {"KeyId": key_id},
        )
        metadata = detail.get("KeyMetadata") or {}
        checks["KMS.DescribeKey"] = {
            "RequestId": detail.get("RequestId"),
            "KeyId": metadata.get("KeyId", key_id),
            "KeyState": metadata.get("KeyState"),
            "KeySpec": metadata.get("KeySpec"),
            "KeyUsage": metadata.get("KeyUsage"),
        }
        if metadata.get("KeyState") != "Enabled":
            return _preflight_failure(effective, checks, "the KMS key is not Enabled")

    current_key = record.get("EncryptionKeyId") or None
    desired_key = effective.get("EncryptionKeyId") or None
    if record.get("EncryptionAlgorithm") == requested and current_key == desired_key:
        return _preflight_failure(effective, checks, "algorithm and key are already unchanged")
    current_state = {
        "InstanceId": effective["InstanceId"],
        "EngineType": engine,
        "EncryptionAlgorithm": record.get("EncryptionAlgorithm"),
        "EncryptionKeyId": current_key,
        "RuleCounts": active["Counts"],
    }
    plan = {
        **_base_plan(effective),
        "InstanceId": effective["InstanceId"],
        "EngineType": engine,
        "Before": current_state,
        "After": {
            "EncryptionAlgorithm": requested,
            "EncryptionKeyMode": effective["EncryptionKeyMode"],
            "EncryptionKeyId": desired_key,
        },
        "Impact": "changes the encryption algorithm/key for every active rule on the instance",
        "ContractNote": "EncryptionKeyMode is confirmation context; AMP infers it from EncryptionKeyId",
    }
    return _finish_preflight(effective, checks, current_state, plan)


def _preflight_sync(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    effective = copy.deepcopy(dict(config))
    checks: Dict[str, Any] = {}
    regions = rpc(client, effective["RegionId"], REGION_LIST_ACTION, {})
    region_items = _items(regions, "RegionList")
    region_match = next(
        (item for item in region_items if item.get("RegionId") == effective["RegionId"]), None
    )
    checks[REGION_LIST_ACTION] = {
        "RequestId": regions.get("RequestId"),
        "RegionId": effective["RegionId"],
        "Found": region_match is not None,
        "RegionName": region_match.get("RegionName") if region_match else None,
    }
    if region_match is None:
        return _preflight_failure(effective, checks, "RegionId was not returned by ListRegions")

    inventory = rpc(
        client,
        effective["RegionId"],
        INSTANCE_LIST_ACTION,
        {"ProductCode": effective["ProductCode"], "CurrentPage": 1, "PageSize": 1},
    )
    visible_count = inventory.get("TotalCount")
    if not isinstance(visible_count, int):
        visible_count = len(_items(inventory))
    checks[INSTANCE_LIST_ACTION] = {
        "RequestId": inventory.get("RequestId"),
        "VisibleColumnEncryptionInstanceCount": visible_count,
    }
    current_state = {"VisibleColumnEncryptionInstanceCount": visible_count}
    plan = {
        **_base_plan(effective),
        "Scope": f"all {effective['ProductCode']} assets for the caller in {effective['RegionId']}",
        "CurrentVisibleColumnEncryptionInstanceCount": visible_count,
        "Impact": "starts product-wide asset, database, account and whitelist synchronization",
        "Verification": "the SDDP page exposes no read API that proves this sync completed",
    }
    return _finish_preflight(effective, checks, current_state, plan)


def _preflight_upgrade(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    effective = copy.deepcopy(dict(config))
    checks: Dict[str, Any] = {}
    attribute, instance_checks, error = _instance_checks(
        client, effective, effective["InstanceId"], require_eligibility=False
    )
    checks.update(instance_checks)
    if error:
        return _preflight_failure(effective, checks, error)
    assert attribute is not None
    engine = str(attribute["Engine"]).strip()
    if effective["ProductCode"] == "PolarDBX2" and effective["UpgradeTime"] == "SpecifyTime":
        return _preflight_failure(
            effective, checks, "PolarDBX2 supports only Immediate or MaintainTime"
        )

    versions_response = rpc(
        client, effective["RegionId"], KERNEL_LIST_ACTION, _identity(effective)
    )
    versions = _items(versions_response, "KernelVersions")
    target = next(
        (item for item in versions if item.get("KernelVersion") == effective["KernelVersion"]),
        None,
    )
    checks[KERNEL_LIST_ACTION] = {
        "RequestId": versions_response.get("RequestId"),
        "KernelVersions": versions,
        "RequestedKernelVersion": effective["KernelVersion"],
        "Matched": target is not None,
    }
    if target is None:
        return _preflight_failure(
            effective, checks, "KernelVersion was not returned by ListMiniEngineVersions"
        )
    current_version = attribute.get("CurrentKernelVersion")
    if current_version == effective["KernelVersion"]:
        return _preflight_failure(effective, checks, "the instance already uses KernelVersion")

    current_state = {
        "InstanceId": effective["InstanceId"],
        "EngineType": engine,
        "CurrentKernelVersion": current_version,
        "InstanceStatus": attribute.get("Status"),
    }
    switch_time = effective.get("SwitchTime")
    plan = {
        **_base_plan(effective),
        "InstanceId": effective["InstanceId"],
        "EngineType": engine,
        "CurrentKernelVersion": current_version,
        "Target": target,
        "UpgradeTime": effective["UpgradeTime"],
        "SwitchTime": switch_time,
        "SwitchTimeUtc": (
            datetime.fromtimestamp(switch_time / 1000, tz=timezone.utc).isoformat()
            if switch_time is not None
            else None
        ),
        "Impact": "starts a database kernel/proxy upgrade and may affect availability",
    }
    return _finish_preflight(effective, checks, current_state, plan)


def run_preflight(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        DELETE_ACTION: _preflight_delete,
        UPDATE_USERS_ACTION: _preflight_users,
        UPDATE_ENCRYPTION_ACTION: _preflight_encryption,
        SYNC_ASSETS_ACTION: _preflight_sync,
        UPGRADE_KERNEL_ACTION: _preflight_upgrade,
    }[config["Action"]](client, config)


def public_preflight_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def _poll_delete(
    client: Any,
    config: Mapping[str, Any],
    profile: CliProfile,
    *,
    wait_seconds: int,
    poll_interval: float,
    ambiguous: bool,
) -> Dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    last: List[Dict[str, Any]] = []
    while True:
        last = []
        for db, table, column in _target_columns(config):
            try:
                last.append(_query_column(client, config, db, table, column))
            except Exception as exc:
                print_safe_error_diagnostics(exc, file=sys.stderr)
                last.append(
                    {
                        "DbName": db,
                        "TableName": table,
                        "ColumnName": column,
                        "Status": "QueryError",
                        "ErrorMessage": _sanitize_error(exc, profile),
                        **safe_error_fields(exc),
                    }
                )
            time.sleep(0.02)
        statuses = [item["Status"] for item in last]
        if statuses and all(status in DELETED_COLUMN_STATUSES for status in statuses):
            return {"FinalState": "SUCCESS", "Columns": last}
        if any(status in FAILED_COLUMN_STATUSES for status in statuses):
            return {"FinalState": "FAILED", "Columns": last}
        if time.monotonic() >= deadline:
            state = "UNKNOWN" if ambiguous and all(s == "QueryError" for s in statuses) else "PENDING"
            return {"FinalState": state, "Columns": last}
        time.sleep(poll_interval)


def _poll_users(
    client: Any,
    config: Mapping[str, Any],
    preflight: Mapping[str, Any],
    profile: CliProfile,
    *,
    wait_seconds: int,
    poll_interval: float,
    ambiguous: bool,
) -> Dict[str, Any]:
    desired = preflight["EffectivePlan"]["AccountsAfter"]
    deadline = time.monotonic() + wait_seconds
    last: List[Dict[str, Any]] = []
    while True:
        last = []
        for item in desired:
            try:
                current = _query_account(
                    client, config, item["InstanceId"], item["AccountId"]
                )
                current["DesiredAuthRole"] = item["AuthRole"]
                expiry_known = item.get("ExpireTimeKnown", True)
                current["DesiredExpireTimeKnown"] = expiry_known
                if expiry_known:
                    current["DesiredExpireTime"] = item["ExpireTime"]
                else:
                    current["VerificationNote"] = item["VerificationNote"]
                current["ProductMatched"] = current.get("ProductCode") in (None, "", config["ProductCode"])
                current["RoleMatched"] = bool(
                    current.get("Found") and current.get("AuthRole") == item["AuthRole"]
                )
                current["Matched"] = (
                    current["ProductMatched"]
                    and current["RoleMatched"]
                    and expiry_known
                    and current.get("ExpireTime") == item.get("ExpireTime")
                )
                last.append(current)
            except Exception as exc:
                print_safe_error_diagnostics(exc, file=sys.stderr)
                last.append(
                    {
                        "InstanceId": item["InstanceId"],
                        "AccountId": item["AccountId"],
                        "Matched": False,
                        "QueryError": _sanitize_error(exc, profile),
                        **safe_error_fields(exc),
                    }
                )
            time.sleep(0.02)
        if last and all(item.get("Matched") for item in last):
            return {"FinalState": "SUCCESS", "Accounts": last}
        if time.monotonic() >= deadline:
            state = "UNKNOWN" if ambiguous and all(item.get("QueryError") for item in last) else "PENDING"
            limitations = list(dict.fromkeys(
                item["VerificationNote"] for item in desired if item.get("VerificationNote")
            ))
            return {"FinalState": state, "Accounts": last, "VerificationLimitations": limitations}
        time.sleep(poll_interval)


def _poll_encryption(
    client: Any,
    config: Mapping[str, Any],
    profile: CliProfile,
    *,
    wait_seconds: int,
    poll_interval: float,
    ambiguous: bool,
) -> Dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    last: Dict[str, Any] = {}
    while True:
        try:
            record, meta = _instance_record(client, config)
            last = {"Instance": record, "Query": meta}
            if record is not None:
                current_key = record.get("EncryptionKeyId") or None
                desired_key = config.get("EncryptionKeyId") or None
                if (
                    record.get("EncryptionAlgorithm") == config["EncryptionAlgorithm"]
                    and current_key == desired_key
                ):
                    return {"FinalState": "SUCCESS", **last}
        except Exception as exc:
            print_safe_error_diagnostics(exc, file=sys.stderr)
            last = {"QueryError": _sanitize_error(exc, profile), **safe_error_fields(exc)}
        if time.monotonic() >= deadline:
            state = "UNKNOWN" if ambiguous and last.get("QueryError") else "PENDING"
            return {"FinalState": state, **last}
        time.sleep(poll_interval)


def _poll_upgrade(
    client: Any,
    config: Mapping[str, Any],
    profile: CliProfile,
    *,
    wait_seconds: int,
    poll_interval: float,
    ambiguous: bool,
) -> Dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    last: Dict[str, Any] = {}
    while True:
        try:
            response = rpc(client, config["RegionId"], ATTRIBUTE_ACTION, _identity(config))
            last = {
                "RequestId": response.get("RequestId"),
                "CurrentKernelVersion": response.get("CurrentKernelVersion"),
                "TargetKernelVersion": config["KernelVersion"],
                "Status": response.get("Status"),
                "ErrorCode": response.get("ErrorCode"),
                "ErrorMessage": response.get("ErrorMessage"),
            }
            if response.get("CurrentKernelVersion") == config["KernelVersion"]:
                return {"FinalState": "SUCCESS", "InstanceAttribute": last}
        except Exception as exc:
            print_safe_error_diagnostics(exc, file=sys.stderr)
            last = {"QueryError": _sanitize_error(exc, profile), **safe_error_fields(exc)}
        if time.monotonic() >= deadline:
            state = "UNKNOWN" if ambiguous and last.get("QueryError") else "PENDING"
            return {"FinalState": state, "InstanceAttribute": last}
        time.sleep(poll_interval)


def verify_after_write(
    client: Any,
    config: Mapping[str, Any],
    preflight: Mapping[str, Any],
    profile: CliProfile,
    *,
    wait_seconds: int,
    poll_interval: float,
    ambiguous: bool,
) -> Dict[str, Any]:
    action = config["Action"]
    if action == SYNC_ASSETS_ACTION:
        if ambiguous:
            return {
                "FinalState": "UNKNOWN",
                "Verification": "no SDDP page read API can disambiguate whether SyncDataAssets was accepted",
            }
        return {
            "FinalState": "ACCEPTED_UNVERIFIED",
            "Verification": "request accepted; the SDDP page exposes no read API proving sync completion",
        }
    if action == DELETE_ACTION:
        return _poll_delete(
            client,
            config,
            profile,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
            ambiguous=ambiguous,
        )
    if action == UPDATE_USERS_ACTION:
        return _poll_users(
            client,
            config,
            preflight,
            profile,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
            ambiguous=ambiguous,
        )
    if action == UPDATE_ENCRYPTION_ACTION:
        return _poll_encryption(
            client,
            config,
            profile,
            wait_seconds=wait_seconds,
            poll_interval=poll_interval,
            ambiguous=ambiguous,
        )
    return _poll_upgrade(
        client,
        config,
        profile,
        wait_seconds=wait_seconds,
        poll_interval=poll_interval,
        ambiguous=ambiguous,
    )


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight, execute once, and verify DSC column-encryption write actions."
    )
    parser.add_argument("--config", required=True, help="JSON plan using Sddp 2026-01-20 fields")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="local validation only (default)")
    mode.add_argument("--preflight", action="store_true", help="run read-only online checks")
    mode.add_argument("--execute", action="store_true", help="submit the configured write exactly once")
    parser.add_argument("--confirm-token", help="exact token from a successful online preflight")
    parser.add_argument("--profile", default="dsc-oauth",
                        help="CLI profile: OAuth, AK, StsToken or RamRoleArn (default: dsc-oauth)")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=180,
        help="maximum read-only verification wait after execute (default: 180)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="seconds between verification polls (minimum: 1)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.confirm_token and not args.execute:
        raise ConfigError("--confirm-token is only valid with --execute")
    if args.execute and not args.confirm_token:
        raise ConfigError("--execute requires --confirm-token from online preflight")
    if args.wait_seconds < 0:
        raise ConfigError("--wait-seconds must be zero or greater")
    if args.poll_interval < 1:
        raise ConfigError("--poll-interval must be at least 1 second")

    normalized = normalize_config(load_json_object(args.config))
    if not args.preflight and not args.execute:
        draft_write_params = write_params(normalized)
        confirmation_only = {
            name: copy.deepcopy(value)
            for name, value in normalized.items()
            if name not in draft_write_params and name not in {"Action", "RegionId"}
        }
        print(
            json.dumps(
                {
                    "Mode": "DRY_RUN",
                    "Executable": False,
                    "DraftPlan": {
                        **_base_plan(normalized),
                        "WriteParameters": draft_write_params,
                        "ConfirmationOnlyContext": confirmation_only,
                    },
                    "DraftFingerprint": plan_token(normalized),
                    "NextStep": "Run --preflight; only its ConfirmationToken can authorize --execute.",
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    profile = resolve_profile(args.profile)
    client = build_client(profile, normalized["RegionId"])
    try:
        preflight = bind_authentication(run_preflight(client, normalized), profile)
    except Exception as exc:
        print_safe_error_diagnostics(exc, file=sys.stderr)
        print(
            json.dumps(
                {
                    "Mode": "PREFLIGHT",
                    "Action": normalized["Action"],
                    "Passed": False,
                    "Error": _sanitize_error(exc, profile),
                    **safe_error_fields(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    public_preflight = public_preflight_result(preflight)

    if args.preflight:
        print(json.dumps(public_preflight, ensure_ascii=False, indent=2))
        return 0 if preflight.get("Passed") else 1
    if not preflight.get("Passed"):
        print(json.dumps(public_preflight, ensure_ascii=False, indent=2))
        return 1

    expected_token = preflight["ConfirmationToken"]
    if not hmac.compare_digest(args.confirm_token, expected_token):
        print(
            json.dumps(
                {
                    "FinalState": "NOT_EXECUTED",
                    "Reason": "confirmation token does not match the fresh effective plan/current state",
                    "CurrentPreflight": public_preflight,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    effective = preflight["_EffectiveConfig"]
    print(
        json.dumps(
            {
                "Event": "PREFLIGHT_PASSED",
                "Action": effective["Action"],
                "EffectivePlan": preflight["EffectivePlan"],
                "ConfirmationToken": expected_token,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    request_id: Optional[str] = None
    ambiguous = False
    explicit_failure = False
    write_error_type: Optional[str] = None
    write_error_message: Optional[str] = None
    write_error_diagnostics = {}
    try:
        response = rpc(
            client,
            effective["RegionId"],
            effective["Action"],
            write_params(effective),
        )
        request_id = response.get("RequestId")
        if request_id:
            print(
                json.dumps(
                    {
                        "Event": "WRITE_ACCEPTED",
                        "Action": effective["Action"],
                        "RequestId": request_id,
                        "Meaning": "accepted response; final state still requires read-only verification",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        else:
            ambiguous = True
            print(
                json.dumps(
                    {
                        "Event": "WRITE_OUTCOME_AMBIGUOUS",
                        "Action": effective["Action"],
                        "Reason": "the write response did not contain RequestId",
                        "Retried": False,
                        "Next": "read-only verification; the write will not be retried automatically",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    except Exception as exc:
        print_safe_error_diagnostics(exc, file=sys.stderr)
        write_error_type = type(exc).__name__
        write_error_message = _sanitize_error(exc, profile)
        write_error_diagnostics = safe_error_fields(exc)
        http_status = getattr(exc, "http_status", None)
        definite_error_response = getattr(exc, "definite_rejection", False) is True or (
            write_error_type == "ServerException"
            and isinstance(http_status, int)
            and 400 <= http_status < 500
            and http_status != 408
        )
        if definite_error_response:
            # A batch user update can have dispatched earlier instances before
            # a later instance fails. Treat the error response as failed or
            # partial, then inspect every target instead of claiming no change.
            explicit_failure = True
            print(
                json.dumps(
                    {
                        "Event": "WRITE_FAILED_OR_PARTIAL",
                        "WriteState": "ERROR_RESPONSE",
                        "Action": effective["Action"],
                        "ErrorType": write_error_type,
                        "ErrorMessage": write_error_message,
                        **write_error_diagnostics,
                        "Retried": False,
                        "Next": "read-only verification of every target",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        else:
            ambiguous = True
            print(
                json.dumps(
                    {
                        "Event": "WRITE_OUTCOME_AMBIGUOUS",
                        "Action": effective["Action"],
                        "ErrorType": write_error_type,
                        "ErrorMessage": write_error_message,
                        **write_error_diagnostics,
                        "Retried": False,
                        "Next": "read-only verification; the write will not be retried automatically",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    verification = verify_after_write(
        client,
        effective,
        preflight,
        profile,
        wait_seconds=args.wait_seconds,
        poll_interval=args.poll_interval,
        ambiguous=ambiguous or explicit_failure,
    )
    observed_state = verification["FinalState"]
    if explicit_failure and observed_state != "SUCCESS":
        verification = {
            **verification,
            "ObservedState": observed_state,
            "FinalState": "FAILED",
            "WriteState": "ERROR_RESPONSE_OR_PARTIAL",
        }
    elif explicit_failure:
        verification = {
            **verification,
            "WriteState": "ERROR_RESPONSE_BUT_DESIRED_STATE_OBSERVED",
        }
    final = {
        **verification,
        "Action": effective["Action"],
        "RequestId": request_id,
        "WriteOutcomeWasAmbiguous": ambiguous,
        "WriteErrorType": write_error_type,
        "WriteErrorMessage": write_error_message,
        "Retried": False,
        **({"WriteErrorDiagnostics": write_error_diagnostics} if write_error_diagnostics else {}),
    }
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return {
        "SUCCESS": 0,
        "ACCEPTED_UNVERIFIED": 2,
        "PENDING": 2,
        "FAILED": 3,
        "UNKNOWN": 4,
    }[verification["FinalState"]]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print_safe_error_diagnostics(exc, file=sys.stderr)
        print(
            json.dumps({"FinalState": "NOT_EXECUTED", "Error": safe_error(exc),
                        **safe_error_fields(exc)}, ensure_ascii=False),
            file=sys.stderr,
        )
        raise SystemExit(1)
