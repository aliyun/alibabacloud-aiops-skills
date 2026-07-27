from __future__ import annotations

import json
import os
import stat
import tempfile
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fcntl

try:
    from .agenthub_command import format_agenthub_command
except ImportError:  # pragma: no cover - direct script execution
    from agenthub_command import format_agenthub_command


AGENTHUB_CONFIG_DIR = Path.home() / ".aliyun_agenthub"
AGENTHUB_CONFIG_FILE = AGENTHUB_CONFIG_DIR / "config.json"
DEFAULT_OAUTH_PROFILE = "aliyun_agenthub_oauth"
DEFAULT_AK_PROFILE = "aliyun_agenthub"
PROFILE_CANDIDATES = (DEFAULT_AK_PROFILE, DEFAULT_OAUTH_PROFILE)


class AgentHubProfileError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProfileCredentials:
    profile_name: str
    mode: str
    access_key_id: str
    access_key_secret: str
    security_token: str | None = None


def default_config_path() -> Path:
    override = os.environ.get("ALIYUN_AGENTHUB_CONFIG_FILE", "").strip()
    return Path(override).expanduser() if override else AGENTHUB_CONFIG_FILE


def ensure_private_config(config_path: Path | None = None) -> Path:
    path = config_path or default_config_path()
    _ensure_private_parent(path.parent)
    with _config_lock(path):
        try:
            path.lstat()
        except FileNotFoundError:
            _write_json_atomic_unlocked(path, {"current": "", "profiles": []})
        else:
            _validate_regular_owned_file(path)
    return path


def load_agenthub_config(*, config_path: Path | None = None, create: bool = False) -> dict[str, Any]:
    path = ensure_private_config(config_path) if create else (config_path or default_config_path())
    if not path.exists():
        raise AgentHubProfileError(f"AgentHub profile config file not found: {path}")
    return _load_config_unlocked(path)


def save_agenthub_config(config: dict[str, Any], *, config_path: Path | None = None) -> None:
    path = config_path or default_config_path()
    _ensure_private_parent(path.parent)
    normalized = {
        "current": str(config.get("current") or ""),
        "profiles": [profile for profile in config.get("profiles", []) if isinstance(profile, dict)],
    }
    with _config_lock(path):
        _write_json_atomic_unlocked(path, normalized)


def save_agenthub_profile(
    profile: dict[str, Any],
    *,
    config_path: Path | None = None,
    make_current: bool = True,
) -> None:
    name = str(profile.get("name") or "").strip()
    if not name:
        raise AgentHubProfileError("profile name is required")
    path = config_path or default_config_path()
    _ensure_private_parent(path.parent)
    with _config_lock(path):
        try:
            path.lstat()
        except FileNotFoundError:
            config = {"current": "", "profiles": []}
        else:
            config = _load_config_unlocked(path)
        profiles = [item for item in config.get("profiles", []) if isinstance(item, dict)]
        replaced = False
        for index, item in enumerate(profiles):
            if item.get("name") == name:
                profiles[index] = dict(profile)
                replaced = True
                break
        if not replaced:
            profiles.append(dict(profile))
        config["profiles"] = profiles
        if make_current:
            config["current"] = name
        _write_json_atomic_unlocked(
            path,
            {
                "current": str(config.get("current") or ""),
                "profiles": profiles,
            },
        )


def select_profile_name(config: dict[str, Any], explicit_profile: str | None = None) -> str:
    if explicit_profile:
        return explicit_profile
    profiles = {profile.get("name"): profile for profile in config.get("profiles", []) if isinstance(profile, dict)}
    current = str(config.get("current") or "").strip()
    ordered_candidates = [
        (DEFAULT_AK_PROFILE, {"ak"}),
        (current, {"ak"}),
        (DEFAULT_OAUTH_PROFILE, {"oauth"}),
        (current, {"oauth"}),
    ]
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for candidate, allowed_modes in ordered_candidates:
        if not candidate:
            continue
        key = (candidate, tuple(sorted(allowed_modes)))
        if key in seen:
            continue
        seen.add(key)
        if _profile_can_supply_credentials(profiles.get(candidate), allowed_modes=allowed_modes):
            return candidate
    if len(profiles) == 1:
        return next(iter(profiles.keys()))
    return DEFAULT_OAUTH_PROFILE


def find_profile(config: dict[str, Any], profile_name: str) -> dict[str, Any]:
    for profile in config.get("profiles", []):
        if isinstance(profile, dict) and profile.get("name") == profile_name:
            return dict(profile)
    raise AgentHubProfileError(f"selected profile does not exist: {profile_name}")


def credentials_from_profile(profile: dict[str, Any]) -> ProfileCredentials:
    name = str(profile.get("name") or "").strip()
    mode = str(profile.get("mode") or "AK")
    mode_lower = mode.lower()
    access_key_id = _required_profile_value(profile, "access_key_id", name)
    access_key_secret = _required_profile_value(profile, "access_key_secret", name)
    security_token = _string_or_none(profile.get("sts_token"))
    if mode_lower == "oauth":
        configure_command = format_agenthub_command(
            "configure_oauth",
            "--profile",
            name or DEFAULT_OAUTH_PROFILE,
        )
        if not security_token:
            raise AgentHubProfileError(
                f"OAuth profile {name} does not contain cached STS credentials; "
                f"run `{configure_command}` in a terminal first"
            )
        expiration = _parse_unix_time(profile.get("sts_expiration"))
        if not expiration or time.time() >= expiration - 60:
            raise AgentHubProfileError(
                f"OAuth profile {name} cached STS credentials are expired; "
                f"run `{configure_command}` in a terminal first"
            )
    elif mode_lower != "ak":
        raise AgentHubProfileError(
            f"profile {name} uses unsupported mode {mode}; only OAuth or AK mode is supported"
        )
    return ProfileCredentials(
        profile_name=name,
        mode=mode,
        access_key_id=access_key_id,
        access_key_secret=access_key_secret,
        security_token=security_token,
    )


def _profile_can_supply_credentials(
    profile: dict[str, Any] | None,
    *,
    allowed_modes: set[str] | None = None,
) -> bool:
    if not profile:
        return False
    mode = str(profile.get("mode") or "AK").lower()
    if allowed_modes is not None and mode not in allowed_modes:
        return False
    if mode == "ak":
        return bool(profile.get("access_key_id") and profile.get("access_key_secret"))
    if mode == "oauth":
        if profile.get("oauth_refresh_token") or profile.get("oauth_access_token"):
            return str(profile.get("oauth_site_type") or "").upper() == "CN"
        return bool(
            profile.get("access_key_id")
            and profile.get("access_key_secret")
            and profile.get("sts_token")
            and _parse_unix_time(profile.get("sts_expiration"))
        )
    return False


def _required_profile_value(profile: dict[str, Any], key: str, profile_name: str) -> str:
    value = _string_or_none(profile.get(key))
    if not value:
        raise AgentHubProfileError(f"profile {profile_name} is missing required field {key}")
    return value


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _parse_unix_time(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    if not text:
        return None
    try:
        from datetime import datetime

        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _load_config_unlocked(path: Path) -> dict[str, Any]:
    fd = _open_regular_owned_file(path)
    try:
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = -1
            data = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentHubProfileError(f"AgentHub profile config file is not valid JSON: {path}") from exc
    finally:
        if fd >= 0:
            os.close(fd)
    if not isinstance(data, dict):
        raise AgentHubProfileError(f"AgentHub profile config JSON is not an object: {path}")
    profiles = data.get("profiles")
    if profiles is None:
        data["profiles"] = []
    elif not isinstance(profiles, list):
        raise AgentHubProfileError("AgentHub profile config field profiles must be a list")
    data.setdefault("current", "")
    return data


def _ensure_private_parent(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
            raise AgentHubProfileError(f"unsafe AgentHub config directory: {path}")
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)


def _validate_regular_owned_file(path: Path) -> None:
    fd = _open_regular_owned_file(path)
    os.close(fd)


def _open_regular_owned_file(path: Path) -> int:
    before = path.lstat()
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
        ):
            raise AgentHubProfileError(f"unsafe AgentHub config file: {path}")
        os.fchmod(fd, 0o600)
        return fd
    except BaseException:
        os.close(fd)
        raise


@contextmanager
def _config_lock(path: Path):
    lock_path = path.with_name(f".{path.name}.lock")
    try:
        before = lock_path.lstat()
    except FileNotFoundError:
        before = None
    flags = os.O_RDWR | os.O_CREAT
    flags |= getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(lock_path, flags, 0o600)
    try:
        info = os.fstat(fd)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or (
                before is not None
                and (info.st_dev, info.st_ino) != (before.st_dev, before.st_ino)
            )
        ):
            raise AgentHubProfileError(f"unsafe AgentHub config lock: {lock_path}")
        after = lock_path.lstat()
        if (
            stat.S_ISLNK(after.st_mode)
            or (info.st_dev, info.st_ino) != (after.st_dev, after.st_ino)
        ):
            raise AgentHubProfileError(f"unsafe AgentHub config lock: {lock_path}")
        os.fchmod(fd, 0o600)
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


def _write_json_atomic_unlocked(path: Path, data: dict[str, Any]) -> None:
    try:
        _validate_regular_owned_file(path)
    except FileNotFoundError:
        pass
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.tmp.", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        tmp_path.unlink(missing_ok=True)
