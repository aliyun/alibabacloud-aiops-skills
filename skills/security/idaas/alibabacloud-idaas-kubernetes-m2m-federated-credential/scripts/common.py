#!/usr/bin/env python3
"""Shared skill utilities: aliyun CLI / kubectl invocation, JSON parsing, output conventions.

Output conventions (as described in SKILL.md):
- Print results to stdout, ending with KEY=value lines (for example FCP_ID=fcp_xxx)
  for the agent to parse.
- Print progress and warnings to stderr, keeping stdout free of those messages.
"""
import json
import secrets
import subprocess
import sys
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent

# --- Observability: version from references/manifest.json + per-process session ID ---
_MANIFEST = SKILL_ROOT / "references" / "manifest.json"


def _load_manifest() -> dict:
    try:
        return json.loads(_MANIFEST.read_text())
    except Exception:
        return {}


_manifest = _load_manifest()
_version = _manifest.get("version", "0.0.0")
_skill_name = _manifest.get("name") or SKILL_ROOT.name
_SESSION_ID = secrets.token_hex(16)
USER_AGENT = f'"AlibabaCloud-Agent-Skills/{_skill_name}/{_SESSION_ID} skill-version/{_version}"'


def info(msg: str) -> None:
    """Write progress messages to stderr."""
    print(msg, file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    """Write an error to stderr and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def run_cli(args: list, timeout: int = 60):
    """Run an external command and return CompletedProcess; callers check its exit status."""
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        die(f"Command not found: {args[0]} (install and configure the {args[0]} CLI first)")
    except subprocess.TimeoutExpired:
        die(f"Command timed out ({timeout}s): {' '.join(args[:5])}...")


def run_aliyun(args: list, timeout: int = 60) -> dict:
    """Run the aliyun CLI and parse JSON output; auto-append --user-agent if not present."""
    if "--user-agent" not in args:
        args = list(args) + ["--user-agent", USER_AGENT]
    p = run_cli(["aliyun"] + args, timeout)
    text = (p.stdout or "").strip() or (p.stderr or "").strip()
    if p.returncode != 0 and not text:
        die(f"aliyun {' '.join(args[:4])} failed with no output (exit={p.returncode})")
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # The CLI also returns JSON for errors such as Forbidden.RAM / InvalidParameter;
        # report non-JSON output as an error.
        die(f"aliyun {' '.join(args[:4])} output could not be parsed:\n{text[:800]}")
    if not isinstance(result, dict):
        die("aliyun returned an unexpected JSON value; expected an object")
    error_code = result.get("error_code") or result.get("Code")
    status = result.get("status_code") or result.get("StatusCode")
    failed_status = str(status).isdigit() and int(status) >= 400
    if p.returncode != 0 or failed_status or error_code:
        # Error responses are JSON too. Never let callers interpret them as an
        # empty successful query or continue creating dependent resources.
        detail = {
            "error_code": error_code or "CliExecutionFailed",
            "status_code": status,
            "request_id": result.get("request_id") or result.get("RequestId"),
        }
        die("aliyun API failed: " + json.dumps(detail, ensure_ascii=False))
    return result


def try_kubectl(args: list, timeout: int = 20):
    """Run kubectl for probing: never dies; returns CompletedProcess, None (unavailable),
    or the string "timeout"."""
    try:
        return subprocess.run(["kubectl"] + args, capture_output=True, text=True,
                              timeout=timeout)
    except (FileNotFoundError, PermissionError, OSError):
        # Not installed / present but not executable (common in sandboxes) → unavailable
        return None
    except subprocess.TimeoutExpired:
        info(f"kubectl timed out ({timeout}s): {' '.join(args[:4])}")
        return "timeout"


def read_jwks_file(path: str) -> str:
    """Read a JWKS JSON file, validate it has a non-empty keys array, return compact JSON."""
    p = Path(path)
    if not p.is_file():
        die(f"JWKS file not found: {path}")
    try:
        d = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        die(f"JWKS file is not valid JSON: {path} ({e})")
    keys = d.get("keys")
    if not isinstance(keys, list) or not keys:
        die(f"JWKS file has no non-empty keys array: {path}")
    return json.dumps(d, ensure_ascii=False, separators=(",", ":"))


def decode_jwt_payload(token: str) -> dict:
    """Decode a JWT payload locally (base64url); returns {} on failure. No external services."""
    import base64
    parts = token.strip().split(".")
    if len(parts) < 2:
        return {}
    try:
        pad = parts[1] + "=" * (-len(parts[1]) % 4)
        return json.loads(base64.urlsafe_b64decode(pad))
    except Exception:
        return {}


def require_args(argv: list, usage: str, n: int) -> list:
    """Check the minimum number of arguments."""
    if len(argv) < n:
        die(usage)
    return argv[:n], argv[n:]
