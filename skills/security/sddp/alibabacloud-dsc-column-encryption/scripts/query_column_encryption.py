#!/usr/bin/env python3
"""Read-only queries for the DSC column-encryption console.

The commands mirror the query actions used by the DE page and target
Sddp 2026-01-20. This file deliberately contains no write action.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence

from create_column_encryption import (
    API_VERSION,
    ConfigError,
    PRODUCT_IDS,
    build_client,
    page_count,
    page_item_signature,
    parse_page_items,
    resolve_profile,
    rpc,
    rpc_product as cli_rpc_product,
)
from aliyun_cli import print_safe_error_diagnostics, safe_error, safe_error_fields


CONTROL_PLANE_REGION = "cn-zhangjiakou"
DEFAULT_PRODUCT_CODES = "RDS,POLARDB,PolarDBX2"
MASKING_STATUSES = ("NotEncrypted", "Success", "Failed")
AUTH_ROLES = ("fullAccess", "restrictedAccess", "noneAccess", "unconfigured")

PAGE_QUERY_ACTIONS = (
    "GetUserStatus",
    "ListRegions",
    "ListTemplates",
    "ListTotalSensitiveInfo",
    "GetDataMaskingAccountCount",
    "ListIdentifyModels",
    "ListRiskLevels",
    "ListDataMaskingInstances",
    "GetDataMaskingColumnCount",
    "CheckDataMaskingInstance",
    "ListDataSources",
    "ListTables",
    "ListColumns",
    "ListDataMaskingColumns",
    "ListDataAssetAccounts",
    "ListDataMaskingEncryptionAlgorithms",
    "GetInstanceAttribute",
    "ListKmsKeys",
    "ListMiniEngineVersions",
)


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _csv_ids(value: str) -> str:
    values: List[str] = []
    seen = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            number = int(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError("must be comma-separated integer IDs") from exc
        if number <= 0:
            raise argparse.ArgumentTypeError("IDs must be greater than zero")
        normalized = str(number)
        if normalized not in seen:
            seen.add(normalized)
            values.append(normalized)
    if not values:
        raise argparse.ArgumentTypeError("must contain at least one ID")
    return ",".join(values)


def _product_code(value: str) -> str:
    normalized = value.strip().lower().replace("-", "")
    aliases = {
        "rds": "RDS",
        "polardb": "POLARDB",
        "polardbx2": "PolarDBX2",
    }
    if normalized not in aliases:
        raise argparse.ArgumentTypeError("must be RDS, POLARDB, or PolarDBX2")
    return aliases[normalized]


def _product_code_list(value: str) -> str:
    codes = list(dict.fromkeys(_product_code(item) for item in value.split(",")))
    return ",".join(codes)


def _nonblank(value: str) -> str:
    if not value.strip():
        raise argparse.ArgumentTypeError("must not be blank")
    return value


def _engine_type(value: str) -> str:
    aliases = {"mysql": "MySQL", "postgresql": "PostgreSQL", "postgres": "PostgreSQL", "pg": "PostgreSQL",
               "oracle": "Oracle", "polarx": "polarx", "polardbx2": "polarx"}
    result = aliases.get(value.strip().casefold())
    if result is None:
        raise argparse.ArgumentTypeError("must be MySQL, PostgreSQL, Oracle, or polarx")
    return result


def _selected_product_ids(args: argparse.Namespace) -> Optional[str]:
    product_code = getattr(args, "product_code", None)
    product_id = getattr(args, "product_id", None)
    return getattr(args, "product_ids", None) or (
        str(product_id or PRODUCT_IDS[product_code]) if product_id or product_code else None
    )


def _validate_filters(args: argparse.Namespace) -> None:
    product_code = getattr(args, "product_code", None)
    product_id = getattr(args, "product_id", None)
    product_ids = getattr(args, "product_ids", None)
    if product_id is not None and product_id not in PRODUCT_IDS.values():
        raise ConfigError("ProductId must be 5 (RDS), 8 (POLARDB), or 27 (PolarDBX2)")
    if product_code and product_id is not None and PRODUCT_IDS[product_code] != product_id:
        raise ConfigError("ProductCode and ProductId must identify the same product")
    if product_ids:
        ids = {int(value) for value in product_ids.split(",")}
        if not ids.issubset(PRODUCT_IDS.values()):
            raise ConfigError("ProductIds supports only 5, 8, and 27 for column encryption")
        single = product_id or (PRODUCT_IDS[product_code] if product_code else None)
        if single is not None and ids != {single}:
            raise ConfigError("ProductIds conflicts with ProductCode/ProductId; use one product selector")
        if args.command == "masking-columns" and len(ids) > 1:
            raise ConfigError(
                "ListDataMaskingColumns does not apply a multi-product ProductIds filter; "
                "query each product separately with --product-code or a single --product-ids value"
            )
    if getattr(args, "risk_level_id", None) and getattr(args, "risk_level_ids", None):
        raise ConfigError("use --risk-level-id or --risk-level-ids, not both")
    codes = getattr(args, "product_code_list", None)
    selected = _selected_product_ids(args)
    if codes and selected and codes != DEFAULT_PRODUCT_CODES:
        if {PRODUCT_IDS[code] for code in codes.split(",")} != {int(value) for value in selected.split(",")}:
            raise ConfigError("ProductCodeList conflicts with the selected product filter")


def _auth_roles(value: str) -> str:
    roles: List[str] = []
    seen = set()
    for raw in value.split(","):
        role = raw.strip()
        if role not in AUTH_ROLES:
            raise argparse.ArgumentTypeError(
                f"roles must be comma-separated values from: {', '.join(AUTH_ROLES)}"
            )
        if role not in seen:
            seen.add(role)
            roles.append(role)
    if not roles:
        raise argparse.ArgumentTypeError("must contain at least one role")
    return ",".join(roles)


def _clean(params: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        name: value
        for name, value in params.items()
        if value is not None and value != ""
    }


def _items(response: Mapping[str, Any], field: str = "Items") -> List[Dict[str, Any]]:
    value = response.get(field, [])
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, dict):
        for nested in value.values():
            if isinstance(nested, list):
                return [item for item in nested if isinstance(item, dict)]
    return []


def _query(
    client: Any,
    region_id: str,
    action: str,
    params: Mapping[str, Any],
    *,
    all_pages: bool = False,
    max_pages: int = 100,
) -> Dict[str, Any]:
    clean_params = _clean(params)
    if not all_pages or "CurrentPage" not in clean_params or "PageSize" not in clean_params:
        return rpc(client, region_id, action, clean_params)

    page = int(clean_params["CurrentPage"])
    page_size = int(clean_params["PageSize"])
    combined: Optional[Dict[str, Any]] = None
    combined_items: List[Dict[str, Any]] = []
    request_ids: List[str] = []
    seen_item_signatures = set()
    total_count: Optional[int] = None
    server_page_size: Optional[int] = None
    pagination_stalled = False
    pagination_completed = False
    fetched = 0
    initial_page = page
    marker = clean_params.get("Marker")
    seen_markers = {str(marker)} if marker is not None else set()

    while fetched < max_pages:
        page_params = {**clean_params, "CurrentPage": page}
        if marker is not None:
            page_params["Marker"] = marker
        response = rpc(client, region_id, action, page_params)
        if combined is None:
            combined = dict(response)
        fetched += 1
        request_id = response.get("RequestId")
        if isinstance(request_id, str) and request_id:
            request_ids.append(request_id)
        try:
            total = page_count(action, response)
            page_items = parse_page_items(action, response, total)
            reported_size = page_count(action, response, "PageSize", minimum=1)
        except ConfigError:
            pagination_stalled = True
            break
        if total is not None:
            if total_count is not None and total_count != total:
                pagination_stalled = True
                break
            total_count = total
        total = total_count
        if reported_size is not None:
            if server_page_size is not None and server_page_size != reported_size:
                pagination_stalled = True
                break
            server_page_size = reported_size
        effective_size = server_page_size or page_size
        offset = (initial_page - 1) * effective_size
        if not page_items:
            pagination_completed = total is None or offset + len(combined_items) == total
            pagination_stalled = not pagination_completed
            break
        if total is not None and offset + len(combined_items) + len(page_items) > total:
            pagination_stalled = True
            break
        item_signatures = {page_item_signature(action, item, clean_params) for item in page_items}
        if len(item_signatures) != len(page_items) or seen_item_signatures.intersection(item_signatures):
            pagination_stalled = True
            break
        seen_item_signatures.update(item_signatures)
        combined_items.extend(page_items)

        if total is not None and offset + len(combined_items) == total:
            pagination_completed = True
            break
        if total is None and server_page_size is not None and len(page_items) < server_page_size:
            pagination_completed = True
            break
        if marker is not None:
            next_marker = response.get("NextMarker")
            if next_marker in (None, "") or str(next_marker) in seen_markers:
                pagination_stalled = True
                break
            marker = next_marker
            seen_markers.add(str(marker))
        page += 1
        time.sleep(0.02)

    assert combined is not None
    combined["Items"] = combined_items
    combined["CurrentPage"] = int(clean_params["CurrentPage"])
    combined["PageSize"] = page_size
    combined["FetchedPages"] = fetched
    combined["RequestIds"] = request_ids
    combined["PaginationComplete"] = pagination_completed
    if fetched >= max_pages and not pagination_completed:
        combined["PaginationTruncated"] = True
    if pagination_stalled:
        combined["PaginationStalled"] = True
    return combined


def _rpc_product(
    client: Any,
    region_id: str,
    product: str,
    version: str,
    action: str,
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    return cli_rpc_product(client, region_id, product, version, action, _clean(params))


def _page_params(args: argparse.Namespace) -> Dict[str, Any]:
    return {"CurrentPage": args.page, "PageSize": args.page_size}


def _template_params(args: argparse.Namespace) -> Dict[str, Any]:
    return {"TemplateId": getattr(args, "template_id", None)}


def _identity_params(args: argparse.Namespace) -> Dict[str, Any]:
    return {
        "ProductCode": getattr(args, "product_code", None),
        "ProductId": getattr(args, "product_id", None),
        "InstanceId": getattr(args, "instance_id", None),
        "Lang": getattr(args, "lang", None),
    }


def _local_name_filter(response: Dict[str, Any], field: str, query: Optional[str]) -> Dict[str, Any]:
    if not query:
        return response
    needle = query.casefold()
    items = [
        item
        for item in _items(response, field)
        if needle in str(item.get("Name", "")).casefold()
    ]
    result = dict(response)
    result[field] = items
    result["LocalFilter"] = {"NameContains": query, "MatchedCount": len(items)}
    return result


def _local_page(
    response: Dict[str, Any], args: argparse.Namespace,
    *, equals: Optional[Mapping[str, str]] = None,
    contains: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Apply filters after fetching page 1 onward, then paginate the matched rows."""
    equals, contains = equals or {}, contains or {}
    rows = [item for item in _items(response) if all(
        str(item.get(field, "")).casefold() == value.casefold()
        for field, value in equals.items()
    ) and all(
        value.casefold() in str(item.get(field, "")).casefold()
        for field, value in contains.items()
    )]
    start = (args.page - 1) * args.page_size
    complete = response.get("PaginationComplete") is True
    result = dict(response)
    result["SourceTotalCount"] = response.get("TotalCount")
    result["TotalCount"] = len(rows) if complete else None
    result["Items"] = rows[start:] if args.all_pages else rows[start:start + args.page_size]
    result["CurrentPage"] = args.page
    result["PageSize"] = args.page_size
    result["LocalFilter"] = {
        "Equals": dict(equals), "Contains": dict(contains),
        "MatchedCount": len(rows), "Complete": complete,
        "SourceStartPage": 1,
    }
    return result


def _instance_params(args: argparse.Namespace) -> Dict[str, Any]:
    return _clean({
        **_template_params(args), **_page_params(args),
        "MaskingStatus": args.masking_status, "RiskLevelId": args.risk_level_id,
        "RiskLevelIds": args.risk_level_ids, "TemplateRuleIds": args.template_rule_ids,
        "ProductId": args.product_id, "ProductIds": args.product_ids,
        "ProductCode": args.product_code, "InstanceId": args.instance_id,
        "EngineType": args.engine_type, "DbName": args.db_name,
        "TableName": args.table_name, "ColumnName": args.column_name, "Lang": args.lang,
    })


def _instances(client: Any, args: argparse.Namespace) -> Dict[str, Any]:
    params = _instance_params(args)
    local = bool(args.engine_type or args.instance_search)
    if local:
        params["CurrentPage"] = 1
    response = _query(client, args.region_id, "ListDataMaskingInstances", params,
                      all_pages=args.all_pages or local, max_pages=args.max_pages)
    if local:
        return _local_page(response, args,
                           equals={"EngineType": args.engine_type} if args.engine_type else {},
                           contains={"InstanceId": args.instance_search} if args.instance_search else {})
    return response


def _resolve_template(
    templates_response: Mapping[str, Any], requested_template_id: Optional[int]
) -> tuple[int, str, Optional[str]]:
    templates = _items(templates_response)
    if requested_template_id is not None:
        match = next(
            (
                item
                for item in templates
                if str(item.get("Id")) == str(requested_template_id)
            ),
            None,
        )
        if match is None:
            raise ConfigError(
                f"TemplateId {requested_template_id} was not returned by ListTemplates"
            )
        return requested_template_id, "explicit", match.get("Name")
    if not templates:
        raise ConfigError("ListTemplates did not return a selectable template")
    try:
        first_template_id = int(templates[0]["Id"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ConfigError("ListTemplates returned an invalid first template ID") from exc
    return first_template_id, "first template, matching the DE page", templates[0].get("Name")


def _page_overview(client: Any, args: argparse.Namespace) -> Dict[str, Any]:
    region_id = args.region_id
    templates = _query(
        client,
        region_id,
        "ListTemplates",
        {"CurrentPage": 1, "PageSize": 50, "Lang": args.lang},
        all_pages=args.template_id is not None,
        max_pages=args.max_pages,
    )
    template_id, selection, template_name = _resolve_template(templates, args.template_id)
    product_ids = _selected_product_ids(args)
    if product_ids is None and args.product_code_list != DEFAULT_PRODUCT_CODES:
        product_ids = ",".join(str(PRODUCT_IDS[code]) for code in args.product_code_list.split(","))
    product_codes = ",".join(code for code, value in PRODUCT_IDS.items()
                             if str(value) in product_ids.split(",")) if product_ids else args.product_code_list
    regions = _query(client, region_id, "ListRegions", {"Lang": args.lang})
    user_status = _query(client, region_id, "GetUserStatus", {"Lang": args.lang})
    total_sensitive = _query(
        client,
        region_id,
        "ListTotalSensitiveInfo",
        {
            "TemplateId": template_id,
            "ProductCodeList": product_codes,
            "CountType": 43,
            "Lang": args.lang,
        },
    )
    risk_levels = _query(
        client,
        region_id,
        "ListRiskLevels",
        {"TemplateId": template_id, "Lang": args.lang},
    )
    identify_models = _query(
        client,
        region_id,
        "ListIdentifyModels",
        {"TemplateId": template_id, "Lang": args.lang},
    )
    account_count = _query(
        client,
        region_id,
        "GetDataMaskingAccountCount",
        {"ProductIds": product_ids, "Lang": args.lang},
    )
    column_count = _query(
        client,
        region_id,
        "GetDataMaskingColumnCount",
        {"TemplateId": template_id, "ProductIds": product_ids, "Lang": args.lang},
    )
    instance_args = argparse.Namespace(**{
        **vars(args), "template_id": template_id, "product_ids": product_ids,
    })
    instances = _instances(client, instance_args)

    checks: List[Dict[str, Any]] = []
    if not args.skip_instance_checks:
        for item in _items(instances):
            instance_id = item.get("InstanceId")
            product_code = item.get("ProductCode")
            if not instance_id or not product_code:
                continue
            try:
                response = _query(
                    client,
                    item.get("RegionId") or region_id,
                    "CheckDataMaskingInstance",
                    {
                        "ProductCode": product_code,
                        "InstanceId": instance_id,
                        "Lang": args.lang,
                    },
                )
                checks.append(
                    {
                        "InstanceId": instance_id,
                        "ProductCode": product_code,
                        "RegionId": item.get("RegionId") or region_id,
                        **response,
                    }
                )
            except Exception as exc:
                checks.append(
                    {
                        "InstanceId": instance_id,
                        "ProductCode": product_code,
                        "RegionId": item.get("RegionId") or region_id,
                        "QueryError": safe_error(exc),
                        **safe_error_fields(exc),
                    }
                )
            time.sleep(0.02)

    account = account_count.get("AccountCount") or {}
    total_accounts = account.get("TotalCount", 0) or 0
    full = account.get("FullAccessCount", 0) or 0
    restricted = account.get("RestrictedAccessCount", 0) or 0
    none_access = account.get("NoneAccessCount", 0) or 0
    status = user_status.get("UserStatus") or {}
    total_quota = status.get("TotalColumnEncryptNumber", 0) or 0
    used_quota = status.get("UsedColumnEncryptNumber", 0) or 0
    columns = column_count.get("ColumnCount") or {}
    total_columns = columns.get("TotalCount", 0) or 0
    sensitive_columns = columns.get("SensitiveCount", 0) or 0
    encrypted_columns = columns.get("MaskedCount", 0) or 0
    failed_columns = columns.get("MaskingFailedCount", 0) or 0
    instance_items = _items(instances)

    return {
        "Mode": "READ_ONLY",
        "View": "DE_PAGE_OVERVIEW",
        "ApiVersion": API_VERSION,
        "RegionId": region_id,
        "InstanceFilters": {**_instance_params(instance_args), "InstanceSearch": args.instance_search},
        "CardScope": {"RegionId": region_id, "TemplateId": template_id, "ProductIds": product_ids,
                      "Note": "Summary APIs do not support the instance/engine/status/column filters."},
        "TemplateContext": {
            "TemplateId": template_id,
            "TemplateName": template_name,
            "Selection": selection,
        },
        "DerivedCards": {
            "ColumnEncryptionQuota": {
                "Total": total_quota,
                "Used": used_quota,
                "Available": total_quota - used_quota,
            },
            "Columns": {
                "Total": total_columns,
                "Sensitive": sensitive_columns,
                "Encrypted": encrypted_columns,
                "NotEncrypted": sensitive_columns - encrypted_columns - failed_columns,
                "Failed": failed_columns,
            },
            "Accounts": {
                "Total": total_accounts,
                "PlaintextAccess": full,
                "CiphertextAccess": restricted + none_access,
                "NotConfigured": total_accounts - full - restricted - none_access,
            },
            "TotalInstances": instances.get("TotalCount", len(instance_items)),
            "VisibleInstanceRows": len(instance_items),
            "InstanceCheckPassed": sum(
                1 for item in checks if not item.get("QueryError") and item.get("ErrorCode") == "Success"
            ),
            "InstanceCheckFailed": sum(
                1 for item in checks if not item.get("QueryError") and item.get("ErrorCode") not in (None, "Success")
            ),
            "InstanceCheckQueryError": sum(1 for item in checks if item.get("QueryError")),
        },
        "Calls": {
            "GetUserStatus": user_status,
            "ListRegions": regions,
            "ListTemplates": templates,
            "ListTotalSensitiveInfo": total_sensitive,
            "GetDataMaskingAccountCount": account_count,
            "ListIdentifyModels": identify_models,
            "ListRiskLevels": risk_levels,
            "ListDataMaskingInstances": instances,
            "GetDataMaskingColumnCount": column_count,
            "CheckDataMaskingInstance": checks,
        },
    }


def _kms_keys(client: Any, args: argparse.Namespace) -> Dict[str, Any]:
    response = _query(client, args.region_id, "ListKmsKeys", _identity_params(args))
    grouped: Dict[str, Dict[str, Any]] = {}
    for item in _items(response):
        key_id = item.get("KeyId")
        if not isinstance(key_id, str) or not key_id:
            continue
        entry = grouped.setdefault(key_id, {"KeyId": key_id, "AliasNames": []})
        alias = item.get("AliasName")
        if alias and alias not in entry["AliasNames"]:
            entry["AliasNames"].append(alias)

    keys = list(grouped.values())
    if args.key_id:
        keys = [item for item in keys if item["KeyId"] == args.key_id]

    if not args.skip_metadata:
        for item in keys:
            try:
                detail = _rpc_product(
                    client,
                    args.region_id,
                    "kms",
                    "2016-01-20",
                    "DescribeKey",
                    {"KeyId": item["KeyId"]},
                )
                metadata = detail.get("KeyMetadata") or {}
                item["KeyMetadata"] = metadata
                item["Selectable"] = metadata.get("KeyState") == "Enabled"
                item["DescribeKeyRequestId"] = detail.get("RequestId")
            except Exception as exc:
                item["Selectable"] = False
                item["DescribeKeyError"] = safe_error(exc)
                item.update(safe_error_fields(exc))
            time.sleep(0.02)

    return {
        "Mode": "READ_ONLY",
        "Action": "ListKmsKeys+DescribeKey" if not args.skip_metadata else "ListKmsKeys",
        "ApiVersion": API_VERSION,
        "RegionId": args.region_id,
        "RawListResponse": response,
        "Keys": keys,
        "MetadataChecked": not args.skip_metadata,
        "SelectableKeys": (
            [item for item in keys if item.get("Selectable")]
            if not args.skip_metadata
            else None
        ),
    }


def run_command(client: Any, args: argparse.Namespace) -> Dict[str, Any]:
    _validate_filters(args)
    command = args.command
    region_id = args.region_id
    lang = getattr(args, "lang", None)

    if command == "page":
        return _page_overview(client, args)
    if command == "user-status":
        return _query(client, region_id, "GetUserStatus", {"Lang": lang})
    if command == "regions":
        return _query(
            client,
            region_id,
            "ListRegions",
            {"Lang": lang, "Identified": args.identified, "Audited": args.audited},
        )
    if command == "templates":
        response = _query(
            client,
            region_id,
            "ListTemplates",
            {
                **_page_params(args),
                "CurrentPage": 1 if args.name else args.page,
                "UsageScenario": args.usage_scenario,
                "FeatureType": args.feature_type,
                "Lang": lang,
            },
            all_pages=args.all_pages or bool(args.name),
            max_pages=args.max_pages,
        )
        return _local_page(response, args, contains={"Name": args.name}) if args.name else response
    if command == "total-sensitive":
        return _query(
            client,
            region_id,
            "ListTotalSensitiveInfo",
            {
                **_template_params(args),
                "ProductCode": args.product_code,
                "ProductCodeList": args.product_code if args.product_code else args.product_code_list,
                "CountType": args.count_type,
                "Lang": lang,
            },
        )
    if command == "account-count":
        return _query(
            client,
            region_id,
            "GetDataMaskingAccountCount",
            {"ProductIds": args.product_ids, "Lang": lang},
        )
    if command == "risk-levels":
        return _query(
            client,
            region_id,
            "ListRiskLevels",
            {**_template_params(args), "FeatureType": args.feature_type, "Lang": lang},
        )
    if command == "identify-models":
        response = _query(
            client,
            region_id,
            "ListIdentifyModels",
            {
                **_template_params(args),
                "FeatureType": args.feature_type,
                "FilterAuditModel": args.filter_audit_model,
                "Lang": lang,
            },
        )
        return _local_name_filter(response, "RuleList", args.name)
    if command == "instances":
        return _instances(client, args)
    if command == "column-count":
        return _query(
            client,
            region_id,
            "GetDataMaskingColumnCount",
            {**_template_params(args), "ProductIds": args.product_ids, "Lang": lang},
        )
    if command == "check-instance":
        return _query(client, region_id, "CheckDataMaskingInstance", _identity_params(args))
    if command == "databases":
        return _query(
            client,
            region_id,
            "ListDataSources",
            {
                **_page_params(args),
                "ProductCode": args.product_code,
                "ProductId": args.product_id,
                "InstanceId": args.instance_id,
                "DbName": args.db_name,
                "ConnectStatus": args.connect_status,
                "IdentifyStatus": args.identify_status,
                "DataSourceId": args.data_source_id,
                "DataAssetId": args.data_asset_id,
                "Lang": lang,
            },
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )
    if command == "tables":
        return _query(
            client,
            region_id,
            "ListTables",
            {
                **_template_params(args),
                **_page_params(args),
                "ProductCode": args.product_code,
                "ProductId": args.product_id,
                "DataAssetSourceId": args.instance_id,
                "DataSourceName": args.db_name,
                "Name": args.name,
                "RiskLevelId": args.risk_level_id,
                "RuleId": args.rule_id,
                "Marker": args.marker,
                "Lang": lang,
            },
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )
    if command == "columns":
        return _query(
            client,
            region_id,
            "ListColumns",
            {
                **_template_params(args),
                **_page_params(args),
                "ProductCode": args.product_code,
                "ProductId": args.product_id,
                "DataAssetSourceId": args.instance_id,
                "DataSourceName": args.db_name,
                "TableName": args.table_name,
                "Name": args.name,
                "EngineType": args.engine_type,
                "RiskLevelId": args.risk_level_id,
                "RuleId": args.rule_id,
                "Lang": lang,
            },
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )
    if command == "masking-columns":
        return _query(
            client,
            region_id,
            "ListDataMaskingColumns",
            {
                **_template_params(args),
                **_page_params(args),
                "ProductCode": args.product_code,
                "ProductId": args.product_id or (int(args.product_ids) if args.product_ids else None),
                "InstanceId": args.instance_id,
                "DbName": args.db_name,
                "TableName": args.table_name,
                "ColumnName": args.column_name,
                "EngineType": args.engine_type,
                "MaskingStatus": args.masking_status,
                "RiskLevelIds": args.risk_level_ids,
                "TemplateRuleIds": args.template_rule_ids,
                "Lang": lang,
            },
            all_pages=args.all_pages,
            max_pages=args.max_pages,
        )
    if command == "accounts":
        local = bool(args.instance_search or args.account_search)
        response = _query(
            client,
            region_id,
            "ListDataAssetAccounts",
            {
                **_page_params(args),
                "CurrentPage": 1 if local else args.page,
                "ProductCode": args.product_code,
                "ProductIds": args.product_ids,
                "InstanceId": args.instance_id,
                "AccountName": args.account_name,
                "AuthRole": args.auth_role,
                "BizType": "DataMasking",
                "Lang": lang,
            },
            all_pages=args.all_pages or local,
            max_pages=args.max_pages,
        )
        return _local_page(response, args, contains=_clean({
            "InstanceId": args.instance_search, "AccountName": args.account_search,
        })) if local else response
    if command == "algorithms":
        return _query(
            client, region_id, "ListDataMaskingEncryptionAlgorithms", _identity_params(args)
        )
    if command == "instance-attribute":
        return _query(client, region_id, "GetInstanceAttribute", _identity_params(args))
    if command == "kms-keys":
        return _kms_keys(client, args)
    if command == "mini-engine-versions":
        return _query(client, region_id, "ListMiniEngineVersions", _identity_params(args))
    raise ConfigError(f"unsupported command: {command}")


def _add_connection(parser: argparse.ArgumentParser, *, region_required: bool = True) -> None:
    parser.add_argument(
        "--region-id",
        type=_nonblank,
        required=region_required,
        default=None if region_required else CONTROL_PLANE_REGION,
        help="service/asset region; global lists default to cn-zhangjiakou",
    )
    parser.add_argument("--profile", default="dsc-oauth",
                        help="CLI profile: OAuth, AK, StsToken or RamRoleArn (default: dsc-oauth)")
    parser.add_argument("--lang", type=_nonblank, default="zh", help="response language (default: zh)")


def _add_template(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    parser.add_argument("--template-id", type=_positive_int, required=required)


def _add_pagination(parser: argparse.ArgumentParser, *, default_size: int = 100) -> None:
    parser.add_argument("--page", type=_positive_int, default=1)
    parser.add_argument("--page-size", type=_positive_int, default=default_size)
    parser.add_argument("--all-pages", action="store_true")
    parser.add_argument("--max-pages", type=_positive_int, default=100)


def _add_identity(parser: argparse.ArgumentParser, *, engine: bool = False) -> None:
    parser.add_argument("--product-code", type=_product_code, required=True)
    parser.add_argument("--product-id", type=_positive_int)
    parser.add_argument("--instance-id", type=_nonblank, required=True)
    if engine:
        parser.add_argument("--engine-type", type=_engine_type)


def _add_instance_filters(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--masking-status", choices=MASKING_STATUSES)
    parser.add_argument("--risk-level-id", type=_positive_int)
    parser.add_argument("--sensitivity-level-ids", "--risk-level-ids",
                        dest="risk_level_ids", type=_csv_ids)
    parser.add_argument("--template-rule-ids", type=_csv_ids)
    parser.add_argument("--product-id", type=_positive_int)
    parser.add_argument("--product-ids", type=_csv_ids)
    parser.add_argument("--product-code", type=_product_code)
    parser.add_argument("--instance-id", type=_nonblank)
    parser.add_argument("--instance-search", type=_nonblank,
                        help="case-insensitive InstanceId substring; scans all pages before filtering")
    parser.add_argument("--engine-type", type=_engine_type,
                        help="fetches all pages and checks returned EngineType before pagination")
    parser.add_argument("--db-name", type=_nonblank)
    parser.add_argument("--table-name", type=_nonblank)
    parser.add_argument("--column-name", type=_nonblank)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only Sddp 2026-01-20 queries matching the DSC DE column-encryption page. "
            f"Allowlisted actions: {', '.join(PAGE_QUERY_ACTIONS)}"
        )
    )
    sub = parser.add_subparsers(dest="command", required=True)

    page = sub.add_parser("page", help="query the complete DE overview and current instance page")
    _add_connection(page)
    _add_template(page)
    _add_pagination(page, default_size=10)
    _add_instance_filters(page)
    page.add_argument("--product-code-list", type=_product_code_list, default=DEFAULT_PRODUCT_CODES)
    page.add_argument("--skip-instance-checks", action="store_true")

    user_status = sub.add_parser("user-status", help="column-encryption quota and sale status")
    _add_connection(user_status, region_required=False)

    regions = sub.add_parser("regions", help="select a region")
    _add_connection(regions, region_required=False)
    regions.add_argument("--identified", action=argparse.BooleanOptionalAction, default=None)
    regions.add_argument("--audited", action=argparse.BooleanOptionalAction, default=None)

    templates = sub.add_parser("templates", help="select a classification template / TemplateId")
    _add_connection(templates, region_required=False)
    _add_pagination(templates, default_size=50)
    templates.add_argument("--usage-scenario", type=int)
    templates.add_argument("--feature-type", type=int)
    templates.add_argument("--name", type=_nonblank, help="name substring; scans all pages before filtering")

    total_sensitive = sub.add_parser("total-sensitive", help="template/region sensitive totals")
    _add_connection(total_sensitive)
    _add_template(total_sensitive)
    total_sensitive.add_argument("--product-code", type=_product_code)
    total_sensitive.add_argument("--product-code-list", type=_product_code_list, default=DEFAULT_PRODUCT_CODES)
    total_sensitive.add_argument("--count-type", type=int, default=43)

    account_count = sub.add_parser("account-count", help="account summary cards")
    _add_connection(account_count)
    account_count.add_argument("--product-ids", type=_csv_ids)

    risk_levels = sub.add_parser("risk-levels", aliases=["sensitivity-levels"],
                                 help="select sensitive levels for a TemplateId")
    risk_levels.set_defaults(command="risk-levels")
    _add_connection(risk_levels, region_required=False)
    _add_template(risk_levels, required=True)
    risk_levels.add_argument("--feature-type", type=int)

    models = sub.add_parser("identify-models", help="select identify rules for a TemplateId")
    _add_connection(models, region_required=False)
    _add_template(models, required=True)
    models.add_argument("--feature-type", type=int)
    models.add_argument("--filter-audit-model", action=argparse.BooleanOptionalAction, default=None)
    models.add_argument("--name", type=_nonblank, help="case-insensitive client-side name filter")

    instances = sub.add_parser("instances", help="select a column-encryption instance")
    _add_connection(instances)
    _add_template(instances, required=True)
    _add_pagination(instances)
    _add_instance_filters(instances)

    column_count = sub.add_parser("column-count", help="total/sensitive/encrypted/failed columns")
    _add_connection(column_count)
    _add_template(column_count, required=True)
    column_count.add_argument("--product-ids", type=_csv_ids)

    check = sub.add_parser("check-instance", help="check whether an instance can use encryption")
    _add_connection(check)
    _add_identity(check)

    databases = sub.add_parser("databases", help="select a database for an instance")
    _add_connection(databases)
    _add_identity(databases)
    _add_pagination(databases)
    databases.add_argument("--db-name", type=_nonblank)
    databases.add_argument("--connect-status", type=_nonblank)
    databases.add_argument("--identify-status", type=_nonblank)
    databases.add_argument("--data-source-id", type=_nonblank)
    databases.add_argument("--data-asset-id", type=_nonblank)

    tables = sub.add_parser("tables", help="select a table for an instance/database/template")
    _add_connection(tables)
    _add_identity(tables)
    _add_template(tables, required=True)
    _add_pagination(tables)
    tables.add_argument("--db-name", type=_nonblank, required=True)
    tables.add_argument("--name", type=_nonblank)
    tables.add_argument("--risk-level-id", type=_positive_int)
    tables.add_argument("--rule-id", type=_positive_int)
    tables.add_argument("--marker", type=_positive_int)

    columns = sub.add_parser("columns", help="select a column for an instance/database/table/template")
    _add_connection(columns)
    _add_identity(columns, engine=True)
    _add_template(columns, required=True)
    _add_pagination(columns)
    columns.add_argument("--db-name", type=_nonblank, required=True)
    columns.add_argument("--table-name", type=_nonblank, required=True)
    columns.add_argument("--name", type=_nonblank)
    columns.add_argument("--risk-level-id", type=_positive_int)
    columns.add_argument("--rule-id", type=_positive_int)

    masking_columns = sub.add_parser(
        "masking-columns", help="query selectable columns and current encryption status"
    )
    _add_connection(masking_columns)
    _add_template(masking_columns, required=True)
    _add_pagination(masking_columns)
    masking_columns.add_argument("--product-code", type=_product_code)
    masking_columns.add_argument("--product-id", type=_positive_int)
    masking_columns.add_argument("--product-ids", type=_csv_ids)
    masking_columns.add_argument("--instance-id", type=_nonblank)
    masking_columns.add_argument("--db-name", type=_nonblank)
    masking_columns.add_argument("--table-name", type=_nonblank)
    masking_columns.add_argument("--column-name", type=_nonblank)
    masking_columns.add_argument("--engine-type", type=_engine_type)
    masking_columns.add_argument("--masking-status", choices=MASKING_STATUSES)
    masking_columns.add_argument("--sensitivity-level-ids", "--risk-level-ids",
                                dest="risk_level_ids", type=_csv_ids)
    masking_columns.add_argument("--template-rule-ids", type=_csv_ids)

    accounts = sub.add_parser("accounts", help="query database accounts and encryption access roles")
    _add_connection(accounts)
    _add_pagination(accounts)
    accounts.add_argument("--product-code", type=_product_code)
    accounts.add_argument("--product-ids", type=_csv_ids)
    accounts.add_argument("--instance-id", type=_nonblank)
    accounts.add_argument("--account-name", type=_nonblank)
    accounts.add_argument("--instance-search", type=_nonblank,
                          help="InstanceId substring; scans all pages before filtering")
    accounts.add_argument("--account-search", type=_nonblank,
                          help="AccountName substring; scans all pages before filtering")
    accounts.add_argument(
        "--auth-role",
        type=_auth_roles,
        help="one or more comma-separated roles",
    )

    algorithms = sub.add_parser("algorithms", help="query algorithms supported by an instance")
    _add_connection(algorithms)
    _add_identity(algorithms)

    attribute = sub.add_parser("instance-attribute", help="query engine/version/KMS support")
    _add_connection(attribute)
    _add_identity(attribute)

    kms = sub.add_parser("kms-keys", help="query KMS candidates and enabled key metadata")
    _add_connection(kms)
    _add_identity(kms)
    kms.add_argument("--key-id", type=_nonblank)
    kms.add_argument(
        "--skip-metadata",
        action="store_true",
        help="skip KMS DescribeKey; the DE page normally performs it",
    )

    versions = sub.add_parser("mini-engine-versions", help="query selectable upgrade versions")
    _add_connection(versions)
    _add_identity(versions)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        _validate_filters(args)
        profile = resolve_profile(args.profile)
        client = build_client(profile, args.region_id)
        result = run_command(client, args)
        result = {**result, "Authentication": {"Mode": profile.mode, "Profile": profile.name}}
    except Exception as exc:
        # Preserve the JSON error on stderr while exposing only validated CLI
        # status/code lines on stdout for callers that inspect the tool output.
        print_safe_error_diagnostics(exc, file=sys.stdout)
        print(
            json.dumps(
                {"Mode": "READ_ONLY", "Action": args.command, "Error": safe_error(exc),
                 **safe_error_fields(exc)},
                ensure_ascii=False,
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
