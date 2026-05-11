#!/usr/bin/env python3
"""DLF Metadata Query - Read-only CLI for querying DLF metadata.

Uses alibabacloud_dlfnext20250310 Python SDK.

Output: Always valid JSON to stdout.
  List actions:  {"count": N, "items": [...]}
  Get actions:   Single JSON object
  Errors:        {"error": "message", "hint": "what to do"}
"""

import json
import os
import re
import sys

try:
    from alibabacloud_tea_openapi.models import Config
    from alibabacloud_dlfnext20250310.client import Client
    from alibabacloud_dlfnext20250310 import models as dlf_models
    from alibabacloud_credentials.client import Client as CredentialClient
    from Tea.exceptions import TeaException
except ImportError:
    print(json.dumps({
        "error": "SDK not installed",
        "hint": "Run: pip install alibabacloud-dlfnext20250310 alibabacloud-credentials"
    }))
    sys.exit(1)


# Attribute lists for serialization (module-level constants)
_CATALOG_ATTRS = (
    "id", "name", "owner", "status", "type", "is_shared",
    "share_id", "created_at", "updated_at", "created_by",
    "updated_by", "options",
)
_DATABASE_ATTRS = (
    "id", "name", "owner", "location", "options",
    "created_at", "created_by", "updated_at", "updated_by",
)
_TABLE_ATTRS = (
    "id", "name", "path", "is_external", "schema_id",
    "owner", "storage_class", "created_at", "updated_at",
    "created_by", "updated_by",
)


def out_json(obj):
    print(json.dumps(obj, ensure_ascii=False, indent=2, default=str))


def out_error(msg, hint=None):
    obj = {"error": str(msg)}
    if hint:
        obj["hint"] = hint
    out_json(obj)
    sys.exit(1)


def extract_arg(args, name):
    """Extract a named argument from args list."""
    for i, arg in enumerate(args):
        if arg == name and i + 1 < len(args):
            val = args[i + 1]
            del args[i:i + 2]
            return val
    return None


# Validation patterns for input parameters
_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_\-\.]+$')
_ID_PATTERN = re.compile(r'^[a-zA-Z0-9_\-]+$')
_PATTERN_PARAM = re.compile(r'^[a-zA-Z0-9_\-\.%\*]+$')
_MAX_PARAM_LEN = 256


def _validate_param(val, name):
    """Validate parameter value for format and length."""
    if len(val) > _MAX_PARAM_LEN:
        out_error(f"Parameter {name} too long (max {_MAX_PARAM_LEN} chars)")
    if val.startswith('-'):
        out_error(f"Invalid value for {name}: '{val}' (looks like a flag, not a value)")


def _validate_name(val, name):
    """Validate a resource name (catalog, database, table)."""
    _validate_param(val, name)
    if not _NAME_PATTERN.match(val):
        out_error(
            f"Invalid {name}: '{val}'",
            f"{name} must contain only alphanumeric characters, hyphens, underscores, or dots"
        )


def _validate_id(val, name):
    """Validate a resource ID (catalog_id)."""
    _validate_param(val, name)
    if not _ID_PATTERN.match(val):
        out_error(
            f"Invalid {name}: '{val}'",
            f"{name} must contain only alphanumeric characters, hyphens, or underscores"
        )


def _validate_pattern(val, name):
    """Validate a search pattern parameter."""
    _validate_param(val, name)
    if not _PATTERN_PARAM.match(val):
        out_error(
            f"Invalid {name}: '{val}'",
            f"{name} must contain only alphanumeric characters, hyphens, underscores, dots, or wildcards (% *)"
        )


def require_arg(args, name, hint, validator=None):
    """Extract a required named argument, validate and exit with error if missing."""
    val = extract_arg(args, name)
    if not val:
        out_error(f"Missing {name}", hint)
    if validator:
        validator(val, name)
    return val


def extract_pagination_args(args):
    """Extract common pagination arguments: --pattern, --max-results, --page-token."""
    pattern = extract_arg(args, "--pattern")
    max_results = extract_arg(args, "--max-results")
    page_token = extract_arg(args, "--page-token")
    if pattern:
        _validate_pattern(pattern, "--pattern")
    if max_results:
        if not max_results.isdigit() or int(max_results) < 1 or int(max_results) > 10000:
            out_error("Invalid --max-results", "Must be an integer between 1 and 10000")
    if page_token:
        _validate_param(page_token, "--page-token")
    return pattern, int(max_results) if max_results else None, page_token


def out_paginated(items, next_page_token):
    """Output a paginated list result."""
    result = {"count": len(items), "items": items}
    if next_page_token:
        result["next_page_token"] = next_page_token
    out_json(result)


def build_client(args):
    """Build DLF client using default credential chain."""
    region = extract_arg(args, "--region") or "cn-hangzhou"
    _validate_name(region, "--region")

    try:
        credential = CredentialClient()
    except Exception as e:
        out_error(
            f"Failed to initialize credentials: {e}",
            "Configure credentials via environment variables, config file, or instance role. "
            "See https://help.aliyun.com/document_detail/378659.html"
        )

    config = Config(
        credential=credential,
        endpoint=f"dlfnext.{region}.aliyuncs.com",
        region_id=region,
        user_agent='AlibabaCloud-Agent-Skills/alibabacloud-dlf-manage',
        connect_timeout=5000,
        read_timeout=10000,
    )

    try:
        return Client(config)
    except Exception as e:
        out_error(f"Failed to create DLF client: {e}",
                  "Check credentials and region.")


def _serialize(obj, attrs):
    """Generic serializer: extract non-None attributes from an SDK object."""
    result = {}
    for a in attrs:
        v = getattr(obj, a, None)
        if v is not None:
            result[a] = v
    return result


def serialize_catalog(cat):
    return _serialize(cat, _CATALOG_ATTRS)


def serialize_database(db):
    return _serialize(db, _DATABASE_ATTRS)


def serialize_table(tbl):
    result = _serialize(tbl, _TABLE_ATTRS)
    schema = getattr(tbl, "schema", None)
    if schema:
        schema_dict = {}
        fields = getattr(schema, "fields", None)
        if fields:
            schema_dict["fields"] = [
                {"id": getattr(f, "id", i), "name": getattr(f, "name", ""),
                 "type": str(getattr(f, "type", ""))}
                for i, f in enumerate(fields)
            ]
        for key in ("partition_keys", "primary_keys", "options", "comment"):
            val = getattr(schema, key, None)
            if val is not None:
                schema_dict[key] = val
        result["schema"] = schema_dict
    return result


# ====== Action handlers ======

def action_list_catalogs(client, args):
    pattern, max_results, page_token = extract_pagination_args(args)
    request = dlf_models.ListCatalogsRequest(
        catalog_name_pattern=pattern,
        max_results=max_results,
        page_token=page_token,
    )
    resp = client.list_catalogs(request)
    catalogs = [serialize_catalog(c) for c in (resp.body.catalogs or [])]
    out_paginated(catalogs, resp.body.next_page_token)


def action_get_catalog(client, args):
    name = require_arg(args, "--catalog", "Specify catalog name, e.g. --catalog my_catalog", _validate_name)
    resp = client.get_catalog(name)
    out_json(serialize_catalog(resp.body))


def action_get_catalog_by_id(client, args):
    cid = require_arg(args, "--id", "Specify catalog ID, e.g. --id clg-paimon-xxxx", _validate_id)
    resp = client.get_catalog_by_id(cid)
    out_json(serialize_catalog(resp.body))


def action_list_databases(client, args):
    catalog_id = require_arg(args, "--catalog-id", "Specify catalog ID, e.g. --catalog-id clg-paimon-xxxx", _validate_id)
    pattern, max_results, page_token = extract_pagination_args(args)
    request = dlf_models.ListDatabasesRequest(
        database_name_pattern=pattern,
        max_results=max_results,
        page_token=page_token,
    )
    resp = client.list_databases(catalog_id, request)
    out_paginated(resp.body.databases or [], resp.body.next_page_token)


def action_list_database_details(client, args):
    catalog_id = require_arg(args, "--catalog-id", "Specify catalog ID, e.g. --catalog-id clg-paimon-xxxx", _validate_id)
    pattern, max_results, page_token = extract_pagination_args(args)
    request = dlf_models.ListDatabaseDetailsRequest(
        database_name_pattern=pattern,
        max_results=max_results,
        page_token=page_token,
    )
    resp = client.list_database_details(catalog_id, request)
    dbs = [serialize_database(d) for d in (resp.body.database_details or [])]
    out_paginated(dbs, resp.body.next_page_token)


def action_get_database(client, args):
    catalog_id = require_arg(args, "--catalog-id", "Specify catalog ID, e.g. --catalog-id clg-paimon-xxxx", _validate_id)
    database = require_arg(args, "--database", "Specify database name, e.g. --database my_db", _validate_name)
    resp = client.get_database(catalog_id, database)
    out_json(serialize_database(resp.body))


def action_list_tables(client, args):
    catalog_id = require_arg(args, "--catalog-id", "Specify catalog ID, e.g. --catalog-id clg-paimon-xxxx", _validate_id)
    database = require_arg(args, "--database", "Specify database name, e.g. --database my_db", _validate_name)
    pattern, max_results, page_token = extract_pagination_args(args)
    request = dlf_models.ListTablesRequest(
        table_name_pattern=pattern,
        max_results=max_results,
        page_token=page_token,
    )
    resp = client.list_tables(catalog_id, database, request)
    out_paginated(resp.body.tables or [], resp.body.next_page_token)


def action_list_table_details(client, args):
    catalog_id = require_arg(args, "--catalog-id", "Specify catalog ID, e.g. --catalog-id clg-paimon-xxxx", _validate_id)
    database = require_arg(args, "--database", "Specify database name, e.g. --database my_db", _validate_name)
    pattern, max_results, page_token = extract_pagination_args(args)
    request = dlf_models.ListTableDetailsRequest(
        table_name_pattern=pattern,
        max_results=max_results,
        page_token=page_token,
    )
    resp = client.list_table_details(catalog_id, database, request)
    tables = [serialize_table(t) for t in (resp.body.table_details or [])]
    out_paginated(tables, resp.body.next_page_token)


def action_get_table(client, args):
    catalog_id = require_arg(args, "--catalog-id", "Specify catalog ID, e.g. --catalog-id clg-paimon-xxxx", _validate_id)
    database = require_arg(args, "--database", "Specify database name, e.g. --database my_db", _validate_name)
    table = require_arg(args, "--table", "Specify table name, e.g. --table my_table", _validate_name)
    resp = client.get_table(catalog_id, database, table)
    out_json(serialize_table(resp.body))


ACTIONS = {
    "list-catalogs": action_list_catalogs,
    "get-catalog": action_get_catalog,
    "get-catalog-by-id": action_get_catalog_by_id,
    "list-databases": action_list_databases,
    "list-database-details": action_list_database_details,
    "get-database": action_get_database,
    "list-tables": action_list_tables,
    "list-table-details": action_list_table_details,
    "get-table": action_get_table,
}

HELP_TEXT = """Usage: dlf_metadata_query.py <action> [options...]

Catalog Actions:
  list-catalogs    [--pattern <name>]              List all catalogs
  get-catalog      --catalog <name>                Get catalog details by name
  get-catalog-by-id --id <catalog_id>              Get catalog details by ID

Database Actions:
  list-databases        --catalog-id <id> [--pattern <name>]    List database names
  list-database-details --catalog-id <id> [--pattern <name>]    List database details
  get-database          --catalog-id <id> --database <name>     Get database details

Table Actions:
  list-tables        --catalog-id <id> --database <name> [--pattern <name>]  List table names
  list-table-details --catalog-id <id> --database <name> [--pattern <name>]  List table details
  get-table          --catalog-id <id> --database <name> --table <name>      Get table details

Global Options:
  --region <region_id>     Optional. Defaults to cn-hangzhou.
  --max-results <N>        Optional. Max records per page.
  --page-token <token>     Optional. Pagination token.

Authentication:
  Uses default credential chain (CredentialClient). Supports:
  - Environment variables (ALIBABA_CLOUD_ACCESS_KEY_ID / SECRET)
  - Credentials file (~/.alibabacloud/credentials)
  - ECS instance RAM role
  See https://help.aliyun.com/document_detail/378659.html
"""


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h", "help"):
        print(HELP_TEXT)
        sys.exit(0)

    action = args.pop(0)

    if action not in ACTIONS:
        all_actions = ", ".join(sorted(ACTIONS.keys()))
        out_error(f"Unknown action: {action}",
                  f"Valid actions: {all_actions}")

    client = build_client(args)

    try:
        ACTIONS[action](client, args)
    except TeaException as e:
        error_msg = str(e)
        # statusCode is only populated when `data` is a dict containing statusCode
        # (see Tea.exceptions.TeaException). Fall back to matching the dotted code
        # string (e.g. 'Forbidden.RAM', 'EntityNotExist.Catalog').
        status_code = getattr(e, 'statusCode', None)
        code_str = str(getattr(e, 'code', '') or '')
        # Check 401 before 404: 'InvalidAccessKeyId.NotFound' contains "NotFound"
        # but is a credential error, not a missing resource.
        if (status_code == 401
                or code_str.startswith('Unauthorized')
                or code_str.startswith('InvalidAccessKey')
                or code_str == 'SignatureDoesNotMatch'):
            out_error(f"Authentication failed: {error_msg}",
                      "Check credential configuration. "
                      "See https://help.aliyun.com/document_detail/378659.html")
        elif status_code == 403 or code_str.startswith('Forbidden') or 'NoPermission' in code_str:
            out_error(f"Permission denied: {error_msg}",
                      "Grant DLF data permissions (LIST/DESCRIBE) in DLF console.")
        elif status_code == 404 or 'NotExist' in code_str or 'NotFound' in code_str:
            out_error(f"Resource not found: {error_msg}")
        else:
            out_error(f"API error: {error_msg}")
    except Exception as e:
        out_error(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()
