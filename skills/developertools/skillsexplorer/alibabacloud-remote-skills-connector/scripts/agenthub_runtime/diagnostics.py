from __future__ import annotations

import os
import platform
import socket
import ssl
import stat
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import default_vendor_proxy_script
try:
    from scripts.a2a_proxy.agenthub_credential_source import default_cli_config_path
    from scripts.a2a_proxy.agenthub_profile import default_config_path
    from scripts.a2a_proxy.references.observability import (
        ObservabilitySessionError,
        build_user_agent,
    )
except ImportError:  # pragma: no cover - direct script execution
    from a2a_proxy.agenthub_credential_source import default_cli_config_path
    from a2a_proxy.agenthub_profile import default_config_path
    from a2a_proxy.references.observability import ObservabilitySessionError, build_user_agent


PASS = "PASS"
WARN = "WARN"
FAIL = "FAIL"
TLS_PROBE_URLS = (
    ("agentexplorer", "https://agentexplorer.aliyuncs.com/"),
    ("skills-catalog", "https://skills.aliyun.com/"),
    ("oauth", "https://oauth.aliyun.com/"),
    ("ramoauth", "https://ramoauth.aliyuncs.com/"),
)


def diagnose() -> list[tuple[str, str, str]]:
    private_config_path = default_config_path()
    cli_config_path = default_cli_config_path()
    vendor_script = default_vendor_proxy_script()
    cli_config_status, cli_config_detail = _config_metadata_check(
        cli_config_path,
        require_private=False,
    )
    private_config_status, private_config_detail = _config_metadata_check(
        private_config_path,
        require_private=True,
    )
    executable = str(sys.executable or "")
    python_ok = bool(executable and Path(executable).is_file())
    python_detail = (
        f"executable={executable or '<empty>'}; version={platform.python_version()}; "
        f"implementation={platform.python_implementation()}"
    )
    verify_paths = ssl.get_default_verify_paths()
    try:
        ca_count = len(ssl.create_default_context().get_ca_certs())
    except ssl.SSLError:
        ca_count = 0
    ca_status = PASS if ca_count > 0 else WARN
    ca_detail = (
        f"default cafile={verify_paths.cafile or '<none>'}; "
        f"capath={verify_paths.capath or '<none>'}; loaded CA count={ca_count}"
    )
    checks: list[tuple[str, str, str]] = [
        ("python", PASS if python_ok else FAIL, python_detail),
        ("ssl", PASS, f"OpenSSL={ssl.OPENSSL_VERSION}"),
        ("ca-trust", ca_status, ca_detail),
        (
            "aliyun-cli-config",
            cli_config_status,
            cli_config_detail,
        ),
        (
            "agenthub-private-config",
            private_config_status,
            private_config_detail,
        ),
        (
            "aliyun-agenthub-profile",
            WARN,
            "credential values are intentionally not inspected; run auth_init to verify readiness",
        ),
        (
            "bundled-a2a-proxy",
            PASS if vendor_script.exists() else FAIL,
            str(vendor_script),
        ),
    ]
    checks.extend(_probe_tls(name, url) for name, url in TLS_PROBE_URLS)
    return checks


def _config_metadata_check(path: Path, *, require_private: bool) -> tuple[str, str]:
    """Inspect only filesystem metadata; never open credential-bearing files."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return WARN, f"not found: {path}"
    except OSError as exc:
        return WARN, f"cannot inspect metadata for {path}: {exc}"
    if not stat.S_ISREG(info.st_mode):
        return FAIL, f"not a regular file: {path}"
    if info.st_uid != os.getuid():
        return FAIL, f"owned by a different user: {path}"
    if require_private and (info.st_nlink != 1 or stat.S_IMODE(info.st_mode) != 0o600):
        return FAIL, f"private config must be a single-link 0600 file: {path}"
    return PASS, f"metadata only; contents not read: {path}"


def _probe_tls(name: str, url: str) -> tuple[str, str, str]:
    try:
        user_agent = build_user_agent()
    except ObservabilitySessionError as exc:
        return f"tls-{name}", FAIL, str(exc)
    request = Request(
        url,
        headers={"User-Agent": user_agent},
        method="HEAD",
    )
    context = ssl.create_default_context()
    try:
        with urlopen(request, timeout=5, context=context):
            pass
    except HTTPError as exc:
        return (
            f"tls-{name}",
            PASS,
            f"strict certificate and hostname verification succeeded; HTTP {exc.code}",
        )
    except URLError as exc:
        return _classify_tls_failure(name, exc.reason)
    except ssl.SSLCertVerificationError as exc:
        return (
            f"tls-{name}",
            FAIL,
            f"strict certificate/hostname verification failed: {exc}",
        )
    except ssl.SSLError as exc:
        return (f"tls-{name}", FAIL, f"strict TLS verification failed: {exc}")
    except (TimeoutError, socket.timeout) as exc:
        return (f"tls-{name}", WARN, f"strict TLS probe timed out: {exc}")
    except OSError as exc:
        return _classify_tls_failure(name, exc)
    return (
        f"tls-{name}",
        PASS,
        "strict certificate and hostname verification succeeded",
    )


def _classify_tls_failure(name: str, reason: object) -> tuple[str, str, str]:
    if isinstance(reason, ssl.SSLCertVerificationError):
        return (
            f"tls-{name}",
            FAIL,
            f"strict certificate/hostname verification failed: {reason}",
        )
    if isinstance(reason, ssl.SSLError):
        return (f"tls-{name}", FAIL, f"strict TLS verification failed: {reason}")
    if isinstance(reason, socket.gaierror):
        category = "DNS"
    elif isinstance(reason, (TimeoutError, socket.timeout)):
        category = "timeout"
    elif "proxy" in str(reason).lower() or "tunnel" in str(reason).lower():
        category = "proxy"
    else:
        category = "network"
    return (
        f"tls-{name}",
        WARN,
        f"strict TLS certificate/hostname verification probe could not complete ({category}): {reason}",
    )
