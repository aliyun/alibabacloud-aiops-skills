#!/usr/bin/env python3
"""Single entry point for the read-only ECS disk encryption and KMS key guide.

Reads instances, disks and snapshots in one region, reports the encryption fields the API
actually returned, and turns them into findings plus one customer-side next step. This
script issues only the whitelisted read-only ``Describe`` actions; it never performs a
mutation and never runs anything inside a customer instance.

    python3 scripts/ecs_encryption_audit.py --region-id cn-hangzhou --instance-id i-xxxx
    python3 scripts/ecs_encryption_audit.py --region-id cn-beijing --disk-id d-xxxx --include-snapshots
    python3 scripts/ecs_encryption_audit.py --region-id cn-beijing --all-disks --format json
"""

import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _cli import AUTH_DENY_CODES, CliError, call, mask, new_session_id
from _constants import (
    ACTION_DESCRIBE_DISKS,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_SNAPSHOTS,
    CONSOLE_CHECK_HINTS,
    DEFAULT_TIMEOUT_SECONDS,
    ECS_API_VERSION,
    ECS_PRODUCT,
    MAX_PAGES,
    MAX_SNAPSHOT_LOOKUPS,
    MAX_TIMEOUT_SECONDS,
    PAGE_SIZE,
    READ_BOUNDARIES,
    READ_ONLY_WHITELIST,
    SKILL_NAME,
    region_endpoint_hint,
)
from sts_token import fetch_caller

ENCRYPTION_TOKENS = ("encrypt", "kms", "algorithm", "cmk", "alias")
KEY_FIELD_NAMES = ("kmskeyid", "cmkkeyid", "cmkeyid", "encryptionkeyid", "keyid")
REGION_RE = re.compile(r"^[a-z][a-z0-9-]{1,30}$")

NEXT_PRIORITY = (
    "CLI-NOT-FOUND",
    "AUTH-MISSING-PERMISSION",
    "SCOPE-ID-SHAPE",
    "SCOPE-NO-OBJECTS",
    "READ-PARTIAL",
    "ORDER-FAILURE-RECORDED",
    "DISK-NOT-ENCRYPTED",
    "DISK-ENCRYPTED-KEY-TYPE-UNCONFIRMED",
    "DISK-ENCRYPTION-FIELD-MISSING",
    "SNAPSHOT-NOT-ENCRYPTED",
    "SNAPSHOT-ENCRYPTED-KEY-TYPE-UNCONFIRMED",
    "DISK-ENCRYPTED-WITH-KEY",
    "SNAPSHOT-ENCRYPTED",
)


def _note(state, message, code=None):
    text = mask(message)
    state["notes"].append(text)
    if code:
        state["codes"].append(str(code))
    print("[WARN] {0}".format(text), file=sys.stderr)


def _finding(state, code, subject, detail, guidance, next_action):
    item = {
        "code": code,
        "subject": str(subject),
        "detail": mask(detail),
        "guidance": guidance,
        "next_action": next_action,
    }
    state["findings"].append(item)
    return item


def _pick(row, names):
    for key in sorted(row):
        if str(key).lower() in names:
            return row[key]
    return None


def _truthy(value):
    """Tri-state read of a boolean-ish field: True, False, or None when absent."""
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in ("true", "1", "yes"):
        return True
    if text in ("false", "0", "no"):
        return False
    return None


def encryption_fields(row):
    """Every returned field whose name mentions encryption, KMS or an algorithm.

    Field naming is taken from the live response rather than assumed, so a key the API
    renames still shows up here instead of being reported as absent.
    """
    out = {}
    for key in sorted(row):
        low = str(key).lower()
        if any(token in low for token in ENCRYPTION_TOKENS):
            out[key] = row[key]
    return out


def _dedupe(rows, key):
    seen = set()
    out = []
    for row in rows:
        marker = row.get(key) or json.dumps(row, sort_keys=True)
        if marker in seen:
            continue
        seen.add(marker)
        out.append(row)
    return out


def _paginate(state, action, params, outer, inner, session_id, timeout):
    rows = []
    page = 1
    failed = False
    complete = False
    while page <= MAX_PAGES:
        query = dict(params)
        query["PageNumber"] = page
        query["PageSize"] = PAGE_SIZE
        try:
            body = call(ECS_PRODUCT, action, query, session_id=session_id, timeout=timeout)
        except CliError as exc:
            failed = True
            _note(state, "{0} page {1} -> {2}".format(action, page, exc), code=exc.code)
            break
        block = body.get(outer)
        chunk = block.get(inner) if isinstance(block, dict) else block
        if chunk is None:
            chunk = []
        if isinstance(chunk, dict):
            chunk = [chunk]
        rows.extend(chunk)
        total = body.get("TotalCount")
        if not isinstance(total, int):
            total = len(rows)
        if len(chunk) < PAGE_SIZE or len(rows) >= total:
            complete = True
            break
        page += 1
    if not complete and not failed:
        _note(state, "{0}: stopped at {1} pages, the list may be partial".format(
            action, MAX_PAGES))
        _finding(state, "READ-PARTIAL", action,
                 "Paging stopped before the whole list was read.",
                 "Narrow the scope (one instance or one disk) or raise --timeout, then re-read.",
                 "Re-read with a narrower scope so every object is covered.")
    return rows


def read_instances(state, args, session_id, timeout):
    if not (args.instance_id or args.all_disks):
        return []
    params = {"RegionId": args.region_id}
    if args.instance_id:
        params["InstanceIds"] = [args.instance_id]
    return _paginate(state, ACTION_DESCRIBE_INSTANCES, params, "Instances", "Instance",
                     session_id, timeout)


def read_disks(state, args, session_id, timeout):
    params = {"RegionId": args.region_id}
    if args.instance_id:
        params["InstanceId"] = args.instance_id
    if args.disk_id:
        params["DiskIds"] = [args.disk_id]
    if args.snapshot_id:
        params["SnapshotId"] = args.snapshot_id
    if args.encrypted_only:
        params["Encrypted"] = True
    return _paginate(state, ACTION_DESCRIBE_DISKS, params, "Disks", "Disk",
                     session_id, timeout)


def read_snapshots(state, args, disks, session_id, timeout):
    if not (args.include_snapshots or args.snapshot_id):
        return []
    scopes = []
    if args.snapshot_id:
        scopes.append({"SnapshotIds": [args.snapshot_id]})
    elif args.instance_id:
        scopes.append({"InstanceId": args.instance_id})
    else:
        for disk in disks[:MAX_SNAPSHOT_LOOKUPS]:
            if disk.get("DiskId"):
                scopes.append({"DiskId": disk.get("DiskId")})
        if len(disks) > MAX_SNAPSHOT_LOOKUPS:
            _note(state, "snapshot detail expanded for the first {0} disks only".format(
                MAX_SNAPSHOT_LOOKUPS))
    rows = []
    for scope in scopes:
        params = {"RegionId": args.region_id}
        params.update(scope)
        rows.extend(_paginate(state, ACTION_DESCRIBE_SNAPSHOTS, params, "Snapshots",
                              "Snapshot", session_id, timeout))
    return _dedupe(rows, "SnapshotId")


def judge_disk(state, disk):
    disk_id = disk.get("DiskId") or "disk-id-not-returned"
    kind = disk.get("Type") or "type-not-returned"
    category = disk.get("Category") or "category-not-returned"
    enc = _truthy(_pick(disk, ("encrypted",)))
    key_ref = _pick(disk, KEY_FIELD_NAMES)
    if enc is True:
        if key_ref:
            return _finding(
                state, "DISK-ENCRYPTED-WITH-KEY", disk_id,
                "{0} ({1}, {2}): encrypted, and the read exposes a key reference "
                "({3}).".format(disk_id, kind, category, mask(key_ref)),
                "The state question is answered. Key policy, rotation and aliases live in KMS, "
                "which this skill does not read - point the customer at the KMS console.",
                "Report the encrypted state with the evidence row; send the customer to the KMS "
                "console for anything about the key itself.")
        return _finding(
            state, "DISK-ENCRYPTED-KEY-TYPE-UNCONFIRMED", disk_id,
            "{0} ({1}, {2}): encrypted, but the read returns no key identifier, so the "
            "service-key versus customer-managed-key question is unresolved.".format(
                disk_id, kind, category),
            "Do not guess the key type. Ask the customer to open the disk Detail pane and the "
            "KMS key list, or to paste a screenshot, then state the answer.",
            "Ask the customer for the disk Detail pane and the KMS key list, then re-read to "
            "confirm.")
    if enc is False:
        return _finding(
            state, "DISK-NOT-ENCRYPTED", disk_id,
            "{0} ({1}, {2}): not encrypted.".format(disk_id, kind, category),
            "Encryption cannot be switched on for a disk that already exists. Offer the two "
            "customer-side paths in references/encryption-basics.md - provision a new encrypted "
            "disk and move the data, or rebuild the system disk from an encrypted image - behind "
            "the mandatory risk block.",
            "Give the customer the two guided paths with the risk block, then re-read this disk "
            "to confirm the result.")
    return _finding(
        state, "DISK-ENCRYPTION-FIELD-MISSING", disk_id,
        "{0} ({1}, {2}): the read returned no encryption field, so the state is unconfirmed.".format(
            disk_id, kind, category),
        "Report the state as unconfirmed and use the console Detail pane check listed in "
        "references/query-recipes.md; never infer it from the disk category.",
        "Ask the customer for the disk Detail pane screenshot, then record the answer as "
        "customer-paste evidence.")


def judge_snapshot(state, snap):
    snap_id = snap.get("SnapshotId") or "snapshot-id-not-returned"
    source = snap.get("SourceDiskId") or "source-disk-not-returned"
    enc = _truthy(_pick(snap, ("encrypted",)))
    key_ref = _pick(snap, KEY_FIELD_NAMES)
    if enc is True:
        code = "SNAPSHOT-ENCRYPTED" if key_ref else "SNAPSHOT-ENCRYPTED-KEY-TYPE-UNCONFIRMED"
        return _finding(
            state, code, snap_id,
            "{0}: encrypted{1} (source disk {2}).".format(
                snap_id,
                " with a visible key reference ({0})".format(mask(key_ref)) if key_ref else
                ", but no key reference is exposed by the read",
                source),
            "A snapshot inherits the encryption property of its source disk; use the KMS console "
            "check to name the key type when the read does not expose it.",
            "Report the encrypted state, then confirm the key type with the customer's console "
            "check.")
    if enc is False:
        return _finding(
            state, "SNAPSHOT-NOT-ENCRYPTED", snap_id,
            "{0}: not encrypted (source disk {1}).".format(snap_id, source),
            "This is the inheritance rule: an unencrypted disk yields an unencrypted snapshot. "
            "To get an encrypted copy the customer copies the snapshot with the encryption "
            "option selected, per references/snapshot-image-encryption.md, and this read then "
            "re-verifies it.",
            "Give the customer the copy-with-encryption steps, then re-read this snapshot id to "
            "confirm.")
    return _finding(
        state, "READ-PARTIAL", snap_id,
        "{0}: no encryption field returned, state unconfirmed.".format(snap_id),
        "Use the snapshot Detail pane check in references/query-recipes.md.",
        "Ask the customer for the snapshot Detail pane, then record the answer.")


def _check_scope(state, args):
    pairs = ((args.instance_id, "i-"), (args.disk_id, "d-"), (args.snapshot_id, "s-"))
    for value, prefix in pairs:
        if value and not value.startswith(prefix):
            _finding(
                state, "SCOPE-ID-SHAPE", value,
                "'{0}' does not carry the {1} prefix of an ECS object, so these ECS reads "
                "cannot see it.".format(
                    value, prefix),
                "Confirm the product line with the customer. Another line (for example a simple "
                "application server) goes to the handoff table in "
                "references/handoff-matrix.md; this skill reports no encryption answer for it.",
                "Ask the customer which product the id belongs to, then hand off if it is not "
                "an ECS resource.")
            return False
    return True


def _auth_findings(state):
    codes = set(state["codes"])
    if "CliNotFound" in codes:
        _finding(
            state, "CLI-NOT-FOUND", "aliyun CLI",
            "The CLI is unavailable, so no cloud fact could be read.",
            "Ask the customer to install the CLI and configure a profile with their own "
            "credentials; this skill never handles a credential itself.",
            "Ask the customer to install and configure the CLI, then re-run the read.")
    for code in sorted(codes & set(AUTH_DENY_CODES)):
        _finding(
            state, "AUTH-MISSING-PERMISSION", code,
            "A read was refused ({0}); the profile lacks the matching Describe permission.".format(
                code),
            "Tell the customer which action is missing and give the minimal policy snippet from "
            "references/ram-policies.md; do not retry with broader rights.",
            "Send the customer the missing action name plus the minimal policy snippet, then "
            "re-run the read.")
    if codes and len(codes - set(AUTH_DENY_CODES) - {"CliNotFound"}) > 0 and not state["findings"]:
        _finding(
            state, "READ-PARTIAL", ",".join(sorted(codes)),
            "The reads returned no usable data; the codes are recorded in the notes.",
            "Report the codes verbatim (masked), check the region and the id, and give the "
            "customer the console self-check path instead of a guess.",
            "Confirm RegionId and the resource id with the customer, then re-run the read.")


def _counts(disks, snapshots):
    def tri(rows):
        enc = un = unknown = 0
        for row in rows:
            value = _truthy(_pick(row, ("encrypted",)))
            if value is True:
                enc += 1
            elif value is False:
                un += 1
            else:
                unknown += 1
        return enc, un, unknown

    d_enc, d_un, d_unk = tri(disks)
    s_enc, s_un, s_unk = tri(snapshots)
    return {
        "instances": None,
        "disks_total": len(disks),
        "disks_encrypted": d_enc,
        "disks_unencrypted": d_un,
        "disks_unconfirmed": d_unk,
        "snapshots_total": len(snapshots),
        "snapshots_encrypted": s_enc,
        "snapshots_unencrypted": s_un,
        "snapshots_unconfirmed": s_unk,
    }


def _status(state, counts):
    codes = set(state["codes"])
    read_any = counts["disks_total"] + counts["snapshots_total"]
    if codes and not read_any:
        return "FAIL"
    if codes or state["notes"]:
        return "DEGRADED"
    if not read_any:
        return "DEGRADED"
    unconfirmed = [f["code"] for f in state["findings"]]
    if "DISK-ENCRYPTED-KEY-TYPE-UNCONFIRMED" in unconfirmed or \
       "DISK-ENCRYPTION-FIELD-MISSING" in unconfirmed or \
       "SNAPSHOT-ENCRYPTED-KEY-TYPE-UNCONFIRMED" in unconfirmed or \
       "SCOPE-ID-SHAPE" in unconfirmed:
        return "DEGRADED"
    return "OK"


def _next_action(state, status):
    present = {item["code"]: item["next_action"] for item in state["findings"]}
    for code in NEXT_PRIORITY:
        if code in present:
            return present[code]
    if status == "FAIL":
        return "Give the customer the failing read verbatim plus the console self-check path; do not report a guessed encryption state."
    return "Report the evidence table, then ask the customer which branch they want: state confirmation, an enablement path, or the snapshot and image chain."


def _row(row, label_fields):
    parts = []
    for label, key in label_fields:
        value = row.get(key)
        if value not in (None, ""):
            parts.append("{0}={1}".format(label, mask(value)))
    enc = encryption_fields(row)
    if enc:
        parts.append("encryption=" + json.dumps(enc, sort_keys=True, default=str))
    else:
        parts.append("encryption=not-returned")
    return "- " + "  ".join(parts)


def _render(state, args, instances, disks, snapshots, counts, status, next_action):
    lines = []
    lines.append("=== ECS disk and snapshot encryption evidence ===")
    lines.append("Skill       : {0} (read-only)".format(SKILL_NAME))
    lines.append("Session     : {0}".format(state["session_id"]))
    lines.append("Account     : {0}".format(state["identity"].get("trace_tag", "unresolved")))
    lines.append("Region      : {0}  endpoint hint {1}".format(
        args.region_id, region_endpoint_hint(args.region_id)))
    lines.append("Reads       : {0} {1} :: {2}".format(
        ECS_PRODUCT, ECS_API_VERSION, ", ".join(READ_ONLY_WHITELIST)))
    lines.append("Scope       : instance={0} disk={1} snapshot={2} all-disks={3} "
                 "snapshots-expanded={4} encrypted-only={5}".format(
                     args.instance_id or "-", args.disk_id or "-", args.snapshot_id or "-",
                     args.all_disks, args.include_snapshots or bool(args.snapshot_id),
                     args.encrypted_only))
    lines.append("")
    lines.append("-- Instances ({0}) --".format(len(instances)))
    if instances:
        for row in instances:
            lines.append(_row(row, [("instanceId", "InstanceId"), ("os", "OSName"),
                                    ("type", "InstanceType"), ("zone", "ZoneId"),
                                    ("state", "Status")]))
    elif args.instance_id or args.all_disks:
        lines.append("- none returned for this profile in this region (see findings)")
    else:
        lines.append("- not in scope: pass --instance-id to read the owning instance")
    lines.append("")
    lines.append("-- Disks ({0}) --".format(len(disks)))
    for row in disks:
        lines.append(_row(row, [("diskId", "DiskId"), ("kind", "Type"), ("category", "Category"),
                                ("sizeGiB", "Size"), ("state", "Status"),
                                ("instance", "InstanceId"), ("zone", "ZoneId")]))
    if not disks:
        lines.append("- none returned in this region (see findings)")
    lines.append("")
    lines.append("-- Snapshots ({0}) --".format(len(snapshots)))
    for row in snapshots:
        lines.append(_row(row, [("snapshotId", "SnapshotId"), ("sourceDisk", "SourceDiskId"),
                                ("sourceType", "SourceDiskType"), ("created", "CreationTime"),
                                ("state", "Status")]))
    if not snapshots:
        lines.append("- not expanded (pass --include-snapshots, or a --snapshot-id)")
    lines.append("")
    lines.append("-- Findings --")
    if state["findings"]:
        for item in state["findings"]:
            lines.append("[{0}] {1}".format(item["code"], item["detail"]))
            lines.append("   -> {0}".format(item["guidance"]))
    else:
        lines.append("- nothing to flag; every object read carried a conclusive encryption field")
    lines.append("")
    lines.append("-- What this read cannot see --")
    for boundary in READ_BOUNDARIES:
        lines.append("- {0}".format(boundary))
    if args.order_error:
        lines.append("")
        lines.append("-- Customer-pasted order text (not verified against any API) --")
        lines.append("- {0}".format(mask(args.order_error)))
    lines.append("")
    lines.append("-- Console check the customer can run --")
    for hint in CONSOLE_CHECK_HINTS:
        lines.append("- {0}".format(hint))
    if state["notes"]:
        lines.append("")
        lines.append("-- Read gaps --")
        for note in state["notes"]:
            lines.append("- {0}".format(note))
    lines.append("")
    lines.append("Summary: instances {0} | disks {1} ({2} encrypted, {3} not, {4} unconfirmed) "
                 "| snapshots {5} ({6} encrypted, {7} not, {8} unconfirmed) | findings {9}".format(
                     len(instances), counts["disks_total"], counts["disks_encrypted"],
                     counts["disks_unencrypted"], counts["disks_unconfirmed"],
                     counts["snapshots_total"], counts["snapshots_encrypted"],
                     counts["snapshots_unencrypted"], counts["snapshots_unconfirmed"],
                     len(state["findings"])))
    lines.append("STATUS: {0}".format(status))
    lines.append("NEXT_ACTION: {0}".format(next_action))
    return "\n".join(lines)


def _parse_args(argv=None):
    parser = argparse.ArgumentParser(
        prog="ecs_encryption_audit.py",
        description="Read-only evidence audit for ECS disk, snapshot and image encryption.")
    parser.add_argument("--region-id", required=True,
                        help="RegionId that owns the resources, for example cn-hangzhou")
    parser.add_argument("--instance-id", help="ECS instance id, i-****")
    parser.add_argument("--disk-id", help="disk id, d-****")
    parser.add_argument("--snapshot-id", help="snapshot id, s-****")
    parser.add_argument("--all-disks", action="store_true",
                        help="list every disk in the region instead of one object")
    parser.add_argument("--include-snapshots", action="store_true",
                        help="also read the snapshots behind the disks in scope")
    parser.add_argument("--encrypted-only", action="store_true",
                        help="ask the API for encrypted disks only (a filter, not a conclusion)")
    parser.add_argument("--order-error",
                        help="verbatim order or permission text the customer pasted; echoed, never interpreted as an error code")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS,
                        help="per-call timeout in seconds (default {0}, max {1})".format(
                            DEFAULT_TIMEOUT_SECONDS, MAX_TIMEOUT_SECONDS))
    parser.add_argument("--format", choices=("text", "json"), default="text")
    args = parser.parse_args(argv)
    if not REGION_RE.match(args.region_id or ""):
        parser.error("--region-id must look like a region id, for example cn-hangzhou")
    if not (args.instance_id or args.disk_id or args.snapshot_id or args.all_disks):
        parser.error("choose a scope: --instance-id, --disk-id, --snapshot-id or --all-disks")
    if args.instance_id and args.disk_id:
        parser.error("--instance-id and --disk-id are alternatives; pick one scope")
    return args


def main(argv=None):
    args = _parse_args(argv)
    timeout = max(1, min(int(args.timeout), MAX_TIMEOUT_SECONDS))
    state = {"session_id": new_session_id(), "notes": [], "codes": [], "findings": [],
             "identity": {}}

    if args.order_error:
        _finding(state, "ORDER-FAILURE-RECORDED", "customer-pasted text",
                 "An order or permission failure was reported by the customer; no cloud read "
                 "can see an order.",
                 "Walk the checklist in references/encryption-permissions.md against the pasted "
                 "text. Do not claim an error code that is not in it. The proven fallback is to "
                 "provision without encryption first, then move the data per the enablement path.",
                 "Ask the customer for the exact error text plus a console screenshot, then walk "
                 "the permission checklist.")

    try:
        state["identity"] = fetch_caller(session_id=state["session_id"], timeout=timeout)
    except CliError as exc:
        _note(state, "identity read -> {0}".format(exc), code=exc.code)

    scope_ok = _check_scope(state, args)
    instances, disks, snapshots = [], [], []
    if scope_ok:
        instances = read_instances(state, args, state["session_id"], timeout)
        disks = read_disks(state, args, state["session_id"], timeout)
        snapshots = read_snapshots(state, args, disks, state["session_id"], timeout)
        if not instances and not disks and not snapshots:
            _finding(
                state, "SCOPE-NO-OBJECTS", args.region_id,
                "No instance, disk or snapshot matched in {0} for this account.".format(
                    args.region_id),
                "Check the region and the id with the customer, and confirm the profile belongs "
                "to the account that owns the resource; an empty list is not evidence of an "
                "unencrypted disk.",
                "Ask the customer to confirm RegionId, the resource id and the account, then "
                "re-run the read.")
    for disk in disks:
        judge_disk(state, disk)
    for snap in snapshots:
        judge_snapshot(state, snap)
    if not disks and not args.all_disks and not snapshots and scope_ok:
        _note(state, "no disk row to judge; the encryption answer is not asserted")
    _auth_findings(state)

    counts = _counts(disks, snapshots)
    counts["instances"] = len(instances)
    status = _status(state, counts)
    next_action = _next_action(state, status)

    if args.format == "json":
        payload = {
            "skill": SKILL_NAME,
            "readOnlyWhitelist": list(READ_ONLY_WHITELIST),
            "session": state["session_id"],
            "identity": state["identity"].get("trace_tag", ""),
            "regionId": args.region_id,
            "scope": {
                "instanceId": args.instance_id,
                "diskId": args.disk_id,
                "snapshotId": args.snapshot_id,
                "allDisks": args.all_disks,
                "includeSnapshots": args.include_snapshots,
                "encryptedOnly": args.encrypted_only,
            },
            "instances": instances,
            "disks": disks,
            "snapshots": snapshots,
            "counts": counts,
            "findings": state["findings"],
            "notes": state["notes"],
            "readBoundaries": list(READ_BOUNDARIES),
            "consoleChecks": list(CONSOLE_CHECK_HINTS),
            "summary": "disks {0}/{1} encrypted, snapshots {2}/{3} encrypted".format(
                counts["disks_encrypted"], counts["disks_total"],
                counts["snapshots_encrypted"], counts["snapshots_total"]),
            "STATUS": status,
            "NEXT_ACTION": next_action,
        }
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
    else:
        print(_render(state, args, instances, disks, snapshots, counts, status, next_action))
    return 0 if status in ("OK", "DEGRADED") else 1


if __name__ == "__main__":
    sys.exit(main())
