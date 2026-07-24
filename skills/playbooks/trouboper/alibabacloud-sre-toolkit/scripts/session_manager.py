#!/usr/bin/env python3
"""SRE session lifecycle manager.

Manages .aliyun-sre/ directory structure, status.json state,
TTL checks, and cleanup.

Stdlib-only, no third-party deps.
"""
from __future__ import annotations

import argparse
try:
    import fcntl
except ImportError:  # non-POSIX (e.g. Windows) has no fcntl
    fcntl = None
import importlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

SRE_DIR_NAME = ".aliyun-sre"
DEFAULT_TTL_SECONDS = 300

VALID_STATUSES = ("pending", "triaged", "diagnosed", "planned", "replanning", "validated", "executed", "failed")

TRANSITION_ORDER = {
    "pending": 0,
    "triaged": 1,
    "diagnosed": 2,
    "planned": 3,
    "replanning": 3,
    "validated": 4,
    "executed": 5,
    "failed": 99,
}

REPLAN_PAIR = {"planned", "replanning"}

STAROPS_CONFIG_DIR = ".starops"
STAROPS_CONFIG_FILE = "config.json"
STAROPS_CONFIG_LOCK = "config.lock"
STAROPS_REQUIRED_KEYS = ("employeeId", "uid")

ALIYUN_CONFIG_PATH = Path.home() / ".aliyun" / "config.json"
PYTHON_DEPS = ("requests", "alibabacloud_credentials")

_PROFILE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")


def _validate_profile_name(profile: str | None) -> None:
    """Validate aliyun CLI profile name to prevent command injection.

    Profile names must be alphanumeric plus underscore/hyphen only.
    """
    if profile is None:
        return
    if not _PROFILE_NAME_RE.match(profile):
        raise ValueError(
            f"Invalid profile name: {profile!r}. "
            "Profile names may only contain A-Z, a-z, 0-9, underscore, and hyphen."
        )


ALIYUN_NOT_INSTALLED_REMEDIATION = (
    "Install aliyun CLI:\n"
    "  macOS: brew install aliyun-cli\n"
    "  Linux: curl -fsSL -o /tmp/aliyun-cli.tgz https://aliyuncli.alicdn.com/aliyun-cli-linux-latest-amd64.tgz && tar xzf /tmp/aliyun-cli.tgz -C /tmp && mkdir -p ~/.local/bin && mv /tmp/aliyun ~/.local/bin/ && export PATH=\"$HOME/.local/bin:$PATH\"\n"
    "  Docs: https://help.aliyun.com/document_detail/121541.html"
)
ALIYUN_NOT_CONFIGURED_REMEDIATION = (
    "Configure aliyun CLI credentials:\n"
    "  Run: aliyun configure\n"
    "  Follow prompts for AccessKey ID, AccessKey Secret and default Region.\n"
    "  Config file: ~/.aliyun/config.json"
)
STAROPS_MISSING_REMEDIATION = (
    "Configure STAROps:\n"
    '  Run: python3 <skill-root>/scripts/session_manager.py configure-set --cwd "$PWD" --scope project --employee-id "<ID>" --uid "<UID>"  (--workspace optional)\n'
    "  See: references/starops-config.md"
)
PYTHON_DEPS_REMEDIATION = (
    "Install Python dependencies:\n"
    "  pip3 install -r <skill-root>/scripts/requirements.txt"
)

STAROPS_CACHE_DIR = Path.home() / ".cache" / "alibabacloud-agent-toolkit"
STAROPS_CACHE_FILE = STAROPS_CACHE_DIR / "starops_capabilities_cache.json"
STAROPS_CACHE_DEFAULT_TTL = 86400


def _secure_write_open(path, append: bool = False) -> int:
    """Open a file for writing with 0o600 permissions (owner-only read/write).

    Returns a raw file descriptor. Wrap with ``os.fdopen(fd, mode)`` to get a
    Python file object. This ensures config/session files are never
    world-readable, regardless of the process umask.
    """
    flags = os.O_CREAT | os.O_WRONLY | (os.O_APPEND if append else os.O_TRUNC)
    return os.open(str(path), flags, 0o600)


def generate_session_name() -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{ts}-{suffix}"


def ensure_sre_dir(cwd: str) -> str:
    sre_dir = os.path.join(cwd, SRE_DIR_NAME)
    os.makedirs(sre_dir, exist_ok=True)
    return sre_dir


def init_session(
    cwd: str,
    uid: str | None = None,
    profile: str | None = None,
    employee_id: str | None = None,
    workspace: str | None = None,
) -> dict:
    sre_dir = ensure_sre_dir(cwd)
    session_name = generate_session_name()
    session_dir = os.path.join(sre_dir, session_name)

    tasks_dir = os.path.join(session_dir, "tasks")
    plan_dir = os.path.join(session_dir, "plan")
    observations_dir = os.path.join(session_dir, "observations")
    os.makedirs(tasks_dir, exist_ok=True)
    os.makedirs(plan_dir, exist_ok=True)
    os.makedirs(observations_dir, exist_ok=True)

    # Resolve a strict single-UID context: explicit args win, then fall back
    # to the matching (or default) account in .starops/config.json, then to
    # the aliyun CLI current profile. Each session is pinned to one UID.
    resolved = _resolve_account(cwd, uid)
    if resolved is not None:
        uid = uid or (resolved.get("uid") or None)
        if profile is None:
            profile = resolved.get("profile") or None
        if employee_id is None:
            employee_id = resolved.get("employeeId") or None
        if workspace is None:
            workspace = resolved.get("workspace") or None
    if not profile:
        profile = _get_aliyun_current_profile() or None

    # Auto-resolve UID for single-account mode when not explicitly provided
    if not uid:
        cred_mode = _compute_credential_mode(_enumerate_aliyun_profiles(), _detect_env_credentials())
        if cred_mode == "single":
            auto_uid = _auto_resolve_uid(profile)
            if auto_uid:
                uid = auto_uid

    now = datetime.now(timezone.utc).isoformat()
    status = {
        "session": session_name,
        "status": "pending",
        "created": now,
        "updated": now,
        "cwd": os.path.abspath(cwd),
        "uid": uid or None,
        "profile": profile or None,
        "employeeId": employee_id or None,
        "workspace": workspace or None,
        "threadId": None,
        "current_hypothesis": None,
        "hypothesis_status": None,
        "reasoning_log_entries": 0,
        "replan_count": 0,
        "max_replans": 3,
    }

    status_path = os.path.join(tasks_dir, "status.json")
    fd = _secure_write_open(status_path)
    with os.fdopen(fd, "w") as f:
        json.dump(status, f, indent=2, ensure_ascii=False)

    return {
        "session": session_name,
        "sre_dir": os.path.join(SRE_DIR_NAME, session_name),
        "status": "pending",
        "uid": uid or None,
        "profile": profile or None,
        "employeeId": employee_id or None,
        "workspace": workspace or None,
    }


def read_status(session_name: str, cwd: str) -> dict | None:
    status_path = os.path.join(cwd, SRE_DIR_NAME, session_name, "tasks", "status.json")
    if not os.path.isfile(status_path):
        return None
    with open(status_path, "r") as f:
        return json.load(f)


def write_status(session_name: str, cwd: str, status_data: dict) -> None:
    status_path = os.path.join(cwd, SRE_DIR_NAME, session_name, "tasks", "status.json")
    status_data["updated"] = datetime.now(timezone.utc).isoformat()
    fd = _secure_write_open(status_path)
    with os.fdopen(fd, "w") as f:
        json.dump(status_data, f, indent=2, ensure_ascii=False)


def update_session(session_name: str, cwd: str, new_status: str, increment_replan: bool = False, thread_id: str | None = None) -> dict:
    if new_status not in VALID_STATUSES:
        return {"error": f"Invalid status: {new_status}. Valid: {VALID_STATUSES}"}

    status_data = read_status(session_name, cwd)
    if status_data is None:
        return {"error": f"Session not found: {session_name}"}

    current = status_data.get("status", "pending")

    if new_status != "failed":
        if not (current in REPLAN_PAIR and new_status in REPLAN_PAIR):
            current_order = TRANSITION_ORDER.get(current, -1)
            new_order = TRANSITION_ORDER.get(new_status, -1)
            if new_order <= current_order:
                return {
                    "error": f"Cannot transition from '{current}' to '{new_status}'. "
                             f"States can only advance forward (use 'failed' to abort)."
                }

    status_data["status"] = new_status
    if increment_replan:
        status_data["replan_count"] = status_data.get("replan_count", 0) + 1
    if thread_id is not None:
        status_data["threadId"] = thread_id
    write_status(session_name, cwd, status_data)

    return {
        "session": session_name,
        "previous_status": current,
        "status": new_status,
        "replan_count": status_data.get("replan_count", 0),
        "threadId": status_data.get("threadId"),
    }


def get_session_status(session_name: str, cwd: str) -> dict:
    status_data = read_status(session_name, cwd)
    if status_data is None:
        return {"error": f"Session not found: {session_name}"}

    status_path = os.path.join(cwd, SRE_DIR_NAME, session_name, "tasks", "status.json")
    age = time.time() - os.path.getmtime(status_path)
    status_data["ttl_remaining_seconds"] = max(0, DEFAULT_TTL_SECONDS - age)
    status_data["expired"] = age > DEFAULT_TTL_SECONDS

    return status_data


def list_sessions(cwd: str) -> list[dict]:
    sre_dir = os.path.join(cwd, SRE_DIR_NAME)
    if not os.path.isdir(sre_dir):
        return []

    sessions = []
    for name in sorted(os.listdir(sre_dir)):
        session_dir = os.path.join(sre_dir, name)
        if not os.path.isdir(session_dir):
            continue
        status_data = read_status(name, cwd)
        if status_data is None:
            continue
        status_path = os.path.join(session_dir, "tasks", "status.json")
        age = time.time() - os.path.getmtime(status_path)
        sessions.append({
            "session": name,
            "status": status_data.get("status", "pending"),
            "created": status_data.get("created", ""),
            "updated": status_data.get("updated", ""),
            "age_seconds": round(age, 1),
            "expired": age > DEFAULT_TTL_SECONDS,
        })

    return sessions


def cleanup_sessions(cwd: str, ttl: int = DEFAULT_TTL_SECONDS) -> dict:
    sre_dir = os.path.join(cwd, SRE_DIR_NAME)
    if not os.path.isdir(sre_dir):
        return {"removed": [], "kept": []}

    sre_resolved = os.path.realpath(sre_dir)
    removed = []
    kept = []
    for name in os.listdir(sre_dir):
        session_dir = os.path.join(sre_dir, name)
        if not os.path.isdir(session_dir):
            continue
        resolved = os.path.realpath(session_dir)
        if not resolved.startswith(sre_resolved + os.sep):
            kept.append(f"{name} (skipped: path outside {SRE_DIR_NAME})")
            continue
        status_path = os.path.join(session_dir, "tasks", "status.json")
        if not os.path.isfile(status_path):
            # Safe: session_dir is validated to be within sre_dir via realpath check above.
            shutil.rmtree(session_dir)
            removed.append({"session": name, "reason": "missing status.json"})
            continue
        age = time.time() - os.path.getmtime(status_path)
        if age > ttl:
            # Safe: session_dir is validated to be within sre_dir via realpath check above.
            shutil.rmtree(session_dir)
            removed.append({"session": name, "reason": f"expired (age: {round(age)}s > {ttl}s)"})
        else:
            kept.append(name)

    return {"removed": removed, "kept": kept}


def _read_json_file(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _load_starops_raw(cwd: str):
    """Load and merge the raw STAROps config dict.

    Returns (merged_dict, source, config_path, project_config_path).
    """
    merged: dict = {}
    source = None
    config_path = None

    project_config_path = Path(cwd) / STAROPS_CONFIG_DIR / STAROPS_CONFIG_FILE
    project_config = _read_json_file(project_config_path)
    if project_config:
        merged.update(project_config)
        source = "project_config"
        config_path = str(project_config_path)

    return merged, source, config_path, project_config_path


def _normalize_accounts(raw: dict) -> list:
    """Extract the account list from a raw config dict.

    New format uses an ``accounts`` array. Old flat format (top-level
    uid/employeeId/workspace) is downgraded to a single-account list.
    """
    accounts = raw.get("accounts")
    result = []
    if isinstance(accounts, list) and accounts:
        for a in accounts:
            if not isinstance(a, dict):
                continue
            result.append({
                "uid": str(a.get("uid", "")).strip(),
                "profile": str(a.get("profile", "")).strip(),
                "employeeId": str(a.get("employeeId", "")).strip(),
                "workspace": str(a.get("workspace", "")).strip(),
            })
        return result

    # Backward-compatible old flat single-account format.
    uid = str(raw.get("uid", "")).strip()
    employee = str(raw.get("employeeId", "")).strip()
    workspace = str(raw.get("workspace", "")).strip()
    profile = str(raw.get("profile", "")).strip()
    if uid or employee or workspace:
        result.append({
            "uid": uid,
            "profile": profile,
            "employeeId": employee,
            "workspace": workspace,
        })
    return result


def _resolve_account(cwd: str, uid: str | None = None) -> dict | None:
    """Return the account matching ``uid`` (or the default first account)."""
    raw, _, _, _ = _load_starops_raw(cwd)
    accounts = _normalize_accounts(raw)
    if not accounts:
        return None
    if uid:
        for a in accounts:
            if a["uid"] == uid:
                return a
        return None
    return accounts[0]


def _upsert_account(accounts: list, uid: str, profile=None, employee_id=None, workspace=None):
    """Insert or update an account entry in-place. Returns (account, created).

    ``None`` fields are left untouched on update.
    """
    for a in accounts:
        if str(a.get("uid", "")).strip() == uid:
            if profile is not None:
                a["profile"] = profile
            if employee_id is not None:
                a["employeeId"] = employee_id
            if workspace is not None:
                a["workspace"] = workspace
            return a, False
    new_account = {
        "uid": uid,
        "profile": profile or "",
        "employeeId": employee_id or "",
        "workspace": workspace or "",
    }
    accounts.append(new_account)
    return new_account, True


def _load_config_with_accounts(target_path: Path) -> dict:
    """Read the config, migrating old flat format into an ``accounts`` list.

    Implements the read side of read-modify-write so concurrent callers do
    not drop entries added by others.
    """
    existing = _read_json_file(target_path)
    accounts = existing.get("accounts")
    if not isinstance(accounts, list):
        migrated = _normalize_accounts(existing)
        existing = {"accounts": migrated}
    return existing


@contextmanager
def _config_lock(target_path: Path):
    """Exclusive file lock covering the whole read-modify-write cycle.

    Serializes concurrent account-add/update/delete against a dedicated lock
    file (``.starops/config.lock``) so that no entries are lost by a
    read-before / write-after interleaving. The lock is always released via
    try/finally, even on exceptions.
    """
    lock_path = target_path.parent / STAROPS_CONFIG_LOCK
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if fcntl is None:
        # No cross-process locking primitive available on this platform.
        # Fail loudly instead of silently allowing a racy read-modify-write.
        raise RuntimeError(
            "fcntl is unavailable on this platform; cross-process config "
            "locking is not supported. Run on a POSIX system (Linux/macOS)."
        )
    lock_file = os.fdopen(_secure_write_open(lock_path), "w")
    try:
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            lock_file.close()


def _write_starops_config_atomic(target_path: Path, data: dict) -> None:
    """Atomically write the config via a unique tmp file + rename.

    Each writer uses a per-process, unique temp name
    (``config.<pid>.<uuid>.tmp``) so concurrent processes never share and
    clobber the same tmp file (which previously caused ENOENT on rename).
    The tmp file is cleaned up if anything fails. Credentials are never
    stored here.
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.parent / f"{STAROPS_CONFIG_FILE}.{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        fd = _secure_write_open(tmp_path)
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
        os.chmod(target_path, 0o600)
    except OSError:
        try:
            if tmp_path.exists():
                resolved_tmp = tmp_path.resolve()
                resolved_parent = target_path.parent.resolve()
                if str(resolved_tmp).startswith(str(resolved_parent) + os.sep):
                    # Safe: tmp_path is validated to be within target_path.parent via resolve check above.
                    tmp_path.unlink()
        except OSError:
            pass
        raise


def _validate_account(account: dict) -> dict:
    """Lightweight validation: STAROps required fields + profile credentials."""
    checks = {}

    missing = [k for k in STAROPS_REQUIRED_KEYS if not str(account.get(k, "")).strip()]
    checks["starops_fields"] = {
        "status": "pass" if not missing else "fail",
        "missing_keys": missing,
    }

    profile = str(account.get("profile", "")).strip()
    if not profile:
        current = _get_aliyun_current_profile()
        checks["profile_credentials"] = {
            "status": "warn",
            "profile": None,
            "note": f"no profile set; falls back to aliyun current '{current}'" if current
                    else "no profile set and no aliyun current profile",
        }
    else:
        info = _lookup_aliyun_profile(profile)
        if info is None:
            checks["profile_credentials"] = {
                "status": "fail",
                "profile": profile,
                "note": "profile not found in ~/.aliyun/config.json",
            }
        else:
            checks["profile_credentials"] = {
                "status": "pass" if info["has_credentials"] else "fail",
                "profile": profile,
                "mode": info["mode"],
                "has_credentials": info["has_credentials"],
            }

    overall = "pass"
    for c in checks.values():
        if c["status"] == "fail":
            overall = "fail"
            break
        if c["status"] == "warn" and overall == "pass":
            overall = "warn"
    return {"status": overall, "checks": checks}


def check_starops_config(cwd: str) -> dict:
    merged, source, config_path, project_config_path = _load_starops_raw(cwd)
    accounts = _normalize_accounts(merged)

    # Compute credential mode for auto-selection indication
    env_creds = _detect_env_credentials()
    cred_mode = _compute_credential_mode(_enumerate_aliyun_profiles(), env_creds)

    # Select the default account (first in accounts[]).
    selected = accounts[0] if accounts else None

    def _not_available(missing_keys):
        searched_paths = []
        if project_config_path.is_file():
            searched_paths.append(str(project_config_path))
        else:
            searched_paths.append(f"{project_config_path} (not found)")
        return {
            "available": False,
            "source": None,
            "config_path": None,
            "accounts": accounts,
            "credential_mode": cred_mode,
            "missing_keys": missing_keys,
            "searched_paths": searched_paths,
        }

    if selected is None:
        return _not_available(list(STAROPS_REQUIRED_KEYS))

    missing = [k for k in STAROPS_REQUIRED_KEYS if not str(selected.get(k, "")).strip()]
    if missing:
        return _not_available(missing)

    profile = str(selected.get("profile", "")).strip()
    if profile:
        profile_source = "config"
    else:
        current = _get_aliyun_current_profile()
        profile = current or ""
        profile_source = "aliyun_current" if current else "none"

    return {
        "available": True,
        "credential_mode": cred_mode,
        "auto_selected": cred_mode == "single",
        "source": source,
        "config_path": config_path,
        "accounts": accounts,
        "employeeId": str(selected["employeeId"]).strip(),
        "workspace": str(selected["workspace"]).strip(),
        "uid": str(selected["uid"]).strip(),
        "profile": profile,
        "profile_source": profile_source,
        "missing_keys": [],
    }


def list_accounts(cwd: str) -> dict:
    raw, source, config_path, _ = _load_starops_raw(cwd)
    accounts = _normalize_accounts(raw)
    current = _get_aliyun_current_profile() or ""
    out = []
    for a in accounts:
        configured_profile = a["profile"]
        effective = configured_profile or current
        out.append({
            "uid": a["uid"],
            "profile": configured_profile or None,
            "effective_profile": effective or None,
            "profile_source": "config" if configured_profile else ("aliyun_current" if current else "none"),
            "employeeId": a["employeeId"],
            "workspace": a["workspace"],
        })
    return {
        "accounts": out,
        "count": len(out),
        "source": source,
        "config_path": config_path,
    }


def set_starops_config(cwd: str, scope: str, employee_id: str, workspace: str, uid: str, profile: str | None = None) -> dict:
    if scope != "project":
        return {"error": f"Invalid scope: {scope}. Only 'project' scope is supported (config stored in project local directory)."}
    target_path = Path(cwd) / STAROPS_CONFIG_DIR / STAROPS_CONFIG_FILE

    try:
        with _config_lock(target_path):
            config = _load_config_with_accounts(target_path)
            account, created = _upsert_account(
                config["accounts"], uid,
                profile=(profile if profile is not None else None),
                employee_id=employee_id,
                workspace=workspace,
            )
            _write_starops_config_atomic(target_path, config)
    except OSError as e:
        return {"error": f"Failed to write config: {e}"}

    return {
        "written": True,
        "created": created,
        "config_path": str(target_path),
        "scope": scope,
        "values": {
            "uid": uid,
            "profile": account.get("profile", ""),
            "employeeId": employee_id,
            "workspace": workspace,
        },
    }


def _account_write(cwd: str, action: str, uid: str, profile, employee_id, workspace) -> dict:
    if not uid:
        return {"error": "--uid is required"}
    profile = None if profile is None else profile.strip()
    target_path = Path(cwd) / STAROPS_CONFIG_DIR / STAROPS_CONFIG_FILE

    try:
        with _config_lock(target_path):
            config = _load_config_with_accounts(target_path)
            accounts = config["accounts"]
            existing = None
            for a in accounts:
                if str(a.get("uid", "")).strip() == uid:
                    existing = a
                    break
            if action == "update" and existing is None:
                return {"error": f"UID not found in accounts (use 'account-add'): {uid}"}

            account, created = _upsert_account(
                accounts, uid,
                profile=(profile if profile is not None else None),
                employee_id=(employee_id if employee_id is not None else None),
                workspace=(workspace if workspace is not None else None),
            )
            _write_starops_config_atomic(target_path, config)
    except OSError as e:
        return {"error": f"Failed to write config: {e}"}

    return {
        "action": action,
        "uid": uid,
        "created": created,
        "account": account,
        "config_path": str(target_path),
        "validation": _validate_account(account),
    }


def account_add(cwd: str, uid: str, profile, employee_id, workspace) -> dict:
    return _account_write(cwd, "add", uid, profile, employee_id, workspace)


def account_update(cwd: str, uid: str, profile, employee_id, workspace) -> dict:
    return _account_write(cwd, "update", uid, profile, employee_id, workspace)


def account_delete(cwd: str, uid: str, confirm: bool = False) -> dict:
    if not uid:
        return {"error": "--uid is required"}
    target_path = Path(cwd) / STAROPS_CONFIG_DIR / STAROPS_CONFIG_FILE

    try:
        with _config_lock(target_path):
            config = _load_config_with_accounts(target_path)
            accounts = config["accounts"]
            removed = None
            remaining = []
            for a in accounts:
                if str(a.get("uid", "")).strip() == uid and removed is None:
                    removed = a
                else:
                    remaining.append(a)
            if removed is None:
                return {"error": f"UID not found in accounts: {uid}"}

            config["accounts"] = remaining
            _write_starops_config_atomic(target_path, config)
    except OSError as e:
        return {"error": f"Failed to write config: {e}"}

    result = {
        "action": "delete",
        "uid": uid,
        "removed_account": removed,
        "config_path": str(target_path),
        "accounts_remaining": len(remaining),
    }

    profile = str(removed.get("profile", "")).strip()
    if profile:
        if confirm:
            print(
                f"WARNING: This will permanently delete aliyun CLI profile '{profile}' and remove the UID mapping.",
                file=sys.stderr,
            )
        # confirm=True only when user passed --confirm to account-remove; the function itself also guards.
        result["profile_deletion"] = _aliyun_configure_delete(profile, confirm=bool(confirm))
    else:
        result["profile_deletion"] = {"deleted": False, "note": "no profile associated with this UID"}
    return result


def _profile_has_credentials(profile: dict) -> bool:
    mode = str(profile.get("mode", "AK")).upper()
    if mode == "AK":
        return bool(profile.get("access_key_id") and profile.get("access_key_secret"))
    if mode == "STS":
        return bool(
            profile.get("access_key_id")
            and profile.get("access_key_secret")
            and profile.get("sts_token")
        )
    if mode in ("RAMROLEARN", "ECSRAMROLE", "OIDC", "CREDENTIALURI",
                "RAMROLEARNWITHROLENAME", "CHAINABLERAMROLEARN", "CLOUDSSO",
                "OAUTH", "EXTERNAL"):
        return True
    return bool(profile.get("access_key_id") and profile.get("access_key_secret"))


def _load_aliyun_config() -> dict | None:
    if not ALIYUN_CONFIG_PATH.is_file():
        return None
    try:
        with open(ALIYUN_CONFIG_PATH, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _get_aliyun_current_profile() -> str:
    config = _load_aliyun_config()
    if not config:
        return ""
    return str(config.get("current", ""))


def _enumerate_aliyun_profiles() -> list:
    config = _load_aliyun_config()
    if not config:
        return []
    profiles = config.get("profiles")
    if not isinstance(profiles, list):
        return []
    out = []
    for p in profiles:
        if not isinstance(p, dict):
            continue
        out.append({
            "name": p.get("name", ""),
            "mode": str(p.get("mode", "AK")).upper(),
            "has_credentials": _profile_has_credentials(p),
        })
    return out


def _lookup_aliyun_profile(name: str) -> dict | None:
    for p in _enumerate_aliyun_profiles():
        if p["name"] == name:
            return p
    return None


def _detect_env_credentials() -> dict | None:
    """Check ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET env vars.

    SECURITY: Only the access key ID (a non-secret identifier) is returned.
    The secret is read solely for a boolean presence check and is never
    returned, logged, or transmitted to any endpoint.
    """
    ak_id = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", "").strip()
    ak_secret = os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", "").strip()
    if ak_id and ak_secret:
        return {"source": "env_vars", "access_key_id": ak_id}
    return None


def _compute_credential_mode(profiles: list, env_creds: dict | None) -> str:
    """Determine credential mode: 'single', 'multi', or 'none'.

    - 0 profiles + env vars → 'single' (env var mode)
    - 1 profile → 'single' (profile takes priority over env vars)
    - >=2 profiles → 'multi'
    - 0 profiles + no env vars → 'none'
    """
    profile_count = len([p for p in profiles if p.get("has_credentials")])
    if profile_count == 0 and env_creds:
        return "single"
    elif profile_count == 1:
        return "single"
    elif profile_count >= 2:
        return "multi"
    else:
        return "none"


def _auto_resolve_uid(profile: str | None = None) -> str | None:
    """Resolve UID via `aliyun sts get-caller-identity` (read-only).

    SECURITY: This executes a strictly read-only STS API call that returns
    the caller's AccountId. It does not modify any cloud resources or
    configurations. Called during user-initiated session init only.
    """
    _validate_profile_name(profile)
    cli = shutil.which("aliyun")
    if cli is None:
        return None
    cmd = [cli, "sts", "get-caller-identity"]
    if profile:
        cmd += ["--profile", profile]
    try:
        # Read-only STS call — returns caller identity, no resource modification.
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
        return str(data.get("AccountId", ""))
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None


def _aliyun_configure_delete(profile, confirm: bool = False) -> dict:
    """Delete an aliyun CLI profile. DESTRUCTIVE — requires explicit confirm=True."""
    _validate_profile_name(profile)
    if not confirm:
        return {
            "deleted": False,
            "note": f"aliyun profile '{profile}' kept; pass --confirm to also delete it",
            "manual_hint": f"aliyun configure delete --profile {profile}",
        }
    cli = shutil.which("aliyun")
    if cli is None:
        return {"deleted": False, "error": "aliyun CLI not installed", "remediation": ALIYUN_NOT_INSTALLED_REMEDIATION}
    try:
        # Destructive operation — caller must have obtained explicit user confirmation via --confirm flag.
        proc = subprocess.run([cli, "configure", "delete", "--profile", profile], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        return {"deleted": False, "error": f"aliyun configure delete failed: {e}"}
    return {
        "deleted": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "profile": profile,
    }


def check_aliyun_cli() -> dict:
    cli_path = shutil.which("aliyun")
    config_path_str = str(ALIYUN_CONFIG_PATH)

    if cli_path is None:
        return {
            "installed": False,
            "cli_path": None,
            "configured": False,
            "config_path": config_path_str,
            "active_profile": None,
            "has_credentials": False,
            "profiles": [],
            "details": "aliyun CLI not found in PATH",
            "remediation": ALIYUN_NOT_INSTALLED_REMEDIATION,
        }

    if not ALIYUN_CONFIG_PATH.is_file():
        return {
            "installed": True,
            "cli_path": cli_path,
            "configured": False,
            "config_path": config_path_str,
            "active_profile": None,
            "has_credentials": False,
            "profiles": [],
            "details": "aliyun CLI config file not found",
            "remediation": ALIYUN_NOT_CONFIGURED_REMEDIATION,
        }

    config = _load_aliyun_config()
    if config is None:
        return {
            "installed": True,
            "cli_path": cli_path,
            "configured": False,
            "config_path": config_path_str,
            "active_profile": None,
            "has_credentials": False,
            "profiles": [],
            "details": "aliyun CLI config parse error",
            "remediation": ALIYUN_NOT_CONFIGURED_REMEDIATION,
        }

    profiles = _enumerate_aliyun_profiles()
    if not profiles:
        return {
            "installed": True,
            "cli_path": cli_path,
            "configured": False,
            "config_path": config_path_str,
            "active_profile": None,
            "has_credentials": False,
            "profiles": [],
            "details": "aliyun CLI no profiles configured",
            "remediation": ALIYUN_NOT_CONFIGURED_REMEDIATION,
        }

    current = str(config.get("current", ""))
    active = None
    for p in profiles:
        if p["name"] == current:
            active = p
            break
    if active is None:
        active = profiles[0]

    profile_name = active["name"]
    mode = active["mode"]
    has_creds = active["has_credentials"]

    if not has_creds:
        return {
            "installed": True,
            "cli_path": cli_path,
            "configured": False,
            "config_path": config_path_str,
            "active_profile": profile_name,
            "has_credentials": False,
            "profiles": profiles,
            "details": f"aliyun CLI profile '{profile_name}' (mode={mode}) missing credentials",
            "remediation": ALIYUN_NOT_CONFIGURED_REMEDIATION,
        }

    return {
        "installed": True,
        "cli_path": cli_path,
        "configured": True,
        "config_path": config_path_str,
        "active_profile": profile_name,
        "has_credentials": True,
        "profiles": profiles,
        "details": "OK",
        "remediation": None,
    }


def check_python_deps() -> dict:
    packages = {}
    missing = []
    for dep in PYTHON_DEPS:
        try:
            # Safe: dep iterates over the hardcoded PYTHON_DEPS tuple
            # ("requests", "alibabacloud_credentials") — never external input.
            importlib.import_module(dep)
            packages[dep] = {"available": True}
        except ImportError:
            packages[dep] = {"available": False}
            missing.append(dep)

    if missing:
        pip_names = ", ".join(m.replace("_", "-") for m in missing)
        return {
            "all_available": False,
            "packages": packages,
            "details": f"missing: {pip_names}",
            "remediation": PYTHON_DEPS_REMEDIATION,
        }

    return {
        "all_available": True,
        "packages": packages,
        "details": "OK",
        "remediation": None,
    }


def check_environment(cwd: str) -> dict:
    aliyun = check_aliyun_cli()
    starops_raw = check_starops_config(cwd)
    deps = check_python_deps()

    # Compute credential mode from profiles + env vars
    env_creds = _detect_env_credentials()
    credential_mode = _compute_credential_mode(aliyun.get("profiles", []), env_creds)
    aliyun["credential_mode"] = credential_mode
    aliyun["env_credentials"] = env_creds

    aliyun_pass = aliyun["installed"] and aliyun["configured"]
    aliyun_check = {
        "status": "pass" if aliyun_pass else "fail",
        **aliyun,
    }

    starops_pass = bool(starops_raw.get("available"))
    starops_check = {
        "status": "pass" if starops_pass else "fail",
        "available": starops_raw.get("available", False),
        "source": starops_raw.get("source"),
        "config_path": starops_raw.get("config_path"),
        "missing_keys": starops_raw.get("missing_keys", []),
        "details": "OK" if starops_pass else "STAROps config missing",
        "remediation": None if starops_pass else STAROPS_MISSING_REMEDIATION,
    }

    deps_pass = deps["all_available"]
    deps_check = {
        "status": "pass" if deps_pass else "fail",
        **deps,
    }

    # Cross-check every account's profile against the enumerated aliyun
    # profiles: report accounts whose profile is missing or lacks credentials.
    profile_index = {p["name"]: p for p in aliyun.get("profiles", [])}
    current_profile = aliyun.get("active_profile") or ""
    account_results = []
    accounts_pass = True
    for a in starops_raw.get("accounts", []):
        prof = str(a.get("profile", "")).strip() or current_profile
        entry = {
            "uid": a.get("uid", ""),
            "profile": prof or None,
            "employeeId": a.get("employeeId", ""),
            "workspace": a.get("workspace", ""),
        }
        if not prof:
            entry["status"] = "fail"
            entry["reason"] = "no profile set and no aliyun current profile"
            accounts_pass = False
        elif prof not in profile_index:
            entry["status"] = "fail"
            entry["reason"] = f"profile '{prof}' not found in aliyun config"
            accounts_pass = False
        elif not profile_index[prof]["has_credentials"]:
            entry["status"] = "fail"
            entry["reason"] = f"profile '{prof}' missing valid credentials"
            accounts_pass = False
        else:
            entry["status"] = "pass"
        account_results.append(entry)

    invalid_accounts = [e for e in account_results if e["status"] == "fail"]
    accounts_check = {
        "status": "pass" if accounts_pass else "fail",
        "count": len(account_results),
        "accounts": account_results,
        "invalid": invalid_accounts,
        "details": "OK" if accounts_pass else f"{len(invalid_accounts)} invalid account profiles",
        "remediation": None if accounts_pass else "associate valid profiles via account-add/account-update",
    }

    failures = sum(1 for c in (aliyun_pass, starops_pass, deps_pass, accounts_pass) if not c)

    return {
        "status": "pass" if failures == 0 else "fail",
        "critical_failures": failures,
        "credential_mode": credential_mode,
        "checks": {
            "aliyun_cli": aliyun_check,
            "starops": starops_check,
            "python_deps": deps_check,
            "accounts": accounts_check,
        },
    }


def starops_cap_cache_get(uid: str, employee_id: str, workspace: str) -> dict:
    cache_key = f"{uid}|{employee_id}|{workspace}"
    ttl = STAROPS_CACHE_DEFAULT_TTL

    if not STAROPS_CACHE_FILE.is_file():
        return {"hit": False, "expired": True}

    try:
        with open(STAROPS_CACHE_FILE, "r") as f:
            cache = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"hit": False, "expired": True}

    entry = cache.get(cache_key)
    if not entry:
        return {"hit": False, "expired": True}

    timestamp = entry.get("timestamp", 0)
    age = time.time() - timestamp
    expired = age > ttl

    if expired:
        return {
            "hit": True,
            "expired": True,
            "cached_at": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
            "age_seconds": round(age),
        }

    return {
        "hit": True,
        "expired": False,
        "capabilities_text": entry.get("capabilities_text", ""),
        "skills_count": entry.get("skills_count", 0),
        "skills_list": entry.get("skills_list", []),
        "cached_at": datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(),
        "ttl_remaining": round(ttl - age),
    }


def starops_cap_cache_set(
    uid: str, employee_id: str, workspace: str, capabilities_text: str,
    skills_count: int, skills_list: list,
) -> dict:
    ttl = STAROPS_CACHE_DEFAULT_TTL

    cache_key = f"{uid}|{employee_id}|{workspace}"

    cache = {}
    if STAROPS_CACHE_FILE.is_file():
        try:
            with open(STAROPS_CACHE_FILE, "r") as f:
                cache = json.load(f)
        except (OSError, json.JSONDecodeError):
            cache = {}

    cache[cache_key] = {
        "timestamp": time.time(),
        "ttl_seconds": ttl,
        "capabilities_text": capabilities_text,
        "skills_count": skills_count,
        "skills_list": skills_list,
    }

    STAROPS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    tmp_path = STAROPS_CACHE_FILE.with_suffix(".tmp")
    fd = _secure_write_open(tmp_path)
    with os.fdopen(fd, "w") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)
    tmp_path.rename(STAROPS_CACHE_FILE)
    os.chmod(STAROPS_CACHE_FILE, 0o600)

    return {
        "cached": True,
        "cache_path": str(STAROPS_CACHE_FILE),
        "ttl_seconds": ttl,
        "skills_count": skills_count,
    }


WORKFLOW_EPILOG = """Mandatory Workflow: env-check -> list-accounts -> init -> starops_manager.py create-thread -> starops_manager.py chat
Run 'python3 session_manager.py workflow' for details.
DO NOT substitute with direct aliyun CLI calls."""


def cmd_workflow() -> dict:
    """Print the mandatory command sequence as JSON."""
    return {
        "mandatory_sequence": [
            {"step": 1, "script": "session_manager.py", "command": "env-check", "must": True, "description": "Check all environment prerequisites"},
            {"step": 2, "script": "session_manager.py", "command": "list-accounts", "must": True, "description": "List all configured UIDs and their profile/employeeId mapping"},
            {"step": 3, "script": "session_manager.py", "command": "init", "must": True, "description": "Initialize a new session bound to a UID"},
            {"step": 4, "script": "starops_manager.py", "command": "create-thread", "must": True, "condition": "STAROps available", "description": "Create STAROps diagnostic Thread"},
            {"step": 5, "script": "starops_manager.py", "command": "chat", "must": True, "condition": "STAROps available", "description": "Send diagnostic query via STAROps SSE stream"},
        ],
        "forbidden": [
            "direct aliyun CLI substitution (e.g. aliyun ecs describe-instances instead of starops_manager.py chat)",
            "skipping any MUST step",
            "curl/wget API calls instead of built-in scripts",
            "using aliyun CLI as primary diagnosis when STAROps is available",
        ],
        "note": "These commands are NON-NEGOTIABLE. Execute in order before any other action for ANY SRE/diagnostic/inspection query.",
    }


def _append_trace(cwd: str, command: str, args_dict: dict, result: dict | None, exit_code: int) -> None:
    """Append an execution trace record to .aliyun-sre/execution-trace.jsonl."""
    sre_dir = os.path.join(cwd, SRE_DIR_NAME)
    if not os.path.isdir(sre_dir):
        os.makedirs(sre_dir, exist_ok=True)
    trace_path = os.path.join(sre_dir, "execution-trace.jsonl")
    session = None
    if isinstance(result, dict):
        session = result.get("session")
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "script": "session_manager.py",
        "command": command,
        "args": args_dict,
        "session": session,
        "exit_code": exit_code,
        "success": exit_code == 0,
    }
    fd = _secure_write_open(trace_path, append=True)
    with os.fdopen(fd, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SRE session lifecycle manager",
        epilog=WORKFLOW_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    p_init = subparsers.add_parser("init", help="Initialize a new session")
    p_init.add_argument("--cwd", default=".", help="Working directory")
    p_init.add_argument("--uid", help="Alibaba Cloud account UID to pin this session to")
    p_init.add_argument("--profile", help="aliyun CLI profile name (falls back to config/current)")
    p_init.add_argument("--employee-id", help="STAROps Digital Employee ID")
    p_init.add_argument("--workspace", help="STAROps workspace identifier")

    p_update = subparsers.add_parser("update", help="Update session status")
    p_update.add_argument("--session", required=True, help="Session name")
    p_update.add_argument("--cwd", default=".", help="Working directory")
    p_update.add_argument("--status", required=True, choices=VALID_STATUSES, help="New status")
    p_update.add_argument("--thread-id", dest="thread_id", help="Persist STAROps threadId to status.json")
    p_update.add_argument("--increment-replan", action="store_true", help="Increment replan_count")

    p_status = subparsers.add_parser("status", help="Query session status")
    p_status.add_argument("--session", required=True, help="Session name")
    p_status.add_argument("--cwd", default=".", help="Working directory")

    p_list = subparsers.add_parser("list", help="List all sessions")
    p_list.add_argument("--cwd", default=".", help="Working directory")

    p_cleanup = subparsers.add_parser("cleanup", help="Remove expired sessions")
    p_cleanup.add_argument("--cwd", default=".", help="Working directory")
    p_cleanup.add_argument("--ttl", type=int, default=DEFAULT_TTL_SECONDS, help="TTL in seconds")

    p_check = subparsers.add_parser("configure-check", help="Check STAROps config availability")
    p_check.add_argument("--cwd", default=".", help="Working directory")

    p_set = subparsers.add_parser("configure-set", help="Write STAROps config")
    p_set.add_argument("--cwd", default=".", help="Working directory")
    p_set.add_argument("--scope", choices=["project"], default="project", help="Config scope (project only, config stored in project local directory)")
    p_set.add_argument("--employee-id", required=True, help="STAROps Digital Employee ID")
    p_set.add_argument("--workspace", default=None, help="STAROps workspace identifier (optional)")
    p_set.add_argument("--uid", required=True, help="Alibaba Cloud account UID owning the workspace")
    p_set.add_argument("--profile", help="aliyun CLI profile name to associate with this UID")

    p_accts = subparsers.add_parser("list-accounts", help="List all configured UIDs and their profile/employeeId/workspace mapping")
    p_accts.add_argument("--cwd", default=".", help="Working directory")

    def _add_account_common(p):
        p.add_argument("--cwd", default=".", help="Working directory")
        p.add_argument("--uid", required=True, help="Alibaba Cloud account UID")
        p.add_argument("--profile", help="aliyun CLI profile name to associate (credentials must be configured externally via 'aliyun configure')")

    p_acc_add = subparsers.add_parser("account-add", help="Add a UID->profile->digital-human mapping")
    _add_account_common(p_acc_add)
    p_acc_add.add_argument("--employee-id", required=True, help="STAROps Digital Employee ID")
    p_acc_add.add_argument("--workspace", default=None, help="STAROps workspace identifier (optional)")

    p_acc_upd = subparsers.add_parser("account-update", help="Update an existing UID's profile or digital-human mapping")
    _add_account_common(p_acc_upd)
    p_acc_upd.add_argument("--employee-id", help="STAROps Digital Employee ID")
    p_acc_upd.add_argument("--workspace", help="STAROps workspace identifier")

    p_acc_del = subparsers.add_parser("account-delete", help="Remove a UID mapping. Use --confirm to ALSO delete the associated aliyun CLI profile (DESTRUCTIVE).")
    p_acc_del.add_argument("--cwd", default=".", help="Working directory")
    p_acc_del.add_argument("--uid", required=True, help="Alibaba Cloud account UID to remove")
    p_acc_del.add_argument("--confirm", action="store_true", help="Also delete the associated aliyun CLI profile (DESTRUCTIVE — cannot be undone).")

    p_env = subparsers.add_parser("env-check", help="Check all environment prerequisites")
    p_env.add_argument("--cwd", default=".", help="Working directory")

    p_cap_get = subparsers.add_parser("starops-cap-cache-get", help="Get cached STAROps capabilities")
    p_cap_get.add_argument("--cwd", default=".", help="Working directory (unused; accepted for CLI compatibility)")
    p_cap_get.add_argument("--uid", default="", help="Alibaba Cloud account UID (cache key component)")
    p_cap_get.add_argument("--employee-id", required=True, help="STAROps Digital Employee ID")
    p_cap_get.add_argument("--workspace", default="", help="STAROps workspace identifier (optional, part of cache key)")

    p_cap_set = subparsers.add_parser("starops-cap-cache-set", help="Cache STAROps capabilities")
    p_cap_set.add_argument("--cwd", default=".", help="Working directory (unused; accepted for CLI compatibility)")
    p_cap_set.add_argument("--uid", default="", help="Alibaba Cloud account UID (cache key component)")
    p_cap_set.add_argument("--employee-id", required=True, help="STAROps Digital Employee ID")
    p_cap_set.add_argument("--workspace", default="", help="STAROps workspace identifier (optional, part of cache key)")
    p_cap_set.add_argument("--capabilities-text", help="Capabilities text (use --capabilities-text-stdin for long text)")
    p_cap_set.add_argument("--capabilities-text-stdin", action="store_true", help="Read capabilities text from stdin")
    p_cap_set.add_argument("--skills-count", type=int, default=0, help="Number of skills discovered")
    p_cap_set.add_argument("--skills-list", default="[]", help="JSON array of {name, description} objects")

    subparsers.add_parser("workflow", help="Print the mandatory command sequence (for agent self-discovery)")

    args = parser.parse_args()

    if args.command == "init":
        result = init_session(
            args.cwd,
            uid=getattr(args, "uid", None),
            profile=getattr(args, "profile", None),
            employee_id=getattr(args, "employee_id", None),
            workspace=getattr(args, "workspace", None),
        )
    elif args.command == "update":
        result = update_session(args.session, args.cwd, args.status, args.increment_replan, args.thread_id)
    elif args.command == "status":
        result = get_session_status(args.session, args.cwd)
    elif args.command == "list":
        result = list_sessions(args.cwd)
    elif args.command == "cleanup":
        result = cleanup_sessions(args.cwd, args.ttl)
    elif args.command == "configure-check":
        result = check_starops_config(args.cwd)
    elif args.command == "configure-set":
        result = set_starops_config(args.cwd, args.scope, args.employee_id, args.workspace, args.uid, profile=args.profile)
    elif args.command == "list-accounts":
        result = list_accounts(args.cwd)
    elif args.command in ("account-add", "account-update"):
        if args.command == "account-add":
            result = account_add(args.cwd, args.uid, args.profile, args.employee_id, args.workspace)
        else:
            result = account_update(args.cwd, args.uid, args.profile, args.employee_id, args.workspace)
    elif args.command == "account-delete":
        result = account_delete(args.cwd, args.uid, confirm=args.confirm)
    elif args.command == "env-check":
        result = check_environment(args.cwd)
    elif args.command == "starops-cap-cache-get":
        result = starops_cap_cache_get(args.uid, args.employee_id, args.workspace)
    elif args.command == "starops-cap-cache-set":
        if args.capabilities_text_stdin:
            cap_text = sys.stdin.read()
        else:
            cap_text = args.capabilities_text or ""
        try:
            s_list = json.loads(args.skills_list)
        except json.JSONDecodeError:
            s_list = []
        result = starops_cap_cache_set(
            args.uid, args.employee_id, args.workspace, cap_text,
            args.skills_count, s_list,
        )
    elif args.command == "workflow":
        result = cmd_workflow()
    else:
        parser.print_help()
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    exit_code = 0
    if isinstance(result, dict):
        if "error" in result:
            exit_code = 1
        if result.get("status") == "fail":
            exit_code = 1
    trace_cwd = getattr(args, "cwd", None) or os.getcwd()
    _append_trace(trace_cwd, args.command, vars(args), result, exit_code)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
