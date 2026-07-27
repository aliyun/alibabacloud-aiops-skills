from __future__ import annotations

import base64
import hashlib
import json
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
import secrets
import time
from datetime import datetime
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request
import webbrowser

try:
    from .references.http_security import secure_urlopen
    from .references.observability import ObservabilitySessionError, build_user_agent
except ImportError:  # pragma: no cover - direct script execution
    from references.http_security import secure_urlopen
    from references.observability import ObservabilitySessionError, build_user_agent


AGENTHUB_OAUTH_CLIENT_ID = "4081417976505782102"
OAUTH_BASE_URL = "https://oauth.aliyun.com"
SIGNIN_BASE_URL = "https://signin.aliyun.com"
DEFAULT_OAUTH_SCOPE = "/internal/agenthub"
DEFAULT_CALLBACK_HOST = "127.0.0.1"
DEFAULT_CALLBACK_PORT = 12345
DEFAULT_CALLBACK_PATH = "/cli/callback"
MAX_OAUTH_RESPONSE_BYTES = 1024 * 1024
MAX_OAUTH_ERROR_BYTES = 256 * 1024
_SAFE_ERROR_CODE_RE = re.compile(r"^[A-Za-z0-9._-]{1,128}$")
_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:-]{1,256}$")

class AgentHubOAuthError(RuntimeError):
    pass


def _user_agent() -> str:
    try:
        return build_user_agent()
    except ObservabilitySessionError as exc:
        raise AgentHubOAuthError(str(exc)) from exc


def _read_limited(stream, maximum: int) -> bytes:
    payload = stream.read(maximum + 1)
    if len(payload) > maximum:
        raise AgentHubOAuthError("OAuth response exceeds the local size limit")
    return payload


def oauth_client_id() -> str:
    return AGENTHUB_OAUTH_CLIENT_ID


def refresh_and_exchange_oauth_profile(
    profile: dict[str, Any],
    *,
    now: float | None = None,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    current_time = int(now if now is not None else time.time())
    _require_cn_profile(profile)
    access_token = str(profile.get("oauth_access_token") or "")
    access_token_expire = _as_int(profile.get("oauth_access_token_expire"))
    updated = dict(profile)
    if not access_token or not access_token_expire or current_time >= access_token_expire - 60:
        updated = refresh_oauth_access_token(updated, now=current_time, urlopen_func=urlopen_func)
        access_token = str(updated.get("oauth_access_token") or "")
    if not access_token:
        raise AgentHubOAuthError("OAuth access token is empty; run configure_oauth in a terminal first")
    sts = exchange_oauth_access_token_for_sts(access_token, urlopen_func=urlopen_func)
    updated.update(sts)
    updated["updated_at"] = current_time
    return updated


def configure_oauth_profile_via_browser(
    *,
    profile_name: str,
    open_browser: bool = True,
    timeout_sec: int = 300,
    urlopen_func: Callable[..., Any] = secure_urlopen,
    browser_open_func: Callable[[str], bool] = webbrowser.open,
    authorize_url_callback: Callable[[str], None] | None = None,
    now: float | None = None,
) -> tuple[dict[str, Any], str]:
    redirect_uri = (
        f"http://{DEFAULT_CALLBACK_HOST}:{DEFAULT_CALLBACK_PORT}{DEFAULT_CALLBACK_PATH}"
    )
    state = f"cli-{secrets.token_urlsafe(16)}"
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    authorize_url = build_authorization_url(
        redirect_uri,
        state,
        code_challenge=code_challenge,
    )
    if authorize_url_callback:
        authorize_url_callback(authorize_url)
    if open_browser:
        try:
            browser_open_func(authorize_url)
        except Exception:
            pass
    code = wait_for_oauth_code(state=state, timeout_sec=timeout_sec)
    current_time = int(now if now is not None else time.time())
    token_payload = exchange_authorization_code_for_token(
        code,
        redirect_uri,
        code_verifier=code_verifier,
        urlopen_func=urlopen_func,
    )
    access_token = str(token_payload.get("access_token") or "")
    if not access_token:
        raise AgentHubOAuthError("OAuth token response does not contain access_token")
    profile = {
        "name": profile_name,
        "mode": "OAuth",
        "oauth_site_type": "CN",
        "oauth_access_token": access_token,
        "oauth_refresh_token": str(token_payload.get("refresh_token") or ""),
        "oauth_access_token_expire": current_time + int(token_payload.get("expires_in") or 3600),
        "oauth_token_type": str(token_payload.get("token_type") or "Bearer"),
    }
    return (
        refresh_and_exchange_oauth_profile(
            profile,
            now=current_time,
            urlopen_func=urlopen_func,
        ),
        authorize_url,
    )


def generate_code_verifier() -> str:
    return secrets.token_urlsafe(96)[:128]


def generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_authorization_url(
    redirect_uri: str,
    state: str,
    *,
    code_challenge: str,
) -> str:
    if not code_challenge:
        raise AgentHubOAuthError("OAuth PKCE code_challenge is empty")
    return (
        f"{SIGNIN_BASE_URL}/oauth2/v1/auth?"
        + urlencode(
            {
                "response_type": "code",
                "client_id": oauth_client_id(),
                "redirect_uri": redirect_uri,
                "scope": DEFAULT_OAUTH_SCOPE,
                "state": state,
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }
        )
    )


def wait_for_oauth_code(*, state: str, timeout_sec: int) -> str:
    result: dict[str, str] = {}

    class CallbackHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A002
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path != DEFAULT_CALLBACK_PATH:
                self.send_error(404, "Not Found")
                return
            params = parse_qs(parsed.query)
            if params.get("state", [""])[0] != state:
                result["error"] = "invalid OAuth state"
                self.send_error(400, "Invalid state")
                return
            code = params.get("code", [""])[0]
            if not code:
                result["error"] = "OAuth callback did not contain code"
                self.send_error(400, "Code not found")
                return
            result["code"] = code
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(
                b"<html><body>Authorization successful. You can close this window.</body></html>"
            )

    try:
        server = HTTPServer((DEFAULT_CALLBACK_HOST, DEFAULT_CALLBACK_PORT), CallbackHandler)
    except OSError as exc:
        raise AgentHubOAuthError(
            f"cannot listen on {DEFAULT_CALLBACK_HOST}:{DEFAULT_CALLBACK_PORT}; "
            "close the process using this port and retry configure_oauth"
        ) from exc
    server.timeout = 1
    deadline = time.time() + timeout_sec
    try:
        while "code" not in result and "error" not in result and time.time() < deadline:
            server.handle_request()
    finally:
        server.server_close()
    if result.get("error"):
        raise AgentHubOAuthError(result["error"])
    if not result.get("code"):
        raise AgentHubOAuthError("OAuth authorization timed out")
    return result["code"]


def exchange_authorization_code_for_token(
    code: str,
    redirect_uri: str,
    *,
    code_verifier: str,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    if not code_verifier:
        raise AgentHubOAuthError("OAuth PKCE code_verifier is empty")
    return _post_form(
        f"{OAUTH_BASE_URL}/v1/token",
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": oauth_client_id(),
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
        urlopen_func=urlopen_func,
    )


def refresh_oauth_access_token(
    profile: dict[str, Any],
    *,
    now: float | None = None,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    current_time = int(now if now is not None else time.time())
    _require_cn_profile(profile)
    refresh_token = str(profile.get("oauth_refresh_token") or "")
    if not refresh_token:
        raise AgentHubOAuthError("OAuth refresh token is empty; run configure_oauth in a terminal first")
    token_url = f"{OAUTH_BASE_URL}/v1/token"
    payload = _post_form(
        token_url,
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": oauth_client_id(),
        },
        urlopen_func=urlopen_func,
    )
    access_token = str(payload.get("access_token") or "")
    if not access_token:
        raise AgentHubOAuthError("OAuth token refresh response does not contain access_token")
    updated = dict(profile)
    updated["oauth_access_token"] = access_token
    updated["oauth_refresh_token"] = str(payload.get("refresh_token") or refresh_token)
    updated["oauth_access_token_expire"] = current_time + int(payload.get("expires_in") or 3600)
    updated["oauth_token_type"] = str(payload.get("token_type") or "Bearer")
    return updated


def exchange_oauth_access_token_for_sts(
    access_token: str,
    *,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    exchange_url = f"{OAUTH_BASE_URL}/v1/exchange"
    payload = _post_empty_json(
        exchange_url,
        headers={"Authorization": f"Bearer {access_token}"},
        urlopen_func=urlopen_func,
    )
    access_key_id = str(payload.get("AccessKeyId") or "")
    access_key_secret = str(payload.get("AccessKeySecret") or "")
    security_token = str(payload.get("SecurityToken") or "")
    expiration = _parse_rfc3339(payload.get("Expiration"))
    if not access_key_id or not access_key_secret or not security_token or not expiration:
        raise AgentHubOAuthError("OAuth exchange response does not contain complete STS credentials")
    return {
        "access_key_id": access_key_id,
        "access_key_secret": access_key_secret,
        "sts_token": security_token,
        "sts_expiration": int(expiration),
    }


def _require_cn_profile(profile: dict[str, Any]) -> None:
    site = str(profile.get("oauth_site_type") or "CN").upper()
    if site != "CN":
        raise AgentHubOAuthError("this AgentHub release supports only the China site")


def _post_form(
    url: str,
    fields: dict[str, str],
    *,
    timeout_sec: int = 30,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    data = urlencode(fields).encode("utf-8")
    request = Request(
        url,
        data=data,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": _user_agent(),
        },
        method="POST",
    )
    return _send_json_request(request, timeout_sec=timeout_sec, urlopen_func=urlopen_func)


def _post_empty_json(
    url: str,
    *,
    headers: dict[str, str],
    timeout_sec: int = 30,
    urlopen_func: Callable[..., Any] = secure_urlopen,
) -> dict[str, Any]:
    merged_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": _user_agent(),
    }
    merged_headers.update(headers)
    request = Request(url, data=b"", headers=merged_headers, method="POST")
    return _send_json_request(request, timeout_sec=timeout_sec, urlopen_func=urlopen_func)


def _send_json_request(
    request: Request,
    *,
    timeout_sec: int,
    urlopen_func: Callable[..., Any],
) -> dict[str, Any]:
    try:
        with urlopen_func(request, timeout=timeout_sec) as response:
            raw = _read_limited(response, MAX_OAUTH_RESPONSE_BYTES).decode("utf-8")
    except HTTPError as exc:
        try:
            raw = _read_limited(exc, MAX_OAUTH_ERROR_BYTES).decode(
                "utf-8",
                errors="replace",
            )
        except AgentHubOAuthError as size_error:
            raise AgentHubOAuthError("OAuth HTTP error response exceeds the local size limit") from size_error
        raise AgentHubOAuthError(
            _format_oauth_error(exc.code, raw, url=request.full_url, headers=exc.headers)
        ) from exc
    except URLError as exc:
        raise AgentHubOAuthError(f"OAuth network error: {exc.reason}") from exc
    try:
        decoded = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AgentHubOAuthError("OAuth response is not valid JSON") from exc
    if not isinstance(decoded, dict):
        raise AgentHubOAuthError("OAuth response JSON is not an object")
    if decoded.get("error"):
        message = f"OAuth error: {_safe_error_code(decoded.get('error'))}"
        raise AgentHubOAuthError(
            _append_request_id(message, _extract_request_id(decoded, None))
        )
    return decoded


def _format_oauth_error(
    status_code: int,
    raw_body: str,
    *,
    url: str | None = None,
    headers: Any | None = None,
) -> str:
    endpoint = _oauth_endpoint_path(url)
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        message = f"OAuth HTTP {status_code}{endpoint}: non-JSON error response"
        request_id = _extract_request_id({}, headers)
        return _append_request_id(message, request_id)
    if not isinstance(payload, dict):
        message = f"OAuth HTTP {status_code}{endpoint}"
        return _append_request_id(message, _extract_request_id({}, headers))
    error_code = _safe_error_code(payload.get("error") or payload.get("ErrorCode"))
    message = f"OAuth HTTP {status_code}{endpoint}: {error_code}"
    return _append_request_id(message, _extract_request_id(payload, headers))


def _oauth_endpoint_path(url: str | None) -> str:
    if not url:
        return ""
    parsed = urlparse(url)
    if parsed.path not in {"/v1/token", "/v1/exchange"}:
        return ""
    return f" at {parsed.path}"


def _safe_error_code(value: Any) -> str:
    text = str(value or "").strip()
    return text if _SAFE_ERROR_CODE_RE.fullmatch(text) else "-"


def _safe_request_id(value: Any) -> str:
    text = str(value or "").strip()
    return text if _SAFE_REQUEST_ID_RE.fullmatch(text) else ""


def _extract_request_id(payload: dict[str, Any], headers: Any | None) -> str:
    for key in ("requestId", "RequestId", "request_id", "x-acs-request-id"):
        value = payload.get(key)
        if value:
            safe = _safe_request_id(value)
            if safe:
                return safe
    if headers is not None:
        for key in ("x-acs-request-id", "X-Acs-Request-Id", "x-acs-requestid"):
            try:
                value = headers.get(key)
            except AttributeError:
                value = None
            if value:
                safe = _safe_request_id(value)
                if safe:
                    return safe
    return ""


def _append_request_id(message: str, request_id: str) -> str:
    if not request_id:
        return message
    return f"{message} requestId={request_id}"


def _parse_rfc3339(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
