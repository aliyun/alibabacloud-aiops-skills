#!/usr/bin/env python3
"""Shared client module for the Flink Ververica CLI.

Provides:
- SDK client initialization (default credential chain + Region to Endpoint)
- Formatted output (JSON, table, or text)
- Safety confirmation (interactive TTY prompt or non-TTY error)
- Standard response envelopes
- Input validation utilities
"""

import json
import os
import re
import sys
import traceback
from pathlib import Path

# ---------------------------------------------------------------------------
# SDK client
# ---------------------------------------------------------------------------

_CLIENT_CACHE: dict = {}

DEFAULT_USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-flink-sql-skill"
ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SCOPE_CONFIG = ROOT_DIR / "assets" / "flink-sql-manager.json"
MANIFEST_PATH = ROOT_DIR / "references" / "manifest.json"


class SkillIdentityError(ValueError):
    """Stop cloud requests when the skill identity cannot be established."""


def scope_config_path() -> Path:
    """Return the path to the non-sensitive local scope configuration."""
    configured = os.environ.get("FLINK_SQL_MANAGER_CONFIG", "").strip()
    return Path(configured).expanduser() if configured else DEFAULT_SCOPE_CONFIG


def load_scope_config():
    """Load Workspace scope defaults without reading or storing credentials."""
    path = scope_config_path()
    if not path.exists():
        return {}, path, ""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {}, path, f"Unable to load the scope configuration: {exc}"
    if not isinstance(raw, dict):
        return {}, path, "The scope configuration must contain a JSON object."
    return raw, path, ""


def apply_scope_defaults(args):
    """Resolve scope from CLI arguments, environment variables, then local configuration."""
    config, path, config_error = load_scope_config()
    setattr(args, "_scope_config_path", str(path))
    setattr(args, "_scope_config_error", config_error)
    setattr(args, "_scope_sources", {})

    fields = (
        ("workspace", "FLINK_WORKSPACE", "workspace"),
        ("namespace", "FLINK_NAMESPACE", "namespace"),
        ("region_id", "FLINK_REGION_ID", "region_id"),
    )
    for attr, env_name, config_key in fields:
        if not hasattr(args, attr):
            continue
        current = getattr(args, attr, None)
        if isinstance(current, str) and current.strip():
            args._scope_sources[attr] = "command line"
            continue
        env_value = os.environ.get(env_name, "").strip()
        config_value = config.get(config_key)
        if env_value:
            setattr(args, attr, env_value)
            args._scope_sources[attr] = env_name
        elif isinstance(config_value, str) and config_value.strip():
            setattr(args, attr, config_value.strip())
            args._scope_sources[attr] = str(path)


def build_user_agent() -> str:
    """Read this skill's manifest on each call; never reuse another skill's UA."""
    try:
        manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SkillIdentityError("Cannot read references/manifest.json; restore the skill manifest before retrying.") from exc
    version = manifest.get("version") if isinstance(manifest, dict) else None
    if (not isinstance(version, str)
            or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.-]+)?", version)
            or manifest.get("name") != "alibabacloud-flink-sql-skill"):
        raise SkillIdentityError("Invalid skill name or version in references/manifest.json; repair it before retrying.")
    session_id = os.environ.get("SKILL_SESSION_ID", "")
    if not re.fullmatch(r"[0-9a-f]{32}", session_id):
        raise SkillIdentityError("Set SKILL_SESSION_ID to one 32-character lowercase hexadecimal ID per Agent session.")
    return f"{DEFAULT_USER_AGENT}/{session_id} skill-version/{version}"


def get_client(region_id: str):
    """Return the cached Ververica API client for *region_id*.

    Use the Alibaba Cloud default credential chain, such as a RAM Role or CLI Profile.
    """
    user_agent = build_user_agent()
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_ververica20220718.client import Client
    from alibabacloud_tea_openapi.models import Config

    cache_key = (region_id, user_agent)
    if cache_key in _CLIENT_CACHE:
        return _CLIENT_CACHE[cache_key]

    if not region_id:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "ValidationError",
                        "message": "region_id is required.",
                    },
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        credential = CredentialClient()
    except Exception as e:
        print(
            json.dumps(
                {
                    "success": False,
                    "error": {
                        "code": "MissingCredentials",
                        "message": f"Failed to resolve credentials: {e}",
                    },
                }
            ),
            file=sys.stderr,
        )
        sys.exit(1)

    config = Config(
        credential=credential,
        endpoint=f"ververica.{region_id}.aliyuncs.com",
        user_agent=user_agent,
    )
    client = Client(config)
    _CLIENT_CACHE[cache_key] = client
    return client


def runtime_options():
    """Return a new ``RuntimeOptions`` instance with explicit timeouts.

    Tea/Darabonba SDK Core interprets these values in milliseconds and divides
    them by 1,000 before passing them to the HTTP layer.

    Default timeouts in milliseconds, overridable through environment variables:
    - ``connect_timeout``: 10,000 ms (``FLINK_SDK_CONNECT_TIMEOUT``)
    - ``read_timeout``: 60,000 ms (``FLINK_SDK_READ_TIMEOUT``)
    """
    from alibabacloud_tea_util.models import RuntimeOptions

    # Allow environment variables to override timeouts in milliseconds.
    connect_timeout = int(os.environ.get("FLINK_SDK_CONNECT_TIMEOUT", "10000"))
    read_timeout = int(os.environ.get("FLINK_SDK_READ_TIMEOUT", "60000"))

    return RuntimeOptions(
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )


# ---------------------------------------------------------------------------
# Standard response helpers
# ---------------------------------------------------------------------------


def success_response(operation: str, data, request_id: str = ""):
    """Build a successful response envelope."""
    return {
        "success": True,
        "operation": operation,
        "data": data,
        "request_id": request_id,
    }


def error_response(operation: str, code: str, message: str, request_id: str = ""):
    """Build an error response envelope."""
    return {
        "success": False,
        "operation": operation,
        "error": {"code": code, "message": message},
        "request_id": request_id,
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------


def output(result: dict, fmt: str = "json"):
    """Write the *result* response envelope to stdout in the requested format."""
    if fmt == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif fmt == "table":
        _print_table(result)
    elif fmt == "text":
        _print_text(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))

    sys.exit(0 if result.get("success") else 1)


def _print_table(result: dict):
    """Format *result* as an aligned table."""
    if not result.get("success"):
        err = result.get("error", {})
        print(
            f"Error [{err.get('code', '?')}]: {err.get('message', '?')}",
            file=sys.stderr,
        )
        return

    data = result.get("data")
    if data is None:
        print("(no data)")
        return

    # If data is a dictionary containing a list, use the first list found.
    rows = _extract_rows(data)
    if rows is None:
        # Single-object result.
        for k, v in (data if isinstance(data, dict) else {}).items():
            print(f"{k}: {v}")
        return

    if not rows:
        print("(empty)")
        return

    # Collect columns from the first row.
    if isinstance(rows[0], dict):
        cols = list(rows[0].keys())
        widths = {c: len(c) for c in cols}
        str_rows = []
        for r in rows:
            sr = {}
            for c in cols:
                val = str(r.get(c, ""))
                sr[c] = val
                widths[c] = max(widths[c], len(val))
            str_rows.append(sr)

        header = "  ".join(c.upper().ljust(widths[c]) for c in cols)
        print(header)
        for sr in str_rows:
            print("  ".join(sr[c].ljust(widths[c]) for c in cols))
    else:
        for r in rows:
            print(r)


def _print_text(result: dict):
    """Write tab-separated values suitable for pipelines."""
    if not result.get("success"):
        err = result.get("error", {})
        print(f"{err.get('code', '?')}\t{err.get('message', '?')}", file=sys.stderr)
        return

    data = result.get("data")
    if data is None:
        return

    rows = _extract_rows(data)
    if rows is None:
        if isinstance(data, dict):
            for k, v in data.items():
                print(f"{k}\t{v}")
        return

    for r in rows:
        if isinstance(r, dict):
            print("\t".join(str(v) for v in r.values()))
        else:
            print(r)


def _extract_rows(data):
    """Try to locate a list of records in *data*."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for v in data.values():
            if isinstance(v, list):
                return v
    return None


# ---------------------------------------------------------------------------
# Safety confirmation
# ---------------------------------------------------------------------------


def require_confirmation(
    operation: str,
    message: str,
    flag_present: bool,
):
    """Check the safety confirmation gate.

    When *flag_present* is true, the caller supplied ``--confirm`` and execution
    may continue. Otherwise, prompt in an interactive TTY or return an error in
    a non-interactive pipeline or Agent environment.

    Return ``None`` when execution may continue, or an error dictionary when
    the caller must stop and report the error.
    """
    if flag_present:
        return None  # Continue.

    if sys.stdin.isatty() and sys.stdout.isatty():
        # Interactive mode: ask the user.
        print(f"\n\u26a0\ufe0f  {message}", file=sys.stderr)
        answer = input("    Continue? [y/N]: ")
        if answer.strip().lower() in ("y", "yes"):
            return None
        return error_response(operation, "Cancelled", "The user cancelled the operation.")

    # Non-interactive mode: return a hard error.
    return error_response(
        operation,
        "SafetyCheckRequired",
        f"{message} Add --confirm to continue.",
    )


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def require_args(args, *names):
    """Require every *name* in *args* to be present and non-empty.

    Return ``None`` on success, or an error dictionary describing the first
    missing argument.
    """
    for name in names:
        val = getattr(args, name, None)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return error_response(
                getattr(args, "subcommand", "unknown"),
                "ValidationError",
                f"Argument '--{name}' is required.",
            )
    return None


# ---------------------------------------------------------------------------
# Common API call wrapper
# ---------------------------------------------------------------------------


def call_api(operation: str, api_func, *api_args, **api_kwargs):
    """Call *api_func* and wrap the result in a standard response.

    Handle SDK exceptions and business failures, including HTTP 200 responses.
    """
    try:
        user_agent = build_user_agent()
        sdk_client = getattr(api_func, "__self__", None)
        if sdk_client is not None:
            sdk_client._user_agent = user_agent
        resp = api_func(*api_args, **api_kwargs)
        # SDK responses expose .body, .headers, and .status_code.
        body = resp.body if hasattr(resp, "body") else resp
        request_id = ""
        if hasattr(resp, "headers") and resp.headers:
            request_id = resp.headers.get("x-acs-request-id", "")
        if hasattr(body, "request_id") and body.request_id:
            request_id = body.request_id

        # Convert the body to a plain dictionary.
        data = _to_dict(body)
        if isinstance(data, dict):
            request_id = data.get("requestId") or request_id
            if data.get("success") is False:
                result = error_response(
                    operation,
                    str(data.get("errorCode") or "ApiError"),
                    str(data.get("errorMessage") or "The API reported a business failure."),
                    request_id,
                )
                result["data"] = data
                return result
        return success_response(operation, data, request_id)
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
        message = getattr(e, "message", str(e))
        request_id = getattr(e, "request_id", "")
        if os.environ.get("FLINK_CLI_DEBUG"):
            traceback.print_exc(file=sys.stderr)
        return error_response(operation, str(code), str(message), str(request_id))


def _to_dict(obj):
    """Recursively convert an SDK Model object to a plain dictionary."""
    if obj is None:
        return None
    if isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if hasattr(obj, "to_map"):
        return _to_dict(obj.to_map())
    if hasattr(obj, "__dict__"):
        return _to_dict(
            {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        )
    return str(obj)


# ---------------------------------------------------------------------------
# Common argparse helpers
# ---------------------------------------------------------------------------


def add_common_args(parser):
    """Add the -w, -n, -r, -o, -v, and -q global arguments to *parser*."""
    # Keep common scope arguments optional in argparse so handlers can always
    # return structured JSON validation errors through require_args().
    parser.add_argument("-w", "--workspace", help="Workspace ID")
    parser.add_argument("-n", "--namespace", help="Namespace name")
    parser.add_argument(
        "-r", "--region_id", help="Region ID (for example, cn-beijing)"
    )
    parser.add_argument(
        "-o",
        "--output",
        choices=["json", "table", "text"],
        default="json",
        help="Output format (default: json)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show request details"
    )
    parser.add_argument(
        "-q", "--quiet", action="store_true", help="Hide status messages"
    )
