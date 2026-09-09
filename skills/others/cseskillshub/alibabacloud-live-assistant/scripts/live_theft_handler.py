#!/usr/bin/env python3
"""
Live stream abuse (bandwidth theft) handling SOP.

Guides standardized handling of a live domain abused by third parties, with
automated authentication detection and log analysis. When URL authentication
is disabled, anyone can misuse the ingest/playback domains and generate
extra traffic charges.

Modes:
  analyze   - Query auth config via aliyun CLI -> fetch access logs -> report
  guide     - Print the full SOP and customer-facing notification templates
  step      - Step-by-step guidance with per-step instructions
  checklist - Print the handling checklist

Cloud API access goes through the aliyun CLI (plugin mode) with the caller's
locally configured credentials. No SDK or token exchange is used.
"""

import argparse
import collections
import copy
import gzip
import io
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
import uuid

# ===== Configuration constants =====

# Per-run session id for platform-level tracing (Observability)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = f"AlibabaCloud-Agent-Skills/alibabacloud-live-assistant/{_SESSION_ID}"
CLI_TIMEOUT = 60

SECURITY_REFERENCE_URL = "https://help.aliyun.com/zh/live/user-guide/security-overview/"
LOG_FIELDS_REFERENCE_URL = "https://help.aliyun.com/zh/live/user-guide/log-management"


# ===== SOP step definitions (4 steps, customer-facing) =====

SOP_STEPS = [
    {
        "step": 1,
        "title": "Confirm billing items and explain the charges",
        "objective": "Identify the source of the extra charges and explain the billing reason",
        "actions": [
            "Query the billing items of the live domain via the console or API (upstream/downstream bandwidth and traffic)",
            "Confirm the abnormal traffic time window and the amount charged",
            "Distinguish normal business traffic from abusive traffic",
        ],
        "output_template": (
            "Domain: {domain}\n"
            "Billing items: {billing_items}\n"
            "Abnormal period: {abnormal_period}\n"
            "Abnormal traffic: {abnormal_traffic}\n"
            "Reason: URL authentication on the domain is disabled, so third parties can use the "
            "ingest/playback domains without authorization, generating extra traffic charges."
        ),
        "tips": "Use the push/pull stream monitoring data of the domain to help identify abnormal traffic.",
    },
    {
        "step": 2,
        "title": "Review the authentication status",
        "objective": "Verify whether URL authentication is configured and locate the risk window",
        "actions": [
            "Query the URL authentication configuration of the domain",
            "Confirm when authentication was disabled, if applicable",
            "Assess the duration of the risk window",
        ],
        "output_template": (
            "Domain: {domain}\n"
            "Authentication status: {auth_status}\n"
            "Disabled since: {auth_disabled_time}\n"
            "Risk window: the domain has been exposed since {auth_disabled_time}\n"
            "Impact: during this period anyone can use the domain for ingest/playback."
        ),
        "tips": "Authentication configuration history is available in the Live console: Domain Management > Access Control.",
    },
    {
        "step": 3,
        "title": "Analyze top IP and top URL traffic",
        "objective": "Collect abuse evidence and provide detailed data for confirmation",
        "actions": [
            "List the top source IPs during the abnormal time window",
            "List the top requested URLs during the abnormal time window",
            "Analyze the source characteristics of the abusive traffic",
        ],
        "output_template": (
            "=== Top IPs (by traffic) ===\n"
            "{top_ips}\n\n"
            "=== Top URLs (by request count) ===\n"
            "{top_urls}\n\n"
            "=== Abuse pattern analysis ===\n"
            "Main source IP ranges: {ip_segments}\n"
            "Main access patterns: {access_patterns}\n"
            "Abuse time windows: {theft_periods}"
        ),
        "tips": "Top IP/URL data is available in the Live console: Data Statistics > Usage Query.",
    },
    {
        "step": 4,
        "title": "Security hardening recommendations",
        "objective": "Guide the customer to enable authentication and harden the domain",
        "actions": [
            "Explain that disabled authentication is the root cause of the abuse",
            "Recommend enabling URL authentication (Type A recommended) immediately",
            "Provide the security best-practice documentation",
        ],
        "output_template": (
            "Configuration issue: URL authentication of {domain} is disabled, which is the direct cause of the abuse.\n\n"
            "Recommended fixes:\n"
            "1. Enable URL authentication immediately (Type A recommended). See: {security_ref}\n"
            "2. Configure an IP blacklist to block known abusive IPs\n"
            "3. Configure referer-based hotlink protection\n"
            "4. Enable ingest callbacks to monitor abnormal streaming in real time\n"
            "5. Configure bandwidth/traffic limits to prevent sudden traffic spikes\n\n"
            "Security reference:\n"
            "{security_ref}"
        ),
        "tips": "Stress the urgency of enabling authentication; every hour of delay may produce more abusive traffic.",
    },
]


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
    sanitize_domain_configs() and would otherwise echo raw auth keys.
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


# ===== Authentication config detection =====

def mask_secret_value(value):
    """Mask a secret string: keep the first 4 chars + ****.

    Same rule as live_stream_url_generator.mask_auth_config; short values
    (<8 chars) would leak too much as a 4-char prefix, so they are masked
    entirely.
    """
    if not value:
        return value
    return (value[:4] + "****") if len(value) >= 8 else "****"


def sanitize_domain_configs(configs):
    """Deep-copy DescribeLiveDomainConfigs output with auth keys masked.

    The raw auth_key1/auth_key2 ArgValues are secrets; any structure
    derived from the API response that may reach stdout/stderr/error JSON
    must go through this sanitizer first.
    """
    masked = copy.deepcopy(configs)
    for cfg in masked:
        if not isinstance(cfg, dict):
            continue
        for arg in cfg.get("FunctionArgs", {}).get("FunctionArg", []):
            if isinstance(arg, dict) and arg.get("ArgName") in ("auth_key1", "auth_key2"):
                arg["ArgValue"] = mask_secret_value(arg.get("ArgValue", ""))
    return masked


def detect_auth_config(domain):
    """Detect whether the domain has URL authentication configured.

    The returned raw_configs are sanitized (auth keys masked) so they are
    safe to surface in any output channel.
    """
    resp = run_aliyun_cli([
        "live", "describe-live-domain-configs",
        "--domain-name", domain,
        "--function-names", "aliauth",
    ])
    configs = resp.get("DomainConfigs", {}).get("DomainConfig", [])

    auth_type = None
    for cfg in configs:
        function = cfg.get("FunctionName", "")
        if function != "aliauth":
            continue
        args = cfg.get("FunctionArgs", {}).get("FunctionArg", [])
        for arg in args:
            if arg.get("ArgName") == "auth_type":
                auth_type = arg.get("ArgValue")
                break
        if auth_type:
            break

    return {
        "auth_enabled": auth_type not in (None, "", "no_auth"),
        "auth_type": auth_type or "no_auth",
        "raw_configs": sanitize_domain_configs(configs),
    }


# ===== Log download and analysis =====

def fetch_log_paths(domain, start_time, end_time):
    """Fetch log download URLs via DescribeLiveDomainLog (aliyun CLI)."""
    resp = run_aliyun_cli([
        "live", "describe-live-domain-log",
        "--domain-name", domain,
        "--start-time", start_time,
        "--end-time", end_time,
    ])
    paths = []
    for group in resp.get("DomainLogDetails", {}).get("DomainLogDetail", []):
        for detail in group.get("LogInfos", {}).get("LogInfoDetail", []):
            log_url = detail.get("LogPath", "")
            if log_url:
                # The LogPath returned by the API sometimes lacks a scheme
                if not log_url.startswith(("http://", "https://")):
                    log_url = "https://" + log_url
                paths.append(log_url)
    return paths


def download_log_text(url, timeout=60):
    """Download a log file (supports .gz and plain text) and return its text."""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = resp.read()
            content_encoding = resp.headers.get("Content-Encoding", "").lower()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to download log, HTTP {e.code}: {body}") from e

    # Detect gzip via Content-Encoding, magic bytes, or file extension
    is_gzip = (
        content_encoding == "gzip"
        or data.startswith(b"\x1f\x8b")
        or url.split("?")[0].endswith(".gz")
    )
    if is_gzip:
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as gz:
            return gz.read().decode("utf-8", errors="replace")
    return data.decode("utf-8", errors="replace")


def _parse_log_line(line):
    """Parse a single live CDN / ingest log line.

    Supports standard CDN access logs and ingest logs, e.g.:
      ip - - [time] "method url protocol" status size "referer" "ua" ...
      [time] ip - port "-" "PUSH url" status size 0 cache "-" "-" ip
    """
    line = line.strip()
    if not line:
        return None

    # Extract quoted fields
    quote_parts = line.split('"')
    quoted = [p.strip() for p in quote_parts[1::2] if p.strip()]

    # Find the quoted field containing the URL; may be "PUSH rtmp://..."
    # or a three-word request field like "GET /a.flv HTTP/1.1".
    url = ""
    method = ""
    request_field = ""

    def _split_request(part):
        """Split a request field into (method, url); tolerate a trailing protocol token."""
        tokens = part.split(None, 2)
        if len(tokens) >= 2:
            return tokens[0], tokens[1]
        return "", tokens[0]

    # Pass 1: method-prefixed request fields (covers "GET /a.flv HTTP/1.1",
    # "PUSH rtmp://..." and bare path requests).
    for part in quoted:
        if part.split(None, 1)[0].upper() in {"GET", "POST", "PUSH", "PULL"}:
            method, url = _split_request(part)
            request_field = part
            break

    # Pass 2 (fallback): the first quoted field containing a scheme URL.
    if not url:
        for part in quoted:
            lower = part.lower()
            if "rtmp://" in lower or "http://" in lower or "https://" in lower:
                tokens = part.split(None, 2)
                if len(tokens) >= 2:
                    method, url = tokens[0], tokens[1]
                    request_field = part
                else:
                    url = part
                break

    parts = line.split(" ")

    # First IPv4 address is the client IP
    ip = ""
    for p in parts:
        if "." in p and p.replace(".", "").isdigit() and p.count(".") == 3:
            ip = p
            break

    # First 3-digit number is the status code; the next number is the size
    status = ""
    size = "0"
    for idx, p in enumerate(parts):
        if p.isdigit() and len(p) == 3 and 100 <= int(p) <= 599:
            status = p
            if idx + 1 < len(parts) and parts[idx + 1].isdigit():
                size = parts[idx + 1]
            break

    # Referer and UA: found among quoted fields
    referer = ""
    user_agent = ""
    for part in quoted:
        if part in {"-", ""}:
            continue
        if part.startswith("http://") or part.startswith("https://"):
            if not referer:
                referer = part
            continue
        if (
            not user_agent
            and part != url
            and part != request_field
            and not part.startswith("PUSH ")
            and not part.startswith("PULL ")
        ):
            user_agent = part

    return {
        "ip": ip,
        "time": parts[0].lstrip("[").rstrip("]") if parts else "",
        "method": method.upper() if method else ("PUSH" if "PUSH" in line else "GET"),
        "url": url,
        "status": status,
        "size": size,
        "referer": referer or "-",
        "user_agent": user_agent or "-",
    }


def analyze_logs(log_text, top_n=10):
    """Analyze log text and return Top-N statistics plus anomaly features."""
    ips = collections.Counter()
    urls = collections.Counter()
    referers = collections.Counter()
    uas = collections.Counter()

    total = 0
    valid = 0
    empty_referer = 0
    non_2xx = 0

    for line in log_text.splitlines():
        total += 1
        record = _parse_log_line(line)
        if not record:
            continue
        valid += 1

        ips[record["ip"]] += 1
        urls[record["url"]] += 1
        referers[record["referer"] or "-"] += 1
        uas[record["user_agent"] or "-"] += 1

        if not record["referer"] or record["referer"] == "-":
            empty_referer += 1
        if record["status"] and not record["status"].startswith("2"):
            non_2xx += 1

    features = []
    if valid == 0:
        features.append(
            "Log content is empty or the format is unrecognized; see the log field reference: "
            + LOG_FIELDS_REFERENCE_URL
        )
    else:
        top_ip, top_ip_count = ips.most_common(1)[0] if ips else (None, 0)
        if top_ip and top_ip_count > valid * 0.3:
            features.append(
                f"Single IP dominates: {top_ip} made {top_ip_count} requests "
                f"({top_ip_count * 100 // valid}%), suggesting concentrated abuse"
            )
        if empty_referer > valid * 0.5:
            features.append(
                f"Empty referer accounts for {empty_referer * 100 // valid}%, "
                "typical of malicious crawlers/abuse tools"
            )
        if non_2xx > valid * 0.1:
            features.append(
                f"Non-2xx responses account for {non_2xx * 100 // valid}%, "
                "indicating many invalid requests"
            )

    return {
        "total_lines": total,
        "valid_lines": valid,
        "top_ips": ips.most_common(top_n),
        "top_urls": urls.most_common(top_n),
        "top_referers": referers.most_common(top_n),
        "top_uas": uas.most_common(top_n),
        "features": features,
    }


# ===== Report generation =====

def generate_report(domain, start_time, end_time, auth_info, log_analysis, log_unavailable_reason=None):
    """Generate the standardized customer-facing abuse analysis report.

    When log_analysis is None the report must explicitly state that logs are
    unavailable (with the reason) and must NOT assert abuse without evidence.
    """
    logs_available = log_analysis is not None
    auth_status = "authentication enabled" if auth_info["auth_enabled"] else "authentication not configured"
    auth_type = auth_info["auth_type"]

    if auth_info["auth_enabled"]:
        if logs_available:
            auth_issue = (
                f"Domain {domain} has URL authentication configured ({auth_type}), but abnormal "
                "access still appears in the logs; the auth key may be leaked or playback URLs "
                "may be redistributed"
            )
        else:
            auth_issue = (
                f"Domain {domain} has URL authentication configured ({auth_type}); log evidence "
                "is unavailable, so no conclusion about actual misuse can be drawn from logs"
            )
        auth_risk = (
            "Authentication is enabled, but the abnormal traffic indicates a possible key leak "
            "or URL redistribution; rotate the key immediately and investigate the sources"
            if logs_available else
            "Authentication is enabled; without log evidence this assessment covers the "
            "configuration only. Verify the auth key has not leaked if abuse is still suspected"
        )
    else:
        auth_issue = (
            f"Domain {domain} has no URL authentication configured, so third parties can use "
            "the ingest/playback domains without authorization"
        )
        auth_risk = (
            "Without URL authentication, anyone can use the domain for ingest/playback, "
            "which exposes it to traffic abuse"
        )

    total_lines = 0
    valid_lines = 0
    top_ips_text = "No data available"
    top_urls_text = "No data available"
    single_ip_analysis = "None"
    empty_referer_ratio = "0%"
    non_2xx_ratio = "0%"

    if log_analysis is not None:
        total_lines = log_analysis.get("total_lines", 0)
        valid_lines = log_analysis.get("valid_lines", 0)

        top_ips = log_analysis.get("top_ips", [])
        if top_ips and valid_lines:
            ip_parts = []
            for ip, count in top_ips[:5]:
                ratio = count * 100 // valid_lines
                ip_parts.append(f"{ip} ({count} requests, {ratio}%)")
            top_ips_text = ", ".join(ip_parts)

            top_ip, top_count = top_ips[0]
            top_ratio = top_count * 100 // valid_lines
            single_ip_analysis = f"{top_ip} made {top_count} requests ({top_ratio}%)"

        top_urls = log_analysis.get("top_urls", [])
        if top_urls:
            url_lines = []
            for idx, (url, count) in enumerate(top_urls[:5], 1):
                url_lines.append(f"{idx}. {url} - {count} requests")
            top_urls_text = "\n".join(url_lines)

        for feature in log_analysis.get("features", []):
            if "Empty referer" in feature and "%" in feature:
                try:
                    empty_referer_ratio = feature.split("accounts for ")[1].split(",")[0].strip()
                except Exception:
                    pass
            if "Non-2xx" in feature and "%" in feature:
                try:
                    non_2xx_ratio = feature.split("account for ")[1].split(",")[0].strip()
                except Exception:
                    pass

    if logs_available:
        problem_summary = [
            "1. Problem summary",
            f"Investigation shows abnormal access to domain {domain} between {start_time} and {end_time}, "
            "suspected traffic abuse / misuse.",
            f"Analyzed {total_lines} log lines in total, of which {valid_lines} are valid access records.",
        ]
        evidence_section = [
            "4. Abuse evidence",
            f"- Top source IPs: {top_ips_text}",
            "- Top requested URLs:",
            top_urls_text,
            "- Anomaly features:",
            f"  - Concentrated single-IP access: {single_ip_analysis}",
            f"  - Empty referer ratio: {empty_referer_ratio}",
            f"  - Non-2xx status ratio: {non_2xx_ratio}",
        ]
    else:
        reason = log_unavailable_reason or "unknown reason"
        problem_summary = [
            "1. Problem summary",
            f"Access logs for domain {domain} between {start_time} and {end_time} are UNAVAILABLE "
            f"({reason}). No log lines were analyzed.",
            "This report therefore contains NO abuse conclusion based on log evidence; it is a "
            "risk assessment based only on the authentication configuration.",
        ]
        evidence_section = [
            "4. Abuse evidence",
            f"- Logs unavailable: {reason}",
            "- No log-based evidence (Top IPs / Top URLs / anomaly features) can be provided.",
        ]

    lines = [
        f"Domain: {domain}",
        f"Analysis window: {start_time} to {end_time}",
        f"Current authentication status: {auth_status} (auth_type={auth_type})",
        "",
        *problem_summary,
        "",
        "2. Billing impact",
        f"- Abnormal period: {start_time} to {end_time}",
        "- Abnormal traffic/bandwidth: verify the exact amount via Usage Query in the console",
        (
            f"- Root cause: {auth_issue}, generating extra upstream/downstream traffic charges."
            if logs_available else
            f"- Configuration finding: {auth_issue}. Without log evidence, actual extra traffic "
            "charges cannot be quantified here; verify via Usage Query in the console."
        ),
        "",
        "3. Authentication status",
        f"- Current status: {auth_status} (auth_type={auth_type})",
        "- Note: this reflects the status at query time, not necessarily at the time of the abuse; "
        "query the configuration change history to confirm the historical status.",
        f"- Risk assessment: {auth_risk}",
        "",
        *evidence_section,
        "",
        "5. Recommendations",
        "1. Check and rotate the URL authentication key immediately; investigate possible key leaks;",
        "2. Add high-frequency abusive IPs to the blacklist;",
        "3. Configure referer-based hotlink protection;",
        "4. Enable bandwidth/traffic alerting to detect sudden abuse early;",
        "5. Optionally enable ingest callbacks to monitor abnormal streaming in real time.",
        "",
        f"Reference: {SECURITY_REFERENCE_URL}",
    ]

    return "\n".join(lines)


# ===== Subcommand implementations =====

def cmd_analyze(args):
    """Automated abuse analysis.

    Log fetching and analysis are attempted regardless of the authentication
    status; the auth status only affects the risk conclusion and the focus
    of the security recommendations.
    """
    try:
        auth_info = detect_auth_config(args.domain)

        log_paths = []
        log_list_error = None
        try:
            log_paths = fetch_log_paths(args.domain, args.start_time, args.end_time)
        except Exception as e:
            # Listing offline logs can fail (e.g. server-side errors in some
            # regions); degrade gracefully and still produce the report.
            log_list_error = redact_secrets(e)[:300]
            print(
                f"[warn] failed to list offline logs, continuing without log evidence: {redact_secrets(e)[:200]}",
                file=sys.stderr,
            )
        log_analysis = None
        log_download_failures = []
        combined_text = ""
        if log_paths:
            for path in log_paths:
                try:
                    combined_text += download_log_text(path) + "\n"
                except Exception as e:
                    # A single unreachable log URL must not abort the whole
                    # analysis; record it and continue with the rest.
                    log_download_failures.append({"url": path, "error": redact_secrets(e)[:300]})
                    print(f"[warn] failed to download log, skipping: {redact_secrets(e)[:200]}", file=sys.stderr)
            if combined_text.strip():
                log_analysis = analyze_logs(combined_text, top_n=10)

        # Why are logs unavailable? Needed so the report can state the
        # limitation explicitly instead of silently claiming log evidence.
        log_unavailable_reason = None
        if log_analysis is None:
            if log_list_error:
                log_unavailable_reason = f"offline logs could not be listed: {log_list_error}"
            elif not log_paths:
                log_unavailable_reason = "no offline log files exist for the given time window"
            elif log_download_failures and not combined_text.strip():
                log_unavailable_reason = "all log files failed to download"
            else:
                log_unavailable_reason = "the downloaded log files are empty"

        report = generate_report(
            args.domain, args.start_time, args.end_time, auth_info, log_analysis,
            log_unavailable_reason,
        )

        logs_available = log_analysis is not None
        if auth_info["auth_enabled"]:
            if logs_available:
                risk_conclusion = (
                    "The domain has URL authentication configured, but the logs were still analyzed "
                    "as requested. If abuse persists, check whether the auth key is leaked or the "
                    "URLs are being redistributed."
                )
            else:
                risk_conclusion = (
                    "Risk assessment based only on the authentication configuration: URL "
                    "authentication is configured, but logs were unavailable "
                    f"({log_unavailable_reason}), so no log-based abuse conclusion can be drawn."
                )
        else:
            if logs_available:
                risk_conclusion = (
                    "The domain has no URL authentication configured and is exposed to traffic abuse; "
                    "enable authentication immediately and investigate the abnormal traffic sources."
                )
            else:
                risk_conclusion = (
                    "Risk assessment based only on the authentication configuration: the domain has "
                    "no URL authentication configured and is exposed to traffic abuse; logs were "
                    f"unavailable ({log_unavailable_reason}). Enable authentication immediately."
                )

        # Structured evidence summary so downstream agents do not need to
        # parse the long text report.
        evidence = {
            "auth_enabled": auth_info["auth_enabled"],
            "auth_type": auth_info["auth_type"],
            "logs_available": logs_available,
            "log_unavailable_reason": log_unavailable_reason,
            "total_lines": log_analysis.get("total_lines", 0) if log_analysis else 0,
            "valid_lines": log_analysis.get("valid_lines", 0) if log_analysis else 0,
            "top_ips": [
                {"ip": ip, "count": count}
                for ip, count in (log_analysis.get("top_ips", [])[:3] if log_analysis else [])
            ],
            "top_urls": [
                {"url": url, "count": count}
                for url, count in (log_analysis.get("top_urls", [])[:3] if log_analysis else [])
            ],
            "features": log_analysis.get("features", []) if log_analysis else [],
        }

        if not auth_info["auth_enabled"]:
            overall_status = "warning"
            severity = "high" if logs_available else "medium"
            if logs_available:
                summary = (
                    "The domain has no URL authentication and log evidence shows abnormal access; "
                    "enable URL authentication immediately and review the top IPs in the evidence."
                )
            else:
                summary = (
                    "The domain has no URL authentication configured, but logs were unavailable so "
                    "abuse could not be confirmed. Next: enable URL authentication and retry the "
                    "analysis once logs exist."
                )
        else:
            overall_status = "ok" if logs_available else "warning"
            severity = "medium" if logs_available else "low"
            if logs_available:
                summary = (
                    "URL authentication is enabled and the logs were analyzed; review the evidence "
                    "for signs of key leakage or URL redistribution."
                )
            else:
                summary = (
                    "URL authentication is enabled, but logs were unavailable so only a "
                    "configuration-based assessment is possible. Next: retry later or check the "
                    "console log settings."
                )

        result = {
            "overall_status": overall_status,
            "severity": severity,
            "summary": summary,
            "domain": args.domain,
            "auth_type": auth_info["auth_type"],
            "auth_enabled": auth_info["auth_enabled"],
            "risk_conclusion": risk_conclusion,
            "evidence": evidence,
            "log_paths": log_paths,
            "log_list_error": log_list_error,
            "log_download_failures": log_download_failures,
            "log_analysis": log_analysis,
            "report": report,
            "security_reference": SECURITY_REFERENCE_URL,
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
                f"The analysis could not be completed: {friendly} "
                "Next: resolve the issue above and retry."
            ),
        }, ensure_ascii=False, indent=2))
        sys.exit(1)


def cmd_guide(args):
    """Print the full SOP and customer-facing templates."""
    result = {
        "sop_name": "Live stream abuse handling procedure",
        "version": "3.0",
        "security_reference": SECURITY_REFERENCE_URL,
        "steps": [],
    }

    for step_info in SOP_STEPS:
        result["steps"].append({
            "step": step_info["step"],
            "title": step_info["title"],
            "objective": step_info["objective"],
            "actions": step_info["actions"],
            "output_template": step_info["output_template"],
            "tips": step_info["tips"],
        })

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_step(args):
    """Print guidance for a single step."""
    step_num = args.step
    if step_num < 1 or step_num > len(SOP_STEPS):
        print(json.dumps({
            "error": f"Invalid step number; valid range: 1-{len(SOP_STEPS)}",
            "available_steps": [s["step"] for s in SOP_STEPS],
        }, ensure_ascii=False, indent=2))
        sys.exit(1)

    step_info = SOP_STEPS[step_num - 1]
    result = {
        "step": step_info["step"],
        "title": step_info["title"],
        "objective": step_info["objective"],
        "actions": step_info["actions"],
        "output_template": step_info["output_template"],
        "tips": step_info["tips"],
        "progress": f"{step_num}/{len(SOP_STEPS)}",
    }

    if step_num > 1:
        result["prev_step"] = f"python3 scripts/live_theft_handler.py step {step_num - 1}"
    if step_num < len(SOP_STEPS):
        result["next_step"] = f"python3 scripts/live_theft_handler.py step {step_num + 1}"

    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_checklist(args):
    """Print the abuse handling checklist."""
    checklist = {
        "sop_name": "Live stream abuse handling checklist",
        "items": [
            {"step": 1, "item": "Billing items identified", "detail": "Confirm the source of abnormal traffic and charges", "checked": False},
            {"step": 2, "item": "Authentication status reviewed", "detail": "Verify auth configuration and the risk window", "checked": False},
            {"step": 3, "item": "Top IP/URL data collected", "detail": "Abuse evidence data is complete", "checked": False},
            {"step": 4, "item": "Security recommendations delivered", "detail": "Authentication enabled and security documentation provided", "checked": False},
        ],
        "security_reference": SECURITY_REFERENCE_URL,
    }
    print(json.dumps(checklist, ensure_ascii=False, indent=2))


# ===== Main entry =====

def main():
    parser = argparse.ArgumentParser(
        description="Live stream abuse (bandwidth theft) handling SOP",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Automated analysis (recommended)\n"
            "  python3 scripts/live_theft_handler.py analyze \\\n"
            "    --domain pull.example.com \\\n"
            "    --start-time 2026-06-24T08:00:00Z --end-time 2026-06-24T20:00:00Z\n\n"
            "  # Print the full SOP\n"
            "  python3 scripts/live_theft_handler.py guide\n\n"
            "  # Show guidance for step 1\n"
            "  python3 scripts/live_theft_handler.py step 1\n\n"
            "  # Print the handling checklist\n"
            "  python3 scripts/live_theft_handler.py checklist\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Automated abuse analysis")
    analyze_parser.add_argument("--domain", required=True, help="Live domain to inspect")
    analyze_parser.add_argument("--start-time", required=True, help="Log start time, ISO 8601 format")
    analyze_parser.add_argument("--end-time", required=True, help="Log end time, ISO 8601 format")

    subparsers.add_parser("guide", help="Print the full SOP and customer-facing templates")
    subparsers.add_parser("checklist", help="Print the abuse handling checklist")

    step_parser = subparsers.add_parser("step", help="Step-by-step guidance")
    step_parser.add_argument("step", type=int, help="Step number (1-4)")

    args = parser.parse_args()

    if args.command == "analyze":
        cmd_analyze(args)
    elif args.command == "guide":
        cmd_guide(args)
    elif args.command == "step":
        cmd_step(args)
    elif args.command == "checklist":
        cmd_checklist(args)


if __name__ == "__main__":
    main()
