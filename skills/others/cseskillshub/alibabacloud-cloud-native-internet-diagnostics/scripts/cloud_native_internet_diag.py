#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SECURITY:
#   - Read-only diagnostics: only Get/Describe APIs are invoked. No resource is
#     created, modified, or deleted.
#   - Single-resource scope: only the one instance / application / function
#     explicitly provided by the user is queried. No scanning or enumeration.
#   - Run only after the user confirms the target (see SKILL.md "User
#     Confirmation").
#   - Credentials are resolved exclusively by the aliyun CLI default credential
#     chain (CLI config or platform-injected environment). This script accepts
#     no AK/SK/token parameters and never reads, prints, or caches credentials.
#   - subprocess is always invoked with an argument list (never shell=True),
#     with stdin=DEVNULL and a hard timeout.
"""
cloud_native_internet_diag.py — Cloud-native product public internet egress
diagnostics (single business entry point).

Covers five Alibaba Cloud cloud-native products:
    mse_gateway   Cloud-native gateway (MSE), instance id starts with gw-
    apig_gateway  Cloud-native API gateway, instance id starts with gw-
    ai_gateway    AI gateway (same API as apig_gateway, distinguished by
                  response field data.gatewayType)
    sae           Serverless App Engine, application id is a UUID
    fc            Function Compute, the instance id is the function name

Flow:
    1. Query the product instance and extract VPC id + vSwitch id
    2. (FC only) Apply the internetAccess / vpcConfig four-quadrant rules
       A/B/C/D; NAT/SNAT egress check runs only for quadrant D
    3. Inline vSwitch egress check: DescribeVSwitchAttributes ->
       DescribeNatGateways -> DescribeSnatTableEntries, deciding whether the
       vSwitch has a NAT SNAT public egress
    4. Dual-layer output: a structured JSON report on stdout (machine layer,
       incl. summary / plain_language_conclusion / recommended_actions for
       non-technical users and downstream agents); progress/warnings plus a
       human-readable report block on stderr (user layer)

Auth: relies entirely on the aliyun CLI default chain; this script performs
no explicit auth handling (SA-2.12).

Usage:
    python3 cloud_native_internet_diag.py \
        --product mse_gateway --region cn-hangzhou --instance-id gw-xxxxxxx

Zero third-party dependencies: standard library + aliyun CLI only.
"""

import argparse
import ipaddress
import json
import re
import shutil
import subprocess
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Per-run session id for platform-level tracing (Observability SA-2.11b/c)
_SESSION_ID = uuid.uuid4().hex
_USER_AGENT = (
    "AlibabaCloud-Agent-Skills/"
    "alibabacloud-cloud-native-internet-diagnostics/" + _SESSION_ID
)

CLI_TIMEOUT_SECONDS = 60

# Pagination limits for vpc Describe* queries (guard against runaway loops)
PAGE_SIZE = 50
MAX_PAGES = 20

# Error codes that indicate an authorization problem (degrade with [WARN])
_AUTH_ERROR_CODES = (
    "Forbidden",
    "Forbidden.RAM",
    "NoPermission",
    "InvalidAccessKeyId.NotFound",
    "SignatureDoesNotMatch",
    "AccessDenied",
    "Unauthorized",
    "SecurityTokenExpired",
)

PRODUCT_NAMES = {
    "mse_gateway": "Cloud-native Gateway (MSE)",
    "apig_gateway": "Cloud-native API Gateway",
    "ai_gateway": "AI Gateway",
    "sae": "Serverless App Engine (SAE)",
    "fc": "Function Compute (FC)",
}

_REGION_RE = re.compile(r"^[a-z]{2}-[a-z0-9]+(-[a-z0-9]+)?$")
_INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9._\-]{1,128}$")
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")
# Plain-text CLI errors carry "ErrorCode: <Code>" (non-JSON fallback).
# [ \t]* (not \s*) prevents matching across newlines into the next field,
# which previously mis-extracted "Recommend" when ErrorCode was empty (ROA
# passthrough errors embed the real payload in Message instead).
_ERROR_CODE_RE = re.compile(r"ErrorCode:[ \t]*([A-Za-z0-9_.\-]+)")
# ROA errors may embed a JSON body in the plain-text Message field
# ({"code": "NotFound.GatewayNotFound", "message": "..."}).
_EMBEDDED_CODE_RE = re.compile(r'"code"\s*:\s*"([^"]+)"')
_EMBEDDED_MSG_RE = re.compile(r'"message"\s*:\s*"([^"]+)"')


def _log(msg: str) -> None:
    """Progress log to stderr (stdout stays pure JSON)."""
    print(msg, file=sys.stderr, flush=True)


# ==================== aliyun CLI subprocess layer ====================

def _sanitize_message(text: str, limit: int = 220) -> str:
    """Collapse whitespace, drop non-ASCII chars (upstream API messages may
    carry localized text), and cap length. Keeps all output English-only."""
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    return cleaned[:limit].strip()


def _parse_cli_error(stdout: str, stderr: str) -> Tuple[str, str]:
    """Extract (Code, Message) from aliyun CLI error output (JSON or plain)."""
    for text in (stdout, stderr):
        if not text:
            continue
        try:
            data = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            continue
        if isinstance(data, dict) and data.get("Code"):
            return (str(data["Code"]),
                    _sanitize_message(str(data.get("Message", "")), 500))
    detail = _ANSI_RE.sub("", (stderr or stdout or "")).strip()
    code: Optional[str] = None
    message: Optional[str] = None
    m = _ERROR_CODE_RE.search(detail)
    if m:
        code = m.group(1)
    # ROA passthrough errors (apig/sae/fc) often leave ErrorCode empty and
    # embed the real error as JSON inside the Message line.
    mc = _EMBEDDED_CODE_RE.search(detail)
    if mc:
        code = mc.group(1)
        mm = _EMBEDDED_MSG_RE.search(detail)
        if mm:
            message = mm.group(1)
    if code:
        return code, _sanitize_message(message or detail, 300)
    return "CliError", _sanitize_message(detail, 300)


def _is_auth_error(code: str) -> bool:
    code_l = (code or "").lower()
    return any(c.lower() in code_l for c in _AUTH_ERROR_CODES)


def _cidr_contains(outer: str, inner: str) -> bool:
    """True when network `outer` fully covers network `inner` (both CIDR)."""
    try:
        return ipaddress.ip_network(outer, strict=False).supernet_of(
            ipaddress.ip_network(inner, strict=False))
    except (ValueError, TypeError):
        return False


def run_cli(cmd: List[str], label: str) -> Tuple[Optional[Dict[str, Any]], Optional[str], bool]:
    """Run an aliyun CLI command (argument list, no shell) and parse JSON.

    Returns (data, error, is_auth_error):
        data  - parsed JSON dict on success, else None
        error - "<Code>: <Message>" on failure, else None
    """
    if shutil.which("aliyun") is None:
        return None, (
            "CliNotFound: aliyun CLI not found on PATH. "
            "Install it and run 'aliyun configure'"
        ), False

    _log(f"[INFO] calling {label}")
    try:
        # stdin=DEVNULL: never hang on interactive CLI prompts (e.g. plugin
        # auto-install questions); fail fast with a timeout/error instead.
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            timeout=CLI_TIMEOUT_SECONDS, stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return None, f"CliError: {label} timed out after {CLI_TIMEOUT_SECONDS}s", False
    except FileNotFoundError:
        return None, (
            "CliNotFound: aliyun CLI not found on PATH. "
            "Install it and run 'aliyun configure'"
        ), False

    data: Optional[Dict[str, Any]] = None
    try:
        parsed = json.loads(proc.stdout)
        if isinstance(parsed, dict):
            data = parsed
    except (json.JSONDecodeError, ValueError):
        pass

    if proc.returncode != 0:
        code, message = _parse_cli_error(proc.stdout, proc.stderr)
        return None, f"{code}: {message}", _is_auth_error(code)

    if data is None:
        return None, "CliError: unparseable JSON response from aliyun CLI", False
    if isinstance(data, dict):
        code = data.get("Code")
        # mse/sae success payloads carry Code:200 / Code:"200" plus
        # Success:true; only a non-200 Code without Success:true is an error.
        if (code is not None and str(code) not in ("200", "")
                and data.get("Success") is not True):
            code_s = str(code)
            return None, f"{code_s}: {str(data.get('Message', ''))[:500]}", \
                _is_auth_error(code_s)
    return data, None, False


# ==================== Step 1: instance lookup (five products) ====================

def query_mse_gateway(region: str, instance_id: str) -> Dict[str, Any]:
    """mse:GetGateway (CLI plugin mode `mse get-gateway`). Fields: Data.Vpc,
    Data.Vswitch."""
    cmd = [
        "aliyun", "mse", "get-gateway",
        "--gateway-unique-id", instance_id,
        "--region", region,
        "--user-agent", _USER_AGENT,
    ]
    data, err, auth = run_cli(cmd, "mse:GetGateway")
    if err:
        return {"success": False, "error": err, "auth_error": auth}

    gw = (data or {}).get("Data") or {}
    if not gw:
        return {
            "success": False,
            "error": (f"InstanceNotFound: gateway {instance_id} not found in "
                      f"region {region}; check the instance id and region"),
            "auth_error": False,
        }
    return {
        "success": True,
        "product": "mse_gateway",
        "instance_name": gw.get("Name", ""),
        "status": gw.get("Status"),
        "vpc_id": gw.get("Vpc", ""),
        "vswitch_id": gw.get("Vswitch", ""),
    }


def query_apig_gateway(region: str, instance_id: str,
                       requested_product: str) -> Dict[str, Any]:
    """apig:GetGateway (ROA passthrough). Fields: data.vpc.vpcId,
    data.vSwitch.vSwitchId, data.gatewayType (API/AI)."""
    cmd = [
        "aliyun", "apig", "GET", "/v1/gateways/" + instance_id,
        "--region", region,
        "--user-agent", _USER_AGENT,
    ]
    data, err, auth = run_cli(cmd, "apig:GetGateway")
    if err:
        return {"success": False, "error": err, "auth_error": auth}

    gw = (data or {}).get("data") or {}
    if not gw:
        return {
            "success": False,
            "error": (f"InstanceNotFound: gateway {instance_id} not found in "
                      f"region {region}; check the instance id and region"),
            "auth_error": False,
        }
    gateway_type = str(gw.get("gatewayType") or "API")
    product = "ai_gateway" if gateway_type == "AI" else "apig_gateway"
    if requested_product != product:
        _log(f"[WARN] user requested {requested_product} but the gateway "
             f"gatewayType is '{gateway_type}' -> reporting as {product}")
    return {
        "success": True,
        "product": product,
        "gateway_type": gateway_type,
        "instance_name": gw.get("name", ""),
        "status": gw.get("status", ""),
        "vpc_id": (gw.get("vpc") or {}).get("vpcId", ""),
        "vswitch_id": (gw.get("vSwitch") or {}).get("vSwitchId", ""),
    }


def query_sae(region: str, instance_id: str) -> Dict[str, Any]:
    """sae:DescribeApplicationConfig (ROA passthrough). Fields: Data.VpcId,
    Data.VSwitchId."""
    cmd = [
        "aliyun", "sae", "GET", "/pop/v1/sam/app/describeApplicationConfig",
        "--AppId", instance_id,
        "--region", region,
        "--user-agent", _USER_AGENT,
    ]
    data, err, auth = run_cli(cmd, "sae:DescribeApplicationConfig")
    if err:
        return {"success": False, "error": err, "auth_error": auth}

    app = (data or {}).get("Data") or {}
    if not app:
        return {
            "success": False,
            "error": (f"InstanceNotFound: SAE application {instance_id} not "
                      f"found in region {region}; check the app id and region"),
            "auth_error": False,
        }
    return {
        "success": True,
        "product": "sae",
        "instance_name": app.get("AppName", ""),
        "vpc_id": app.get("VpcId", ""),
        "vswitch_id": app.get("VSwitchId", ""),
        "namespace_id": app.get("NamespaceId", ""),
    }


def _fc_quadrant(has_vpc: bool, internet_access: bool) -> Tuple[str, str, bool]:
    """FC four-quadrant rules (see references/module2_vswitch_egress.md).

    Returns (quadrant, diagnosis, need_vswitch_check).
    """
    if not has_vpc and internet_access:
        return (
            "A",
            "Quadrant A: no VPC configured and internetAccess=true. The "
            "function reaches the public internet via a shared public IP; "
            "there is NO fixed public egress IP",
            False,
        )
    if not has_vpc and not internet_access:
        return (
            "B",
            "Quadrant B: no VPC configured and internetAccess=false. The "
            "function CANNOT access the public internet",
            False,
        )
    if has_vpc and internet_access:
        return (
            "C",
            "Quadrant C: VPC configured and internetAccess=true. The function "
            "reaches the public internet via a shared public IP (not fixed) "
            "and can also reach VPC internal resources",
            False,
        )
    return (
        "D",
        "Quadrant D: VPC configured and internetAccess=false. The function "
        "egresses through the VPC vSwitch and MAY obtain a fixed public IP "
        "via a NAT gateway SNAT rule; the vSwitch egress must be verified",
        True,
    )


def query_fc(region: str, function_name: str) -> Dict[str, Any]:
    """fc:GetFunction (ROA passthrough). Fields: vpcConfig.vpcId,
    vpcConfig.vSwitchIds (array), internetAccess."""
    cmd = [
        "aliyun", "fc", "GET", "/2023-03-30/functions/" + function_name,
        "--region", region,
        "--user-agent", _USER_AGENT,
    ]
    data, err, auth = run_cli(cmd, "fc:GetFunction")
    if err:
        return {"success": False, "error": err, "auth_error": auth}

    body = data or {}
    vpc_config = body.get("vpcConfig") or {}
    vswitch_ids = vpc_config.get("vSwitchIds") or []
    vpc_id = vpc_config.get("vpcId", "")
    internet_access = bool(body.get("internetAccess", True))
    has_vpc = bool(vswitch_ids and vpc_id)

    quadrant, diagnosis, need_check = _fc_quadrant(has_vpc, internet_access)
    return {
        "success": True,
        "product": "fc",
        "instance_name": body.get("functionName", function_name),
        "vpc_id": vpc_id,
        "vswitch_id": vswitch_ids[0] if vswitch_ids else "",
        "vswitch_ids": vswitch_ids,
        "internet_access": internet_access,
        "has_vpc_config": has_vpc,
        "fc_quadrant": quadrant,
        "diagnosis": diagnosis,
        "need_vswitch_check": need_check,
    }


# ==================== Step 2: inline vSwitch egress check ====================

def check_vswitch_egress(region: str, vswitch_id: str) -> Dict[str, Any]:
    """Decide whether the vSwitch has a NAT SNAT public egress.

    Chain: DescribeVSwitchAttributes (VpcId + CidrBlock) ->
    DescribeNatGateways (server-side --vpc-id filter, paginated) ->
    DescribeSnatTableEntries (paginated; entries match when SourceVSwitchId
    equals the vSwitch, or a SourceCIDR covers the vSwitch CidrBlock).
    Every sub-query failure degrades gracefully with a [WARN] trace on stderr.
    """
    result: Dict[str, Any] = {
        "vswitch_id": vswitch_id,
        "vpc_id": "",
        "nat_gateways_checked": 0,
        "snat_entries_matched": 0,
        "has_public_egress": False,
        "conclusion": "",
        "degraded": False,
        "warnings": [],
    }

    # 2.1 vSwitch attributes
    cmd = [
        "aliyun", "vpc", "describe-vswitch-attributes",
        "--vswitch-id", vswitch_id,
        "--region", region,
        "--user-agent", _USER_AGENT,
    ]
    data, err, auth = run_cli(cmd, "vpc:DescribeVSwitchAttributes")
    if err:
        tag = "[WARN]" if auth else "[ERROR]"
        msg = f"{tag} DescribeVSwitchAttributes failed -> {err}"
        _log(msg)
        result["degraded"] = True
        result["warnings"].append(err)
        result["conclusion"] = (
            "Egress check inconclusive: vSwitch attributes unavailable; "
            "cannot determine NAT SNAT egress"
        )
        return result
    vpc_id = str((data or {}).get("VpcId") or "")
    vswitch_cidr = str((data or {}).get("CidrBlock") or "")
    result["vpc_id"] = vpc_id
    result["vswitch_cidr"] = vswitch_cidr

    # 2.2 NAT gateways of the VPC (server-side VpcId filter + pagination)
    nat_gateways: List[Dict[str, Any]] = []
    page_number = 1
    while page_number <= MAX_PAGES:
        cmd = [
            "aliyun", "vpc", "describe-nat-gateways",
            "--biz-region-id", region,
            "--page-size", str(PAGE_SIZE),
            "--page-number", str(page_number),
            "--region", region,
            "--user-agent", _USER_AGENT,
        ]
        if vpc_id:
            cmd[3:3] = ["--vpc-id", vpc_id]
        data, err, auth = run_cli(
            cmd, f"vpc:DescribeNatGateways(page {page_number})")
        if err:
            tag = "[WARN]" if auth else "[ERROR]"
            _log(f"{tag} DescribeNatGateways failed -> {err}")
            result["degraded"] = True
            result["warnings"].append(err)
            result["conclusion"] = (
                "Egress check inconclusive: NAT gateway list unavailable; "
                "cannot determine NAT SNAT egress"
            )
            return result
        batch = ((data or {}).get("NatGateways") or {}).get("NatGateway") or []
        nat_gateways.extend(batch)
        total = int((data or {}).get("TotalCount") or 0)
        if not batch or len(nat_gateways) >= total:
            break
        page_number += 1
    matched: List[Dict[str, Any]] = []
    for nat in nat_gateways:
        if vpc_id and nat.get("VpcId") and nat.get("VpcId") != vpc_id:
            continue
        matched.append(nat)
    result["nat_gateways_checked"] = len(matched)

    if not matched:
        result["conclusion"] = (
            "No NAT gateway found in the VPC of this vSwitch; the vSwitch has "
            "no NAT SNAT public egress"
        )
        return result

    # 2.3 SNAT table entries of each matched NAT gateway (paginated)
    matched_entries: List[Dict[str, Any]] = []
    for nat in matched:
        snat_table_ids = ((nat.get("SnatTableIds") or {}).get("SnatTableId")) or []
        for table_id in snat_table_ids:
            page_number = 1
            fetched = 0
            while page_number <= MAX_PAGES:
                cmd = [
                    "aliyun", "vpc", "describe-snat-table-entries",
                    "--biz-region-id", region,
                    "--snat-table-id", str(table_id),
                    "--page-size", str(PAGE_SIZE),
                    "--page-number", str(page_number),
                    "--region", region,
                    "--user-agent", _USER_AGENT,
                ]
                data, err, auth = run_cli(
                    cmd, f"vpc:DescribeSnatTableEntries({table_id} page {page_number})")
                if err:
                    tag = "[WARN]" if auth else "[ERROR]"
                    _log(f"{tag} DescribeSnatTableEntries failed -> {err}")
                    result["degraded"] = True
                    result["warnings"].append(err)
                    break
                entries = ((data or {}).get("SnatTableEntries") or {}).get("SnatTableEntry") or []
                total = int((data or {}).get("TotalCount") or 0)
                for entry in entries:
                    vs_hit = entry.get("SourceVSwitchId") == vswitch_id
                    source_cidr = str(entry.get("SourceCIDR") or "")
                    cidr_hit = bool(source_cidr and vswitch_cidr
                                    and _cidr_contains(source_cidr, vswitch_cidr))
                    if (vs_hit or cidr_hit) and entry.get("SnatIp"):
                        matched_entries.append({
                            "snat_table_id": str(table_id),
                            "snat_entry_id": entry.get("SnatEntryId", ""),
                            "snat_ip": entry.get("SnatIp", ""),
                            "status": entry.get("Status", ""),
                            "match": "SourceVSwitchId" if vs_hit else "SourceCIDR",
                        })
                fetched += len(entries)
                if not entries or fetched >= total:
                    break
                page_number += 1

    result["snat_entries_matched"] = len(matched_entries)
    result["matched_snat_entries"] = matched_entries

    if matched_entries:
        available = [e for e in matched_entries if e.get("status") == "Available"]
        result["has_public_egress"] = bool(available)
        if available:
            ips = ", ".join(sorted({e["snat_ip"] for e in available}))
            result["conclusion"] = (
                "The vSwitch has a NAT SNAT public egress: SNAT entry "
                f"(status Available) covers this vSwitch with public IP {ips}; "
                "workloads on this vSwitch can reach the public internet via a "
                "fixed public IP"
            )
        else:
            result["conclusion"] = (
                "SNAT entries cover this vSwitch but none is in status "
                "Available; public egress is currently unreliable"
            )
    elif result["degraded"]:
        result["conclusion"] = (
            "Egress check inconclusive: SNAT table entries could not be fully "
            "queried; rerun after the API error is resolved"
        )
    else:
        result["conclusion"] = (
            "NAT gateway(s) exist in the VPC but no SNAT entry covers this "
            "vSwitch; the vSwitch has no NAT SNAT public egress"
        )
    return result


# ==================== Dual-layer report (user layer + machine layer) ====================

def _egress_ips(egress: Optional[Dict[str, Any]]) -> str:
    """Comma-joined sorted public IPs from matched SNAT entries (incl. sub_checks)."""
    if not egress:
        return ""
    entries: List[Dict[str, Any]] = list(egress.get("matched_snat_entries") or [])
    for sub in egress.get("sub_checks") or []:
        entries.extend(sub.get("matched_snat_entries") or [])
    ips = sorted({str(e.get("snat_ip") or "") for e in entries if e.get("snat_ip")})
    return ", ".join(ips)


def _build_dual_layer(report: Dict[str, Any]) -> None:
    """Fill summary / plain_language_conclusion / recommended_actions.

    summary: a few plain-English sentences for non-technical users.
    plain_language_conclusion: one-sentence verdict.
    recommended_actions: actionable next steps (empty when nothing to do).
    """
    product_name = report.get("product_name") or report.get("product") or "resource"
    egress = report.get("egress_check")
    ips = _egress_ips(egress)
    quadrant = report.get("fc_quadrant")
    summary, plain, actions = "", "", []

    if not report.get("success"):
        err = str(report.get("error") or "")
        code = err.split(":", 1)[0].strip() if err else "UnknownError"
        if report.get("auth_error") or any(
                _is_auth_error(w.split(":", 1)[0]) for w in report.get("warnings") or []):
            summary = (
                f"Unable to verify internet access for this {product_name}: "
                f"the query was rejected for insufficient permissions ({code}). "
                "Please check that the caller account has the read-only RAM "
                "permissions listed in references/ram-policies.md, then retry."
            )
            plain = "Unable to verify: the account lacks the required read permissions."
            actions = [
                "Grant the read-only RAM actions listed in references/ram-policies.md",
                "Rerun the diagnosis after the permissions are attached",
            ]
        else:
            summary = (
                f"Unable to verify internet access for this {product_name}: "
                f"the instance lookup failed ({code}). Please check that the "
                "instance id and region are correct, and that the product type "
                "matches the instance (MSE gateways and API/AI gateways both "
                "use gw- prefixed ids but different APIs)."
            )
            plain = f"Unable to verify: the instance was not found or the query failed ({code})."
            actions = [
                "Double-check the instance id and region with the customer",
                "Confirm the exact product type (mse_gateway / apig_gateway / ai_gateway / sae / fc)",
            ]
    elif quadrant == "A":
        summary = (
            "This FC function CAN access the internet through a shared public "
            "IP provided by Function Compute. The IP is shared with other "
            "customers and is NOT fixed, so it cannot be whitelisted reliably."
        )
        plain = "Internet access works via a shared public IP; there is no fixed egress IP."
        actions = [
            "If a fixed egress IP is required: bind a VPC/vSwitch, set "
            "internetAccess=false, and add a NAT gateway SNAT rule for the vSwitch",
        ]
    elif quadrant == "B":
        summary = (
            "This FC function CANNOT access the public internet: it has no "
            "VPC binding and internet access is disabled."
        )
        plain = "No internet access: VPC not configured and internet access disabled."
        actions = [
            "Enable internetAccess=true for shared public IP egress, or",
            "Bind a VPC/vSwitch with internetAccess=false and add a NAT "
            "gateway SNAT rule for a fixed public egress IP",
        ]
    elif quadrant == "C":
        summary = (
            "This FC function CAN access the internet through a shared public "
            "IP (internetAccess=true) and can also reach resources inside its "
            "VPC. The egress IP is NOT fixed."
        )
        plain = "Internet access works via a shared public IP; there is no fixed egress IP."
        actions = [
            "If a fixed egress IP is required: set internetAccess=false and "
            "add a NAT gateway SNAT rule for the bound vSwitch",
        ]
    elif quadrant == "D" and egress is not None:
        if egress.get("degraded") and not egress.get("has_public_egress"):
            summary = (
                "This FC function routes internet traffic through its VPC "
                "(internetAccess=false), but the NAT egress check could not "
                f"be completed ({'; '.join((egress.get('warnings') or [])[:1])}). "
                "Please check the warnings and rerun."
            )
            plain = "Unable to verify: the NAT/SNAT egress check was incomplete."
            actions = ["Resolve the API errors listed in warnings, then rerun the diagnosis"]
        elif egress.get("has_public_egress"):
            summary = (
                f"This FC function CAN access the internet through a fixed "
                f"public IP {ips} (NAT gateway SNAT). No action needed."
            )
            plain = f"Internet access works through fixed public IP {ips}."
        else:
            summary = (
                "This FC function routes internet traffic through its VPC "
                "(internetAccess=false), but no NAT gateway SNAT rule covers "
                "its vSwitch, so it currently has NO working public egress."
            )
            plain = "No working internet egress: the vSwitch has no NAT SNAT rule."
            actions = [
                "Create a NAT gateway in the VPC (or reuse an existing one)",
                "Add a SNAT entry covering the vSwitch "
                f"({report.get('vswitch_id') or 'the bound vSwitch'}) with an EIP",
            ]
    elif egress is not None:
        if egress.get("degraded") and not egress.get("has_public_egress"):
            summary = (
                f"Unable to fully verify internet access for this {product_name}: "
                f"a sub-query failed ({'; '.join((egress.get('warnings') or [])[:1])}). "
                "Please check the warnings and rerun."
            )
            plain = "Unable to verify: the NAT/SNAT egress check was incomplete."
            actions = ["Resolve the API errors listed in warnings, then rerun the diagnosis"]
        elif egress.get("has_public_egress"):
            summary = (
                f"This {product_name} instance CAN reach the public internet: "
                f"its vSwitch has a NAT gateway SNAT egress with public IP "
                f"{ips}. No action needed."
            )
            plain = f"Internet access works through fixed public IP {ips}."
        else:
            summary = (
                f"This {product_name} instance currently has NO public "
                "internet egress: no NAT gateway SNAT rule covers its vSwitch "
                "(a SNAT rule is what lets private-network workloads reach "
                "the internet through a fixed public IP)."
            )
            plain = "No working internet egress: the vSwitch has no NAT SNAT rule."
            actions = [
                "Create a NAT gateway in the VPC (or reuse an existing one)",
                "Add a SNAT entry covering the vSwitch "
                f"({report.get('vswitch_id') or 'the bound vSwitch'}) with an EIP",
            ]
    else:
        # No egress check ran and no quadrant matched (e.g. no bound vSwitch)
        summary = (
            f"Unable to establish internet egress for this {product_name}: "
            "the instance has no bound vSwitch. "
            f"{'The instance lookup failed; please check the error details.' if not report.get('success') else 'Please check the instance network configuration.'}"
        )
        plain = report.get("conclusion") or "Unable to establish internet egress."
        actions = ["Verify the instance network configuration in the console"]

    report["summary"] = summary
    report["plain_language_conclusion"] = plain
    report["recommended_actions"] = actions


def print_human_report(report: Dict[str, Any]) -> None:
    """Append a human-readable report block to stderr (user layer).

    Existing [INFO]/[WARN]/[ERROR] lines are emitted earlier and stay
    untouched; this block only appends.
    """
    bar = "=" * 64
    _log("")
    _log(bar)
    _log("Public Internet Egress Diagnosis Report")
    _log(bar)
    _log(f"  Product  : {report.get('product_name', report.get('product', ''))}")
    _log(f"  Instance : {report.get('instance_id', '')}")
    _log(f"  Region   : {report.get('region', '')}")
    if report.get("vpc_id"):
        _log(f"  VPC      : {report.get('vpc_id')}")
    if report.get("vswitch_id"):
        _log(f"  vSwitch  : {report.get('vswitch_id')}")
    if report.get("fc_quadrant"):
        _log(f"  FC mode  : quadrant {report.get('fc_quadrant')} "
             f"(internetAccess={'true' if report.get('internet_access') else 'false'})")
    _log("-" * 64)
    _log("  Conclusion:")
    _log(f"    {report.get('plain_language_conclusion', '')}")
    _log("")
    _log("  Details:")
    parts = [p.strip().rstrip(".") for p in (report.get("summary") or "").split(". ")
             if p.strip()]
    for part in parts:
        _log(f"    {part}.")
    _log("")
    _log("  How it works:")
    _log("    The instance sits on a private network (VPC). To reach the")
    _log("    internet it needs an exit route; the common one is a NAT")
    _log("    gateway with a SNAT rule - a managed translator that lets")
    _log("    private workloads go out through a fixed public IP.")
    actions = report.get("recommended_actions") or []
    if actions:
        _log("")
        _log("  Next steps:")
        for i, a in enumerate(actions, start=1):
            _log(f"    {i}. {a}")
    else:
        _log("")
        _log("  Next steps: none - no action needed.")
    _log(bar)


# ==================== Main flow ====================

def diagnose(product: str, region: str, instance_id: str) -> Dict[str, Any]:
    report: Dict[str, Any] = {
        "success": False,
        "skill": "alibabacloud-cloud-native-internet-diagnostics",
        "session_id": _SESSION_ID,
        "product": product,
        "product_name": PRODUCT_NAMES.get(product, product),
        "instance_id": instance_id,
        "region": region,
        "vpc_id": "",
        "vswitch_id": "",
        "egress_check": None,
        "conclusion": "",
        "warnings": [],
    }

    # Step 1: instance lookup
    _log(f"[INFO] querying {PRODUCT_NAMES.get(product, product)} instance "
         f"{instance_id} in region {region}")
    if product == "mse_gateway":
        inst = query_mse_gateway(region, instance_id)
    elif product in ("apig_gateway", "ai_gateway"):
        inst = query_apig_gateway(region, instance_id, product)
    elif product == "sae":
        inst = query_sae(region, instance_id)
    elif product == "fc":
        inst = query_fc(region, instance_id)
    else:
        report["conclusion"] = f"UnsupportedProduct: unsupported product type {product}"
        return report

    if not inst.get("success"):
        err = inst.get("error", "UnknownError")
        if inst.get("auth_error"):
            _log(f"[WARN] authorization error during instance lookup: {err} "
                 "-> degraded, verify RAM permissions "
                 "(see references/ram-policies.md)")
            report["warnings"].append(err)
        else:
            _log(f"[ERROR] instance lookup failed: {err}")
        report["error"] = err
        report["auth_error"] = bool(inst.get("auth_error"))
        report["conclusion"] = f"Instance lookup failed: {err}"
        _build_dual_layer(report)
        return report

    # Merge instance facts
    report["product"] = inst.get("product", product)
    report["product_name"] = PRODUCT_NAMES.get(report["product"], report["product"])
    for key in ("instance_name", "status", "gateway_type", "vpc_id",
                "vswitch_id", "vswitch_ids", "internet_access",
                "has_vpc_config", "fc_quadrant", "diagnosis",
                "need_vswitch_check", "namespace_id"):
        if key in inst:
            report[key] = inst[key]
    _log(f"[INFO] instance resolved: vpc={report.get('vpc_id') or '(none)'}, "
         f"vswitch={report.get('vswitch_id') or '(none)'}")

    # Step 2: decide whether the vSwitch egress check is needed
    if product == "fc":
        if not report.get("need_vswitch_check"):
            # Quadrant A/B/C: the instance query already gives the conclusion
            report["conclusion"] = report.get("diagnosis", "")
            report["success"] = True
            _build_dual_layer(report)
            return report
        _log("[INFO] FC quadrant D: verifying NAT SNAT egress of the vSwitch")
    if not report.get("vswitch_id"):
        report["error"] = (
            "VSwitchNotFound: the instance returned no vSwitch id; "
            "public egress cannot be verified"
        )
        report["conclusion"] = (
            "The instance has no bound vSwitch; public internet egress "
            "cannot be established"
        )
        _build_dual_layer(report)
        return report

    # Step 3: inline vSwitch egress check
    # FC quadrant D: every bound vSwitch is checked; any hit means the
    # function has a fixed public egress. Other products check one vSwitch.
    if product == "fc" and len(report.get("vswitch_ids") or []) > 1:
        vswitch_ids = list(report["vswitch_ids"])
    else:
        vswitch_ids = [report["vswitch_id"]]
    sub_checks = [check_vswitch_egress(region, vs) for vs in vswitch_ids]

    if len(sub_checks) == 1:
        egress = sub_checks[0]
    else:
        hit = next((c for c in sub_checks if c.get("has_public_egress")), None)
        egress = {
            "vswitch_ids_checked": vswitch_ids,
            "vswitches_checked": len(vswitch_ids),
            "vpc_id": next((c.get("vpc_id") for c in sub_checks if c.get("vpc_id")), ""),
            "nat_gateways_checked": sum(c.get("nat_gateways_checked", 0) for c in sub_checks),
            "snat_entries_matched": sum(c.get("snat_entries_matched", 0) for c in sub_checks),
            "has_public_egress": hit is not None,
            "degraded": any(c.get("degraded") for c in sub_checks),
            "warnings": [w for c in sub_checks for w in (c.get("warnings") or [])],
            "conclusion": "",
            "sub_checks": sub_checks,
        }
        if hit is not None:
            egress["conclusion"] = (
                f"Checked {len(vswitch_ids)} bound vSwitches; at least one has "
                f"a NAT SNAT public egress. {hit.get('conclusion', '')}"
            )
        elif egress["degraded"]:
            egress["conclusion"] = (
                f"Checked {len(vswitch_ids)} bound vSwitches; egress check "
                "inconclusive: SNAT table entries could not be fully queried; "
                "rerun after the API error is resolved"
            )
        else:
            egress["conclusion"] = (
                f"Checked {len(vswitch_ids)} bound vSwitches; none of them "
                "has a NAT SNAT public egress"
            )

    report["egress_check"] = egress
    if egress.get("vpc_id") and not report.get("vpc_id"):
        report["vpc_id"] = egress["vpc_id"]
    if egress.get("warnings"):
        report["warnings"].extend(egress["warnings"])

    fc_prefix = ""
    if product == "fc":
        # diagnosis already restates the quadrant; keep the prefix short to
        # avoid duplicating the "Quadrant D: ..." text in the conclusion.
        fc_prefix = "FC quadrant D confirmed. "
    report["conclusion"] = fc_prefix + egress["conclusion"]
    report["success"] = True  # degraded results are still reportable

    _build_dual_layer(report)
    return report


def main():
    parser = argparse.ArgumentParser(
        description="Cloud-native product public internet egress diagnostics "
                    "(read-only, aliyun CLI default credential chain)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Products (--product):
  mse_gateway   Cloud-native gateway (MSE), instance id starts with gw-
  apig_gateway  Cloud-native API gateway, instance id starts with gw-
  ai_gateway    AI gateway, instance id starts with gw-
  sae           Serverless App Engine, application id (UUID)
  fc            Function Compute, function name

Examples:
  python3 cloud_native_internet_diag.py \\
      --product mse_gateway --region cn-hangzhou --instance-id gw-xxxxxxx
  python3 cloud_native_internet_diag.py \\
      --product fc --region cn-hangzhou --instance-id my-function
        """,
    )
    parser.add_argument("--product", required=True,
                        choices=["mse_gateway", "apig_gateway", "ai_gateway",
                                 "sae", "fc"],
                        help="Product type to diagnose")
    parser.add_argument("--region", required=True,
                        help="Region id, e.g. cn-hangzhou")
    parser.add_argument("--instance-id", required=True,
                        help="Instance id / SAE app id / FC function name")
    args = parser.parse_args()

    # Strict input validation (regex + length), no shell interpolation
    if not _REGION_RE.match(args.region):
        _log(f"[ERROR] invalid region id format: {args.region} "
             "(expected e.g. cn-hangzhou)")
        report = {
            "success": False,
            "product": args.product,
            "product_name": PRODUCT_NAMES.get(args.product, args.product),
            "instance_id": args.instance_id,
            "region": args.region,
            "error": f"InvalidParameter: invalid region id format: {args.region}",
            "conclusion": "Parameter validation failed; nothing was queried",
            "summary": (
                "The region id format is invalid, so nothing was queried. "
                "Please provide a region id like cn-hangzhou and rerun."
            ),
            "plain_language_conclusion": "Unable to run: invalid region id format.",
            "recommended_actions": [
                "Use a valid region id such as cn-hangzhou, cn-shanghai, cn-beijing",
            ],
            "warnings": [],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print_human_report(report)
        sys.exit(1)
    if not _INSTANCE_ID_RE.match(args.instance_id):
        _log(f"[ERROR] invalid instance id format: {args.instance_id} "
             "(allowed: letters, digits, dot, underscore, hyphen, max 128 chars)")
        report = {
            "success": False,
            "product": args.product,
            "product_name": PRODUCT_NAMES.get(args.product, args.product),
            "instance_id": args.instance_id,
            "region": args.region,
            "error": f"InvalidParameter: invalid instance id format: {args.instance_id}",
            "conclusion": "Parameter validation failed; nothing was queried",
            "summary": (
                "The instance id format is invalid, so nothing was queried. "
                "Please provide the exact instance id (gateway id / SAE app "
                "id / FC function name) and rerun."
            ),
            "plain_language_conclusion": "Unable to run: invalid instance id format.",
            "recommended_actions": [
                "Double-check the instance id with the customer and rerun",
            ],
            "warnings": [],
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print_human_report(report)
        sys.exit(1)

    report = diagnose(args.product, args.region, args.instance_id)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print_human_report(report)
    sys.exit(0 if report.get("success") else 1)


if __name__ == "__main__":
    main()
