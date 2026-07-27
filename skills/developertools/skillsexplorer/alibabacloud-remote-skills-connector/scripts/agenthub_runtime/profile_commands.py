from __future__ import annotations

import getpass
import re
import sys
from pathlib import Path
from typing import TextIO

try:
    from scripts.a2a_proxy.agenthub_oauth import AgentHubOAuthError, configure_oauth_profile_via_browser
    from scripts.a2a_proxy.agenthub_profile import (
        DEFAULT_AK_PROFILE,
        DEFAULT_OAUTH_PROFILE,
        AgentHubProfileError,
        default_config_path,
        ensure_private_config,
        save_agenthub_profile,
    )
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.agenthub_oauth import AgentHubOAuthError, configure_oauth_profile_via_browser
    from a2a_proxy.agenthub_profile import (
        DEFAULT_AK_PROFILE,
        DEFAULT_OAUTH_PROFILE,
        AgentHubProfileError,
        default_config_path,
        ensure_private_config,
        save_agenthub_profile,
    )


def configure_ak_profile(
    *,
    profile_name: str = DEFAULT_AK_PROFILE,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    stdin: TextIO | None = None,
    config_path: Path | None = None,
) -> int:
    input_stream = stdin if stdin is not None else sys.stdin
    if not _require_user_terminal("configure_ak", stdin=input_stream, stderr=stderr):
        return 2
    path = ensure_private_config(config_path or default_config_path())
    stdout.write(f"将写入 AgentHub 私有配置文件：{path}\n")
    stdout.write("AccessKeyId: ")
    stdout.flush()
    access_key_id = input_stream.readline().strip()
    access_key_secret = getpass.getpass("AccessKeySecret: ")
    if not access_key_id or not access_key_secret:
        stderr.write("AccessKeyId 和 AccessKeySecret 不能为空。\n")
        return 2
    save_agenthub_profile(
        {
            "name": profile_name,
            "mode": "AK",
            "access_key_id": access_key_id,
            "access_key_secret": access_key_secret,
        },
        config_path=path,
        make_current=True,
    )
    stdout.write(f"AgentHub AK profile 已写入：{profile_name}。凭证值不会输出到对话或日志。\n")
    return 0


def configure_oauth_profile(
    *,
    profile_name: str = DEFAULT_OAUTH_PROFILE,
    no_browser: bool = False,
    timeout_sec: int = 300,
    stdout: TextIO = sys.stdout,
    stderr: TextIO = sys.stderr,
    stdin: TextIO | None = None,
    config_path: Path | None = None,
) -> int:
    input_stream = stdin if stdin is not None else sys.stdin
    if not _require_user_terminal("configure_oauth", stdin=input_stream, stderr=stderr):
        return 2
    path = ensure_private_config(config_path or default_config_path())
    stdout.write(f"将写入 AgentHub 私有配置文件：{path}\n")
    stdout.write("正在启动 OAuth 授权流程。浏览器完成授权后，本地脚本会写入 OAuth/STS 缓存。\n")
    stdout.write("不要把浏览器地址栏、OAuth code、token 或任何凭证内容粘贴到对话里。\n")
    stdout.flush()
    try:
        def show_authorize_url(authorize_url: str) -> None:
            if no_browser:
                stdout.write("请在浏览器中打开以下授权地址：\n")
            else:
                stdout.write("如果浏览器没有自动打开，请手动访问以下授权地址：\n")
            stdout.write(f"{authorize_url}\n")
            stdout.flush()

        profile, _authorize_url = configure_oauth_profile_via_browser(
            profile_name=profile_name,
            open_browser=not no_browser,
            timeout_sec=timeout_sec,
            authorize_url_callback=show_authorize_url,
        )
        save_agenthub_profile(profile, config_path=path, make_current=True)
    except AgentHubOAuthError as exc:
        request_id = _safe_request_id_from_error(exc)
        suffix = f" requestId={request_id}" if request_id else ""
        stderr.write(
            "AgentHub OAuth profile 配置失败；请检查网络、授权状态或终端环境后重试。"
            f"{suffix}\n"
        )
        return 1
    except AgentHubProfileError as exc:
        stderr.write(f"AgentHub OAuth profile 配置失败：{exc}\n")
        return 1
    stdout.write(f"AgentHub OAuth profile 已写入：{profile_name}。凭证值不会输出到对话或日志。\n")
    return 0


def _safe_request_id_from_error(error: BaseException) -> str:
    match = re.search(r"(?:^|\s)requestId=([A-Za-z0-9._:-]{1,256})(?:$|\s)", str(error))
    return match.group(1) if match else ""


def _require_user_terminal(command_name: str, *, stdin: TextIO, stderr: TextIO) -> bool:
    if stdin.isatty():
        return True
    stderr.write(
        f"{command_name} 必须由用户在本地交互终端手动执行，不能由端侧 Agent 代执行。\n"
    )
    return False
