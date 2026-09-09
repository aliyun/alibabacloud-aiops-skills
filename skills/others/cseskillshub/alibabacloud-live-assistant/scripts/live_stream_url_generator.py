#!/usr/bin/env python3
"""
Generate Alibaba Cloud Live ingest/playback test URLs.

Workflow:
1. Call DescribeLiveDomainMapping (aliyun CLI) to determine whether the
   input domain is an ingest (publish) or playback (vhost) domain
2. Call DescribeLiveDomainConfigs (aliyun CLI) to query the aliauth config
3. Generate ingest/playback URLs based on the authentication type

Cloud API access goes through the aliyun CLI (plugin mode) with the caller's
locally configured credentials. No SDK or token exchange is used.

Output format: JSON
"""

import argparse
import copy
import hashlib
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone

# ===== Configuration constants =====

# Per-run session id for platform-level tracing (Observability)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-live-assistant/{_SESSION_ID}"
CLI_TIMEOUT = 60


# ===== aliyun CLI helpers =====

# Parameter names whose values are secrets and must never be echoed verbatim.
_SECRET_PARAM_NAMES = (
    r"auth_key\d*|authkey|accesskeysecret|access_key_secret|secret[_-]?key"
    r"|security[_-]?token|sts[_-]?token|signature"
)

# Non-alphanumeric delimiters end a raw value in query strings and JSON text.
_SECRET_PAIR = r'(\b(?:{names})\s*[=:]\s*)("?)([^\s"\',;&]{{4,}})\2'


def redact_secrets(text):
    """Mask secret values in free-form CLI text before anything is printed.

    Applied unconditionally to CLI stdout/stderr: the aliyun CLI can prepend
    plugin-install banners that break JSON parsing, which bypasses
    mask_auth_config() and would otherwise echo raw auth keys.
    """
    s = str(text)
    # DescribeLiveDomainConfigs shape: {"ArgName": "auth_key1", "ArgValue": "<secret>"}
    s = re.sub(
        r'("ArgName"\s*:\s*"auth_key\d?"[^{}]*?"ArgValue"\s*:\s*")([^"]*)(")',
        r'\1****\3', s)
    s = re.sub(
        r'("ArgValue"\s*:\s*")([^"]*)("[^{}]*?"ArgName"\s*:\s*"auth_key\d?")',
        r'\1****\3', s)
    # Plain "name": "value" JSON members
    s = re.sub(
        '("%s"\\s*:\\s*")([^"]*)(")' % _SECRET_PARAM_NAMES,
        r'\1****\3', s, flags=re.I)
    # name=value (URL query) and name: value (log lines)
    s = re.sub(
        _SECRET_PAIR.format(names=_SECRET_PARAM_NAMES),
        r'\1\2****', s, flags=re.I)
    return s


def run_aliyun_cli(cli_args, timeout=CLI_TIMEOUT):
    """Run an aliyun CLI command (plugin mode) and parse the JSON output.

    Every invocation carries a per-session --user-agent for tracing.
    """
    cmd = ["aliyun"] + cli_args + ["--user-agent", _USER_AGENT]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"aliyun CLI timed out after {timeout}s: {' '.join(cli_args[:2])}") from e
    except FileNotFoundError as e:
        raise RuntimeError(
            "aliyun CLI not found. Install the Aliyun CLI and the 'aliyun-cli-live' plugin first."
        ) from e

    if proc.returncode != 0:
        stderr = (proc.stderr or "").strip()
        raise RuntimeError(
            f"aliyun CLI failed (exit {proc.returncode}): {redact_secrets(stderr)[:500]}")

    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"aliyun CLI returned non-JSON output: {redact_secrets(proc.stdout)[:500]}") from e

    # The aliyun CLI can exit 0 while the response body carries an API error
    # ({"Code": ..., "Message": ...}); surface it as a failure explicitly.
    if isinstance(result, dict) and result.get("Code"):
        raise RuntimeError(
            f"aliyun CLI API error: {result.get('Code')}: {result.get('Message', '')}"
        )
    return result


def friendly_cli_error(err_msg):
    """Map common CLI/API errors to a one-line business-friendly message.

    The raw error is kept separately (in raw_error) for traceability.
    """
    msg = redact_secrets(err_msg)
    if "InvalidDomain.NotFound" in msg:
        return "The domain does not exist or does not belong to the current account."
    if "Forbidden" in msg or "NoPermission" in msg or "Unauthorized" in msg:
        return (
            "The current credentials lack permission for this operation; "
            "check the RAM policy of the account or role in use."
        )
    if "timed out" in msg.lower() or "timeout" in msg.lower():
        return "The request timed out; please retry in a moment."
    return msg


# ===== Domain mapping and authentication config =====

def resolve_domains(input_domain):
    """Resolve the ingest and playback domains from the input domain.

    Uses DescribeLiveDomainMapping and returns:
      {"push_domain": str, "pull_domain": str, "input_type": "publish"|"vhost"}
    """
    resp = run_aliyun_cli([
        "live", "describe-live-domain-mapping",
        "--domain-name", input_domain,
    ])
    models = resp.get("LiveDomainModels", {}).get("LiveDomainModel", [])

    push_domain = None
    pull_domain = None
    input_type = None

    for model in models:
        domain_type = model.get("Type", "").lower()
        domain_name = model.get("DomainName", "")
        if domain_type == "publish":
            push_domain = domain_name
        elif domain_type == "vhost":
            pull_domain = domain_name
        if domain_name == input_domain:
            input_type = domain_type

    if not push_domain or not pull_domain:
        raise RuntimeError(
            f"Unable to resolve the full ingest/playback domain mapping from "
            f"{input_domain}; API returned: {models}"
        )

    return {
        "push_domain": push_domain,
        "pull_domain": pull_domain,
        "input_type": input_type,
    }


def parse_auth_config(domain):
    """Parse the aliauth configuration of a domain.

    Returns a dict: {"auth_type", "auth_key", "auth_m3u8", "ali_auth_delta"}
    """
    resp = run_aliyun_cli([
        "live", "describe-live-domain-configs",
        "--domain-name", domain,
        "--function-names", "aliauth",
    ])
    configs = resp.get("DomainConfigs", {}).get("DomainConfig", [])

    for cfg in configs:
        if cfg.get("FunctionName") != "aliauth":
            continue
        args = cfg.get("FunctionArgs", {}).get("FunctionArg", [])
        result = {
            "auth_type": "no_auth",
            "auth_key": "",
            "auth_m3u8": "off",
            "ali_auth_delta": "0",
        }
        for arg in args:
            name = arg.get("ArgName", "")
            value = arg.get("ArgValue", "")
            if name == "auth_type":
                result["auth_type"] = value
            elif name == "auth_key1":
                result["auth_key"] = value
            elif name == "auth_m3u8":
                result["auth_m3u8"] = value
            elif name == "ali_auth_delta":
                result["ali_auth_delta"] = value
        return result

    return {
        "auth_type": "no_auth",
        "auth_key": "",
        "auth_m3u8": "off",
        "ali_auth_delta": "0",
    }


# ===== URL generation =====

def mask_auth_config(auth_info):
    """Return a copy of the auth config with the raw auth_key masked.

    The raw URL-authentication key is a secret; only a short prefix is kept
    for traceability. The signed auth_key embedded in the generated URLs is
    a signature result (not the key itself) and stays untouched.
    """
    masked = copy.deepcopy(auth_info)
    key = masked.get("auth_key", "")
    if key:
        # Short keys (<8 chars) would leak too much of the secret as a
        # 4-char prefix; mask them entirely instead.
        masked["auth_key"] = (key[:4] + "****") if len(key) >= 8 else "****"
    return masked


def _generate_auth_key(uri, key, timestamp, rand="0", uid="0"):
    """Generate a Type-A URL authentication auth_key."""
    raw = f"{uri}-{timestamp}-{rand}-{uid}-{key}"
    return f"{timestamp}-{rand}-{uid}-{hashlib.md5(raw.encode()).hexdigest()}"


def _build_url(scheme, domain, uri, auth_key=None):
    """Assemble a single URL."""
    url = f"{scheme}://{domain}{uri}"
    if auth_key:
        url += f"?auth_key={auth_key}"
    return url


def _maybe_auth(uri, auth_info, expire_at):
    """Decide whether to generate an auth_key based on the auth config."""
    auth_type = auth_info.get("auth_type", "no_auth")
    auth_key = auth_info.get("auth_key", "")
    if auth_type == "type_a" and auth_key:
        return _generate_auth_key(uri, auth_key, expire_at)
    return None


def generate_stream_urls(push_domain, pull_domain, app_name, stream_name, push_auth, pull_auth, expire_seconds=3600):
    """Generate the full set of ingest/playback URLs.

    Ingest URLs use the push_domain auth config; playback URLs use the
    pull_domain auth config.
    """
    # Expiry timestamp: now + validity + server clock skew tolerance
    # (take the larger delta of the two domains)
    push_delta = int(push_auth.get("ali_auth_delta", "0") or "0")
    pull_delta = int(pull_auth.get("ali_auth_delta", "0") or "0")
    expire_at = int(time.time()) + expire_seconds + max(push_delta, pull_delta)

    push_uri = f"/{app_name}/{stream_name}"
    flv_uri = f"/{app_name}/{stream_name}.flv"
    m3u8_uri = f"/{app_name}/{stream_name}.m3u8"

    return {
        "push": {
            "rtmp": _build_url("rtmp", push_domain, push_uri, _maybe_auth(push_uri, push_auth, expire_at)),
            "rts": _build_url("artc", push_domain, push_uri, _maybe_auth(push_uri, push_auth, expire_at)),
        },
        "pull": {
            "rtmp": _build_url("rtmp", pull_domain, push_uri, _maybe_auth(push_uri, pull_auth, expire_at)),
            "flv": _build_url("https", pull_domain, flv_uri, _maybe_auth(flv_uri, pull_auth, expire_at)),
            "m3u8": _build_url("https", pull_domain, m3u8_uri, _maybe_auth(m3u8_uri, pull_auth, expire_at)),
            "rts": _build_url("artc", pull_domain, push_uri, _maybe_auth(push_uri, pull_auth, expire_at)),
        },
        "expires_at": expire_at,
        "expires_at_iso": datetime.fromtimestamp(expire_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


# ===== Main entry =====

def _default_stream_name():
    """Default stream name: MMDD_test, e.g. 0626_test."""
    now = datetime.now()
    return f"{now.month:02d}{now.day:02d}_test"


def main():
    parser = argparse.ArgumentParser(
        description="Generate Alibaba Cloud Live ingest/playback test URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 scripts/live_stream_url_generator.py generate \\\n"
            "    --domain push.example.com\n\n"
            "  python3 scripts/live_stream_url_generator.py generate \\\n"
            "    --domain pull.example.com \\\n"
            "    --app-name live --stream-name my_test --expire-seconds 7200\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen_parser = subparsers.add_parser("generate", help="Generate ingest/playback URLs")
    gen_parser.add_argument("--domain", required=True, help="Live domain to query (ingest or playback)")
    gen_parser.add_argument("--app-name", default="live", help="AppName, default live")
    gen_parser.add_argument(
        "--stream-name",
        default=_default_stream_name(),
        help=f"StreamName, default {_default_stream_name()}",
    )
    gen_parser.add_argument("--expire-seconds", type=int, default=3600, help="URL validity in seconds, default 3600")

    args = parser.parse_args()

    if args.command != "generate":
        parser.print_help()
        sys.exit(1)

    try:
        mapping = resolve_domains(args.domain)
        push_domain = mapping["push_domain"]
        pull_domain = mapping["pull_domain"]

        # Each domain uses its own auth config (usually identical, but
        # querying them separately is more accurate)
        push_auth = parse_auth_config(push_domain)
        pull_auth = parse_auth_config(pull_domain)

        urls = generate_stream_urls(
            push_domain,
            pull_domain,
            args.app_name,
            args.stream_name,
            push_auth,
            pull_auth,
            args.expire_seconds,
        )

        result = {
            "overall_status": "ok",
            "severity": "info",
            "summary": (
                f"Push/pull test URLs for {args.domain} were generated successfully. "
                f"Next: use the push URLs in your streaming tool and the pull URLs in a player "
                f"before they expire at {urls['expires_at_iso']} UTC."
            ),
            "input_domain": args.domain,
            "input_type": mapping["input_type"],
            "push_domain": push_domain,
            "pull_domain": pull_domain,
            "app_name": args.app_name,
            "stream_name": args.stream_name,
            "push_auth_type": push_auth["auth_type"],
            "pull_auth_type": pull_auth["auth_type"],
            "expires_at": urls["expires_at"],
            "expires_at_iso": urls["expires_at_iso"],
            "validity_note": (
                f"The URLs stay valid for the requested {args.expire_seconds}s plus the platform's "
                "configured auth delta extension (ali_auth_delta, taken as the larger value of the "
                "two domains) to tolerate server clock skew."
            ),
            "usage_note": (
                "Use the push_* URLs in your streaming tool (e.g. OBS or ffmpeg) to publish the "
                "stream, and the pull_* URLs in a player to watch it."
            ),
            "urls": {
                "push_rtmp": urls["push"]["rtmp"],
                "push_rts": urls["push"]["rts"],
                "pull_rtmp": urls["pull"]["rtmp"],
                "pull_flv": urls["pull"]["flv"],
                "pull_m3u8": urls["pull"]["m3u8"],
                "pull_rts": urls["pull"]["rts"],
            },
            "push_auth_config": mask_auth_config(push_auth),
            "pull_auth_config": mask_auth_config(pull_auth),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))

    except Exception as e:
        friendly = friendly_cli_error(e)
        print(json.dumps({
            "status": "error",
            "error": friendly,
            "raw_error": redact_secrets(str(e)),
            "overall_status": "failed",
            "severity": "high",
            "summary": (
                f"The URLs could not be generated: {friendly} "
                "Next: resolve the issue above and retry."
            ),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
