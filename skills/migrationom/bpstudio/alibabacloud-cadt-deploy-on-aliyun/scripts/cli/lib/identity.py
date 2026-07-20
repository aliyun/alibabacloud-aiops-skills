"""Identity resolver — derives uid from local aliyun CLI profile.

Resolution priority:
  1. ALIYUN_UID env-var (testing / CI)
  2. ~/.cadt-uid-cache file (written after first successful resolve)
  3. ~/.aliyun/config.json profile fields (account_id / uid / user_id)
  4. aliyun sts get-caller-identity (live call, then cached)
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from functools import lru_cache
from typing import Optional

from .errors import IdentityNotFound

ENV_VAR = "ALIYUN_UID"
CACHE_FILE = os.path.join(os.path.expanduser("~"), ".cadt-uid-cache")
ALIYUN_CONFIG = os.path.join(os.path.expanduser("~"), ".aliyun", "config.json")


@lru_cache(maxsize=1)
def get_uid() -> str:
    """Resolve uid in priority: env-var → cache → profile → sts call."""
    # 1. explicit env-var (testing / CI)
    env_uid = os.environ.get(ENV_VAR)
    if env_uid:
        return env_uid

    # 2. cache file (written after first successful resolve)
    cached = _read_cache()
    if cached:
        return cached

    # 3. parse aliyun profile static fields
    parsed = _parse_aliyun_profile()
    if parsed:
        _write_cache(parsed)
        return parsed

    # 4. live call: aliyun sts get-caller-identity
    sts_uid = _get_caller_identity()
    if sts_uid:
        _write_cache(sts_uid)
        return sts_uid

    raise IdentityNotFound(
        "Unable to resolve current aliyun uid",
        fix_hint=(
            "Ensure you have run `aliyun configure` to set up credentials, "
            f"or explicitly set environment variable {ENV_VAR}=<your-uid>"
        ),
    )


def _read_cache() -> Optional[str]:
    if not os.path.isfile(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return f.read().strip() or None
    except OSError:
        return None


def _write_cache(uid: str) -> None:
    try:
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            f.write(uid)
    except OSError:
        # Cache failure is non-fatal.
        pass


def _parse_aliyun_profile() -> Optional[str]:
    """Best-effort parse of ~/.aliyun/config.json static fields."""
    if not os.path.isfile(ALIYUN_CONFIG):
        return None
    try:
        with open(ALIYUN_CONFIG, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    current = cfg.get("current")
    for profile in cfg.get("profiles", []):
        if profile.get("name") != current:
            continue
        for key in ("account_id", "uid", "user_id"):
            val = profile.get(key)
            if val:
                return str(val)
    return None


def _get_caller_identity() -> Optional[str]:
    """Call `aliyun sts get-caller-identity` to resolve AccountId.

    Tries with --region from environment first (for STS endpoint reachability),
    then falls back to no region flag.
    """
    aliyun_bin = shutil.which("aliyun")
    if not aliyun_bin:
        return None

    regions: list[str] = []
    for env_key in ("ALIBABA_CLOUD_REGION_ID", "REGION_ID"):
        r = os.environ.get(env_key)
        if r:
            regions.append(r)
            break
    regions.append("")

    session_id = os.environ.get("SKILL_SESSION_ID", "")

    for region in regions:
        cmd = [aliyun_bin, "sts", "get-caller-identity"]
        if region:
            cmd.extend(["--region", region])
        if session_id:
            cmd.extend(["--user-agent", f"AlibabaCloud-Agent-Skills/alibabacloud-cadt-deploy-on-aliyun/{session_id}"])
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True, text=True, timeout=15,
                stdin=subprocess.DEVNULL,
            )
            if proc.returncode != 0:
                continue
            data = json.loads(proc.stdout)
            account_id = data.get("AccountId") or data.get("accountId")
            if account_id:
                return str(account_id)
        except (OSError, json.JSONDecodeError, subprocess.TimeoutExpired):
            continue
    return None
