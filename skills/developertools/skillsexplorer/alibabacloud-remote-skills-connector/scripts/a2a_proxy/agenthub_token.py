from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request

try:
    from .agenthub_oauth import AgentHubOAuthError, refresh_and_exchange_oauth_profile
    from .references.http_security import secure_urlopen
    from .references.observability import ObservabilitySessionError, build_user_agent
    from .agenthub_profile import (
        AgentHubProfileError,
        ProfileCredentials,
        credentials_from_profile,
        find_profile,
        load_agenthub_config,
        save_agenthub_profile,
    )
except ImportError:  # pragma: no cover - direct script execution
    from agenthub_oauth import AgentHubOAuthError, refresh_and_exchange_oauth_profile
    from references.http_security import secure_urlopen
    from references.observability import ObservabilitySessionError, build_user_agent
    from agenthub_profile import (
        AgentHubProfileError,
        ProfileCredentials,
        credentials_from_profile,
        find_profile,
        load_agenthub_config,
        save_agenthub_profile,
    )


ACTION = "GenerateAccessToken"
VERSION = "2026-04-21"
RAMOAUTH_URL = "https://ramoauth.aliyuncs.com/"
AGENTHUB_CLIENT_ID = "4081417976505782102"
AGENTHUB_SCOPE = "/internal/agenthub"
REGION_ID = "cn-hangzhou"
DEFAULT_TIMEOUT_SEC = 30
AUTH_REQUIRED_EXIT_CODE = 20
MAX_TOKEN_RESPONSE_BYTES = 1024 * 1024
MAX_TOKEN_ERROR_BYTES = 256 * 1024

class ProfileCredentialError(RuntimeError):
    pass


class GenerateAccessTokenError(RuntimeError):
    pass


def _user_agent() -> str:
    try:
        return build_user_agent()
    except ObservabilitySessionError as exc:
        raise GenerateAccessTokenError(str(exc)) from exc


def _read_limited(stream, maximum: int) -> bytes:
    payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise GenerateAccessTokenError(
            "GenerateAccessToken response exceeds the local size limit"
        )
    return payload


def percent_encode(value: Any) -> str:
    return quote(str(value), safe="-_.~")


def build_signed_rpc_params(
    *,
    method: str,
    action: str,
    version: str,
    region_id: str,
    access_key_id: str,
    access_key_secret: str,
    security_token: str | None,
    extra_params: dict[str, str],
    timestamp: str | None = None,
    nonce: str | None = None,
) -> dict[str, str]:
    if not access_key_id or not access_key_secret:
        raise ProfileCredentialError("selected profile does not contain usable AK credentials")

    params: dict[str, str] = {
        "Action": action,
        "Version": version,
        "Format": "JSON",
        "AccessKeyId": access_key_id,
        "SignatureMethod": "HMAC-SHA1",
        "SignatureNonce": nonce or str(uuid.uuid4()),
        "SignatureVersion": "1.0",
        "Timestamp": timestamp or _utc_timestamp(),
        "RegionId": region_id,
    }
    params.update({key: str(value) for key, value in extra_params.items() if value is not None})
    if security_token:
        params["SecurityToken"] = security_token

    canonical = "&".join(
        f"{percent_encode(key)}={percent_encode(value)}"
        for key, value in sorted(params.items(), key=lambda item: item[0])
    )
    string_to_sign = f"{method.upper()}&%2F&{percent_encode(canonical)}"
    digest = hmac.new(
        f"{access_key_secret}&".encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    params["Signature"] = base64.b64encode(digest).decode("ascii")
    return params


def load_profile_credentials(config_path: Path, profile_name: str) -> ProfileCredentials:
    try:
        config = load_agenthub_config(config_path=config_path)
        profile = find_profile(config, profile_name)
        if _oauth_sts_needs_refresh(profile):
            profile = refresh_and_exchange_oauth_profile(profile)
            save_agenthub_profile(profile, config_path=config_path, make_current=True)
        return credentials_from_profile(profile)
    except (AgentHubProfileError, AgentHubOAuthError) as exc:
        raise ProfileCredentialError(str(exc)) from exc


def generate_access_token(
    *,
    credentials: ProfileCredentials,
    timeout_sec: int = DEFAULT_TIMEOUT_SEC,
    timestamp: str | None = None,
    nonce: str | None = None,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    params = build_signed_rpc_params(
        method="POST",
        action=ACTION,
        version=VERSION,
        region_id=REGION_ID,
        access_key_id=credentials.access_key_id,
        access_key_secret=credentials.access_key_secret,
        security_token=credentials.security_token,
        extra_params={"ClientId": AGENTHUB_CLIENT_ID, "Scope": AGENTHUB_SCOPE},
        timestamp=timestamp,
        nonce=nonce,
    )
    body = urlencode(params, quote_via=quote, safe="-_.~").encode("utf-8")
    request = Request(
        RAMOAUTH_URL,
        data=body,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": _user_agent(),
        },
        method="POST",
    )
    try:
        with urlopen_func(request, timeout=timeout_sec) as response:
            raw = _read_limited(response, MAX_TOKEN_RESPONSE_BYTES).decode("utf-8")
    except HTTPError as exc:
        try:
            raw = _read_limited(exc, MAX_TOKEN_ERROR_BYTES).decode(
                "utf-8",
                errors="replace",
            )
        except GenerateAccessTokenError as size_error:
            raise GenerateAccessTokenError(
                "GenerateAccessToken HTTP error response exceeds the local size limit"
            ) from size_error
        raise GenerateAccessTokenError(_format_openapi_error(exc.code, raw)) from exc
    except URLError as exc:
        raise GenerateAccessTokenError(f"NetworkError: {exc.reason}") from exc
    except TimeoutError as exc:
        raise GenerateAccessTokenError("GenerateAccessToken request timed out") from exc

    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GenerateAccessTokenError("GenerateAccessToken response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise GenerateAccessTokenError("GenerateAccessToken response JSON is not an object")
    return decoded


def _oauth_sts_needs_refresh(profile: dict[str, Any]) -> bool:
    if str(profile.get("mode") or "AK").lower() != "oauth":
        return False
    expiration = _parse_unix_time(profile.get("sts_expiration"))
    return not (
        profile.get("access_key_id")
        and profile.get("access_key_secret")
        and profile.get("sts_token")
        and expiration
        and time.time() < expiration - 60
    )


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
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _format_openapi_error(status_code: int, raw_body: str) -> str:
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        return f"HTTPStatus: {status_code}\nMessage: {_trim(raw_body)}"
    if not isinstance(payload, dict):
        return f"HTTPStatus: {status_code}\nMessage: {_trim(raw_body)}"
    code = payload.get("Code") or payload.get("ErrorCode") or payload.get("code") or ""
    message = payload.get("Message") or payload.get("message") or ""
    request_id = payload.get("RequestId") or payload.get("requestId") or ""
    lines = [f"HTTPStatus: {status_code}"]
    if code:
        lines.append(f"ErrorCode: {code}")
    if message:
        lines.append(f"Message: {message}")
    if request_id:
        lines.append(f"RequestId: {request_id}")
    return "\n".join(lines)


def _trim(text: str, limit: int = 1000) -> str:
    collapsed = " ".join(str(text or "").split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _run_generate(args: argparse.Namespace) -> int:
    config_path = Path(args.config_file).expanduser()
    try:
        credentials = load_profile_credentials(config_path, args.profile)
        response = generate_access_token(
            credentials=credentials,
            timeout_sec=args.timeout_sec,
        )
    except ProfileCredentialError as exc:
        print(
            "\n".join(
                (
                    f"[ERROR] 无法加载 AgentHub profile={args.profile!r} "
                    f"from config={str(config_path)!r}: {exc}",
                    "期望格式：配置文件根节点是 JSON object，包含非空 profiles 数组；"
                    "其中必须存在同名 profile，并包含所选认证模式要求的字段。",
                    "修复方法：通过公开 agenthub.py auth_init 流程重新选择凭证来源，"
                    "或运行对应的 configure_ak / configure_oauth 命令；不要在日志或对话中粘贴凭证。",
                )
            ),
            file=sys.stderr,
        )
        return AUTH_REQUIRED_EXIT_CODE
    except GenerateAccessTokenError as exc:
        print(
            "\n".join(
                (
                    f"[ERROR] GenerateAccessToken 调用失败（profile={args.profile!r}）: {exc}",
                    "排查：确认 SKILL_SESSION_ID 是本会话持续复用的 32 位小写十六进制值；"
                    "确认可通过 HTTPS 访问 ramoauth.aliyuncs.com。ram:GenerateAccessToken "
                    "默认无需显式 Allow；若返回 NoPermission，请让账号管理员检查并移除或收窄适用于当前身份的显式 Deny，"
                    "然后通过 agenthub.py auth_init --refresh 重试。",
                    "若错误中包含 RequestId，请保留该值用于服务端诊断，但不要输出 AK、STS Token 或 OAuth token。",
                )
            ),
            file=sys.stderr,
        )
        return 1
    json.dump(response, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate AgentHub access token without aliyun CLI.")
    subcommands = parser.add_subparsers(dest="command", required=True)
    generate = subcommands.add_parser("generate", help="Call ramoauth GenerateAccessToken directly.")
    generate.add_argument("--config-file", required=True)
    generate.add_argument("--profile", required=True)
    generate.add_argument("--timeout-sec", type=int, default=DEFAULT_TIMEOUT_SEC)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.command == "generate":
        return _run_generate(args)
    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
