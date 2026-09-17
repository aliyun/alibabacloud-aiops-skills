#!/usr/bin/env python3
"""Git synchronization for Deployment SQL, Flink configuration, and resource configuration."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

from client import (
    add_common_args,
    call_api,
    error_response,
    get_client,
    load_scope_config,
    output,
    require_args,
    require_confirmation,
    runtime_options,
    success_response,
)


DEFAULT_GIT_LOCAL_PATH = "/tmp/vvr-sql-sync"
DEFAULT_GIT_BRANCH = "main"
DEPLOYMENTS_DIRECTORY = "deployments"


class GitSyncError(RuntimeError):
    """Git synchronization could not complete safely."""


def _string(value):
    return value.strip() if isinstance(value, str) else ""


def _valid_branch(branch):
    if not branch or branch.startswith("-") or branch.endswith(("/", ".")):
        return False
    if branch in (".", "..") or ".." in branch or "@{" in branch or "//" in branch:
        return False
    return not bool(re.search(r"[\x00-\x20~^:?*\\\[]", branch))


def _normalize_local_path(value, config_path):
    path = Path(value or DEFAULT_GIT_LOCAL_PATH).expanduser()
    if not path.is_absolute():
        path = config_path.parent / path
    return path.resolve()


def parse_git_settings(config, config_path):
    """Parse optional Git configuration and return ``(settings, error, configured)``."""
    if "git" not in config:
        return None, "", False

    raw = config.get("git")
    if not isinstance(raw, dict):
        return None, "git configuration must be a JSON object", True

    repo_url = _string(raw.get("repo_url"))
    local_value = _string(raw.get("local_path")) or DEFAULT_GIT_LOCAL_PATH
    branch = _string(raw.get("branch")) or DEFAULT_GIT_BRANCH

    if not repo_url:
        return None, "git.repo_url must not be empty", True
    if repo_url.startswith("-"):
        return None, "The Git repository URL must not start with '-'", True

    parsed_url = urlsplit(repo_url)
    if parsed_url.scheme.lower() == "ext":
        return None, "The Git ext remote protocol is not supported", True
    if parsed_url.scheme in ("http", "https") and (
        parsed_url.username or parsed_url.password
    ):
        return None, "A Git HTTP(S) URL must not embed a username, token, or password", True

    if not _valid_branch(branch):
        return None, f"Invalid Git branch name: {branch}", True

    local_path = _normalize_local_path(local_value, config_path)
    if local_path == Path(local_path.anchor):
        return None, "The local Git path must not be the filesystem root", True

    return (
        {
            "repo_url": repo_url,
            "local_path": str(local_path),
            "branch": branch,
        },
        "",
        True,
    )


def load_git_settings():
    config, config_path, config_error = load_scope_config()
    if config_error:
        return None, config_error, "git" in config
    return parse_git_settings(config, config_path)


def git_sync_enabled():
    settings, error, configured = load_git_settings()
    return configured and not error and settings is not None


def git_config_summary(config, config_path):
    settings, error, configured = parse_git_settings(config, config_path)
    if not configured:
        return {"enabled": False}, ""
    if error:
        return {"enabled": False, "configured": True}, error
    return {
        "enabled": True,
        "local_path": settings["local_path"],
        "branch": settings["branch"],
    }, ""


def api_result_succeeded(result):
    if not isinstance(result, dict) or result.get("success") is not True:
        return False
    body = result.get("data")
    return not (isinstance(body, dict) and body.get("success") is False)


def api_result_data(result):
    if not isinstance(result, dict):
        return None
    body = result.get("data")
    if isinstance(body, dict) and "data" in body:
        return body.get("data")
    return body


def _api_error(result):
    if not isinstance(result, dict):
        return "Invalid platform response format"
    if result.get("success") is False:
        error = result.get("error") or {}
        return str(error.get("message") or error.get("code") or "Platform call failed")
    body = result.get("data")
    if isinstance(body, dict) and body.get("success") is False:
        return str(body.get("errorMessage") or body.get("errorCode") or "Platform call failed")
    return "Platform call result was not confirmed"


def api_result_error(result):
    return _api_error(result)


def _mapping(value):
    if isinstance(value, dict):
        return value
    if hasattr(value, "to_map"):
        mapped = value.to_map()
        return mapped if isinstance(mapped, dict) else {}
    return {}


def _get(mapping, *keys):
    mapping = _mapping(mapping)
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def deployment_name(deployment):
    data = _mapping(deployment)
    return _string(_get(data, "name", "deploymentName")) or _string(
        _get(data, "deploymentId", "deployment_id")
    )


def extract_sql(deployment):
    artifact = _get(deployment, "artifact")
    if _string(_get(artifact, "kind")).upper() != "SQLSCRIPT":
        return None
    sql_artifact = _get(artifact, "sqlArtifact", "sql_artifact")
    sql = _get(sql_artifact, "sqlScript", "sql_script")
    return sql if isinstance(sql, str) else None


def format_flink_conf(deployment):
    flink_conf = _get(deployment, "flinkConf", "flink_conf")
    if not isinstance(flink_conf, dict) or not flink_conf:
        return ""

    lines = []
    for key in sorted(flink_conf):
        value = flink_conf[key]
        if isinstance(value, (dict, list)):
            value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        elif isinstance(value, bool):
            value = str(value).lower()
        elif value is None:
            value = ""
        else:
            value = str(value)
        value = value.replace("\\", "\\\\").replace("\r", "\\r").replace("\n", "\\n")
        lines.append(f"{key}={value}")
    return "\n".join(lines) + "\n"


def _resource_spec(value):
    spec = _mapping(value)
    result = {}
    if _get(spec, "cpu") is not None:
        result["cpu"] = _get(spec, "cpu")
    if _get(spec, "memory") is not None:
        result["memory"] = _get(spec, "memory")
    return result


def _basic_resource_config(value, include_empty_specs=False):
    basic = _mapping(value)
    result = {}
    parallelism = _get(basic, "parallelism")
    if parallelism is not None:
        result["parallelism"] = parallelism
    job_manager = _resource_spec(
        _get(
            basic,
            "jobmanagerResourceSettingSpec",
            "jobManagerResourceSettingSpec",
            "jobmanager_resource_setting_spec",
        )
    )
    task_manager = _resource_spec(
        _get(
            basic,
            "taskmanagerResourceSettingSpec",
            "taskManagerResourceSettingSpec",
            "taskmanager_resource_setting_spec",
        )
    )
    if job_manager or include_empty_specs:
        result["jobManager"] = job_manager
    if task_manager or include_empty_specs:
        result["taskManager"] = task_manager
    return result


def format_resource_config(deployment):
    streaming_value = _get(
        deployment, "streamingResourceSetting", "streaming_resource_setting"
    )
    if streaming_value is not None:
        streaming = _mapping(streaming_value)
        mode = _string(
            _get(streaming, "resourceSettingMode", "resource_setting_mode")
        ).upper()
        basic = _get(streaming, "basicResourceSetting", "basic_resource_setting")
        expert_value = _get(
            streaming, "expertResourceSetting", "expert_resource_setting"
        )
        expert = _mapping(expert_value)
        if not mode:
            mode = "UNKNOWN"
        result = {"mode": mode}
        if mode == "EXPERT" and expert_value is not None:
            job_manager = _resource_spec(
                _get(
                    expert,
                    "jobmanagerResourceSettingSpec",
                    "jobManagerResourceSettingSpec",
                    "jobmanager_resource_setting_spec",
                )
            )
            result["jobManager"] = job_manager
            resource_plan = _get(expert, "resourcePlan", "resource_plan")
            if isinstance(resource_plan, str):
                try:
                    resource_plan = json.loads(resource_plan)
                except json.JSONDecodeError:
                    pass
            if resource_plan not in (None, ""):
                result["resourcePlan"] = resource_plan
        elif mode == "BASIC" and basic is not None:
            result.update(_basic_resource_config(basic, include_empty_specs=True))
        return result

    batch_value = _get(deployment, "batchResourceSetting", "batch_resource_setting")
    if batch_value is not None:
        batch = _mapping(batch_value)
        result = {"mode": "BATCH"}
        max_slot = _get(batch, "maxSlot", "max_slot")
        if max_slot is not None:
            result["maxSlot"] = max_slot
        result.update(
            _basic_resource_config(
                _get(batch, "basicResourceSetting", "basic_resource_setting")
            )
        )
        return result

    return None


def sanitize_file_name(name):
    safe = re.sub(r"[^a-zA-Z0-9_.-]", "_", _string(name))
    if safe in (".", ".."):
        safe = ""
    return safe or "unnamed-deployment"


class GitSyncService:
    def __init__(self, settings):
        self.repo_url = settings["repo_url"]
        self.local_path = Path(settings["local_path"]).expanduser().resolve()
        self.branch = settings["branch"]
        if not _valid_branch(self.branch):
            raise GitSyncError(f"Invalid Git branch name: {self.branch}")

    def _run(self, *arguments, cwd=None, check=True, timeout=120):
        environment = os.environ.copy()
        environment["GIT_TERMINAL_PROMPT"] = "0"
        try:
            result = subprocess.run(
                ["git", "-c", "core.hooksPath=/dev/null", *arguments],
                cwd=cwd,
                text=True,
                capture_output=True,
                timeout=timeout,
                env=environment,
            )
        except FileNotFoundError as exc:
            raise GitSyncError("The git executable was not found") from exc
        except subprocess.TimeoutExpired as exc:
            raise GitSyncError(f"The Git operation timed out after {timeout} seconds") from exc
        if check and result.returncode != 0:
            message = (result.stderr or result.stdout or "Git operation failed").strip()
            raise GitSyncError(message)
        return result

    def _git(self, *arguments, check=True):
        return self._run(*arguments, cwd=self.local_path, check=check)

    def _remote_branch_exists(self):
        return (
            self._git(
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/remotes/origin/{self.branch}",
                check=False,
            ).returncode
            == 0
        )

    def _local_branch_exists(self):
        return (
            self._git(
                "show-ref",
                "--verify",
                "--quiet",
                f"refs/heads/{self.branch}",
                check=False,
            ).returncode
            == 0
        )

    def _has_commit(self):
        return self._git("rev-parse", "--verify", "HEAD", check=False).returncode == 0

    def ensure_repo(self):
        if shutil.which("git") is None:
            raise GitSyncError("The git executable was not found")

        git_dir = self.local_path / ".git"
        if not git_dir.is_dir():
            if self.local_path.exists() and not self.local_path.is_dir():
                raise GitSyncError(
                    f"The local Git path exists and is not a directory: {self.local_path}"
                )
            if self.local_path.exists() and any(self.local_path.iterdir()):
                raise GitSyncError(
                    f"The local Git path exists and is not empty: {self.local_path}"
                )
            self.local_path.parent.mkdir(parents=True, exist_ok=True)
            self._run("clone", self.repo_url, str(self.local_path), cwd=self.local_path.parent)

        remote = self._git("remote", "get-url", "origin").stdout.strip()
        if remote != self.repo_url:
            raise GitSyncError(
                f"The local repository origin does not match the configuration: {self.local_path}"
            )

        if self._git("status", "--porcelain").stdout.strip():
            raise GitSyncError(
                f"The local Git repository has uncommitted changes; resolve them first: {self.local_path}"
            )

        self._git("fetch", "origin")
        remote_branch = self._remote_branch_exists()
        local_branch = self._local_branch_exists()
        current = self._git("branch", "--show-current", check=False).stdout.strip()

        if current != self.branch:
            if local_branch:
                self._git("checkout", self.branch)
            elif remote_branch:
                self._git("checkout", "-b", self.branch, "--track", f"origin/{self.branch}")
            else:
                self._git("checkout", "-b", self.branch)

        if remote_branch and self._has_commit():
            self._git("pull", "--rebase", "origin", self.branch)
        return {
            "enabled": True,
            "success": True,
            "local_path": str(self.local_path),
            "branch": self.branch,
        }

    def _deployment_directory(self, name):
        root = self.local_path / DEPLOYMENTS_DIRECTORY
        if root.exists() and root.is_symlink():
            raise GitSyncError("The Git deployments directory must not be a symbolic link")
        root.mkdir(parents=True, exist_ok=True)
        target = root / sanitize_file_name(name)
        if target.exists() and target.is_symlink():
            raise GitSyncError("A Deployment synchronization directory must not be a symbolic link")
        if target.resolve().parent != root.resolve():
            raise GitSyncError("The Deployment name resolves outside the Git repository")
        return target

    def _write_deployment(self, deployment):
        name = deployment_name(deployment)
        if not name:
            raise GitSyncError("The Deployment response contains neither a name nor an ID")
        target = self._deployment_directory(name)
        target.mkdir(parents=True, exist_ok=True)

        files = {"flink-conf.properties": format_flink_conf(deployment)}
        sql = extract_sql(deployment)
        if sql is not None:
            files["job.sql"] = sql
        resource_config = format_resource_config(deployment)
        if resource_config is not None:
            files["resource-config.json"] = (
                json.dumps(
                    resource_config,
                    ensure_ascii=False,
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
        for filename, content in files.items():
            path = target / filename
            if path.is_symlink():
                raise GitSyncError(f"A Git synchronization artifact must not be a symbolic link: {path}")
            path.write_text(content, encoding="utf-8")
        return name, target

    def _commit_and_push(self, message):
        self._git("commit", "-m", message)
        commit = self._git("rev-parse", "HEAD").stdout.strip()
        self._git("push", "-u", "origin", self.branch)
        return commit

    def _push_pending_commit(self):
        if not self._has_commit():
            return False
        remote_branch = self._remote_branch_exists()
        if not remote_branch:
            self._git("push", "-u", "origin", self.branch)
            return True
        counts = self._git(
            "rev-list", "--left-right", "--count", f"origin/{self.branch}...{self.branch}"
        ).stdout.split()
        ahead = int(counts[1]) if len(counts) == 2 else 0
        if ahead:
            self._git("push", "-u", "origin", self.branch)
            return True
        return False

    def sync_deployment(self, deployment, action):
        name_hint = deployment_name(deployment)
        if not name_hint:
            raise GitSyncError("The Deployment response contains neither a name nor an ID")
        self.ensure_repo()
        target_hint = self._deployment_directory(name_hint)
        tracked = (
            self._git(
                "ls-files",
                "--error-unmatch",
                str((target_hint / "job.sql").relative_to(self.local_path)),
                check=False,
            ).returncode
            == 0
        )
        if action == "deploy":
            action = "update" if tracked else "create"
        name, target = self._write_deployment(deployment)
        relative = target.relative_to(self.local_path)
        self._git("add", "--", str(relative))
        changed = self._git("diff", "--cached", "--quiet", check=False).returncode == 1
        if not changed:
            pushed = self._push_pending_commit()
            return {
                "enabled": True,
                "success": True,
                "action": action,
                "deployment": name,
                "deployment_path": str(relative),
                "changed": False,
                "pushed": pushed,
                "local_path": str(self.local_path),
                "branch": self.branch,
            }
        commit = self._commit_and_push(f"[{action}] {name}")
        return {
            "enabled": True,
            "success": True,
            "action": action,
            "deployment": name,
            "deployment_path": str(relative),
            "changed": True,
            "commit": commit,
            "pushed": True,
            "local_path": str(self.local_path),
            "branch": self.branch,
        }

    def delete_deployment(self, name):
        self.ensure_repo()
        target = self._deployment_directory(name)
        if target.exists():
            shutil.rmtree(target)
        relative = target.relative_to(self.local_path)
        self._git("add", "-A", "--", str(relative))
        changed = self._git("diff", "--cached", "--quiet", check=False).returncode == 1
        if not changed:
            pushed = self._push_pending_commit()
            return {
                "enabled": True,
                "success": True,
                "action": "delete",
                "deployment": name,
                "deployment_path": str(relative),
                "changed": False,
                "pushed": pushed,
                "local_path": str(self.local_path),
                "branch": self.branch,
            }
        commit = self._commit_and_push(f"[delete] {name}")
        return {
            "enabled": True,
            "success": True,
            "action": "delete",
            "deployment": name,
            "deployment_path": str(relative),
            "changed": True,
            "commit": commit,
            "pushed": True,
            "local_path": str(self.local_path),
            "branch": self.branch,
        }

    def sync_all(self, deployments):
        self.ensure_repo()
        names = []
        for deployment in deployments:
            name, _ = self._write_deployment(deployment)
            names.append(name)
        self._git("add", "--", DEPLOYMENTS_DIRECTORY)
        changed = self._git("diff", "--cached", "--quiet", check=False).returncode == 1
        if not changed:
            pushed = self._push_pending_commit()
            return {
                "enabled": True,
                "success": True,
                "action": "sync",
                "deployments": names,
                "deployment_paths": [
                    str(Path(DEPLOYMENTS_DIRECTORY) / sanitize_file_name(name))
                    for name in names
                ],
                "count": len(names),
                "changed": False,
                "pushed": pushed,
                "local_path": str(self.local_path),
                "branch": self.branch,
            }
        commit = self._commit_and_push(f"sync {len(names)} deployments")
        return {
            "enabled": True,
            "success": True,
            "action": "sync",
            "deployments": names,
            "deployment_paths": [
                str(Path(DEPLOYMENTS_DIRECTORY) / sanitize_file_name(name))
                for name in names
            ],
            "count": len(names),
            "changed": True,
            "commit": commit,
            "pushed": True,
            "local_path": str(self.local_path),
            "branch": self.branch,
        }


def _auto_failure(action, error, deployment=""):
    result = {
        "enabled": True,
        "success": False,
        "action": action,
        "error": str(error),
    }
    if deployment:
        result["deployment"] = deployment
    print(f"[Git Sync] {action} synchronization failed: {error}", file=sys.stderr)
    return result


def auto_sync_deployment(deployment, action):
    settings, error, configured = load_git_settings()
    if not configured:
        return None
    if error or settings is None:
        return _auto_failure(action, error or "Invalid Git configuration")
    try:
        return GitSyncService(settings).sync_deployment(deployment, action)
    except Exception as exc:
        return _auto_failure(action, exc, deployment_name(deployment))


def auto_delete_deployment(name, prefetch_error=""):
    settings, error, configured = load_git_settings()
    if not configured:
        return None
    if error or settings is None:
        return _auto_failure("delete", error or "Invalid Git configuration", name)
    if prefetch_error:
        return _auto_failure("delete", prefetch_error, name)
    if not name:
        return _auto_failure("delete", "Unable to obtain the Deployment name before deletion")
    try:
        return GitSyncService(settings).delete_deployment(name)
    except Exception as exc:
        return _auto_failure("delete", exc, name)


def attach_git_sync(result, git_result):
    if git_result is not None:
        result["git_sync"] = git_result
    return result


def fetch_deployment(args, deployment_id, client=None):
    from alibabacloud_ververica20220718.models import GetDeploymentHeaders

    active_client = client or get_client(args.region_id)
    headers = GetDeploymentHeaders(workspace=args.workspace)
    return call_api(
        "get_deployment_for_git",
        active_client.get_deployment_with_options,
        args.namespace,
        deployment_id,
        headers,
        runtime_options(),
    )


def _list_all_deployments(args, client):
    from alibabacloud_ververica20220718.models import (
        ListDeploymentsHeaders,
        ListDeploymentsRequest,
    )

    page_index = 1
    page_size = 100
    deployment_ids = []
    while True:
        headers = ListDeploymentsHeaders(workspace=args.workspace)
        request = ListDeploymentsRequest(page_index=page_index, page_size=page_size)
        result = call_api(
            "list_deployments_for_git",
            client.list_deployments_with_options,
            args.namespace,
            request,
            headers,
            runtime_options(),
        )
        if not api_result_succeeded(result):
            return None, _api_error(result)
        body = result.get("data") or {}
        items = body.get("data") if isinstance(body, dict) else None
        if not isinstance(items, list):
            items = []
        for item in items:
            deployment_id = _string(
                _get(item, "deploymentId", "deployment_id")
            )
            if deployment_id:
                deployment_ids.append(deployment_id)
        total = body.get("totalSize") if isinstance(body, dict) else None
        if not items or len(items) < page_size:
            break
        if isinstance(total, int) and len(deployment_ids) >= total:
            break
        page_index += 1
        if page_index > 1000:
            return None, "Deployment pagination exceeded the safety limit of 1,000 pages"

    deployments = []
    for deployment_id in deployment_ids:
        result = fetch_deployment(args, deployment_id, client)
        if not api_result_succeeded(result):
            return None, f"Failed to read Deployment {deployment_id}: {_api_error(result)}"
        deployment = api_result_data(result)
        if isinstance(deployment, dict):
            deployments.append(deployment)
    return deployments, ""


def cmd_git_init(args):
    chk = require_confirmation(
        "git_init",
        "Initializing Git synchronization clones or updates the repository at the configured local path.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    settings, error, configured = load_git_settings()
    if not configured:
        return output(
            error_response("git_init", "GitSyncNotConfigured", "Git synchronization is not configured"),
            args.output,
        )
    if error or settings is None:
        return output(
            error_response("git_init", "GitConfigurationError", error), args.output
        )
    try:
        data = GitSyncService(settings).ensure_repo()
    except Exception as exc:
        return output(
            error_response("git_init", "GitSyncError", str(exc)), args.output
        )
    output(success_response("git_init", data), args.output)


def cmd_git_sync(args):
    err = require_args(args, "workspace", "namespace", "region_id")
    if err:
        return output(err, args.output)
    chk = require_confirmation(
        "git_sync",
        "Git synchronization writes files, creates a commit, and pushes to the configured remote branch.",
        args.confirm,
    )
    if chk:
        return output(chk, args.output)

    settings, config_error, configured = load_git_settings()
    if not configured:
        return output(
            error_response("git_sync", "GitSyncNotConfigured", "Git synchronization is not configured"),
            args.output,
        )
    if config_error or settings is None:
        return output(
            error_response("git_sync", "GitConfigurationError", config_error),
            args.output,
        )

    client = get_client(args.region_id)
    if args.deployment_id:
        result = fetch_deployment(args, args.deployment_id, client)
        if not api_result_succeeded(result):
            return output(
                error_response("git_sync", "DeploymentReadError", _api_error(result)),
                args.output,
            )
        deployment = api_result_data(result)
        deployments = [deployment] if isinstance(deployment, dict) else []
    else:
        deployments, list_error = _list_all_deployments(args, client)
        if list_error:
            return output(
                error_response("git_sync", "DeploymentReadError", list_error),
                args.output,
            )

    if args.deployment_id and not deployments:
        return output(
            error_response("git_sync", "DeploymentNotFound", "No Deployment is available to synchronize"),
            args.output,
        )
    if not deployments:
        return output(
            success_response(
                "git_sync",
                {
                    "enabled": True,
                    "success": True,
                    "action": "sync",
                    "deployments": [],
                    "deployment_paths": [],
                    "count": 0,
                    "changed": False,
                    "pushed": False,
                    "local_path": settings["local_path"],
                    "branch": settings["branch"],
                    "message": "No Deployment is available to synchronize",
                },
            ),
            args.output,
        )
    try:
        service = GitSyncService(settings)
        if args.deployment_id:
            data = service.sync_deployment(deployments[0], "sync")
        else:
            data = service.sync_all(deployments)
    except Exception as exc:
        return output(
            error_response("git_sync", "GitSyncError", str(exc)), args.output
        )
    output(success_response("git_sync", data), args.output)


def register(subparsers):
    init_parser = subparsers.add_parser(
        "git_init", help="Initialize or update the Git synchronization repository"
    )
    add_common_args(init_parser)
    init_parser.add_argument(
        "--confirm", action="store_true", help="Confirm initialization of the local Git repository"
    )
    init_parser.set_defaults(func=cmd_git_init, subcommand="git_init")

    sync_parser = subparsers.add_parser(
        "git_sync", help="Synchronize all Deployments or one Deployment to Git"
    )
    add_common_args(sync_parser)
    sync_parser.add_argument(
        "--deployment_id", help="Synchronize only this Deployment; omit to synchronize all Deployments"
    )
    sync_parser.add_argument(
        "--confirm", action="store_true", help="Confirm the Git commit and push"
    )
    sync_parser.set_defaults(func=cmd_git_sync, subcommand="git_sync")
