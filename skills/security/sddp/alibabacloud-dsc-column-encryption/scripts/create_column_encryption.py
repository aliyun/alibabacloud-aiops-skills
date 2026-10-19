#!/usr/bin/env python3
"""Safely create and verify a DSC column-encryption rule.

The script targets the Sddp 2026-01-20 API backed by yundun-dsc-service.
Local dry-run is the default. A production write requires a successful online
preflight and the exact confirmation token generated from the effective plan.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from aliyun_cli import (
    DEFAULT_PROFILE, CliProfile, build_client, print_safe_error_diagnostics, resolve_profile,
    safe_error, safe_error_fields,
)


API_VERSION = "2026-01-20"
CREATE_ACTION = "CreateDataMaskingRule"
CHECK_ACTION = "CheckDataMaskingInstance"
ATTRIBUTE_ACTION = "GetInstanceAttribute"
ALGORITHM_ACTION = "ListDataMaskingEncryptionAlgorithms"
KMS_KEYS_ACTION = "ListKmsKeys"
COLUMN_LIST_ACTION = "ListDataMaskingColumns"
TEMPLATE_LIST_ACTION = "ListTemplates"
INSTANCE_LIST_ACTION = "ListDataMaskingInstances"
ACCOUNT_LIST_ACTION = "ListDataAssetAccounts"

PRODUCT_IDS = {"RDS": 5, "POLARDB": 8, "PolarDBX2": 27}
ALGORITHMS = {"AES_128_GCM", "AES_256_GCM", "SM4_128_GCM"}
KEY_MODES = {"client_key", "kms_key"}
EXPIRY_OPERATIONS = {"PRESERVE", "CLEAR", "SET"}
MAX_EXPIRE_TIME_MS = 2_145_953_410_000
REGION_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

TOP_LEVEL_FIELDS = {
    "RegionId",
    "TemplateId",
    "ProductCode",
    "ProductId",
    "InstanceId",
    "EngineType",
    "EncAlgorithm",
    "EncryptionKeyMode",
    "EncryptionKeyId",
    "SubRuleList",
    "UserList",
    "RiskHandleId",
    "Lang",
    "ExpireTimeOperation",
    "ExpireTime",
}
SUB_RULE_FIELDS = {"DbName", "TableName", "Columns"}
USER_FIELDS = {"AccountId"}
LEGACY_OR_PRIVATE_FIELDS = {
    "ServiceRegionId",
    "BackendRegionId",
    "ResourceGroupId",
    "CooperationChannel",
}
FAILED_STATUSES = {"Failed", "DeleteFailed"}


class ConfigError(ValueError):
    """Raised when the requested plan is unsafe or does not match the API."""


def load_json_object(path: Path | str) -> Dict[str, Any]:
    config_path = Path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ConfigError(f"{config_path} must contain a JSON object")
    return value


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
    for raw_column in value.split(","):
        column = raw_column.strip()
        if not column or column in seen:
            continue
        seen.add(column)
        result.append(column)
    if not result:
        raise ConfigError(f"{name} must contain at least one column")
    return result


def normalize_config(raw: Mapping[str, Any], *, now_ms: Optional[int] = None) -> Dict[str, Any]:
    if not isinstance(raw, Mapping):
        raise ConfigError("config must be a JSON object")

    unknown = set(raw) - TOP_LEVEL_FIELDS
    legacy = unknown & LEGACY_OR_PRIVATE_FIELDS
    if legacy:
        names = ", ".join(sorted(legacy))
        raise ConfigError(
            f"legacy/private fields are not allowed: {names}. "
            "Use RegionId for routing; resource group and cooperation channel are service-managed."
        )
    if unknown:
        raise ConfigError(f"unsupported top-level fields: {', '.join(sorted(unknown))}")

    region_id = _require_nonblank(raw.get("RegionId"), "RegionId")
    if not REGION_PATTERN.fullmatch(region_id):
        raise ConfigError("RegionId may contain only lowercase letters, digits, and hyphens")

    product_code = _require_nonblank(raw.get("ProductCode"), "ProductCode")
    if product_code not in PRODUCT_IDS:
        supported = ", ".join(PRODUCT_IDS)
        raise ConfigError(f"ProductCode must be one of: {supported}")

    instance_id = _require_nonblank(raw.get("InstanceId"), "InstanceId")

    template_id = raw.get("TemplateId")
    if template_id is not None:
        template_id = _require_int(template_id, "TemplateId")
        if template_id <= 0:
            raise ConfigError("TemplateId must be greater than zero")

    product_id = raw.get("ProductId")
    if product_id is not None:
        product_id = _require_int(product_id, "ProductId")
        expected_id = PRODUCT_IDS[product_code]
        if product_id != expected_id:
            raise ConfigError(
                f"ProductId {product_id} conflicts with ProductCode {product_code}; expected {expected_id}"
            )

    engine_type = raw.get("EngineType")
    if engine_type is not None:
        engine_type = _require_nonblank(engine_type, "EngineType")

    algorithm = raw.get("EncAlgorithm")
    if algorithm is not None:
        algorithm = _require_nonblank(algorithm, "EncAlgorithm").upper()
        if algorithm not in ALGORITHMS:
            raise ConfigError(f"EncAlgorithm must be one of: {', '.join(sorted(ALGORITHMS))}")

    key_id = raw.get("EncryptionKeyId")
    if key_id is not None:
        key_id = _require_nonblank(key_id, "EncryptionKeyId")

    key_mode = raw.get("EncryptionKeyMode")
    if key_mode is None:
        key_mode = "kms_key" if key_id else None
    else:
        key_mode = _require_nonblank(key_mode, "EncryptionKeyMode").lower()
    if key_mode is not None and key_mode not in KEY_MODES:
        raise ConfigError("EncryptionKeyMode must be client_key or kms_key")
    if key_mode == "client_key" and key_id:
        raise ConfigError("EncryptionKeyId cannot be used with client_key")

    raw_sub_rules = raw.get("SubRuleList")
    if not isinstance(raw_sub_rules, list) or not raw_sub_rules:
        raise ConfigError("SubRuleList must be a non-empty array")

    grouped_columns: Dict[Tuple[str, str], List[str]] = {}
    grouped_seen: Dict[Tuple[str, str], set[str]] = {}
    for index, item in enumerate(raw_sub_rules, start=1):
        name = f"SubRuleList[{index - 1}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{name} must be an object")
        extra = set(item) - SUB_RULE_FIELDS
        if extra:
            raise ConfigError(f"{name} has unsupported fields: {', '.join(sorted(extra))}")
        db_name = _require_nonblank(item.get("DbName"), f"{name}.DbName")
        table_name = _require_nonblank(item.get("TableName"), f"{name}.TableName")
        columns = _split_columns(item.get("Columns"), f"{name}.Columns")
        key = (db_name, table_name)
        destination = grouped_columns.setdefault(key, [])
        seen = grouped_seen.setdefault(key, set())
        for column in columns:
            if column not in seen:
                seen.add(column)
                destination.append(column)

    sub_rules = [
        {"DbName": db, "TableName": table, "Columns": ",".join(columns)}
        for (db, table), columns in grouped_columns.items()
    ]

    raw_users = raw.get("UserList", [])
    if not isinstance(raw_users, list):
        raise ConfigError("UserList must be an array")
    users: List[Dict[str, str]] = []
    seen_users = set()
    for index, item in enumerate(raw_users, start=1):
        name = f"UserList[{index - 1}]"
        if not isinstance(item, dict):
            raise ConfigError(f"{name} must be an object")
        extra = set(item) - USER_FIELDS
        if extra:
            raise ConfigError(f"{name} has unsupported fields: {', '.join(sorted(extra))}")
        account_id = _require_nonblank(item.get("AccountId"), f"{name}.AccountId")
        if account_id not in seen_users:
            seen_users.add(account_id)
            users.append({"AccountId": account_id})

    expire_operation = raw.get("ExpireTimeOperation", "PRESERVE")
    expire_operation = _require_nonblank(expire_operation, "ExpireTimeOperation").upper()
    if expire_operation not in EXPIRY_OPERATIONS:
        raise ConfigError("ExpireTimeOperation must be PRESERVE, CLEAR, or SET")
    expire_time = raw.get("ExpireTime")
    if expire_operation == "SET":
        if not users:
            raise ConfigError("SET expiry requires at least one UserList account")
        expire_time = _require_int(expire_time, "ExpireTime")
        current_ms = int(time.time() * 1000) if now_ms is None else now_ms
        expire_time = (expire_time // 1000) * 1000
        if expire_time <= current_ms:
            raise ConfigError("ExpireTime must be in the future")
        if expire_time > MAX_EXPIRE_TIME_MS:
            raise ConfigError("ExpireTime must not exceed 2038-01-01T10:10:10Z")
    elif expire_time is not None:
        raise ConfigError(f"ExpireTime must be omitted when ExpireTimeOperation is {expire_operation}")
    if expire_operation != "PRESERVE" and not users:
        raise ConfigError(f"{expire_operation} expiry requires at least one UserList account")

    risk_handle_id = raw.get("RiskHandleId")
    if risk_handle_id is not None:
        risk_handle_id = _require_int(risk_handle_id, "RiskHandleId")

    lang = raw.get("Lang")
    if lang is not None:
        lang = _require_nonblank(lang, "Lang")

    normalized: Dict[str, Any] = {
        "RegionId": region_id,
        "ProductCode": product_code,
        "InstanceId": instance_id,
        "SubRuleList": sub_rules,
        "UserList": users,
        "ExpireTimeOperation": expire_operation,
    }
    optional_values = {
        "TemplateId": template_id,
        "EncryptionKeyMode": key_mode,
        "ProductId": product_id,
        "EngineType": engine_type,
        "EncAlgorithm": algorithm,
        "EncryptionKeyId": key_id,
        "RiskHandleId": risk_handle_id,
        "Lang": lang,
        "ExpireTime": expire_time if expire_operation == "SET" else None,
    }
    for name, value in optional_values.items():
        if value is not None:
            normalized[name] = value
    return normalized


def target_columns(config: Mapping[str, Any]) -> List[Tuple[str, str, str]]:
    result: List[Tuple[str, str, str]] = []
    for rule in config["SubRuleList"]:
        for column in _split_columns(rule["Columns"], "SubRuleList.Columns"):
            result.append((rule["DbName"], rule["TableName"], column))
    return result


def plan_token(config: Mapping[str, Any]) -> str:
    canonical = json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:20]


def plan_summary(config: Mapping[str, Any]) -> Dict[str, Any]:
    expire_time = config.get("ExpireTime")
    expire_iso = None
    if expire_time is not None:
        expire_iso = datetime.fromtimestamp(expire_time / 1000, tz=timezone.utc).isoformat()
    return {
        "Endpoint": f"sddp.{config['RegionId']}.aliyuncs.com",
        "RegionId": config["RegionId"],
        "TemplateId": config.get("TemplateId"),
        "ProductCode": config["ProductCode"],
        "ProductId": config.get("ProductId", PRODUCT_IDS[config["ProductCode"]]),
        "InstanceId": config["InstanceId"],
        "EngineTypeHint": config.get("EngineType"),
        "EncAlgorithm": config.get("EncAlgorithm", "AUTO_DURING_PREFLIGHT"),
        "EncryptionKeyMode": config.get("EncryptionKeyMode", "INHERIT_DURING_PREFLIGHT"),
        "EncryptionKeyId": config.get("EncryptionKeyId"),
        "Targets": [
            {"DbName": db, "TableName": table, "ColumnName": column}
            for db, table, column in target_columns(config)
        ],
        "UniqueColumnCount": len(target_columns(config)),
        "WhitelistAccounts": [item["AccountId"] for item in config["UserList"]],
        "ExpireTimeOperation": config["ExpireTimeOperation"],
        "ExpireTime": expire_time,
        "ExpireTimeUtc": expire_iso,
        "RiskHandleId": config.get("RiskHandleId"),
    }


def rpc(client: Any, region_id: str, action: str, params: Mapping[str, Any]) -> Dict[str, Any]:
    return rpc_product(client, region_id, "sddp", API_VERSION, action, params)


def rpc_product(
    client: Any, region_id: str, product: str, version: str,
    action: str, params: Mapping[str, Any],
) -> Dict[str, Any]:
    return client.call(region_id, product, version, action, params)


def _items(response: Mapping[str, Any], field: str) -> List[Dict[str, Any]]:
    value = response.get(field, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for nested in value.values():
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _is_success_code(code: Any) -> bool:
    return isinstance(code, str) and code.lower() == "success"


def _is_available_item(item: Mapping[str, Any]) -> bool:
    code = item.get("ErrorCode")
    return code in (None, "") or _is_success_code(code)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return isinstance(value, str) and value.lower() == "true"


def page_count(
    action: str, response: Mapping[str, Any], field: str = "TotalCount", *, minimum: int = 0,
) -> Optional[int]:
    value = response.get(field)
    if value is None:
        return None
    if isinstance(value, str) and re.fullmatch(r"[0-9]+", value):
        try:
            value = int(value)
        except ValueError as exc:
            raise ConfigError(f"{action} returned an invalid {field}") from exc
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ConfigError(f"{action} returned an invalid {field}")
    return value


def parse_page_items(
    action: str, response: Mapping[str, Any], total: Optional[int],
) -> List[Dict[str, Any]]:
    raw_items = response.get("Items")
    if raw_items is None and total == 0:
        raw_items = []
    elif isinstance(raw_items, dict):
        nested_pages = [value for value in raw_items.values() if isinstance(value, list)]
        raw_items = nested_pages[0] if len(nested_pages) == 1 else None
    if not isinstance(raw_items, list) or any(not isinstance(item, dict) for item in raw_items):
        raise ConfigError(f"{action} did not return a verifiable Items page")
    return raw_items


def page_item_signature(action: str, item: Mapping[str, Any], params: Mapping[str, Any]) -> str:
    """Identify known DSC objects without treating mutable state as a new row."""
    product = item.get("ProductCode") or item.get("ProductId")
    if product in (None, ""):
        product = params.get("ProductCode") or params.get("ProductId")
    product = str(PRODUCT_IDS.get(product, product)) if isinstance(product, (str, int)) else None
    instance = item.get("InstanceId") or params.get("InstanceId")
    identity = None
    if action == COLUMN_LIST_ACTION:
        db = item.get("DbName") or params.get("DbName")
        table = item.get("TableName") or params.get("TableName")
        name = item.get("Name")  # ColumnName in the request is only a substring filter.
        if all(isinstance(value, str) and value for value in (db, table, name)):
            identity = (product, instance, db, table, name)
    elif action == ACCOUNT_LIST_ACTION:
        name = item.get("AccountName")
        if all(isinstance(value, str) and value for value in (instance, name)):
            identity = (product, instance, name)
    elif action == INSTANCE_LIST_ACTION:
        if isinstance(instance, str) and instance:
            identity = (product, instance)
    elif action == TEMPLATE_LIST_ACTION:
        template_id = item.get("Id")
        if isinstance(template_id, (str, int)) and not isinstance(template_id, bool) and str(template_id):
            identity = (str(template_id),)
    elif action == "ListDataSources":
        db = item.get("DbName") or params.get("DbName")
        if all(isinstance(value, str) and value for value in (instance, db)):
            identity = (product, instance, db)
    elif action in ("ListTables", "ListColumns"):
        source = item.get("DataAssetSourceId") or params.get("DataAssetSourceId")
        db = item.get("DataSourceName") or params.get("DataSourceName")
        name = item.get("Name")
        if all(isinstance(value, str) and value for value in (source, db, name)):
            if action == "ListTables":
                identity = (product, source, db, name)
            else:
                table = item.get("TableName") or params.get("TableName")
                if isinstance(table, str) and table:
                    identity = (product, source, db, item.get("SchemaName") or "", table, name)
    value = (action, identity) if identity is not None else ("record", item)
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def paged_items(
    client: Any, region_id: str, action: str, params: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Read every page; partial or repeating pages cannot establish a target."""
    combined: List[Dict[str, Any]] = []
    seen_item_signatures = set()
    total_count: Optional[int] = None
    server_page_size: Optional[int] = None
    for page in range(1, 101):
        response = rpc(client, region_id, action, {**params, "CurrentPage": page, "PageSize": 100})
        total = page_count(action, response)
        items = parse_page_items(action, response, total)
        reported_size = page_count(action, response, "PageSize", minimum=1)
        if reported_size is not None:
            if server_page_size is not None and server_page_size != reported_size:
                raise ConfigError(f"{action} changed PageSize during pagination; exact selection is incomplete")
            server_page_size = reported_size
        item_signatures = {page_item_signature(action, item, params) for item in items}
        if len(item_signatures) != len(items) or seen_item_signatures.intersection(item_signatures):
            raise ConfigError(f"{action} returned a repeated page or overlapping items; exact selection is incomplete")
        seen_item_signatures.update(item_signatures)
        combined.extend(items)
        if total is not None:
            if total_count is not None and total_count != total:
                raise ConfigError(f"{action} changed TotalCount during pagination; exact selection is incomplete")
            total_count = total
        if total_count is not None:
            if len(combined) > total_count:
                raise ConfigError(f"{action} returned more items than TotalCount; exact selection is incomplete")
            if len(combined) == total_count:
                return combined
            if not items:
                raise ConfigError(f"{action} returned an incomplete page")
        elif not items or (server_page_size is not None and len(items) < server_page_size):
            return combined
        time.sleep(0.02)
    raise ConfigError(f"{action} exceeded 100 pages; narrow the target")


def query_instance(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    params = {name: config[name] for name in ("ProductCode", "InstanceId", "Lang") if name in config}
    records = paged_items(client, config["RegionId"], INSTANCE_LIST_ACTION, params)
    record = next((item for item in records if item.get("InstanceId") == config["InstanceId"]
                   and item.get("ProductCode") in (None, "", config["ProductCode"])), None)
    if record is None:
        raise ConfigError("the exact instance was not returned by ListDataMaskingInstances")
    return {"InstanceId": config["InstanceId"],
            "EncryptionAlgorithm": record.get("EncryptionAlgorithm") or None,
            "EncryptionKeyId": record.get("EncryptionKeyId") or None}


def query_account(client: Any, config: Mapping[str, Any], account_id: str) -> Dict[str, Any]:
    records = paged_items(client, config["RegionId"], ACCOUNT_LIST_ACTION,
                         {"ProductCode": config["ProductCode"], "InstanceId": config["InstanceId"],
                          "AccountName": account_id})
    record = next((item for item in records if item.get("AccountName") == account_id
                   and item.get("InstanceId") in (None, "", config["InstanceId"])
                   and item.get("ProductCode") in (None, "", config["ProductCode"])), None)
    if record is None:
        raise ConfigError(f"the exact account {account_id} was not returned by ListDataAssetAccounts")
    return {"InstanceId": config["InstanceId"], "AccountId": account_id,
            "AuthRole": record.get("AuthRole"), "ExpireTime": record.get("ExpireTime")}


def run_preflight(client: Any, config: Mapping[str, Any]) -> Dict[str, Any]:
    region_id = config["RegionId"]
    base = {"ProductCode": config["ProductCode"], "InstanceId": config["InstanceId"]}
    checks: Dict[str, Any] = {}

    template_id = config.get("TemplateId")
    if template_id is not None:
        template_match: Optional[Dict[str, Any]] = None
        pages_checked = 0
        for page_number in range(1, 101):
            template_response = rpc(
                client,
                region_id,
                TEMPLATE_LIST_ACTION,
                {"CurrentPage": page_number, "PageSize": 50, "Lang": config.get("Lang")},
            )
            pages_checked += 1
            page_items = _items(template_response, "Items")
            template_match = next(
                (item for item in page_items if str(item.get("Id")) == str(template_id)),
                None,
            )
            if template_match is not None:
                break
            total = template_response.get("TotalCount")
            if len(page_items) < 50 or (
                isinstance(total, int) and page_number * 50 >= total
            ):
                break
        checks[TEMPLATE_LIST_ACTION] = {
            "TemplateId": template_id,
            "Found": template_match is not None,
            "TemplateName": template_match.get("Name") if template_match else None,
            "PagesChecked": pages_checked,
        }
        if template_match is None:
            return {
                "Mode": "PREFLIGHT",
                "Passed": False,
                "Checks": checks,
                "Error": f"TemplateId {template_id} was not returned by ListTemplates",
            }

    eligibility = rpc(client, region_id, CHECK_ACTION, base)
    checks[CHECK_ACTION] = {
        "RequestId": eligibility.get("RequestId"),
        "ErrorCode": eligibility.get("ErrorCode"),
        "ErrorMessage": eligibility.get("ErrorMessage"),
    }
    if not _is_success_code(eligibility.get("ErrorCode")):
        return {
            "Mode": "PREFLIGHT",
            "Passed": False,
            "Checks": checks,
            "Error": "instance eligibility check did not return Success",
        }

    attribute = rpc(client, region_id, ATTRIBUTE_ACTION, base)
    checks[ATTRIBUTE_ACTION] = {
        "RequestId": attribute.get("RequestId"),
        "Engine": attribute.get("Engine"),
        "EngineVersion": attribute.get("EngineVersion"),
        "CurrentKernelVersion": attribute.get("CurrentKernelVersion"),
        "Status": attribute.get("Status"),
        "KmsEncryptionSupported": attribute.get("KmsEncryptionSupported"),
        "ErrorCode": attribute.get("ErrorCode"),
        "ErrorMessage": attribute.get("ErrorMessage"),
    }
    attribute_code = attribute.get("ErrorCode")
    if attribute_code not in (None, "") and not _is_success_code(attribute_code):
        return {
            "Mode": "PREFLIGHT",
            "Passed": False,
            "Checks": checks,
            "Error": "instance attribute check failed",
        }
    actual_engine = attribute.get("Engine")
    if not isinstance(actual_engine, str) or not actual_engine.strip():
        return {
            "Mode": "PREFLIGHT",
            "Passed": False,
            "Checks": checks,
            "Error": "GetInstanceAttribute did not return the instance engine",
        }
    actual_engine = actual_engine.strip()
    engine_hint = config.get("EngineType")
    if engine_hint and str(engine_hint).lower() != actual_engine.lower():
        return {
            "Mode": "PREFLIGHT",
            "Passed": False,
            "Checks": checks,
            "Error": f"EngineType hint {engine_hint} conflicts with actual engine {actual_engine}",
        }

    current_instance = query_instance(client, config)
    checks[INSTANCE_LIST_ACTION] = current_instance
    algorithm_response = rpc(client, region_id, ALGORITHM_ACTION, base)
    algorithms = _items(algorithm_response, "Algorithms")
    checks[ALGORITHM_ACTION] = {
        "RequestId": algorithm_response.get("RequestId"),
        "Algorithms": [
            {
                "Name": item.get("Name"),
                "Available": _is_available_item(item),
                "ErrorCode": item.get("ErrorCode"),
                "ErrorMessage": item.get("ErrorMessage"),
            }
            for item in algorithms
        ],
    }
    available = [item for item in algorithms if item.get("Name") and _is_available_item(item)]
    requested_algorithm = config.get("EncAlgorithm") or current_instance.get("EncryptionAlgorithm")
    if requested_algorithm:
        selected = next((item for item in available if item.get("Name") == requested_algorithm), None)
        if selected is None:
            return {
                "Mode": "PREFLIGHT",
                "Passed": False,
                "Checks": checks,
                "Error": f"requested algorithm {requested_algorithm} is not currently available",
            }
        selected_algorithm = requested_algorithm
        algorithm_selection = "explicit" if config.get("EncAlgorithm") else "inherited instance algorithm"
    else:
        if not available:
            return {
                "Mode": "PREFLIGHT",
                "Passed": False,
                "Checks": checks,
                "Error": "the instance has no currently available encryption algorithm",
            }
        selected_algorithm = str(available[0]["Name"])
        algorithm_selection = "first currently available algorithm"

    effective = copy.deepcopy(dict(config))
    effective["EngineType"] = actual_engine
    effective["EncAlgorithm"] = selected_algorithm
    key_mode = effective.get("EncryptionKeyMode")
    if key_mode is None:
        key_mode = "kms_key" if current_instance.get("EncryptionKeyId") else "client_key"
    effective["EncryptionKeyMode"] = key_mode
    if key_mode == "kms_key" and not effective.get("EncryptionKeyId"):
        if not current_instance.get("EncryptionKeyId"):
            raise ConfigError("kms_key requires an explicit EncryptionKeyId or an existing instance KMS key")
        effective["EncryptionKeyId"] = current_instance["EncryptionKeyId"]
    if current_instance.get("EncryptionAlgorithm") and (
        selected_algorithm != current_instance["EncryptionAlgorithm"]
        or effective.get("EncryptionKeyId") != current_instance.get("EncryptionKeyId")
    ):
        raise ConfigError("existing instance algorithm/key changes require UpdateDataMaskingEncryptionAlgorithm; "
                          "complete that instance-wide operation before creating additional columns")
    checks[ALGORITHM_ACTION]["Selected"] = selected_algorithm
    checks[ALGORITHM_ACTION]["SelectionReason"] = algorithm_selection

    if effective["EncryptionKeyMode"] == "kms_key":
        if not _as_bool(attribute.get("KmsEncryptionSupported")):
            return {
                "Mode": "PREFLIGHT",
                "Passed": False,
                "Checks": checks,
                "Error": "the instance does not currently support KMS column encryption",
            }
        key_response = rpc(client, region_id, KMS_KEYS_ACTION, base)
        keys = _items(key_response, "Items")
        key_id = effective["EncryptionKeyId"]
        matched = any(item.get("KeyId") == key_id for item in keys)
        checks[KMS_KEYS_ACTION] = {
            "RequestId": key_response.get("RequestId"),
            "ReturnedKeyCount": len(keys),
            "RequestedKeyId": key_id,
            "Matched": matched,
        }
        if not matched:
            return {
                "Mode": "PREFLIGHT",
                "Passed": False,
                "Checks": checks,
                "Error": "the requested KMS key was not returned by ListKmsKeys",
            }

        detail = rpc_product(client, region_id, "kms", "2016-01-20", "DescribeKey", {"KeyId": key_id})
        metadata = detail.get("KeyMetadata") or {}
        checks["KMS.DescribeKey"] = {
            "KeyId": metadata.get("KeyId"), "KeyState": metadata.get("KeyState"),
            "KeySpec": metadata.get("KeySpec"), "KeyUsage": metadata.get("KeyUsage"),
        }
        if metadata.get("KeyId") != key_id or str(metadata.get("KeyState", "")).lower() != "enabled":
            raise ConfigError("DescribeKey did not confirm the requested KMS key is Enabled")

    columns_before = [query_column_status(client, effective, *target) for target in target_columns(effective)]
    checks[COLUMN_LIST_ACTION] = columns_before
    if any(item["Status"] not in {"NotEncrypted", "Success", "Failed"} for item in columns_before):
        raise ConfigError("every target must be exactly visible and NotEncrypted, Success, or Failed; "
                          "wait for processing/deleting columns before submitting")
    accounts_before = [query_account(client, effective, item["AccountId"]) for item in effective["UserList"]]
    accounts_after = []
    for current in accounts_before:
        operation = effective["ExpireTimeOperation"]
        expiry = effective.get("ExpireTime") if operation == "SET" else (
            None if operation == "CLEAR" else current["ExpireTime"])
        expected = {"InstanceId": effective["InstanceId"], "AccountId": current["AccountId"],
                    "AuthRole": "fullAccess", "ExpireTime": expiry}
        if operation == "PRESERVE" and current["AuthRole"] == "unconfigured":
            # The account API hides expiry without an active instance rule, but
            # creation can preserve a deadline retained in data_masking_user.
            expected.pop("ExpireTime")
            expected["ExpireTimeKnown"] = False
            expected["VerificationNote"] = (
                "PRESERVE may retain a hidden previous expiry for this unconfigured account; "
                "the original expiry cannot be established by the read API, so preservation "
                "cannot be verified and must not be described as permanent access."
            )
        accounts_after.append(expected)
    checks[ACCOUNT_LIST_ACTION] = accounts_before
    current_state = {"Instance": current_instance, "Columns": columns_before, "Accounts": accounts_before}
    effective_plan = {**plan_summary(effective), "CurrentState": current_state, "AccountsAfter": accounts_after}
    token = plan_token({"Config": effective, "CurrentState": current_state})
    return {
        "Mode": "PREFLIGHT",
        "Passed": True,
        "Checks": checks,
        "EffectivePlan": effective_plan,
        "ConfirmationToken": token,
        "_ExpectedAccounts": accounts_after,
        "_EffectiveConfig": effective,
    }


def create_params(config: Mapping[str, Any]) -> Dict[str, Any]:
    params: Dict[str, Any] = {}
    for name, value in config.items():
        # TemplateId scopes discovery and verification, but the current
        # CreateDataMaskingRule AMP contract does not expose it.
        if name not in {"RegionId", "TemplateId"}:
            params[name] = value
    return params


def _sanitize_error(exc: Exception, credentials: CliProfile) -> str:
    return safe_error(exc)


def query_column_status(
    client: Any,
    config: Mapping[str, Any],
    db_name: str,
    table_name: str,
    column_name: str,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "ProductCode": config["ProductCode"],
        "InstanceId": config["InstanceId"],
        "DbName": db_name,
        "TableName": table_name,
        "ColumnName": column_name,
        "CurrentPage": 1,
        "PageSize": 100,
    }
    if config.get("EngineType"):
        params["EngineType"] = config["EngineType"]
    if config.get("TemplateId"):
        params["TemplateId"] = config["TemplateId"]
    items = paged_items(client, config["RegionId"], COLUMN_LIST_ACTION, params)
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
        return {
            "DbName": db_name,
            "TableName": table_name,
            "ColumnName": column_name,
            "Status": "NotVisible",
        }
    return {
        "DbName": db_name,
        "TableName": table_name,
        "ColumnName": column_name,
        "Status": exact.get("MaskingStatus") or "Unknown",
        "ErrorCode": exact.get("ErrorCode"),
        "ErrorMessage": exact.get("ErrorMessage"),
        "RuleId": exact.get("RuleId"),
    }


def poll_columns(
    client: Any,
    config: Mapping[str, Any],
    credentials: CliProfile,
    *,
    wait_seconds: int,
    poll_interval: float,
    write_was_ambiguous: bool,
    expected_accounts: Sequence[Mapping[str, Any]] = (),
) -> Dict[str, Any]:
    deadline = time.monotonic() + wait_seconds
    previous_signature: Optional[str] = None
    statuses: List[Dict[str, Any]] = []

    while True:
        statuses = []
        for db_name, table_name, column_name in target_columns(config):
            try:
                status = query_column_status(client, config, db_name, table_name, column_name)
            except Exception as exc:  # A read failure must never trigger another write.
                print_safe_error_diagnostics(exc, file=sys.stderr)
                status = {
                    "DbName": db_name,
                    "TableName": table_name,
                    "ColumnName": column_name,
                    "Status": "QueryError",
                    "ErrorMessage": _sanitize_error(exc, credentials),
                    **safe_error_fields(exc),
                }
            statuses.append(status)
            time.sleep(0.02)  # Keep status reads comfortably below the 100 QPS API limit.

        signature = json.dumps(statuses, ensure_ascii=False, sort_keys=True)
        if signature != previous_signature:
            print(
                json.dumps({"Event": "COLUMN_STATUS", "Columns": statuses}, ensure_ascii=False),
                flush=True,
            )
            previous_signature = signature

        account_states = []
        for expected in expected_accounts:
            try:
                current = query_account(client, config, expected["AccountId"])
                verification_note = {}
                if expected.get("ExpireTimeKnown") is False:
                    verification_note = {
                        "DesiredExpireTimeKnown": False,
                        "VerificationNote": expected["VerificationNote"],
                    }
                account_states.append({
                    **current,
                    "Matched": expected.get("ExpireTimeKnown") is not False and current == expected,
                    **verification_note,
                })
            except Exception as exc:
                print_safe_error_diagnostics(exc, file=sys.stderr)
                account_states.append({"AccountId": expected["AccountId"], "Matched": False,
                                       "QueryError": _sanitize_error(exc, credentials),
                                       **safe_error_fields(exc)})
        try:
            instance_state = query_instance(client, config)
            instance_state["Matched"] = (
                instance_state["EncryptionAlgorithm"] == config["EncAlgorithm"]
                and instance_state["EncryptionKeyId"] == config.get("EncryptionKeyId"))
        except Exception as exc:
            print_safe_error_diagnostics(exc, file=sys.stderr)
            instance_state = {"Matched": False, "QueryError": _sanitize_error(exc, credentials),
                              **safe_error_fields(exc)}
        verification = {"Columns": statuses, "Accounts": account_states, "Instance": instance_state}
        status_names = [item["Status"] for item in statuses]
        if (status_names and all(status == "Success" for status in status_names)
                and all(item["Matched"] for item in account_states) and instance_state["Matched"]):
            return {"FinalState": "SUCCESS", **verification}
        if any(status in FAILED_STATUSES for status in status_names):
            return {"FinalState": "FAILED", **verification}
        if time.monotonic() >= deadline:
            invisible = all(status in {"NotVisible", "QueryError"} for status in status_names)
            state = "UNKNOWN" if write_was_ambiguous and invisible else "PENDING"
            return {"FinalState": state, **verification}
        time.sleep(poll_interval)


def public_preflight_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in result.items() if not key.startswith("_")}


def bind_authentication(result: Mapping[str, Any], profile: CliProfile) -> Dict[str, Any]:
    """Bind the online confirmation to the selected profile name and mode.

    A profile name is not a cloud account identity. Reauthorizing that same
    profile still requires a fresh preflight and review of the resulting plan.
    """
    bound = copy.deepcopy(dict(result))
    auth = {"Mode": profile.mode, "Profile": profile.name}
    bound["Authentication"] = auth
    if isinstance(bound.get("EffectivePlan"), dict):
        bound["EffectivePlan"]["Authentication"] = auth
    if bound.get("ConfirmationToken"):
        bound["ConfirmationToken"] = plan_token({
            "BusinessConfirmationToken": bound["ConfirmationToken"], "Authentication": auth,
        })
    return bound


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preflight, create, and verify a DSC column-encryption rule."
    )
    parser.add_argument("--config", required=True, help="JSON plan using Sddp 2026-01-20 field names")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="local validation only (default)")
    mode.add_argument("--preflight", action="store_true", help="run read-only online checks")
    mode.add_argument("--execute", action="store_true", help="perform one production create request")
    parser.add_argument("--confirm-token", help="exact token returned by a successful online preflight")
    parser.add_argument("--profile", default=DEFAULT_PROFILE,
                        help="CLI profile: OAuth, AK, StsToken or RamRoleArn (default: dsc-oauth)")
    parser.add_argument(
        "--wait-seconds",
        type=int,
        default=180,
        help="maximum asynchronous verification wait after execute (default: 180)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=3.0,
        help="seconds between column status polls (minimum: 1)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.confirm_token and not args.execute:
        raise ConfigError("--confirm-token is only valid with --execute")
    if args.execute and not args.confirm_token:
        raise ConfigError("--execute requires --confirm-token from a successful online preflight")
    if args.wait_seconds < 0:
        raise ConfigError("--wait-seconds must be zero or greater")
    if args.poll_interval < 1:
        raise ConfigError("--poll-interval must be at least 1 second")

    normalized = normalize_config(load_json_object(args.config))
    if not args.preflight and not args.execute:
        output = {
            "Mode": "DRY_RUN",
            "Executable": False,
            "DraftPlan": plan_summary(normalized),
            "DraftFingerprint": plan_token(normalized),
            "NextStep": "Run --preflight; only its ConfirmationToken can authorize --execute.",
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    credentials = resolve_profile(args.profile)
    client = build_client(credentials, normalized["RegionId"])
    try:
        preflight = bind_authentication(run_preflight(client, normalized), credentials)
    except Exception as exc:
        print_safe_error_diagnostics(exc, file=sys.stderr)
        print(
            json.dumps(
                {
                    "Mode": "PREFLIGHT",
                    "Passed": False,
                    "Error": _sanitize_error(exc, credentials),
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

    effective = preflight["_EffectiveConfig"]
    expected_token = preflight["ConfirmationToken"]
    if not hmac.compare_digest(args.confirm_token, expected_token):
        print(
            json.dumps(
                {
                    "FinalState": "NOT_EXECUTED",
                    "Reason": "confirmation token does not match the current effective plan",
                    "CurrentPreflight": public_preflight,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    print(
        json.dumps(
            {
                "Event": "PREFLIGHT_PASSED",
                "EffectivePlan": preflight["EffectivePlan"],
                "ConfirmationToken": expected_token,
            },
            ensure_ascii=False,
        ),
        flush=True,
    )

    write_ambiguous = False
    request_id = None
    write_error_diagnostics = {}
    try:
        create_response = rpc(
            client,
            effective["RegionId"],
            CREATE_ACTION,
            create_params(effective),
        )
        request_id = create_response.get("RequestId")
        if request_id:
            print(
                json.dumps(
                    {
                        "Event": "CREATE_ACCEPTED",
                        "RequestId": request_id,
                        "Meaning": "accepted for asynchronous processing; not final success",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
        else:
            write_ambiguous = True
            print(
                json.dumps(
                    {
                        "Event": "CREATE_OUTCOME_AMBIGUOUS",
                        "Reason": "the create response did not contain RequestId",
                        "Retried": False,
                        "Next": "querying target columns before any retry",
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    except Exception as exc:
        print_safe_error_diagnostics(exc, file=sys.stderr)
        error_type = type(exc).__name__
        error_message = _sanitize_error(exc, credentials)
        write_error_diagnostics = safe_error_fields(exc)
        http_status = getattr(exc, "http_status", None)
        definite_rejection = (getattr(exc, "definite_rejection", False) or
                              (error_type == "ServerException" and isinstance(http_status, int)
                               and 400 <= http_status < 500 and http_status != 408))
        if definite_rejection:
            print(
                json.dumps(
                    {
                        "FinalState": "FAILED",
                        "WriteState": "REJECTED",
                        "ErrorType": error_type,
                        "ErrorMessage": error_message,
                        **write_error_diagnostics,
                        "Retried": False,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 3
        write_ambiguous = True
        print(
            json.dumps(
                {
                    "Event": "CREATE_OUTCOME_AMBIGUOUS",
                    "ErrorType": error_type,
                    "ErrorMessage": error_message,
                    **write_error_diagnostics,
                    "Retried": False,
                    "Next": "querying target columns before any retry",
                },
                ensure_ascii=False,
            ),
            flush=True,
        )

    verification = poll_columns(
        client,
        effective,
        credentials,
        wait_seconds=args.wait_seconds,
        poll_interval=args.poll_interval,
        write_was_ambiguous=write_ambiguous,
        expected_accounts=preflight["_ExpectedAccounts"],
    )
    final = {
        **verification,
        "RequestId": request_id,
        "WriteOutcomeWasAmbiguous": write_ambiguous,
        "Retried": False,
        **({"WriteErrorDiagnostics": write_error_diagnostics} if write_error_diagnostics else {}),
    }
    print(json.dumps(final, ensure_ascii=False, indent=2))
    return {"SUCCESS": 0, "PENDING": 2, "FAILED": 3, "UNKNOWN": 4}[verification["FinalState"]]


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print_safe_error_diagnostics(exc, file=sys.stderr)
        print(json.dumps({"FinalState": "NOT_EXECUTED", "Error": safe_error(exc),
                          **safe_error_fields(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
