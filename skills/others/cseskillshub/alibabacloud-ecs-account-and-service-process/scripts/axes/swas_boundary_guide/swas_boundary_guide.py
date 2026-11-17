#!/usr/bin/env python3
"""
swas_boundary_guide.py -- Single entry script of the SWAS Boundary Guide skill
==============================================================================
SECURITY: This script is strictly READ-ONLY. Cloud access is limited to the
whitelisted read actions DescribeInstances / DescribeInstanceStatus /
DescribeAvailableResource (ECS) and GetCallerIdentity (STS), enforced at the
code layer by _cli.py. It never creates, modifies, deletes, resets, stops or
releases any resource, never handles AK/SK explicitly (the aliyun CLI default
credential chain resolves authentication), and only inspects the resource the
user specified. Invoke it only after the scope is confirmed per SKILL.md.

Modes (mutually exclusive):
  --identify          Product attribution: is the given instance id / IP a
                      Simple Application Server or an ECS instance? Read-only
                      attribute, status and OS evidence for ECS ids/IPs;
                      id-form attribution plus console guidance for SWAS ids
                      (the ECS OpenAPI surface cannot see SWAS resources).
  --rules             Boundary-rule wording library distilled from real
                      support tickets (--list-rules / --topic <key>).
  --migration-check   Image-migration precondition check (target disk >=
                      source disk, cross-region copy path, SWAS-to-ECS share
                      path) plus optional read-only availability lookup of
                      the target region/instance type.
  --connect-check     OS-to-connection-method matrix (Linux=SSH,
                      Windows=RDP) with reset/replace data-loss warnings.
  --refer             Out-of-scope symptom classification and handoff
                      wording to the neighbouring skill / human channel.

Every run ends with the contract lines:
  STATUS: OK|DEGRADED|FAIL
  NEXT_ACTION: <what the agent must do next>

Usage examples:
  python3 swas_boundary_guide.py --identify --instance-id i-bp12abcd34efgh67ab --region cn-hangzhou
  python3 swas_boundary_guide.py --identify --ip 203.0.113.10 --region cn-hangzhou
  python3 swas_boundary_guide.py --rules --topic migration
  python3 swas_boundary_guide.py --migration-check --source-disk-gb 50 --target-plan 99yuan-ecs-economy-e --target-region cn-hangzhou
  python3 swas_boundary_guide.py --connect-check --os-type linux --attempted rdp
  python3 swas_boundary_guide.py --refer --symptom "disk io stays at 100 percent"
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any, Optional

import _cli
from _constants import (
    BOUNDARY_TOPICS,
    CONNECTION_MATRIX,
    DEFAULT_REGION,
    DOC_LINKS,
    ECS_ID_PREFIX,
    HANDOFF_ROUTES,
    KNOWN_PLANS,
    MIGRATION_FACTS,
    NEXT_ACTION_BY_STATUS,
    PAGE_SIZE,
    SKILL_NAME,
    SWAS_ID_HEX_LENGTH,
)

# ---------------------------------------------------------------------------
# Input validation patterns (strict; values are passed as subprocess argument
# list elements only, never through a shell)
# ---------------------------------------------------------------------------

_ECS_ID_RE = re.compile(r"^i-[a-z0-9]{6,64}$")
_SWAS_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_REGION_RE = re.compile(r"^[a-z]{2}-[a-z]+(-[a-z0-9]+)*$")
_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")
_INSTANCE_TYPE_RE = re.compile(r"^[A-Za-z0-9.\-]{2,64}$")

VALID_OS_TYPES = ("linux", "windows")
VALID_PRODUCTS = ("swas", "ecs")


def _warn(msg: str) -> None:
    print(f"[WARN] {msg}", file=sys.stderr)


def _die_usage(parser: argparse.ArgumentParser, msg: str) -> None:
    parser.error(msg)  # exits 2


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------

def _dig(obj: Any, *keys: str, default: Any = None) -> Any:
    """Walk a nested dict safely; return default on any miss."""
    node = obj
    for key in keys:
        if not isinstance(node, dict):
            return default
        node = node.get(key)
        if node is None:
            return default
    return node


def _doc_urls(keys: list) -> list:
    """Resolve DOC_LINKS keys to URLs; unknown keys are skipped (never
    invent a URL)."""
    urls = []
    for key in keys or []:
        url = DOC_LINKS.get(key)
        if url:
            urls.append(url)
        else:
            _warn(f"doc link key '{key}' is not in the verified link set; "
                  f"skipped (no URL fabricated)")
    return urls


def classify_instance_id(raw: str) -> str:
    """Return 'ecs' | 'swas' | 'unknown' for an instance-id string."""
    iid = raw.strip().lower()
    if _ECS_ID_RE.match(iid):
        return "ecs"
    if _SWAS_ID_RE.match(iid):
        return "swas"
    return "unknown"


def _validate_region(parser, region: str) -> str:
    if not _REGION_RE.match(region):
        _die_usage(parser, f"invalid region id '{region}' "
                           f"(expected form like cn-hangzhou / ap-southeast-1)")
    return region


def _validate_ip(parser, ip: str) -> str:
    m = _IPV4_RE.match(ip)
    if not m or any(int(g) > 255 for g in m.groups()):
        _die_usage(parser, f"invalid IPv4 address '{ip}'")
    return ip


def _base_result(mode: str) -> dict:
    return {
        "skill": SKILL_NAME,
        "mode": mode,
        "status": "OK",
        "summary": "",
        "key_findings": [],
        "suggestions": [],
        "auto_filled": [],
        "errors": [],
        "degraded_checks": [],
        "report_lines": [],
        "next_action": "",
    }


# ---------------------------------------------------------------------------
# ECS read-only queries (all through the shared, whitelisted CLI layer)
# ---------------------------------------------------------------------------

def _query_instances_by_params(region: str, params: dict,
                               profile: Optional[str],
                               errors: list) -> Optional[list]:
    """One DescribeInstances call. Returns the instance list (possibly empty)
    on success, or None when the call failed (error recorded in `errors`)."""
    full_params = {"RegionId": region, "PageSize": PAGE_SIZE}
    full_params.update(params)
    try:
        body = _cli.call("ecs", "DescribeInstances", full_params,
                         region=region, profile=profile)
        instances = _dig(body, "Instances", "Instance", default=[])
        return instances if isinstance(instances, list) else []
    except _cli.CliError as e:
        if _cli.is_permission_error(e):
            errors.append(_cli.permission_hint("ecs", "DescribeInstances"))
        else:
            errors.append(f"DescribeInstances failed: "
                          f"{getattr(e, 'code', '') or 'Unknown'}: {e}")
        _warn(f"ecs DescribeInstances: {e}")
        return None


def _query_instance_status(region: str, instance_id: str,
                           profile: Optional[str], errors: list) -> str:
    """Read-only status cross-check; returns the status string or 'N/A'."""
    try:
        body = _cli.call("ecs", "DescribeInstanceStatus",
                         {"RegionId": region, "InstanceId.1": instance_id},
                         region=region, profile=profile)
        rows = _dig(body, "InstanceStatuses", "InstanceStatus", default=[])
        if isinstance(rows, list) and rows:
            return str(rows[0].get("Status") or "N/A")
        return "N/A"
    except _cli.CliError as e:
        if _cli.is_permission_error(e):
            errors.append(_cli.permission_hint("ecs", "DescribeInstanceStatus"))
        else:
            errors.append(f"DescribeInstanceStatus failed: "
                          f"{getattr(e, 'code', '') or 'Unknown'}: {e}")
        _warn(f"ecs DescribeInstanceStatus: {e}")
        return "N/A"


def _instance_facts(inst: dict, status_override: str = "") -> dict:
    """Extract the attribution-relevant fields from one DescribeInstances
    row. Missing fields become 'N/A' -- never guessed."""
    memory_mib = inst.get("Memory")
    memory_gib = (f"{int(memory_mib) / 1024:g} GiB"
                  if isinstance(memory_mib, (int, float)) and memory_mib
                  else "N/A")
    public_ips = _dig(inst, "PublicIpAddress", "IpAddress", default=[]) or []
    eip = _dig(inst, "EipAddress", "IpAddress", default="") or ""
    private_ips = (_dig(inst, "VpcAttributes", "PrivateIpAddress", "IpAddress",
                        default=[]) or [])
    return {
        "instance_id": str(inst.get("InstanceId") or "N/A"),
        "instance_name": str(inst.get("InstanceName") or "N/A"),
        "status": status_override or str(inst.get("Status") or "N/A"),
        "region_id": str(inst.get("RegionId") or "N/A"),
        "zone_id": str(inst.get("ZoneId") or "N/A"),
        "instance_type": str(inst.get("InstanceType") or "N/A"),
        "instance_type_family": str(inst.get("InstanceTypeFamily") or "N/A"),
        "cpu": inst.get("Cpu", "N/A"),
        "memory": memory_gib,
        "os_name": str(inst.get("OSName") or "N/A"),
        "os_type": str(inst.get("OSType") or "N/A"),
        "image_id": str(inst.get("ImageId") or "N/A"),
        "charge_type": str(inst.get("InstanceChargeType") or "N/A"),
        "internet_charge_type": str(inst.get("InternetChargeType") or "N/A"),
        "creation_time": str(inst.get("CreationTime") or "N/A"),
        "expired_time": str(inst.get("ExpiredTime") or "N/A"),
        "public_ip": (public_ips[0] if public_ips else (eip or "N/A")),
        "eip": eip or "N/A",
        "private_ip": (private_ips[0] if private_ips else "N/A"),
        "security_group_ids": _dig(inst, "SecurityGroupIds", "SecurityGroupId",
                                   default=[]) or [],
    }


# ---------------------------------------------------------------------------
# Mode: identify
# ---------------------------------------------------------------------------

def mode_identify(args, parser) -> dict:
    result = _base_result("identify")

    if not args.instance_id and not args.ip:
        result["status"] = "FAIL"
        result["summary"] = ("No lookup target: provide --instance-id or "
                             "--ip for product attribution.")
        result["next_action"] = ("Ask the customer for the instance id "
                                 "(ECS ids start with 'i-', Simple "
                                 "Application Server ids are 32-character "
                                 "hex strings) or the public IP, plus the "
                                 "region; or guide them to the console "
                                 "server list to copy it.")
        return result

    region = args.region
    if not region:
        region = DEFAULT_REGION
        result["auto_filled"].append(
            f"region auto-filled to the default '{DEFAULT_REGION}' (the "
            f"customer did not specify one)")
    _validate_region(parser, region)

    _cli.check_cli_available()
    uid = _cli.resolve_account_id(region=region, profile=args.profile)
    if uid:
        result["auto_filled"].append(
            f"account UID derived via sts get-caller-identity: {uid} "
            f"(used only as a traceability label)")
    else:
        result["degraded_checks"].append(
            "sts get-caller-identity failed; the UID traceability label is "
            "unavailable. Verify the credential chain with `aliyun "
            "configure` if queries below also fail.")
        _warn("sts get-caller-identity failed; continuing without UID label")

    # ---- Branch 1: SWAS-form instance id (no ECS API can see it) ---------
    if args.instance_id:
        iid = args.instance_id.strip().lower()
        form = classify_instance_id(iid)
        if form == "swas":
            result["status"] = "DEGRADED"
            result["attribution"] = {
                "product": "Simple Application Server (SWAS)",
                "method": "id-form recognition (32-character hex string)",
                "instance_id": iid,
                "api_visible": False,
            }
            result["summary"] = (
                f"The id '{iid}' matches the Simple Application Server "
                f"id form (a {SWAS_ID_HEX_LENGTH}-character hex string), so "
                f"the resource is attributed to SWAS, not ECS. The "
                f"whitelisted ECS read APIs cannot query SWAS resources "
                f"(real tickets confirm 'no SWAS resource visible under ECS "
                f"queries'), so attribution here is by id form and details "
                f"degrade to console self-service.")
            result["key_findings"] = [
                f"Attribution: Simple Application Server (id form: "
                f"{SWAS_ID_HEX_LENGTH}-char hex; ECS ids start with "
                f"'{ECS_ID_PREFIX}').",
                "SWAS plan details (CPU/memory/disk/bandwidth), region and "
                "expiry are read in the Simple Application Server console "
                "-> Servers -> overview; this read-only skill has no "
                "verified SWAS-side API and does not fabricate one.",
                "SWAS and ECS are two different products with separate "
                "console inventories; one account can hold both.",
            ]
            result["suggestions"] = [
                "For product/spec questions run: python3 "
                "scripts/swas_boundary_guide.py --rules --topic "
                "product-identity (or spec-terminology).",
                "For migration/region questions run: python3 "
                "scripts/swas_boundary_guide.py --migration-check "
                "--source-product swas --source-disk-gb <from console> "
                "--target-region <region>.",
                "For connection problems run: python3 "
                "scripts/swas_boundary_guide.py --connect-check --os-type "
                "<linux|windows from the console overview>.",
            ]
            result["report_lines"] = [
                "Attribution: Simple Application Server (by id form).",
                "Console path: Alibaba Cloud console -> Simple Application "
                "Server -> Servers (plan, region, image/OS, expiry).",
                "Note: ECS OpenAPI queries do not return SWAS resources; no "
                "SWAS-side read action is verified for this skill, so no "
                "API evidence is claimed.",
            ]
            result["next_action"] = (
                "Present the SWAS attribution and console guidance; answer "
                "the underlying question with --rules / --migration-check / "
                "--connect-check. Never claim API-verified attributes for a "
                "SWAS id.")
            return result
        if form == "unknown":
            result["status"] = "FAIL"
            result["summary"] = (
                f"The id '{args.instance_id}' matches neither the ECS form "
                f"(starts with '{ECS_ID_PREFIX}') nor the Simple Application "
                f"Server form ({SWAS_ID_HEX_LENGTH}-character hex string).")
            result["next_action"] = (
                "Ask the customer to copy the exact instance id from the "
                "console (ECS console -> Instances, or Simple Application "
                "Server console -> Servers), or provide the public IP "
                "instead (--ip).")
            return result

    # ---- Branch 2: ECS-form id and/or IP -> read-only ECS queries --------
    found = []
    matched_by = ""
    api_ok = 0

    if args.instance_id:  # form == "ecs" here
        iid = args.instance_id.strip().lower()
        rows = _query_instances_by_params(
            region, {"InstanceIds": json.dumps([iid])}, args.profile,
            result["errors"])
        if rows is not None:
            api_ok += 1
            if rows:
                found = rows
                matched_by = f"InstanceIds=[{iid}]"

    if not found and args.ip:
        ip = _validate_ip(parser, args.ip.strip())
        for flag in ("PublicIpAddresses", "EipAddresses",
                     "PrivateIpAddresses", "InnerIpAddresses"):
            rows = _query_instances_by_params(
                region, {flag: json.dumps([ip])}, args.profile,
                result["errors"])
            if rows is not None:
                api_ok += 1
                if rows:
                    found = rows
                    matched_by = f"{flag}=[{ip}]"
                    break

    if not found:
        result["status"] = "DEGRADED" if api_ok else "FAIL"
        result["summary"] = (
            f"No instance matched under account UID "
            f"{uid or 'N/A'} in region '{region}'."
            if api_ok else
            f"All read-only lookups failed in region '{region}'; no "
            f"attribution evidence could be collected.")
        if api_ok:
            result["key_findings"] = [
                "An empty result is a valid finding, not an API error: "
                "nothing matches this credential in this region.",
                "Possible reasons: (1) the resource lives in another region "
                "-- re-run with the correct --region; (2) the credential "
                "belongs to a different account than the resource; (3) the "
                "instance was released or expired; (4) the id/IP belongs to "
                "a Simple Application Server, which the ECS OpenAPI surface "
                "cannot see.",
            ]
            result["suggestions"] = [
                "Confirm the region and account in the console (Simple "
                "Application Server console -> Servers, or ECS console -> "
                "Instances) and re-run with --region <region>.",
                "If the id is a 32-character hex string, treat it as a "
                "Simple Application Server id (see --rules --topic "
                "product-identity).",
            ]
        result["next_action"] = (
            "Ask the customer for the correct region/account or the exact "
            "instance id; if all calls failed with NoPermission / "
            "ImplicitDeny, point to references/ram-policies.md for the "
            "minimal read-only policy.")
        return result

    # ---- Attribution succeeded: report the ECS evidence -------------------
    facts_list = []
    for inst in found[:5]:
        iid = str(inst.get("InstanceId") or "")
        status_x = _query_instance_status(region, iid, args.profile,
                                          result["errors"]) if iid else "N/A"
        facts_list.append(_instance_facts(inst, status_x))

    first = facts_list[0]
    result["attribution"] = {
        "product": "ECS (Elastic Compute Service)",
        "method": f"read-only DescribeInstances match via {matched_by}",
        "matched_count": len(facts_list),
        "instances": facts_list,
    }
    result["summary"] = (
        f"Attribution complete: {len(facts_list)} instance(s) matched under "
        f"account UID {uid or 'N/A'} in region '{region}' via "
        f"{matched_by}. The resource is an ECS instance, NOT a Simple "
        f"Application Server -- the two are different products.")
    for facts in facts_list:
        result["key_findings"].append(
            f"{facts['instance_id']}: status={facts['status']}, "
            f"type={facts['instance_type']} "
            f"(family {facts['instance_type_family']}), "
            f"cpu={facts['cpu']}, memory={facts['memory']}, "
            f"os={facts['os_name']} ({facts['os_type']}), "
            f"public_ip={facts['public_ip']}, "
            f"charge={facts['charge_type']}, "
            f"expires={facts['expired_time']}")
        ostype = str(facts["os_type"]).lower()
        if ostype in CONNECTION_MATRIX:
            entry = CONNECTION_MATRIX[ostype]
            result["key_findings"].append(
                f"Connection method for {ostype}: {entry['method']}. "
                f"{entry['notes']}")
    result["suggestions"] = [
        "If the customer believed this was a Simple Application Server, "
        "explain the product difference: run --rules --topic "
        "product-identity and cite the doc links it prints.",
        "For connection questions run --connect-check --os-type "
        f"{str(first['os_type']).lower() or '<linux|windows>'}.",
        "For migration questions run --migration-check with the source disk "
        "size read from the console (DescribeInstances does not return disk "
        "sizes and no disk API is whitelisted here).",
    ]
    result["report_lines"] = [
        f"Attribution: ECS instance (matched via {matched_by}).",
        f"Region auto-filled/used: {region}. Account UID: {uid or 'N/A'}.",
    ]
    if any(str(e).startswith("DescribeInstanceStatus failed")
           for e in result["errors"]):
        result["status"] = "DEGRADED"
    if result["errors"] and any("DescribeInstances failed" in str(e)
                                for e in result["errors"]):
        result["status"] = "DEGRADED"
    result["next_action"] = (
        "Present the attribution table and the OS-matched connection method; "
        "route the underlying question to --rules / --migration-check / "
        "--connect-check / --refer. Read-only skill: every recommendation is "
        "manual guidance.")
    return result


# ---------------------------------------------------------------------------
# Mode: rules (embedded knowledge, no API calls)
# ---------------------------------------------------------------------------

def mode_rules(args, parser) -> dict:
    result = _base_result("rules")
    if args.list_rules or not args.topic:
        result["summary"] = (
            f"{len(BOUNDARY_TOPICS)} boundary-rule topics are available.")
        for key, topic in BOUNDARY_TOPICS.items():
            result["report_lines"].append(
                f"{key}: {topic['title']} ({len(topic['rules'])} rules)")
        result["next_action"] = (
            "Pick the topic matching the customer's question and re-run with "
            "--topic <key>; relay the rule wording and its doc links "
            "verbatim.")
        return result

    topic = BOUNDARY_TOPICS.get(args.topic)
    if topic is None:
        result["status"] = "FAIL"
        result["summary"] = (f"Unknown rule topic '{args.topic}'. Valid "
                             f"topics: {', '.join(BOUNDARY_TOPICS)}.")
        result["next_action"] = "Re-run with a valid --topic key."
        return result

    result["topic"] = args.topic
    result["title"] = topic["title"]
    rules_out = []
    for rule in topic["rules"]:
        entry = {
            "text": rule["text"],
            "evidence": rule.get("evidence", []),
            "docs": _doc_urls(rule.get("docs", [])),
        }
        if rule.get("evidence_quality") == "summary":
            entry["evidence_note"] = (
                "Derived from a support-ticket summary whose full dialogue "
                "was not re-verified; present it as ticket wording, not as "
                "an official policy quote.")
        rules_out.append(entry)
        line = f"- {rule['text']}"
        if entry["docs"]:
            line += " Docs: " + " ; ".join(entry["docs"])
        if "evidence_note" in entry:
            line += " [evidence: ticket summary, not fully re-verified]"
        result["report_lines"].append(line)
    result["rules"] = rules_out
    result["summary"] = (
        f"Boundary rules for topic '{args.topic}' ({topic['title']}): "
        f"{len(rules_out)} rules loaded from the embedded, ticket-sourced "
        f"knowledge base. No cloud API was called.")
    result["next_action"] = (
        "Relay the matching rule(s) and their doc links to the customer "
        "verbatim; never invent URLs beyond the printed ones. Combine with "
        "--identify when the question concerns a specific resource.")
    return result


# ---------------------------------------------------------------------------
# Mode: migration-check
# ---------------------------------------------------------------------------

def mode_migration_check(args, parser) -> dict:
    result = _base_result("migration-check")

    source_product = args.source_product
    target_product = args.target_product
    source_region = args.source_region
    target_region = args.target_region
    if source_region:
        _validate_region(parser, source_region)
    if target_region:
        _validate_region(parser, target_region)
    if args.target_instance_type and not _INSTANCE_TYPE_RE.match(
            args.target_instance_type):
        _die_usage(parser, f"invalid --target-instance-type "
                           f"'{args.target_instance_type}'")

    plan = None
    if args.target_plan:
        plan = KNOWN_PLANS.get(args.target_plan)
        if plan is None:
            _die_usage(parser, f"unknown --target-plan '{args.target_plan}'; "
                               f"known plans: {', '.join(KNOWN_PLANS)}")

    target_gb = args.target_disk_gb
    if target_gb is None and plan:
        target_gb = float(plan["system_disk_gb"])
        result["auto_filled"].append(
            f"target system disk auto-filled from the known plan "
            f"'{args.target_plan}': {target_gb:g} GiB")

    lines = []
    verdict = "FEASIBLE_WITH_CONDITIONS"

    # 1) Capacity precondition (target disk >= source disk)
    if args.source_disk_gb is not None and target_gb is not None:
        if target_gb >= args.source_disk_gb:
            lines.append(
                f"Capacity precondition PASSED: target system disk "
                f"{target_gb:g} GiB >= source system disk "
                f"{args.source_disk_gb:g} GiB.")
        else:
            verdict = "BLOCKED"
            lines.append(
                f"Capacity precondition FAILED: target system disk "
                f"{target_gb:g} GiB < source system disk "
                f"{args.source_disk_gb:g} GiB. Image-based migration is "
                f"blocked; choose a larger target plan/disk or migrate "
                f"manually.")
    else:
        result["status"] = "DEGRADED"
        result["degraded_checks"].append(
            "Capacity comparison skipped: --source-disk-gb and/or "
            "--target-disk-gb (or --target-plan) not supplied. The source "
            "system disk size is read in the console (SWAS: server "
            "overview; ECS: disk list) -- DescribeInstances does not return "
            "disk sizes and no disk API is whitelisted for this skill.")
        lines.append(
            "Capacity precondition NOT CHECKED (disk sizes missing). "
            "Remember: image migration requires target system disk >= "
            "source system disk.")

    if plan:
        lines.append(f"Target plan '{plan['label']}': {plan['vcpu']} vCPU / "
                     f"{plan['memory_gib']} GiB memory / "
                     f"{plan['bandwidth_mbps']} Mbps / "
                     f"{plan['system_disk_gb']} GiB {plan['disk_category']} "
                     f"system disk. Conditions: {plan['conditions']}.")

    # 2) Path selection
    cross_region = bool(source_region and target_region
                        and source_region != target_region)
    if source_product == "swas" and target_product == "ecs":
        lines.append("Path: Simple Application Server -> ECS. There is no "
                     "seamless conversion; the supported channel is the "
                     "custom image:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(
            MIGRATION_FACTS["swas_to_ecs_steps"], start=1))
    elif cross_region and source_product == target_product:
        lines.append(f"Path: cross-region move ({source_region} -> "
                     f"{target_region}). The region of an existing instance "
                     f"cannot be changed; use the image-copy path:")
        lines.extend(f"  {i}. {s}" for i, s in enumerate(
            MIGRATION_FACTS["cross_region_steps"], start=1))
    elif source_product == target_product and not cross_region:
        lines.append(
            "Path: same product, same region -- there is nothing to migrate. "
            "The product type of an instance cannot be changed, and this "
            "skill does not modify plans; for plan/pricing changes see the "
            "console purchase page or the commercial channel.")
    else:
        lines.append(
            "Path: generic migration -- see the official migration guide "
            "printed below and verify the capacity precondition first.")

    # 3) Standing warnings (ticket-verified wording)
    lines.append("Warnings (always state these):")
    lines.append(f"  - {MIGRATION_FACTS['price_difference']}")
    lines.append(f"  - {MIGRATION_FACTS['promo_renewal']}")
    lines.append(f"  - {MIGRATION_FACTS['manual_fallback']}")
    if target_region and target_region.startswith("cn-") and (
            not source_region or not source_region.startswith("cn-")):
        lines.append(f"  - {MIGRATION_FACTS['icp_note']}")
    lines.append("Docs: " + " ; ".join(
        _doc_urls(["MIGRATE_SERVERS", "SHARED_INSTANCE_FAMILIES", "ACT99"])))

    # 4) Optional read-only availability lookup for the target region
    if target_region:
        avail = _check_available_resource(
            target_region, args.target_instance_type,
            args.instance_charge_type, args.profile, result)
        lines.append(avail)

    result["migration"] = {
        "verdict": verdict,
        "source_product": source_product,
        "target_product": target_product,
        "source_region": source_region or "N/A",
        "target_region": target_region or "N/A",
        "source_disk_gb": args.source_disk_gb,
        "target_disk_gb": target_gb,
        "target_plan": args.target_plan,
    }
    result["report_lines"] = lines
    result["summary"] = (
        f"Migration precondition check {verdict}: {source_product}"
        f"{(' (' + source_region + ')') if source_region else ''} -> "
        f"{target_product}{(' (' + target_region + ')') if target_region else ''}, "
        f"source disk {args.source_disk_gb if args.source_disk_gb is not None else 'N/A'} GiB, "
        f"target disk {target_gb if target_gb is not None else 'N/A'} GiB.")
    result["suggestions"] = [
        "Relay the verdict, the step list and every warning to the customer; "
        "the migration itself is executed manually by the customer in the "
        "console -- this skill never performs it.",
        "If BLOCKED, present the manual-migration fallback and, when the "
        "target is a promotional plan, the promo-renewal warning.",
    ]
    result["next_action"] = (
        "Present the migration checklist with preconditions, steps, warnings "
        "and doc links. Never execute any migration, purchase or image "
        "operation.")
    return result


def _check_available_resource(target_region: str,
                              instance_type: Optional[str],
                              charge_type: str,
                              profile: Optional[str],
                              result: dict) -> str:
    """Read-only DescribeAvailableResource lookup for the target region."""
    params = {
        "RegionId": target_region,
        "DestinationResource": "InstanceType",
        "InstanceChargeType": charge_type,
    }
    if instance_type:
        params["InstanceType"] = instance_type
    try:
        body = _cli.call("ecs", "DescribeAvailableResource", params,
                         region=target_region, profile=profile)
    except _cli.CliError as e:
        if _cli.is_permission_error(e):
            result["errors"].append(
                _cli.permission_hint("ecs", "DescribeAvailableResource"))
        else:
            result["errors"].append(
                f"DescribeAvailableResource failed: "
                f"{getattr(e, 'code', '') or 'Unknown'}: {e}")
        _warn(f"ecs DescribeAvailableResource: {e}")
        result["status"] = "DEGRADED"
        result["degraded_checks"].append(
            f"Availability lookup failed for {target_region}; the customer "
            f"can check purchasable plans on the console buy page instead.")
        return (f"Availability in {target_region}: NOT VERIFIED (API call "
                f"failed, recorded as degraded).")

    zones = _dig(body, "AvailableZones", "AvailableZone", default=[]) or []
    if not zones:
        return (f"Availability in {target_region}: the API returned no "
                f"available-zone entries for the requested filters "
                f"(charge type {charge_type}"
                f"{', instance type ' + instance_type if instance_type else ''}"
                f"); treat the target as not purchasable with these filters "
                f"and re-check on the console buy page.")
    if instance_type:
        in_stock = []
        for zone in zones:
            resources = _dig(zone, "AvailableResources", "AvailableResource",
                             default=[]) or []
            for res in resources:
                supported = _dig(res, "SupportedResources",
                                 "SupportedResource", default=[]) or []
                for item in supported:
                    if str(item.get("Value") or "") == instance_type and \
                            str(item.get("StatusCategory") or "") == \
                            "WithStock":
                        in_stock.append(str(zone.get("ZoneId") or "N/A"))
        if in_stock:
            return (f"Availability in {target_region}: {instance_type} is "
                    f"purchasable (WithStock) in zone(s): "
                    f"{', '.join(in_stock)}.")
        return (f"Availability in {target_region}: {instance_type} has NO "
                f"WithStock zone under charge type {charge_type}; pick "
                f"another instance type/zone or charge type on the console "
                f"buy page.")
    zone_summary = ", ".join(
        f"{z.get('ZoneId', 'N/A')}({z.get('StatusCategory', 'N/A')})"
        for z in zones[:10])
    return (f"Availability in {target_region}: {len(zones)} zone(s) "
            f"reported for InstanceType resources: {zone_summary}. Pass "
            f"--target-instance-type for a stock verdict on one type.")


# ---------------------------------------------------------------------------
# Mode: connect-check (pure knowledge)
# ---------------------------------------------------------------------------

def mode_connect_check(args, parser) -> dict:
    result = _base_result("connect-check")
    os_type = args.os_type.lower()
    if os_type not in VALID_OS_TYPES:
        _die_usage(parser, f"--os-type must be one of {VALID_OS_TYPES}")
    entry = CONNECTION_MATRIX[os_type]
    lines = [
        f"OS type: {os_type}",
        f"Correct connection method: {entry['method']}",
        f"Note: {entry['notes']}",
    ]
    mismatch = ""
    if args.attempted:
        attempted = args.attempted.lower()
        if attempted == "rdp" and os_type == "linux":
            mismatch = (
                "MISMATCH: Remote Desktop (RDP/mstsc) cannot work against a "
                "Linux image -- this is expected product behavior, not a "
                "fault. Use SSH/Workbench, or switch the server to a "
                "Windows image first (data-erasing; see warnings below).")
        elif attempted == "ssh" and os_type == "windows":
            mismatch = (
                "MISMATCH: a Windows image does not serve plain SSH by "
                "default. Use Remote Desktop (RDP) or the console "
                "Workbench/VNC instead.")
        else:
            mismatch = (f"The attempted method '{args.attempted}' matches "
                        f"this OS type; if it still fails, check the "
                        f"firewall/security rules for the port and the "
                        f"local network, then escalate with evidence.")
        lines.append(mismatch)
    lines.append("Mandatory warnings when switching OS (state all three):")
    lines.append("  - Resetting a SWAS system or replacing an ECS OS erases "
                 "ALL data on the system disk; back up first.")
    lines.append("  - The public IP address does not change.")
    lines.append("  - A fresh Windows image can take 5-10 minutes on first "
                 "boot before RDP accepts connections (ticket wording).")
    lines.append("Console entries differ by product: SWAS uses 'Reset "
                 "System'; ECS uses 'Replace Operating System'.")
    lines.append("Docs: " + " ; ".join(
        _doc_urls(["RESET_SWAS", "REPLACE_ECS_OS"])))
    result["connect"] = {
        "os_type": os_type,
        "method": entry["method"],
        "attempted": args.attempted or "N/A",
        "mismatch": mismatch or "N/A",
    }
    result["report_lines"] = lines
    result["summary"] = (
        f"Connection-method check for a {os_type} server: use "
        f"{entry['method']}."
        + (f" Attempted method verdict: {mismatch}" if mismatch else ""))
    result["suggestions"] = [
        "Tell the customer the correct connection method for their OS "
        "before any troubleshooting; most 'cannot connect' tickets in this "
        "tier are method/OS mismatches.",
        "If a Windows desktop is required on a Linux server, present the "
        "reset/replace guidance WITH the data-loss warning; the operation "
        "itself is performed by the customer in the console, never by this "
        "skill.",
    ]
    result["next_action"] = (
        "Present the connection matrix, the mismatch verdict (if any) and "
        "the three mandatory warnings with the two doc links.")
    return result


# ---------------------------------------------------------------------------
# Mode: refer (out-of-scope classification, pure function)
# ---------------------------------------------------------------------------

def mode_refer(args, parser) -> dict:
    result = _base_result("refer")
    symptom = args.symptom.strip()
    if not symptom or len(symptom) > 500:
        _die_usage(parser, "--symptom must be 1-500 characters")
    lowered = symptom.lower()
    matches = []
    for route_id, route in HANDOFF_ROUTES.items():
        hit = [kw for kw in route["keywords"] if kw in lowered]
        if hit:
            matches.append((route_id, route, hit))

    lines = [f"Symptom (verbatim): {symptom}"]
    if matches:
        for route_id, route, hit in matches:
            lines.append(
                f"- Route '{route_id}' matched on {hit}: hand off to "
                f"{route['target']}. {route['note']}")
        result["summary"] = (
            f"Symptom classified as out of scope; matched route(s): "
            f"{', '.join(m[0] for m in matches)}. This skill only identifies "
            f"and hands off -- it never diagnoses in-guest faults itself.")
        result["referrals"] = [
            {"route": m[0], "target": m[1]["target"], "note": m[1]["note"],
             "matched_keywords": m[2]} for m in matches]
    else:
        lines.append(
            "- No out-of-scope route matched. First establish attribution "
            "with --identify; if the problem is inside the guest OS and "
            "persists, guide the customer to submit a support ticket with "
            "the collected evidence.")
        result["summary"] = (
            "No referral route matched the symptom wording; default to "
            "attribution first (--identify), then a support ticket with "
            "evidence if it is an in-guest fault.")
    lines.append("Handoff context checklist (attach to every referral):")
    lines.append("  product attribution (SWAS or ECS) + instance id + region "
                 "+ OS type + status, all from --identify output;")
    lines.append("  what was already checked here (API readings, rule "
                 "wording given, probe guidance);")
    lines.append("  for evidence requests (e.g. security detections), cite "
                 "the detection source -- never assert an unfounded cause.")
    result["report_lines"] = lines
    result["suggestions"] = [
        "Output: attribution result + one-sentence symptom classification + "
        "the handoff target. Do not expand into in-guest diagnosis.",
        "Commercial asks (refund, eligibility restore, release on the "
        "customer's behalf) are NEVER executed; quote the rule wording via "
        "--rules --topic commerce and escalate to the human channel.",
    ]
    result["next_action"] = (
        "Present the handoff wording with the context checklist; if the "
        "matched target is another skill, say so explicitly so the agent "
        "can route the conversation.")
    return result


# ---------------------------------------------------------------------------
# Rendering & contract
# ---------------------------------------------------------------------------

def render(result: dict, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, indent=2))
        return
    print("=" * 72)
    print(f"{SKILL_NAME} -- mode: {result['mode']}")
    print("=" * 72)
    print("\nSummary")
    print("-------")
    print(result["summary"] or "N/A")
    if result.get("report_lines"):
        print("\nDetails")
        print("-------")
        for line in result["report_lines"]:
            print(line)
    if result.get("key_findings"):
        print("\nKey findings")
        print("------------")
        for line in result["key_findings"]:
            print(f"- {line}")
    if result.get("suggestions"):
        print("\nSuggestions (manual guidance only -- read-only skill)")
        print("----------------------------------------------------")
        for line in result["suggestions"]:
            print(f"- {line}")
    if result.get("auto_filled"):
        print("\nAuto-filled parameters (declared per contract)")
        print("----------------------------------------------")
        for line in result["auto_filled"]:
            print(f"- {line}")
    if result.get("degraded_checks"):
        print("\nGraceful degradation log")
        print("------------------------")
        for line in result["degraded_checks"]:
            print(f"- [WARN|DEGRADE] {line}")
    if result.get("errors"):
        print("\nErrors")
        print("------")
        for line in result["errors"]:
            print(f"- {line}")


def finish(result: dict) -> int:
    status = result.get("status", "OK")
    next_action = result.get("next_action") or NEXT_ACTION_BY_STATUS.get(
        status, NEXT_ACTION_BY_STATUS["OK"])
    result["next_action"] = next_action
    print(f"\nSTATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")
    return 0 if status in ("OK", "DEGRADED") else 1


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swas_boundary_guide.py",
        description=("Read-only Simple Application Server (SWAS) boundary "
                     "guide: product attribution, boundary-rule wording, "
                     "migration preconditions, connection-method matching "
                     "and out-of-scope handoff. Never mutates anything."),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--identify", action="store_true",
                      help="Product attribution for an instance id / IP "
                           "(default mode)")
    mode.add_argument("--rules", action="store_true",
                      help="Print boundary-rule wording from the embedded "
                           "knowledge base")
    mode.add_argument("--migration-check", action="store_true",
                      help="Image-migration precondition check")
    mode.add_argument("--connect-check", action="store_true",
                      help="OS-to-connection-method matching")
    mode.add_argument("--refer", action="store_true",
                      help="Out-of-scope symptom classification + handoff")

    parser.add_argument("--instance-id", default=None,
                        help="Instance id (ECS 'i-...' or SWAS 32-hex)")
    parser.add_argument("--ip", default=None, help="IPv4 address to look up")
    parser.add_argument("--region", default=None,
                        help=f"Region id (default: {DEFAULT_REGION}, "
                             f"auto-filled and declared)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")

    parser.add_argument("--list-rules", action="store_true",
                        help="With --rules: list available topics")
    parser.add_argument("--topic", default=None,
                        help="With --rules: topic key to print")

    parser.add_argument("--source-product", default="swas",
                        choices=VALID_PRODUCTS,
                        help="Migration source product (default: swas)")
    parser.add_argument("--target-product", default="ecs",
                        choices=VALID_PRODUCTS,
                        help="Migration target product (default: ecs)")
    parser.add_argument("--source-disk-gb", type=float, default=None,
                        help="Source system disk size in GiB (from console)")
    parser.add_argument("--target-disk-gb", type=float, default=None,
                        help="Target system disk size in GiB")
    parser.add_argument("--target-plan", default=None,
                        help=f"Known target plan key: "
                             f"{', '.join(KNOWN_PLANS)}")
    parser.add_argument("--source-region", default=None,
                        help="Source region id (for cross-region checks)")
    parser.add_argument("--target-region", default=None,
                        help="Target region id (enables the read-only "
                             f"availability lookup)")
    parser.add_argument("--target-instance-type", default=None,
                        help="Target ECS instance type for the stock check")
    parser.add_argument("--instance-charge-type", default="PrePaid",
                        choices=("PrePaid", "PostPaid"),
                        help="Charge type for the availability lookup "
                             "(default: PrePaid)")

    parser.add_argument("--os-type", default=None,
                        help="With --connect-check: linux | windows")
    parser.add_argument("--attempted", default=None,
                        help="With --connect-check: method the customer "
                             "already tried (rdp | ssh | workbench)")

    parser.add_argument("--symptom", default=None,
                        help="With --refer: customer symptom wording")

    parser.add_argument("--json", action="store_true",
                        help="Emit structured JSON instead of the readable "
                             "report")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.rules:
        result = mode_rules(args, parser)
    elif args.migration_check:
        result = mode_migration_check(args, parser)
    elif args.connect_check:
        if not args.os_type:
            _die_usage(parser, "--connect-check requires --os-type "
                               "<linux|windows>")
        result = mode_connect_check(args, parser)
    elif args.refer:
        if not args.symptom:
            _die_usage(parser, "--refer requires --symptom \"<customer "
                               "wording>\"")
        result = mode_refer(args, parser)
    else:
        result = mode_identify(args, parser)

    render(result, args.json)
    sys.exit(finish(result))


if __name__ == "__main__":
    main()
