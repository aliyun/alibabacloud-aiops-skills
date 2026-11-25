#!/usr/bin/env python3
"""
app_server_deploy_guide.py -- single entry point of the ECS game and
application server deployment guide skill.
=============================================================================
SECURITY: This script reaches the cloud ONLY through ``_cli.run_cli``, which
enforces the action whitelist in ``_constants.py``. Evidence queries mutate
nothing and run on their own. Two capabilities change state and are gated:
one confirmed Cloud Assistant inspection reading per call (class B), and one
confirmed pre-cleanup snapshot of one named disk (class C). Both are refused
unless this run carries a confirmation repeating, verbatim, the exact command
or disk id of THAT call. Nothing outside the whitelist is ever issued, and no
install, cleanup, deletion, restart, firewall edit or service change is ever
performed or scripted here -- those stay numbered steps for a human.

Credentials: resolved exclusively by the aliyun CLI default credential chain.
This script never reads, accepts, stores, prints or passes key material.

Every run ends with ``STATUS: OK|DEGRADED|FAIL`` and one ``NEXT_ACTION:`` line,
and prints a 32-character hex session id that every CLI call of the run
carries in its --user-agent value.

Usage examples:

  python3 scripts/app_server_deploy_guide.py \
      --region-id cn-hangzhou --instance-id i-bp1example000000 \
      --intent fresh-install --server-type game

  python3 scripts/app_server_deploy_guide.py \
      --region-id cn-shanghai --instance-id i-bp1example000000 \
      --intent deploy-failure --error-text "cannot create new file during install"

  python3 scripts/app_server_deploy_guide.py \
      --region-id cn-hangzhou --instance-id i-bp1example000000 \
      --probe inodes --confirm-probe "df -i"

  python3 scripts/app_server_deploy_guide.py \
      --region-id cn-hangzhou --intent selection \
      --want-instance-type ecs.hfg7.large --zone-id cn-hangzhou-j

  python3 scripts/app_server_deploy_guide.py \
      --region-id cn-hangzhou --instance-id i-bp1example000000 \
      --snapshot-disk-id d-bp1exampledisk00 --confirm-snapshot d-bp1exampledisk00
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time

import _cli
from _constants import (
    ACTION_CREATE_SNAPSHOT,
    ACTION_DESCRIBE_AVAILABLE_RESOURCE,
    ACTION_DESCRIBE_INSTANCES,
    ACTION_DESCRIBE_INSTANCE_STATUS,
    ACTION_DESCRIBE_INVOCATIONS,
    ACTION_GET_CALLER_IDENTITY,
    ACTION_RUN_COMMAND,
    CLI_TIMEOUT_SECONDS,
    CODE_CONFIRMATION_REQUIRED,
    CODE_IMPLICIT_DENY,
    CODE_INVALID_CREDENTIAL,
    CODE_NO_PERMISSION,
    DEPLOY_PATH_DOCS,
    DISK_ID_RE,
    EXIT_FOR_STATUS,
    GUEST_OUTPUT_MAX_CHARS,
    GUEST_POLL_INTERVAL_SECONDS,
    GUEST_PROBES,
    GUEST_WAIT_DEFAULT_SECONDS,
    GUEST_WAIT_MAX_SECONDS,
    HANDOFF_TARGETS,
    HUMAN_ONLY_CHECKS,
    INSPECTION_COMMAND_NAME,
    INSPECTION_DESCRIPTION,
    INSTANCE_ID_RE,
    INSTANCE_TYPE_RE,
    LIMITATIONS,
    MANUAL_PREREQUISITES,
    PAGE_SIZE,
    PATH_LABELS,
    POST_DEPLOY_HUMAN_CHECKS,
    PRODUCT_ECS,
    PRODUCT_STS,
    REGION_RE,
    SCRIPT_TYPE_LINUX,
    SNAPSHOT_BILLING_NOTE,
    SNAPSHOT_DESCRIPTION,
    SNAPSHOT_NAME_PREFIX,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    SYMPTOM_SIGNATURES,
    ZONE_ID_RE,
)

# Statuses a Cloud Assistant invocation can sit in while still unfinished.
GUEST_IN_PROGRESS_SET = {"pending", "running", "invoking", "scheduled",
                         "stopping"}

# --- whitelist integrity self-checks (pure, run at import) ----------------------
# A probe must be a bare listing command line: no shell metacharacters, no
# chaining. run_probe is the only writer of CommandContent, and it only ever
# takes from this map.
_PROBE_SHAPE_RE = re.compile(r"^[a-z0-9][A-Za-z0-9 ./=+-]*$")
for _probe in GUEST_PROBES.values():
    assert _PROBE_SHAPE_RE.match(_probe["command"]), _probe["command"]
    for _ch in (";", "|", "&", "`", "$", ">", "<", "\n"):
        assert _ch not in _probe["command"], _probe["command"]

INSTANCE_INTENTS = ("fresh-install", "image-copy", "migration", "pre-check",
                    "deploy-failure")


def _dig(obj, *path):
    node = obj
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def _unwrap(body, outer, inner):
    """Return body[outer][inner] as a list, tolerating both list shapes."""
    layer = _dig(body, outer, inner)
    if layer is None:
        return []
    if isinstance(layer, dict):
        layer = layer.get("Item") or []
    return layer if isinstance(layer, list) else []


class Evidence:
    """One line per step attempted, failures included; nothing is silent."""

    def __init__(self):
        self.rows = []

    def add(self, step, action, result, detail, code=""):
        self.rows.append({"step": step, "action": action, "result": result,
                          "detail": _cli.mask_secrets(detail)[:400],
                          "code": code})

    def degraded(self):
        return any(r["result"] in ("failed", "refused", "unconfirmed",
                                   "unread") for r in self.rows)


def classify_symptom(text):
    """Return (branch, statement, target_key, matched) for customer wording."""
    low = (text or "").lower()
    if not low.strip():
        return None
    for branch, needles, statement, target in SYMPTOM_SIGNATURES:
        for needle in needles:
            if needle in low:
                return branch, statement, target, needle
    return None


def stock_verdict(zones):
    """Summarise the availability query without inventing a status."""
    seen_available = False
    seen_sold_out = False
    rows = []
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        zone_id = str(zone.get("ZoneId") or "not returned")
        z_status = str(zone.get("Status") or "not returned")
        z_category = str(zone.get("StatusCategory") or "")
        for res in _unwrap(zone, "AvailableResources", "AvailableResource"):
            r_status = str(res.get("Status") or z_status)
            r_value = str(res.get("Value") or zone_id)
            rows.append((r_value, r_status,
                         str(res.get("StatusCategory") or z_category)))
            if r_status == "Available":
                seen_available = True
            elif r_status == "SoldOut":
                seen_sold_out = True
    if seen_available:
        verdict = "IN STOCK (at query time)"
    elif seen_sold_out:
        verdict = "SOLD OUT (at query time)"
    else:
        verdict = "UNKNOWN (no recognised status returned)"
    return verdict, rows


def clip(text):
    text = text or ""
    if len(text) <= GUEST_OUTPUT_MAX_CHARS:
        return text
    return text[:GUEST_OUTPUT_MAX_CHARS] + "\n  ...[truncated by this skill]"


def invocation_result(rows, invoke_id):
    """Take the status and output of the invocation this run dispatched."""
    row = {}
    for item in rows:
        if isinstance(item, dict) and str(item.get("InvokeId") or "") == invoke_id:
            row = item
            break
    if not row and rows and isinstance(rows[0], dict):
        row = rows[0]
    status = str(row.get("InvocationStatus") or row.get("InvokeStatus") or "")
    output = ""
    for inst_row in _unwrap(row, "InvokeInstances", "InvokeInstance"):
        if isinstance(inst_row, dict):
            status = str(inst_row.get("InvocationStatus") or status)
            output = str(inst_row.get("Output") or "")
            break
    return status, output


def render_facts(instance):
    """Pull the fields this tier's decisions rest on; report gaps honestly."""
    private_ips = (_dig(instance, "VpcAttributes", "PrivateIpAddress",
                        "IpAddress")
                   or _dig(instance, "InnerIpAddresses", "InnerIpAddress")
                   or [])
    public_ips = (_dig(instance, "PublicIpAddress", "IpAddress") or [])
    if not public_ips:
        eip = _dig(instance, "EipAddress", "IpAddress")
        public_ips = [eip] if eip else []
    sec_groups = _dig(instance, "SecurityGroupIds", "SecurityGroupId") or []
    return {
        "instance_id": instance.get("InstanceId") or "not returned",
        "name": instance.get("InstanceName") or "not returned",
        "status": instance.get("Status") or "not returned",
        "instance_type": instance.get("InstanceType") or "not returned",
        "zone": instance.get("ZoneId") or "not returned",
        "os": instance.get("OSType") or "not returned",
        "image_id": instance.get("ImageId") or "not returned",
        "charge_type": instance.get("InstanceChargeType") or "not returned",
        "private_ip": ", ".join(str(x) for x in private_ips) or "not returned",
        "public_ip": ", ".join(str(x) for x in public_ips) or "none reported",
        "security_groups": ", ".join(str(x) for x in sec_groups) or "not returned",
    }


def run_probe(args, instance, evidence):
    """Class B: dispatch ONE published reading, then fetch its result back."""
    probe = args.probe
    if not probe:
        return {"requested": False}
    entry = GUEST_PROBES[probe]
    command = entry["command"]
    result = {"requested": True, "name": probe, "command": command,
              "ran": False, "outcome": "", "detail": "", "invoke_id": "",
              "invocation_status": "", "output": ""}
    os_reported = str(instance.get("OSType") or "").lower()
    if os_reported.startswith("win"):
        result["outcome"] = "refused"
        result["detail"] = ("the published guest readings of this release are "
                            "Linux shell probes; on a Windows guest every "
                            "check stays a human step run in the console "
                            "session. Ask the operator to run the check and "
                            "paste the output.")
        return result
    if args.confirm_probe != command:
        result["outcome"] = "unconfirmed"
        result["detail"] = ("no confirmation repeating this exact command, so "
                            "nothing ran inside the guest. Tell the operator: "
                            "one command (%s), on instance %s, it only prints "
                            "state and changes nothing, and approval covers "
                            "this one call. Then re-run with --confirm-probe "
                            "carrying the command verbatim."
                            % (command, args.instance_id))
        return result
    encoded = _cli.encode_command(command)
    try:
        body = _cli.run_cli(PRODUCT_ECS, ACTION_RUN_COMMAND, {
            "RegionId": args.region_id,
            "Type": SCRIPT_TYPE_LINUX,
            "CommandContent": encoded,
            "ContentEncoding": "Base64",
            "Name": INSPECTION_COMMAND_NAME,
            "Description": INSPECTION_DESCRIPTION,
            "InstanceId.1": args.instance_id,
            "Timeout": str(args.guest_wait),
        }, session_id=args.session_id, timeout=args.timeout,
            confirmation=encoded)
    except _cli.CliError as exc:
        evidence.add("guest-inspection", ACTION_RUN_COMMAND, "failed",
                     exc.message, exc.code)
        result["outcome"] = ("unconfirmed" if exc.code == CODE_CONFIRMATION_REQUIRED
                             else "failed")
        result["detail"] = exc.message
        return result
    evidence.add("guest-inspection", ACTION_RUN_COMMAND, "ok",
                 "one confirmed reading dispatched")
    result["ran"] = True
    invoke_id = str((body or {}).get("InvokeId") or "")
    result["invoke_id"] = invoke_id or "not returned"
    poll_probe(args, invoke_id, result, evidence)
    return result


def poll_probe(args, invoke_id, result, evidence):
    """Poll the dispatched reading until it ends or the wait budget runs out."""
    params = {"RegionId": args.region_id, "InstanceId": args.instance_id,
              "IncludeOutput": "true", "ContentEncoding": "PlainText",
              "PageSize": PAGE_SIZE}
    if invoke_id:
        params["InvokeId"] = invoke_id
    deadline = time.monotonic() + args.guest_wait
    while True:
        try:
            body = _cli.run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INVOCATIONS,
                                params, session_id=args.session_id,
                                timeout=args.timeout)
        except _cli.CliError as exc:
            evidence.add("guest-readback", ACTION_DESCRIBE_INVOCATIONS,
                         "failed", exc.message, exc.code)
            result["outcome"] = "unread"
            result["detail"] = ("the reading was dispatched but this skill "
                                "could not fetch its result back: %s"
                                % exc.message)
            return
        rows = _unwrap(body, "Invocations", "Invocation")
        status, output = invocation_result(rows, invoke_id)
        evidence.add("guest-readback", ACTION_DESCRIBE_INVOCATIONS, "ok",
                     "invocation status %s" % (status or "not returned"))
        result["invocation_status"] = status or "not returned"
        if output:
            result["output"] = clip(_cli.decode_output(output))
        if status and status.lower().strip() not in GUEST_IN_PROGRESS_SET:
            result["outcome"] = "returned"
            result["detail"] = "the reading completed; output is below"
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            result["outcome"] = "still running"
            result["detail"] = ("the reading has not finished within %ss; "
                                "nothing beyond its dispatch status is "
                                "claimed" % args.guest_wait)
            return
        time.sleep(min(GUEST_POLL_INTERVAL_SECONDS, max(1, int(remaining))))


def run_snapshot(args, evidence):
    """Class C: one snapshot of one disk, on a confirmation naming that disk."""
    disk_id = args.snapshot_disk_id
    if not disk_id:
        return {"requested": False}
    result = {"requested": True, "disk_id": disk_id, "created": False,
              "snapshot_id": "", "detail": ""}
    if not re.match(DISK_ID_RE, disk_id):
        result["detail"] = ("not shaped like a disk id, so no call was made; "
                            "the snapshot-first rule then stays a manual "
                            "console step")
        return result
    if args.confirm_snapshot != disk_id:
        result["detail"] = ("no confirmation naming this disk, so no snapshot "
                            "was taken. %s Tell the operator that, then "
                            "re-run with --confirm-snapshot carrying that "
                            "disk id." % SNAPSHOT_BILLING_NOTE)
        return result
    try:
        body = _cli.run_cli(PRODUCT_ECS, ACTION_CREATE_SNAPSHOT, {
            "RegionId": args.region_id,
            "DiskId": disk_id,
            "SnapshotName": SNAPSHOT_NAME_PREFIX + args.session_id[:8],
            "Description": SNAPSHOT_DESCRIPTION,
        }, session_id=args.session_id, timeout=args.timeout,
            confirmation=disk_id)
    except _cli.CliError as exc:
        evidence.add("pre-cleanup-snapshot", ACTION_CREATE_SNAPSHOT,
                     "failed", exc.message, exc.code)
        result["detail"] = exc.message
        return result
    evidence.add("pre-cleanup-snapshot", ACTION_CREATE_SNAPSHOT, "ok",
                 "one snapshot created for %s" % disk_id)
    result["created"] = True
    result["snapshot_id"] = str((body or {}).get("SnapshotId") or "not returned")
    result["detail"] = SNAPSHOT_BILLING_NOTE
    return result


def gather(args, evidence):
    """Identity plus instance lookup. Returns (out, control) with control in
    {abort, continue}; a credential or permission abort stops the run."""
    out = {"uid": "", "identity_type": "", "instances": [], "errors": []}
    try:
        identity = _cli.run_cli(PRODUCT_STS, ACTION_GET_CALLER_IDENTITY, {},
                                session_id=args.session_id,
                                timeout=args.timeout)
        out["uid"] = str(identity.get("AccountId") or "")
        out["identity_type"] = str(identity.get("IdentityType") or "Unknown")
        evidence.add("identity", ACTION_GET_CALLER_IDENTITY, "ok",
                     "account verified")
    except _cli.CliError as exc:
        evidence.add("identity", ACTION_GET_CALLER_IDENTITY, "failed",
                     exc.message, exc.code)
        out["errors"].append(("identity", exc.code, exc.message))
        return out, "abort"

    params = {"RegionId": args.region_id, "PageSize": PAGE_SIZE,
              "PageNumber": 1}
    label = "region scan"
    if args.instance_id:
        params["InstanceIds"] = json.dumps([args.instance_id])
        label = "instance-id"
    elif args.instance_name:
        params["InstanceName"] = args.instance_name
        label = "instance-name"
    elif args.private_ip:
        params["PrivateIpAddresses"] = args.private_ip
        label = "private-ip"
    try:
        body = _cli.run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INSTANCES, params,
                            session_id=args.session_id, timeout=args.timeout)
        out["instances"] = _unwrap(body, "Instances", "Instance")
        evidence.add("instance-facts(%s)" % label, ACTION_DESCRIBE_INSTANCES,
                     "ok", "%d instance(s) matched" % len(out["instances"]))
    except _cli.CliError as exc:
        evidence.add("instance-facts", ACTION_DESCRIBE_INSTANCES, "failed",
                     exc.message, exc.code)
        out["errors"].append(("instance-facts", exc.code, exc.message))
        return out, "abort"
    return out, "continue"


def read_instance_status(args, evidence):
    """The readiness gate: Running or not, straight from the status call."""
    try:
        body = _cli.run_cli(PRODUCT_ECS, ACTION_DESCRIBE_INSTANCE_STATUS, {
            "RegionId": args.region_id,
            "InstanceId.1": args.instance_id,
            "PageSize": PAGE_SIZE,
        }, session_id=args.session_id, timeout=args.timeout)
        rows = _unwrap(body, "InstanceStatuses", "InstanceStatus")
        status = str(rows[0].get("Status") or "") if rows else ""
        evidence.add("instance-status", ACTION_DESCRIBE_INSTANCE_STATUS, "ok",
                     "reported %s" % (status or "nothing"))
        return status or "not returned"
    except _cli.CliError as exc:
        evidence.add("instance-status", ACTION_DESCRIBE_INSTANCE_STATUS,
                     "failed", exc.message, exc.code)
        return ""


def read_stock(args, evidence):
    """Optional availability check for the type the customer wants to buy."""
    try:
        params = {"RegionId": args.region_id,
                  "DestinationResource": "InstanceType",
                  "InstanceType": args.want_instance_type}
        if args.zone_id:
            params["ZoneId"] = args.zone_id
        body = _cli.run_cli(PRODUCT_ECS, ACTION_DESCRIBE_AVAILABLE_RESOURCE,
                            params, session_id=args.session_id,
                            timeout=args.timeout)
        zones = _unwrap(body, "AvailableZones", "AvailableZone")
        verdict, rows = stock_verdict(zones)
        evidence.add("stock-check", ACTION_DESCRIBE_AVAILABLE_RESOURCE, "ok",
                     "%d zone record(s) returned" % len(zones))
        return {"type": args.want_instance_type,
                "zone": args.zone_id or "all zones in region",
                "verdict": verdict, "rows": rows}
    except _cli.CliError as exc:
        evidence.add("stock-check", ACTION_DESCRIBE_AVAILABLE_RESOURCE,
                     "failed", exc.message, exc.code)
        return None


def docs_for(intent, server_type):
    keys = {
        "fresh-install": (("instance-selection", "high-clock", "free-trial")
                          if server_type == "game" else
                          ("instance-selection", "gpu-families")),
        "image-copy": ("custom-image",),
        "migration": ("server-migration",),
        "selection": ("instance-selection", "high-clock", "gpu-families",
                      "free-trial"),
        "pre-check": (),
        "deploy-failure": (),
        "unknown": ("instance-selection",),
    }.get(intent, ("instance-selection",))
    return [DEPLOY_PATH_DOCS[k] for k in keys]


def build_guidance(args, symptom, facts, status_live):
    """Path guidance + numbered manual steps; never a runnable mutation."""
    guidance = []
    handoffs = []
    intent = args.intent
    if intent in PATH_LABELS:
        guidance.append(PATH_LABELS[intent])
        if intent == "fresh-install":
            guidance.append("Buy or reuse the instance (the console purchase "
                            "flow is a human step), then install the server "
                            "software inside the guest yourself: this skill "
                            "never installs.")
        elif intent == "image-copy":
            guidance.append("Build one instance, create the custom image "
                            "from it, then launch the remaining instances "
                            "from that image; cross-account sharing follows "
                            "the shared-image document. After launching, "
                            "this skill can verify how many of the new "
                            "instances reached Running.")
        elif intent == "migration":
            guidance.append("Follow the server-migration document for the "
                            "tool path; this skill verifies the target "
                            "instance only. Whole-site deep migration "
                            "diagnosis belongs to its own tier.")
        elif intent == "selection":
            guidance.append("For game and single-thread-sensitive servers "
                            "the high-clock-speed (hf) families are the "
                            "sizing reference; GPU-backed applications use "
                            "the GPU family document; small personal trials "
                            "can start from the free-trial scenario list.")
    elif intent == "pre-check":
        guidance.append("Pre-deploy readiness check: the instance gate above "
                        "plus the 'space' and 'inodes' probes (or the "
                        "customer's own df -h / df -i output) decide whether "
                        "the target file system can receive the install.")
    elif intent == "deploy-failure":
        guidance.append("Deployment failure triage: the symptom match and "
                        "any confirmed readings above decide the next tier. "
                        "This package guides deployment; it does not "
                        "install, clean, or restart anything.")
    else:
        guidance.append("Intent unclear: the four supported deployment paths "
                        "are listed in references/deploy-paths.md; ask one "
                        "clarifying question before choosing.")
    guidance.extend(MANUAL_PREREQUISITES)
    if status_live and status_live != "Running" and facts:
        handoffs.append(("instance is not Running (live status: %s)"
                         % status_live,
                         HANDOFF_TARGETS["instance-state"],
                         "deployment cannot start on a non-running instance"))
    if symptom:
        branch, statement, target_key, _matched = symptom
        if target_key in HANDOFF_TARGETS:
            handoffs.append((statement, HANDOFF_TARGETS[target_key],
                             "the symptom belongs to that tier; this skill "
                             "stops at identification and evidence"))
        elif target_key == "stock":
            guidance.append("Stock is a moment-in-time answer: another zone, "
                            "another type, or waiting are the customer's "
                            "options; purchasing and spec changes are console "
                            "flows this skill guides but never submits.")
        elif target_key == "post-deploy-check":
            guidance.extend(POST_DEPLOY_HUMAN_CHECKS)
    if not facts:
        guidance.append("If the customer actually holds a Simple Application "
                        "Server rather than an ECS instance, the client "
                        "management document shows how to tell the products "
                        "apart before continuing.")
    return guidance, handoffs


def build_findings(args, facts, status_live, stock, symptom, probe, snapshot):
    findings = []
    if facts:
        findings.append("Instance %s (%s) in %s is reported %s by the "
                        "instance-list query."
                        % (facts["instance_id"], facts["instance_type"],
                           args.region_id, facts["status"]))
    if status_live == "Running":
        findings.append("The live status call confirms Running: the deploy "
                        "precondition on instance state is met.")
    elif status_live and status_live != "not returned":
        findings.append("The live status call reports %s, so the instance is "
                        "not ready to receive a deployment right now."
                        % status_live)
    if stock:
        findings.append("Stock for %s in %s: %s. This is the state at query "
                        "time, not a purchase guarantee."
                        % (stock["type"], stock["zone"], stock["verdict"]))
    if symptom:
        findings.append("Symptom wording matched (%s): %s"
                        % (symptom[3], symptom[1]))
    if probe.get("requested"):
        if probe.get("outcome") == "returned":
            findings.append("The confirmed '%s' reading completed with status "
                            "%s; its output is in the GUEST INSPECTION "
                            "section." % (probe["name"],
                                          probe["invocation_status"]))
        else:
            findings.append("The '%s' reading did not complete through this "
                            "skill: %s" % (probe["name"],
                                           probe.get("detail", "")))
    if snapshot.get("requested"):
        if snapshot.get("created"):
            findings.append("Snapshot-first satisfied: snapshot %s of disk "
                            "%s created (billable until a human deletes it)."
                            % (snapshot["snapshot_id"], snapshot["disk_id"]))
        else:
            findings.append("The pre-cleanup snapshot did not run: %s"
                            % snapshot.get("detail", ""))
    return findings


def render_text(rep):
    line = "=" * 72
    out = [line,
           "ECS GAME / APPLICATION SERVER DEPLOYMENT GUIDE - evidence report",
           line,
           "session id : %s" % rep["session_id"],
           "account    : %s (%s)" % (rep["uid"] or "not returned",
                                     rep["identity_type"] or "-"),
           "",
           "DECLARED INPUTS"]
    for key, value in rep["declared_inputs"].items():
        out.append("  %-22s %s" % (key + ":", value))
    out.append("")
    if rep.get("instance_error"):
        out.append("INSTANCE LOOKUP")
        out.append("  %s" % rep["instance_error"])
        out.append("")
    if rep["facts"]:
        out.append("INSTANCE FACTS")
        for key in ("instance_id", "name", "status", "instance_type", "zone",
                    "os", "image_id", "charge_type", "private_ip",
                    "public_ip", "security_groups"):
            out.append("  %-14s %s" % (key, rep["facts"][key]))
        out.append("")
    if rep["candidates"]:
        out.append("AMBIGUOUS MATCHES (ask the customer to confirm one id)")
        for row in rep["candidates"]:
            out.append("  %s | %s | %s | %s" % row)
        out.append("")
    if rep["stock"]:
        out.append("STOCK CHECK")
        out.append("  type %s in %s -> %s"
                   % (rep["stock"]["type"], rep["stock"]["zone"],
                      rep["stock"]["verdict"]))
        for value, status, category in rep["stock"]["rows"]:
            out.append("    %-24s %-10s %s" % (value, status, category))
        out.append("")
    if rep["symptom"]:
        out.append("SYMPTOM MATCH")
        out.append("  quoted wording : %s" % rep["symptom"]["matched"])
        out.append("  reading        : %s" % rep["symptom"]["statement"])
        out.append("")
    if rep["probe"].get("requested"):
        out.append("GUEST INSPECTION (class B, per-call confirmation)")
        out.append("  probe    : %s (%s)" % (rep["probe"]["name"],
                                             rep["probe"]["command"]))
        out.append("  outcome  : %s" % rep["probe"]["outcome"])
        if rep["probe"].get("invoke_id"):
            out.append("  invoke   : %s [%s]"
                       % (rep["probe"]["invoke_id"],
                          rep["probe"]["invocation_status"]))
        if rep["probe"].get("output"):
            out.append("  guest reading:")
            out.extend("    " + text for text in
                       rep["probe"]["output"].splitlines())
        if rep["probe"].get("detail"):
            out.append("  note     : %s" % rep["probe"]["detail"])
        out.append("")
    if rep["snapshot"].get("requested"):
        out.append("PRE-CLEANUP SNAPSHOT (class C, per-call confirmation)")
        out.append("  disk     : %s" % rep["snapshot"]["disk_id"])
        out.append("  created  : %s"
                   % (("yes: " + rep["snapshot"]["snapshot_id"])
                      if rep["snapshot"]["created"] else "no"))
        if rep["snapshot"].get("detail"):
            out.append("  note     : %s" % rep["snapshot"]["detail"])
        out.append("")
    out.append("DEPLOYMENT PATH GUIDANCE (manual steps for a human)")
    for step, text in enumerate(rep["guidance"], 1):
        out.append("  %d. %s" % (step, text))
    out.append("")
    if rep["docs"]:
        out.append("VERIFIED DOCUMENTS")
        for doc in rep["docs"]:
            out.append("  - %s: %s" % (doc["title"], doc["url"]))
        out.append("")
    out.append("MANUAL CHECKS THE SKILL WILL NOT RUN")
    for text in rep["human_checks"]:
        out.append("  - %s" % text)
    out.append("")
    if rep["findings"]:
        out.append("FINDINGS")
        for text in rep["findings"]:
            out.append("  - %s" % text)
        out.append("")
    if rep["handoffs"]:
        out.append("HANDOFF")
        for statement, target, reason in rep["handoffs"]:
            out.append("  - %s -> %s (%s)" % (statement, target, reason))
        out.append("")
    out.append("EVIDENCE LOG")
    for row in rep["evidence"]:
        suffix = (" | " + row["detail"]) if row["detail"] else ""
        out.append("  %-26s %-26s %-12s %s%s"
                   % (row["step"], row["action"], row["result"],
                      row["code"] or "-", suffix))
    out.append("")
    out.append("RISK NOTES")
    for text in rep["risk_notes"]:
        out.append("  - %s" % text)
    out.append("")
    out.append("LIMITATIONS")
    for text in rep["limitations"]:
        out.append("  - %s" % text)
    out.append("")
    out.append("SUMMARY")
    out.append("  %s" % rep["summary"])
    out.append("")
    out.append("STATUS: %s" % rep["status"])
    out.append("NEXT_ACTION: %s" % rep["next_action"])
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="ECS game / application server deployment guide: "
                    "evidence-backed readiness, stock and symptom triage "
                    "with confirmation-gated guest inspection and snapshot.",
    )
    parser.add_argument("--region-id", "--region", dest="region_id",
                        help="required: region of the target instance "
                             "(never guessed)")
    parser.add_argument("--instance-id", default=None,
                        help="target instance id (i-...)")
    parser.add_argument("--instance-name", default=None,
                        help="lookup filter when no id is known")
    parser.add_argument("--private-ip", default=None,
                        help="lookup filter when no id is known")
    parser.add_argument("--intent", default="unknown",
                        choices=("fresh-install", "image-copy", "migration",
                                 "selection", "pre-check", "deploy-failure",
                                 "unknown"),
                        help="what the customer wants this session for")
    parser.add_argument("--server-type", default="game",
                        choices=("game", "application"),
                        help="selects sizing references in the guidance")
    parser.add_argument("--want-instance-type", default=None,
                        help="instance type to check stock for")
    parser.add_argument("--zone-id", default=None,
                        help="optional zone narrowing for the stock check")
    parser.add_argument("--error-text", default="",
                        help="customer's wording or on-screen error, verbatim")
    parser.add_argument("--note", default="",
                        help="one extra line of customer context, routing "
                             "only")
    parser.add_argument("--probe", default=None, choices=sorted(GUEST_PROBES),
                        help="dispatch this published inspection reading "
                             "(class B, gated)")
    parser.add_argument("--confirm-probe", default=None,
                        help="the exact probe command string, repeated: this "
                             "single call's confirmation")
    parser.add_argument("--guest-wait", type=int,
                        default=GUEST_WAIT_DEFAULT_SECONDS,
                        help="seconds to wait for a probe result "
                             "(max %s)" % GUEST_WAIT_MAX_SECONDS)
    parser.add_argument("--snapshot-disk-id", default=None,
                        help="disk for the class C pre-cleanup snapshot")
    parser.add_argument("--confirm-snapshot", default=None,
                        help="that same disk id, repeated: this single "
                             "call's confirmation")
    parser.add_argument("--timeout", type=int, default=CLI_TIMEOUT_SECONDS,
                        help="per-call timeout in seconds")
    parser.add_argument("--output", default="text", choices=("text", "json"))
    args = parser.parse_args()

    args.session_id = _cli.new_session_id()
    args.guest_wait = max(5, min(args.guest_wait, GUEST_WAIT_MAX_SECONDS))

    def fail(detail, next_action):
        # Machine-readable mode MUST emit ONLY a JSON object on stdout even on the
        # argument-validation failure path; otherwise the aggregate harness adapter's
        # json.loads() chokes on the human trailer (Extra data) and the tool result
        # degrades to a string. The STATUS:/NEXT_ACTION: text trailer is for the
        # human report path only.
        if args.output == "json":
            print(json.dumps({"session_id": args.session_id, "status": STATUS_FAIL,
                              "error": detail, "next_action": next_action},
                             indent=2, ensure_ascii=False))
        else:
            print("session id : %s" % args.session_id)
            print("[FAIL] %s" % detail)
            print("STATUS: %s" % STATUS_FAIL)
            print("NEXT_ACTION: %s" % next_action)
        sys.exit(EXIT_FOR_STATUS[STATUS_FAIL])

    if not args.region_id or not re.match(REGION_RE, args.region_id):
        fail("region is required and must look like cn-hangzhou",
             "re-run with --region-id <the region of the instance>; this "
             "skill never guesses a region")
    if args.instance_id and not re.match(INSTANCE_ID_RE, args.instance_id):
        fail("instance id %r is not shaped like i-..." % args.instance_id,
             "re-run with the exact instance id from the console")
    if args.want_instance_type and not re.match(
            INSTANCE_TYPE_RE, args.want_instance_type):
        fail("instance type %r rejected by the input pattern"
             % args.want_instance_type,
             "re-run with the exact type name, e.g. ecs.hfg7.large")
    if args.zone_id and not re.match(ZONE_ID_RE, args.zone_id):
        fail("zone id %r rejected by the input pattern" % args.zone_id,
             "re-run with the exact zone name, e.g. cn-hangzhou-j")

    ev = Evidence()
    gathered, control = gather(args, ev)
    if control == "abort":
        step, code, message = gathered["errors"][0]
        if code == CODE_INVALID_CREDENTIAL:
            fail("%s step failed: %s" % (step, message),
                 _cli.credential_remediation())
        if code == CODE_NO_PERMISSION:
            fail("%s step refused: %s" % (step, message),
                 "NoPermission means the credential lacks that exact action: "
                 "grant the single missing action named under "
                 "references/ram-policies.md, then re-run this identical "
                 "command")
        if code == CODE_IMPLICIT_DENY:
            fail("%s step refused: %s" % (step, message),
                 "ImplicitDeny means a control or group policy blocks this "
                 "action: ask the account administrator to lift that deny "
                 "(see references/ram-policies.md); never work around it "
                 "with a broader grant. Then re-run this identical command")
        fail("%s step failed: %s" % (step, message),
             "check the region id and the CLI account, then re-run")

    instances = gathered["instances"]
    candidates = []
    facts = None
    instance_error = ""
    needs_instance = (bool(args.instance_id or args.instance_name
                           or args.private_ip)
                      or args.intent in INSTANCE_INTENTS or bool(args.probe))
    if not instances:
        if needs_instance:
            instance_error = ("no instance matched in %s%s"
                              % (args.region_id,
                                 (" for %s" % (args.instance_id
                                               or args.instance_name
                                               or args.private_ip))
                                 if needs_instance and (args.instance_id
                                                        or args.instance_name
                                                        or args.private_ip)
                                 else ""))
    elif len(instances) > 1 and not args.instance_id:
        candidates = [(str(i.get("InstanceId") or "?"),
                       str(i.get("InstanceName") or "?"),
                       str(i.get("Status") or "?"),
                       str(i.get("InstanceType") or "?"))
                      for i in instances[:10]]
    else:
        facts = render_facts(instances[0])

    status_live = ""
    if facts and args.instance_id:
        status_live = read_instance_status(args, ev)
    elif facts:
        status_live = facts["status"]

    stock = read_stock(args, ev) if args.want_instance_type else None

    probe_result = {"requested": False}
    if args.probe:
        if not facts:
            probe_result = {"requested": True, "outcome": "refused",
                            "name": args.probe,
                            "command": GUEST_PROBES[args.probe]["command"],
                            "detail": "no single instance was resolved, so "
                                      "the guest was not touched"}
        else:
            args.instance_id = facts["instance_id"]
            probe_result = run_probe(args, instances[0], ev)

    snapshot_result = run_snapshot(args, ev)

    symptom = classify_symptom(args.error_text or args.note)
    guidance, handoffs = build_guidance(args, symptom, facts, status_live)
    findings = build_findings(args, facts, status_live, stock, symptom,
                              probe_result, snapshot_result)

    risk_notes = [
        "Nothing outside the whitelist in references/ram-policies.md is ever "
        "called; the transport refuses it before a process starts.",
        "Class B and C ran only if this call carried its own confirmation; a "
        "confirmation is never reused.",
        "Installing software, opening ports, starting or restarting services, "
        "deleting or cleaning files are manual steps: this skill never does "
        "them, and any cleanup guidance must carry a completed snapshot "
        "first.",
        SNAPSHOT_BILLING_NOTE,
    ]
    docs = docs_for(args.intent, args.server_type)

    n_steps = len(ev.rows)
    n_bad = sum(1 for r in ev.rows if r["result"] != "ok")
    if facts:
        head = ("Instance %s (%s, %s) was checked in %s."
                % (facts["instance_id"], facts["instance_type"],
                   facts["status"], args.region_id))
    elif candidates:
        head = ("The region scan in %s returned %d candidate instances; the "
                "target is not fixed yet." % (args.region_id, len(candidates)))
    elif instance_error:
        head = "No deployment target resolved in %s." % args.region_id
    else:
        head = "This run checked account and stock context only."
    summary = ("%s Deployment path in play: %s. Evidence steps: %d (%d did "
               "not come back clean)." % (head, args.intent, n_steps, n_bad))

    if instance_error:
        status = STATUS_FAIL
        next_action = ("re-run with the exact --region-id and --instance-id; "
                       "if the customer owns a Simple Application Server "
                       "instead of an ECS instance, that is a different "
                       "product (see references/handoff-boundaries.md)")
    elif candidates:
        status = STATUS_DEGRADED
        next_action = ("ask the customer which listed instance id is the "
                       "deploy target, then re-run with --instance-id set")
    elif ev.degraded() or probe_result.get("outcome") in ("unconfirmed",
                                                          "refused", "failed",
                                                          "unread",
                                                          "still running") \
            or (snapshot_result.get("requested")
                and not snapshot_result.get("created")):
        status = STATUS_DEGRADED
        next_action = ("relay the partial report; for each failed, refused or "
                       "unconfirmed step, ask the customer to run the named "
                       "manual check and paste the output")
    else:
        status = STATUS_OK
        next_action = ("relay the report and its numbered manual guidance; "
                       "run --probe checks one confirmed command at a time "
                       "when a guest reading is needed next")

    report = {
        "session_id": args.session_id,
        "summary": summary,
        "uid": gathered["uid"],
        "identity_type": gathered["identity_type"],
        "declared_inputs": {
            "region-id": "%s (user supplied)" % args.region_id,
            "instance filter": (args.instance_id or args.instance_name
                                or args.private_ip
                                or "none: region scan (default)"),
            "intent": args.intent + (" (default: ask one clarifying question)"
                                     if args.intent == "unknown" else ""),
            "server-type": args.server_type + (" (default)" if
                                               args.server_type == "game"
                                               else ""),
            "stock target": args.want_instance_type or "not requested",
            "guest-wait": "%ss (default 60)" % args.guest_wait,
            "per-call timeout": "%ss (default 30)" % args.timeout,
        },
        "instance_error": instance_error,
        "facts": facts,
        "candidates": candidates,
        "stock": stock,
        "symptom": ({"branch": symptom[0], "statement": symptom[1],
                     "target": HANDOFF_TARGETS.get(symptom[2], symptom[2]),
                     "matched": symptom[3]} if symptom else None),
        "probe": probe_result,
        "snapshot": snapshot_result,
        "findings": findings,
        "guidance": guidance,
        "docs": docs,
        "human_checks": list(HUMAN_ONLY_CHECKS),
        "handoffs": handoffs,
        "evidence": ev.rows,
        "risk_notes": risk_notes,
        "limitations": list(LIMITATIONS),
        "status": status,
        "next_action": next_action,
    }

    if args.output == "json":
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(render_text(report))
    sys.exit(EXIT_FOR_STATUS[status])


if __name__ == "__main__":
    main()
