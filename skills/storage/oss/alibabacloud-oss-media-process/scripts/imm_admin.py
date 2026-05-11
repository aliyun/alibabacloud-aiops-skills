#!/usr/bin/env python3
"""Alibaba Cloud IMM Administration Script.

Manages IMM (Intelligent Media Management) resources required by
image-intelligent operations such as blind watermark extraction and AI detection.

Subcommands:
    auto-setup      Auto-check/create IMM project and bind bucket (one command)
    create-project  Create an IMM project and auto-bind bucket
    list-projects   List IMM projects
    get-project     Get IMM project details
    check-imm       Check IMM project and bucket binding status
    delete-project  Delete an IMM project
    bind-bucket     Bind an OSS bucket to an IMM project
    unbind-bucket   Unbind an OSS bucket from an IMM project

Environment Variables / Aliyun CLI:
    Credentials auto-discovered via alibabacloud-credentials SDK
    (Supports ~/.aliyun/config.json, environment variables, ECS metadata).
    ALIBABA_CLOUD_OSS_BUCKET         Default OSS bucket name
    ALIBABA_CLOUD_OSS_REGION         Default OSS region (e.g., cn-hangzhou)
    ALIBABA_CLOUD_IMM_PROJECT        IMM project name
"""

import argparse
import json
import os
import sys

from errors import die as _die

# Ensure sibling modules (load_env, imm_client, etc.) are importable
# regardless of the working directory when invoked via absolute path.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)


def _get_imm_client(region: str):
    """Create and return an IMM client. Delegates to shared imm_client module."""
    from imm_client import get_imm_client
    return get_imm_client(region)


# ---------------------------------------------------------------------------
# Subcommand handlers
# ---------------------------------------------------------------------------


def cmd_create_project(args) -> None:
    """Create an IMM project and auto-bind bucket."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)
    request = models.CreateProjectRequest(project_name=args.project)
    response = client.create_project(request)

    result = {
        "success": True,
        "action": "create_project",
        "project": args.project,
    }
    if hasattr(response.body, "project") and response.body.project:
        proj = response.body.project
        result["details"] = {
            "project_name": getattr(proj, "project_name", None),
            "create_time": getattr(proj, "create_time", None),
            "service_role": getattr(proj, "service_role", None),
        }

    # Auto-bind bucket to the newly created project
    bind_request = models.AttachOSSBucketRequest(
        project_name=args.project,
        ossbucket=args.bucket,
    )
    client.attach_ossbucket(bind_request)
    result["auto_bind"] = {
        "bucket": args.bucket,
        "status": "bound",
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_list_projects(args) -> None:
    """List all IMM projects."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)
    request = models.ListProjectsRequest()
    if args.max_results:
        request.max_results = args.max_results

    response = client.list_projects(request)

    projects = []
    if hasattr(response.body, "projects") and response.body.projects:
        for proj in response.body.projects:
            projects.append({
                "project_name": getattr(proj, "project_name", None),
                "create_time": getattr(proj, "create_time", None),
            })

    result = {
        "success": True,
        "action": "list_projects",
        "count": len(projects),
        "projects": projects,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_get_project(args) -> None:
    """Get details of an IMM project."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)
    request = models.GetProjectRequest(project_name=args.project)
    response = client.get_project(request)

    details = {}
    if hasattr(response.body, "project") and response.body.project:
        proj = response.body.project
        details = {
            "project_name": getattr(proj, "project_name", None),
            "create_time": getattr(proj, "create_time", None),
            "service_role": getattr(proj, "service_role", None),
            "dataset_count": getattr(proj, "dataset_count", None),
        }

    result = {
        "success": True,
        "action": "get_project",
        "project": args.project,
        "details": details,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_check_imm(args) -> None:
    """Check IMM setup status: project existence and bucket binding."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)
    project_name = args.project
    bucket = args.bucket

    result = {
        "success": True,
        "action": "check_imm",
        "region": args.region,
        "project": project_name,
        "bucket": bucket,
        "checks": {},
    }

    # Check 1: Project exists
    try:
        get_request = models.GetProjectRequest(project_name=project_name)
        get_response = client.get_project(get_request)
        proj = getattr(get_response.body, "project", None)
        if proj:
            result["checks"]["project_exists"] = {
                "status": "pass",
                "project_name": getattr(proj, "project_name", project_name),
                "create_time": getattr(proj, "create_time", None),
                "service_role": getattr(proj, "service_role", None),
            }
        else:
            result["checks"]["project_exists"] = {
                "status": "fail",
                "message": f"Project '{project_name}' not found.",
            }
            result["success"] = False
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return
    except Exception as exc:
        result["checks"]["project_exists"] = {
            "status": "fail",
            "message": str(exc),
        }
        result["success"] = False
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Check 2: Bucket binding (query by bucket only, same approach as auto-setup)
    try:
        attach_request = models.GetOSSBucketAttachmentRequest()
        attach_request.ossbucket = bucket
        resp = client.get_ossbucket_attachment(attach_request)
        bound_project = None
        if resp.body:
            body_map = resp.body.to_map() if hasattr(resp.body, "to_map") else {}
            bound_project = (
                body_map.get("ProjectName")
                or body_map.get("project_name")
            )
        if bound_project:
            bound_match = bound_project == project_name
            result["checks"]["bucket_bound"] = {
                "status": "pass" if bound_match else "warn",
                "bucket": bucket,
                "bound_to": bound_project,
            }
            if not bound_match:
                result["checks"]["bucket_bound"]["message"] = (
                    f"Bucket is bound to '{bound_project}', not '{project_name}'."
                )
        else:
            result["checks"]["bucket_bound"] = {
                "status": "fail",
                "bucket": bucket,
                "message": f"Bucket '{bucket}' is not bound to any IMM project.",
                "hint": f"Run: python imm_admin.py bind-bucket --project {project_name} --bucket {bucket} --region {args.region}",
            }
            result["success"] = False
    except Exception as exc:
        err_msg = str(exc)
        if any(kw in err_msg for kw in ("NotAttached", "NotFound", "404")):
            result["checks"]["bucket_bound"] = {
                "status": "fail",
                "bucket": bucket,
                "message": f"Bucket '{bucket}' is not bound to any IMM project.",
                "hint": f"Run: python imm_admin.py bind-bucket --project {project_name} --bucket {bucket} --region {args.region}",
            }
        else:
            result["checks"]["bucket_bound"] = {
                "status": "fail",
                "bucket": bucket,
                "message": f"Binding check error: {err_msg}",
            }
        result["success"] = False

    # Summary
    pass_count = sum(1 for c in result["checks"].values() if c["status"] == "pass")
    total_count = len(result["checks"])
    result["summary"] = f"{pass_count}/{total_count} checks passed"

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_delete_project(args) -> None:
    """Delete an IMM project with protective pre-check."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)

    # Protective pre-check: verify project exists and check for bound buckets
    try:
        get_request = models.GetProjectRequest(project_name=args.project)
        get_response = client.get_project(get_request)
        proj = getattr(get_response.body, "project", None)
        if proj:
            dataset_count = getattr(proj, "dataset_count", 0)
            if dataset_count and dataset_count > 0:
                _die(
                    f"Project '{args.project}' still has {dataset_count} "
                    f"dataset(s) bound. Unbind all buckets before deleting.",
                    "Use 'unbind-bucket' to remove bucket bindings first."
                )
    except Exception as exc:
        print(
            json.dumps({"status": "warning", "message":
                        f"Pre-check skipped: {exc}"}),
            file=sys.stderr,
        )

    request = models.DeleteProjectRequest(project_name=args.project)
    client.delete_project(request)

    result = {
        "success": True,
        "action": "delete_project",
        "project": args.project,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_bind_bucket(args) -> None:
    """Bind an OSS bucket to an IMM project."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)
    request = models.AttachOSSBucketRequest(
        project_name=args.project,
        ossbucket=args.bucket,
    )
    client.attach_ossbucket(request)

    result = {
        "success": True,
        "action": "bind_bucket",
        "project": args.project,
        "bucket": args.bucket,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_unbind_bucket(args) -> None:
    """Unbind an OSS bucket from an IMM project."""
    from alibabacloud_imm20200930 import models

    client = _get_imm_client(args.region)
    request = models.DetachOSSBucketRequest(
        project_name=args.project,
        ossbucket=args.bucket,
    )
    client.detach_ossbucket(request)

    result = {
        "success": True,
        "action": "unbind_bucket",
        "project": args.project,
        "bucket": args.bucket,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_auto_setup(args) -> None:
    """Auto-setup IMM: check bucket, check/create project, bind bucket.

    Workflow:
      1. Verify OSS bucket exists and is accessible.
      2. Query whether the bucket is already bound to an IMM project.
      3. If bound, reuse the existing project.
      4. If not bound, create a new project (name auto-generated) and bind it.
      5. Output the resolved project name for downstream use.
    """
    import datetime
    import random

    from alibabacloud_imm20200930 import models
    try:
        import oss2
    except ImportError:
        _die("oss2 SDK not installed.", "pip install oss2==2.19.1")

    client = _get_imm_client(args.region)
    bucket_name = args.bucket
    region = args.region

    result = {
        "success": False,
        "action": "auto_setup",
        "region": region,
        "bucket": bucket_name,
        "steps": [],
    }

    # Step 1: Verify OSS bucket exists
    try:
        from credential import USER_AGENT, get_oss_credentials_provider
        credentials_provider = get_oss_credentials_provider()
        endpoint = "https://oss-{}.aliyuncs.com".format(region)
        auth = oss2.ProviderAuth(credentials_provider)
        bucket_obj = oss2.Bucket(
            auth, endpoint, bucket_name,
            connect_timeout=(30, 60),
            app_name=USER_AGENT,
        )
        info = bucket_obj.get_bucket_info()
        result["steps"].append({
            "step": "check_bucket",
            "status": "pass",
            "message": "Bucket '{}' exists (created: {})".format(
                bucket_name, info.creation_date),
        })
    except Exception as e:
        result["steps"].append({
            "step": "check_bucket",
            "status": "fail",
            "message": "Bucket '{}' not accessible: {}".format(bucket_name, e),
        })
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Step 2: Query existing IMM binding for this bucket
    existing_project = None
    try:
        req = models.GetOSSBucketAttachmentRequest()
        req.ossbucket = bucket_name
        resp = client.get_ossbucket_attachment(req)
        if resp.body:
            body_map = resp.body.to_map() if hasattr(resp.body, "to_map") else {}
            existing_project = (
                body_map.get("ProjectName")
                or body_map.get("project_name")
            )
    except Exception as e:
        err_msg = e.message if hasattr(e, "message") else str(e)
        # Not attached is expected — continue to create
        if not any(kw in err_msg for kw in ("NotAttached", "NotFound", "404")):
            # Unexpected error — still try to continue
            result["steps"].append({
                "step": "query_binding",
                "status": "warn",
                "message": "Query binding returned unexpected error: {}".format(err_msg),
            })

    if existing_project:
        result["steps"].append({
            "step": "query_binding",
            "status": "pass",
            "message": "Bucket already bound to project '{}'".format(existing_project),
        })
        result["success"] = True
        result["project_name"] = existing_project
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    result["steps"].append({
        "step": "query_binding",
        "status": "info",
        "message": "Bucket is not bound to any IMM project. Will create one.",
    })

    # Step 3: Create a new IMM project
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    safe_name = "".join(c for c in bucket_name if c.isalnum() or c == "-")[:20]
    if not safe_name:
        safe_name = "".join(
            random.choice("abcdefghijklmnopqrstuvwxyz0123456789")
            for _ in range(6)
        )
    new_project_name = "imm-auto-{}-{}".format(safe_name, date_str)

    created_project = None
    try:
        create_req = models.CreateProjectRequest(project_name=new_project_name)
        resp = client.create_project(create_req)
        if resp.body:
            body_map = resp.body.to_map() if hasattr(resp.body, "to_map") else {}
            created_project = (
                body_map.get("ProjectName")
                or body_map.get("projectName")
                or body_map.get("Name")
                or new_project_name
            )
        else:
            created_project = new_project_name
        result["steps"].append({
            "step": "create_project",
            "status": "pass",
            "message": "Project '{}' created".format(created_project),
        })
    except Exception as e:
        err_msg = e.message if hasattr(e, "message") else str(e)
        if "AlreadyExists" in err_msg:
            # Retry with a random suffix
            new_project_name += "-{}".format(random.randint(1000, 9999))
            try:
                create_req = models.CreateProjectRequest(project_name=new_project_name)
                resp = client.create_project(create_req)
                created_project = new_project_name
                result["steps"].append({
                    "step": "create_project",
                    "status": "pass",
                    "message": "Project '{}' created (retry with suffix)".format(created_project),
                })
            except Exception as e2:
                err2 = e2.message if hasattr(e2, "message") else str(e2)
                result["steps"].append({
                    "step": "create_project",
                    "status": "fail",
                    "message": "Failed to create project: {}".format(err2),
                })
                print(json.dumps(result, ensure_ascii=False, indent=2))
                return
        else:
            result["steps"].append({
                "step": "create_project",
                "status": "fail",
                "message": "Failed to create project: {}".format(err_msg),
            })
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    # Step 4: Bind bucket to the new project
    try:
        attach_req = models.AttachOSSBucketRequest(
            project_name=created_project,
            ossbucket=bucket_name,
        )
        client.attach_ossbucket(attach_req)
        result["steps"].append({
            "step": "bind_bucket",
            "status": "pass",
            "message": "Bucket '{}' bound to project '{}'".format(
                bucket_name, created_project),
        })
    except Exception as e:
        err_msg = e.message if hasattr(e, "message") else str(e)
        if "already" in err_msg.lower() or "Attached" in err_msg:
            result["steps"].append({
                "step": "bind_bucket",
                "status": "pass",
                "message": "Binding already exists",
            })
        else:
            result["steps"].append({
                "step": "bind_bucket",
                "status": "fail",
                "message": "Failed to bind bucket: {}".format(err_msg),
            })
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return

    result["success"] = True
    result["project_name"] = created_project
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage Alibaba Cloud IMM resources for image-intelligent operations.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Auto-setup: check/create IMM project and bind bucket\n"
            "  python imm_admin.py auto-setup --bucket my-bucket --region cn-hangzhou\n\n"
            "  # Create an IMM project (auto-binds bucket)\n"
            "  python imm_admin.py create-project --project my-project "
            "--bucket my-bucket --region cn-hangzhou\n\n"
            "  # List all projects\n"
            "  python imm_admin.py list-projects --region cn-hangzhou\n\n"
            "  # Check IMM project and bucket binding status\n"
            "  python imm_admin.py check-imm\n\n"
            "  # Bind a bucket to a project\n"
            "  python imm_admin.py bind-bucket --project my-project "
            "--bucket my-bucket --region cn-hangzhou\n\n"
            "  # Unbind a bucket\n"
            "  python imm_admin.py unbind-bucket --project my-project "
            "--bucket my-bucket --region cn-hangzhou\n\n"
            "  # Delete a project\n"
            "  python imm_admin.py delete-project --project my-project --region cn-hangzhou\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    subparsers.required = True

    _region_help = (
        "Region (e.g., cn-hangzhou). "
        "Falls back to ALIBABA_CLOUD_OSS_REGION environment variable."
    )
    _region_default = os.environ.get("ALIBABA_CLOUD_OSS_REGION")

    _bucket_help = (
        "OSS bucket name. "
        "Falls back to ALIBABA_CLOUD_OSS_BUCKET environment variable."
    )
    _bucket_default = os.environ.get("ALIBABA_CLOUD_OSS_BUCKET")

    # create-project
    p_create = subparsers.add_parser(
        "create-project",
        help="Create an IMM project and auto-bind bucket.",
    )
    p_create.add_argument("--project", required=True, help="IMM project name.")
    p_create.add_argument(
        "--bucket", default=_bucket_default, help=_bucket_help,
    )
    p_create.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_create.set_defaults(func=cmd_create_project)

    # list-projects
    p_list = subparsers.add_parser(
        "list-projects", help="List all IMM projects.",
    )
    p_list.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_list.add_argument(
        "--max-results", type=int, default=100,
        help="Maximum number of results to return (default: 100).",
    )
    p_list.set_defaults(func=cmd_list_projects)

    # get-project
    p_get = subparsers.add_parser(
        "get-project", help="Get details of an IMM project.",
    )
    p_get.add_argument("--project", required=True, help="IMM project name.")
    p_get.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_get.set_defaults(func=cmd_get_project)

    # check-imm
    p_check = subparsers.add_parser(
        "check-imm", help="Check IMM project and bucket binding status.",
    )
    p_check.add_argument(
        "--project", default=os.environ.get("ALIBABA_CLOUD_IMM_PROJECT"),
        help="IMM project name. Falls back to ALIBABA_CLOUD_IMM_PROJECT env var.",
    )
    p_check.add_argument(
        "--bucket", default=_bucket_default, help=_bucket_help,
    )
    p_check.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_check.set_defaults(func=cmd_check_imm)

    # delete-project
    p_delete = subparsers.add_parser(
        "delete-project", help="Delete an IMM project.",
    )
    p_delete.add_argument("--project", required=True, help="IMM project name.")
    p_delete.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_delete.set_defaults(func=cmd_delete_project)

    # bind-bucket
    p_bind = subparsers.add_parser(
        "bind-bucket", help="Bind an OSS bucket to an IMM project.",
    )
    p_bind.add_argument("--project", required=True, help="IMM project name.")
    p_bind.add_argument(
        "--bucket", default=_bucket_default, help=_bucket_help,
    )
    p_bind.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_bind.set_defaults(func=cmd_bind_bucket)

    # unbind-bucket
    p_unbind = subparsers.add_parser(
        "unbind-bucket", help="Unbind an OSS bucket from an IMM project.",
    )
    p_unbind.add_argument("--project", required=True, help="IMM project name.")
    p_unbind.add_argument(
        "--bucket", default=_bucket_default, help=_bucket_help,
    )
    p_unbind.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_unbind.set_defaults(func=cmd_unbind_bucket)

    # auto-setup
    p_auto = subparsers.add_parser(
        "auto-setup",
        help="Auto-setup IMM: check bucket, check/create project, bind bucket.",
    )
    p_auto.add_argument(
        "--bucket", default=_bucket_default, help=_bucket_help,
    )
    p_auto.add_argument(
        "--region", default=_region_default, help=_region_help,
    )
    p_auto.set_defaults(func=cmd_auto_setup)

    return parser


def main() -> None:
    # Load environment variables from config files (does not override existing)
    from load_env import ensure_env_loaded
    ensure_env_loaded(verbose=False)

    parser = build_parser()
    args = parser.parse_args()

    # Validate region (required for all subcommands)
    if not args.region:
        _die(
            "Region is required. Use --region or set "
            "ALIBABA_CLOUD_OSS_REGION environment variable.",
            "Example: --region cn-hangzhou or "
            "export ALIBABA_CLOUD_OSS_REGION='cn-hangzhou'",
        )

    # Validate bucket for subcommands that require it
    if args.command in ("create-project", "bind-bucket", "unbind-bucket", "check-imm", "auto-setup"):
        if not getattr(args, "bucket", None):
            _die(
                "Bucket name is required. Use --bucket or set "
                "ALIBABA_CLOUD_OSS_BUCKET environment variable.",
                "Example: --bucket my-bucket or "
                "export ALIBABA_CLOUD_OSS_BUCKET='my-bucket'",
            )

    # Validate project for check-imm
    if args.command == "check-imm":
        if not getattr(args, "project", None):
            _die(
                "IMM project name is required. Use --project or set "
                "ALIBABA_CLOUD_IMM_PROJECT environment variable.",
                "Example: --project my-imm-project or "
                "export ALIBABA_CLOUD_IMM_PROJECT='my-imm-project'",
            )

    args.func(args)


if __name__ == "__main__":
    main()
