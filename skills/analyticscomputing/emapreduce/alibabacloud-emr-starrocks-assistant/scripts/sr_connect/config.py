"""Read/write ~/.starrocks/{profile}.cnf — MySQL client compatible INI format.

Per-profile state lives in two files (both mode 600 under a 700 directory):
    {profile}.cnf      INI with [client] (pymysql-compatible) + [meta] section
    {profile}.grants   Raw SHOW GRANTS FOR CURRENT_USER() output, plain text
"""

from __future__ import annotations

import configparser
import os
import stat
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigNotFoundError


@dataclass
class ProfileConfig:
    host: str
    port: int
    user: str
    password: str
    ssl: bool = False
    logged_in_at: str | None = None


def config_dir() -> Path:
    return Path.home() / ".starrocks"


def config_path(profile: str) -> Path:
    return config_dir() / f"{profile}.cnf"


def grants_path(profile: str) -> Path:
    return config_dir() / f"{profile}.grants"


def exists(profile: str) -> bool:
    return config_path(profile).exists()


def read(profile: str) -> ProfileConfig:
    path = config_path(profile)
    if not path.exists():
        raise ConfigNotFoundError(
            f"Profile '{profile}' not found at {path}. "
            f"Run sr-login first, or check SR_PROFILE env var."
        )
    parser = configparser.ConfigParser()
    parser.read(path)
    if "client" not in parser:
        raise ConfigNotFoundError(f"{path} missing [client] section")
    client = parser["client"]
    meta = parser["meta"] if "meta" in parser else {}
    return ProfileConfig(
        host=client["host"],
        port=int(client.get("port", "9030")),
        user=client["user"],
        password=client["password"],
        ssl=client.getboolean("ssl", fallback=False),
        logged_in_at=meta.get("logged_in_at") or None,
    )


def write(profile: str, cfg: ProfileConfig) -> Path:
    """Write profile config with strict mode 600. Creates ~/.starrocks with 700 if missing."""
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, stat.S_IRWXU)  # 700

    path = config_path(profile)
    parser = configparser.ConfigParser()
    parser["client"] = {
        "host": cfg.host,
        "port": str(cfg.port),
        "user": cfg.user,
        "password": cfg.password,
    }
    if cfg.ssl:
        parser["client"]["ssl"] = "true"
    if cfg.logged_in_at:
        parser["meta"] = {"logged_in_at": cfg.logged_in_at}

    tmp = path.with_suffix(".cnf.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(f"# Managed by sr-login. Do not edit manually.\n")
            f.write(f"# Profile: {profile}\n")
            parser.write(f)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, path)
    os.chmod(path, 0o600)
    return path


def read_grants(profile: str) -> str:
    p = grants_path(profile)
    if not p.exists():
        return ""
    return p.read_text()


def write_grants(profile: str, grants: str) -> Path:
    d = config_dir()
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, stat.S_IRWXU)
    p = grants_path(profile)
    tmp = p.with_suffix(".grants.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(grants)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise
    os.replace(tmp, p)
    os.chmod(p, 0o600)
    return p


def remove(profile: str) -> bool:
    """Delete profile config + grants. Returns True if .cnf was removed."""
    removed = False
    path = config_path(profile)
    if path.exists():
        path.unlink()
        removed = True
    gp = grants_path(profile)
    if gp.exists():
        gp.unlink()
    return removed
