from __future__ import annotations

import json
import os
import re
import stat
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .config import skill_root


TOKEN_MARK_BEGIN = "===A2A_TOKEN_BEGIN==="
TOKEN_MARK_END = "===A2A_TOKEN_END==="
TOKEN_CHARSET_RE = re.compile(r"^[A-Za-z0-9._\-+/=]+$")
AUTH_REQUIRED_EXIT_CODE = 20
CACHE_EXPIRY_BUFFER_SEC = 60


@dataclass(frozen=True)
class CredentialPreflightResult:
    ok: bool
    message: str
    exit_code: int = 0


def default_token_script() -> Path:
    return skill_root() / "scripts" / "a2a_proxy" / "get_token.sh"


def prepare_agenthub_credentials(
    *,
    refresh: bool = False,
    credential_source: str | None = None,
    runner=subprocess.run,
    token_script: Path | None = None,
    profile_guidance_provider: Callable[[], str | None] | None = None,
    timeout_sec: int = 60,
) -> CredentialPreflightResult:
    # Kept in the signature for callers that injected the former pre-check.
    # The helper is now the sole credential/cache state machine: it can reuse a
    # valid token before requiring the originally selected source to exist.
    del profile_guidance_provider

    script = token_script or default_token_script()
    if not script.exists():
        return CredentialPreflightResult(
            ok=False,
            message=f"AgentHub 凭证初始化失败：找不到 token 脚本 {script}。",
            exit_code=1,
        )

    command = "refresh" if refresh else "login"
    helper_command = ["bash", str(script), command, "CN"]
    if credential_source:
        helper_command.extend(["--credential-source", credential_source])
    try:
        result = runner(
            helper_command,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            env={**os.environ, "AGENTHUB_PYTHON": sys.executable},
        )
    except subprocess.TimeoutExpired:
        return CredentialPreflightResult(
            ok=False,
            message="AgentHub 凭证初始化超时，请检查 profile 配置、网络或 ramoauth 服务是否正常。",
            exit_code=1,
        )

    stdout = str(getattr(result, "stdout", "") or "")
    stderr = str(getattr(result, "stderr", "") or "")
    returncode = int(getattr(result, "returncode", 0) or 0)
    if returncode != 0:
        sanitized = _sanitize_token_protocol_output("\n".join(part for part in (stdout, stderr) if part))
        if returncode == AUTH_REQUIRED_EXIT_CODE:
            message = sanitized or (
                "AgentHub 凭证初始化需要用户先完成本地 profile 配置；"
                "若 GenerateAccessToken 返回 NoPermission，该 API 默认无需显式 Allow，"
                "请让账号管理员检查是否存在覆盖 ram:GenerateAccessToken 的显式 Deny。"
            )
            return CredentialPreflightResult(
                ok=False,
                message=message,
                exit_code=AUTH_REQUIRED_EXIT_CODE,
            )
        message = sanitized or f"AgentHub 凭证初始化失败 (exit code: {returncode})。"
        return CredentialPreflightResult(ok=False, message=message, exit_code=1)

    token = _extract_token(stdout)
    if not _is_valid_token(token):
        return CredentialPreflightResult(
            ok=False,
            message="AgentHub 凭证初始化失败：token 脚本输出格式异常，请重试或检查脚本输出。",
            exit_code=1,
        )

    cache_file = Path.home() / ".aliyun_agenthub" / "CN_credential"
    cache_error = _validate_credential_cache(cache_file)
    if cache_error:
        return CredentialPreflightResult(
            ok=False,
            message=f"AgentHub 凭证初始化失败：{cache_error}",
            exit_code=1,
        )

    status = "已刷新" if refresh else "已就绪"
    return CredentialPreflightResult(
        ok=True,
        message=(
            f"AgentHub 凭证{status}：中国站，缓存文件 {cache_file}。"
            "后续 send/continue/check/subscribe/cancel 会复用该凭证缓存。"
        ),
        exit_code=0,
    )


def _extract_token(output: str) -> str:
    lines = output.splitlines()
    try:
        start = lines.index(TOKEN_MARK_BEGIN)
        end = lines.index(TOKEN_MARK_END, start + 1)
    except ValueError:
        return ""
    candidates = [line.strip() for line in lines[start + 1:end] if line.strip()]
    if len(candidates) != 1:
        return ""
    return candidates[0]


def _is_valid_token(token: str) -> bool:
    return bool(token and token.isascii() and TOKEN_CHARSET_RE.match(token) and len(token) >= 20)


def _validate_credential_cache(cache_file: Path) -> str | None:
    try:
        info = cache_file.lstat()
    except FileNotFoundError:
        return f"token 缓存文件不存在或为空：{cache_file}。"
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.getuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_nlink != 1
        or info.st_size <= 0
    ):
        return f"token 缓存文件权限、所有者或文件类型不安全：{cache_file}。"
    flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(cache_file, flags)
    except OSError:
        return f"token 缓存文件不可读取或不是有效 JSON：{cache_file}。"
    try:
        opened = os.fstat(fd)
        if (
            not stat.S_ISREG(opened.st_mode)
            or opened.st_uid != os.getuid()
            or stat.S_IMODE(opened.st_mode) != 0o600
            or opened.st_nlink != 1
            or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
        ):
            return f"token 缓存文件权限、所有者或文件类型不安全：{cache_file}。"
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = -1
            data = json.load(stream)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return f"token 缓存文件不可读取或不是有效 JSON：{cache_file}。"
    finally:
        if fd >= 0:
            os.close(fd)

    if not isinstance(data, dict):
        return f"token 缓存结构异常：{cache_file}。"
    token_response = data.get("token_response")
    obtained_at = _as_number(data.get("token_obtained_at"))
    expires_in = _as_number(data.get("token_expires_in"))
    if not isinstance(token_response, dict) or not obtained_at or not expires_in:
        return f"token 缓存结构不完整：{cache_file}。"

    if time.time() >= obtained_at + expires_in - CACHE_EXPIRY_BUFFER_SEC:
        return f"token 缓存已经过期或即将过期：{cache_file}。"

    payload = token_response.get("Data") or token_response
    if not isinstance(payload, dict):
        return f"token 缓存响应结构异常：{cache_file}。"
    cached_token = str(payload.get("AccessToken") or payload.get("access_token") or "")
    if not _is_valid_token(cached_token):
        return f"token 缓存中没有可用的 access token：{cache_file}。"
    return None


def _as_number(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sanitize_token_protocol_output(output: str) -> str:
    sanitized_lines: list[str] = []
    skipping_token = False
    for line in output.splitlines():
        stripped = line.strip()
        if stripped == TOKEN_MARK_BEGIN:
            skipping_token = True
            continue
        if stripped == TOKEN_MARK_END:
            skipping_token = False
            continue
        if skipping_token:
            continue
        sanitized_lines.append(line)
    return "\n".join(sanitized_lines).strip()
