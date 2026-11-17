#!/usr/bin/env python3
"""
icp_filing_check.py -- Single entry point for the ECS ICP filing guide skill
============================================================================
SECURITY: READ-ONLY. This script issues only the whitelisted read queries
(ecs DescribeInstances / DescribeSecurityGroups / DescribeSecurityGroupAttribute,
vpc DescribeEipAddresses, sts GetCallerIdentity) through `_cli.call`, which
refuses anything else before a process is even spawned. It never runs a command
inside an instance, never opens an interactive session, and never changes a
cloud resource. Every remedy it prints is manual guidance for the customer to
carry out in the console.

Modes
-----
  eligibility   Does this account hold a server that can carry an ICP filing
                service code? (Chinese mainland node + subscription whose
                PURCHASED length is longer than 3 months, renewals included +
                public bandwidth)                                     [capability C1]
  triage        A filed (or filing-in-progress) site will not open: prove from
                read-only cloud data whether the block is a security-group or
                public-address problem rather than filing interception
                                                                  [capability C2]
  knowledge     Filing rules and consequences, each carrying its ticket evidence
                and confidence flag, plus the boundary/handoff routing
                                                       [capabilities C3 + C4]
  selftest      Offline deterministic checks of every judgment function
                (no network, no credentials, no API call)

Output contract
---------------
Every mode ends with:
    STATUS: OK|DEGRADED|FAIL
    NEXT_ACTION: <one concrete instruction for the agent>
Exit code: 0 = a usable conclusion was produced, 1 = none.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

import _cli
from _cli import CliError
from _constants import (
    API_BLIND_SPOTS,
    API_VERSIONS,
    CONNECTION_RESET_SYMPTOMS,
    CUSTOMER_ENTRY_POINTS,
    ESCALATION_ROUTES,
    ICP_FILING_KNOWLEDGE,
    KNOWLEDGE_ORDER,
    MAINLAND_REGIONS,
    MAX_REGION_SCAN,
    MAX_SECURITY_GROUPS_CHECKED,
    MAX_SG_RULES,
    MIN_SUBSCRIPTION_MONTHS,
    NO_FIXED_TERM_YEAR,
    PURCHASED_TERM_HINT,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    SUBSCRIPTION_TERM_DOC,
    SUBSCRIPTION_TERM_EXCLUSIONS,
    SUBSCRIPTION_TERM_RULE,
    SUBSCRIPTION_TERM_RULE_ZH,
    WEB_PORTS,
)

BANNER = "Alibaba Cloud ECS ICP filing guide (READ-ONLY)"

# Strict input shapes: everything is passed to the CLI as a separate argument
# (never through a shell), and anything that could be mistaken for an option
# token is rejected before it gets near a call.
REGION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,30}$")
INSTANCE_ID_RE = re.compile(r"^(?:i-[a-z0-9]{6,30}|[a-z0-9]{6,30})$")
_OCTET = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
IPV4_RE = re.compile(r"^" + _OCTET + r"(?:\." + _OCTET + r"){3}$")
DOMAIN_RE = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,24}$", re.I)
TOPIC_KEYS = set(KNOWLEDGE_ORDER)


def validate(value: Optional[str], pattern: re.Pattern, label: str) -> Optional[str]:
    """Return the cleaned value or None, printing a rejection when malformed."""
    if value is None or value == "":
        return None
    cleaned = value.strip()
    if cleaned.startswith("-") or not pattern.match(cleaned):
        print(f"[ERROR] {label} '{cleaned[:40]}' is not a valid identifier; "
              f"it was rejected instead of being sent to the API.", file=sys.stderr)
        return None
    return cleaned


# ===========================================================================
# Pure judgment functions (no I/O -- unit-tested by mode `selftest`)
# ===========================================================================

def is_mainland_region(region_id: str, mainland: Iterable[str] = MAINLAND_REGIONS) -> bool:
    """Condition 1: the instance sits in a Chinese mainland node."""
    return (region_id or "").strip() in set(mainland)


def parse_api_utc(value: str) -> Optional[datetime]:
    """Parse the ECS UTC timestamps seen in the real responses.

    Verified shapes: '2026-09-15T05:34Z' (DescribeInstances) and
    '2026-09-18T02:32:07Z' (security-group rules). Returns None when the value
    is absent or unparseable -- never a guessed date.
    """
    text = (value or "").strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def months_between(start: datetime, end: datetime) -> float:
    """Month distance between two datetimes, rounded to 0.1 month."""
    if not start or not end:
        return 0.0
    return round((end - start).total_seconds() / (30.44 * 24 * 3600), 1)


def evaluate_instance_eligibility(
    instance: dict[str, Any],
    region_id: str,
    now: Optional[datetime] = None,
    purchased_months: Optional[float] = None,
) -> dict[str, Any]:
    """Score one instance against the three filing-server conditions.

    Only fields the API really returns are read. Anything unreadable becomes an
    explicit `unknown` condition, which downgrades the verdict to
    `needs_confirmation` rather than silently passing or failing.

    Condition 2 follows the official wording: subscription billing whose
    PURCHASED length is longer than 3 months, cumulative renewals included, and
    explicitly unrelated to server usage time or remaining term. The API does
    not return renewal history, so the judgement is made from, in order:
    `purchased_months` when the operator read it in the billing center, then the
    creation-to-expiry span as an explicitly labelled approximation, and
    otherwise `unknown`. A short remaining term never produces a `fail`.
    """
    now = now or datetime.now(timezone.utc)
    region = (str(instance.get("RegionId") or "") or region_id or "").strip()
    instance_id = str(instance.get("InstanceId") or "")
    charge_type = str(instance.get("InstanceChargeType") or "")
    expired_at = parse_api_utc(str(instance.get("ExpiredTime") or ""))
    created_at = parse_api_utc(str(instance.get("CreationTime") or ""))

    mainland = is_mainland_region(region)

    # Condition 2 -- a subscription whose PURCHASED length reaches the minimum.
    # The "more than 3 months" rule counts the original purchase plus renewals;
    # usage time and the term still remaining are explicitly irrelevant.
    term_state = "unknown"
    term_detail = "InstanceChargeType was not returned by the API."
    purchased_span: Optional[float] = None
    term_basis = "none"
    if charge_type == "PostPaid":
        term_state = "fail"
        term_detail = ("charge type is PostPaid (pay-as-you-go); the official "
                       "rule asks for subscription billing, so convert it to "
                       "subscription first. A free-trial ECS instance never "
                       "qualifies either.")
    elif charge_type == "PrePaid":
        if purchased_months is not None:
            purchased_span = round(float(purchased_months), 1)
            term_basis = "billing-center figure supplied on the command line"
            if purchased_span > MIN_SUBSCRIPTION_MONTHS:
                term_state = "pass"
                term_detail = (f"cumulative purchased length {purchased_span} months "
                               f"({term_basis}); the remaining term is irrelevant "
                               f"to this rule.")
            else:
                term_state = "fail"
                term_detail = (f"cumulative purchased length {purchased_span} months "
                               f"({term_basis}) does not exceed "
                               f"{MIN_SUBSCRIPTION_MONTHS} months; renewing adds to "
                               f"the cumulative length.")
        elif expired_at is None:
            term_detail = ("PrePaid instance but ExpiredTime was not returned, so "
                           "the purchased length cannot even be approximated. "
                           + PURCHASED_TERM_HINT)
        elif expired_at.year >= NO_FIXED_TERM_YEAR:
            term_detail = ("PrePaid instance reporting the no-fixed-term sentinel "
                           "expiry, so the purchased length cannot be derived. "
                           + PURCHASED_TERM_HINT)
        elif created_at is None:
            term_detail = ("PrePaid instance but CreationTime was not returned, so "
                           "the purchased length cannot be approximated. "
                           + PURCHASED_TERM_HINT)
        else:
            purchased_span = months_between(created_at, expired_at)
            term_basis = ("approximated from CreationTime to ExpiredTime, which "
                          "covers the original purchase plus renewals but not any "
                          "expired-then-renewed gap")
            if purchased_span >= MIN_SUBSCRIPTION_MONTHS:
                term_state = "pass"
                term_detail = (f"purchased/in-service span ~{purchased_span} months "
                               f"({created_at.date().isoformat()} -> "
                               f"{expired_at.date().isoformat()}, ~"
                               f"{max(months_between(now, expired_at), 0.0)} months "
                               f"left, which is NOT the criterion). {term_basis}; "
                               f"confirm the cumulative figure in the billing "
                               f"center when the case is borderline.")
            else:
                term_state = "unknown"
                term_detail = (f"purchased/in-service span only ~{purchased_span} "
                               f"months ({created_at.date().isoformat()} -> "
                               f"{expired_at.date().isoformat()}), which is below "
                               f"the 3-month purchase condition. " +
                               PURCHASED_TERM_HINT)
    elif charge_type:
        term_detail = f"unrecognised charge type '{charge_type}'."

    # Condition 3 -- public bandwidth is enabled.
    fixed_ips = [str(ip) for ip in
                 (instance.get("PublicIpAddress") or {}).get("IpAddress") or []]
    eip = str((instance.get("EipAddress") or {}).get("IpAddress") or "")
    raw_bandwidth = instance.get("InternetMaxBandwidthOut")
    try:
        bandwidth = int(raw_bandwidth) if raw_bandwidth is not None else None
    except (TypeError, ValueError):
        bandwidth = None

    if bandwidth is not None and bandwidth > 0:
        bandwidth_state = "pass"
        bandwidth_detail = f"public bandwidth out {bandwidth} Mbit/s."
    elif eip:
        bandwidth_state = "pass"
        bandwidth_detail = f"public traffic is carried by the associated EIP {eip}."
    elif fixed_ips:
        bandwidth_state = "pass"
        bandwidth_detail = ("a fixed public address is attached (" + ", ".join(fixed_ips) +
                            ") although InternetMaxBandwidthOut reads 0; confirm the "
                            "bandwidth value on the instance page.")
    else:
        bandwidth_state = "fail"
        bandwidth_detail = ("no public bandwidth (InternetMaxBandwidthOut=0), no fixed "
                            "public address and no EIP: the internet cannot reach it.")

    checks = {
        "mainland_region": {
            "state": "pass" if mainland else "fail",
            "detail": f"region {region or 'not returned'}"
                      + ("" if mainland else " is not a Chinese mainland node"),
        },
        "subscription_term": {"state": term_state, "detail": term_detail},
        "public_bandwidth": {"state": bandwidth_state, "detail": bandwidth_detail},
    }
    missing = [name for name, res in checks.items() if res["state"] == "fail"]
    unknown = [name for name, res in checks.items() if res["state"] == "unknown"]
    verdict = ("eligible" if not missing and not unknown
               else "not_eligible" if missing else "needs_confirmation")

    return {
        "instance_id": instance_id,
        "instance_name": str(instance.get("InstanceName") or ""),
        "region_id": region,
        "status": str(instance.get("Status") or ""),
        "os": str(instance.get("OSNameEn") or instance.get("OSName") or ""),
        "public_addresses": fixed_ips + ([eip] if eip else []),
        "security_group_ids": [
            str(sg) for sg in (instance.get("SecurityGroupIds") or {}).get("SecurityGroupId") or []
        ],
        "purchased_months_estimate": purchased_span,
        "purchased_months_basis": term_basis,
        "checks": checks,
        "missing_conditions": missing,
        "unconfirmed_conditions": unknown,
        "verdict": verdict,
    }


def port_range_covers(port_range: str, port: int) -> bool:
    """Does a PortRange token like '80/80' or '-1/-1' include `port`?

    '-1/-1' means every port (observed on real ICMP rules). An empty or
    malformed value is treated as NOT matching, so the caller sees a gap rather
    than a false pass.
    """
    text = (port_range or "").strip()
    if text in ("-1/-1", "*"):
        return True
    low_s, sep, high_s = text.partition("/")
    if not sep:
        return False
    try:
        low, high = int(low_s), int(high_s)
    except ValueError:
        return False
    if low == -1 and high == -1:
        return True
    return low <= port <= high


def is_public_source(rule: dict[str, Any]) -> bool:
    """True when the rule admits the whole public internet as its source."""
    cidr = str(rule.get("SourceCidrIp") or "").strip()
    ipv6 = str(rule.get("Ipv6SourceCidrIp") or "").strip()
    if rule.get("SourceGroupId") or rule.get("SourcePrefixListId"):
        return False
    if not cidr and not ipv6:
        return False
    return cidr == "0.0.0.0/0" or ipv6 == "::/0"


def _priority_of(rule: dict[str, Any]) -> int:
    try:
        return int(rule.get("Priority"))
    except (TypeError, ValueError):
        return 101


def evaluate_sg_port(permissions: list[dict[str, Any]], port: int) -> dict[str, Any]:
    """Decide whether inbound public traffic to `port` passes one security group.

    Mirrors the documented rule merge: among the matching ingress rules the
    lowest Priority number wins, a Drop at that level beats any Accept, and no
    match at all means deny (the default policy).
    """
    matches = [
        rule for rule in permissions
        if str(rule.get("Direction") or "ingress").lower() in ("ingress", "all")
        and str(rule.get("IpProtocol") or "").upper() in ("ALL", "TCP")
        and port_range_covers(str(rule.get("PortRange") or ""), port)
    ]
    if not matches:
        return {
            "port": port, "verdict": "no_rule", "public_allowed": False,
            "matched_rules": [],
            "note": (f"no inbound TCP rule covers port {port}; the security group's "
                     f"default policy is deny, so the request never reaches the instance"),
        }

    best = min(_priority_of(rule) for rule in matches)
    winners = [rule for rule in matches if _priority_of(rule) == best]
    dropped = [rule for rule in winners if str(rule.get("Policy") or "").lower() == "drop"]
    public_accept = [rule for rule in winners
                     if str(rule.get("Policy") or "").lower() == "accept" and is_public_source(rule)]
    narrow_accept = [rule for rule in winners
                     if str(rule.get("Policy") or "").lower() == "accept" and not is_public_source(rule)]

    if dropped:
        verdict, public_allowed = "explicitly_dropped", False
    elif public_accept:
        verdict, public_allowed = "open_to_public", True
    elif narrow_accept:
        verdict, public_allowed = "limited_source_only", False
    else:
        verdict, public_allowed = "no_allowing_rule", False

    sources = sorted({
        str(rule.get("SourceCidrIp") or rule.get("Ipv6SourceCidrIp")
            or rule.get("SourceGroupId") or "(no source set)")
        for rule in (public_accept + narrow_accept)
    })
    note = ""
    if not public_allowed:
        note = (f"port {port} is not open to the public internet in this group "
                f"({verdict}); sources actually allowed: "
                f"{', '.join(sources) if sources else 'none'}")
    return {
        "port": port,
        "verdict": verdict,
        "public_allowed": public_allowed,
        "winning_priority": best,
        "matched_rules": [
            {
                "rule_id": str(rule.get("SecurityGroupRuleId") or ""),
                "policy": str(rule.get("Policy") or ""),
                "priority": rule.get("Priority"),
                "port_range": str(rule.get("PortRange") or ""),
                "ip_protocol": str(rule.get("IpProtocol") or ""),
                "source": str(rule.get("SourceCidrIp") or rule.get("Ipv6SourceCidrIp")
                              or rule.get("SourceGroupId") or "(no source set)"),
            }
            for rule in sorted(matches, key=_priority_of)[:10]
        ],
        "note": note,
    }


def overall_port_verdict(per_sg: list[dict[str, Any]], port: int) -> dict[str, Any]:
    """Merge one port's verdicts across every security group attached to the NIC."""
    def _flag(groups: list[dict[str, Any]], wanted: str) -> bool:
        return any(any(p["port"] == port and p["verdict"] == wanted for p in g["ports"])
                   for g in groups)

    open_groups = [g for g in per_sg
                   if any(p["port"] == port and p["public_allowed"] for p in g["ports"])]
    if open_groups:
        verdict = "allowed"
        where = ", ".join(g["security_group_id"] for g in open_groups)
    elif _flag(per_sg, "explicitly_dropped"):
        verdict = "blocked_by_drop_rule"
        where = ", ".join(g["security_group_id"] for g in per_sg
                          if _flag([g], "explicitly_dropped"))
    elif _flag(per_sg, "limited_source_only"):
        verdict = "allowed_for_narrow_source_only"
        where = ", ".join(g["security_group_id"] for g in per_sg
                          if _flag([g], "limited_source_only"))
    else:
        verdict = "no_inbound_allow_rule"
        where = ", ".join(g["security_group_id"] for g in per_sg)
    return {"port": port, "verdict": verdict, "groups_involved": where}


def matches_symptom(text: str) -> list[str]:
    """Which declared customer-visible symptom strings appear in `text`?"""
    low = (text or "").lower()
    return [sym for sym in CONNECTION_RESET_SYMPTOMS if sym in low]


def search_topics(query: str) -> list[tuple[str, int]]:
    """Rank knowledge keys by keyword overlap with the customer's wording."""
    words = [w for w in re.sub(r"[^a-z0-9 ]", " ", (query or "").lower()).split() if len(w) > 3]
    scored: list[tuple[str, int]] = []
    for key in KNOWLEDGE_ORDER:
        entry = ICP_FILING_KNOWLEDGE[key]
        haystack = (entry["title"] + " " + " ".join(entry["points"])).lower()
        score = sum(haystack.count(word) for word in words)
        if score:
            scored.append((key, score))
    scored.sort(key=lambda kv: (-kv[1], kv[0]))
    return scored


def match_routes(text: str) -> list[str]:
    """Which escalation routes claim this request?"""
    low = (text or "").lower()
    return [
        name for name, route in ESCALATION_ROUTES.items()
        if any(signal.lower() in low for signal in route["signals"])
    ]


# ===========================================================================
# Evidence gathering -- the only place that touches the CLI
# ===========================================================================

class Evidence:
    """Runs whitelisted read queries and remembers every degradation."""

    def __init__(self, profile: Optional[str], timeout: int):
        self.profile = profile
        self.timeout = timeout
        self.errors: list[dict[str, str]] = []
        self.calls: list[str] = []

    def record(self, step: str, err: BaseException) -> None:
        rec = _cli.describe_error(err)
        rec["step"] = step
        self.errors.append(rec)
        print(f"[WARN] {step}: {rec['code'] or 'error'}: {rec['message'][:240]}",
              file=sys.stderr)

    def note(self, step: str, message: str) -> None:
        print(f"[WARN|DEGRADE] {step}: {message}", file=sys.stderr)


def describe_all_instances(ev: Evidence, region: str) -> list[dict[str, Any]]:
    ev.calls.append("ecs/DescribeInstances")
    try:
        return _cli.paginate_page_number(
            "ecs", "DescribeInstances", {"RegionId": region},
            items_path=["Instances", "Instance"], region=region, profile=ev.profile)
    except CliError as err:
        ev.record(f"DescribeInstances in {region}", err)
        return []


def find_instance(ev: Evidence, region: str, instance_id: Optional[str],
                  public_ip: Optional[str]) -> tuple[list[dict[str, Any]], str]:
    """Locate the target instance and report HOW it was located."""
    params: dict[str, Any] = {"RegionId": region}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
        how = f"filtered by InstanceIds={instance_id}"
    elif public_ip:
        params["PublicIpAddresses"] = json.dumps([public_ip])
        how = f"filtered by PublicIpAddresses={public_ip}"
    else:
        how = "no filter (every instance in the region)"

    ev.calls.append("ecs/DescribeInstances")
    try:
        found = _cli.paginate_page_number(
            "ecs", "DescribeInstances", params, items_path=["Instances", "Instance"],
            region=region, profile=ev.profile)
    except CliError as err:
        ev.record(f"DescribeInstances in {region}", err)
        return [], how

    if public_ip and not found:
        # The fixed-public-IP filter does not match EIP-fronted instances: try
        # the EIP filter, then fall back to matching the returned fields locally.
        ev.calls.append("ecs/DescribeInstances (EipAddresses filter)")
        try:
            found = _cli.paginate_page_number(
                "ecs", "DescribeInstances",
                {"RegionId": region, "EipAddresses": json.dumps([public_ip])},
                items_path=["Instances", "Instance"], region=region, profile=ev.profile)
            how = f"filtered by EipAddresses={public_ip}"
        except CliError as err:
            ev.record(f"EIP-filtered DescribeInstances in {region}", err)
        if not found:
            all_instances = describe_all_instances(ev, region)
            found = [
                inst for inst in all_instances
                if public_ip in [str(ip) for ip in
                                 (inst.get("PublicIpAddress") or {}).get("IpAddress") or []]
                or public_ip == str((inst.get("EipAddress") or {}).get("IpAddress") or "")
            ]
            how = f"matched locally against PublicIpAddress/EipAddress of {len(all_instances)} instance(s)"
    return found, how


def list_security_groups(ev: Evidence, region: str) -> list[dict[str, Any]]:
    ev.calls.append("ecs/DescribeSecurityGroups")
    try:
        return _cli.paginate_page_number(
            "ecs", "DescribeSecurityGroups", {"RegionId": region},
            items_path=["SecurityGroups", "SecurityGroup"],
            region=region, profile=ev.profile)
    except CliError as err:
        ev.record(f"DescribeSecurityGroups in {region}", err)
        return []


def security_group_rules(ev: Evidence, region: str, sg_id: str) -> list[dict[str, Any]]:
    ev.calls.append("ecs/DescribeSecurityGroupAttribute")
    try:
        # No pagination on this API (PageNumber/NextToken are rejected; verified
        # 2026-09-24) - it returns the whole filtered rule set in one call.
        body = _cli.call("ecs", "DescribeSecurityGroupAttribute",
                         {"RegionId": region, "SecurityGroupId": sg_id,
                          "Direction": "ingress"},
                         region=region, profile=ev.profile)
        perms = ((body.get("Permissions") or {}).get("Permission") or [])
        return [p for p in perms if isinstance(p, dict)][:MAX_SG_RULES]
    except CliError as err:
        ev.record(f"DescribeSecurityGroupAttribute for {sg_id}", err)
        return []


def eip_snapshot(ev: Evidence, region: str) -> list[dict[str, Any]]:
    ev.calls.append("vpc/DescribeEipAddresses")
    try:
        return _cli.paginate_page_number(
            "vpc", "DescribeEipAddresses", {"RegionId": region},
            items_path=["EipAddresses", "EipAddress"],
            region=region, profile=ev.profile)
    except CliError as err:
        ev.record(f"DescribeEipAddresses in {region}", err)
        return []


# ===========================================================================
# Report rendering helpers
# ===========================================================================

def rule(width: int = 76) -> str:
    return "=" * width


def blind_spot_lines() -> list[str]:
    return ["What no read-only cloud API in this skill can see:"] + \
           [f"  - {spot}" for spot in API_BLIND_SPOTS]


def finish(payload: dict[str, Any], status: str, next_action: str, as_json: bool) -> int:
    """Emit the report (or JSON) and close the STATUS / NEXT_ACTION contract."""
    payload["status"] = status
    payload["next_action"] = next_action
    payload["read_only"] = True
    lines = payload.pop("_lines", [])
    if as_json:
        payload["STATUS"] = status
        payload["NEXT_ACTION"] = next_action
        print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
    else:
        print("\n".join(lines))
        print(f"\nSTATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    return 0 if status in (STATUS_OK, STATUS_DEGRADED) else 1


def rollup_status(errors: list[dict[str, str]], nothing_read: bool) -> str:
    if nothing_read and errors:
        return STATUS_FAIL
    if nothing_read or errors:
        return STATUS_DEGRADED
    return STATUS_OK


def fail_open(args: argparse.Namespace, mode: str, reason: str, header: str,
              next_action: str) -> int:
    """Report a precondition failure without ever inventing evidence."""
    payload = {
        "mode": mode, "status": STATUS_FAIL, "read_only": True,
        "reason": reason, "next_action": next_action,
        "STATUS": STATUS_FAIL, "NEXT_ACTION": next_action,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(rule())
        print(f" {header} -- {BANNER}")
        print(rule())
        print(f"  {reason}")
        print("  Nothing was concluded and no cloud resource was touched.")
        print(f"\nSTATUS: {STATUS_FAIL}")
        print(f"NEXT_ACTION: {next_action}")
    return 1


# ===========================================================================
# Mode: eligibility (capability C1)
# ===========================================================================

def mode_eligibility(args: argparse.Namespace) -> int:
    if args.region and not args.regions:
        args.regions = args.region
    regions = [r.strip() for r in (args.regions or "").split(",") if r.strip()]
    auto_selected = not regions
    if auto_selected:
        regions = list(MAINLAND_REGIONS)
    regions = [r for r in regions if validate(r, REGION_RE, "region id")]
    if len(regions) > MAX_REGION_SCAN:
        print(f"[WARN] region list trimmed to the {MAX_REGION_SCAN}-region cap",
              file=sys.stderr)
        regions = regions[:MAX_REGION_SCAN]
    if not regions:
        return fail_open(args, "eligibility", "no usable region id was supplied.",
                         "ELIGIBILITY SCAN", "Re-run with --regions cn-hangzhou,cn-shanghai "
                         "using valid region identifiers.")

    ev = Evidence(args.profile, args.timeout)
    uid = _cli.resolve_account_uid(profile=args.profile, timeout=args.timeout)
    if not uid:
        ev.note("caller identity", "STS GetCallerIdentity returned no account; the "
                                   "report keeps its UID label as 'unresolved'")

    inspected = 0
    buckets: dict[str, list[dict[str, Any]]] = {"eligible": [], "needs_confirmation": [],
                                                "not_eligible": []}
    region_failures: list[str] = []
    for region in regions:
        before = len(ev.errors)
        instances = describe_all_instances(ev, region)
        if len(ev.errors) > before:
            region_failures.append(region)
        for inst in instances:
            inspected += 1
            row = evaluate_instance_eligibility(
                inst, region, purchased_months=args.purchased_months)
            buckets[row["verdict"]].append(row)

    lines = [rule(), f" ICP FILING SERVER ELIGIBILITY -- {BANNER}", rule(),
             f"  Account UID (traceability label): {uid or 'unresolved'}",
             f"  Regions scanned: {len(regions)}"
             + (" (auto-selected Chinese mainland scan list; override with --regions)"
                if auto_selected else " (exactly as requested)"),
             f"  Instances inspected: {inspected}", ""]

    if inspected == 0:
        verdict_text = "NONE_FOUND"
        lines.append("  No ECS instance was visible in the scanned regions.")
        if region_failures:
            lines.append(f"  Regions that failed to answer: {', '.join(region_failures)} -- this")
            lines.append("  is a permission/configuration gap, NOT evidence that the account is empty.")
    elif buckets["eligible"]:
        verdict_text = "ELIGIBLE_INSTANCE_FOUND"
        lines.append(f"  {len(buckets['eligible'])} instance(s) satisfy all three conditions:")
        for row in buckets["eligible"]:
            lines.append(f"    - {row['instance_id']}  region={row['region_id']}  "
                         f"public={', '.join(row['public_addresses']) or 'none reported'}  "
                         f"state={row['status'] or 'unknown'}")
        lines.append("  Next: bind the filing service code to one of these (same account), or use")
        lines.append("  the free code the system generates for a compliant instance.")
    else:
        verdict_text = "NO_ELIGIBLE_INSTANCE"
        lines.append("  No instance in the scanned regions satisfies all three conditions.")

    lines += ["", "  The three conditions (official filing-server list, ticket T-C097A6CB):",
              "    1. the server is in a Chinese mainland node;",
              f"    2. {SUBSCRIPTION_TERM_RULE}",
              "       Official wording: " + SUBSCRIPTION_TERM_RULE_ZH,
              "    3. public bandwidth is enabled on it.", ""]
    for exclusion in SUBSCRIPTION_TERM_EXCLUSIONS:
        lines.append(f"    - {exclusion}")
    lines.append(f"    Rule page: {SUBSCRIPTION_TERM_DOC}")
    if args.purchased_months is not None:
        lines.append(f"  Cumulative purchased length supplied by the caller: "
                     f"{args.purchased_months} months (used for condition 2).")
    else:
        lines.append("  Condition 2 basis per instance: " + PURCHASED_TERM_HINT)
    lines.append("")

    detail_rows = buckets["not_eligible"] + buckets["needs_confirmation"]
    shown = detail_rows[:15]
    if shown:
        lines.append(f"  Per-instance detail ({len(shown)} of {len(detail_rows)} shown):")
        for row in shown:
            lines.append(f"    - {row['instance_id']} [{row['region_id']}] "
                         f"verdict={row['verdict']}")
            for name, res in row["checks"].items():
                lines.append(f"        {name:<19} {res['state']:<9} {res['detail']}")
        if len(detail_rows) > len(shown):
            lines.append(f"        ... {len(detail_rows) - len(shown)} more (use --json for all)")
        lines.append("")

    if buckets["needs_confirmation"]:
        lines.append(f"  {len(buckets['needs_confirmation'])} instance(s) have a condition the API "
                     f"does not expose.")
        lines.append("  Never report those as eligible: ask the customer for the cumulative")
        lines.append("  purchased length (billing center / 费用中心) or the bandwidth value")
        lines.append("  (instance page). A short remaining term is NOT a disqualification.")
        lines.append("")

    lines += ["  This check cannot see (ask the customer, or hand off):",
              "    - the filing service code inventory and its state -- no filing-data API is",
              "      whitelisted here, so read it in the ICP Filing console;",
              "    - whether a code was already consumed by another filing;",
              "    - the domain's real-name subject and the filing subject;",
              "    - whether a paid code is refundable (a commercial decision).", "",
              ] + blind_spot_lines()

    if region_failures:
        lines += ["", f"  Permission hint: if a region failed with NoPermission or ImplicitDeny, "
                      f"the missing",
                  f"  read action is listed in references/ram-policies.md."]

    if verdict_text == "NONE_FOUND" and not region_failures:
        next_action = ("Say plainly that no ECS instance was found in the scanned regions, "
                       "list the regions scanned, and ask the customer to confirm the region "
                       "of the server they intended; an empty scan is a finding, not an error.")
    elif verdict_text == "ELIGIBLE_INSTANCE_FOUND":
        next_action = ("Report the eligible instances, restate the three conditions, and send "
                       "the filing submission itself to the ICP Filing console. Never claim a "
                       "filing state from this output.")
    elif verdict_text == "NONE_FOUND":
        next_action = ("Report which regions could not be read and the failing code; grant the "
                       "read-only actions in references/ram-policies.md and re-run. Do not "
                       "conclude that the account holds no server.")
    else:
        next_action = ("Give the per-instance missing condition, then guide the customer to "
                       "obtain a compliant Chinese mainland subscription instance -- billed "
                       "as subscription with a purchased length longer than "
                       f"{MIN_SUBSCRIPTION_MONTHS} months including renewals -- with public "
                       "bandwidth in the SAME account (a console purchase they perform "
                       "themselves -- this skill never buys, renews or refunds), or to the "
                       "paid filing concierge.")
    return finish({"mode": "eligibility", "uid_label": uid or "unresolved",
                   "regions_scanned": regions, "regions_with_failures": region_failures,
                   "instances_inspected": inspected, "eligible": buckets["eligible"],
                   "needs_confirmation": buckets["needs_confirmation"],
                   "not_eligible": buckets["not_eligible"], "verdict": verdict_text,
                   "subscription_term_rule": {
                       "official_zh": SUBSCRIPTION_TERM_RULE_ZH,
                       "rendered": SUBSCRIPTION_TERM_RULE,
                       "exclusions": list(SUBSCRIPTION_TERM_EXCLUSIONS),
                       "doc": SUBSCRIPTION_TERM_DOC,
                       "caller_supplied_months": args.purchased_months,
                   },
                   "errors": ev.errors, "api_calls_made": sorted(set(ev.calls)),
                   "api_versions": API_VERSIONS, "_lines": lines},
                  rollup_status(ev.errors, nothing_read=inspected == 0 and bool(region_failures)),
                  next_action, args.json)


# ===========================================================================
# Mode: triage (capability C2)
# ===========================================================================

def mode_triage(args: argparse.Namespace) -> int:
    region = validate(args.region, REGION_RE, "region id")
    instance_id = validate(args.instance_id, INSTANCE_ID_RE, "instance id")
    public_ip = validate(args.public_ip, IPV4_RE, "public IP")
    domain = validate(args.domain, DOMAIN_RE, "domain") if args.domain else None
    if args.region and not region:
        return fail_open(args, "triage", "the region id supplied is not a valid identifier.",
                         "ACCESS TRIAGE", "Re-run with a region id such as cn-hangzhou.")
    if args.instance_id and not instance_id:
        return fail_open(args, "triage", "the instance id supplied is not a valid identifier.",
                         "ACCESS TRIAGE", "Re-run with the i-... id shown in the ECS console.")
    if args.public_ip and not public_ip:
        return fail_open(args, "triage", "the public IP supplied is not a valid IPv4 address.",
                         "ACCESS TRIAGE", "Re-run with the dotted-quad address the domain resolves to.")

    ev = Evidence(args.profile, args.timeout)
    uid = _cli.resolve_account_uid(profile=args.profile, timeout=args.timeout)
    symptom_hits = sorted(set(matches_symptom(args.symptom or "") + matches_symptom(args.question or "")))

    instances, how = find_instance(ev, region or "", instance_id, public_ip)
    payload: dict[str, Any] = {
        "mode": "triage", "uid_label": uid or "unresolved", "region_id": region,
        "domain": domain or "", "symptom": args.symptom or "",
        "symptom_codes_detected": symptom_hits, "lookup_method": how,
        "instances": [], "security_groups": [], "port_verdicts": [],
        "eip_addresses": [], "errors": ev.errors,
        "api_calls_made": sorted(set(ev.calls)), "api_versions": API_VERSIONS,
    }

    lines = [rule(), f" FILED-SITE ACCESS TRIAGE -- {BANNER}", rule(),
             f"  Account UID (traceability label): {uid or 'unresolved'}",
             f"  Region: {region}   Instance: {instance_id or '(looked up by public IP)'}   "
             f"Domain: {domain or '(not given)'}",
             f"  Instance lookup: {how}", ""]

    if symptom_hits:
        lines += ["  Declared symptom strings in the request: " + ", ".join(symptom_hits),
                  "  ROUTE FIRST: a connection torn down mid-request is the shape of an inbound-rule",
                  "  interception, so the security group is examined before any filing talk. In ticket",
                  "  T-63E5332F the customer had already proven TCP setup worked and HTTP/TLS died",
                  "  after ~5 seconds with empty server logs: the cause was missing 80/443 inbound",
                  "  rules, and the agent's answer was explicitly 'unrelated to filing synchronisation'.",
                  ""]

    if not instances:
        lines.append("  Step 1 -- NO instance could be confirmed in this region.")
        lines.append("  Nothing may be concluded about the website: the domain may point at another")
        lines.append("  region, at an EIP, at a CDN or object-storage origin, or at an instance the")
        lines.append("  current credential cannot see. Filing is not established as a cause here.")
        lines += [""] + blind_spot_lines()
        payload["verdict"] = "INSTANCE_NOT_LOCATED"
        payload["_lines"] = lines
        core = bool(ev.errors)
        return finish(payload, STATUS_FAIL if core else STATUS_DEGRADED,
                      "Ask the customer for the instance ID and region (or the public IP and "
                      "region) as shown in the ECS console, and for the DNS record the domain "
                      "currently resolves to; then re-run. Never attribute the outage to filing "
                      "on this evidence.", args.json)

    inst = instances[0]
    row = evaluate_instance_eligibility(inst, region or "",
                                        purchased_months=args.purchased_months)
    payload["instances"] = [row]
    lines.append(f"  Step 1 -- instance {row['instance_id']}  status={row['status'] or 'unknown'}  "
                 f"region={row['region_id']}")
    lines.append(f"           name: {row['instance_name'] or '(unset)'}   os: {row['os'] or 'unknown'}")
    lines.append(f"           public addresses: {', '.join(row['public_addresses']) or 'NONE'}")
    lines.append(f"           security groups:  {', '.join(row['security_group_ids']) or 'none reported'}")
    if not row["public_addresses"]:
        lines.append("           NOTE: no fixed public address and no EIP -- a domain cannot reach this")
        lines.append("           instance directly; check NAT/CDN/object storage or another instance.")
    lines.append("")

    sg_ids = row["security_group_ids"][:MAX_SECURITY_GROUPS_CHECKED]
    if len(row["security_group_ids"]) > MAX_SECURITY_GROUPS_CHECKED:
        ev.note("security groups", f"{len(row['security_group_ids'])} groups attached; only the "
                                   f"first {MAX_SECURITY_GROUPS_CHECKED} were inspected")

    inventory = list_security_groups(ev, region or "")
    names = {str(g.get("SecurityGroupId")): str(g.get("SecurityGroupName") or "")
             for g in inventory}
    if not sg_ids:
        lines.append(f"  Step 2 -- the instance reported no security group. Region inventory "
                     f"holds {len(inventory)} group(s): "
                     + ", ".join(list(names)[:MAX_SECURITY_GROUPS_CHECKED] or ["none"]))
        lines.append("  Ask the customer which group the instance uses before concluding anything.")
        lines.append("")

    per_sg: list[dict[str, Any]] = []
    ports_txt = ", ".join(str(p) for p in WEB_PORTS)
    lines.append(f"  Step 2 -- inbound rules for web ports {ports_txt} "
                 f"({'no group attached' if not sg_ids else str(len(sg_ids)) + ' group(s)'}):")
    for sg_id in sg_ids:
        raw_rules = security_group_rules(ev, region or "", sg_id)
        name = names.get(sg_id, "")
        entry: dict[str, Any] = {"security_group_id": sg_id, "security_group_name": name,
                                 "rule_count_returned": len(raw_rules), "ports": []}
        label = f"[{sg_id}" + (f" / {name}" if name else "") + "]"
        for port in WEB_PORTS:
            verdict = evaluate_sg_port(raw_rules, port)
            entry["ports"].append(verdict)
            extra = (f" (winning priority {verdict['winning_priority']})"
                     if verdict["matched_rules"] else "")
            lines.append(f"    {label} port {port}: {verdict['verdict']}{extra}"
                         + (f" -- {verdict['note']}" if verdict["note"] else ""))
            for rule_row in verdict["matched_rules"][:3]:
                lines.append(f"        rule {rule_row['rule_id'] or '(id unset)'}: "
                             f"{rule_row['policy']} prio={rule_row['priority']} "
                             f"{rule_row['ip_protocol']} {rule_row['port_range']} "
                             f"src={rule_row['source']}")
        per_sg.append(entry)
    payload["security_groups"] = per_sg
    lines.append("")

    merged = [overall_port_verdict(per_sg, port) for port in WEB_PORTS] if per_sg else []
    payload["port_verdicts"] = merged
    blocked = [m for m in merged if m["verdict"] != "allowed"]
    if merged:
        lines.append("  Step 2 conclusion across the attached groups:")
        for m in merged:
            mark = "OK" if m["verdict"] == "allowed" else "!!"
            lines.append(f"    [{mark}] port {m['port']}: {m['verdict']} "
                         f"(groups: {m['groups_involved'] or 'none'})")
        lines.append("")
    if blocked:
        ports_txt = ", ".join(str(m["port"]) for m in blocked)
        lines += [f"  VERDICT: inbound public traffic to {ports_txt} is stopped by the SECURITY GROUP,",
                  "  not by filing. This is the most frequent root cause in this scenario",
                  "  (tickets T-63E5332F, T-7DFF74E6 and T-AF9A4EAA were all missing inbound rules).",
                  "",
                  "  MANUAL fix -- this skill never writes a rule, the customer does it in the console:",
                  f"    {CUSTOMER_ENTRY_POINTS['security_group_console']['console_path']}",
                  "    ECS console > Security Groups > the group above > Inbound > add a rule for",
                  "    TCP 80/80 and 443/443 with source 0.0.0.0/0 (or a narrower CIDR they choose),",
                  "    then retest from outside the network.",
                  "    Guidance: https://help.aliyun.com/zh/ecs/user-guide/manage-security-group-rules",
                  ""]
    elif merged:
        lines += ["  VERDICT: the security groups allow public inbound traffic on the web ports,",
                  "  so the security group is NOT the blocker. Continue down the tree (steps 3-4).", ""]

    lines.append("  Step 3 -- Elastic IP addresses in this region (public egress state):")
    eips = [{
        "allocation_id": str(e.get("AllocationId") or ""),
        "ip_address": str(e.get("IpAddress") or ""),
        "status": str(e.get("Status") or ""),
        "bandwidth": str(e.get("Bandwidth") or ""),
        "instance_id": str(e.get("InstanceId") or ""),
        "instance_type": str(e.get("InstanceType") or ""),
        "charge_type": str(e.get("InternetChargeType") or ""),
    } for e in eip_snapshot(ev, region or "")]
    payload["eip_addresses"] = eips
    mine = [e for e in eips if e["instance_id"] == row["instance_id"]
            or e["ip_address"] in row["public_addresses"]]
    if not eips:
        lines.append("    none returned for this region: the instance uses a fixed public address")
        lines.append("    (see step 1) or no public egress at all.")
    for e in (mine or eips[:MAX_SECURITY_GROUPS_CHECKED]):
        flag = "" if e["status"] == "InUse" else f"  <-- status {e['status']}, not InUse"
        bound = f" bound to {e['instance_id']}" if e["instance_id"] else " not bound to any resource"
        lines.append(f"    {e['ip_address']}  status={e['status']}{flag}  "
                     f"bandwidth={e['bandwidth']}M  charge={e['charge_type']}{bound}")
    if mine and any(e["status"] != "InUse" for e in mine):
        lines.append("    An EIP that is not InUse carries no traffic to the instance.")
    if eips and not mine:
        lines.append(f"    (showing {min(len(eips), MAX_SECURITY_GROUPS_CHECKED)} of {len(eips)} "
                     f"EIPs in the region; none is attached to this instance)")
    lines.append("")

    lines.append("  Step 4 -- what the cloud side cannot answer; do not guess these:")
    lines.append("    - FILING STATE: ask the customer for the ICP Filing console status of this")
    lines.append("      domain. No filing-data API is whitelisted here, so a claim that the filing")
    lines.append("      system itself is blocking access may never be stated from this output")
    lines.append("      alone (the only ticket in this tier whose summary claimed that")
    lines.append("      -- T-FC32DAA3 -- has no transcript evidence, so it stays unverified).")
    if domain:
        lines.append(f"    - DNS: in the Alibaba Cloud DNS console check that {domain} carries an @")
        lines.append("      record (plus www) pointing at the public address above. In tickets")
        lines.append("      T-16AB330B and T-3BE66325 the subdomain worked while the root domain")
        lines.append("      simply had no record -- no security group and no filing was involved.")
    else:
        lines.append("    - DNS: ask for the domain name, then have the customer check the root (@)")
        lines.append("      record in the Alibaba Cloud DNS console against the address above.")
    lines += ["    - GUEST LISTENER: this skill never runs a command on the instance. The customer",
              "      can look for a process listening on 80/443 (ss/netstat, the web-server error",
              "      log, the local firewall), or the check is handed to alibabacloud-ecs-diagnose",
              "      or a server specialist. Ticket T-D9F63B3E was exactly this: the group allowed",
              "      443, nothing was listening, and the customer had blamed filing.",
              "      Being unfiled does not close a port; a filing-side block and a closed port",
              "      are different findings and need different remedies.",
              ""]
    lines += blind_spot_lines()

    if blocked:
        verdict_text = "BLOCKED_BY_SECURITY_GROUP"
        next_action = ("Report the security-group finding with the rule evidence quoted from this "
                       "output, give the console path and the security-group-rules doc for the "
                       "manual fix, and state that filing is not the cause. Never offer to add the "
                       "rule yourself.")
    elif not row["public_addresses"]:
        verdict_text = "NO_PUBLIC_ADDRESS"
        next_action = ("Tell the customer the instance has no public address for a domain to point "
                       "at, ask where the domain actually resolves today, and route the hosting "
                       "question from there.")
    elif merged:
        verdict_text = "NETWORK_PATH_CLEAR_FILING_STATE_UNKNOWN"
        next_action = ("Cloud-side path is clear: request the ICP Filing console status for the "
                       "domain and the guest listener self-check, then route to a filing agent or "
                       "to alibabacloud-ecs-diagnose. Do not declare the filing side clean.")
    else:
        verdict_text = "INSUFFICIENT_EVIDENCE"
        next_action = ("No security group could be inspected for this instance: ask which group it "
                       "uses (or grant ecs:DescribeSecurityGroupAttribute) and re-run.")
    payload["verdict"] = verdict_text
    payload["_lines"] = lines
    return finish(payload, rollup_status(ev.errors, nothing_read=False), next_action, args.json)


# ===========================================================================
# Mode: knowledge (capabilities C3 + C4)
# ===========================================================================

def topic_dict(key: str) -> dict[str, Any]:
    entry = ICP_FILING_KNOWLEDGE[key]
    return {
        "key": key,
        "title": entry["title"],
        "points": list(entry["points"]),
        "confidence": entry["confidence"],
        "tickets": list(entry["tickets"]),
        "docs": list(entry["docs"]),
    }


def render_topic(key: str) -> list[str]:
    entry = ICP_FILING_KNOWLEDGE[key]
    lines = [f"\n[{key}] {entry['title']}",
             f"  evidence: tickets {', '.join(entry['tickets'])}   "
             f"confidence: {entry['confidence']}"]
    if entry["confidence"] != "transcript-verified":
        lines += ["  CAVEAT: not backed by a complete support transcript. Confirm the wording",
                  "          with a filing specialist before quoting it as policy to a customer."]
    lines += [f"  - {point}" for point in entry["points"]]
    if entry["docs"]:
        lines.append("  reference links (quoted by the handling agent in the ticket; re-verify")
        lines.append("  before sending them to a customer -- see references/icp-filing-guide__help-links.md):")
        lines += [f"    {doc}" for doc in entry["docs"]]
    return lines


def mode_knowledge(args: argparse.Namespace) -> int:
    if args.list_topics:
        if args.json:
            print(json.dumps({"mode": "knowledge", "catalogue": [topic_dict(k) for k in KNOWLEDGE_ORDER],
                              "STATUS": STATUS_OK, "read_only": True,
                              "NEXT_ACTION": "Re-run with --topic <key>."},
                             ensure_ascii=False, indent=2))
        else:
            print(rule())
            print(f" KNOWLEDGE CATALOGUE -- {BANNER}")
            print(rule())
            for key in KNOWLEDGE_ORDER:
                entry = ICP_FILING_KNOWLEDGE[key]
                print(f"  {key:<40} {entry['title']}  [{entry['confidence']}]")
            print("\nSTATUS: OK")
            print("NEXT_ACTION: Re-run with --topic <key> for one topic, or --query \"<customer wording>\" "
                  "to rank topics and routing for a request.")
        return 0

    if args.topic and args.topic not in TOPIC_KEYS:
        return fail_open(args, "knowledge", f"unknown topic key '{args.topic[:40]}'.",
                         "KNOWLEDGE", "Re-run with --list-topics to see the catalogue.")

    if args.topic:
        keys = [args.topic]
    elif args.query:
        keys = [key for key, _score in search_topics(args.query)][:args.limit]
        if not keys:
            print("[WARN|DEGRADE] no topic matched the wording; printing the whole catalogue. "
                  "Never substitute model memory for this.", file=sys.stderr)
            keys = list(KNOWLEDGE_ORDER)
    else:
        keys = list(KNOWLEDGE_ORDER)

    routes = match_routes(args.query) if args.query else []
    payload: dict[str, Any] = {
        "mode": "knowledge", "read_only": True,
        "query": args.query or "", "topics": [topic_dict(k) for k in keys],
        "routes": [{"route": name, "may_say": ESCALATION_ROUTES[name]["skill_may_say"],
                    "route_to": ESCALATION_ROUTES[name]["route_to"],
                    "tickets": list(ESCALATION_ROUTES[name]["tickets"])} for name in routes],
        "entry_points": {name: (entry.get("url") or entry.get("console_path")
                                or "console navigation")
                         for name, entry in CUSTOMER_ENTRY_POINTS.items()},
        "blind_spots": list(API_BLIND_SPOTS),
    }

    if args.json:
        payload["STATUS"] = STATUS_OK
        payload["next_action"] = payload["NEXT_ACTION"] = (
            "Relay only the printed points, keep every confidence caveat, and send each "
            "filing-progress, commercial, DNS or in-guest request to the owner named in routes.")
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    lines = [rule(), f" ICP FILING RULES AND ROUTING -- {BANNER}", rule(),
             "  Every statement below is embedded ticket evidence or a fixed official entry",
             "  point. Nothing is answered from model memory."]
    for key in keys:
        lines += render_topic(key)
    if routes:
        lines.append("\n  Boundary and handoff for this request:")
        for name in routes:
            route = ESCALATION_ROUTES[name]
            lines += [f"    [{name}]",
                      f"      this skill may say : {route['skill_may_say']}",
                      f"      the work belongs to: {route['route_to']}",
                      f"      ticket evidence    : {', '.join(route['tickets'])}"]
    elif args.query:
        lines.append("\n  No escalation route keyword matched; the request stays inside this "
                     "skill's read-only scope.")
    lines.append("\n  Console entry points to show the customer (nothing is operated for them):")
    for name, entry in CUSTOMER_ENTRY_POINTS.items():
        where = entry.get("url") or entry.get("console_path") or "(console navigation)"
        lines.append(f"    - {name}: {entry['label']}  {where}")
    lines += [""] + blind_spot_lines()
    payload["_lines"] = lines
    return finish(payload, STATUS_OK,
                  "Relay only these points with their confidence caveats, and route every "
                  "filing-progress, commercial, DNS or in-guest request to the owner named "
                  "above instead of answering it here.", args.json)


# ===========================================================================
# Mode: selftest (offline; no API call, no credentials)
# ===========================================================================

def mode_selftest(args: argparse.Namespace) -> int:
    failures: list[str] = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            failures.append(name)

    now = datetime(2026, 9, 18, tzinfo=timezone.utc)
    base = {
        "InstanceId": "i-test000001", "RegionId": "cn-hangzhou", "Status": "Running",
        "InstanceChargeType": "PrePaid", "CreationTime": "2026-03-01T00:00Z",
        "ExpiredTime": "2026-12-31T15:59Z",
        "InternetMaxBandwidthOut": 5, "PublicIpAddress": {"IpAddress": ["47.0.0.1"]},
        "SecurityGroupIds": {"SecurityGroupId": ["sg-test0000001"]},
    }
    check("compliant subscription passes",
          evaluate_instance_eligibility(base, "cn-hangzhou", now)["verdict"] == "eligible")
    post = dict(base, InstanceChargeType="PostPaid", InternetMaxBandwidthOut=0,
                PublicIpAddress={"IpAddress": []}, ExpiredTime="2099-12-31T15:59Z")
    post_row = evaluate_instance_eligibility(post, "cn-hangzhou", now)
    check("pay-as-you-go without bandwidth fails both",
          post_row["verdict"] == "not_eligible"
          and "subscription_term" in post_row["missing_conditions"]
          and "public_bandwidth" in post_row["missing_conditions"])
    check("a non-mainland region fails condition 1",
          "mainland_region" in evaluate_instance_eligibility(
              dict(base, RegionId="cn-hongkong"), "cn-hongkong", now)["missing_conditions"])
    check("an unreadable term is never a silent pass",
          evaluate_instance_eligibility(dict(base, ExpiredTime=""), "cn-hangzhou", now)
          ["verdict"] == "needs_confirmation")
    # Official rule: the criterion is the accumulated PURCHASED length, not the
    # term still remaining. 12 months bought, 2 months left must never fail.
    twelve_bought_two_left = dict(base, CreationTime="2025-11-18T00:00Z",
                                  ExpiredTime="2026-11-18T00:00Z")
    short_left_row = evaluate_instance_eligibility(twelve_bought_two_left,
                                                   "cn-hangzhou", now)
    check("12 months purchased with 2 months left is not a term failure",
          "subscription_term" not in short_left_row["missing_conditions"]
          and short_left_row["checks"]["subscription_term"]["state"] == "pass"
          and short_left_row["verdict"] == "eligible")
    check("a 1-month-old subscription is unknown, never a fail",
          evaluate_instance_eligibility(dict(base, CreationTime="2026-08-20T00:00Z",
                                             ExpiredTime="2026-09-20T00:00Z"),
                                        "cn-hangzhou", now)
          ["checks"]["subscription_term"]["state"] == "unknown")
    check("the remaining term alone never fails the term condition",
          all(evaluate_instance_eligibility(
              dict(base, CreationTime="2025-01-01T00:00Z", ExpiredTime=expiry),
              "cn-hangzhou", now)["checks"]["subscription_term"]["state"] != "fail"
              for expiry in ("2026-09-20T00:00Z", "2026-10-18T00:00Z",
                             "2026-12-31T00:00Z")))
    check("a caller-supplied purchased length decides condition 2",
          evaluate_instance_eligibility(base, "cn-hangzhou", now, purchased_months=12)
          ["checks"]["subscription_term"]["state"] == "pass"
          and evaluate_instance_eligibility(base, "cn-hangzhou", now,
                                            purchased_months=1)
          ["checks"]["subscription_term"]["state"] == "fail")
    check("a missing creation time is unknown, not assumed",
          evaluate_instance_eligibility(dict(base, CreationTime=""), "cn-hangzhou", now)
          ["checks"]["subscription_term"]["state"] == "unknown")
    check("an EIP counts as the public path",
          evaluate_instance_eligibility(
              dict(base, InternetMaxBandwidthOut=0, PublicIpAddress={"IpAddress": []},
                   EipAddress={"IpAddress": "47.0.0.9"}), "cn-hangzhou", now)["verdict"] == "eligible")
    check("missing charge type is unknown, not assumed",
          evaluate_instance_eligibility({"InstanceId": "i-x"}, "cn-hangzhou", now)
          ["unconfirmed_conditions"] == ["subscription_term"])
    check("API timestamp parsing tolerates both shapes",
          parse_api_utc("2026-09-15T05:34Z") is not None
          and parse_api_utc("2026-09-18T02:32:07Z") is not None
          and parse_api_utc("not-a-date") is None)

    check("'all ports' range covers a web port", port_range_covers("-1/-1", 8080))
    check("exact range covers its port", port_range_covers("80/80", 80))
    check("exact range rejects another port", not port_range_covers("80/80", 443))
    check("range span covers inside", port_range_covers("1/1024", 80))
    check("empty range never matches", not port_range_covers("", 80))
    check("malformed range never matches", not port_range_covers("http", 80))

    open_80 = [{"Direction": "ingress", "IpProtocol": "TCP", "PortRange": "80/80",
                "Policy": "Accept", "Priority": 1, "SourceCidrIp": "0.0.0.0/0",
                "SecurityGroupRuleId": "sgr-open"}]
    check("public accept opens the port", evaluate_sg_port(open_80, 80)["verdict"] == "open_to_public")
    check("a private source is not public",
          evaluate_sg_port([dict(open_80[0], SourceCidrIp="10.0.0.0/8")], 80)["verdict"]
          == "limited_source_only")
    check("an empty group has no rule", evaluate_sg_port([], 443)["verdict"] == "no_rule")
    check("drop beats accept at equal priority",
          evaluate_sg_port([dict(open_80[0], Policy="Drop"), open_80[0]], 80)["verdict"]
          == "explicitly_dropped")
    check("a better-priority accept still opens the port",
          evaluate_sg_port([open_80[0], dict(open_80[0], Policy="Drop", Priority=2)], 80)
          ["verdict"] == "open_to_public")
    check("a UDP rule does not open a TCP port",
          evaluate_sg_port([dict(open_80[0], IpProtocol="UDP")], 80)["verdict"] == "no_rule")
    check("the ALL protocol covers web ports",
          evaluate_sg_port([dict(open_80[0], IpProtocol="ALL", PortRange="-1/-1")], 443)
          ["public_allowed"] is True)
    check("an egress rule is ignored for ingress",
          evaluate_sg_port([dict(open_80[0], Direction="egress")], 80)["verdict"] == "no_rule")

    closed = {"security_group_id": "sg-closed", "ports": [evaluate_sg_port([], 80)]}
    opened = {"security_group_id": "sg-open", "ports": [evaluate_sg_port(open_80, 80)]}
    check("one open group merges to allowed",
          overall_port_verdict([closed, opened], 80)["verdict"] == "allowed")
    check("no open group merges to a block",
          overall_port_verdict([closed], 80)["verdict"] == "no_inbound_allow_rule")
    check("a drop anywhere is reported as a drop",
          overall_port_verdict([closed, {"security_group_id": "sg-drop",
                                         "ports": [evaluate_sg_port(
                                             [dict(open_80[0], Policy="Drop")], 80)]}], 80)
          ["verdict"] == "blocked_by_drop_rule")

    check("declared symptoms route to the security-group path",
          matches_symptom("Chrome says ERR_CONNECTION_CLOSED after about 5 seconds")
          == ["err_connection_closed"])
    check("unrelated wording matches nothing", matches_symptom("the disk is full") == [])
    ranked = search_topics("no instance to select when binding the filing service code")
    check("topic ranking returns an ordered, valid list",
          bool(ranked) and all(key in TOPIC_KEYS for key, _ in ranked))
    check("commercial requests route out", "commercial-actions" in match_routes("please refund this purchase"))
    check("compliance material requests route out",
          "classified-protection-and-other-compliance" in match_routes("I need the classified protection certificate"))
    check("DNS edit requests route out", "dns-record-work" in match_routes("add an A record for the root domain"))
    check("in-guest requests route out", "in-guest-and-deployment-work" in match_routes("install IIS and .NET for me"))

    check("catalogue matches the knowledge base", set(KNOWLEDGE_ORDER) == set(ICP_FILING_KNOWLEDGE))
    for key, entry in ICP_FILING_KNOWLEDGE.items():
        check(f"{key}: carries ticket evidence", bool(entry["tickets"]))
        check(f"{key}: carries content", bool(entry["points"]))
        check(f"{key}: declares confidence",
              entry["confidence"] in ("transcript-verified", "summary-only", "partial-transcript"))
    check("input validation rejects option-like tokens",
          validate("--help", REGION_RE, "region") is None
          and validate("cn-hangzhou", REGION_RE, "region") == "cn-hangzhou")
    check("input validation rejects malformed ids",
          validate("i-bp1abc123", INSTANCE_ID_RE, "id") is not None
          and validate("47.0.0.1", IPV4_RE, "ip") is not None
          and validate("999.1.1.1", IPV4_RE, "ip") is None
          and validate("example.com", DOMAIN_RE, "domain") is not None)
    try:
        _cli.assert_read_only("ecs", "DescribeInstances")
        refused = False
        _cli.assert_read_only("ecs", "DeleteInstance")
    except CliError:
        refused = True
    check("the read-only gate refuses a mutating action", refused)

    print(rule())
    print(f" OFFLINE SELF-TEST -- {BANNER}")
    print(rule())
    print(f"  {0 if failures else 'no'} failures across the judgment functions "
          f"(no API call, no credential needed).")
    if failures:
        for name in failures:
            print(f"  FAILED: {name}")
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: Fix the judgment functions before running any query; a broken "
              "verdict here would corrupt every report.")
        return 1
    print("\nSTATUS: OK")
    print("NEXT_ACTION: Proceed to the eligibility, triage or knowledge mode.")
    return 0


# ===========================================================================
# Entry point
# ===========================================================================

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="icp_filing_check.py",
        description=(f"{SKILL_NAME}: read-only ICP filing server eligibility check, "
                     f"filed-site access triage and filing-rule guidance. No cloud "
                     f"resource is ever created, changed or deleted."),
        epilog=("APIs used (read-only, verified): "
                + ", ".join(f"{product}:{version}" for product, version in
                            sorted(API_VERSIONS.items()))
                + "."),
    )
    parser.add_argument("mode", choices=("eligibility", "triage", "knowledge", "selftest"),
                        help="eligibility = C1, triage = C2, knowledge = C3 + C4, "
                             "selftest = offline function checks")
    parser.add_argument("--region", default=None,
                        help="region id such as cn-hangzhou (required for triage)")
    parser.add_argument("--regions", default=None,
                        help="comma-separated regions for eligibility; default = the "
                             "built-in Chinese mainland scan list")
    parser.add_argument("--purchased-months", dest="purchased_months", type=float,
                        default=None,
                        help="eligibility only: the instance's cumulative purchased "
                             "length in months (original purchase plus renewals), read "
                             "by the customer in the billing center. When omitted the "
                             "script approximates it from CreationTime to ExpiredTime "
                             "and never fails an instance for a short remaining term.")
    parser.add_argument("--instance-id", default=None, help="ECS instance id (i-...)")
    parser.add_argument("--public-ip", default=None,
                        help="public IPv4 address of the web server (fixed public IP or EIP)")
    parser.add_argument("--domain", default=None,
                        help="domain the customer says is filed (drives the DNS guidance line)")
    parser.add_argument("--symptom", default=None,
                        help="browser error wording, e.g. err_connection_reset")
    parser.add_argument("--question", default=None,
                        help="customer's own wording; scanned for the declared symptom strings")
    parser.add_argument("--query", default=None,
                        help="knowledge mode: customer wording used to rank topics and routes")
    parser.add_argument("--topic", default=None,
                        help="knowledge mode: one topic key (see --list-topics)")
    parser.add_argument("--list-topics", action="store_true",
                        help="knowledge mode: print the topic catalogue")
    parser.add_argument("--limit", type=int, default=3,
                        help="knowledge mode: how many ranked topics to print (1-13)")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--timeout", type=int, default=60,
                        help="per-call timeout in seconds (5-600, default 60)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)

    args.limit = max(1, min(args.limit, len(KNOWLEDGE_ORDER)))
    if not 5 <= args.timeout <= 600:
        print("[WARN] --timeout outside 5..600 seconds; using the 60 second default",
              file=sys.stderr)
        args.timeout = 60
    if args.purchased_months is not None and not 0 < args.purchased_months <= 1200:
        print("[WARN] --purchased-months outside 0..1200 months; ignoring it and "
              "approximating from the instance data instead", file=sys.stderr)
        args.purchased_months = None

    if args.mode == "selftest":
        return mode_selftest(args)

    if args.mode == "knowledge":
        return mode_knowledge(args)

    _cli.check_cli_available()
    if args.mode == "eligibility":
        return mode_eligibility(args)

    if not (args.instance_id or args.public_ip):
        return fail_open(args, "triage",
                         "triage needs one of --instance-id or --public-ip to locate the server.",
                         "ACCESS TRIAGE",
                         "Ask the customer for the instance ID (or the public IP the domain "
                         "resolves to) and its region, then re-run.")
    return mode_triage(args)


if __name__ == "__main__":
    sys.exit(main())
