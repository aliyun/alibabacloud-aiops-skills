#!/usr/bin/env python3
"""W1: SQL Development & Deployment – folders, drafts, validation, deploy."""

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
# Folder management (4)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_folder(args):
    err = require_args(args, "workspace", "namespace", "region_id", "folder_name")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_folder",
        f"Create folder '{args.folder_name}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import CreateFolderHeaders, CreateFolderRequest, Folder

    client = get_client(args.region_id)
    body = Folder(name=args.folder_name)
    if args.parent_id:
        body.parent_id = args.parent_id
    headers = CreateFolderHeaders(workspace=args.workspace)
    req = CreateFolderRequest(body=body)
    ns = args.namespace
    result = call_api(
        "create_folder",
        client.create_folder_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_update_folder(args):
    err = require_args(args, "workspace", "namespace", "region_id", "folder_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_folder",
        f"Update folder '{args.folder_id}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import UpdateFolderHeaders, UpdateFolderRequest, Folder

    client = get_client(args.region_id)
    body = Folder()
    if args.folder_name:
        body.name = args.folder_name
    headers = UpdateFolderHeaders(workspace=args.workspace)
    req = UpdateFolderRequest(body=body)
    ns = args.namespace
    result = call_api(
        "update_folder",
        client.update_folder_with_options,
        ns, args.folder_id, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_delete_folder(args):
    err = require_args(args, "workspace", "namespace", "region_id", "folder_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_folder",
        f"Delete folder '{args.folder_id}'. Only empty folders can be deleted.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteFolderHeaders

    client = get_client(args.region_id)
    headers = DeleteFolderHeaders(workspace=args.workspace)
    ns = args.namespace
    result = call_api(
        "delete_folder",
        client.delete_folder_with_options,
        ns, args.folder_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_get_folder(args):
    err = require_args(args, "workspace", "namespace", "region_id", "folder_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetFolderHeaders, GetFolderRequest

    client = get_client(args.region_id)
    headers = GetFolderHeaders(workspace=args.workspace)
    req = GetFolderRequest(folder_id=args.folder_id)
    ns = args.namespace
    result = call_api(
        "get_folder",
        client.get_folder_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Draft management (6)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_create_draft(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "create_draft",
        "Create a new deployment draft.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        CreateDeploymentDraftHeaders,
        CreateDeploymentDraftRequest,
        DeploymentDraft,
        Artifact,
        SqlArtifact,
    )
    import json as _json

    client = get_client(args.region_id)
    if args.body_json:
        body = DeploymentDraft().from_map(_json.loads(args.body_json))
    else:
        body = DeploymentDraft()
        if args.name:
            body.name = args.name
        if args.folder_id:
            body.parent_id = args.folder_id
        # execution_mode defaults to STREAMING
        body.execution_mode = getattr(args, "execution_mode", None) or "STREAMING"
        # engine_version is required by the API
        body.engine_version = getattr(args, "engine_version", None) or "vvr-8.0.11-flink-1.17"
        if args.content:
            body.artifact = Artifact(
                kind="SQLSCRIPT",
                sql_artifact=SqlArtifact(sql_script=args.content),
            )

    headers = CreateDeploymentDraftHeaders(workspace=args.workspace)
    req = CreateDeploymentDraftRequest(body=body)
    ns = args.namespace
    result = call_api(
        "create_draft",
        client.create_deployment_draft_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_update_draft(args):
    err = require_args(args, "workspace", "namespace", "region_id", "draft_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "update_draft",
        f"Update draft '{args.draft_id}'.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        UpdateDeploymentDraftHeaders,
        UpdateDeploymentDraftRequest,
        DeploymentDraft,
        Artifact,
        SqlArtifact,
    )
    import json as _json

    client = get_client(args.region_id)
    if args.body_json:
        body = DeploymentDraft().from_map(_json.loads(args.body_json))
    else:
        body = DeploymentDraft()
        if args.content:
            body.artifact = Artifact(
                kind="SQLSCRIPT",
                sql_artifact=SqlArtifact(sql_script=args.content),
            )

    headers = UpdateDeploymentDraftHeaders(workspace=args.workspace)
    req = UpdateDeploymentDraftRequest(body=body)
    ns = args.namespace
    result = call_api(
        "update_draft",
        client.update_deployment_draft_with_options,
        ns, args.draft_id, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_delete_draft(args):
    err = require_args(args, "workspace", "namespace", "region_id", "draft_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "delete_draft",
        f"Delete draft '{args.draft_id}'. Cannot delete drafts with active deployments.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import DeleteDeploymentDraftHeaders

    client = get_client(args.region_id)
    headers = DeleteDeploymentDraftHeaders(workspace=args.workspace)
    ns = args.namespace
    result = call_api(
        "delete_draft",
        client.delete_deployment_draft_with_options,
        ns, args.draft_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_get_draft(args):
    err = require_args(args, "workspace", "namespace", "region_id", "draft_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetDeploymentDraftHeaders

    client = get_client(args.region_id)
    headers = GetDeploymentDraftHeaders(workspace=args.workspace)
    ns = args.namespace
    result = call_api(
        "get_draft",
        client.get_deployment_draft_with_options,
        ns, args.draft_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_list_drafts(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import ListDeploymentDraftsHeaders, ListDeploymentDraftsRequest

    client = get_client(args.region_id)
    headers = ListDeploymentDraftsHeaders(workspace=args.workspace)
    req = ListDeploymentDraftsRequest()
    if args.page_size:
        req.page_size = int(args.page_size)
    if args.page_index:
        req.page_index = int(args.page_index)
    ns = args.namespace
    result = call_api(
        "list_drafts",
        client.list_deployment_drafts_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_get_draft_lock(args):
    err = require_args(args, "workspace", "namespace", "region_id", "draft_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetDeploymentDraftLockHeaders, GetDeploymentDraftLockRequest

    client = get_client(args.region_id)
    headers = GetDeploymentDraftLockHeaders(workspace=args.workspace)
    req = GetDeploymentDraftLockRequest(deployment_draft_id=args.draft_id)
    ns = args.namespace
    result = call_api(
        "get_draft_lock",
        client.get_deployment_draft_lock_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Validation & Deploy (5)
# ═══════════════════════════════════════════════════════════════════════════


def cmd_validate_draft(args):
    err = require_args(args, "workspace", "namespace", "region_id", "draft_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        ValidateDeploymentDraftAsyncHeaders,
        ValidateDeploymentDraftAsyncRequest,
        DraftValidateParams,
    )

    client = get_client(args.region_id)
    headers = ValidateDeploymentDraftAsyncHeaders(workspace=args.workspace)
    body = DraftValidateParams(
        deployment_draft_id=args.draft_id,
        deployment_target_name=getattr(args, "deployment_target", None),
    )
    req = ValidateDeploymentDraftAsyncRequest(body=body)
    ns = args.namespace
    result = call_api(
        "validate_draft",
        client.validate_deployment_draft_async_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_get_validate_result(args):
    err = require_args(args, "workspace", "namespace", "region_id", "ticket_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetValidateDeploymentDraftResultHeaders

    client = get_client(args.region_id)
    headers = GetValidateDeploymentDraftResultHeaders(workspace=args.workspace)
    ns = args.namespace
    result = call_api(
        "get_validate_result",
        client.get_validate_deployment_draft_result_with_options,
        ns, args.ticket_id, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_validate_sql(args):
    err = require_args(args, "workspace", "namespace", "region_id", "statement")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import (
        ValidateSqlStatementHeaders,
        ValidateSqlStatementRequest,
        SqlStatementWithContext,
    )

    client = get_client(args.region_id)
    headers = ValidateSqlStatementHeaders(workspace=args.workspace)
    body = SqlStatementWithContext(statement=args.statement)
    req = ValidateSqlStatementRequest(body=body)
    ns = args.namespace
    result = call_api(
        "validate_sql",
        client.validate_sql_statement_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_deploy_draft(args):
    err = require_args(args, "workspace", "namespace", "region_id", "draft_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "deploy_draft",
        f"Deploy draft '{args.draft_id}' to production. This may affect running jobs.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    from alibabacloud_ververica20220718.models import (
        DeployDeploymentDraftAsyncHeaders,
        DeployDeploymentDraftAsyncRequest,
        DraftDeployParams,
        BriefDeploymentTarget,
    )

    client = get_client(args.region_id)
    headers = DeployDeploymentDraftAsyncHeaders(workspace=args.workspace)
    dep_target = None
    if getattr(args, "deployment_target", None):
        dep_target = BriefDeploymentTarget(
            mode=getattr(args, "deployment_target_mode", "PER_JOB"),
            name=args.deployment_target,
        )
    body = DraftDeployParams(
        deployment_draft_id=args.draft_id,
        deployment_target=dep_target,
    )
    req = DeployDeploymentDraftAsyncRequest(body=body)
    ns = args.namespace
    result = call_api(
        "deploy_draft",
        client.deploy_deployment_draft_async_with_options,
        ns, req, headers, runtime_options(),
    )
    output(result, args.output)


def cmd_get_deploy_result(args):
    err = require_args(args, "workspace", "namespace", "region_id", "ticket_id")
    if err:
        return output(err, args.output)

    from alibabacloud_ververica20220718.models import GetDeployDeploymentDraftResultHeaders

    client = get_client(args.region_id)
    headers = GetDeployDeploymentDraftResultHeaders(workspace=args.workspace)
    ns = args.namespace
    result = call_api(
        "get_deploy_result",
        client.get_deploy_deployment_draft_result_with_options,
        ns, args.ticket_id, headers, runtime_options(),
    )
    output(result, args.output)


# ═══════════════════════════════════════════════════════════════════════════
# Subparser registration
# ═══════════════════════════════════════════════════════════════════════════


def register(subparsers):
    """Register all W1 subcommands."""

    def _add(name, help_text, func, extra_args=None):
        p = subparsers.add_parser(name, help=help_text)
        add_common_args(p)
        if extra_args:
            extra_args(p)
        p.set_defaults(func=func, subcommand=name)

    # ── Folders ────────────────────────────────────────────────────────

    def _folder_create(p):
        p.add_argument("--folder_name", required=True, help="Folder name")
        p.add_argument("--parent_id", help="Parent folder ID")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _folder_id(p):
        p.add_argument("--folder_id", required=True, help="Folder ID")

    def _folder_update(p):
        p.add_argument("--folder_id", required=True, help="Folder ID")
        p.add_argument("--folder_name", help="New folder name")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _folder_delete(p):
        p.add_argument("--folder_id", required=True, help="Folder ID")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    _add("create_folder", "Create a folder for organizing drafts", cmd_create_folder, _folder_create)
    _add("update_folder", "Update folder information", cmd_update_folder, _folder_update)
    _add("delete_folder", "Delete an empty folder", cmd_delete_folder, _folder_delete)
    _add("get_folder", "Get folder details", cmd_get_folder, _folder_id)

    # ── Drafts ─────────────────────────────────────────────────────────

    def _draft_create(p):
        p.add_argument("--name", help="Draft name")
        p.add_argument("--content", help="SQL content")
        p.add_argument(
            "--sql",
            dest="content",
            help="Alias of --content for SQL content (backward compatibility)",
        )
        p.add_argument("--folder_id", help="Parent folder ID")
        p.add_argument("--execution_mode", default="STREAMING", help="Execution mode: STREAMING or BATCH (default: STREAMING)")
        p.add_argument("--engine_version", help="Engine version (e.g. vvr-8.0.11-flink-1.17)")
        p.add_argument("--body_json", help="Full draft body as JSON (advanced)")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _draft_update(p):
        p.add_argument("--draft_id", required=True, help="Draft ID")
        p.add_argument("--content", help="Updated SQL content")
        p.add_argument("--body_json", help="Full draft body as JSON (advanced)")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _draft_id(p):
        p.add_argument("--draft_id", required=True, help="Draft ID")

    def _draft_delete(p):
        p.add_argument("--draft_id", required=True, help="Draft ID")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    def _draft_list(p):
        p.add_argument("--page_size", help="Page size")
        p.add_argument("--page_index", help="Page index")

    _add("create_draft", "Create a SQL deployment draft", cmd_create_draft, _draft_create)
    _add("update_draft", "Update a SQL deployment draft", cmd_update_draft, _draft_update)
    _add("delete_draft", "Delete a SQL deployment draft", cmd_delete_draft, _draft_delete)
    _add("get_draft", "Get draft details", cmd_get_draft, _draft_id)
    _add("list_drafts", "List all drafts", cmd_list_drafts, _draft_list)
    _add("get_draft_lock", "Get draft edit lock status", cmd_get_draft_lock, _draft_id)

    # ── Validation & Deploy ────────────────────────────────────────────

    def _validate_draft(p):
        p.add_argument("--draft_id", required=True, help="Draft ID to validate")
        p.add_argument("--deployment_target", help="Deployment target name for validation")

    def _ticket(p):
        p.add_argument("--ticket_id", required=True, help="Async ticket ID")

    def _validate_sql(p):
        p.add_argument("--statement", help="SQL statement to validate")
        p.add_argument(
            "--sql",
            dest="statement",
            help="Alias of --statement (backward compatibility)",
        )

    def _deploy_draft(p):
        p.add_argument("--draft_id", required=True, help="Draft ID to deploy")
        p.add_argument("--deployment_target", help="Deployment target name")
        p.add_argument("--deployment_target_mode", help="Deployment target mode (default PER_JOB)")
        p.add_argument("--confirm", action="store_true", help="Skip interactive confirmation")

    _add("validate_draft", "Deep-validate a draft (async)", cmd_validate_draft, _validate_draft)
    _add("get_validate_result", "Get validation result by ticket ID", cmd_get_validate_result, _ticket)
    _add("validate_sql", "Quick-validate SQL syntax", cmd_validate_sql, _validate_sql)
    _add("deploy_draft", "Deploy a draft to production (async)", cmd_deploy_draft, _deploy_draft)
    _add("get_deploy_result", "Get deploy result by ticket ID", cmd_get_deploy_result, _ticket)
