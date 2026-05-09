#!/usr/bin/env python3
"""W2: Job Operations – deployment management, job instances, savepoints, diagnostics."""

from client import (
    add_common_args,
    call_api,
    get_client,
    output,
    require_args,
    require_confirmation,
    runtime_options,
)

# ── helpers ────────────────────────────────────────────────────────────────

_HEADERS = {"Content-Type": "application/json"}


def _ws_ns(args):
    return args.workspace, args.namespace


# ═══════════════════════════════════════════════════════════════════════════
# Deployment management (9)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_deployment(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_deployment",
        "Creating a deployment consumes cluster resources.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        CreateDeploymentHeaders,
        CreateDeploymentRequest,
        Deployment,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)

    body = Deployment()
    if args.name:
        body.name = args.name
    if args.deployment_target:
        body.deployment_target_name = args.deployment_target
    if args.engine_version:
        body.engine_version = args.engine_version

    import json as _json

    if args.body_json:
        body = Deployment().from_map(_json.loads(args.body_json))

    headers = CreateDeploymentHeaders(workspace=ws)
    req = CreateDeploymentRequest(body=body)
    result = call_api(
        "create_deployment",
        client.create_deployment_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_update_deployment(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_deployment",
        f"Update deployment '{args.deployment_id}'. This may affect running jobs.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        UpdateDeploymentHeaders,
        UpdateDeploymentRequest,
        Deployment,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)

    import json as _json

    body = Deployment()
    if args.body_json:
        body = Deployment().from_map(_json.loads(args.body_json))

    headers = UpdateDeploymentHeaders(workspace=ws)
    req = UpdateDeploymentRequest(body=body)
    result = call_api(
        "update_deployment",
        client.update_deployment_with_options,
        ns,
        args.deployment_id,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_deployment(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetDeploymentHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetDeploymentHeaders(workspace=ws)
    result = call_api(
        "get_deployment",
        client.get_deployment_with_options,
        ns,
        args.deployment_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_list_deployments(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        ListDeploymentsHeaders,
        ListDeploymentsRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = ListDeploymentsHeaders(workspace=ws)
    req = ListDeploymentsRequest()
    if args.page_size:
        req.page_size = int(args.page_size)
    if args.page_index:
        req.page_index = int(args.page_index)
    result = call_api(
        "list_deployments",
        client.list_deployments_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_delete_deployment(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_deployment",
        f"DELETE deployment '{args.deployment_id}' (IRREVERSIBLE).",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteDeploymentHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = DeleteDeploymentHeaders(workspace=ws)
    result = call_api(
        "delete_deployment",
        client.delete_deployment_with_options,
        ns,
        args.deployment_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_search_by_name(args):
    err = require_args(args, "workspace", "namespace", "region_id", "name")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetDeploymentsByNameHeaders,
        GetDeploymentsByNameRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetDeploymentsByNameHeaders(workspace=ws)
    req = GetDeploymentsByNameRequest()
    result = call_api(
        "search_by_name",
        client.get_deployments_by_name_with_options,
        ns,
        args.name,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_search_by_label(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "label_key", "label_value"
    )
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetDeploymentsByLabelHeaders,
        GetDeploymentsByLabelRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetDeploymentsByLabelHeaders(workspace=ws)
    req = GetDeploymentsByLabelRequest(
        label_key=args.label_key, label_value=args.label_value
    )
    result = call_api(
        "search_by_label",
        client.get_deployments_by_label_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_search_by_ip(args):
    err = require_args(args, "workspace", "namespace", "region_id", "ip")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetDeploymentsByIpHeaders,
        GetDeploymentsByIpRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetDeploymentsByIpHeaders(workspace=ws)
    req = GetDeploymentsByIpRequest(dst_ip=args.ip)
    if getattr(args, "dst_port", None):
        req.dst_port = str(args.dst_port)
    if getattr(args, "src_ip", None):
        req.src_ip = args.src_ip
    if getattr(args, "src_port", None):
        req.src_port = str(args.src_port)
    result = call_api(
        "search_by_ip",
        client.get_deployments_by_ip_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_events(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetEventsHeaders, GetEventsRequest

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetEventsHeaders(workspace=ws)
    req = GetEventsRequest(deployment_id=args.deployment_id)
    result = call_api(
        "get_events",
        client.get_events_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Job instances (9)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_start_job(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "restore_strategy"
    )
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "start_job",
        f"Start job for deployment '{args.deployment_id}'. This consumes compute resources.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        StartJobWithParamsHeaders,
        StartJobWithParamsRequest,
        StartJobRequestBody,
        DeploymentRestoreStrategy,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)

    body = StartJobRequestBody(
        deployment_id=args.deployment_id,
        restore_strategy=DeploymentRestoreStrategy(kind=args.restore_strategy),
    )

    import json as _json

    if args.body_json:
        body = StartJobRequestBody().from_map(_json.loads(args.body_json))

    headers = StartJobWithParamsHeaders(workspace=ws)
    req = StartJobWithParamsRequest(body=body)
    result = call_api(
        "start_job",
        client.start_job_with_params_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_stop_job(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "job_id"
    )
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "stop_job",
        f"Stop job '{args.job_id}'. Consider creating a savepoint first to avoid data loss.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        StopJobHeaders,
        StopJobRequest,
        StopJobRequestBody,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)

    strategy = getattr(args, "stop_strategy", None) or "NONE"
    body = StopJobRequestBody(stop_strategy=strategy)
    headers = StopJobHeaders(workspace=ws)
    req = StopJobRequest(body=body)
    result = call_api(
        "stop_job",
        client.stop_job_with_options,
        ns,
        args.job_id,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_job(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "job_id"
    )
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetJobHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetJobHeaders(workspace=ws)
    result = call_api(
        "get_job",
        client.get_job_with_options,
        ns,
        args.job_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_list_jobs(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListJobsHeaders, ListJobsRequest

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = ListJobsHeaders(workspace=ws)
    req = ListJobsRequest(deployment_id=args.deployment_id)
    if args.page_size:
        req.page_size = int(args.page_size)
    if args.page_index:
        req.page_index = int(args.page_index)
    result = call_api(
        "list_jobs",
        client.list_jobs_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_delete_job(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "job_id"
    )
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_job",
        f"Delete job '{args.job_id}' (non-running state only). This is irreversible.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteJobHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = DeleteJobHeaders(workspace=ws)
    result = call_api(
        "delete_job",
        client.delete_job_with_options,
        ns,
        args.job_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_hot_update_job(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "job_id"
    )
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "hot_update_job",
        f"Hot-update running job '{args.job_id}'. This modifies a live job.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import HotUpdateJobHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = HotUpdateJobHeaders(workspace=ws)
    result = call_api(
        "hot_update_job",
        client.hot_update_job_with_options,
        ns,
        args.job_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_hot_update_result(args):
    err = require_args(args, "workspace", "namespace", "region_id", "hot_update_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetHotUpdateJobResultHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetHotUpdateJobResultHeaders(workspace=ws)
    result = call_api(
        "get_hot_update_result",
        client.get_hot_update_job_result_with_options,
        ns,
        args.hot_update_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_start_log(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "job_id"
    )
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetLatestJobStartLogHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetLatestJobStartLogHeaders(workspace=ws)
    result = call_api(
        "get_start_log",
        client.get_latest_job_start_log_with_options,
        ns,
        args.deployment_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_diagnose_job(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "deployment_id", "job_id"
    )
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetJobDiagnosisHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetJobDiagnosisHeaders(workspace=ws)
    result = call_api(
        "diagnose_job",
        client.get_job_diagnosis_with_options,
        ns,
        args.deployment_id,
        args.job_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Savepoints (4)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_savepoint(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_savepoint",
        f"Create savepoint for deployment '{args.deployment_id}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        CreateSavepointHeaders,
        CreateSavepointRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)

    req = CreateSavepointRequest(
        deployment_id=args.deployment_id,
        description=getattr(args, "description", None),
    )

    headers = CreateSavepointHeaders(workspace=ws)
    result = call_api(
        "create_savepoint",
        client.create_savepoint_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_savepoint(args):
    err = require_args(args, "workspace", "namespace", "region_id", "savepoint_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetSavepointHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetSavepointHeaders(workspace=ws)
    result = call_api(
        "get_savepoint",
        client.get_savepoint_with_options,
        ns,
        args.savepoint_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_delete_savepoint(args):
    err = require_args(args, "workspace", "namespace", "region_id", "savepoint_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_savepoint",
        f"Delete savepoint '{args.savepoint_id}'. This is irreversible.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteSavepointHeaders

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = DeleteSavepointHeaders(workspace=ws)
    result = call_api(
        "delete_savepoint",
        client.delete_savepoint_with_options,
        ns,
        args.savepoint_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_list_savepoints(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        ListSavepointsHeaders,
        ListSavepointsRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = ListSavepointsHeaders(workspace=ws)
    req = ListSavepointsRequest(deployment_id=args.deployment_id)
    if args.page_size:
        req.page_size = int(args.page_size)
    if args.page_index:
        req.page_index = int(args.page_index)
    result = call_api(
        "list_savepoints",
        client.list_savepoints_with_options,
        ns,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Auxiliary (4)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_generate_resource_plan(args):
    err = require_args(args, "workspace", "namespace", "region_id", "deployment_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GenerateResourcePlanWithFlinkConfAsyncHeaders,
        GenerateResourcePlanWithFlinkConfAsyncRequest,
    )
    import json as _json

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GenerateResourcePlanWithFlinkConfAsyncHeaders(workspace=ws)
    # The backend requires a request body; send an empty JSON object by default.
    body = {}
    if getattr(args, "body_json", None):
        parsed = _json.loads(args.body_json)
        if isinstance(parsed, dict):
            body = parsed
    req = GenerateResourcePlanWithFlinkConfAsyncRequest(body=body)
    result = call_api(
        "generate_resource_plan",
        client.generate_resource_plan_with_flink_conf_async_with_options,
        ns,
        args.deployment_id,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_resource_plan_result(args):
    err = require_args(args, "workspace", "namespace", "region_id", "ticket_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetGenerateResourcePlanResultHeaders,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetGenerateResourcePlanResultHeaders(workspace=ws)
    result = call_api(
        "get_resource_plan_result",
        client.get_generate_resource_plan_result_with_options,
        ns,
        args.ticket_id,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_get_lineage(args):
    err = require_args(
        args, "workspace", "namespace", "region_id", "lineage_id", "lineage_id_type"
    )
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        GetLineageInfoHeaders,
        GetLineageInfoParams,
        GetLineageInfoRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = GetLineageInfoHeaders(workspace=ws)
    # Backend requires these boolean fields to be present; default to False.
    is_column_level = getattr(args, "is_column_level", False)
    is_temporary = getattr(args, "is_temporary", False)
    params = GetLineageInfoParams(
        id=args.lineage_id,
        id_type=args.lineage_id_type,
        direction=getattr(args, "direction", None) or "BOTH",
        depth=getattr(args, "depth", None),
        is_column_level=bool(is_column_level),
        is_temporary=bool(is_temporary),
        namespace=ns,
        workspace=ws,
    )
    req = GetLineageInfoRequest(body=params)
    result = call_api(
        "get_lineage",
        client.get_lineage_info_with_options,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


def cmd_flink_api_proxy(args):
    err = require_args(args, "workspace", "namespace", "region_id", "flink_api_path")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        FlinkApiProxyHeaders,
        FlinkApiProxyRequest,
    )

    client = get_client(args.region_id)
    ws, ns = _ws_ns(args)
    headers = FlinkApiProxyHeaders(workspace=ws)
    req = FlinkApiProxyRequest(
        flink_api_path=args.flink_api_path,
        namespace=ns,
        resource_type=args.resource_type,
        resource_id=args.resource_id,
    )
    result = call_api(
        "flink_api_proxy",
        client.flink_api_proxy_with_options,
        req,
        headers,
        runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Subparser registration
# ═══════════════════════════════════════════════════════════════════════════


def register(subparsers):
    """Register all W2 subcommands on the given argparse subparsers object."""

    def _add(name, help_text, func, extra_args=None):
        p = subparsers.add_parser(name, help=help_text)
        add_common_args(p)
        if extra_args:
            extra_args(p)
        p.set_defaults(func=func, subcommand=name)

    # ── Deployment management ──────────────────────────────────────────

    def _deployment_create_args(p):
        p.add_argument("--name", help="Deployment name")
        p.add_argument("--deployment_target", help="Deployment target name")
        p.add_argument(
            "--engine_version", help="Engine version (e.g. vvr-8.0.9-flink-1.17)"
        )
        p.add_argument(
            "--body_json", help="Full deployment body as JSON string (advanced)"
        )
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _deployment_id_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")

    def _deployment_id_confirm(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _deployment_update_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--body_json", help="Updated deployment body as JSON string")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _page_args(p):
        p.add_argument("--page_size", help="Page size")
        p.add_argument("--page_index", help="Page index")

    def _search_name(p):
        p.add_argument("--name", required=True, help="Deployment name to search")

    def _search_label(p):
        p.add_argument("--label_key", required=True, help="Label key")
        p.add_argument("--label_value", required=True, help="Label value")

    def _search_ip(p):
        p.add_argument("--ip", required=True, help="Node IP address")
        p.add_argument("--dst_port", help="Destination port")
        p.add_argument("--src_ip", help="Source IP address")
        p.add_argument("--src_port", help="Source port")

    _add(
        "create_deployment",
        "Create a deployment",
        cmd_create_deployment,
        _deployment_create_args,
    )
    _add(
        "update_deployment",
        "Update a deployment",
        cmd_update_deployment,
        _deployment_update_args,
    )
    _add(
        "get_deployment",
        "Get deployment details",
        cmd_get_deployment,
        _deployment_id_args,
    )
    _add("list_deployments", "List all deployments", cmd_list_deployments, _page_args)
    _add(
        "delete_deployment",
        "Delete a deployment (irreversible)",
        cmd_delete_deployment,
        _deployment_id_confirm,
    )
    _add(
        "search_by_name", "Search deployments by name", cmd_search_by_name, _search_name
    )
    _add(
        "search_by_label",
        "Search deployments by label",
        cmd_search_by_label,
        _search_label,
    )
    _add(
        "search_by_ip", "Search deployments by IP address", cmd_search_by_ip, _search_ip
    )

    def _events_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")

    _add("get_events", "Get deployment run events", cmd_get_events, _events_args)

    # ── Job instances ──────────────────────────────────────────────────

    def _start_job_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument(
            "--restore_strategy", required=True, help="Restore strategy: LATEST or NONE"
        )
        p.add_argument("--body_json", help="Full start-job body as JSON (advanced)")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _job_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--job_id", required=True, help="Job ID")

    def _hot_update_result_args(p):
        p.add_argument(
            "--hot_update_id",
            required=True,
            help="Hot-update ID returned by hot_update_job",
        )

    def _job_confirm(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--job_id", required=True, help="Job ID")
        p.add_argument(
            "--stop_strategy",
            help="Stop strategy: NONE, STOP_WITH_SAVEPOINT, STOP_WITH_DRAIN",
        )
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _list_jobs_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--page_size", help="Page size")
        p.add_argument("--page_index", help="Page index")

    _add("start_job", "Start a job instance", cmd_start_job, _start_job_args)
    _add("stop_job", "Stop a job instance", cmd_stop_job, _job_confirm)
    _add("get_job", "Get job instance details", cmd_get_job, _job_args)
    _add(
        "list_jobs",
        "List job instances for a deployment",
        cmd_list_jobs,
        _list_jobs_args,
    )
    _add(
        "delete_job", "Delete a non-running job instance", cmd_delete_job, _job_confirm
    )
    _add("hot_update_job", "Hot-update a running job", cmd_hot_update_job, _job_confirm)
    _add(
        "get_hot_update_result",
        "Get hot-update result",
        cmd_get_hot_update_result,
        _hot_update_result_args,
    )
    _add("get_start_log", "Get latest job startup log", cmd_get_start_log, _job_args)
    _add("diagnose_job", "Diagnose job failures", cmd_diagnose_job, _job_args)

    # ── Savepoints ─────────────────────────────────────────────────────

    def _savepoint_create_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--description", help="Savepoint description")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _savepoint_id(p):
        p.add_argument("--savepoint_id", required=True, help="Savepoint ID")

    def _savepoint_delete(p):
        p.add_argument("--savepoint_id", required=True, help="Savepoint ID")
        p.add_argument(
            "--confirm", action="store_true", help="Skip interactive confirmation"
        )

    def _savepoint_list(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--page_size", help="Page size")
        p.add_argument("--page_index", help="Page index")

    _add(
        "create_savepoint",
        "Create a savepoint",
        cmd_create_savepoint,
        _savepoint_create_args,
    )
    _add("get_savepoint", "Get savepoint details", cmd_get_savepoint, _savepoint_id)
    _add(
        "delete_savepoint",
        "Delete a savepoint (irreversible)",
        cmd_delete_savepoint,
        _savepoint_delete,
    )
    _add(
        "list_savepoints",
        "List savepoints for a deployment",
        cmd_list_savepoints,
        _savepoint_list,
    )

    # ── Auxiliary ──────────────────────────────────────────────────────

    def _resource_plan_args(p):
        p.add_argument("--deployment_id", required=True, help="Deployment ID")
        p.add_argument("--body_json", help="Flink conf JSON object for plan generation")

    def _ticket_args(p):
        p.add_argument("--ticket_id", required=True, help="Async ticket ID")

    def _flink_proxy_args(p):
        p.add_argument("--flink_api_path", required=True, help="Flink REST API path")
        p.add_argument(
            "--resource_type", help="Resource type (sessioncluster or deployment)"
        )
        p.add_argument("--resource_id", help="Resource ID (cluster or deployment ID)")

    def _lineage_args(p):
        p.add_argument(
            "--lineage_id", required=True, help="Lineage root ID (job ID or table ID)"
        )
        p.add_argument(
            "--lineage_id_type",
            required=True,
            help="Lineage ID type (for example JOB or TABLE)",
        )
        p.add_argument(
            "--direction",
            default="BOTH",
            help="Lineage direction: UPSTREAM, DOWNSTREAM, BOTH",
        )
        p.add_argument("--depth", type=int, help="Lineage depth")
        p.add_argument(
            "--is_column_level", action="store_true", help="Use column-level lineage"
        )
        p.add_argument(
            "--is_temporary", action="store_true", help="Mark table as temporary"
        )

    _add(
        "generate_resource_plan",
        "Generate resource plan (async)",
        cmd_generate_resource_plan,
        _resource_plan_args,
    )
    _add(
        "get_resource_plan_result",
        "Get resource plan generation result",
        cmd_get_resource_plan_result,
        _ticket_args,
    )
    _add("get_lineage", "Get job lineage information", cmd_get_lineage, _lineage_args)
    _add(
        "flink_api_proxy",
        "Proxy Flink REST API (read-only)",
        cmd_flink_api_proxy,
        _flink_proxy_args,
    )
