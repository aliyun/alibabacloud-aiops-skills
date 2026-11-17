#!/usr/bin/env python3
"""
transfer_guide.py -- ECS cross-account transfer & entity-change guide (entry)
============================================================================
Single entry point for the skill. The agent MUST drive every diagnosis and
every guide through THIS script (argparse modes below); assembling raw
`aliyun` CLI commands by hand is prohibited by SKILL.md.

SECURITY / PERMISSION MODEL:
  * Inventory and status evidence uses query-class actions only
    (DescribeInstances / DescribeInstanceStatus / DescribeAvailableResource /
    GetCallerIdentity); they run automatically because none of them changes
    any resource.
  * The ONLY action with a write effect is the snapshot backup
    (CreateSnapshot, parameters DiskId and RegionId required). It is
    confirmation-gated:
    this script refuses to invoke it unless --confirm yes is passed, and the
    agent must first tell the user what runs, its cost impact, and its
    reversibility.
  * No other cloud mutation is ever issued or scripted here -- destructive
    or commercial steps are printed as human guidance only.
  * Credentials: none are ever read, printed, cached or passed by this
    script; the aliyun CLI default credential chain resolves everything.

Modes (mutually exclusive):
  --assess                K1 feasibility verdict (pure logic on facts)
  --precheck              K2 instance-side condition checklist (live queries)
  --create-snapshot       gated snapshot backup before an OS replacement
  --guide TOPIC           K3 image-migration path / K4 post-transfer list /
                          K5 account & related-product rules
  --blocker TEXT          K6 console blocker lookup (pasted error wording)
  --handoff TEXT          K7 route out-of-scope symptoms to sibling skills
  --list-links            official help links used by this skill (evidence set)

Output contract: a report (or --json) ending with
  STATUS: OK|DEGRADED|FAIL
  NEXT_ACTION: <single next step>
Exit codes: 0 = OK/DEGRADED, 1 = FAIL, 2 = argparse usage error only.
"""

from __future__ import annotations

import argparse
import datetime
import ipaddress
import json
import re
import sys
import time

import _cli
import _constants as C

_START = time.monotonic()

# ---------------------------------------------------------------------------
# Input validation (strict; nothing user-supplied reaches a shell)
# ---------------------------------------------------------------------------

REGION_RE = re.compile(r"^[a-z0-9-]{4,32}$")
ZONE_RE = re.compile(r"^[a-z0-9-]{4,32}$")
INSTANCE_RE = re.compile(r"^i-[a-z0-9]{6,40}$")
DISK_RE = re.compile(r"^d-[a-z0-9-]{6,40}$")
TYPE_RE = re.compile(r"^ecs\.[A-Za-z0-9.\-]{2,60}$")
SNAPSHOT_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9\-_.:]{1,127}$")

YES_NO_UNKNOWN = ("yes", "no", "unknown")
ACCOUNT_TYPES = ("individual", "enterprise", "unknown")
ENTITY_RELATIONS = ("same", "different", "unknown")


def remaining_budget() -> float:
    """Seconds left of the overall run budget."""
    return C.RUN_BUDGET_SECONDS - (time.monotonic() - _START)


def _budget_result():
    if remaining_budget() <= 5:
        return {
            "status": "DEGRADED",
            "exit_code": 1,
            "title": "Run budget exhausted",
            "summary": ("The 300-second run budget was reached before this "
                        "mode finished its queries."),
            "findings": [],
            "next_action": "re-run the same mode (fresh evidence window)",
        }
    return None


def _bad(title: str, summary: str, next_action: str):
    return {
        "status": "FAIL",
        "exit_code": 1,
        "title": title,
        "summary": summary,
        "findings": [],
        "next_action": next_action,
    }


# ---------------------------------------------------------------------------
# K1 -- pure decision function (unit-testable, no model judgement)
# ---------------------------------------------------------------------------

_VERDICT_ORDER = {"TRANSFER_NOT_ELIGIBLE": 2, "NEEDS_MANUAL_REVIEW": 1,
                  "TRANSFER_ELIGIBLE": 0}


def assess_eligibility(source_type: str, target_type: str,
                       entity_relation: str, cross_region: str,
                       campaign: str, reseller: str) -> dict:
    """Return a three-way transfer feasibility verdict with reasons.

    Pure function over the collected facts; the fact table itself lives in
    _constants.DIRECTION_MATRIX / OVERRIDE_REASONS.
    """
    reasons = []
    caveats = []
    verdict = None

    def escalate(v: str) -> None:
        nonlocal verdict
        if verdict is None or _VERDICT_ORDER[v] > _VERDICT_ORDER[verdict]:
            verdict = v

    key = f"{source_type}->{target_type}"
    rule = C.DIRECTION_MATRIX.get(key)
    if rule is None:
        escalate("NEEDS_MANUAL_REVIEW")
        reasons.append(
            "A real-name verification type is missing or unknown: collect "
            + C.ASSESS_INPUT_HELP
        )
    else:
        reasons.append(f"Direction rule ({source_type} -> {target_type}): "
                       f"{rule['rule']} [evidence: {rule['evidence']}]")
        if rule.get("caveat"):
            caveats.append(rule["caveat"])
        base = rule["verdict"]
        if key == "enterprise->enterprise":
            if entity_relation == "different":
                escalate("TRANSFER_NOT_ELIGIBLE")
                reasons.append(C.OVERRIDE_REASONS["entity_relation_different"]["text"])
            elif entity_relation == "unknown":
                escalate("NEEDS_MANUAL_REVIEW")
                reasons.append(C.OVERRIDE_REASONS["entity_relation_unknown"]["text"])
            else:
                escalate("TRANSFER_ELIGIBLE")
        elif base == "ELIGIBLE_WITH_CONDITIONS":
            escalate("TRANSFER_ELIGIBLE")
        elif base == "LIKELY_ELIGIBLE":
            escalate("TRANSFER_ELIGIBLE")
            caveats.append(
                "Individual-to-individual support is weak evidence: state "
                "it as 'expected to pass the standard review', never as a "
                "guarantee.")
        elif base == "LIKELY_NOT_ELIGIBLE":
            escalate("TRANSFER_NOT_ELIGIBLE")
            caveats.append(
                "Enterprise-to-individual non-support is summary-only "
                "evidence: hedge with 'confirm against the official "
                "transfer-limitations section' before rejecting.")

    if cross_region == "yes":
        escalate("TRANSFER_NOT_ELIGIBLE")
        reasons.append(C.OVERRIDE_REASONS["cross_region"]["text"])
    elif cross_region == "unknown":
        caveats.append(C.OVERRIDE_REASONS["cross_region"]["text"] +
                       " (verify the instance and destination vSwitch share "
                       "region AND zone)")

    if campaign == "yes":
        escalate("TRANSFER_NOT_ELIGIBLE")
        reasons.append(C.OVERRIDE_REASONS["campaign_yes"]["text"])
    elif campaign == "unknown":
        escalate("NEEDS_MANUAL_REVIEW")
        reasons.append(C.OVERRIDE_REASONS["campaign_unknown"]["text"])

    if reseller == "yes":
        escalate("NEEDS_MANUAL_REVIEW")
        reasons.append(C.OVERRIDE_REASONS["reseller_yes"]["text"])
    elif reseller == "unknown":
        caveats.append("Ask whether either account is a distribution "
                       "(reseller) customer; that relationship cannot be "
                       "queried here.")

    verdict = verdict or "NEEDS_MANUAL_REVIEW"
    if verdict == "TRANSFER_ELIGIBLE":
        next_action = ("run --precheck for the instance-side facts, then "
                       "hand the customer the console transfer flow "
                       "(see references/transfer-conditions.md); give the "
                       "post-transfer list (--guide post-transfer)")
    elif verdict == "TRANSFER_NOT_ELIGIBLE":
        next_action = ("explain the blocking reason with its doc anchor, "
                       "then run --guide image-migration for the fallback "
                       "path (snapshot-first rule applies)")
    else:
        next_action = ("collect the missing facts from the customer; if the "
                       "verified entity or campaign status stays unclear, "
                       "open a ticket with instance id + both account UIDs")
    return {
        "verdict": verdict,
        "reasons": reasons,
        "caveats": caveats,
        "next_action": next_action,
    }


def cmd_assess(args) -> dict:
    missing = []
    if args.source_type == "unknown":
        missing.append("--source-type")
    if args.target_type == "unknown":
        missing.append("--target-type")
    out = assess_eligibility(
        source_type=args.source_type,
        target_type=args.target_type,
        entity_relation=args.entity_relation,
        cross_region=args.cross_region,
        campaign=args.campaign_instance,
        reseller=args.reseller_account,
    )
    findings = [f"Verdict: {out['verdict']}"]
    findings += [f"Reason: {r}" for r in out["reasons"]]
    findings += [f"Caveat: {c}" for c in out["caveats"]]
    findings.append("Timing: " + C.TRANSFER_TIMING["typical"])
    findings.append("Note: " + C.CONSOLE_FLOW_NOTE)
    status = "OK"
    if missing and out["verdict"] == "NEEDS_MANUAL_REVIEW":
        status = "DEGRADED"
        findings.append("Still missing: " + ", ".join(missing) + " "
                        + C.ASSESS_INPUT_HELP)
    return {
        "status": status,
        "exit_code": 0,
        "title": "K1 transfer feasibility verdict",
        "summary": (f"Verdict for {args.source_type} -> {args.target_type} "
                    f"(entity relation: {args.entity_relation}, cross-region:"
                    f" {args.cross_region}, campaign: {args.campaign_instance}"
                    f", reseller: {args.reseller_account}): {out['verdict']}"),
        "findings": findings,
        "next_action": out["next_action"],
        "verdict": out["verdict"],
    }


# ---------------------------------------------------------------------------
# K2 -- live instance-side pre-check
# ---------------------------------------------------------------------------

def _first(d: dict, *keys, default=""):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def _instance_lines(inst: dict) -> str:
    iid = _first(inst, "InstanceId", default="?")
    status = _first(inst, "Status", default="?")
    zone = _first(inst, "ZoneId", default="?")
    charge = _first(inst, "InstanceChargeType", default="?")
    vpc = _first(inst, "VpcId", default="(classic/none)")
    vsw = _first(inst, "VSwitchId", default="(none)")
    sg_ids = _first(_first(inst, "SecurityGroupIds", default={}),
                    "SecurityGroupId", default=[])
    pub = _first(_first(inst, "PublicIpAddress", default={}),
                 "IpAddress", default=[])
    eip_block = _first(inst, "EipAddress", default={}) or {}
    eip_ip = _first(eip_block, "IpAddress", default="")
    keypair = _first(inst, "KeyPairName", default="")
    os_type = _first(inst, "OSName", default="")
    return (
        f"instance {iid}: status={status} zone={zone} charge={charge} "
        f"os={os_type or '?'} vpc={vpc} vswitch={vsw} "
        f"security_groups={','.join(sg_ids) if sg_ids else '(none)'} "
        f"public_ip={','.join(pub) if pub else '(none)'} "
        f"eip={eip_ip or '(none)'} keypair={keypair or '(none)'}"
    )


def cmd_precheck(args) -> dict:
    if args.region_id is None:
        return _bad("K2 pre-transfer check",
                    "--region-id is required (ECS queries are regional; "
                    "region is never guessed).",
                    "ask the customer which region the instance lives in, "
                    "then re-run with --region-id <region>")
    if not REGION_RE.match(args.region_id):
        return _bad("K2 pre-transfer check",
                    f"--region-id '{args.region_id}' is not a valid region "
                    "token.", "fix the region id (e.g. cn-hangzhou)")
    if args.instance_id and not INSTANCE_RE.match(args.instance_id):
        return _bad("K2 pre-transfer check",
                    f"--instance-id '{args.instance_id}' is not a valid "
                    "instance id.", "fix the instance id (i-...)")
    public_ips = None
    if args.public_ip:
        try:
            ipaddress.ip_address(args.public_ip)
        except ValueError:
            return _bad("K2 pre-transfer check",
                        f"--public-ip '{args.public_ip}' is not a valid "
                        "IPv4/IPv6 address.", "fix the public IP value")
        public_ips = [args.public_ip]
    budget = _budget_result()
    if budget:
        budget["title"] = "K2 pre-transfer check"
        return budget

    errors: list[str] = []
    findings: list[str] = []

    uid = _cli.resolve_account_id(profile=args.profile)
    if uid:
        findings.append(f"Current credential account UID: {uid} (verified "
                        "against this account only; the other account's "
                        "resources are not visible from here)")
    else:
        errors.append("sts:GetCallerIdentity unavailable -> UID not shown; "
                      "identity failure degrades traceability only")

    params = {}
    if args.instance_id:
        params["InstanceIds"] = [args.instance_id]
    if public_ips:
        params["PublicIpAddresses"] = public_ips
    try:
        instances = _cli.describe_instances(args.region_id, params,
                                            profile=args.profile)
    except _cli.CliError as e:
        return _bad("K2 pre-transfer check",
                    f"DescribeInstances failed: {e}",
                    "check the credential's query permission against "
                    "references/ram-policies.md (expect NoPermission / "
                    "ImplicitDeny codes), then re-run")

    if not instances:
        res = _bad("K2 pre-transfer check",
                   "The query succeeded but returned no instance in "
                   + args.region_id + (f" for {args.instance_id or args.public_ip}"
                                       if (args.instance_id or args.public_ip)
                                       else ""),
                   "confirm the region and the account (run sts_token.py "
                   "in each account); list without filters to see what the "
                   "credential can see")
        res["findings"] = ["DescribeInstances returned zero instances"]
        return res

    # Instance state (best effort, one call when an id filter was given).
    if args.instance_id:
        try:
            body = _cli.call("ecs", "DescribeInstanceStatus",
                             {"RegionId": args.region_id,
                              "InstanceId.1": args.instance_id},
                             region=args.region_id, profile=args.profile,
                             timeout=int(min(C.API_TIMEOUT_SECONDS,
                                             max(5, remaining_budget()))))
            states = _first(_first(body, "InstanceStatuses", default={}),
                            "InstanceStatus", default=[])
            for s in states or []:
                findings.append(f"Status of {_first(s, 'InstanceId')}:"
                                f" {_first(s, 'Status')}")
        except _cli.CliError as e:
            errors.append(f"DescribeInstanceStatus degraded: {e}")

    # Destination-zone sellability pre-check (the 0002HRZLAX blocker class).
    if args.target_zone:
        if not ZONE_RE.match(args.target_zone):
            errors.append(f"--target-zone '{args.target_zone}' invalid; "
                          "zone pre-check skipped")
        else:
            zparams = {"RegionId": args.region_id,
                       "DestinationResource": "InstanceType",
                       "ZoneId": args.target_zone}
            if args.target_instance_type:
                if TYPE_RE.match(args.target_instance_type):
                    zparams["InstanceType"] = args.target_instance_type
                else:
                    errors.append("--target-instance-type invalid; omitted "
                                  "from the sellability query")
            if args.charge_type in ("PrePaid", "PostPaid"):
                zparams["InstanceChargeType"] = args.charge_type
            try:
                body = _cli.call("ecs", "DescribeAvailableResource",
                                 zparams, region=args.region_id,
                                 profile=args.profile,
                                 timeout=int(min(C.API_TIMEOUT_SECONDS,
                                                 max(5, remaining_budget()))))
                zones = _first(_first(body, "AvailableZones", default={}),
                               "AvailableZone", default=[])
                hit = [z for z in (zones or [])
                       if _first(z, "ZoneId") == args.target_zone]
                if hit:
                    z0 = hit[0]
                    findings.append(
                        f"Target zone {args.target_zone}: "
                        f"status={_first(z0, 'Status')} "
                        f"category={_first(z0, 'StatusCategory')} "
                        "(sellability for the transfer wizard)")
                else:
                    findings.append(
                        f"Target zone {args.target_zone} was NOT returned "
                        "as sellable for this resource selection -- pick "
                        "another zone / instance type before transferring")
            except _cli.CliError as e:
                errors.append(f"DescribeAvailableResource degraded: {e}")

    # Render the instance rows (cap the human report, keep JSON complete).
    for inst in instances[:C.MAX_INSTANCE_REPORT]:
        findings.append(_instance_lines(inst))
    if len(instances) > C.MAX_INSTANCE_REPORT:
        findings.append(f"({len(instances) - C.MAX_INSTANCE_REPORT} further "
                        "instances omitted from this report; included in "
                        "--json)")

    # Map the facts onto the five hard conditions.
    zones_needed = sorted({_first(i, "ZoneId", default="?")
                           for i in instances})
    vpcs = sorted({_first(i, "VpcId", default="(classic/none)")
                   for i in instances})
    findings.append(
        "Condition 1 (same verified entity): not queryable -- answer it "
        "via --assess inputs / Account Center self-check.")
    findings.append(
        f"Condition 2 (network): the transfer wizard's vSwitch and "
        f"security group must live in VPC {vpcs} and in the instance zone "
        f"{zones_needed}; cross-region transfer never works.")
    findings.append(
        "Condition 3 (balance): if the target account has pay-as-you-go "
        "resources, its owner must confirm available balance > 100 CNY "
        "in Billing Center (not queryable here).")
    blocked = []
    for inst in instances:
        iid = _first(inst, "InstanceId", default="?")
        eip = _first(_first(inst, "EipAddress", default={}) or {},
                     "IpAddress", default="")
        kp = _first(inst, "KeyPairName", default="")
        if eip:
            blocked.append(f"{iid} has bound EIP {eip}")
        if kp:
            blocked.append(f"{iid} uses key pair {kp}")
    if blocked:
        findings.append("Condition 4 (unbind first): " + "; ".join(blocked)
                        + " -- detach these before starting the transfer.")
    else:
        findings.append("Condition 4 (unbind first): no EIP / key-pair "
                        "bindings seen on the listed instances.")
    findings.append(
        "Condition 5 (instance limits): campaign / discount purchase "
        "status is not queryable -- answer via --assess or a backend "
        "ticket.")

    status = "OK" if not errors else "DEGRADED"
    return {
        "status": status,
        "exit_code": 0,
        "title": "K2 pre-transfer condition check",
        "summary": (f"Listed {len(instances)} instance(s) in "
                    f"{args.region_id} and mapped the queried facts onto "
                    f"the five hard transfer conditions."),
        "findings": findings,
        "warnings": errors,
        "next_action": ("fix every unmet condition, then hand the customer "
                        "the console transfer flow; if a condition cannot "
                        "be met, run --guide image-migration instead"),
        "instances": instances,
    }


# ---------------------------------------------------------------------------
# Gated snapshot backup (the only write effect of this skill)
# ---------------------------------------------------------------------------

def cmd_create_snapshot(args) -> dict:
    if not args.disk_id or not DISK_RE.match(args.disk_id):
        return _bad("Gated snapshot backup",
                    "--create-snapshot requires a valid --disk-id (d-...).",
                    "ask the customer which system disk to back up; run "
                    "--precheck first if the disk is unknown")
    if not args.region_id or not REGION_RE.match(args.region_id):
        return _bad("Gated snapshot backup",
                    "--create-snapshot requires a valid --region-id: snapshot "
                    "requests are regional and the region is never guessed.",
                    "ask the customer which region the disk lives in "
                    "(--precheck reports it), then re-run with "
                    "--region-id <region>")
    name = args.snapshot_name or (
        "transfer-pre-backup-"
        + datetime.datetime.now().strftime("%Y%m%d%H%M"))
    if not SNAPSHOT_NAME_RE.match(name):
        return _bad("Gated snapshot backup",
                    f"snapshot name '{name}' is invalid (must start with a "
                    "letter, 2-128 chars of letters/digits/-_:.).",
                    "choose a conforming --snapshot-name")
    if args.confirm.lower() != "yes":
        impact = [f"Impact {i}: {t}" for i, t in enumerate(C.SNAPSHOT_IMPACT, 1)]
        return {
            "status": "FAIL",
            "exit_code": 1,
            "title": "Gated snapshot backup -- confirmation required",
            "summary": ("CreateSnapshot was NOT invoked: the confirmation "
                        "gate is closed until the user approves this exact "
                        f"disk ({args.disk_id})."),
            "findings": impact + [
                "Tell the user: what runs (one snapshot request on the "
                "named disk), impact (snapshot appears and accrues "
                "snapshot storage fees until a human deletes it), "
                "reversibility (a copy; the disk itself is untouched).",
            ],
            "next_action": ("after the user explicitly agrees, re-run with "
                            "--confirm yes (approval is per call only)"),
        }
    budget = _budget_result()
    if budget:
        budget["title"] = "Gated snapshot backup"
        return budget
    try:
        body = _cli.call("ecs", "CreateSnapshot",
                         {"RegionId": args.region_id,
                          "DiskId": args.disk_id, "SnapshotName": name},
                         region=args.region_id, profile=args.profile,
                         timeout=int(min(C.API_TIMEOUT_SECONDS,
                                         max(5, remaining_budget()))))
    except _cli.CliError as e:
        return _bad("Gated snapshot backup", f"CreateSnapshot failed: {e}",
                    "report the code verbatim (NoPermission / "
                    "ImplicitDeny -> see references/ram-policies.md); do "
                    "not retry blind")
    snap_id = _first(body, "SnapshotId", default="(not returned)")
    return {
        "status": "OK",
        "exit_code": 0,
        "title": "Gated snapshot backup",
        "summary": (f"Snapshot {snap_id} ({name}) requested for disk "
                    f"{args.disk_id}."),
        "findings": [
            "Creation is asynchronous: check progress under ECS console > "
            "Storage & Snapshots > Snapshots.",
            "The snapshot bills storage fees until the customer deletes it.",
            "Proceed with the OS replacement / image rebuild only after "
            "the snapshot reaches the accomplished state.",
        ],
        "next_action": ("wait until the snapshot is accomplished, then "
                        "continue --guide image-migration step 4"),
        "snapshot_id": snap_id,
    }


# ---------------------------------------------------------------------------
# K3 / K4 / K5 embedded guidance
# ---------------------------------------------------------------------------

GUIDE_TOPICS = {
    "image-migration": ("K3 cross-account migration by shared custom image",
                        C.IMAGE_MIGRATION_STEPS, C.IMAGE_MIGRATION_RULES,
                        "collect the destination UID from its owner (that "
                        "account runs sts_token.py); before any OS "
                        "replacement on an existing target instance run "
                        "--create-snapshot behind the confirmation gate"),
    "post-transfer": ("K4 post-transfer verification checklist",
                      None, C.POST_TRANSFER_CHECKLIST,
                      "give every applicable row to the customer after the "
                      "transfer completes; update DNS first among them"),
    "account-rules": ("K5 related products & account rules",
                      None, C.ACCOUNT_RULES,
                      "answer the matched rule verbatim-plus-hedge; route "
                      "out-of-scope products via --handoff"),
}


def cmd_guide(args) -> dict:
    title, steps, rules, next_action = GUIDE_TOPICS[args.guide]
    findings = []
    if steps:
        findings += [f"Step {s['step']}: {s['title']} -- {s['detail']}"
                     for s in steps]
    if rules:
        kind = "Rule" if args.guide == "image-migration" else "Item"
        for i, r in enumerate(rules, 1):
            text = r["text"] if isinstance(r, dict) else r
            findings.append(f"{kind} {i}: {text}")
    return {
        "status": "OK",
        "exit_code": 0,
        "title": title,
        "summary": f"Guidance emitted for topic '{args.guide}'.",
        "findings": findings,
        "next_action": next_action,
    }


# ---------------------------------------------------------------------------
# K6 blocker lookup / K7 hand-off / links
# ---------------------------------------------------------------------------

def cmd_blocker(args) -> dict:
    text = args.blocker.lower()
    matches = [b for b in C.BLOCKERS if any(k.lower() in text
                                            for k in b["match"])]
    if not matches:
        matches = [{"id": "uncatalogued",
                    "meaning": C.GENERIC_BLOCKER_FALLBACK["meaning"],
                    "actions": C.GENERIC_BLOCKER_FALLBACK["actions"]}]
    findings = []
    for b in matches:
        findings.append(f"Blocker [{b['id']}]: {b['meaning']}")
        findings += [f"  next: {a}" for a in b["actions"]]
    return {
        "status": "OK",
        "exit_code": 0,
        "title": "K6 transfer blocker lookup",
        "summary": (f"{len(matches)} catalogued blocker pattern(s) matched "
                    "the pasted wording." if matches[0]["id"] != "uncatalogued"
                    else "No catalogued blocker matched; fallback guidance "
                         "emitted."),
        "findings": findings,
        "next_action": ("run --assess / --precheck next; if the console "
                        "still blocks, open a ticket with instance id, "
                        "both account UIDs, and the exact error text"),
    }


def cmd_handoff(args) -> dict:
    text = args.handoff.lower()
    for rule in C.HANDOFF_RULES:
        if rule.get("then") == "IN_SCOPE":
            if any(k.lower() in text for k in rule["scope_guard"]):
                return {
                    "status": "OK",
                    "exit_code": 0,
                    "title": "K7 routing",
                    "summary": "Symptom mentions transfer/account context: "
                               "it stays IN SCOPE of this skill.",
                    "findings": ["route: THIS skill (continue with "
                                 "--assess / --precheck / --guide)"],
                    "next_action": "choose the matching mode and run it",
                }
            continue
        if any(k.lower() in text for k in rule["match"]):
            return {
                "status": "OK",
                "exit_code": 0,
                "title": "K7 routing",
                "summary": f"Symptom routed OUT of scope -> {rule['route']}.",
                "findings": [rule["line"]],
                "next_action": (f"hand off to {rule['route']} with the "
                                "customer's original wording; do not "
                                "diagnose it here"),
            }
    return {
        "status": "OK",
        "exit_code": 0,
        "title": "K7 routing",
        "summary": "No routing keyword matched; the request most likely "
                   "stays in scope.",
        "findings": ["continue with --assess and --precheck"],
        "next_action": "run --assess for the feasibility verdict",
    }


def cmd_links(_args) -> dict:
    findings = []
    for group, entries in C.HELP_LINKS.items():
        for e in entries:
            url = e.get("url") or "(no evidenced URL -- verify manually)"
            note = e.get("note", "")
            anchors = "".join(f" | {a}" for a in e.get("anchors", []))
            findings.append(f"[{group}] {e['label']}: {url}{anchors}"
                            + (f" -- {note}" if note else ""))
    return {
        "status": "OK",
        "exit_code": 0,
        "title": "Official help links used by this skill",
        "summary": ("Links are exactly the URLs quoted inside the "
                    "support-ticket dialogues this skill was distilled "
                    "from; unverified ones are marked, never invented."),
        "findings": findings,
        "next_action": "cite only these URLs when referring the customer "
                       "to documentation",
    }


# ---------------------------------------------------------------------------
# Rendering + main
# ---------------------------------------------------------------------------

def render(res: dict, as_json: bool) -> None:
    if as_json:
        printable = {k: v for k, v in res.items()
                     if k not in ("exit_code", "title")}
        print(json.dumps(printable, indent=2, ensure_ascii=False,
                         default=str))
    else:
        print("=" * 72)
        print(res.get("title", ""))
        print("=" * 72)
        print("Summary: " + res.get("summary", ""))
        print("-" * 72)
        for f in res.get("findings", []):
            print(f"- {f}")
        for w in res.get("warnings", []):
            print(f"[WARN] {w}")
    print("\nSTATUS: " + res["status"])
    print("NEXT_ACTION: " + res.get("next_action", "-"))


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="transfer_guide.py",
        description="ECS cross-account transfer & entity-change guide "
                    "(single entry point; query-class evidence + one "
                    "confirmation-gated snapshot backup action)",
    )
    modes = p.add_mutually_exclusive_group()
    modes.add_argument("--assess", action="store_true",
                       help="K1 feasibility verdict from collected facts")
    modes.add_argument("--precheck", action="store_true",
                       help="K2 live instance-side condition checklist")
    modes.add_argument("--create-snapshot", action="store_true",
                       help="gated snapshot backup (requires --disk-id, "
                            "--region-id and --confirm yes)")
    modes.add_argument("--guide", choices=sorted(GUIDE_TOPICS),
                       help="print embedded guidance topic")
    modes.add_argument("--blocker", metavar="TEXT",
                       help="look up pasted console error/status wording")
    modes.add_argument("--handoff", metavar="TEXT",
                       help="route an out-of-scope symptom to a sibling "
                            "skill / product line")
    modes.add_argument("--list-links", action="store_true",
                       help="print the evidenced official help links")

    p.add_argument("--region-id", help="region of the instance (required "
                                       "for --precheck and "
                                       "--create-snapshot)")
    p.add_argument("--instance-id", help="instance id filter (i-...)")
    p.add_argument("--public-ip", help="public IP filter for lookup")
    p.add_argument("--target-zone", help="destination vSwitch zone for the "
                                         "sellability pre-check")
    p.add_argument("--target-instance-type", help="instance type for the "
                                                  "sellability pre-check")
    p.add_argument("--charge-type", choices=("PrePaid", "PostPaid"),
                   help="charge type for the sellability pre-check")
    p.add_argument("--source-type", choices=ACCOUNT_TYPES, default="unknown",
                   help="source account real-name verification type")
    p.add_argument("--target-type", choices=ACCOUNT_TYPES, default="unknown",
                   help="target account real-name verification type")
    p.add_argument("--entity-relation", choices=ENTITY_RELATIONS,
                   default="unknown",
                   help="whether both accounts show the identical verified "
                        "entity name")
    p.add_argument("--cross-region", choices=YES_NO_UNKNOWN, default="unknown",
                   help="whether the move crosses regions")
    p.add_argument("--campaign-instance", choices=YES_NO_UNKNOWN,
                   default="unknown", help="was the instance a campaign / "
                                           "discount purchase")
    p.add_argument("--reseller-account", choices=YES_NO_UNKNOWN,
                   default="unknown", help="is either account a "
                                           "distribution (reseller) account")
    p.add_argument("--disk-id", help="disk to snapshot (d-...)")
    p.add_argument("--snapshot-name", help="name for the snapshot")
    p.add_argument("--confirm", default="no",
                   help="'yes' opens the per-call confirmation gate for "
                        "--create-snapshot")
    p.add_argument("--profile", default=None,
                   help="optional aliyun CLI credential profile name")
    p.add_argument("--json", action="store_true", help="machine-readable")
    return p


MODE_FUNCS = {
    "assess": cmd_assess,
    "precheck": cmd_precheck,
    "create_snapshot": cmd_create_snapshot,
    "guide": cmd_guide,
    "blocker": cmd_blocker,
    "handoff": cmd_handoff,
    "list_links": cmd_links,
}


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    chosen = [(k, getattr(args, k)) for k in
              ("assess", "precheck", "create_snapshot", "guide", "blocker",
               "handoff", "list_links")]
    active = [k for k, v in chosen if v]
    if len(active) != 1:
        render({
            "status": "FAIL",
            "exit_code": 1,
            "title": "usage",
            "summary": ("Exactly one mode is required: --assess, "
                        "--precheck, --create-snapshot, --guide, --blocker, "
                        "--handoff, --list-links."),
            "findings": [],
            "next_action": ("pick the mode: feasibility -> --assess; live "
                            "facts -> --precheck; backup -> "
                            "--create-snapshot; guidance -> --guide TOPIC; "
                            "pasted error -> --blocker"),
        }, args.json)
        return 1
    if active[0] not in ("assess", "guide", "blocker", "handoff",
                         "list_links"):
        _cli.check_cli_available()
    res = MODE_FUNCS[active[0]](args)
    render(res, args.json)
    return int(res.get("exit_code", 0))


if __name__ == "__main__":
    sys.exit(main())
