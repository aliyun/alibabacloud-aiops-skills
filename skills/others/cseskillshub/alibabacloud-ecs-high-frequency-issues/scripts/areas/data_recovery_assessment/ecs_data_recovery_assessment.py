#!/usr/bin/env python3
"""
ecs_data_recovery_assessment.py -- Single entry point for the ECS
data-loss recoverability assessment skill (read-only + manual guidance)
========================================================================
SECURITY: READ-ONLY. The only cloud action this script performs is the
whitelisted read-only query `ecs DescribeInstances`; everything else is
offline reasoning over facts the CUSTOMER supplied or self-checked. It never
runs commands inside an instance, never performs console or API changes, and
never reads, prints or forwards credentials (the aliyun CLI default credential
chain resolves authentication).

Modes (mutually exclusive):
  --instance-id <i-...> | --public-ip <a.b.c.d>  --region-id <region>
        Step 1 evidence: read-only instance existence / status check.
  --assess --loss-type <k> [--carrier <k>] [--backup k1,k2,...]
           [--backup-time <k>] [--overwrite <k>] [--instance-state <k>]
           [--os <k>]
        Step 2 verdict: recoverability matrix over the evidence gathered.
  --self-check        Print the backup-asset customer self-check checklist
                      (entry / object / expected result / fallback per asset).
  --handoff <key|all> Neighbouring-symptom recognition and handoff wording.
  --docs [<key>]      Official documentation index (optionally one entry).
  --list-options      List every accepted enum value for the flags above.

Output contract: every run ends with `STATUS: OK|DEGRADED|FAIL` and a
`NEXT_ACTION:` line. Exit codes: 0 = OK/DEGRADED conclusion, 1 = no usable
conclusion, 2 = argparse usage error only.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import os
import re
import sys
from typing import Optional

import _cli
import _constants as K

# ---------------------------------------------------------------------------
# Input validation (strict regex + enum checks; nothing is guessed)
# ---------------------------------------------------------------------------

_INSTANCE_ID_RE = re.compile(r"^i-[a-z0-9]{6,}$")
_IPV4_RE = re.compile(
    r"^(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}"
    r"(?:25[0-5]|2[0-4]\d|1?\d?\d)$")

_BACKUP_TIME_VALUES = ("matched", "older", "unknown")
_OVERWRITE_VALUES = ("none", "possible", "confirmed")
_INSTANCE_STATE_VALUES = ("present-running", "present-stopped",
                          "not-visible", "unknown")
_OS_VALUES = ("linux", "windows", "unknown")


def _validate_choice(value: str, allowed: tuple, flag: str) -> str:
    if value not in allowed:
        raise SystemExit(
            f"[ERROR] --{flag} got invalid value {value!r}; allowed: "
            f"{', '.join(allowed)}. Run --list-options for definitions.")
    return value


# ---------------------------------------------------------------------------
# Boundary assertions for the validators (normal / boundary / invalid)
# ---------------------------------------------------------------------------
assert _INSTANCE_ID_RE.match("i-2zeexampleec0dd80c40")
assert not _INSTANCE_ID_RE.match("i-short")
assert not _INSTANCE_ID_RE.match("d-2zeexample4bf7e21641")
assert _IPV4_RE.match("47.98.1.2")
assert not _IPV4_RE.match("47.98.1")
assert not _IPV4_RE.match("47.98.1.256")
try:
    _validate_choice("nope", _BACKUP_TIME_VALUES, "backup-time")
    raise AssertionError("invalid choice must exit")
except SystemExit:
    pass


# ---------------------------------------------------------------------------
# Recoverability matrix (pure function, capability C3 x C2 -> C4)
# ---------------------------------------------------------------------------

def determine_verdict(loss_type: str, carrier: str, backups: set[str],
                      backup_time: str, overwrite: str,
                      instance_state: str) -> dict:
    """Apply the tiered recoverability matrix and return a verdict dict.

    Keys: verdict, rationale (list of str), paths (list of guidance keys),
    expectation (list of EXPECTATION_LINES keys), handoff (list of rule keys),
    evidence_needed (list of str).
    """
    out = {"verdict": K.VERDICT_INSUFFICIENT, "rationale": [], "paths": [],
           "expectation": [], "handoff": [], "evidence_needed": []}

    def finalize(verdict: str) -> dict:
        out["verdict"] = verdict
        return out

    named = backups - {"none", "unknown"}
    has_none = "none" in backups
    has_unknown = "unknown" in backups
    live_deletion = (
        loss_type in ("mistaken-delete", "intrusion-deletion")
        and carrier not in ("local-disk", "memory-cache")
        and instance_state != "not-visible")

    # Gate 0: never conclude on missing evidence; never promise optimism.
    if not backups or has_unknown:
        out["rationale"].append(
            "Backup-asset inventory not confirmed by the customer yet; any "
            "'unknown' entry keeps the verdict conservative.")
        if has_unknown:
            out["evidence_needed"].append(
                "Confirm each backup asset line in the self-check list and "
                "paste back the console result or screenshot.")
        else:
            out["evidence_needed"].append(
                "Work through the backup-asset self-check list and collect "
                "the customer's answers before any verdict.")
        if live_deletion:
            out["expectation"].append("deletion-on-live-disk")
            out["paths"].append("guest-side-recovery-practice")
        return finalize(K.VERDICT_INSUFFICIENT)

    # Gate 1: suspected loss that may only be a path/mount change.
    if loss_type == "suspected-loss":
        out["rationale"].append(
            "Symptoms fit a 'not actually lost' pattern (changed storage "
            "path, disk not mounted). Prove or disprove with read-only guest "
            "checks the customer runs and pastes back.")
        out["paths"].append("guest-side-recovery-practice")
        out["evidence_needed"].append(
            "Ask the customer to run lsblk / df -h / mount / find inside the "
            "instance themselves and paste the output.")
        return finalize(K.VERDICT_NOT_A_LOSS)

    # Gate 2: memory-only cache data was never on disk.
    if loss_type == "cache-not-persisted" or carrier == "memory-cache":
        out["expectation"].append("cache-not-on-disk")
        if named & {"database-backup", "binlog", "local-copy"}:
            out["rationale"].append(
                "A logical dump or local copy of the cached dataset may "
                "still cover an older point; disk-side recovery is moot.")
            return finalize(K.VERDICT_OLDER_POINT)
        out["rationale"].append(
            "The lost content existed only in memory without persistence; no "
            "cloud-side carrier ever held it.")
        out["paths"].append("rebuild-from-scratch")
        return finalize(K.VERDICT_NOT_RECOVERABLE)

    # Gate 3: confirmed overwrite of the only copy destroys recovery odds.
    if overwrite == "confirmed" and not named:
        out["rationale"].append(
            "New writes after the loss are confirmed and no backup asset "
            "survives: the released blocks are overwritten.")
        if live_deletion:
            out["rationale"].append(
                "Confirmed writes lower the odds sharply but do not prove every "
                "block was overwritten; the file-level attempt is still offered "
                "with its risk notice before any unrecoverable conclusion.")
            out["expectation"].append("deletion-on-live-disk")
            out["expectation"].append("no-auto-backup")
            out["paths"].append("guest-side-recovery-practice")
            return finalize(K.VERDICT_INSUFFICIENT)
        out["paths"].append("rebuild-from-scratch")
        return finalize(K.VERDICT_NOT_RECOVERABLE)

    # Gate 4: no backup asset at all -> platform-side recovery impossible.
    if has_none and not named:
        out["rationale"].append(
            "Customer confirmed: no snapshot, no image, no backup copy of "
            "any kind covers the lost data.")
        if live_deletion:
            out["rationale"].append(
                "The loss is a deletion on a disk that still exists, so the "
                "absent backup only rules out a PLATFORM-side restore. A "
                "file-level attempt is still open and must be offered before "
                "any unrecoverable conclusion.")
            out["expectation"].append("deletion-on-live-disk")
            out["expectation"].append("no-auto-backup")
            out["paths"].append("guest-side-recovery-practice")
            if loss_type == "intrusion-deletion":
                out["expectation"].append("third-party-recovery")
                out["handoff"].append("host-intrusion")
            return finalize(K.VERDICT_INSUFFICIENT)
        if loss_type == "expiry-release" or instance_state == "not-visible":
            out["expectation"].append("release-is-permanent")
        if loss_type == "system-reinstall" or carrier == "system-disk":
            out["expectation"].append("reinstall-clears-system-disk")
        if carrier == "local-disk":
            out["expectation"].append("local-disk-retention")
        if loss_type == "intrusion-deletion":
            out["expectation"].append("third-party-recovery")
            out["handoff"].append("host-intrusion")
        out["expectation"].append("no-auto-backup")
        out["paths"].append("rebuild-from-scratch")
        return finalize(K.VERDICT_NOT_RECOVERABLE)

    # Gate 5: assets exist -> match class, time, and carrier.
    def time_gate() -> Optional[str]:
        if backup_time == "matched":
            return K.VERDICT_RECOVERABLE
        if backup_time == "older":
            return K.VERDICT_OLDER_POINT
        out["rationale"].append(
            "Assets exist but their creation times were not checked against "
            "the loss moment; verdict waits for the timestamps.")
        out["evidence_needed"].append(
            "Note each snapshot/image/backup's creation time versus the loss "
            "time in the self-check answers.")
        return None

    verdict: Optional[str] = None

    # Which classes of assets can carry the lost data?
    covers_system = bool(named & {"system-disk-snapshot", "custom-image",
                                  "ecs-file-backup", "cloud-backup"})
    covers_data = bool(named & {"data-disk-snapshot", "auto-snapshot-policy",
                                "ecs-file-backup", "cloud-backup",
                                "database-backup", "binlog", "local-copy"})
    if carrier == "system-disk":
        usable = covers_system
    elif carrier == "data-disk":
        usable = covers_data
    elif carrier == "local-disk":
        usable = bool(named & {"ecs-file-backup", "cloud-backup",
                               "database-backup", "binlog", "local-copy"})
        out["expectation"].append("local-disk-retention")
        out["rationale"].append(
            "Local disks cannot be covered by snapshots; only file-level or "
            "logical backups apply.")
    else:  # carrier unknown
        out["rationale"].append(
            "The carrier (system disk / data disk / local disk / memory) is "
            "not identified yet; asset-to-carrier matching is incomplete.")
        out["evidence_needed"].append(
            "Confirm which disk held the lost data before finalizing.")
        usable = False

    if not usable:
        out["rationale"].append(
            "The surviving assets do not cover the carrier that held the "
            "lost data (class mismatch), or the carrier is unidentified.")
        if named:
            out["expectation"].append("no-auto-backup")
        if loss_type == "expiry-release" or instance_state == "not-visible":
            out["expectation"].append("release-is-permanent")
        if live_deletion:
            out["expectation"].append("deletion-on-live-disk")
            if not named:
                out["paths"].append("guest-side-recovery-practice")
        else:
            out["paths"].append("rebuild-from-scratch")
        # A customer-confirmed negative for the COVERING class is required
        # before a hard NOT-RECOVERABLE; otherwise stay conservative.
        if has_none:
            return finalize(K.VERDICT_NOT_RECOVERABLE)
        out["evidence_needed"].append(
            "Ask whether any snapshot/image of the covered class exists at "
            "all before the final conclusion.")
        return finalize(K.VERDICT_INSUFFICIENT)

    verdict = time_gate()
    if verdict is None:
        return finalize(K.VERDICT_INSUFFICIENT)

    # Route to concrete recovery paths (best available first).
    if named & {"system-disk-snapshot"} and carrier == "system-disk":
        if instance_state == "not-visible":
            out["rationale"].append(
                "The instance is gone: a SYSTEM-disk snapshot can be turned "
                "into a custom image and the environment rebuilt (a "
                "DATA-disk snapshot cannot).")
            out["paths"].append("custom-image-rebuild")
        else:
            out["paths"].append("snapshot-rollback-system-disk")
    elif named & {"custom-image"}:
        out["paths"].append("custom-image-rebuild")
    elif named & {"ecs-file-backup", "cloud-backup"}:
        out["paths"].append("file-backup-restore")
        out["handoff"].append("backup-product-operations")
    elif named & {"data-disk-snapshot", "auto-snapshot-policy"}:
        out["paths"].append("snapshot-new-disk-extraction")
        out["rationale"].append(
            "Disk snapshots roll back or re-create the DISK they were taken "
            "from; extraction via a new disk is the standard safe route.")
    elif named & {"database-backup", "binlog", "local-copy"}:
        out["paths"].append("rebuild-from-scratch")
        out["rationale"].append(
            "Restore from the logical dump / log replay / local copy; "
            "reconcile the gap since its newest point manually.")

    # A disk snapshot used as an extraction source can never return the whole
    # state once the instance itself is gone, so RECOVERABLE would overstate
    # the outcome: only the files inside the snapshot come back.
    if (verdict == K.VERDICT_RECOVERABLE
            and "snapshot-new-disk-extraction" in out["paths"]
            and (instance_state == "not-visible"
                 or loss_type == "expiry-release")):
        verdict = K.VERDICT_EXTRACTION
        out["rationale"].append(
            "The instance itself is gone: the snapshot can only be built out "
            "as a new disk and mined file by file. A DATA-disk snapshot "
            "cannot become a custom image, so the previous system state "
            "cannot be rolled back.")
        # The expiry-release branch below already emits this line.
        if loss_type != "expiry-release":
            out["expectation"].append("release-is-permanent")

    # Residuals: no backup covering the moment + files still on a live disk.
    if not out["paths"]:
        out["paths"].append("guest-side-recovery-practice")
        out["rationale"].append(
            "Only the in-guest best-practice recovery tooling remains; its "
            "success is not guaranteed once blocks were overwritten.")

    if loss_type == "intrusion-deletion":
        out["expectation"].append("third-party-recovery")
        out["handoff"].append("host-intrusion")
    if loss_type == "expiry-release":
        out["expectation"].append("release-is-permanent")
        out["handoff"].append("deleted-instance-lifecycle")
    if overwrite == "possible":
        out["rationale"].append(
            "Post-loss write activity is possible: stop non-essential "
            "writes and snapshot the current state as a safety net first.")
    return finalize(verdict)


# ---------------------------------------------------------------------------
# Matrix boundary assertions (normal / boundary / invalid inputs)
# ---------------------------------------------------------------------------
_v = determine_verdict("mistaken-delete", "data-disk", {"unknown"},
                       "unknown", "none", "present-running")
assert _v["verdict"] == K.VERDICT_INSUFFICIENT, _v
_v = determine_verdict("mistaken-delete", "data-disk", {"none"},
                       "matched", "none", "present-running")
assert _v["verdict"] == K.VERDICT_INSUFFICIENT, _v
assert "no-auto-backup" in _v["expectation"], _v
assert "guest-side-recovery-practice" in _v["paths"], _v
assert "deletion-on-live-disk" in _v["expectation"], _v
assert "rebuild-from-scratch" not in _v["paths"], _v
_v = determine_verdict("expiry-release", "system-disk",
                       {"none"}, "matched", "none", "not-visible")
assert _v["verdict"] == K.VERDICT_NOT_RECOVERABLE, _v
assert "release-is-permanent" in _v["expectation"], _v
_v = determine_verdict("mistaken-delete", "data-disk", {"none"},
                       "matched", "none", "not-visible")
assert _v["verdict"] == K.VERDICT_NOT_RECOVERABLE, _v
_v = determine_verdict("mistaken-delete", "system-disk",
                       {"system-disk-snapshot"}, "matched", "none",
                       "not-visible")
assert _v["verdict"] == K.VERDICT_RECOVERABLE, _v
assert "custom-image-rebuild" in _v["paths"], _v
_v = determine_verdict("system-reinstall", "system-disk",
                       {"data-disk-snapshot"}, "matched", "none",
                       "present-running")
# Only a non-matching asset class was reported and the customer never
# confirmed the negative for the covering class -> stay conservative.
assert _v["verdict"] == K.VERDICT_INSUFFICIENT, _v
_v = determine_verdict("mistaken-format", "data-disk",
                       {"data-disk-snapshot"}, "older", "none",
                       "present-stopped")
assert _v["verdict"] == K.VERDICT_OLDER_POINT, _v
_v = determine_verdict("suspected-loss", "unknown", {"none"}, "unknown",
                       "none", "present-running")
assert _v["verdict"] == K.VERDICT_NOT_A_LOSS, _v
_v = determine_verdict("cache-not-persisted", "memory-cache", {"none"},
                       "unknown", "none", "present-running")
assert _v["verdict"] == K.VERDICT_NOT_RECOVERABLE, _v
assert "cache-not-on-disk" in _v["expectation"], _v
# Extraction-only downgrade: instance gone, so only files can come back.
_v = determine_verdict("mistaken-delete", "data-disk", {"data-disk-snapshot"},
                       "matched", "none", "not-visible")
assert _v["verdict"] == K.VERDICT_EXTRACTION, _v
assert "snapshot-new-disk-extraction" in _v["paths"], _v
# Counterpart: instance still present, so a full data-disk restore is real.
_v = determine_verdict("mistaken-delete", "data-disk", {"data-disk-snapshot"},
                       "matched", "none", "present-running")
assert _v["verdict"] == K.VERDICT_RECOVERABLE, _v
assert "release-is-permanent" not in _v["expectation"], _v


# ---------------------------------------------------------------------------
# Mode: read-only instance evidence (capability C1)
# ---------------------------------------------------------------------------

def _dig(obj, path):
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def gather_instance_evidence(instance_id: Optional[str], public_ip: Optional[str],
                             region_id: str, profile: Optional[str]) -> dict:
    """Call the whitelisted read-only DescribeInstances and summarize facts."""
    params = {"RegionId": region_id, "PageSize": K.PAGE_SIZE, "PageNumber": 1}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    if public_ip:
        params["PublicIpAddresses"] = public_ip

    errors: list[str] = []
    uid = _cli.resolve_account_id(region=region_id, profile=profile)
    if uid:
        print(f"[info] account UID auto-derived via the read-only identity "
              f"check: {uid} (traceability label only)")
    body = {}
    try:
        body = _cli.call("ecs", "DescribeInstances", params,
                         region=region_id, profile=profile)
    except _cli.CliError as e:
        errors.append(f"{e.code or 'CliError'}: {e}")
        print(f"[WARN] {e.code or 'CliError'}: {e}", file=sys.stderr)
        if e.code in ("NoPermission", "ImplicitDeny") or "permission" in str(e).lower():
            print(K.PERMISSION_FAILURE_NOTE, file=sys.stderr)

    instances = _dig(body, ["Instances", "Instance"]) or []
    result = {"region_id": region_id, "uid": uid, "errors": errors,
              "requested": instance_id or public_ip, "found": [],
              "visible_total": len(instances), "not_visible": False}

    for inst in instances:
        row = {
            "instance_id": inst.get("InstanceId", "(not reported)"),
            "instance_name": inst.get("InstanceName", "(not reported)"),
            "status": inst.get("Status", "(not reported)"),
            "os_name": inst.get("OSName") or inst.get("OSNameEn")
                       or "(not reported)",
            "charge_type": inst.get("InstanceChargeType", "(not reported)"),
            "expired_time": inst.get("ExpiredTime", "(not reported)"),
            "zone_id": inst.get("ZoneId", "(not reported)"),
            "public_ips": _dig(inst, ["PublicIpAddress", "IpAddress"]) or [],
            "eip": inst.get("EipAddress", {}).get("IpAddress", "")
                    if isinstance(inst.get("EipAddress"), dict) else "",
        }
        result["found"].append(row)

    if not errors and not instances:
        result["not_visible"] = True
    return result


def render_gather(result: dict, as_json: bool) -> int:
    findings: list[str] = []
    if result["errors"]:
        findings = [f"query error: {e}" for e in result["errors"]]
        status, code = "FAIL", 1
        next_action = ("fix the reported CLI/permission problem (see "
                       "references/ram-policies.md), then re-run this "
                       "evidence step")
    elif result["not_visible"]:
        findings.append(K.NOT_VISIBLE_NOTE)
        status, code = "OK", 0
        next_action = ("collect the customer's own confirmation of region / "
                       "account and the expiry or release notification, then "
                       "run --assess with --instance-state not-visible")
    else:
        for row in result["found"]:
            meaning = K.INSTANCE_STATUS_MEANING.get(
                row["status"], "status as reported by the query")
            findings.append(
                f"instance {row['instance_id']} ({row['instance_name']}) "
                f"status={row['status']} zone={row['zone_id']} "
                f"os={row['os_name']} charge={row['charge_type']} "
                f"expired={row['expired_time']}")
            findings.append(f"  meaning: {meaning}")
            if row["public_ips"]:
                findings.append(f"  public ips: {', '.join(row['public_ips'])}")
            if row.get("eip"):
                findings.append(f"  eip: {row['eip']}")
        findings.append(
            f"{len(result['found'])} instance(s) visible to this query in "
            f"region {result['region_id']}")
        status, code = "OK", 0
        next_action = ("run --assess with the customer's loss facts "
                       "(--loss-type/--carrier/--backup/--backup-time) to "
                       "get the recoverability verdict")

    if as_json:
        print(json.dumps({"status": status, "evidence": result,
                          "key_findings": findings,
                          "next_action": next_action}, indent=2, ensure_ascii=False))
    else:
        print("=" * 60)
        print(f"Step 1 evidence -- read-only instance check (region "
              f"{result['region_id']})")
        print("=" * 60)
        for line in findings:
            print(f"  {line}")
        if result["uid"]:
            print(f"  account UID (auto-derived, traceability only): "
                  f"{result['uid']}")
        print("\nSummary")
        print("-------")
        print(f"STATUS: {status}")
        print(f"NEXT_ACTION: {next_action}")
    return code


# ---------------------------------------------------------------------------
# Mode: verdict + guidance (capabilities C4/C5/C6)
# ---------------------------------------------------------------------------

def _self_check_shortlist(backups):
    items = K.SELF_CHECK_ITEMS
    named = {b for b in backups if b not in ("none", "unknown")}
    if not named:
        return items[:3]
    picked = []
    for item in items:
        asset = item["asset"].lower()
        for key in named:
            if any(token in asset for token in key.split("-") if len(token) > 3):
                if item not in picked:
                    picked.append(item)
                break
    return (picked or items)[:3]


def render_assess(args: argparse.Namespace, as_json: bool) -> int:
    backups = {b.strip() for b in args.backup.split(",") if b.strip()}
    bad = backups - set(K.BACKUP_ASSETS)
    if bad:
        print(f"[ERROR] unknown --backup value(s): {', '.join(sorted(bad))}; "
              f"see --list-options", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run with valid backup-asset keys")
        return 1
    verdict = determine_verdict(
        args.loss_type, args.carrier, backups, args.backup_time,
        args.overwrite, args.instance_state)

    guidance = []
    for key in verdict["paths"]:
        path = K.RECOVERY_PATHS[key]
        guidance.append({
            "key": key,
            "when": path["when"],
            "steps": list(path["steps"]),
            "risk_notices": list(path["risk-notices"]),
        })
    if guidance and args.loss_type != "cache-not-persisted":
        guidance[0]["steps"].insert(0, K.SNAPSHOT_FIRST_NOTICE)

    expectation_lines = [K.EXPECTATION_LINES[k]
                         for k in verdict["expectation"]]
    customer_question = os.environ.get("ECS_CUSTOMER_QUESTION", "") or ""
    branch = loss_branch_topic(customer_question)
    if branch:
        expectation_lines = list(K.LOSS_BRANCH_LINES[branch]) + expectation_lines
    if K.agent_offline_signal(customer_question):
        expectation_lines = list(K.AGENT_OFFLINE_LINES) + expectation_lines
    elif not branch:
        expectation_lines = list(K.DEFAULT_LOSS_LINES) + expectation_lines
    handoffs = []
    for key in verdict["handoff"]:
        rule = K.HANDOFF_RULES[key]
        handoffs.append({"key": key, "signal": rule["signal"],
                         "target": rule["target"],
                         "safety_note": rule["safety-note"]})

    definite = verdict["verdict"] in (
        K.VERDICT_RECOVERABLE, K.VERDICT_EXTRACTION, K.VERDICT_OLDER_POINT,
        K.VERDICT_NOT_RECOVERABLE, K.VERDICT_NOT_A_LOSS)
    status = "OK" if definite else "DEGRADED"

    if as_json:
        print(json.dumps({
            "status": status,
            "verdict": verdict["verdict"],
            "verdict_meaning": K.VERDICT_MEANING[verdict["verdict"]],
            "rationale": verdict["rationale"],
            "inputs": {
                "loss_type": args.loss_type, "carrier": args.carrier,
                "backups": sorted(backups),
                "backup_time": args.backup_time,
                "overwrite": args.overwrite,
                "instance_state": args.instance_state,
                "os": args.os,
            },
            "guidance": guidance,
            "expectation_lines": expectation_lines,
            "evidence_needed": verdict["evidence_needed"],
            "handoffs": handoffs,
            "prevention": K.PREVENTION_ACTIONS,
            "read_only_declaration": (
                "All listed actions are performed manually by the customer "
                "in the console; this skill executes nothing on the cloud or "
                "inside the instance."),
        }, indent=2, ensure_ascii=False))
        print("\nSTATUS: " + status)
        return 0

    print("## Verdict")
    print(f"Verdict        : {verdict['verdict']}")
    print(f"Meaning        : {K.VERDICT_MEANING[verdict['verdict']]}")
    print("## Decision basis")
    print(f"  loss event   : {K.LOSS_TYPES[args.loss_type]['label']}")
    print(f"  carrier      : {K.CARRIERS[args.carrier]}")
    print(f"  assets       : "
          f"{', '.join(K.BACKUP_ASSETS[b]['label'] for b in sorted(backups))}")
    print(f"  backup time  : {args.backup_time}; post-loss writes: "
          f"{args.overwrite}; instance state: {args.instance_state}")
    for line in verdict["rationale"]:
        print(f"  why          : {line}")

    if expectation_lines:
        print("\n## What the customer needs to hear (fixed wording)")
        for line in expectation_lines:
            print(f"  - {line}")

    if guidance and definite:
        print("\n## Recovery guidance (customer performs every step manually)")
        for g in guidance:
            print(f"* {g['key']} -- {g['when']}")
            for i, step in enumerate(g["steps"], 1):
                print(f"    {i}. {step}")
            for note in g["risk_notices"]:
                print(f"    ! risk notice: {note}")
            print("    re-verify: after execution, re-run this script's "
                  "evidence mode plus the customer's own file/service "
                  "checks; only report success on pasted-back evidence.")
    elif guidance:
        attempt = [g for g in guidance
                   if g["key"] == "guest-side-recovery-practice"]
        if attempt:
            print("\n## Recovery attempt to offer now (customer performs every step)")
            for g in attempt:
                for i, step in enumerate(g["steps"], 1):
                    print(f"    {i}. {step}")
                for note in g["risk_notices"]:
                    print(f"    ! risk notice: {note}")

    if not definite:
        print("\n## Where to look first (customer self-check; paste the result back)")
        shortlist = _self_check_shortlist(backups)
        entries = []
        for item in shortlist:
            text = item["entry"].split("(")[0].strip()
            text = text.replace("ECS console -> ", "")
            entries.append(text)
        merged = "; ".join(entries)
        print(f"  - Have the customer paste back, from ECS console -> {merged} "
              f"(in the lost disk's region), in one reply.")
        if any("snapshot" in asset for asset in backups):
            print("  - Have the customer check the snapshot time: if it predates "
                  "the loss, roll back the disk (overwrites current data) or "
                  "create a new disk from it and copy files out; snapshot first.")
        if backups & {"ecs-file-backup", "cloud-backup", "database-backup"}:
            print("  - Have the customer open the Cloud Backup (HBR) console, "
                  "pick the vault and a restore point before the loss, and "
                  "restore to a NEW path first, then verify before switching.")

    if verdict["verdict"] == K.VERDICT_NOT_RECOVERABLE:
        print("\n## Confirm the negative in the console (customer performs)")
        print("  - Have the customer open ECS console -> Snapshots and custom "
              "Images, plus the released-instance list, and paste back any "
              "surviving asset before accepting the verdict.")
        if args.loss_type == "intrusion-deletion":
            print("  - Have the customer engage a specialized third-party "
                  "data-recovery service for forensic or decryption work; "
                  "the platform cannot undelete or decrypt.")

    if verdict["evidence_needed"]:
        print("\n## Evidence still needed before any firmer conclusion")
        for line in verdict["evidence_needed"]:
            print(f"  - {line}")
        print("  (run: python3 ecs_data_recovery_assessment.py --self-check)",
              file=sys.stderr)

    if handoffs:
        print("\n## Handoff recognition (do not diagnose these here)")
        for h in handoffs:
            print(f"  signal: {h['signal']}")
            print(f"  - Have the customer route this to: {h['target']}")
            print(f"  safety: {h['safety_note']}")

    print("\n## Prevention after this incident")
    for line in K.PREVENTION_ACTIONS:
        print(f"  - {line}")

    print("\nReminder: this skill never executes cloud-side changes or "
          "in-guest commands; it never promises a recovery outcome beyond "
          "the verdict above.")
    print(f"\nSTATUS: {status}")
    if definite:
        print("NEXT_ACTION: deliver the verdict with its evidence list; "
              "guide the customer through the path above and re-verify with "
              "the read-only check plus pasted-back results")
    else:
        print("NEXT_ACTION: collect the missing evidence via --self-check "
              "before any conclusion stronger than the conservative verdict "
              "shown")
    return 0


# ---------------------------------------------------------------------------
# Modes: self-check / handoff / docs / options
# ---------------------------------------------------------------------------

def infer_loss_type(question: str) -> str:
    """Name the loss event from the customer's own words when the caller did not.

    A real customer call carries no `--loss-type`, so every ticket used to land on
    `unknown` and receive one identical backup-inventory ask. The patterns are
    ordered: an intrusion or an expiry outranks the generic "my files are gone".
    """
    text = (question or "").strip()
    if not text:
        return ""
    for key, pattern in K.LOSS_TYPE_PATTERNS:
        if pattern.search(text):
            return key
    return ""


def consultation_topic(question: str) -> str:
    """A recovery-area ticket is often a procedure question, not a data loss.

    "How do I restart the server" and "create a cloud disk" reached this area and
    were answered with a snapshot-rollback playbook and a request for database
    settings and NAS copies. The loss-wording gate keeps a real loss out of this
    path; `snapshot_rollback_effect` is exempt because its own pattern already
    requires an impact question ("will it affect ..."), not a reported loss.
    """
    text = (question or "").strip()
    if not text:
        return ""
    matched = next((topic for topic, pattern in K.CONSULT_TOPICS
                    if pattern.search(text)), "")
    if not matched:
        return ""
    if matched in K.CONSULT_LOSS_OVERRIDE:
        return matched
    return "" if K.LOSS_WORDING_RE.search(text) else matched


def loss_branch_topic(question: str) -> str:
    """Name the scenario the customer's own words already point at.

    Manual calibration on 15 tickets showed the loss path answered every loss with
    one backup-inventory ask, even when the question itself names the likely cause:
    "files gone after a reboot" (data disk not auto-mounted), "MongoDB data lost,
    maybe hacked" (database port exposed), "my other server is gone" (released after
    expiry). These lines go to the FRONT of the fixed-wording section so the compact
    budget delivers them instead of the generic ask; the verdict stays conservative
    because none of them is a confirmed read.
    """
    text = (question or "").strip()
    if not text:
        return ""
    return next((topic for topic, pattern in K.LOSS_BRANCH_TOPICS
                 if pattern.search(text)), "")


def consultation_answer(topic: str) -> str:
    return "\n".join(
        ["RULE-LEAD: [platform_rule] this is a procedure question, not a data loss: "
         "the answer is the documented console path, so no recovery verdict is claimed",
         "",
         "--- Ask the customer to check these, in this order ---"]
        + list(K.CONSULT_STEPS[topic])
        + ["",
           "STATUS: OK",
           "NEXT_ACTION: deliver the procedure above, confirm the missing parameter "
           "with the customer, and ask them to report the result"])


def render_self_check(as_json: bool) -> int:
    if as_json:
        print(json.dumps({"status": "OK", "self_check": K.SELF_CHECK_ITEMS},
                         indent=2, ensure_ascii=False))
        return 0
    print("=" * 60)
    print("Backup-asset customer self-check checklist")
    print("(the customer opens each console page, pastes back the result)")
    print("=" * 60)
    for i, item in enumerate(K.SELF_CHECK_ITEMS, 1):
        print(f"\n[{i}] {item['asset']}")
        print(f"    entry    : {item['entry']}")
        print(f"    object   : {item['object']}")
        print(f"    expected : {item['expected']}")
        print(f"    fallback : {item['fallback']}")
    print("\nGround rule: until every line above is answered, the verdict "
          "stays INSUFFICIENT-EVIDENCE; no optimistic recovery promise is "
          "allowed.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: have the customer work through the list and re-run "
          "--assess with the confirmed facts")
    return 0


def render_handoff(key: str, as_json: bool) -> int:
    if key != "all" and key not in K.HANDOFF_RULES:
        print(f"[ERROR] unknown --handoff key {key!r}; valid: all, "
              f"{', '.join(K.HANDOFF_RULES)}", file=sys.stderr)
        print("STATUS: FAIL")
        print("NEXT_ACTION: re-run --handoff all to see the rule set")
        return 1
    rules = (K.HANDOFF_RULES if key == "all"
             else {key: K.HANDOFF_RULES[key]})
    if as_json:
        print(json.dumps({"status": "OK", "handoffs": rules}, indent=2,
                         ensure_ascii=False))
        return 0
    print("=" * 60)
    print("Neighbouring-symptom recognition and handoff")
    print("=" * 60)
    for k, rule in rules.items():
        print(f"\n[{k}]")
        print(f"    recognize : {rule['signal']}")
        print(f"    route to  : {rule['target']}")
        print(f"    first     : {rule['safety-note']}")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: if the request matches a signal, state the boundary "
          "and route it; handle here only the data-recoverability question")
    return 0


def render_docs(key: Optional[str], as_json: bool) -> int:
    entries = K.DOC_INDEX
    if key:
        entries = [d for d in K.DOC_INDEX if d["key"] == key]
        if not entries:
            print(f"[ERROR] unknown --docs key {key!r}; valid: "
                  f"{', '.join(d['key'] for d in K.DOC_INDEX)}",
                  file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: re-run --docs without a key to list all")
            return 1
    if as_json:
        print(json.dumps({"status": "OK", "docs": entries}, indent=2,
                         ensure_ascii=False))
        return 0
    print("=" * 60)
    print("Official documentation index (cite only these URLs)")
    print("=" * 60)
    for d in entries:
        print(f"  {d['title']}")
        print(f"    {d['url']}")
        print(f"    use: {d['use']}  [source: {d['source']}]")
    print("\nCite entries whose source is 'help-search' freely; for "
          "'support-conversation' entries state the link was provided in "
          "past support conversations and re-check it opens the current "
          "document before quoting numbers from it.")
    print("\nSTATUS: OK")
    print("NEXT_ACTION: attach the relevant documents to the guidance you "
          "deliver")
    return 0


def render_options() -> int:
    print("loss-type     :", ", ".join(K.LOSS_TYPES))
    print("carrier       :", ", ".join(K.CARRIERS))
    print("backup        :", ", ".join(K.BACKUP_ASSETS), "(comma-separated "
          "list allowed; 'none' must be stated explicitly to confirm the "
          "negative)")
    print("backup-time   :", ", ".join(_BACKUP_TIME_VALUES))
    print("overwrite     :", ", ".join(_OVERWRITE_VALUES))
    print("instance-state:", ", ".join(_INSTANCE_STATE_VALUES))
    print("os            :", ", ".join(_OS_VALUES))
    print("handoff keys  :", ", ".join(K.HANDOFF_RULES))
    print("docs keys     :", ", ".join(d["key"] for d in K.DOC_INDEX))
    print("\nSTATUS: OK")
    print("NEXT_ACTION: pick values and re-run the matching mode")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing and mode dispatch
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ecs_data_recovery_assessment.py",
        description=("Read-only ECS data-loss recoverability assessment: "
                     "instance evidence, backup-asset self-check, tiered "
                     "verdict and manual console guidance (the customer "
                     "performs every action)"),
    )
    parser.add_argument("--instance-id", default=None,
                        help="ECS instance id (i-...) for the read-only "
                             "existence check")
    parser.add_argument("--public-ip", default=None,
                        help="Public IP address to locate the instance "
                             "instead of an id")
    parser.add_argument("--region-id", default=None,
                        help="Region id for the read-only query (required "
                             "with --instance-id/--public-ip; never guessed)")
    parser.add_argument("--profile", default=None,
                        help="Optional aliyun CLI credential profile name")
    parser.add_argument("--assess", action="store_true",
                        help="Run the recoverability matrix on supplied facts")
    parser.add_argument("--loss-type", default="unknown",
                        help="Loss-event key (see --list-options)")
    parser.add_argument("--carrier", default="unknown",
                        help="Where the lost data lived (see --list-options)")
    parser.add_argument("--backup", default="",
                        help="Comma-separated surviving backup-asset keys; "
                             "'none' = customer-confirmed negative")
    parser.add_argument("--backup-time", default="unknown",
                        choices=_BACKUP_TIME_VALUES,
                        help="Do surviving assets cover the needed moment?")
    parser.add_argument("--overwrite", default="none",
                        help="Post-loss write risk: none|possible|confirmed")
    parser.add_argument("--instance-state", default="unknown",
                        choices=_INSTANCE_STATE_VALUES,
                        help="Result of the Step 1 existence check")
    parser.add_argument("--os", default="unknown", choices=_OS_VALUES,
                        help="Guest OS family, selects the right "
                             "best-practice document branch")
    parser.add_argument("--self-check", action="store_true",
                        help="Print the backup-asset customer self-check list")
    parser.add_argument("--handoff", default=None, metavar="KEY",
                        help="Print handoff rule(s): a key or 'all'")
    parser.add_argument("--docs", nargs="?", const="__all__", default=None,
                        metavar="KEY", help="Print documentation index")
    parser.add_argument("--list-options", action="store_true",
                        help="List every accepted enum value and exit")
    parser.add_argument("--json", action="store_true", help="JSON output")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    asked = os.environ.get("ECS_CUSTOMER_QUESTION", "") or ""
    consult = consultation_topic(asked)
    if consult and not (args.list_options or args.self_check or args.handoff
                        or args.docs is not None):
        sys.stdout.write(consultation_answer(consult) + "\n")
        return 0

    if args.list_options:
        return render_options()
    if args.self_check:
        return render_self_check(args.json)
    if args.handoff:
        return render_handoff(args.handoff, args.json)
    if args.docs is not None:
        key = None if args.docs == "__all__" else args.docs
        return render_docs(key, args.json)

    if args.assess:
        if args.loss_type == "unknown":
            inferred = infer_loss_type(asked)
            if inferred:
                args.loss_type = inferred
        try:
            _validate_choice(args.loss_type, tuple(K.LOSS_TYPES), "loss-type")
            _validate_choice(args.carrier, tuple(K.CARRIERS), "carrier")
            _validate_choice(args.overwrite, _OVERWRITE_VALUES, "overwrite")
        except SystemExit as e:
            print(str(e), file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: re-run --assess with valid values from "
                  "--list-options")
            return 1
        return render_assess(args, args.json)

    if args.instance_id or args.public_ip:
        if args.instance_id and not _INSTANCE_ID_RE.match(args.instance_id):
            print("[ERROR] --instance-id must look like i-<alnum>; got "
                  f"{args.instance_id!r}", file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: ask the customer for the exact instance id")
            return 1
        if args.public_ip and not _IPV4_RE.match(args.public_ip):
            print("[ERROR] --public-ip must be a valid IPv4 address; got "
                  f"{args.public_ip!r}", file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: ask the customer for the exact public IP")
            return 1
        if not args.region_id:
            print("[ERROR] --region-id is required for the read-only "
                  "instance query and is never guessed.", file=sys.stderr)
            print("STATUS: FAIL")
            print("NEXT_ACTION: ask the customer which region the instance "
                  "lives in, then re-run with --region-id <region>")
            return 1
        _cli.check_cli_available()
        result = gather_instance_evidence(args.instance_id, args.public_ip,
                                          args.region_id, args.profile)
        return render_gather(result, args.json)

    parser.print_help()
    print("\nSTATUS: FAIL")
    print("NEXT_ACTION: choose a mode -- evidence check (--instance-id + "
          "--region-id), verdict (--assess), --self-check, --handoff, "
          "--docs, or --list-options")
    return 1


if __name__ == "__main__":
    sys.exit(main())
