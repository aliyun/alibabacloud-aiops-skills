#!/usr/bin/env python3
"""Request the IDaaS token endpoint with an ECS PKCS#7 signature to verify M2M token issuance.

Usage: test_m2m_token.py <instance_endpoint> <client_id> <cred_name> <scope> <assertion_file>
  instance_endpoint: Instance DefaultEndpoint (the host returned by GetInstance), without https://.
  Custom domains require --region <region> --instance-id <iid>; the host is checked
  against GetInstance before any assertion is transmitted.
  client_id:         M2M client application ID (app_xxx).
  cred_name:         Application federated credential name (application_federated_credential_name).
  scope:             <ResourceServerIdentifier>|<ScopeValue>, e.g. api:/mcp.server.com|.all.
                     Preserve slashes exactly as registered; do not normalize them.
                     .all is a wildcard for all scopes.
  assertion_file:    Signature file (PEM or single-line base64; delimiters and line breaks
                     are removed automatically).

Output: HTTP response with tokens automatically redacted (first 12 characters and
        total length only). Error responses without sensitive values are printed unchanged
        for troubleshooting. Successful responses also include ---TOKEN_SUMMARY---
        with decoded JWT claims.

Redaction must occur in script stdout: stdout enters the agent context, transcript,
and telemetry as-is. Printing a complete bearer token constitutes a leak; it can be
used to exchange for STS credentials through PAM while valid.
"""
import argparse
import base64
import ipaddress
import json
import re
import subprocess
import sys
import time
from pathlib import Path

from common import run_aliyun

TOKEN_PREFIX_LEN = 12
SENSITIVE_FIELDS = ("access_token", "refresh_token", "id_token")


def redact_token(value: str) -> str:
    # Never expose a short token in full merely because it fits the prefix.
    prefix = value[:min(TOKEN_PREFIX_LEN, max(0, len(value) - 4))]
    return f"{prefix}...(redacted, {len(value)} characters total)"


def redact_body(body: str) -> str:
    """Redact successful responses; preserve error responses without token fields for troubleshooting."""
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return body.strip()
    def scrub(value):
        if isinstance(value, dict):
            return {key: redact_token(item) if key in SENSITIVE_FIELDS and isinstance(item, str) and item
                    else scrub(item) for key, item in value.items()}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value
    d = scrub(d)
    return json.dumps(d, ensure_ascii=False, indent=2)


def normalize_assertion(path: str) -> str:
    p = Path(path)
    if not p.is_file():
        sys.exit(f"ERROR: Signature file not found: {path}")
    raw = p.read_text()
    # Remove PEM delimiters and all whitespace to obtain single-line base64 (verified format).
    sig = "".join(l for l in raw.splitlines() if not l.startswith("-----"))
    sig = re.sub(r"\s+", "", sig)
    if not sig:
        sys.exit("ERROR: Signature file is empty")
    return sig


def validate_endpoint(endpoint: str, *, region=None, instance_id=None) -> None:
    # Accept a bare DNS host only: never URLs, credentials, ports, paths or IPs.
    label = r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    if len(endpoint) > 253 or not re.fullmatch(rf"{label}(?:\.{label})+", endpoint):
        sys.exit("ERROR: Token endpoint must be a lowercase bare DNS hostname")
    try:
        ipaddress.ip_address(endpoint)
    except ValueError:
        pass
    else:
        sys.exit("ERROR: Token endpoint must not be an IP address")
    if bool(region) != bool(instance_id):
        sys.exit("ERROR: Supply both --region and --instance-id for endpoint verification")
    if region and instance_id:
        if not re.fullmatch(r"idaas_[a-z0-9]+", instance_id):
            sys.exit("ERROR: Invalid IDaaS instance ID")
        result = run_aliyun(["eiam", "get-instance", "--region", region,
                             "--instance-id", instance_id])
        actual = result.get("Instance", {}).get("DefaultEndpoint", {}).get("Endpoint")
        if endpoint != actual:
            sys.exit("ERROR: Token endpoint differs from GetInstance DefaultEndpoint")
    elif not endpoint.endswith(".aliyunidaas.com"):
        sys.exit("ERROR: Custom endpoints require --region and --instance-id for GetInstance verification")


def post_token(endpoint: str, form: dict, sig: str, *, region=None, instance_id=None):
    validate_endpoint(endpoint, region=region, instance_id=instance_id)
    args = [
        "curl", "-sS", "--request", "POST",
        "--url", f"https://{endpoint}/api/v2/iauths_system/oauth2/token",
        "--header", "Content-Type: application/x-www-form-urlencoded",
        "--data-urlencode", f"grant_type=client_credentials",
        "--data-urlencode", f"client_id={form['client_id']}",
        "--data-urlencode",
        "client_assertion_type=urn:cloud:idaas:params:oauth:client-assertion-type:pkcs7-bearer",
        "--data-urlencode", f"client_assertion={sig}",
        "--data-urlencode", f"scope={form['scope']}",
        "--data-urlencode",
        f"application_federated_credential_name={form['cred_name']}",
        "-w", "\nHTTP_STATUS=%{http_code}",
    ]
    try:
        p = subprocess.run(args, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        sys.exit("ERROR: Token request timed out after 60 seconds; check connectivity before retrying")
    except OSError:
        sys.exit("ERROR: Cannot run curl; install it and check the execution environment")
    if p.returncode:
        sys.exit(f"ERROR: Token request failed (curl exit={p.returncode}); check network and certificate trust")
    return p.stdout or ""


def summarize(body: str) -> None:
    try:
        d = json.loads(body)
    except json.JSONDecodeError:
        return
    if not isinstance(d, dict) or not isinstance(d.get("access_token"), str):
        return
    parts = d["access_token"].split(".")
    if len(parts) < 2:
        return
    pad = lambda s: base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
    try:
        pl = json.loads(pad(parts[1]))
    except Exception:
        return
    if not isinstance(pl, dict):
        return
    def fmt(timestamp):
        try:
            return time.strftime("%F %T", time.localtime(int(timestamp)))
        except (ValueError, TypeError, OverflowError, OSError):
            return "unavailable"
    tok = d["access_token"]
    print("---TOKEN_SUMMARY---")
    print("access_token:", redact_token(tok))
    print("sub:", pl.get("sub"), "| aud:", pl.get("aud"))
    print("scope:", pl.get("scope"))
    print("Validity:", fmt(pl.get("iat", 0)), "→", fmt(pl.get("exp", 0)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("endpoint", "client_id", "cred_name", "scope", "assertion_file"):
        parser.add_argument(name)
    parser.add_argument("--region")
    parser.add_argument("--instance-id")
    opts = parser.parse_args()
    endpoint, client_id, cred_name, scope, sig_file = (
        opts.endpoint, opts.client_id, opts.cred_name, opts.scope, opts.assertion_file)
    sig = normalize_assertion(sig_file)
    form = {"client_id": client_id, "cred_name": cred_name, "scope": scope}

    resp = post_token(endpoint, form, sig, region=opts.region, instance_id=opts.instance_id)

    body = resp.rsplit("HTTP_STATUS=", 1)[0]
    status = resp.rsplit("HTTP_STATUS=", 1)[1].strip() if "HTTP_STATUS=" in resp else "?"
    print(redact_body(body))
    print(f"HTTP_STATUS={status}")
    if not status.isdigit() or not 200 <= int(status) < 300:
        sys.exit(1)
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        sys.exit("ERROR: Token endpoint returned a non-JSON success response")
    if not isinstance(result, dict) or not isinstance(result.get("access_token"), str) or not result["access_token"]:
        sys.exit("ERROR: Token endpoint response contains no access_token")
    summarize(body)


if __name__ == "__main__":
    main()
