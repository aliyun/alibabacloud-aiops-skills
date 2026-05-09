#!/usr/bin/env python3
"""W5: Workspace Administration – members, variables, deployment targets."""

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
# Member management (5)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_member(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_member",
        "Add a new member to the namespace.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import CreateMemberHeaders, CreateMemberRequest, Member
    import json as _json

    client = get_client(args.region_id)
    body = Member()
    if args.member:
        body.member = args.member
    if args.role:
        body.role = args.role
    if args.body_json:
        body = Member().from_map(_json.loads(args.body_json))
    headers = CreateMemberHeaders(workspace=args.workspace)
    req = CreateMemberRequest(body=body)
    result = call_api("create_member", client.create_member_with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


def cmd_update_member(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_member",
        "Update member permissions.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import UpdateMemberHeaders, UpdateMemberRequest, Member
    import json as _json

    client = get_client(args.region_id)
    body = Member()
    if args.member:
        body.member = args.member
    if args.role:
        body.role = args.role
    if args.body_json:
        body = Member().from_map(_json.loads(args.body_json))
    headers = UpdateMemberHeaders(workspace=args.workspace)
    req = UpdateMemberRequest(body=body)
    result = call_api("update_member", client.update_member_with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


def cmd_delete_member(args):
    err = require_args(args, "workspace", "namespace", "region_id", "member")
    if err:
        return output(err, args.output)
    chk = require_confirmation("delete_member", f"Delete member '{args.member}' from namespace.", args.confirm)
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteMemberHeaders

    client = get_client(args.region_id)
    headers = DeleteMemberHeaders(workspace=args.workspace)
    result = call_api("delete_member", client.delete_member_with_options, args.namespace, args.member, headers, runtime_options())
    output(result, args.output)


def cmd_get_member(args):
    err = require_args(args, "workspace", "namespace", "region_id", "member")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetMemberHeaders

    client = get_client(args.region_id)
    headers = GetMemberHeaders(workspace=args.workspace)
    result = call_api("get_member", client.get_member_with_options, args.namespace, args.member, headers, runtime_options())
    output(result, args.output)


def cmd_list_members(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListMembersHeaders, ListMembersRequest

    client = get_client(args.region_id)
    headers = ListMembersHeaders(workspace=args.workspace)
    req = ListMembersRequest()
    result = call_api("list_members", client.list_members_with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Variable management (4)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_variable(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_variable",
        "Create a new variable.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import CreateVariableHeaders, CreateVariableRequest, Variable
    import json as _json

    client = get_client(args.region_id)
    body = Variable()
    if args.var_name:
        body.name = args.var_name
    if args.var_value:
        body.value = args.var_value
    if args.body_json:
        body = Variable().from_map(_json.loads(args.body_json))
    headers = CreateVariableHeaders(workspace=args.workspace)
    req = CreateVariableRequest(body=body)
    result = call_api("create_variable", client.create_variable_with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


def cmd_update_variable(args):
    err = require_args(args, "workspace", "namespace", "region_id", "var_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_variable",
        f"Update variable '{args.var_name}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import UpdateVariableHeaders, UpdateVariableRequest, Variable
    import json as _json

    client = get_client(args.region_id)
    body = Variable()
    if args.var_name:
        body.name = args.var_name
    if args.var_value:
        body.value = args.var_value
    if args.body_json:
        body = Variable().from_map(_json.loads(args.body_json))
    headers = UpdateVariableHeaders(workspace=args.workspace)
    req = UpdateVariableRequest(body=body)
    result = call_api("update_variable", client.update_variable_with_options, args.namespace, args.var_name, req, headers, runtime_options())
    output(result, args.output)


def cmd_delete_variable(args):
    err = require_args(args, "workspace", "namespace", "region_id", "var_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation("delete_variable", f"Delete variable '{args.var_name}'. It may be referenced by jobs.", args.confirm)
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteVariableHeaders

    client = get_client(args.region_id)
    headers = DeleteVariableHeaders(workspace=args.workspace)
    result = call_api("delete_variable", client.delete_variable_with_options, args.namespace, args.var_name, headers, runtime_options())
    output(result, args.output)


def cmd_list_variables(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListVariablesHeaders, ListVariablesRequest

    client = get_client(args.region_id)
    headers = ListVariablesHeaders(workspace=args.workspace)
    req = ListVariablesRequest()
    result = call_api("list_variables", client.list_variables_with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Deployment targets (4, V2)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_deploy_target(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_deploy_target",
        "Create a new deployment target.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import CreateDeploymentTargetV2Headers, CreateDeploymentTargetV2Request, Resource
    import json as _json

    client = get_client(args.region_id)
    body = Resource()
    target_name = getattr(args, "name", None)
    if args.body_json:
        parsed = _json.loads(args.body_json)
        target_name = target_name or parsed.get("name")
        body = Resource().from_map(parsed.get("resource", parsed))
    headers = CreateDeploymentTargetV2Headers(workspace=args.workspace)
    req = CreateDeploymentTargetV2Request(body=body, deployment_target_name=target_name)
    result = call_api("create_deploy_target", client.create_deployment_target_v2with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


def cmd_update_deploy_target(args):
    err = require_args(args, "workspace", "namespace", "region_id", "target_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_deploy_target",
        f"Update deployment target '{args.target_name}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import UpdateDeploymentTargetV2Headers, UpdateDeploymentTargetV2Request, Resource
    import json as _json

    client = get_client(args.region_id)
    body = Resource()
    if args.body_json:
        parsed = _json.loads(args.body_json)
        body = Resource().from_map(parsed.get("resource", parsed))
    headers = UpdateDeploymentTargetV2Headers(workspace=args.workspace)
    req = UpdateDeploymentTargetV2Request(body=body)
    result = call_api("update_deploy_target", client.update_deployment_target_v2with_options, args.namespace, args.target_name, req, headers, runtime_options())
    output(result, args.output)


def cmd_delete_deploy_target(args):
    err = require_args(args, "workspace", "namespace", "region_id", "target_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation("delete_deploy_target", f"Delete deployment target '{args.target_name}'. Jobs may reference it.", args.confirm)
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteDeploymentTargetHeaders

    client = get_client(args.region_id)
    headers = DeleteDeploymentTargetHeaders(workspace=args.workspace)
    result = call_api("delete_deploy_target", client.delete_deployment_target_with_options, args.namespace, args.target_name, headers, runtime_options())
    output(result, args.output)


def cmd_list_deploy_targets(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListDeploymentTargetsHeaders, ListDeploymentTargetsRequest

    client = get_client(args.region_id)
    headers = ListDeploymentTargetsHeaders(workspace=args.workspace)
    req = ListDeploymentTargetsRequest()
    result = call_api("list_deploy_targets", client.list_deployment_targets_with_options, args.namespace, req, headers, runtime_options())
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Subparser registration
# ═══════════════════════════════════════════════════════════════════════════


def register(subparsers):
    """Register all W5 subcommands."""

    def _add(name, help_text, func, extra_args=None):
        p = subparsers.add_parser(name, help=help_text)
        add_common_args(p)
        if extra_args:
            extra_args(p)
        p.set_defaults(func=func, subcommand=name)

    # Members
    def _member_create(p):
        p.add_argument("--member", help="Member UID")
        p.add_argument("--role", help="Role name")
        p.add_argument("--body_json", help="Full member body as JSON")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _member_id(p):
        p.add_argument("--member", required=True, help="Member UID")

    def _member_delete(p):
        p.add_argument("--member", required=True, help="Member UID")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    _add("create_member", "Add a member with permissions", cmd_create_member, _member_create)
    _add("update_member", "Update member permissions", cmd_update_member, _member_create)
    _add("delete_member", "Delete a member", cmd_delete_member, _member_delete)
    _add("get_member", "Get member details", cmd_get_member, _member_id)
    _add("list_members", "List all members", cmd_list_members, None)

    # Variables
    def _var_create(p):
        p.add_argument("--var_name", help="Variable name")
        p.add_argument("--var_value", help="Variable value")
        p.add_argument("--body_json", help="Full variable body as JSON")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _var_update(p):
        p.add_argument("--var_name", required=True, help="Variable name")
        p.add_argument("--var_value", help="New variable value")
        p.add_argument("--body_json", help="Full variable body as JSON")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _var_delete(p):
        p.add_argument("--var_name", required=True, help="Variable name")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    _add("create_variable", "Create a variable", cmd_create_variable, _var_create)
    _add("update_variable", "Update a variable", cmd_update_variable, _var_update)
    _add("delete_variable", "Delete a variable", cmd_delete_variable, _var_delete)
    _add("list_variables", "List all variables", cmd_list_variables, None)

    # Deployment targets
    def _target_create(p):
        p.add_argument("--name", help="Deployment target name")
        p.add_argument("--body_json", help="Full body as JSON")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _target_update(p):
        p.add_argument("--target_name", required=True, help="Deployment target name")
        p.add_argument("--body_json", help="Updated body as JSON")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _target_delete(p):
        p.add_argument("--target_name", required=True, help="Deployment target name")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    _add("create_deploy_target", "Create a deployment target (V2)", cmd_create_deploy_target, _target_create)
    _add("update_deploy_target", "Update a deployment target (V2)", cmd_update_deploy_target, _target_update)
    _add("delete_deploy_target", "Delete a deployment target", cmd_delete_deploy_target, _target_delete)
    _add("list_deploy_targets", "List all deployment targets", cmd_list_deploy_targets, None)
