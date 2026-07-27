from __future__ import annotations

import io
import re
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


OFFICIAL_AGENTHUB_REGION_SUFFIX = ".cn-beijing.agenthub.aliyuncs.com"
_AGENT_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_ALLOWED_ENDPOINT_PATHS = {"", "/", "/rpc"}


class RejectRedirectHandler(HTTPRedirectHandler):
    """Reject redirects so API credentials are never forwarded to another URL."""

    def http_error_302(self, req, fp, code, msg, headers):
        location = headers.get("Location") or headers.get("URI") or "unknown location"
        fp.close()
        raise HTTPError(
            req.full_url,
            code,
            f"API redirect blocked: {location}",
            headers,
            io.BytesIO(),
        )

    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def secure_urlopen(request: Request | str, *, timeout: float) -> Any:
    """Open one API request with default TLS verification and no redirects."""
    return build_opener(RejectRedirectHandler()).open(request, timeout=timeout)


def validate_agent_id(agent_id: str) -> str:
    """Return the canonical AgentHub DNS label or reject it."""
    if not isinstance(agent_id, str):
        raise ValueError("agent_id must be a string")
    value = agent_id
    if not value or not value.isascii() or not _AGENT_ID_RE.fullmatch(value):
        raise ValueError("agent_id must be one lowercase ASCII DNS label (1-63 chars)")
    return value


def expected_agenthub_host(agent_id: str) -> str:
    return f"{validate_agent_id(agent_id)}{OFFICIAL_AGENTHUB_REGION_SUFFIX}"


def normalize_official_agenthub_endpoint(
    endpoint: str,
    *,
    agent_id: str | None = None,
) -> str:
    """Validate and canonicalize a public China-site AgentHub endpoint.

    The public connector accepts only the selected agent's HTTPS host and the
    root or ``/rpc`` path.  It never upgrades HTTP or accepts a different
    official-looking tenant host.
    """
    if not isinstance(endpoint, str):
        raise ValueError("AgentHub endpoint must be a string")
    value = endpoint
    parsed = urlsplit(value)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        raise ValueError("AgentHub endpoint must use HTTPS")
    if not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("AgentHub endpoint must not contain user information")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("AgentHub endpoint contains an invalid port") from exc
    if port is not None:
        raise ValueError("AgentHub endpoint must not specify a port")
    if parsed.netloc.lower() != hostname:
        # Covers empty/explicit port delimiters and any non-host authority
        # syntax that urllib would otherwise normalize away.
        raise ValueError("AgentHub endpoint authority must contain only the host")
    if parsed.query or parsed.fragment or parsed.path not in _ALLOWED_ENDPOINT_PATHS:
        raise ValueError("AgentHub endpoint path must be root or /rpc")
    if not hostname.endswith(OFFICIAL_AGENTHUB_REGION_SUFFIX):
        raise ValueError("AgentHub endpoint is not an official China-site host")
    label = hostname[: -len(OFFICIAL_AGENTHUB_REGION_SUFFIX)]
    validate_agent_id(label)
    if agent_id is not None and hostname != expected_agenthub_host(agent_id):
        raise ValueError("AgentHub endpoint does not match agent_id")
    origin = f"https://{hostname}"
    return f"{origin}/rpc" if parsed.path == "/rpc" else origin


def agenthub_origin(endpoint: str, *, agent_id: str | None = None) -> str:
    normalized = normalize_official_agenthub_endpoint(endpoint, agent_id=agent_id)
    return normalized[:-4] if normalized.endswith("/rpc") else normalized


def agenthub_rpc_url(endpoint: str, *, agent_id: str | None = None) -> str:
    normalized = normalize_official_agenthub_endpoint(endpoint, agent_id=agent_id)
    return normalized if normalized.endswith("/rpc") else f"{normalized}/rpc"
