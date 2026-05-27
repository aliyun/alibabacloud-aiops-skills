#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dyvmsapi public RPC direct-call script (zero dependencies; Python 3 stdlib only)

================================================================================
Owning Skill and trigger conditions
================================================================================
This script is the entrypoint for the **external-network fallback path** of the
Skill `alibabacloud-vms-smart-call-by-tts`. It pairs with SKILL.md §1.alt /
§6.alt and the reference document `references/external-network-fallback.md`.

Use this path only when:
  - The runtime cannot reach the intranet-online CLI plugin source
    (cli.aliyun-inc.com)
  - SKILL.md §1.3 reports `lookup cli.aliyun-inc.com: no such host`
  - Public sandbox / external CI/CD / non-Alibaba-employee environment with no
    Alibaba intranet or VPN access

**Do not** use this script while the primary path (aliyun CLI + intranet-online
dyvmsapi plugin) is functional.

================================================================================
Capability
================================================================================
Zero-dependency (Python 3 stdlib only) direct call to the dyvmsapi public
gateway, covering any RPC-style API such as SubmitIntent /
QueryCallDetailByCallId.

⚠️ Important notice
--------------------------------------------------------------------------------
1. SubmitIntent visibility in the Alibaba Cloud metadata center is still
   `private`. The public gateway is reachable and signing succeeds, but
   **Alibaba Cloud does not guarantee an SLA for this invocation pattern**, and
   it may change at any time. For production paths, prefer the intranet-online
   CLI plugin documented in this repository's SKILL.md.
2. This script only relays HTTP + RPC signing; it does NOT validate parameters.
   Verify the API's required fields yourself.
3. Hardcoding AK/SK into the script is strictly forbidden; use environment
   variables or pass them temporarily on the command line.

================================================================================
Usage examples
================================================================================

⚠️ When invoking this script as part of the `alibabacloud-vms-smart-call-by-tts`
   Skill flow, do not export credentials yourself; route through the helper for
   automatic injection:
       python3 scripts/run_with_aliyun_creds.py -- \\
           python3 scripts/dyvmsapi_rpc.py SubmitIntent -P UserMessage="..."
   The export examples below apply only when the script is used standalone
   (e.g. CI/CD, local debugging).

# 1) Provide credentials via environment variables (recommended)
export ALIBABA_CLOUD_ACCESS_KEY_ID=LTAI...
export ALIBABA_CLOUD_ACCESS_KEY_SECRET=xxxx
# When using STS temporary credentials, also set the security token (the script
# will automatically include it in the signature as the public parameter
# SecurityToken). The script also accepts the common SDK env names
# ALIBABACLOUD_SECURITY_TOKEN / ALIYUN_SECURITY_TOKEN as aliases.
export ALIBABA_CLOUD_SECURITY_TOKEN=CAIS...

# 2) Call SubmitIntent — initiate an outbound call from a natural-language intent
python3 scripts/dyvmsapi_rpc.py SubmitIntent \\
    -P UserMessage="Call Zhang San and remind him about the 3 PM meeting"

# 3) Call QueryCallDetailByCallId — query call detail
#    QueryDate is a **Unix-millisecond timestamp (int)**, NOT a yyyyMMdd string.
#    The front segment of CallId is exactly that millisecond timestamp — reuse
#    it directly. Do NOT convert it via datetime.strftime.
python3 scripts/dyvmsapi_rpc.py QueryCallDetailByCallId \\
    -P CallId=1779786101083^9876543210 \\
    -P ProdId=11000000300006 \\
    -P QueryDate=1779786101083

# 4) Pass AK/SK explicitly (NOT recommended; would be recorded in shell history)
python3 scripts/dyvmsapi_rpc.py SubmitIntent \\
    --access-key-id LTAI... \\
    --access-key-secret xxxx \\
    -P UserMessage="..."

# 5) Custom endpoint / version (rarely needed)
python3 scripts/dyvmsapi_rpc.py SubmitIntent \\
    --endpoint dyvmsapi.aliyuncs.com \\
    --version 2017-05-25 \\
    -P UserMessage="..."

================================================================================
Arguments
================================================================================
Positional:
    Action                  PascalCase API name, e.g. SubmitIntent

Optional:
    -P, --param KEY=VALUE   Business parameter (repeatable). Key MUST be PascalCase.
    --version VER           API version (default: 2017-05-25)
    --endpoint HOST         Gateway domain (default: dyvmsapi.aliyuncs.com)
    --access-key-id ID      AccessKeyId; defaults to env ALIBABA_CLOUD_ACCESS_KEY_ID
    --access-key-secret SK  AccessKeySecret; defaults to env ALIBABA_CLOUD_ACCESS_KEY_SECRET
    --security-token TOKEN  STS token (StsToken mode only). Defaults to env
                            ALIBABA_CLOUD_SECURITY_TOKEN; the aliases
                            ALIBABACLOUD_SECURITY_TOKEN / ALIYUN_SECURITY_TOKEN
                            are also accepted. When non-empty it is included
                            in the signature as the public parameter
                            SecurityToken. Strictly forbidden to pass it as a
                            business parameter via -P SecurityToken=...
    --method {GET,POST}     HTTP method (default: POST)
    --timeout SECONDS       Request timeout (default: 30)
    --debug                 Print the StringToSign and final URL for diagnosis

================================================================================
Exit codes
================================================================================
    0   HTTP 200 and the response JSON has no Code field, or Code=OK
    1   Non-200 HTTP / network error
    2   Response Code field is a non-OK error code
    3   Argument error
"""
import argparse
import base64
import hashlib
import hmac
import json
import os
import sys
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone


def percent_encode(s: str) -> str:
    """Percent-encode per the Alibaba Cloud RPC signing rule (RFC3986; '~' is not encoded)."""
    return urllib.parse.quote(str(s), safe="~")


def build_signature(method: str, params: dict, access_key_secret: str) -> str:
    """
    Build the Signature per the Alibaba Cloud RPC signing rule.
    StringToSign = METHOD + & + percentEncode("/") + & + percentEncode(canonicalQueryString)
    """
    sorted_items = sorted(params.items(), key=lambda kv: kv[0])
    canonical_qs = "&".join(
        f"{percent_encode(k)}={percent_encode(v)}" for k, v in sorted_items
    )
    string_to_sign = f"{method}&{percent_encode('/')}&{percent_encode(canonical_qs)}"
    key = (access_key_secret + "&").encode("utf-8")
    digest = hmac.new(key, string_to_sign.encode("utf-8"), hashlib.sha1).digest()
    return base64.b64encode(digest).decode("utf-8"), string_to_sign


def parse_kv_list(kv_list):
    out = {}
    if not kv_list:
        return out
    for item in kv_list:
        if "=" not in item:
            raise ValueError(f"-P expects KEY=VALUE form; received: {item!r}")
        k, v = item.split("=", 1)
        if not k:
            raise ValueError(f"-P KEY must not be empty: {item!r}")
        out[k] = v
    return out


def main():
    parser = argparse.ArgumentParser(
        description="dyvmsapi public RPC direct-call script (zero dependencies)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("action", help="PascalCase API name, e.g. SubmitIntent")
    parser.add_argument(
        "-P", "--param", action="append", default=[],
        help="Business parameter KEY=VALUE (repeatable)",
    )
    parser.add_argument("--version", default="2017-05-25", help="API version (default: 2017-05-25)")
    parser.add_argument("--endpoint", default="dyvmsapi.aliyuncs.com", help="Gateway domain")
    parser.add_argument(
        "--access-key-id",
        default=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID", ""),
        help="AccessKeyId (defaults to env ALIBABA_CLOUD_ACCESS_KEY_ID)",
    )
    parser.add_argument(
        "--access-key-secret",
        default=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET", ""),
        help="AccessKeySecret (defaults to env ALIBABA_CLOUD_ACCESS_KEY_SECRET)",
    )
    parser.add_argument(
        "--security-token",
        default=(
            os.environ.get("ALIBABA_CLOUD_SECURITY_TOKEN")
            or os.environ.get("ALIBABACLOUD_SECURITY_TOKEN")
            or os.environ.get("ALIYUN_SECURITY_TOKEN")
            or ""
        ),
        help=(
            "STS token (StsToken mode only). Defaults to "
            "ALIBABA_CLOUD_SECURITY_TOKEN / ALIBABACLOUD_SECURITY_TOKEN / ALIYUN_SECURITY_TOKEN. "
            "When non-empty, included in the signature as the public parameter SecurityToken."
        ),
    )
    parser.add_argument("--method", choices=["GET", "POST"], default="POST")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--debug", action="store_true", help="Print StringToSign and other diagnostics")

    args = parser.parse_args()

    if not args.access_key_id or not args.access_key_secret:
        print(
            "[ERROR] AK/SK not provided. Set env "
            "ALIBABA_CLOUD_ACCESS_KEY_ID / ALIBABA_CLOUD_ACCESS_KEY_SECRET, "
            "or pass --access-key-id / --access-key-secret.",
            file=sys.stderr,
        )
        sys.exit(3)

    try:
        biz_params = parse_kv_list(args.param)
    except ValueError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(3)

    # Public parameters (RPC style)
    common = {
        "Format": "JSON",
        "Version": args.version,
        "AccessKeyId": args.access_key_id,
        "SignatureMethod": "HMAC-SHA1",
        "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "SignatureVersion": "1.0",
        "SignatureNonce": uuid.uuid4().hex,
        "Action": args.action,
    }
    # STS temporary credential: include SecurityToken as a public parameter for signing
    if args.security_token:
        common["SecurityToken"] = args.security_token
    # If a business parameter shares a name with a public parameter, the business
    # parameter takes precedence (extremely rare).
    all_params = {**common, **biz_params}

    signature, string_to_sign = build_signature(
        args.method, all_params, args.access_key_secret
    )
    all_params["Signature"] = signature

    if args.debug:
        print(f"[DEBUG] StringToSign = {string_to_sign}", file=sys.stderr)

    url = f"https://{args.endpoint}/"
    encoded_qs = urllib.parse.urlencode(all_params)

    # Skill-identifying User-Agent (kept consistent with SKILL.md §1.1.1 per-command --user-agent declaration).
    ua = "AlibabaCloud-Agent-Skills/alibabacloud-vms-smart-call-by-tts/1.0.0"

    if args.method == "GET":
        full_url = f"{url}?{encoded_qs}"
        req = urllib.request.Request(
            full_url,
            method="GET",
            headers={"User-Agent": ua},
        )
    else:
        req = urllib.request.Request(
            url,
            data=encoded_qs.encode("utf-8"),
            method="POST",
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": ua,
            },
        )

    if args.debug:
        target = full_url if args.method == "GET" else url
        print(f"[DEBUG] {args.method} {target}", file=sys.stderr)

    try:
        with urllib.request.urlopen(req, timeout=args.timeout) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[ERROR] network exception: {e}", file=sys.stderr)
        sys.exit(1)

    # Pretty-print JSON
    try:
        parsed = json.loads(body)
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    except Exception:
        print(body)
        if status != 200:
            sys.exit(1)
        sys.exit(0)

    if status != 200:
        sys.exit(1)
    code = parsed.get("Code")
    if code and code != "OK":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()
