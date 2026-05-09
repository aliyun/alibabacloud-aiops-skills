#!/usr/bin/env python3
"""
Shared client module for Flink Ververica CLI.

Provides:
- SDK client initialization (default credential chain + region -> endpoint)
- Output formatting (json / table / text)
- Safety confirmation logic (TTY interactive prompt / non-TTY error)
- Standardized response envelope
- Input validation utilities
"""

import json
import os
import sys
import traceback

# ---------------------------------------------------------------------------
# SDK client
# ---------------------------------------------------------------------------

_CLIENT_CACHE: dict = {}

DEFAULT_USER_AGENT = "AlibabaCloud-Agent-Skills/alibabacloud-flink-workspace-ops"


def get_client(region_id: str):
    """Return a cached Ververica API client for *region_id*.

    Uses Alibaba Cloud default credential chain (RAM role, CLI profile, etc.)
    """
    from alibabacloud_credentials.client import Client as CredentialClient
    from alibabacloud_ververica20220718.client import Client
    from alibabacloud_tea_openapi.models import Config

    if region_id in _CLIENT_CACHE:
        return _CLIENT_CACHE[region_id]

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
        user_agent=DEFAULT_USER_AGENT,
    )
    client = Client(config)
    _CLIENT_CACHE[region_id] = client
    return client


def runtime_options():
    """Return a new ``RuntimeOptions`` instance with explicit timeout configuration.

    Timeout defaults (can be overridden via environment variables):
    - connect_timeout: 10 seconds (FLINK_SDK_CONNECT_TIMEOUT)
    - read_timeout: 60 seconds (FLINK_SDK_READ_TIMEOUT)
    """
    from alibabacloud_tea_util.models import RuntimeOptions

    # Allow environment variable override for timeout settings
    connect_timeout = int(os.environ.get("FLINK_SDK_CONNECT_TIMEOUT", "10"))
    read_timeout = int(os.environ.get("FLINK_SDK_READ_TIMEOUT", "60"))

    return RuntimeOptions(
        connect_timeout=connect_timeout,
        read_timeout=read_timeout,
    )


# ---------------------------------------------------------------------------
# Standardised response helpers
# ---------------------------------------------------------------------------


def success_response(operation: str, data, request_id: str = ""):
    """Build a success envelope dict."""
    return {
        "success": True,
        "operation": operation,
        "data": data,
        "request_id": request_id,
    }


def error_response(operation: str, code: str, message: str, request_id: str = ""):
    """Build an error envelope dict."""
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
    """Print *result* envelope to stdout in the requested format."""
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
    """Pretty-print *result* as an aligned table."""
    if not result.get("success"):
        err = result.get("error", {})
        print(
            f"ERROR [{err.get('code', '?')}]: {err.get('message', '?')}",
            file=sys.stderr,
        )
        return

    data = result.get("data")
    if data is None:
        print("(no data)")
        return

    # If data is a dict containing a list value, use the first list found
    rows = _extract_rows(data)
    if rows is None:
        # single-object result
        for k, v in (data if isinstance(data, dict) else {}).items():
            print(f"{k}: {v}")
        return

    if not rows:
        print("(empty)")
        return

    # Collect columns from first row
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
    """Print tab-separated values suitable for piping."""
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
    """Try to find a list of records inside *data*."""
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
    """
    Check the safety confirmation gate.

    If *flag_present* is True the caller already passed --confirm
    and we proceed silently.

    Otherwise:
      - In an interactive TTY → prompt the user.
      - In a non-interactive pipe / agent context → return an error dict.

    Returns None on success (proceed) or an error-dict to output and abort.
    """
    if flag_present:
        return None  # OK

    if sys.stdin.isatty() and sys.stdout.isatty():
        # Interactive mode – ask the user
        print(f"\n\u26a0\ufe0f  {message}", file=sys.stderr)
        answer = input("    Proceed? [y/N]: ")
        if answer.strip().lower() in ("y", "yes"):
            return None
        return error_response(operation, "Cancelled", "User cancelled the operation.")

    # Non-interactive – hard error
    return error_response(
        operation,
        "SafetyCheckRequired",
        f"{message} Add --confirm to proceed.",
    )


# ---------------------------------------------------------------------------
# Input validation helpers
# ---------------------------------------------------------------------------


def require_args(args, *names):
    """
    Validate that every *name* is present (not None / empty) on *args*.
    Returns None if OK, or an error-dict describing the first missing param.
    """
    for name in names:
        val = getattr(args, name, None)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            return error_response(
                getattr(args, "subcommand", "unknown"),
                "ValidationError",
                f"Parameter '--{name}' is required.",
            )
    return None


# ---------------------------------------------------------------------------
# Generic API call wrapper
# ---------------------------------------------------------------------------


def call_api(operation: str, api_func, *api_args, **api_kwargs):
    """
    Invoke *api_func* and wrap the result in a standard envelope.

    Handles SDK exceptions and returns a uniform error envelope.
    """
    try:
        resp = api_func(*api_args, **api_kwargs)
        # SDK responses expose .body / .headers / .status_code
        body = resp.body if hasattr(resp, "body") else resp
        request_id = ""
        if hasattr(resp, "headers") and resp.headers:
            request_id = resp.headers.get("x-acs-request-id", "")
        if hasattr(body, "request_id") and body.request_id:
            request_id = body.request_id

        # Convert body to plain dict
        data = _to_dict(body)
        return success_response(operation, data, request_id)
    except Exception as e:
        code = getattr(e, "code", type(e).__name__)
        message = getattr(e, "message", str(e))
        request_id = getattr(e, "request_id", "")
        if os.environ.get("FLINK_CLI_DEBUG"):
            traceback.print_exc(file=sys.stderr)
        return error_response(operation, str(code), str(message), str(request_id))


def _to_dict(obj):
    """Recursively convert SDK model objects to plain dicts."""
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
    """Add -w / -n / -r / -o / -v / -q global flags to *parser*."""
    # Keep common scope flags optional at argparse level so handlers can always
    # return structured JSON validation errors via require_args().
    parser.add_argument("-w", "--workspace", help="Workspace ID")
    parser.add_argument("-n", "--namespace", help="Namespace name")
    parser.add_argument(
        "-r", "--region_id", help="Region ID (e.g. cn-beijing)"
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
        "-q", "--quiet", action="store_true", help="Suppress status messages"
    )
