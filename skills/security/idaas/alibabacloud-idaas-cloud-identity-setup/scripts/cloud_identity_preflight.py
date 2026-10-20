#!/usr/bin/env python3
"""Read-only preflight for IDaaS multi-cloud account onboarding."""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import pathlib
import platform
import re
import shutil
import subprocess
import sys
from typing import Any

from skill_ua import user_agent


VENDORS = {"alibaba_cloud", "aws", "tencent_cloud"}
DEFAULT_SITE = {"alibaba_cloud": "china_mainland", "aws": "global", "tencent_cloud": "china_mainland"}


class CommandError(RuntimeError):
    def __init__(self, argv: list[str], message: str, returncode: int = 1, error_type: str = 'unknown', request_id: str | None = None):
        super().__init__(message)
        self.argv = argv
        self.returncode = returncode
        self.error_type = error_type
        self.request_id = request_id
        self.error_code = None
        self.action = None


def command_failure(argv, completed):
    """Extract only known error families and UUID request IDs, never raw output."""
    raw = completed.stdout + '\n' + completed.stderr
    if re.search(r"Plugin .+ is required.+not installed", raw, re.I | re.S):
        return CommandError(argv, 'Required official CLI plugin is not installed; prepare the selected profile before discovery', completed.returncode or 1, 'environment')
    if re.search(r"not a valid api|unknown command|unchecked version", raw, re.I):
        return CommandError(argv, 'Installed CLI does not support the requested API or version; no credential or resource change is a remedy', completed.returncode or 1, 'environment')
    code = re.search(r'(?:error_code|ErrorCode|Code)[\s"\':=]+([A-Za-z0-9_.-]+)', raw)
    value = code.group(1).lower() if code else ''
    family = 'unknown'
    if value.startswith(('forbidden', 'nopermission', 'accessdenied')):
        family = 'permission'
    elif value.startswith(('invalidparameter', 'missingparameter')):
        family = 'parameter'
    elif value.startswith(('throttling', 'requestlimitexceeded', 'toomanyrequests')):
        family = 'throttling'
    elif value.startswith(('internalerror', 'serviceunavailable', 'internalfailure')):
        family = 'internal'
    elif value.startswith(('invalidaccesskeyid', 'expiredsecuritytoken', 'invalidsecuritytoken')):
        family = 'authentication'
    request = re.search(r'RequestId[\s"\':=]+([A-Fa-f0-9]{8}(?:-[A-Fa-f0-9]{4}){3}-[A-Fa-f0-9]{12})', raw)
    request_id = request.group(1) if request else None
    error = CommandError(argv, 'Cloud request failed: ' + family + '; no raw credential/error output retained',
                         completed.returncode, family, request_id)
    error.error_code = code.group(1) if code else None
    if '--action' in argv and pathlib.Path(argv[1]).name == 'eiam_auxiliary_api.py':
        index = argv.index('--action') + 1
        if index < len(argv) and argv[index] in ('GetCloudAccountRoleConfig', 'CheckCloudAccountRoleConfig'):
            error.action = argv[index]
    return error


def error_fields(error):
    return {'reason': str(error), 'error_type': error.error_type,
            'failed_action': error.action or ' '.join(error.argv[1:3]),
            'error_code': error.error_code, 'RequestId': error.request_id}


def error_status(error, eiam=False):
    if error.error_type == 'permission':
        return 'permission_denied'
    if error.error_type == 'environment':
        return 'environment_required'
    if error.error_type == 'authentication':
        return 'eiam_auth_required' if eiam else 'auth_required'
    return 'discovery_incomplete'


def run_json(argv: list[str]) -> dict[str, Any]:
    try:
        env = os.environ.copy()
        if pathlib.Path(argv[0]).stem.lower() == 'aliyun':
            env['ALIBABA_CLOUD_USER_AGENT'] = user_agent()
        completed = subprocess.run(argv, check=False, text=True, capture_output=True, timeout=60, env=env, stdin=subprocess.DEVNULL)
    except ValueError as exc:
        raise CommandError(argv, str(exc)) from exc
    except subprocess.TimeoutExpired as exc:
        raw = '\n'.join(part.decode('utf-8', errors='replace') if isinstance(part, bytes) else (part or '')
                        for part in (exc.stdout, exc.stderr))
        if re.search(r"Plugin .+ is required.+not installed", raw, re.I | re.S):
            raise CommandError(argv, 'Required official CLI plugin is not installed; discovery did not complete', error_type='environment') from exc
        raise CommandError(argv, "CLI request timed out; discovery is incomplete", error_type='timeout') from exc
    except FileNotFoundError as exc:
        raise CommandError(argv, f"CLI not installed: {argv[0]}", 127, 'environment') from exc
    if completed.returncode or re.search(r"Plugin .+ is required.+not installed", completed.stdout + '\n' + completed.stderr, re.I | re.S):
        raise command_failure(argv, completed)
    try:
        value = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        if 'ErrorCode' in completed.stdout or 'ERROR:' in completed.stdout:
            raise command_failure(argv, completed) from exc
        raise CommandError(argv, "CLI returned non-JSON output") from exc
    if not isinstance(value, dict):
        raise CommandError(argv, "CLI returned an unexpected JSON value")
    return value


def cli_path(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise CommandError([name], f"CLI not installed: {name}", 127, 'environment')
    return path


def default_state_file(vendor: str, account_id: str, instance_id: str) -> pathlib.PurePath:
    filename = f"{vendor}-{account_id}-{instance_id}.json"
    if platform.system().lower() == "windows":
        root = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        user_root = os.environ.get("USERPROFILE") or r"C:\Users\Default"
        base = pathlib.PureWindowsPath(root) if root else pathlib.PureWindowsPath(user_root) / "AppData" / "Local"
        return base / "Codex" / "idaas-cloud-identity-setup" / filename
    return pathlib.Path.home() / ".codex" / "state" / "idaas-cloud-identity-setup" / filename


def caller_identity(vendor: str, profile: str, region: str | None = None) -> tuple[str, dict[str, Any]]:
    if vendor == "alibaba_cloud":
        data = run_json([cli_path("aliyun"), "sts", "get-caller-identity", "--profile", profile])
        return str(data.get("AccountId", "")), data
    if vendor == "aws":
        data = run_json([
            cli_path("aws"), "sts", "get-caller-identity", "--profile", profile,
            "--region", region or "us-east-1", "--output", "json",
        ])
        return str(data.get("Account", "")), data
    data = run_json([cli_path("tccli"), "sts", "GetCallerIdentity", "--profile", profile])
    response = data.get("Response", data)
    return str(response.get("AccountId") or response.get("AccountUin") or response.get("OwnerUin") or ""), data


def list_instances(eiam_profile: str) -> list[dict[str, Any]]:
    items = []
    for page in range(1, 1001):
        data = run_json([cli_path("aliyun"), "eiam", "list-instances",
                         "--page-number", str(page), "--page-size", "100",
                         "--profile", eiam_profile])
        batch = data.get("Instances")
        if not isinstance(batch, list):
            raise CommandError([], "instance response has no valid Instances array")
        items.extend(batch)
        total = data.get("TotalCount")
        if (total is not None and len(items) >= int(total)) or len(batch) < 100:
            return items
    raise CommandError([], "instance pagination exceeded the safety limit")


def get_instance(instance_id: str, eiam_profile: str) -> dict[str, Any]:
    data = run_json([cli_path("aliyun"), "eiam", "get-instance",
                     "--instance-id", instance_id, "--profile", eiam_profile])
    instance = data.get("Instance", data)
    if not isinstance(instance, dict) or instance.get("InstanceId") != instance_id:
        raise CommandError([], "instance response does not match the requested instance")
    return instance


def list_accounts(instance_id: str, eiam_profile: str) -> list[dict[str, Any]]:
    items, seen = [], set()
    token = None
    for _ in range(1000):
        argv = [cli_path("aliyun"), "eiam", "list-cloud-accounts", "--instance-id", instance_id,
                "--max-results", "100", "--profile", eiam_profile]
        if token:
            argv.extend(["--next-token", token])
        data = run_json(argv)
        batch = data.get("CloudAccounts")
        if not isinstance(batch, list):
            raise CommandError(argv, "account response has no valid CloudAccounts array")
        items.extend(batch)
        token = data.get("NextToken")
        if not token:
            return items
        if not isinstance(token, str) or token in seen:
            raise CommandError(argv, "account pagination returned an invalid or repeated token")
        seen.add(token)
    raise CommandError([], "account pagination exceeded the safety limit")


def account_match(item: dict[str, Any], vendor: str, account_id: str) -> bool:
    return (
        str(item.get("CloudAccountVendorType", "")) == vendor
        and str(item.get("CloudAccountExternalId", "")) == account_id
    )


def compact_account(instance: dict[str, Any], account: dict[str, Any]) -> dict[str, Any]:
    endpoint = instance.get("DefaultEndpoint") or {}
    return {
        "instance_id": instance.get("InstanceId"),
        "instance_description": instance.get("Description"),
        "instance_endpoint": endpoint.get("Endpoint"),
        "cloud_account_id": account.get("CloudAccountId"),
        "health": account.get("CloudAccountHealth"),
        "provider_name": account.get("CloudAccountProviderName"),
        "site": account.get("CloudAccountSite"),
    }


def emit(result: dict[str, Any], state_file: str | None) -> int:
    result["schema_version"] = 1
    if state_file:
        path = pathlib.Path(state_file).expanduser()
        result["state_file"] = str(path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        except OSError as exc:
            result["state_warning"] = f"unable to persist state: {exc}"
    payload = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    print(payload)
    return 0 if result["status"] in {"ready_new", "ready_resume", "local_validation_passed"} else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only IDaaS cloud identity onboarding preflight")
    parser.add_argument("--vendor", required=True, choices=sorted(VENDORS))
    parser.add_argument("--account-id", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--eiam-profile", required=True)
    parser.add_argument("--cloud-profile", required=True)
    parser.add_argument("--site", choices=["china_mainland", "global"])
    parser.add_argument("--cloud-region", help="Cloud CLI region; AWS defaults from site")
    parser.add_argument("--state-file")
    parser.add_argument("--verify-target-only", action="store_true", help="Verify an existing target record only; never infer readiness for new onboarding")
    parser.add_argument("--local-only", action="store_true", help="Validate supplied input syntax only; never discover CLIs, credentials, or cloud resources")
    args = parser.parse_args()

    base = {
        "vendor": args.vendor,
        "account_id": args.account_id,
        "instance_id": args.instance_id,
        "site": args.site or DEFAULT_SITE[args.vendor],
        "profiles": {"eiam": args.eiam_profile, "cloud": args.cloud_profile},
        "environment": {
            "os": platform.system().lower(),
            "python": sys.executable,
        },
    }
    state_file = args.state_file or str(default_state_file(args.vendor, args.account_id, args.instance_id))
    if not re.fullmatch(r"[0-9]{1,32}", args.account_id) or (args.vendor == "aws" and len(args.account_id) != 12):
        return emit({**base, "status": "invalid_input", "reason": "invalid account_id"}, None)

    if not re.fullmatch(r"idaas_[a-z0-9]{1,64}", args.instance_id):
        return emit({**base, "status": "invalid_input", "reason": "invalid instance_id"}, None)
    for profile in (args.eiam_profile, args.cloud_profile):
        if not re.fullmatch(r"[A-Za-z0-9_.@-]{1,128}", profile) or profile.startswith("-"):
            return emit({**base, "status": "invalid_input", "reason": "invalid profile name"}, None)
    if args.local_only:
        return emit({**base, "status": "local_validation_passed",
                     "cloud_calls": 0, "identity_verified": False,
                     "reason": "syntax only; not evidence of cloud identity, access, or onboarding readiness"}, None)
    try:
        cloud_region = args.cloud_region
        if args.vendor == "aws" and not cloud_region:
            cloud_region = "cn-north-1" if base["site"] == "china_mainland" else "us-east-1"
        actual_id, _ = caller_identity(args.vendor, args.cloud_profile, cloud_region)
    except CommandError as exc:
        return emit({
            **base, "status": error_status(exc),
            **error_fields(exc), "required_cli": exc.argv[0],
        }, state_file)
    if actual_id != args.account_id:
        return emit({
            **base, "status": "wrong_cloud_account", "actual_account_id": actual_id,
            "reason": "authenticated cloud account does not match the requested account",
        }, state_file)

    try:
        instances = ([get_instance(args.instance_id, args.eiam_profile)]
                     if args.verify_target_only else list_instances(args.eiam_profile))
    except CommandError as exc:
        return emit({**base, "status": error_status(exc, eiam=True),
                     **error_fields(exc)}, state_file)
    target = next((item for item in instances if item.get("InstanceId") == args.instance_id), None)
    if not target:
        return emit({
            **base, "status": "instance_unavailable",
            "reason": "target instance is not visible to the EIAM profile",
        }, state_file)

    base["environment"]["cli_paths"] = {
        "aliyun": cli_path("aliyun"),
        "cloud": cli_path({"alibaba_cloud": "aliyun", "aws": "aws", "tencent_cloud": "tccli"}[args.vendor]),
    }

    if args.verify_target_only:
        instances = [target]
        base["discovery_scope"] = "existing_target_only"

    found: list[dict[str, Any]] = []
    failed_instances = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(8, max(1, len(instances)))) as pool:
        pending = {pool.submit(list_accounts, str(item["InstanceId"]), args.eiam_profile): item for item in instances}
        for future, instance in pending.items():
            try:
                accounts = future.result()
            except CommandError:
                failed_instances.append(instance["InstanceId"])
                continue
            found.extend(compact_account(instance, account) for account in accounts if account_match(account, args.vendor, args.account_id))

    if failed_instances:
        return emit({**base, "status": "discovery_incomplete", "failed_instances": failed_instances,
                     "reason": "account discovery failed; do not infer absence or proceed to writes"}, state_file)
    target_record = next((item for item in found if item["instance_id"] == args.instance_id), None)
    records_elsewhere = [item for item in found if item["instance_id"] != args.instance_id ]
    if args.verify_target_only and not target_record:
        return emit({**base, "status": "discovery_incomplete", "reason": "target-only verification found no existing record; full discovery is required before new onboarding"}, state_file)
    if records_elsewhere:
        status = "managed_elsewhere"
        action = "stop: account is managed by another instance; ownership transfer is outside this skill and no records or shared trust may be changed"
    elif target_record:
        status = "ready_resume"
        action = "reuse the existing target EIAM cloud account and continue from its health state"
    else:
        status = "ready_new"
        action = "create the EIAM cloud account, configure cloud resources, and verify health"

    return emit({
        **base,
        "status": status,
        "identity_verified": True,
        "target_instance": {
            "instance_id": target.get("InstanceId"),
            "description": target.get("Description"),
            "endpoint": (target.get("DefaultEndpoint") or {}).get("Endpoint"),
        },
        "target_record": target_record,
        "existing_records": records_elsewhere,
        "planned_action": action,
    }, state_file)


if __name__ == "__main__":
    sys.exit(main())
