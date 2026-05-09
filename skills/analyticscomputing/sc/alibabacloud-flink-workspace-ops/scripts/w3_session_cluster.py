#!/usr/bin/env python3
"""W3: Session Cluster Management – create, update, delete, start, stop."""

from client import (
    add_common_args,
    call_api,
    get_client,
    output,
    require_args,
    require_confirmation,
    runtime_options,
)


def cmd_create_session_cluster(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_session_cluster",
        "Creating a Session cluster consumes compute resources.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        CreateSessionClusterHeaders,
        CreateSessionClusterRequest,
        SessionCluster,
    )
    import json as _json

    client = get_client(args.region_id)
    body = SessionCluster()
    if args.name:
        body.name = args.name
    if args.body_json:
        body = SessionCluster().from_map(_json.loads(args.body_json))

    headers = CreateSessionClusterHeaders(workspace=args.workspace)
    req = CreateSessionClusterRequest(body=body)
    result = call_api(
        "create_session_cluster",
        client.create_session_cluster_with_options,
        args.namespace, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_update_session_cluster(args):
    err = require_args(args, "workspace", "namespace", "region_id", "cluster_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_session_cluster",
        f"Update Session cluster '{args.cluster_id}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        UpdateSessionClusterHeaders,
        UpdateSessionClusterRequest,
        SessionCluster,
    )
    import json as _json

    client = get_client(args.region_id)
    body = SessionCluster()
    if args.body_json:
        body = SessionCluster().from_map(_json.loads(args.body_json))

    headers = UpdateSessionClusterHeaders(workspace=args.workspace)
    req = UpdateSessionClusterRequest(body=body)
    result = call_api(
        "update_session_cluster",
        client.update_session_cluster_with_options,
        args.namespace, args.cluster_id, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_delete_session_cluster(args):
    err = require_args(args, "workspace", "namespace", "region_id", "cluster_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_session_cluster",
        f"DELETE Session cluster '{args.cluster_id}' (IRREVERSIBLE). All jobs on this cluster will be affected.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteSessionClusterHeaders

    client = get_client(args.region_id)
    headers = DeleteSessionClusterHeaders(workspace=args.workspace)
    result = call_api(
        "delete_session_cluster",
        client.delete_session_cluster_with_options,
        args.namespace, args.cluster_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_get_session_cluster(args):
    err = require_args(args, "workspace", "namespace", "region_id", "cluster_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetSessionClusterHeaders

    client = get_client(args.region_id)
    headers = GetSessionClusterHeaders(workspace=args.workspace)
    result = call_api(
        "get_session_cluster",
        client.get_session_cluster_with_options,
        args.namespace, args.cluster_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_list_session_clusters(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListSessionClustersHeaders

    client = get_client(args.region_id)
    headers = ListSessionClustersHeaders(workspace=args.workspace)
    result = call_api(
        "list_session_clusters",
        client.list_session_clusters_with_options,
        args.namespace, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_start_session_cluster(args):
    err = require_args(args, "workspace", "namespace", "region_id", "cluster_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "start_session_cluster",
        f"Start Session cluster '{args.cluster_id}'. This consumes compute resources.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import StartSessionClusterHeaders

    client = get_client(args.region_id)
    headers = StartSessionClusterHeaders(workspace=args.workspace)
    result = call_api(
        "start_session_cluster",
        client.start_session_cluster_with_options,
        args.namespace, args.cluster_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_stop_session_cluster(args):
    err = require_args(args, "workspace", "namespace", "region_id", "cluster_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "stop_session_cluster",
        f"Stop Session cluster '{args.cluster_id}'. Jobs running on this cluster will be affected.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import StopSessionClusterHeaders

    client = get_client(args.region_id)
    headers = StopSessionClusterHeaders(workspace=args.workspace)
    result = call_api(
        "stop_session_cluster",
        client.stop_session_cluster_with_options,
        args.namespace, args.cluster_id, headers, runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Subparser registration
# ═══════════════════════════════════════════════════════════════════════════


def register(subparsers):
    """Register all W3 subcommands."""

    def _add(name, help_text, func, extra_args=None):
        p = subparsers.add_parser(name, help=help_text)
        add_common_args(p)
        if extra_args:
            extra_args(p)
        p.set_defaults(func=func, subcommand=name)

    def _create_args(p):
        p.add_argument("--name", help="Session cluster name")
        p.add_argument("--body_json", help="Full body as JSON (advanced)")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _id(p):
        p.add_argument("--cluster_id", required=True, help="Session cluster ID")

    def _id_confirm(p):
        p.add_argument("--cluster_id", required=True, help="Session cluster ID")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _id_force(p):
        p.add_argument("--cluster_id", required=True, help="Session cluster ID")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _update_args(p):
        p.add_argument("--cluster_id", required=True, help="Session cluster ID")
        p.add_argument("--body_json", help="Updated body as JSON (advanced)")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    _add("create_session_cluster", "Create a Session cluster", cmd_create_session_cluster, _create_args)
    _add("update_session_cluster", "Update Session cluster configuration", cmd_update_session_cluster, _update_args)
    _add("delete_session_cluster", "Delete a Session cluster (irreversible)", cmd_delete_session_cluster, _id_force)
    _add("get_session_cluster", "Get Session cluster details", cmd_get_session_cluster, _id)
    _add("list_session_clusters", "List all Session clusters", cmd_list_session_clusters, None)
    _add("start_session_cluster", "Start a Session cluster", cmd_start_session_cluster, _id_confirm)
    _add("stop_session_cluster", "Stop a Session cluster", cmd_stop_session_cluster, _id_confirm)
