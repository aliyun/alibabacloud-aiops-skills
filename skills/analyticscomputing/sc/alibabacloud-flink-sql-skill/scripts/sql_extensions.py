#!/usr/bin/env python3
"""SQL lifecycle implementation for Catalogs, Tables, Connectors, UDFs, and engines."""

from client import (
    add_common_args,
    call_api,
    get_client,
    output,
    require_args,
    require_confirmation,
    runtime_options,
)


# ═══════════════════════════════════════════════════════════════════════════
# UDF management (six commands)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_udf_artifact(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_udf_artifact",
        "Upload and parse a UDF Artifact.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        CreateUdfArtifactHeaders,
        CreateUdfArtifactRequest,
        UdfArtifact,
    )
    import json as _json

    client = get_client(args.region_id)
    body = UdfArtifact()
    if args.body_json:
        body = UdfArtifact().from_map(_json.loads(args.body_json))
    headers = CreateUdfArtifactHeaders(workspace=args.workspace)
    req = CreateUdfArtifactRequest(body=body)
    result = call_api(
        "create_udf_artifact",
        client.create_udf_artifact_with_options,
        args.namespace,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_update_udf_artifact(args):
    err = require_args(args, "workspace", "namespace", "region_id", "udf_artifact_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_udf_artifact",
        f"Update UDF Artifact '{args.udf_artifact_name}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        UpdateUdfArtifactHeaders,
        UpdateUdfArtifactRequest,
        UdfArtifact,
    )
    import json as _json

    client = get_client(args.region_id)
    body = UdfArtifact()
    if args.body_json:
        body = UdfArtifact().from_map(_json.loads(args.body_json))
    headers = UpdateUdfArtifactHeaders(workspace=args.workspace)
    req = UpdateUdfArtifactRequest(body=body)
    result = call_api(
        "update_udf_artifact",
        client.update_udf_artifact_with_options,
        args.namespace,
        args.udf_artifact_name,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_udf_artifacts(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetUdfArtifactsHeaders,
        GetUdfArtifactsRequest,
    )

    client = get_client(args.region_id)
    headers = GetUdfArtifactsHeaders(workspace=args.workspace)
    req = GetUdfArtifactsRequest()
    if args.udf_artifact_name:
        req.udf_artifact_name = args.udf_artifact_name
    result = call_api(
        "get_udf_artifacts",
        client.get_udf_artifacts_with_options,
        args.namespace,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_delete_udf_artifact(args):
    err = require_args(args, "workspace", "namespace", "region_id", "udf_artifact_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_udf_artifact",
        f"Delete UDF Artifact '{args.udf_artifact_name}'. Delete its registered Functions first.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteUdfArtifactHeaders

    client = get_client(args.region_id)
    headers = DeleteUdfArtifactHeaders(workspace=args.workspace)
    result = call_api(
        "delete_udf_artifact",
        client.delete_udf_artifact_with_options,
        args.namespace,
        args.udf_artifact_name,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_register_udf_function(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "register_udf_function",
        "Register a UDF Function for use in SQL.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        RegisterUdfFunctionHeaders,
        RegisterUdfFunctionRequest,
    )
    import json as _json

    client = get_client(args.region_id)
    parsed = _json.loads(args.body_json) if args.body_json else {}
    headers = RegisterUdfFunctionHeaders(workspace=args.workspace)
    req = RegisterUdfFunctionRequest(
        class_name=parsed.get("className"),
        function_name=parsed.get("functionName"),
        udf_artifact_name=parsed.get("udfArtifactName"),
    )
    result = call_api(
        "register_udf_function",
        client.register_udf_function_with_options,
        args.namespace,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_delete_udf_function(args):
    err = require_args(args, "workspace", "namespace", "region_id", "function_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_udf_function",
        f"Delete UDF Function '{args.function_name}'. A SQL Job may reference it.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        DeleteUdfFunctionHeaders,
        DeleteUdfFunctionRequest,
    )

    client = get_client(args.region_id)
    headers = DeleteUdfFunctionHeaders(workspace=args.workspace)
    req = DeleteUdfFunctionRequest(
        class_name=getattr(args, "class_name", None),
        udf_artifact_name=getattr(args, "udf_artifact_name", None),
    )
    result = call_api(
        "delete_udf_function",
        client.delete_udf_function_with_options,
        args.namespace,
        args.function_name,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Custom Connectors (three commands)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_list_connectors(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListCustomConnectorsHeaders

    client = get_client(args.region_id)
    headers = ListCustomConnectorsHeaders(workspace=args.workspace)
    result = call_api(
        "list_connectors",
        client.list_custom_connectors_with_options,
        args.namespace,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_register_connector(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "register_connector",
        "Register a custom Connector.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        RegisterCustomConnectorHeaders,
        RegisterCustomConnectorRequest,
    )
    import json as _json

    client = get_client(args.region_id)
    parsed = _json.loads(args.body_json) if args.body_json else {}
    headers = RegisterCustomConnectorHeaders(workspace=args.workspace)
    req = RegisterCustomConnectorRequest(jar_url=parsed.get("jarUrl"))
    result = call_api(
        "register_connector",
        client.register_custom_connector_with_options,
        args.namespace,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_delete_connector(args):
    err = require_args(args, "workspace", "namespace", "region_id", "connector_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_connector",
        f"Delete Connector '{args.connector_name}'. A Job may reference it.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteCustomConnectorHeaders

    client = get_client(args.region_id)
    headers = DeleteCustomConnectorHeaders(workspace=args.workspace)
    result = call_api(
        "delete_connector",
        client.delete_custom_connector_with_options,
        args.namespace,
        args.connector_name,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Metadata (four commands)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_get_catalogs(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetCatalogsHeaders,
        GetCatalogsRequest,
    )

    client = get_client(args.region_id)
    headers = GetCatalogsHeaders(workspace=args.workspace)
    req = GetCatalogsRequest()
    if args.catalog_name:
        req.catalog_name = args.catalog_name
    result = call_api(
        "get_catalogs",
        client.get_catalogs_with_options,
        args.namespace,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_databases(args):
    err = require_args(args, "workspace", "namespace", "region_id", "catalog_name")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetDatabasesHeaders,
        GetDatabasesRequest,
    )

    client = get_client(args.region_id)
    headers = GetDatabasesHeaders(workspace=args.workspace)
    req = GetDatabasesRequest()
    if args.database_name:
        req.database_name = args.database_name
    result = call_api(
        "get_databases",
        client.get_databases_with_options,
        args.namespace,
        args.catalog_name,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_tables(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "catalog_name", "database_name"
    )
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetTablesHeaders, GetTablesRequest

    client = get_client(args.region_id)
    headers = GetTablesHeaders(workspace=args.workspace)
    req = GetTablesRequest()
    if args.table_name:
        req.table_name = args.table_name
    result = call_api(
        "get_tables",
        client.get_tables_with_options,
        args.namespace,
        args.catalog_name,
        args.database_name,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_execute_sql(args):
    err = require_args(args, "workspace", "namespace", "region_id", "statement")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "execute_sql",
        "Execute a DDL or DML statement. This modifies metadata.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        ExecuteSqlStatementHeaders,
        ExecuteSqlStatementRequest,
        SqlStatementWithContext,
    )

    client = get_client(args.region_id)
    headers = ExecuteSqlStatementHeaders(workspace=args.workspace)
    body = SqlStatementWithContext(statement=args.statement)
    req = ExecuteSqlStatementRequest(body=body)
    result = call_api(
        "execute_sql",
        client.execute_sql_statement_with_options,
        args.namespace,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Engine versions (one command)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_list_engine_versions(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListEngineVersionMetadataHeaders

    client = get_client(args.region_id)
    headers = ListEngineVersionMetadataHeaders(workspace=args.workspace)
    result = call_api(
        "list_engine_versions",
        client.list_engine_version_metadata_with_options,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Subparser registration
# ═══════════════════════════════════════════════════════════════════════════


def register(subparsers):
    """Register SQL metadata, Connector, UDF, and engine subcommands."""

    def _add(name, help_text, func, extra_args=None):
        p = subparsers.add_parser(name, help=help_text)
        add_common_args(p)
        if extra_args:
            extra_args(p)
        p.set_defaults(func=func, subcommand=name)

    # UDF
    def _udf_create(p):
        p.add_argument("--body_json", required=True, help="UDF Artifact Body JSON")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _udf_name(p):
        p.add_argument("--udf_artifact_name", required=True, help="UDF Artifact name")

    def _udf_update(p):
        p.add_argument("--udf_artifact_name", required=True, help="UDF Artifact name")
        p.add_argument("--body_json", required=True, help="Updated request body JSON")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _udf_get(p):
        p.add_argument("--udf_artifact_name", help="Filter by Artifact name (optional)")

    def _udf_delete(p):
        p.add_argument("--udf_artifact_name", required=True, help="UDF Artifact name")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _udf_register(p):
        p.add_argument(
            "--body_json", required=True, help="UDF Function registration request body JSON"
        )
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _udf_fn_delete(p):
        p.add_argument("--function_name", required=True, help="UDF Function name")
        p.add_argument("--class_name", help="UDF class name (required by the API)")
        p.add_argument(
            "--udf_artifact_name", help="UDF Artifact name (required by the API)"
        )
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    # Connector
    def _conn_register(p):
        p.add_argument("--body_json", required=True, help="Connector Body JSON")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _conn_delete(p):
        p.add_argument("--connector_name", required=True, help="Connector name")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    # Metadata
    def _catalog(p):
        p.add_argument(
            "--catalog_name", help="Catalog name (optional; omit to list all Catalogs)"
        )

    def _database(p):
        p.add_argument("--catalog_name", required=True, help="Catalog name")
        p.add_argument("--database_name", help="Database name (optional)")

    def _table(p):
        p.add_argument("--catalog_name", required=True, help="Catalog name")
        p.add_argument("--database_name", required=True, help="Database name")
        p.add_argument("--table_name", help="Table name (optional)")

    def _sql(p):
        p.add_argument("--statement", required=True, help="DDL or DML SQL statement")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    _add("get_catalogs", "List Catalogs or get Catalog details", cmd_get_catalogs, _catalog)
    _add("get_databases", "List Databases or get Database details", cmd_get_databases, _database)
    _add("get_tables", "List Tables or get Table details", cmd_get_tables, _table)
    _add("execute_sql", "Execute a DDL or DML SQL statement (DQL is unsupported)", cmd_execute_sql, _sql)

    # UDF Artifact
    _add(
        "create_udf_artifact",
        "Create a UDF Artifact",
        cmd_create_udf_artifact,
        _udf_create,
    )
    _add(
        "update_udf_artifact",
        "Update a UDF Artifact",
        cmd_update_udf_artifact,
        _udf_update,
    )
    _add(
        "get_udf_artifacts",
        "List UDF Artifacts or get Artifact details",
        cmd_get_udf_artifacts,
        _udf_get,
    )
    _add(
        "delete_udf_artifact",
        "Delete a UDF Artifact",
        cmd_delete_udf_artifact,
        _udf_delete,
    )
    _add(
        "register_udf_function",
        "Register a UDF Function",
        cmd_register_udf_function,
        _udf_register,
    )
    _add(
        "delete_udf_function",
        "Delete a UDF Function",
        cmd_delete_udf_function,
        _udf_fn_delete,
    )

    # Connector
    _add("list_connectors", "List custom Connectors", cmd_list_connectors, None)
    _add(
        "register_connector",
        "Register a custom Connector",
        cmd_register_connector,
        _conn_register,
    )
    _add(
        "delete_connector",
        "Delete a custom Connector",
        cmd_delete_connector,
        _conn_delete,
    )

    # Engine versions
    _add(
        "list_engine_versions",
        "List supported engine versions",
        cmd_list_engine_versions,
        None,
    )
