"""
dns_openapi.py - Alibaba Cloud OpenAPI wrapper

Invokes DNS-related APIs via aliyun CLI or Python SDK.
Supports STS AssumeRole for cross-account access.
Covers: Alidns (Cloud DNS), Domain, pvtz (PrivateZone), STS.
"""

import json
import os
import shutil
import subprocess
import sys
import time
from typing import Optional

import re

HAS_CLI = shutil.which("aliyun") is not None


def _to_plugin_action(api_name: str) -> str:
    """Convert PascalCase API name to CLI plugin mode kebab-case.

    e.g. DescribeDomains -> describe-domains
    """
    s = re.sub(r'([A-Z])', r'-\1', api_name).lower().lstrip('-')
    return s

# STS temporary credential cache
_sts_cache = {
    "credentials": None,
    "expiration": 0,
}


def _run_cli(product: str, api: str, params: dict = None,
             region: str = None, timeout: int = 30) -> dict:
    """
    Call aliyun CLI and return JSON result.

    Args:
        product: product code (alidns, domain, pvtz, sts)
        api: API name
        params: request parameters
        region: region
        timeout: timeout in seconds

    Returns:
        dict: API response JSON
    """
    if not HAS_CLI:
        return {"error": "aliyun CLI unavailable, please install: https://help.aliyun.com/document_detail/139508.html"}

    action = _to_plugin_action(api)
    cmd = ["aliyun", product, action]

    # Add region (default cn-hangzhou)
    effective_region = region or os.environ.get("ALIBABA_CLOUD_REGION", "cn-hangzhou")
    cmd.extend(["--region", effective_region])

    # Security: must set timeout and user-agent
    cmd.extend(["--read-timeout", "30", "--connect-timeout", "10"])
    session_id = os.environ.get("ALICLOUD_SKILL_SESSION_ID", "unknown")
    default_ua = f"AlibabaCloud-Agent-Skills/alibabacloud-dns-resolve-diagnose-customer/{session_id}"
    ua = os.environ.get("ALIBABA_CLOUD_USER_AGENT", default_ua)
    cmd.extend(["--user-agent", ua])

    # Add params (PascalCase -> kebab-case for aliyun CLI plugin mode)
    if params:
        for key, value in params.items():
            if value is not None:
                kebab_key = _to_plugin_action(key)
                cmd.extend([f"--{kebab_key}", str(value)])

    # If STS credentials available, pass via CLI args
    env = os.environ.copy()
    sts_creds = _get_sts_credentials()
    if sts_creds:
        cmd.extend(["--sts-token", sts_creds["SecurityToken"]])

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, env=env,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"API call timed out: {product} {api}"}
    except FileNotFoundError:
        return {"error": "aliyun CLI unavailable"}

    stdout = result.stdout.strip()
    stderr = result.stderr.strip()

    if result.returncode != 0:
        # Try to parse error message from stderr
        error_msg = stderr or stdout or f"API call failed (exit code {result.returncode})"
        try:
            err_json = json.loads(error_msg)
            code = err_json.get("Code", "")
            message = err_json.get("Message", error_msg)
            if code == "Forbidden" or "Forbidden" in str(message):
                return {"error": f"Insufficient permissions: {message}. Please check RAM permission configuration."}
            elif code == "Throttling" or "Throttling" in str(message):
                return {"error": f"API throttled: {message}. Please retry later."}
            elif "InvalidDomainName" in code or "DomainNotFound" in code:
                return {"error": f"Domain does not exist or is not under the current account: {message}"}
            return {"error": f"{code}: {message}"}
        except json.JSONDecodeError:
            return {"error": error_msg}

    try:
        return json.loads(stdout)
    except json.JSONDecodeError:
        return {"error": f"Cannot parse API response: {stdout[:200]}"}


def _call_with_retry(product: str, api: str, params: dict = None,
                     region: str = None, max_retries: int = 3) -> dict:
    """API call with retry (handles throttling and transient errors)."""
    for attempt in range(max_retries):
        result = _run_cli(product, api, params, region)
        error = result.get("error", "")
        if "throttled" in error or "Throttling" in error:
            wait = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
            time.sleep(wait)
            continue
        return result
    return result


# ─── STS AssumeRole ────────────────────────────────────────────────

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

    # Check if cache is still valid (refresh 5 min before expiry)
    if _sts_cache["credentials"] and time.time() < _sts_cache["expiration"] - 300:
        return _sts_cache["credentials"]

    # Call STS AssumeRole (without STS token, use original AK/SK)
    cmd = [
        "aliyun", "sts", _to_plugin_action("AssumeRole"),
        "--RoleArn", role_arn,
        "--RoleSessionName", "dnsdiag",
        "--DurationSeconds", "3600",
        "--region", "cn-hangzhou",
    ]

    # Call STS AssumeRole without shell=True to avoid shell injection
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if result.returncode != 0:
        print(f"[WARNING] STS AssumeRole failed: {result.stderr}", file=sys.stderr)
        return None

    try:
        resp = json.loads(result.stdout)
        creds = resp.get("Credentials", {})
        _sts_cache["credentials"] = creds
        # Parse expiration time
        exp_str = creds.get("Expiration", "")
        if exp_str:
            from datetime import datetime, timezone
            try:
                exp_dt = datetime.strptime(exp_str, "%Y-%m-%dT%H:%M:%SZ")
                _sts_cache["expiration"] = exp_dt.replace(tzinfo=timezone.utc).timestamp()
            except ValueError:
                _sts_cache["expiration"] = time.time() + 3300  # Default 55 minutes
        return creds
    except json.JSONDecodeError:
        return None


# ─── Alidns API ────────────────────────────────────────────────────

def describe_domains(keyword: str = None, region: str = None) -> dict:
    """
    Query the domain list under the account.

    Returns:
        dict: {"domains": [{"DomainName": ..., "DomainId": ..., ...}], "total": int}
    """
    params = {"PageSize": "100"}
    if keyword:
        params["KeyWord"] = keyword
        params["SearchMode"] = "LIKE"

    result = _call_with_retry("alidns", "DescribeDomains", params, region)
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
        dict: domain details (DNS servers, version, line type, etc.)
    """
    params = {
        "DomainName": domain,
        "NeedDetailAttributes": "true",
    }
    result = _call_with_retry("alidns", "DescribeDomainInfo", params, region)
    return result


def describe_domain_records(domain: str, rr: str = None,
                            record_type: str = None,
                            region: str = None) -> dict:
    """
    Query DNS record list of a domain. Auto-pagination to fetch all records.

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

        result = _call_with_retry("alidns", "DescribeDomainRecords", params, region)
        if "error" in result:
            if all_records:
                # Already got partial data, return what we have
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


# ─── Domain API ────────────────────────────────────────────────────

def query_domain_registration(domain: str, region: str = None) -> dict:
    """
    Query domain registration info (Alibaba Cloud registered domains only).

    Returns:
        dict: registration info (expiry, status, real-name verification, etc.)
    """
    params = {"DomainName": domain}
    result = _call_with_retry("domain", "QueryDomainByDomainName", params, region)
    return result


# ─── GTM API ───────────────────────────────────────────────────────

def describe_gtm_instances(keyword: str = None, region: str = None) -> dict:
    """
    Query new-version DNS GTM instance list.

    Returns:
        dict: {"instances": [...], "total": int}
    """
    params = {"PageSize": "100"}
    if keyword:
        params["Keyword"] = keyword

    # Try new-version GTM first
    result = _call_with_retry("alidns", "DescribeDnsGtmInstances", params, region)
    if "error" not in result:
        instances = result.get("GtmInstances", [])
        return {
            "instances": instances,
            "total": result.get("TotalItems", 0),
            "version": "new",
        }

    # New version failed, try legacy version
    result = _call_with_retry("alidns", "DescribeGtmInstances", params, region)
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
    # Try new version first
    result = _call_with_retry("alidns", "DescribeDnsGtmInstance", params, region)
    if "error" not in result:
        return result
    # Fallback to legacy version
    result = _call_with_retry("alidns", "DescribeGtmInstance", params, region)
    return result


def describe_gtm_access_strategies(instance_id: str, region: str = None) -> dict:
    """Query GTM access policy list."""
    params = {
        "InstanceId": instance_id,
        "PageSize": "100",
    }
    result = _call_with_retry("alidns", "DescribeDnsGtmAccessStrategies", params, region)
    if "error" in result:
        # Try legacy version
        result = _call_with_retry("alidns", "DescribeGtmAccessStrategies", params, region)
    return result


# ─── PrivateZone API ───────────────────────────────────────────────

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

    result = _call_with_retry("pvtz", "DescribeZones", params, region)
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

        result = _call_with_retry("pvtz", "DescribeZoneRecords", params, region)
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
    """
    Query PrivateZone details (including VPC binding info).
    """
    params = {"ZoneId": zone_id}
    result = _call_with_retry("pvtz", "DescribeZoneInfo", params, region)
    return result


# ─── Convenience functions ──────────────────────────────────────────────────────

def check_domain_in_account(domain: str, region: str = None) -> dict:
    """
    Check whether the domain is under the current account.

    Returns:
        dict: {"found": bool, "domain_info": dict or None, "product": str}
    """
    # Check Cloud DNS
    info = describe_domain_info(domain, region)
    if "error" not in info and info.get("DomainName"):
        return {
            "found": True,
            "domain_info": info,
            "product": "alidns",
        }

    # Check PrivateZone
    zones = describe_zones(keyword=domain, region=region)
    if "error" not in zones:
        for zone in zones.get("zones", []):
            if zone.get("ZoneName", "").rstrip(".") == domain.rstrip("."):
                return {
                    "found": True,
                    "domain_info": zone,
                    "product": "privatezone",
                }

    # Check domain registration
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
            # Already queried this zone
            continue

        records_resp = describe_domain_records(zone, region=region)
        if "error" in records_resp:
            results[zone] = {"error": records_resp["error"], "records": [], "matched_rr": []}
            continue

        all_records = records_resp.get("records", [])

        # Filter records matching RR
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


# ─── CLI entry point ──────────────────────────────────────────────────────

def _normalize_argv(argv):
    """Normalize CLI arguments: convert PascalCase/kebab-case flags to script's expected format.

    Maps common Agent mistakes to correct flags:
    --DomainName / --domain-name -> --domain
    --RR / --HostRecord -> --rr
    --Type / --RecordType -> --type
    --ZoneId / --zone-id -> --zone-id
    --Keyword -> --keyword
    """
    alias_map = {
        "--domainname": "--domain",
        "--domain-name": "--domain",
        "--domain_name": "--domain",
        "--rr": "--rr",
        "--hostrecord": "--rr",
        "--host-record": "--rr",
        "--type": "--type",
        "--recordtype": "--type",
        "--record-type": "--type",
        "--zoneid": "--zone-id",
        "--zone_id": "--zone-id",
        "--keyword": "--keyword",
    }
    result = []
    for arg in argv:
        if arg.startswith("--") and "=" in arg:
            flag, _, val = arg.partition("=")
            normalized = alias_map.get(flag.lower(), flag)
            result.append(f"{normalized}={val}")
        elif arg.startswith("--"):
            result.append(alias_map.get(arg.lower(), arg))
        else:
            result.append(arg)
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Alibaba Cloud DNS OpenAPI tool")
    sub = parser.add_subparsers(dest="action")

    # Domain list
    p = sub.add_parser("domains", help="Query domain list")
    p.add_argument("--keyword", "--Keyword", help="Search keyword")

    # Domain details
    p = sub.add_parser("domain-info", help="Query domain config details")
    p.add_argument("--domain", "--DomainName", "--domain-name", required=True, help="Domain")

    # DNS records
    p = sub.add_parser("records", help="Query DNS records")
    p.add_argument("--domain", "--DomainName", "--domain-name", required=True, help="Domain")
    p.add_argument("--rr", "--RR", "--HostRecord", help="Host record filter")
    p.add_argument("--type", "--Type", "--RecordType", help="Record type filter")

    # Domain registration info
    p = sub.add_parser("registration", help="Query domain registration info")
    p.add_argument("--domain", "--DomainName", "--domain-name", required=True, help="Domain")

    # GTM instance
    p = sub.add_parser("gtm", help="Query GTM instance list")
    p.add_argument("--keyword", "--Keyword", help="Search keyword")

    # PrivateZone
    p = sub.add_parser("pvtz-zones", help="Query PrivateZone list")
    p.add_argument("--keyword", "--Keyword", help="Search keyword")

    p = sub.add_parser("pvtz-records", help="Query PrivateZone records")
    p.add_argument("--zone-id", "--ZoneId", "--zone_id", required=True, help="Zone ID")

    # Account domain check
    p = sub.add_parser("check", help="Check whether domain is under current account")
    p.add_argument("--domain", "--DomainName", "--domain-name", required=True, help="Domain")

    # Normalize argv to handle PascalCase/kebab-case aliases
    normalized_argv = _normalize_argv(sys.argv[1:])
    args = parser.parse_args(normalized_argv)

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
