"""
dns_openapi.py - Alibaba Cloud OpenAPI wrapper for DNS diagnostics.

Calls DNS-related APIs via the aliyun CLI in plugin mode (kebab-case).
Supports STS AssumeRole for cross-account access.
Covers: Alidns, Domain, pvtz (PrivateZone), STS.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from typing import Optional


def _camel_to_kebab(name: str) -> str:
    """Convert CamelCase to kebab-case for aliyun CLI plugin mode."""
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

HAS_CLI = shutil.which("aliyun") is not None

if HAS_CLI:
    try:
        subprocess.run(
            "aliyun configure set --auto-plugin-install true",
            shell=True, capture_output=True, text=True, timeout=5,
        )
        subprocess.run(
            "aliyun plugin install --names aliyun-cli-alidns aliyun-cli-domain aliyun-cli-pvtz 2>/dev/null",
            shell=True, capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        pass


_sts_cache = {
    "credentials": None,
    "expiration": 0,
}


def _pascal_to_kebab(name: str) -> str:
    """Convert PascalCase API name to kebab-case plugin mode."""
    import re
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', name)
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', s)
    return s.lower()


def _run_cli(product: str, api: str, params: dict = None,
             region: str = None, timeout: int = 30) -> dict:
    """
    Call aliyun CLI and return JSON result.
    Uses plugin mode (kebab-case) and relies on default credential chain.
    """
    if not HAS_CLI:
        return {"error": "aliyun CLI not available. Install: https://help.aliyun.com/document_detail/139508.html"}

    plugin_api = _pascal_to_kebab(api)
    cmd = ["aliyun", product, plugin_api]

    effective_region = region or os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    cmd.extend(["--region", effective_region])

    cmd.extend(["--read-timeout", "30", "--connect-timeout", "10"])
    # UA format: AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session-id}
    session_id = os.environ.get("SESSION_ID", "no-session")
    ua = f"AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{session_id}"
    cmd.extend(["--user-agent", ua])

    if params:
        for key, value in params.items():
            if value is not None:
                cmd.extend([f"--{_camel_to_kebab(key)}", str(value)])

    env = os.environ.copy()

    import shlex
    shell_cmd = " ".join(shlex.quote(c) for c in cmd)
    try:
        result = subprocess.run(
            shell_cmd, shell=True, capture_output=True, text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"API call timed out: {product} {api}"}
    except FileNotFoundError:
        return {"error": "aliyun CLI not available"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        error_msg = stderr or stdout or f"API call failed (exit code {result.returncode})"
        try:
            err_json = json.loads(error_msg)
            code = err_json.get("Code", "")
            message = err_json.get("Message", error_msg)
            if code == "Forbidden" or "Forbidden" in str(message):
                return {"error": f"Permission denied: {message}. Check RAM policy."}
            elif code == "Throttling" or "Throttling" in str(message):
                return {"error": f"API throttled: {message}. Retry later."}
            elif "InvalidDomainName" in code or "DomainNotFound" in code:
                return {"error": f"Domain not found or not in current account: {message}"}
            return {"error": f"{code}: {message}"}
        except json.JSONDecodeError:
            return {"error": error_msg}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Cannot parse API response: {stdout[:200]}"}


def _call_with_retry(product: str, api: str, params: dict = None,
                     region: str = None, max_retries: int = 3) -> dict:
    """API call with retry for transient errors (throttling, etc.)."""
    for attempt in range(max_retries):
        result = _run_cli(product, api, params, region)
        error = result.get("error", "")
        if "Throttling" in error or "throttled" in error:
            wait = 2 ** attempt
            time.sleep(wait)
            continue
        return result
    return result


# --- STS AssumeRole ---

def _get_sts_credentials() -> Optional[dict]:
    """
    Get STS temporary credentials (if ROLE_ARN is configured).
    Uses cache to avoid repeated calls.

    Returns:
        dict with {AccessKeyId, AccessKeySecret, SecurityToken} or None
    """
    role_arn = os.environ.get("ALIBABA_CLOUD_ROLE_ARN", "")
    if not role_arn:
        return None

    if _sts_cache["credentials"] and time.time() < _sts_cache["expiration"] - 300:
        return _sts_cache["credentials"]

    cmd = [
        "aliyun", "sts", "assume-role",
        "--role-arn", role_arn,
        "--role-session-name", "dnsdiag",
        "--duration-seconds", "3600",
        "--region", "cn-hangzhou",
        "--read-timeout", "30", "--connect-timeout", "10",
        "--user-agent", f"AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose/{os.environ.get('SESSION_ID', 'no-session')}",
    ]

    import shlex
    shell_cmd = " ".join(shlex.quote(c) for c in cmd)
    try:
        result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True, timeout=15)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0:
        print(f"[WARNING] STS assume-role failed: {result.stderr}", file=sys.stderr)
        return None

    try:
        resp = json.loads(result.stdout)
        creds = resp.get("Credentials", {})
        _sts_cache["credentials"] = creds
        exp_str = creds.get("Expiration", "")
        if exp_str:
            from datetime import datetime, timezone
            try:
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%dT%H:%M:%SZ")
                _sts_cache["expiration"] = exp_dt.replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                _sts_cache["expiration"] = time.time() + 3300
        return creds
    except json.JSONDecodeError:
        return None


# --- Alidns API ---

def describe_domains(keyword: str = None, region: str = None) -> dict:
    """
    Query domain list under the account.

    Returns:
        dict: {"domains": [{"DomainName": ..., "DomainId": ..., ...}], "total": int}
    """
    params = {"PageSize": "100"}
    if keyword:
        params["KeyWord"] = keyword
        params["SearchMode"] = "LIKE"

    result = _call_with_retry("alidns", "describe-domains", params, region)
    if "error" in result:
        return result

    domains = result.get("Domains", {}).get("Domain", [])
    return {
        "domains": domains,
        "total": result.get("TotalCount", 0),
    }


def describe_domain_info(domain: str, region: str = None) -> dict:
    """
    Query domain configuration details.

    Returns:
        dict: Domain details (DNS servers, version, line types, etc.)
    """
    params = {
        "DomainName": domain,
        "NeedDetailAttributes": "true",
    }
    result = _call_with_retry("alidns", "describe-domain-info", params, region)
    return result


def describe_domain_records(domain: str, rr: str = None,
                            record_type: str = None,
                            region: str = None) -> dict:
    """
    Query DNS records for a domain. Automatically paginates to fetch all records.

    Returns:
        dict: {"records": [{RR, Type, Value, TTL, Line, Status, ...}], "total": int}
    """
    all_records = []
    page = 1
    page_size = 500

    while True:
        params = {
            "DomainName": domain,
            "PageNumber": str(page),
            "PageSize": str(page_size),
        }
        if rr:
            params["RRKeyWord"] = rr
            params["SearchMode"] = "EXACT"
        if record_type:
            params["Type"] = record_type

        result = _call_with_retry("alidns", "describe-domain-records", params, region)
        if "error" in result:
            if all_records:
                break
            return result

        records = result.get("DomainRecords", {}).get("Record", [])
        all_records.extend(records)

        total = result.get("TotalCount", 0)
        if page * page_size >= total:
            break
        page += 1

    return {
        "records": all_records,
        "total": len(all_records),
    }


# --- Domain API ---

def query_domain_registration(domain: str, region: str = None) -> dict:
    """
    Query domain registration info (only for domains registered at Alibaba Cloud).

    Returns:
        dict: Registration info (expiry date, status, real-name verification, etc.)
    """
    params = {"DomainName": domain}
    result = _call_with_retry("domain", "query-domain-by-domain-name", params, region)
    return result


# --- GTM API ---

def describe_gtm_instances(keyword: str = None, region: str = None) -> dict:
    """
    Query DNS GTM instance list.

    Returns:
        dict: {"instances": [...], "total": int}
    """
    params = {"PageSize": "100"}
    if keyword:
        params["Keyword"] = keyword

    result = _call_with_retry("alidns", "describe-dns-gtm-instances", params, region)
    if "error" not in result:
        instances = result.get("GtmInstances", [])
        return {
            "instances": instances,
            "total": result.get("TotalItems", 0),
            "version": "new",
        }

    result = _call_with_retry("alidns", "describe-gtm-instances", params, region)
    if "error" in result:
        return result

    instances = result.get("GtmInstances", {}).get("GtmInstance", [])
    return {
        "instances": instances,
        "total": result.get("TotalItems", 0),
        "version": "old",
    }


def describe_dns_gtm_instance(instance_id: str, region: str = None) -> dict:
    """Query GTM instance details."""
    params = {"InstanceId": instance_id}
    result = _call_with_retry("alidns", "describe-dns-gtm-instance", params, region)
    if "error" not in result:
        return result
    result = _call_with_retry("alidns", "describe-gtm-instance", params, region)
    return result


def describe_gtm_access_strategies(instance_id: str, region: str = None) -> dict:
    """Query GTM access strategy list."""
    params = {
        "InstanceId": instance_id,
        "PageSize": "100",
    }
    result = _call_with_retry("alidns", "describe-dns-gtm-access-strategies", params, region)
    if "error" in result:
        result = _call_with_retry("alidns", "describe-gtm-access-strategies", params, region)
    return result


# --- PrivateZone API ---

def describe_zones(keyword: str = None, vpc_id: str = None,
                   region: str = None) -> dict:
    """
    Query PrivateZone list.

    Returns:
        dict: {"zones": [...], "total": int}
    """
    params = {"PageSize": "100"}
    if keyword:
        params["Keyword"] = keyword
        params["SearchMode"] = "LIKE"
    if vpc_id:
        params["QueryVpcId"] = vpc_id

    result = _call_with_retry("pvtz", "describe-zones", params, region)
    if "error" in result:
        return result

    zones = result.get("Zones", {}).get("Zone", [])
    return {
        "zones": zones,
        "total": result.get("TotalItems", 0),
    }


def describe_zone_records(zone_id: str, keyword: str = None,
                          region: str = None) -> dict:
    """
    Query PrivateZone DNS records.

    Returns:
        dict: {"records": [...], "total": int}
    """
    all_records = []
    page = 1

    while True:
        params = {
            "ZoneId": zone_id,
            "PageNumber": str(page),
            "PageSize": "100",
        }
        if keyword:
            params["Keyword"] = keyword
            params["SearchMode"] = "LIKE"

        result = _call_with_retry("pvtz", "describe-zone-records", params, region)
        if "error" in result:
            if all_records:
                break
            return result

        records = result.get("Records", {}).get("Record", [])
        all_records.extend(records)

        total = result.get("TotalItems", 0)
        if page * 100 >= total:
            break
        page += 1

    return {
        "records": all_records,
        "total": len(all_records),
    }


def describe_zone_info(zone_id: str, region: str = None) -> dict:
    """Query PrivateZone details (including VPC bindings)."""
    params = {"ZoneId": zone_id}
    result = _call_with_retry("pvtz", "describe-zone-info", params, region)
    return result


# --- Utility functions ---

def check_domain_in_account(domain: str, region: str = None) -> dict:
    """
    Check whether the domain exists in the current account.

    Returns:
        dict: {"found": bool, "domain_info": dict or None, "product": str}
    """
    info = describe_domain_info(domain, region)
    records_resp = describe_domain_records(domain, region=region)
    records = records_resp.get("records", []) if "error" not in records_resp else []

    if "error" not in info and info.get("DomainName"):
        return {
            "found": True,
            "domain_info": info,
            "records": records,
            "product": "alidns",
        }

    if records:
        return {
            "found": True,
            "domain_info": info if "error" not in info else {},
            "records": records,
            "product": "alidns",
        }

    zones = describe_zones(keyword=domain, region=region)
    if "error" not in zones:
        for zone in zones.get("zones", []):
            if zone.get("ZoneName", "").rstrip(".") == domain.rstrip("."):
                return {
                    "found": True,
                    "domain_info": zone,
                    "product": "privatezone",
                }

    reg = query_domain_registration(domain, region)
    if "error" not in reg and reg.get("DomainName"):
        return {
            "found": True,
            "domain_info": reg,
            "product": "domain_registered",
        }

    return {"found": False, "domain_info": None, "product": None}


def get_all_records_for_candidates(candidates: list, region: str = None) -> dict:
    """
    Query DNS records for all predicted domain candidates.

    Args:
        candidates: list[DomainCandidate] from dns_common.split_domain

    Returns:
        dict: {zone: {"records": [...], "matched_rr": [...]}}
    """
    results = {}

    for candidate in candidates:
        zone = candidate.zone if hasattr(candidate, "zone") else candidate["zone"]
        rr = candidate.rr if hasattr(candidate, "rr") else candidate["rr"]

        if zone in results:
            continue

        records_resp = describe_domain_records(zone, region=region)
        if "error" in records_resp:
            results[zone] = {"error": records_resp["error"], "records": [], "matched_rr": []}
            continue

        all_records = records_resp.get("records", [])

        matched = []
        for rec in all_records:
            rec_rr = rec.get("RR", "")
            if rec_rr == rr or rec_rr == "*":
                matched.append(rec)

        results[zone] = {
            "all_records": all_records,
            "matched_rr": matched,
            "query_rr": rr,
            "total": len(all_records),
        }

    return results


# --- CLI entry point ---

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Alibaba Cloud DNS OpenAPI tool")
    sub = parser.add_subparsers(dest="action")

    p = sub.add_parser("domains", help="Query domain list")
    p.add_argument("--keyword", help="Search keyword")

    p = sub.add_parser("domain-info", help="Query domain details")
    p.add_argument("--domain", required=True)

    p = sub.add_parser("records", help="Query DNS records")
    p.add_argument("--domain", required=True)
    p.add_argument("--rr", help="Host record filter")
    p.add_argument("--type", help="Record type filter")

    p = sub.add_parser("registration", help="Query domain registration info")
    p.add_argument("--domain", required=True)

    p = sub.add_parser("gtm", help="Query GTM instance list")
    p.add_argument("--keyword", help="Search keyword")

    p = sub.add_parser("pvtz-zones", help="Query PrivateZone list")
    p.add_argument("--keyword", help="Search keyword")

    p = sub.add_parser("pvtz-records", help="Query PrivateZone records")
    p.add_argument("--zone-id", required=True)

    p = sub.add_parser("check", help="Check if domain is in current account")
    p.add_argument("--domain", required=True)

    args = parser.parse_args()

    if args.action == "domains":
        result = describe_domains(args.keyword)
    elif args.action == "domain-info":
        result = describe_domain_info(args.domain)
    elif args.action == "records":
        result = describe_domain_records(args.domain, args.rr, getattr(args, "type", None))
    elif args.action == "registration":
        result = query_domain_registration(args.domain)
    elif args.action == "gtm":
        result = describe_gtm_instances(args.keyword)
    elif args.action == "pvtz-zones":
        result = describe_zones(args.keyword)
    elif args.action == "pvtz-records":
        result = describe_zone_records(args.zone_id)
    elif args.action == "check":
        result = check_domain_in_account(args.domain)
    else:
        parser.print_help()
        return

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
