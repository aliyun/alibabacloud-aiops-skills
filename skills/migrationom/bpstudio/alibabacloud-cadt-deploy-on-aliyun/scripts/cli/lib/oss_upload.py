"""Shared OSS upload utility.

Usage: upload_to_oss(file_path, app_name, region) -> package_url

Flow: tarball validation -> STS credentials -> ossutil upload -> size verification -> return OSS URL.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import time
from typing import Any, Dict, List

from .errors import HookReject, PRE_HOOK_REJECTED
from .identity import get_uid

ALIYUN_BIN = shutil.which("aliyun") or "aliyun"
RETRY_MAX = 3

_SKILL_NAME = "alibabacloud-cadt-deploy-on-aliyun"
def _session_id() -> str:
    return os.environ.get("SKILL_SESSION_ID", "")


def _ua_flags() -> list:
    sid = _session_id()
    if sid:
        return ["--user-agent", f"AlibabaCloud-Agent-Skills/{_SKILL_NAME}/{sid}"]
    return []


def _info(msg: str) -> None:
    print(f"INFO:  {msg}", file=sys.stderr)


def _retry(cmd: list, label: str) -> subprocess.CompletedProcess:
    for i in range(1, RETRY_MAX + 1):
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120,
                                  stdin=subprocess.DEVNULL)
            if proc.returncode == 0:
                return proc
        except subprocess.TimeoutExpired:
            pass
        if i < RETRY_MAX:
            _info(f"{label} failed (attempt {i}/{RETRY_MAX}), retrying in {i}s")
            time.sleep(i)
    raise HookReject(
        PRE_HOOK_REJECTED,
        f"{label} still failed after {RETRY_MAX} retries",
        fix_hint="Check aliyun CLI availability and network connectivity",
    )


def _exec_json(cmd: list, label: str) -> dict:
    proc = _retry(cmd, label)
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"{label} output is not JSON: {proc.stdout[:200]}",
            fix_hint="Check aliyun CLI version (aliyun version)",
        )


_APPLE_DOUBLE_PREFIX = "._"


def _find_appledouble_members(tar_path: str) -> List[str]:
    """Scan a tar.gz for AppleDouble resource fork metadata files."""
    bad_names: List[str] = []
    try:
        with tarfile.open(tar_path, "r:gz") as tf:
            for member in tf.getmembers():
                base = os.path.basename(member.name)
                if base.startswith(_APPLE_DOUBLE_PREFIX):
                    bad_names.append(member.name)
    except tarfile.ReadError:
        pass
    return bad_names


def _validate_tarball(file_path: str) -> None:
    """Check tar.gz for AppleDouble metadata (macOS resource fork leakage).

    Raises HookReject if any ``._*`` entries are found, with a clear
    fix-hint pointing to ``COPYFILE_DISABLE=1 tar -czf``.
    """
    if not file_path.endswith(".tar.gz") and not file_path.endswith(".tgz"):
        return

    bad = _find_appledouble_members(file_path)
    if bad:
        preview = bad[:5]
        suffix = f" (+{len(bad) - 5} more)" if len(bad) > 5 else ""
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"Deploy artifact contains {len(bad)} AppleDouble metadata file(s): "
            f"{', '.join(preview)}{suffix}",
            fix_hint=(
                "Re-pack with: COPYFILE_DISABLE=1 tar -czf <output> -C <dir> .  "
                "(macOS resource fork prevention — required on all platforms)"
            ),
        )


def upload_to_oss(file_path: str, app_name: str, region: str = "cn-hangzhou") -> str:
    """Upload a local file to OSS and return the public URL.

    Raises HookReject on any failure (file not found, STS failure, upload failure).
    """
    if not file_path:
        raise HookReject(
            PRE_HOOK_REJECTED,
            "filePath is required",
            fix_hint='Pass "filePath": "/path/to/build-artifact"',
        )

    if not os.path.isfile(file_path):
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"File not found: {file_path}",
            fix_hint="Verify build artifact path is correct, or run the build step first",
        )

    _validate_tarball(file_path)

    if not app_name:
        raise HookReject(
            PRE_HOOK_REJECTED,
            "appName is required for OSS upload",
            fix_hint='Pass "appName": "your-app-name"',
        )

    uid = get_uid()
    _info(f"uid={uid}  appName={app_name}")

    _info("Calling bpstudio get-token to obtain STS credentials...")
    token_raw = _exec_json(
        [ALIYUN_BIN, "bpstudio", "get-token",
         "--api-version", "2021-09-31",
         "--region", region] + _ua_flags(),
        "bpstudio get-token",
    )

    code = str(token_raw.get("Code", ""))
    if code != "200":
        msg = token_raw.get("Message", "")
        rid = token_raw.get("RequestId", "")
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"get-token failed: Code={code} Message={msg} RequestId={rid}",
            fix_hint="Check that aliyun configure credentials are valid",
        )

    data = token_raw.get("Data") or {}
    oss_ak = data.get("AccessKeyId", "")
    oss_sk = data.get("AccessKeySecret", "")
    oss_tk = data.get("SecurityToken", "")
    oss_ep = data.get("Endpoint", "")
    oss_bk = data.get("Bucket", "")

    if not all([oss_ak, oss_sk, oss_tk, oss_ep, oss_bk]):
        raise HookReject(
            PRE_HOOK_REJECTED,
            "get-token response STS credentials missing required fields",
            fix_hint="Check API response data completeness",
        )

    oss_ep = re.sub(r"^https?://", "", oss_ep).rstrip("/")

    filename = os.path.basename(file_path)
    object_key = f"{uid}/{app_name}/{filename}"

    _info(f"Uploading {file_path} -> https://{oss_bk}.{oss_ep}/{object_key}")
    _retry(
        [ALIYUN_BIN, "ossutil", "cp", file_path, f"oss://{oss_bk}/{object_key}",
         "--access-key-id", oss_ak,
         "--access-key-secret", oss_sk,
         "--sts-token", oss_tk,
         "--endpoint", oss_ep,
         "--force"] + _ua_flags(),
        "ossutil cp",
    )

    local_size = os.path.getsize(file_path)
    _info(f"Verifying remote size... (local={local_size})")

    stat_proc = _retry(
        [ALIYUN_BIN, "ossutil", "stat", f"oss://{oss_bk}/{object_key}",
         "--access-key-id", oss_ak,
         "--access-key-secret", oss_sk,
         "--sts-token", oss_tk,
         "--endpoint", oss_ep] + _ua_flags(),
        "ossutil stat",
    )
    stat_output = stat_proc.stdout + stat_proc.stderr
    match = re.search(r"(?:Content-Length|ContentLength|Size)\s*[:=]\s*(\d+)", stat_output, re.IGNORECASE)
    if not match:
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"oss stat could not parse Content-Length; raw output: {stat_output[:300]}",
            fix_hint="Check aliyun CLI version or whether the OSS object exists",
        )

    remote_size = int(match.group(1))
    if local_size != remote_size:
        raise HookReject(
            PRE_HOOK_REJECTED,
            f"Upload size mismatch: local={local_size} remote={remote_size} -> treated as upload failure",
            fix_hint=f"Suggest re-running; if multipart residual, manually run aliyun ossutil rm oss://{oss_bk}/{object_key}",
        )
    _info(f"Size verification passed ({local_size} bytes)")

    return f"https://{oss_bk}.{oss_ep}/{object_key}"