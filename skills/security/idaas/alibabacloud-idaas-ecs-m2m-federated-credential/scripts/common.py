#!/usr/bin/env python3
"""Shared skill utilities: aliyun CLI calls, JSON parsing, and output conventions.

Output conventions (as described in SKILL.md):
- Print results to stdout, ending with KEY=value (for example FCP_ID=fcp_xxx)
  for the agent to parse.
- Print progress and warnings to stderr, keeping stdout free of those messages.
"""
import json
import os
import re
import secrets
import subprocess
import sys
import time
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = SKILL_ROOT / "assets"
CERT_FILE = ASSETS_DIR / "alibaba_cloud_pkcs7_cert.pem"

# The agent exports one session ID for the entire workflow. Standalone calls
# receive their own ID; a missing manifest never silently changes the version.
_MANIFEST = SKILL_ROOT / "references" / "manifest.json"
try:
    _version = json.loads(_MANIFEST.read_text())["version"]
    if not isinstance(_version, str) or not _version.strip():
        raise ValueError("empty version")
except (OSError, ValueError, KeyError) as exc:
    sys.exit(f"ERROR: Restore a valid references/manifest.json before running scripts: {exc}")
_SESSION_ID = os.environ.get("SKILL_SESSION_ID", secrets.token_hex(16))
if not re.fullmatch(r"[0-9a-f]{32}", _SESSION_ID):
    sys.exit("ERROR: SKILL_SESSION_ID must be 32 lowercase hexadecimal characters")
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-idaas-ecs-m2m-federated-credential/{_version}/{_SESSION_ID}"

# Supported EIAM regions for input pre-validation
SUPPORTED_REGIONS = [
    "cn-hangzhou", "cn-beijing", "cn-hongkong",
    "ap-southeast-1", "ap-southeast-5", "ap-northeast-2",
    "eu-central-1",
]

# Provider name pattern: lowercase letters, digits, underscore, hyphen; max 64 chars
PROVIDER_NAME_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
# General name pattern: max 64 characters
GENERAL_NAME_MAX = 64

# Error classification patterns (matched against CLI JSON error output)
_THROTTLING_RE = re.compile(r"Throttling", re.IGNORECASE)
_SYSTEM_ERROR_RE = re.compile(
    r"(InternalError|ServiceUnavailable|HTTPDNS|ConnectionTimeout)",
    re.IGNORECASE,
)
_PERMISSION_RE = re.compile(r"(Forbidden\.RAM|Forbidden\.Access|NoPermission)", re.IGNORECASE)
_PARAMETER_RE = re.compile(r"(Invalid|MissingParameter|NameAlreadyExists)", re.IGNORECASE)


class CloudError(SystemExit):
    """Preserve the service code for narrow, explicit fallback handling."""

    def __init__(self, code: str, message: str, request_id: str = ""):
        self.error_code = code
        super().__init__(f"ERROR: {code}: {message} (request_id={request_id or 'unavailable'})")


def info(msg: str) -> None:
    """Write progress messages to stderr."""
    print(msg, file=sys.stderr)


def die(msg: str, code: int = 1) -> None:
    """Write an error to stderr and exit."""
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(code)


def classify_error(text: str) -> str:
    """Classify an API error string into a category.

    Unknown errors remain unknown; do not blame user parameters without evidence.
    """
    if _PERMISSION_RE.search(text):
        return "permission"
    if _THROTTLING_RE.search(text):
        return "throttling"
    if _SYSTEM_ERROR_RE.search(text):
        return "system"
    if _PARAMETER_RE.search(text):
        return "parameter"
    return "unknown"


def run_cli(args: list, timeout: int = 60):
    """Run an external command and return CompletedProcess; callers check its exit status."""
    if args and args[0] == "aliyun" and "--user-agent" not in args:
        args = list(args) + ["--user-agent", _USER_AGENT]
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        die(f"Command not found: {args[0]} (install and configure the aliyun CLI first)")
    except subprocess.TimeoutExpired:
        die(f"Command timed out ({timeout}s): {' '.join(args[:5])}...")


def run_aliyun(args: list, timeout: int = 60, max_retries: int = 3) -> dict:
    """Parse object responses; retry transient read failures, never replay writes.

    A write can have succeeded even when its response is lost. The agent must
    reconcile the recorded resources before retrying a create, grant or delete.
    """
    if len(args) < 2:
        die("aliyun product and action are required")
    if args[0] == "eiam" and "--region" in args:
        validate_region(args[args.index("--region") + 1])
    if "--user-agent" not in args:
        args = list(args) + ["--user-agent", _USER_AGENT]
    action = args[1].replace("-", "").lower()
    retry_limit = max_retries if action.startswith(("get", "list", "describe", "check")) else 0
    for attempt in range(retry_limit + 1):
        p = run_cli(["aliyun"] + args, timeout)
        text = (p.stdout or "").strip() or (p.stderr or "").strip()
        try:
            data = parse_cli_json(text, args[0])
        except json.JSONDecodeError:
            # CLI SDK errors also use labeled text on stderr. Keep their code
            # and request ID so permission fallback and diagnostics still work.
            diagnostic = p.stderr or text
            fields = dict(re.findall(r"(?m)^\s*(ErrorCode|RequestId|Message):\s*([^\n]*)", diagnostic))
            sdk_data = None
            for payload in re.findall(r"(?m)^\s*Data:\s*(\{[^\n]*\})\s*$", diagnostic):
                try:
                    candidate = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                if isinstance(candidate, dict) and candidate.get("Code") and candidate.get("RequestId"):
                    sdk_data = candidate
                    break
            if p.returncode and sdk_data is not None:
                data = sdk_data
            elif p.returncode and fields.get("ErrorCode"):
                data = {"Code": fields["ErrorCode"].strip(),
                        "RequestId": fields.get("RequestId", "").strip(),
                        "Message": fields.get("Message", "Cloud request failed").strip()}
            else:
                die(f"aliyun {args[0]} {args[1]} returned non-JSON output (exit={p.returncode}); check CLI configuration and connectivity")
        if not isinstance(data, dict):
            die(f"aliyun {args[0]} {args[1]} returned a non-object response")
        code = data.get("Code") or data.get("code") or data.get("error_code")
        status = data.get("status_code", data.get("StatusCode"))
        http_error = str(status).isdigit() and int(status) >= 400
        service_error = code and str(code).lower() not in ("success", "200")
        failed = p.returncode != 0 or http_error or service_error
        if not failed:
            return data
        err_cat = classify_error(str(code or ""))
        if not service_error and str(status) == "429":
            err_cat = "throttling"
        elif not service_error and str(status).isdigit() and 500 <= int(status) < 600:
            err_cat = "system"
        if (err_cat == "throttling" and attempt < retry_limit) or (err_cat == "system" and attempt < min(2, retry_limit)):
            wait = 5 * (2 ** attempt) if err_cat == "throttling" else 3
            info(f"Transient read error, retrying in {wait}s (attempt {attempt + 1}/{retry_limit})...")
            time.sleep(wait)
            continue
        raise CloudError(str(code if service_error else (f"HTTP.{status}" if http_error else f"CLI.Exit{p.returncode}")),
                         str(data.get("Message") or data.get("message") or "Cloud request failed"),
                         str(data.get("RequestId") or data.get("request_id") or ""))


def parse_cli_json(text: str, product: str):
    """Accept JSON after the CLI's known first-install status lines only.

    Some released CLI builds print plugin installation progress on stdout.
    Do not search arbitrary prose for a JSON fragment or replay the request:
    the original cloud call may already have completed.
    """
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        lines = text.splitlines()
        plugin = re.escape(f"aliyun-cli-{product}")
        version = r"v?\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?"
        status = re.compile(
            rf"(?:Downloading {plugin} {version}\.\.\.|"
            rf"Plugin {plugin} {version} installed successfully!)"
        )
        consumed = 0
        while consumed < len(lines) and status.fullmatch(lines[consumed]):
            consumed += 1
        if not consumed:
            raise
        # json.loads still rejects trailing messages, multiple responses and
        # malformed bodies; normal error-envelope checks remain with the caller.
        return json.loads("\n".join(lines[consumed:]))


def list_all_pages(args: list, collection: str, id_field: str, page_size: int = 100) -> list:
    """Read numbered pages completely; reject incomplete or unstable results."""
    rows = []
    ids = set()
    expected_total = None
    for page in range(1, 1001):
        data = run_aliyun(args + ["--page-number", str(page), "--page-size", str(page_size)])
        values = data
        for key in collection.split("."):
            values = values.get(key) if isinstance(values, dict) else None
        total = data.get("TotalCount")
        if not isinstance(values, list) or type(total) is not int or total < 0:
            die(f"{args[1]} returned an incomplete list response")
        if expected_total is not None and total != expected_total:
            die(f"{args[1]} resource count changed during pagination; rerun the query")
        expected_total = total
        for value in values:
            resource_id = value.get(id_field) if isinstance(value, dict) else None
            if not isinstance(resource_id, str) or not resource_id or resource_id in ids:
                die(f"{args[1]} returned missing or repeated resource IDs")
            ids.add(resource_id)
            rows.append(value)
        if len(rows) == total:
            return rows
        if not values or len(rows) > total:
            die(f"{args[1]} pagination did not match TotalCount")
    die(f"{args[1]} exceeded the pagination limit")


def load_cert() -> str:
    """Read the bundled official Alibaba Cloud PKCS#7 root certificate."""
    if not CERT_FILE.is_file():
        die(f"Bundled certificate file is missing: {CERT_FILE}")
    return CERT_FILE.read_text()


def validate_region(region: str) -> None:
    """Validate that the region is in the EIAM supported list; die if not."""
    if region not in SUPPORTED_REGIONS:
        die(
            f"Region '{region}' is not supported by EIAM. "
            f"Supported regions: {', '.join(SUPPORTED_REGIONS)}"
        )


def validate_provider_name(name: str) -> None:
    """Validate provider name format [a-z0-9_-]{1,64}; die if invalid."""
    if not PROVIDER_NAME_RE.match(name):
        die(
            f"Provider name '{name}' is invalid. "
            f"Must match [a-z0-9_-]{{1,64}} (lowercase letters, digits, underscore, hyphen; max 64 characters)."
        )


def validate_general_name(name: str, label: str = "name") -> None:
    """Validate that a general name (application, credential) is ≤64 characters."""
    if not name or len(name) > GENERAL_NAME_MAX:
        die(f"{label} '{name}' is invalid. Must be 1–{GENERAL_NAME_MAX} characters.")
