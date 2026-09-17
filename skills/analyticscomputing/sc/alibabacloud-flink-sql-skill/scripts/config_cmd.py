#!/usr/bin/env python3
"""Initialize and validate configuration for the unified Flink SQL lifecycle CLI."""

import json
import os
import shutil
import tempfile

from client import (
    add_common_args,
    build_user_agent,
    error_response,
    load_scope_config,
    output,
    require_args,
    scope_config_path,
    success_response,
)
from git_sync import (
    DEFAULT_GIT_BRANCH,
    DEFAULT_GIT_LOCAL_PATH,
    git_config_summary,
    parse_git_settings,
)


def cmd_config_init(args):
    """Store one non-sensitive Workspace scope and optional Git configuration locally."""
    error = require_args(args, "workspace", "namespace", "region_id")
    if error:
        return output(error, args.output)

    path = scope_config_path()
    existed = path.exists()
    if existed and not args.overwrite:
        result = error_response(
            "config_init",
            "ConfigurationExists",
            f"Configuration file already exists: {path}. Add --overwrite to replace the configured scope.",
        )
        result["data"] = {"config_path": str(path), "overwritten": False}
        return output(result, args.output)

    scope = {
        "region_id": args.region_id.strip(),
        "workspace": args.workspace.strip(),
        "namespace": args.namespace.strip(),
    }
    stored_config = dict(scope)
    git_repo_url = (getattr(args, "git_repo_url", None) or "").strip()
    git_local_path = (getattr(args, "git_local_path", None) or "").strip()
    git_branch = (getattr(args, "git_branch", None) or "").strip()
    if (git_local_path or git_branch) and not git_repo_url:
        result = error_response(
            "config_init",
            "GitConfigurationError",
            "A Git repository URL is required when a local path or branch is provided.",
        )
        result["data"] = {"config_path": str(path), "overwritten": False}
        return output(result, args.output)

    git_summary = {"enabled": False}
    if git_repo_url:
        candidate = {
            "git": {
                "repo_url": git_repo_url,
                "local_path": git_local_path or DEFAULT_GIT_LOCAL_PATH,
                "branch": git_branch or DEFAULT_GIT_BRANCH,
            }
        }
        git_settings, git_error, _ = parse_git_settings(candidate, path)
        if git_error or git_settings is None:
            result = error_response(
                "config_init",
                "GitConfigurationError",
                git_error or "Invalid Git configuration",
            )
            result["data"] = {"config_path": str(path), "overwritten": False}
            return output(result, args.output)
        stored_config["git"] = git_settings
        git_summary = {
            "enabled": True,
            "local_path": git_settings["local_path"],
            "branch": git_settings["branch"],
        }
    temporary_path = ""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(stored_config, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        os.chmod(temporary_path, 0o600)
        os.replace(temporary_path, path)
    except OSError as exc:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
        result = error_response(
            "config_init", "ConfigurationWriteError", f"Unable to write the configuration file: {exc}"
        )
        result["data"] = {"config_path": str(path), "overwritten": False}
        return output(result, args.output)

    return output(
        success_response(
            "config_init",
            {
                "config_path": str(path),
                "scope": scope,
                "git_sync": git_summary,
                "overwritten": existed,
                "credentials_stored": False,
                "flink_api_request_performed": False,
            },
        ),
        args.output,
    )


def _credential_check():
    try:
        from alibabacloud_credentials.client import Client as CredentialClient
    except ImportError:
        return False, "", "Credential SDK import failed; install assets/requirements.txt with the same Python interpreter"

    try:
        provider = CredentialClient()
        credential = provider.get_credential()
        credential_type = getattr(credential, "type", "") or provider.get_type() or "default-chain"
        has_access_key = bool(getattr(credential, "access_key_id", None))
        has_bearer_token = bool(getattr(credential, "bearer_token", None))
        if not has_access_key and not has_bearer_token:
            return False, credential_type, "No usable credentials were resolved"
        return True, credential_type, ""
    except Exception:
        return False, "", "The default credential chain could not resolve credentials"


def cmd_config_doctor(args):
    """Validate the local scope and credential discovery without calling the Flink API."""
    build_user_agent()
    scope = {
        "workspace": getattr(args, "workspace", None),
        "namespace": getattr(args, "namespace", None),
        "region_id": getattr(args, "region_id", None),
    }
    missing = [name for name, value in scope.items() if not value]
    config_error = getattr(args, "_scope_config_error", "")
    credential_ok, credential_type, credential_error = _credential_check()
    stored_config, config_path, stored_config_error = load_scope_config()
    git_summary, git_error = git_config_summary(stored_config, config_path)

    data = {
        "config_path": getattr(args, "_scope_config_path", ""),
        "scope": scope,
        "scope_sources": getattr(args, "_scope_sources", {}),
        "credential": {
            "resolved": credential_ok,
            "type": credential_type,
        },
        "git_sync": git_summary,
        "flink_api_request_performed": False,
        "credential_provider_may_refresh_oauth": True,
    }

    problems = []
    if config_error:
        problems.append(config_error)
    elif stored_config_error:
        problems.append(stored_config_error)
    if missing:
        problems.append(
            "Missing scope fields: "
            + ", ".join(missing)
            + "; use config_init to store the complete scope first"
        )
    if not credential_ok:
        problems.append("The Alibaba Cloud credential chain is unavailable: " + credential_error)
    if git_error:
        problems.append("Invalid Git synchronization configuration: " + git_error)
    elif git_summary.get("enabled") and shutil.which("git") is None:
        problems.append("Git synchronization is enabled, but the git executable was not found")

    if problems:
        result = error_response("config_doctor", "ConfigurationError", "; ".join(problems))
        result["data"] = data
        return output(result, args.output)

    return output(success_response("config_doctor", data), args.output)


def register(subparsers):
    init_parser = subparsers.add_parser(
        "config_init",
        help="Store one Workspace scope and optional Git synchronization configuration",
    )
    add_common_args(init_parser)
    init_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace the existing local scope configuration",
    )
    init_parser.add_argument(
        "--git-repo-url",
        "--git_repo_url",
        dest="git_repo_url",
        help="Optional remote Git repository URL; enables automatic synchronization",
    )
    init_parser.add_argument(
        "--git-local-path",
        "--git_local_path",
        dest="git_local_path",
        help=f"Local Git clone path (default: {DEFAULT_GIT_LOCAL_PATH})",
    )
    init_parser.add_argument(
        "--git-branch",
        "--git_branch",
        dest="git_branch",
        help=f"Git synchronization branch (default: {DEFAULT_GIT_BRANCH})",
    )
    init_parser.set_defaults(func=cmd_config_init, subcommand="config_init")

    parser = subparsers.add_parser(
        "config_doctor",
        help="Validate scope, credential discovery, and Git configuration without calling the Flink resource API",
    )
    add_common_args(parser)
    parser.set_defaults(func=cmd_config_doctor, subcommand="config_doctor")
