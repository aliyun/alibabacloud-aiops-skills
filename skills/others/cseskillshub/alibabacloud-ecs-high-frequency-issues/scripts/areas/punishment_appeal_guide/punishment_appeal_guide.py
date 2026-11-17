#!/usr/bin/env python3
"""
punishment_appeal_guide.py -- single entry point of the ECS Punishment Appeal
Guide skill (punishment / rectification / unblock-appeal symptom area, RO+G)
===========================================================================
SECURITY: This skill is strictly READ-ONLY. This script only invokes the four
whitelisted ECS Describe* queries (see _constants.API_WHITELIST) plus the
STS identity check, all through the shared CLI layer, to collect evidence.
It never runs commands inside the guest, never changes cloud resources, and
never reads, prints or forwards any credential: authentication is resolved
exclusively by the aliyun CLI default credential chain.

What it does:
  Step 1  verify the caller identity (account label for traceability only)
  Step 2  read-only evidence: instance existence / Status / platform lock
          reasons (DescribeInstances), lightweight status cross-check
          (DescribeInstanceStatus), security-group inventory and rules
          (DescribeSecurityGroups / DescribeSecurityGroupAttribute, with an
          optional port-coverage check)
  Step 3  classify the disposal into the 7-tier model (account / instance /
          URL-site / egress port / transaction risk control / judicial-
          regulatory / unverified claim)
  Step 4  render guidance ONLY (no side effects): remediation checklist
          pointer, appeal-material list, submission channel wording, review
          timeliness, fixed talks, handoffs
  Step 5  close with the STATUS: OK|DEGRADED|FAIL + NEXT_ACTION contract

Platform-side facts (punishment records, violating-content detail, appeal
progress) are NOT visible through any query available here; the report says
so explicitly instead of guessing.
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

import _cli
from _constants import (
    API_WHITELIST,
    BILLING_MITIGATION,
    DEGRADED_FALLBACK,
    DISPOSE_TIERS,
    ECS_PRODUCT,
    FIXED_TALKS,
    HANDOFF_RULES,
    INVISIBLE_SUMMARY,
    MATERIAL_CHECKLISTS,
    MAX_PAGES,
    MAX_SG_DETAIL_LOOKUPS,
    OFFICIAL_DOC_LINKS,
    PAGE_SIZE,
    REMEDIATION_BY_VIOLATION,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    STATUS_PAGE_SIZE,
)

_IPV4_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_INSTANCE_ID_RE = re.compile(r"^[A-Za-z0-9-]{6,64}$")

_TIER_PRIORITY = ["judicial", "transaction", "port", "account",
                  "instance", "url"]

# Authentication-failure code literals used for degradation hints: this
# skill only ever reports NoPermission / ImplicitDeny style codes.
_PERMISSION_CODES = ("nopermission", "implicitdeny", "accessdenied",
                     "notauthorized")


def _warn(errors: list[str], message: str) -> None:
    """Record a degradation line (per-query failures never abort the run)."""
    errors.append(message)
    print(f"[WARN] {message}", file=sys.stderr)


def _permission_issue(err_text: str) -> bool:
    low = (err_text or "").lower()
    return any(code in low for code in _PERMISSION_CODES)


# ---------------------------------------------------------------------------
# Step 1/2: evidence collection (all read-only, per-query degradation)
# ---------------------------------------------------------------------------

def fetch_instances(args, errors: list[str]) -> list[dict] | None:
    """DescribeInstances filtered by instance ids or public IP (or none).

    Returns the raw instance list, or None when the query itself failed.
    """
    params: dict = {"RegionId": args.region_id}
    if args.instance_ids:
        wanted = [t.strip() for t in args.instance_ids.split(",") if t.strip()]
        bad = [t for t in wanted if not _INSTANCE_ID_RE.match(t)]
        if bad:
            _warn(errors, "instance id(s) not in expected format: "
                          + ", ".join(bad)
                          + "; query proceeds with the raw value, verify the id")
        params["InstanceIds"] = json.dumps(wanted)
    elif args.public_ip:
        params["PublicIpAddresses"] = args.public_ip
    try:
        return _cli.paginate_page_number(
            ECS_PRODUCT, "DescribeInstances", params,
            ["Instances", "Instance"],
            region=args.region_id, profile=args.profile,
            page_size=PAGE_SIZE, max_pages=MAX_PAGES)
    except _cli.CliError as e:
        hint = " (permission gap: see references/ram-policies.md)" \
            if _permission_issue(str(e)) else ""
        _warn(errors, f"DescribeInstances failed{hint}: {e}")
        return None


def fetch_instance_statuses(args, instance_ids: list[str],
                            errors: list[str]) -> list[dict] | None:
    """DescribeInstanceStatus: by explicit ids when known, else region list.

    Returns the raw status list, or None when the query itself failed.
    """
    params: dict = {"RegionId": args.region_id}
    if instance_ids:
        for idx, iid in enumerate(instance_ids[:STATUS_PAGE_SIZE], start=1):
            params[f"InstanceId.{idx}"] = iid
    try:
        return _cli.paginate_page_number(
            ECS_PRODUCT, "DescribeInstanceStatus", params,
            ["InstanceStatuses", "InstanceStatus"],
            region=args.region_id, profile=args.profile,
            page_size=STATUS_PAGE_SIZE, max_pages=MAX_PAGES)
    except _cli.CliError as e:
        _warn(errors, f"DescribeInstanceStatus failed: {e}")
        return None


def fetch_security_groups(args, errors: list[str]) -> list[dict] | None:
    """DescribeSecurityGroups inventory for the region (None on failure)."""
    try:
        return _cli.paginate_page_number(
            ECS_PRODUCT, "DescribeSecurityGroups",
            {"RegionId": args.region_id},
            ["SecurityGroups", "SecurityGroup"],
            region=args.region_id, profile=args.profile,
            page_size=PAGE_SIZE, max_pages=MAX_PAGES)
    except _cli.CliError as e:
        _warn(errors, f"DescribeSecurityGroups failed: {e}")
        return None


def fetch_sg_permissions(args, security_group_ids: list[str],
                         errors: list[str]) -> dict[str, list[dict]]:
    """DescribeSecurityGroupAttribute rules per inspected security group.

    Partial results are kept; per-group failures are recorded and the run
    continues (the error-degradation discipline of this skill).
    """
    out: dict[str, list[dict]] = {}
    for sg_id in security_group_ids[:MAX_SG_DETAIL_LOOKUPS]:
        try:
            # DescribeSecurityGroupAttribute accepts no pagination parameters
            # (PageNumber/MaxResults/NextToken are all rejected by the CLI;
            # verified 2026-09-24) and returns the full rule set in one call.
            body = _cli.call(ECS_PRODUCT, "DescribeSecurityGroupAttribute",
                             {"RegionId": args.region_id, "SecurityGroupId": sg_id},
                             region=args.region_id, profile=args.profile)
            perms = ((body.get("Permissions") or {}).get("Permission") or [])
            out[sg_id] = [p for p in perms if isinstance(p, dict)]
        except _cli.CliError as e:
            _warn(errors, f"DescribeSecurityGroupAttribute({sg_id}) failed: {e}")
    if len(security_group_ids) > MAX_SG_DETAIL_LOOKUPS:
        _warn(errors,
              f"only the first {MAX_SG_DETAIL_LOOKUPS} security groups were "
              f"inspected; {len(security_group_ids) - MAX_SG_DETAIL_LOOKUPS} "
              "more were skipped by the lookup cap")
    return out


# ---------------------------------------------------------------------------
# Fact extraction helpers (defensive: only fields actually present are read)
# ---------------------------------------------------------------------------

def extract_lock_reasons(instance: dict) -> list[str]:
    """Collect platform lock reasons from OperationLocks (all shapes)."""
    locks: list[str] = []
    raw = instance.get("OperationLocks")
    if isinstance(raw, dict):
        raw = raw.get("LockReason")
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                val = str(item.get("LockReason", "")).strip()
            else:
                val = str(item).strip()
            if val:
                locks.append(val)
    direct = instance.get("LockReason")
    if isinstance(direct, str) and direct.strip():
        locks.append(direct.strip())
    return sorted(set(locks))


def instance_public_ips(instance: dict) -> list[str]:
    ips: list[str] = []
    pub = instance.get("PublicIpAddress")
    if isinstance(pub, dict):
        pub = pub.get("IpAddress")
    if isinstance(pub, list):
        ips.extend(str(x) for x in pub)
    eip = _cli.dig(instance, ["EipAddress", "IpAddress"])
    if isinstance(eip, str) and eip:
        ips.append(eip)
    return ips


def instance_sg_ids(instance: dict) -> list[str]:
    sgs = instance.get("SecurityGroupIds")
    if isinstance(sgs, dict):
        sgs = sgs.get("SecurityGroupId")
    if isinstance(sgs, list):
        return [str(x) for x in sgs]
    return []


def _port_range_covers(port_range: str, port: int) -> bool:
    """'from/to' semantics of security-group PortRange; '-1/-1' = all."""
    try:
        lo_s, _, hi_s = port_range.partition("/")
        lo, hi = int(lo_s), int(hi_s)
    except (ValueError, TypeError):
        return False
    if lo == -1 and hi == -1:
        return True
    return lo <= port <= hi


def port_covered(sg_permissions: dict[str, list[dict]], port: int,
                 protocol: str) -> tuple[bool, str]:
    """True when ANY ingress Accept rule covers the port for the protocol."""
    for sg_id, perms in sg_permissions.items():
        for perm in perms:
            direction = str(perm.get("Direction", "")).lower()
            if direction not in ("ingress", "in"):
                continue
            if str(perm.get("Policy", "")).lower() != "accept":
                continue
            proto = str(perm.get("IpProtocol", "")).lower()
            if protocol not in ("all", "any") and proto not in ("all", protocol):
                continue
            if _port_range_covers(str(perm.get("PortRange", "")), port):
                src = perm.get("SourceCidrIp") or perm.get("Ipv6SourceCidrIp") \
                    or perm.get("SourceGroupId") or "n/a"
                return True, (f"sg {sg_id}: {proto} port "
                              f"{perm.get('PortRange')} from {src}")
    return False, ""


def egress_mentions_port_25(sg_permissions: dict[str, list[dict]]) -> bool:
    """Whether any egress rule text mentions port 25 (factual echo only)."""
    for perms in sg_permissions.values():
        for perm in perms:
            if str(perm.get("Direction", "")).lower() in ("egress", "out") \
                    and "25" in str(perm.get("PortRange", "")):
                return True
    return False


# ---------------------------------------------------------------------------
# Step 3: tier classification (pure function, deterministic)
# ---------------------------------------------------------------------------

def classify_tier(symptom: str, notice_keyword: str,
                  facts: dict) -> tuple[str, list[str]]:
    """Return (tier_key, rationale). Never fabricates: every rationale line
    states which input or which API field it is based on."""
    rationale: list[str] = []
    haystack = (notice_keyword or "").lower()

    if symptom != "auto":
        rationale.append(f"forced by explicit --symptom {symptom!r}")
        return symptom, rationale

    scores: dict[str, int] = {}
    for key in _TIER_PRIORITY:
        hits = [cue for cue in DISPOSE_TIERS[key]["cues"] if cue in haystack]
        if hits:
            scores[key] = len(hits)
            rationale.append(
                f"notice keyword matched {key} cues: {', '.join(hits[:4])}")

    locks = facts.get("lock_reasons") or []
    running = facts.get("running_count", 0)
    total = facts.get("instance_count", 0)

    if locks:
        rationale.append("DescribeInstances reports platform lock reason(s): "
                         + ", ".join(locks))
    if total == 0 and facts.get("instances_query_ok"):
        rationale.append("no matching instance in this region and account "
                         "(verify region / account ownership first: "
                         "punishment records are account-scoped)")

    if not scores:
        if locks:
            rationale.append("defaulted from observed platform lock facts")
            return "instance", rationale
        if total and not running:
            rationale.append("instance(s) exist but none is Running and no "
                             "platform lock is recorded: a self-induced "
                             "stop cannot be excluded")
            return "unverified", rationale
        rationale.append("no notice text supplied and no adverse cloud "
                         "fact observed; the block claim stays unverified")
        return "unverified", rationale

    if max(scores.values()) == 1 and len(scores) > 1:
        # Ambiguous single-cue match: prefer tiers the cloud facts corroborate.
        if "instance" in scores and locks:
            scores["instance"] += 1
        if "url" in scores and running:
            scores["url"] += 1

    best = max(_TIER_PRIORITY, key=lambda k: scores.get(k, 0))
    rationale.append("most-cue-matched tier selected"
                     + ("" if len(scores) == 1 else
                        "; multiple tiers matched, confirm with the customer"))
    return best, rationale


def matched_handoffs(haystack: str) -> list[dict]:
    out = []
    low = (haystack or "").lower()
    for rule in HANDOFF_RULES:
        if any(token in low for token in rule["match"]):
            out.append(rule)
    return out


# ---------------------------------------------------------------------------
# Step 4: guidance assembly
# ---------------------------------------------------------------------------

def build_guidance(tier_key: str, facts: dict, extra_text: str) -> dict:
    tier = DISPOSE_TIERS[tier_key]
    materials = MATERIAL_CHECKLISTS[tier["materials_key"]]
    talks = [FIXED_TALKS[k] for k in tier["talk_keys"] if k in FIXED_TALKS]

    remediation_keys: list[str] = []
    if tier_key in ("url", "instance"):
        low = extra_text.lower()
        if any(w in low for w in ("mining", "miner", "pool")):
            remediation_keys.append("mining_outreach_alert")
        if any(w in low for w in ("dispute", "hijack", "false", "exercise")):
            remediation_keys.append("reporting_dispute")
        if any(w in low for w in ("attack", "outbound")):
            remediation_keys.append("outbound_attack")
        if not remediation_keys:
            remediation_keys.append("tampered_or_injected_content")
            remediation_keys.append("generic_missing_detail")
    elif tier_key == "account":
        remediation_keys.append("outbound_attack")

    docs = []
    if tier_key == "account":
        docs = [OFFICIAL_DOC_LINKS["stop_an_instance"],
                OFFICIAL_DOC_LINKS["instance_faq"],
                OFFICIAL_DOC_LINKS["workbench_system_management"]]
    elif tier_key in ("url", "instance"):
        docs = [OFFICIAL_DOC_LINKS["workbench_system_management"]]

    return {
        "tier": tier_key,
        "tier_label": tier["label"],
        "api_evidence_wording": tier["api_evidence"],
        "invisible": tier["invisible"],
        "path": tier["path"],
        "materials": materials,
        "talks": talks,
        "remediation_keys": remediation_keys,
        "billing_mitigation": BILLING_MITIGATION if tier_key == "account" else "",
        "official_docs": docs,
        "handoffs": matched_handoffs(extra_text),
    }


def decide_next_action(tier_key: str, status: str) -> str:
    if status == STATUS_FAIL:
        return ("restore read-only query access (configure the default "
                "credential chain / grant the actions listed in "
                "references/ram-policies.md), then re-run; if impossible, "
                "collect the original notice text and open a manual ticket")
    if status == STATUS_DEGRADED:
        return DEGRADED_FALLBACK
    if tier_key == "unverified":
        return ("ask the customer HOW the block was judged and request the "
                "original notice; without it do not endorse the claim, then "
                "refer to the handoff map if the issue is plain reachability")
    if tier_key in ("instance", "url"):
        return ("deliver the remediation checklist and the appeal-material "
                "list; after the customer submits the appeal and it passes, "
                "re-run this script to verify the instance status returned "
                "to Running (closing evidence)")
    if tier_key == "transaction":
        return ("state the exact accepted verification material "
                "(person-held ID photo) BEFORE the customer submits, then "
                "point to the appeal entry named in the notice")
    if tier_key == "account":
        return ("quote the release timestamp from the notice, deliver the "
                "billing-mitigation guidance for pay-as-you-go instances, "
                "and route an appeal through the manual channel if the "
                "customer disputes the freeze")
    if tier_key == "port":
        return ("hand off per the guidance above; do not collect appeal "
                "materials in this skill")
    return "deliver the fixed talk verbatim; run no further queries for this request"


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def render_text(args, evidence: dict, rationale: list[str],
                guidance: dict, status: str, next_action: str) -> None:
    line = "=" * 68
    print(line)
    print(" ECS PUNISHMENT & APPEAL GUIDE - read-only triage report")
    print(line)
    print(f" Account label : {evidence['account_label'] or 'unresolved (identity check degraded)'}")
    print(f" Region queried: {args.region_id} (user-provided)")
    print(f" Queries OK    : {', '.join(evidence['queries_ok']) or 'none'}")
    if evidence["queries_failed"]:
        print(f" Queries failed: {', '.join(evidence['queries_failed'])}")
    if evidence["queries_skipped"]:
        print(f" Queries skipped: {', '.join(evidence['queries_skipped'])}")

    print("")
    print("--- Instance facts (DescribeInstances / DescribeInstanceStatus) ---")
    if not evidence["instances"]:
        print("  no instance matched the given filter in this region/account")
    for inst in evidence["instances"]:
        print(f"  {inst['InstanceId']} | status={inst['Status']} | "
              f"charge={inst['InstanceChargeType']} | "
              f"public-ips={','.join(inst['PublicIps']) or 'none'} | "
              f"sgs={','.join(inst['SecurityGroupIds']) or 'none'}")
        if inst["LockReasons"]:
            print(f"      platform lock reason(s): {', '.join(inst['LockReasons'])}")
    if evidence["statuses"]:
        pairs = ", ".join(f"{s.get('InstanceId')}:{s.get('Status')}"
                          for s in evidence["statuses"][:20])
        print(f"  DescribeInstanceStatus: {pairs}")

    print("")
    print("--- Security-group facts (DescribeSecurityGroups / ...Attribute) ---")
    print(f"  {evidence['sg_count']} security group(s) in region; "
          f"inspected: {', '.join(evidence['sg_inspected']) or 'none'}")
    for sg_id, rule_count in evidence["sg_rule_counts"].items():
        print(f"  {sg_id}: {rule_count} rule(s)")
    if evidence["port_check"]:
        print(f"  port check: {evidence['port_check']}")
    if evidence["port25_note"]:
        print(f"  note: {evidence['port25_note']}")

    print("")
    print("--- Classification ---")
    print(f"  Tier: {guidance['tier_label']}")
    for why in rationale:
        print(f"  - {why}")
    print(f"  What the queries can/cannot prove: {guidance['api_evidence_wording']}")

    print("")
    print("--- Guidance (customer-executed; this skill changes nothing) ---")
    print(f"  Path: {guidance['path']}")
    if guidance["remediation_keys"]:
        print("  Remediation checklists (full steps in "
              "references/punishment-appeal-guide__remediation-checklist.md):")
        for key in guidance["remediation_keys"]:
            print(f"    * {REMEDIATION_BY_VIOLATION[key]['title']}")
        print("    (hard rule: manual snapshot/backup BEFORE any cleanup or change)")
    print(f"  Appeal materials ({guidance['materials']['title']}):")
    for item in guidance["materials"]["items"]:
        print(f"    - {item}")
    print(f"  Materials note: {guidance['materials']['note']}")
    print("  Talks:")
    for talk in guidance["talks"]:
        print(f"    * {talk}")
    if guidance["billing_mitigation"]:
        print(f"  Billing mitigation: {guidance['billing_mitigation']}")
    if guidance["official_docs"]:
        print("  Official docs (help.aliyun.com):")
        for url in guidance["official_docs"]:
            print(f"    - {url}")
    if guidance["handoffs"]:
        print("  Handoffs (references/punishment-appeal-guide__handoff-map.md):")
        for rule in guidance["handoffs"]:
            print(f"    * {rule['say']} -> {rule['target']}")

    print("")
    print(f"--- Boundary ---\n  {INVISIBLE_SUMMARY}")

    print("")
    print("--- Graceful degradation log ---")
    if evidence["errors"]:
        for err in evidence["errors"]:
            print(f"  [WARN] {err}")
    else:
        print("  none")

    print("")
    print(f"STATUS: {status}")
    print(f"NEXT_ACTION: {next_action}")


def render_json(payload: dict) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=False))


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="punishment_appeal_guide.py",
        description="Read-only triage and manual guidance for ECS "
                    "punishment / rectification / unblock-appeal cases. "
                    "Executes ONLY whitelisted Describe* queries: "
                    + ", ".join(API_WHITELIST) + ".",
    )
    parser.add_argument("--region-id", default=None,
                        help="Required. ECS region id, e.g. cn-hangzhou")
    parser.add_argument("--instance-ids", default=None,
                        help="Comma-separated ECS instance ids to check")
    parser.add_argument("--public-ip", default=None,
                        help="Public IP of the claimed affected instance")
    parser.add_argument("--security-group-id", default=None,
                        help="Force-inspect this security group id in addition "
                             "to the ones attached to matched instances")
    parser.add_argument("--symptom", default="auto",
                        choices=["auto", "account", "instance", "url", "port",
                                 "transaction", "judicial", "unverified"],
                        help="Disposal tier hint from the customer wording; "
                             "'auto' classifies from the notice keyword and "
                             "API facts (default, auto-filled and declared)")
    parser.add_argument("--notice-keyword", default="",
                        help="Key wording copied from the violation notice "
                             "(e.g. 'illegal content', 'security management "
                             "policy', 'force stopped')")
    parser.add_argument("--check-port", type=int, default=None,
                        help="When set, verify an ingress allow rule covers "
                             "this port (1-65535) on the inspected groups")
    parser.add_argument("--check-protocol", default="tcp",
                        choices=["tcp", "udp", "icmp", "all"],
                        help="Protocol for --check-port (default tcp)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true",
                        help="Machine-readable JSON output")
    args = parser.parse_args(argv)

    if not args.region_id:
        print("[ERROR] --region-id is required (every whitelisted query is "
              "region-scoped).", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: ask the customer which region the instance is in; "
              "if unknown, the notice or the console resource list carries it")
        sys.exit(1)
    if args.public_ip and not _IPV4_RE.match(args.public_ip):
        print("[ERROR] --public-ip is not a valid IPv4 address.",
              file=sys.stderr)
        sys.exit(2)
    if args.check_port is not None and not (1 <= args.check_port <= 65535):
        print("[ERROR] --check-port must be between 1 and 65535.",
              file=sys.stderr)
        sys.exit(2)
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    _cli.check_cli_available()

    errors: list[str] = []
    queries_ok: list[str] = []
    queries_failed: list[str] = []
    queries_skipped: list[str] = []

    # Step 1: identity (traceability label only; failure degrades, never aborts)
    uid = _cli.resolve_account_id(profile=args.profile)
    if uid:
        account_label = f"account ending {uid[-4:]}"
    else:
        account_label = ""
        _warn(errors, "caller identity unresolved: the default credential "
                      "chain may be unavailable or restricted (an "
                      "account-level action itself can restrict even read "
                      "access); evidence below may be partial")

    # Step 2: read-only evidence
    instances_raw = fetch_instances(args, errors)
    if instances_raw is None:
        queries_failed.append("DescribeInstances")
        instances_raw = []
    else:
        queries_ok.append("DescribeInstances")

    instances: list[dict] = []
    for item in instances_raw:
        if not isinstance(item, dict):
            continue
        instances.append({
            "InstanceId": str(item.get("InstanceId", "")),
            "Status": str(item.get("Status", "")),
            "InstanceChargeType": str(item.get("InstanceChargeType", "")),
            "PublicIps": instance_public_ips(item),
            "SecurityGroupIds": instance_sg_ids(item),
            "LockReasons": extract_lock_reasons(item),
        })

    id_set = sorted({i["InstanceId"] for i in instances if i["InstanceId"]})
    statuses_raw = fetch_instance_statuses(args, id_set, errors)
    if statuses_raw is None:
        queries_failed.append("DescribeInstanceStatus")
        statuses: list[dict] = []
    else:
        queries_ok.append("DescribeInstanceStatus")
        statuses = statuses_raw

    sg_groups_raw = fetch_security_groups(args, errors)
    if sg_groups_raw is None:
        queries_failed.append("DescribeSecurityGroups")
        sg_groups: list[dict] = []
    else:
        queries_ok.append("DescribeSecurityGroups")
        sg_groups = sg_groups_raw

    target_sgs: list[str] = []
    if args.security_group_id:
        target_sgs.append(args.security_group_id)
    for inst in instances:
        for sg in inst["SecurityGroupIds"]:
            if sg not in target_sgs:
                target_sgs.append(sg)
    if not target_sgs and sg_groups:
        target_sgs = [str(g.get("SecurityGroupId", "")) for g in sg_groups
                      if isinstance(g, dict) and g.get("SecurityGroupId")]

    failed_before = len(errors)
    sg_perms = fetch_sg_permissions(args, target_sgs, errors)
    if not target_sgs:
        queries_skipped.append("DescribeSecurityGroupAttribute "
                               "(no security group to inspect)")
    elif len(errors) > failed_before and not sg_perms:
        queries_failed.append("DescribeSecurityGroupAttribute")
    elif sg_perms:
        queries_ok.append("DescribeSecurityGroupAttribute")

    port_check = ""
    if args.check_port and sg_perms:
        covered, rule_text = port_covered(sg_perms, args.check_port,
                                          args.check_protocol)
        if covered:
            port_check = (f"{args.check_protocol}/{args.check_port} COVERED "
                          f"by an ingress allow rule -> {rule_text}")
        else:
            port_check = (f"{args.check_protocol}/{args.check_port} NOT "
                          "covered by any ingress allow rule -> a plain "
                          "configuration gap explains the outage; hand it to "
                          "the access-block area (references/punishment-appeal-guide__handoff-map.md)")
    elif args.check_port:
        port_check = (f"{args.check_protocol}/{args.check_port} not evaluated: "
                      "no security-group rule evidence available")

    port25_note = ""
    if sg_perms and egress_mentions_port_25(sg_perms):
        port25_note = ("an egress rule mentioning port 25 was observed in the "
                       "security-group data; the platform-wide outbound "
                       "port-25 mail policy is separate and owned by the "
                       "email-sending area")

    all_locks = sorted({lock for inst in instances
                        for lock in inst["LockReasons"]})
    running_count = sum(1 for i in instances if i["Status"] == "Running")

    facts = {
        "instance_count": len(instances),
        "running_count": running_count,
        "lock_reasons": all_locks,
        "instances_query_ok": "DescribeInstances" in queries_ok,
        "sg_count": len(sg_groups),
    }

    # Step 3: classification
    tier_key, rationale = classify_tier(args.symptom, args.notice_keyword, facts)
    extra_text = " ".join([args.notice_keyword or "", args.symptom or ""])
    guidance = build_guidance(tier_key, facts, extra_text)

    # Step 4/5: status + output
    if not queries_ok:
        status = STATUS_FAIL
    elif queries_failed or not instances or not uid:
        status = STATUS_DEGRADED
    else:
        status = STATUS_OK
    next_action = decide_next_action(tier_key, status)

    evidence = {
        "account_label": account_label,
        "instances": instances,
        "statuses": statuses,
        "sg_count": len(sg_groups),
        "sg_inspected": sorted(sg_perms.keys()),
        "sg_rule_counts": {k: len(v) for k, v in sg_perms.items()},
        "port_check": port_check,
        "port25_note": port25_note,
        "queries_ok": queries_ok,
        "queries_failed": queries_failed,
        "queries_skipped": queries_skipped,
        "errors": errors,
    }

    if args.json:
        render_json({
            "account_label": account_label,
            "region": args.region_id,
            "auto_filled": {
                "symptom": args.symptom,
                "declared": ("--symptom defaulted to 'auto' (classified from "
                             "the notice keyword and API facts)"
                             if args.symptom == "auto" else
                             "--symptom explicitly provided"),
            },
            "evidence": evidence,
            "classification": {"tier": tier_key,
                               "label": guidance["tier_label"],
                               "rationale": rationale},
            "guidance": guidance,
            "boundary": INVISIBLE_SUMMARY,
            "degradation_log": errors,
            "status": status,
            "next_action": next_action,
        })
    else:
        render_text(args, evidence, rationale, guidance, status, next_action)

    return 0 if status in (STATUS_OK, STATUS_DEGRADED) else 1


if __name__ == "__main__":
    sys.exit(main())
