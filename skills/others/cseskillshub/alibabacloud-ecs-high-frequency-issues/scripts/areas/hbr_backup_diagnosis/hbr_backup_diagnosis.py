#!/usr/bin/env python3
"""Single entry point for ECS Cloud Backup (HBR) backup/restore diagnosis.

The agent drives this script; it must not compose aliyun CLI calls by hand.

Operation classes this script implements:
  A  informational cloud queries  - run automatically, no per-call consent;
  B  side-effect-free guest probes - consent-gated, one command per consent;
  C  low-risk reversible writes    - consent-gated, snapshot before any cleanup;
  D  destructive operations        - never implemented, guidance only.

Every command ends with the two contract lines:
  STATUS: OK | DEGRADED | FAIL
  NEXT_ACTION: <the single next step>
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import binascii
import json
import sys
import time

from _cli import CliError, call_soft, mask_secrets, session_id, user_agent
from _constants import (
    ALL_CATEGORIES,
    API_ECS_CREATE_SNAPSHOT,
    API_ECS_DESCRIBE_DISKS,
    API_ECS_DESCRIBE_INSTANCES,
    API_ECS_DESCRIBE_INVOCATIONS,
    API_ECS_DESCRIBE_SNAPSHOTS,
    API_ECS_RUN_COMMAND,
    AUTH_ERROR_TOKENS,
    CATEGORY_CLOUD_ASSISTANT,
    CATEGORY_DISK_SPACE,
    CATEGORY_ECS_RELEASED,
    CATEGORY_RESTORE_SKIPPED,
    CATEGORY_ROLE_OR_BILLING,
    CATEGORY_UNKNOWN,
    DEFAULT_PAGE_SIZE,
    DOC_LINKS,
    DOC_TITLES_WITHOUT_URL,
    ECS_API_VERSION,
    GUEST_COMMANDS,
    GUEST_POLL_INTERVAL_SECONDS,
    GUEST_POLL_MAX_ATTEMPTS,
    HANDOFF_RULES,
    PRODUCT_ECS,
    REJECTED_COMMAND_TOKENS,
    ROOT_CAUSE_CANDIDATES,
    SHELL_METACHARACTERS,
    SKILL_NAME,
    STS_API_VERSION,
    SYMPTOM_PATTERNS,
)

CLEANUP_MANUAL_WARNING = (
    "Deleting files, emptying a recycle bin, stopping a service or growing a volume is performed "
    "by the customer. This skill prints candidates, it never removes data."
)

_REJECTED_TOKENS = frozenset(token.lower() for token in REJECTED_COMMAND_TOKENS)

_FINISHED_STATES = ("Success", "Finished", "Failed", "Stopped", "PartialFailed", "Error",
                    "Timeout", "Invalid", "Aborted")


# ---------------------------------------------------------------------------
# Evidence collection and rendering
# ---------------------------------------------------------------------------
class Evidence(object):
    """Accumulates the query trail plus conclusions, then renders one report."""

    def __init__(self, title):
        self.title = title
        self.rows = []
        self.findings = []
        self.manual_steps = []
        self.candidates = []
        self.notes = []
        self.status = "OK"
        self.show_handoff = True

    def record(self, action, params, outcome, summary):
        self.rows.append({
            "action": action,
            "params": _fmt_params(params),
            "outcome": outcome,
            "summary": mask_secrets(summary),
        })

    def finding(self, text):
        self.findings.append(text)

    def manual(self, text):
        self.manual_steps.append(text)

    def note(self, text):
        self.notes.append(text)

    def candidate(self, candidate):
        self.candidates.append(candidate)

    def degrade(self):
        if self.status == "OK":
            self.status = "DEGRADED"

    def fail(self):
        self.status = "FAIL"

    def render(self, identity_tag, inputs, next_action):
        out = []
        out.append("=" * 72)
        out.append(self.title)
        out.append("=" * 72)
        out.append("Skill      : {0}".format(SKILL_NAME))
        out.append("Session-Id : {0}".format(session_id()))
        out.append("User-Agent : {0}".format(user_agent()))
        out.append("Identity   : {0}".format(identity_tag))
        out.append("API surface: ecs/{0} sts/{1}".format(ECS_API_VERSION, STS_API_VERSION))
        out.append("")
        out.append("-- Inputs (flag any value this skill assumed rather than was told) ------")
        for key in sorted(inputs):
            out.append("  {0:<16}: {1}".format(key, inputs[key]))
        out.append("")
        out.append("-- Evidence -----------------------------------------------------------")
        if not self.rows:
            out.append("  (no cloud query was needed for this question)")
        for index, row in enumerate(self.rows, 1):
            out.append("  [{0}] {1}  params: {2}".format(index, row["action"], row["params"]))
            out.append("      -> {0}: {1}".format(row["outcome"], row["summary"]))
        out.append("")
        out.append("-- Findings -----------------------------------------------------------")
        for text in self.findings or ["Nothing was confirmed from returned data."]:
            out.append("  - {0}".format(text))

        if self.candidates:
            out.append("")
            out.append("-- Root-cause candidates (case history, not measured here) ----------")
            for candidate in self.candidates:
                out.append("  * [{0} | confidence: {1}]".format(candidate["id"],
                                                                candidate["confidence"]))
                out.append("      symptom    : {0}".format(candidate["summary"]))
                for check in candidate["manual_checks"]:
                    out.append("      self-check : {0}".format(check))
                out.append("      resolution : {0}".format(candidate["verified_mitigation"]))
                out.append("      case refs  : {0}".format(", ".join(candidate["case_refs"])))

        if self.manual_steps:
            out.append("")
            out.append("-- Manual-only actions --------------------------------------------")
            for step in self.manual_steps:
                out.append("  ! {0}".format(step))

        if self.notes:
            out.append("")
            out.append("-- Notes -----------------------------------------------------------")
            for text in self.notes:
                out.append("  i {0}".format(text))

        if self.show_handoff:
            out.append("")
            out.append("-- Hand-off --------------------------------------------------------")
            for rule in HANDOFF_RULES:
                out.append("  if {0}".format(rule["when"]))
                out.append("     -> {0}".format(rule["target"]))

        out.append("")
        out.append("STATUS: {0}".format(self.status))
        out.append("NEXT_ACTION: {0}".format(next_action))
        return "\n".join(out)


def _fmt_params(params):
    if not params:
        return "-"
    return ",".join("{0}={1}".format(k, params[k]) for k in sorted(params))


def _resolve_identity():
    import sts_token
    record, error = sts_token.resolve_identity()
    if error is not None:
        sys.stderr.write("[WARN] identity check failed: {0}\n".format(mask_secrets(str(error))))
        return "account=unverified", error
    return sts_token.uid_tag(record), None


def _truncate(text, limit=160):
    if not text:
        return "not supplied"
    return text if len(text) <= limit else text[:limit] + "..."


# ---------------------------------------------------------------------------
# Symptom classification
# ---------------------------------------------------------------------------
def classify(alert_text, forced=None):
    """Return (category, matched_tokens). Never guesses: no match -> UNKNOWN."""
    if forced and forced != CATEGORY_UNKNOWN:
        return forced, ["--category given"]
    if not alert_text:
        return CATEGORY_UNKNOWN, []
    haystack = alert_text.lower()
    for category, patterns in SYMPTOM_PATTERNS:
        hits = [token for token in patterns if token in haystack]
        if hits:
            return category, sorted(set(hits))[:6]
    return CATEGORY_UNKNOWN, []


def _instances_of(payload):
    return (payload.get("Instances") or {}).get("Instance") or []


def _invocation_instances(payload):
    collected = []
    for invocation in (payload.get("Invocations") or {}).get("Invocation") or []:
        for instance in (invocation.get("InvokeInstances") or {}).get("InvokeInstance") or []:
            merged = dict(instance)
            merged["InvokeId"] = invocation.get("InvokeId")
            merged["InvocationStatus"] = invocation.get("InvocationStatus")
            collected.append(merged)
    return collected


# ---------------------------------------------------------------------------
# Class A queries
# ---------------------------------------------------------------------------
def query_instance(ev, region_id, instance_id=None):
    """Returns a dict (scoped), a list (region-wide), {} when absent, None on error."""
    params = {"RegionId": region_id, "PageSize": DEFAULT_PAGE_SIZE}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    payload, error = call_soft(API_ECS_DESCRIBE_INSTANCES, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_INSTANCES, params, "WARN", str(error))
        ev.degrade()
        return None
    instances = _instances_of(payload)
    if not instances:
        ev.record(API_ECS_DESCRIBE_INSTANCES, params, "EMPTY",
                  "no instance returned in {0}".format(region_id))
        return {}
    ev.record(API_ECS_DESCRIBE_INSTANCES, params, "OK", "; ".join(
        "{0} Status={1} Charge={2} OS={3}".format(
            inst.get("InstanceId"), inst.get("Status"), inst.get("InstanceChargeType"),
            inst.get("OSType")) for inst in instances))
    return instances[0] if instance_id else instances


def query_disks(ev, region_id, instance_id=None):
    params = {"RegionId": region_id, "PageSize": DEFAULT_PAGE_SIZE}
    if instance_id:
        params["InstanceId"] = instance_id
    payload, error = call_soft(API_ECS_DESCRIBE_DISKS, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_DISKS, params, "WARN", str(error))
        ev.degrade()
        return []
    disks = (payload.get("Disks") or {}).get("Disk") or []
    if not disks:
        ev.record(API_ECS_DESCRIBE_DISKS, params, "EMPTY", "no disk returned")
        return []
    ev.record(API_ECS_DESCRIBE_DISKS, params, "OK", "; ".join(
        "{0} {1} {2}GB role={3} charge={4} status={5}".format(
            d.get("DiskId"), d.get("Category"), d.get("Size"), d.get("Type"),
            d.get("DiskChargeType"), d.get("Status")) for d in disks))
    return disks


def query_snapshots(ev, region_id, instance_id=None, disk_id=None):
    params = {"RegionId": region_id, "PageSize": DEFAULT_PAGE_SIZE}
    if instance_id:
        params["InstanceId"] = instance_id
    if disk_id:
        params["DiskId"] = disk_id
    payload, error = call_soft(API_ECS_DESCRIBE_SNAPSHOTS, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_SNAPSHOTS, params, "WARN", str(error))
        ev.degrade()
        return []
    snapshots = (payload.get("Snapshots") or {}).get("Snapshot") or []
    if not snapshots:
        ev.record(API_ECS_DESCRIBE_SNAPSHOTS, params, "EMPTY",
                  "no snapshot found in {0}".format(region_id))
        return []
    ev.record(API_ECS_DESCRIBE_SNAPSHOTS, params, "OK",
              "{0} snapshot(s), summed source-disk capacity {1}GB, ids: {2}".format(
                  len(snapshots),
                  sum(int(s.get("SourceDiskSize") or 0) for s in snapshots),
                  ", ".join(s.get("SnapshotId", "?") for s in snapshots[:5])))
    return snapshots


def query_invocations(ev, region_id, instance_id=None, invoke_id=None, include_output=False):
    params = {"RegionId": region_id, "PageSize": DEFAULT_PAGE_SIZE}
    if instance_id:
        params["InstanceId"] = instance_id
    if invoke_id:
        params["InvokeId"] = invoke_id
    if include_output:
        params["IncludeOutput"] = True
        params["ContentEncoding"] = "PlainText"
    payload, error = call_soft(API_ECS_DESCRIBE_INVOCATIONS, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_INVOCATIONS, params, "WARN", str(error))
        return None, error
    rows = _invocation_instances(payload)
    if not rows:
        ev.record(API_ECS_DESCRIBE_INVOCATIONS, params, "EMPTY",
                  "no Cloud Assistant invocation history matched")
        return [], None
    ev.record(API_ECS_DESCRIBE_INVOCATIONS, params, "OK", "; ".join(
        "{0} status={1} exit={2}".format(
            r.get("InvokeId"),
            r.get("InvocationStatus") or r.get("InvokeRecordStatus"),
            r.get("ExitCode")) for r in rows[:8]))
    return rows, None


def add_region_note(ev, region_id, alarm_region=None):
    ev.note(
        "Region under query: {0}. State it back to the customer and confirm it matches the "
        "region named in the alarm or the bill. A wrong console region is a confirmed cause of "
        "'the resource does not exist' in this tier.".format(region_id)
    )
    if alarm_region and alarm_region != region_id:
        ev.degrade()
        ev.finding("Region mismatch: the alarm names '{0}' but the query used '{1}'. Re-run "
                   "against '{0}' before drawing a conclusion.".format(alarm_region, region_id))


def add_candidates(ev, category):
    for candidate in ROOT_CAUSE_CANDIDATES.get(category, ()):
        ev.candidate(candidate)


def add_billing_pointers(ev):
    ev.note("Cloud Backup billing items and methods: {0}".format(DOC_LINKS["hbr_billing_methods"]))
    ev.note("Block storage (disk) billing: {0}".format(DOC_LINKS["block_storage_billing"]))
    ev.note("Snapshot billing: {0}".format(DOC_LINKS["snapshot_billing"]))
    ev.note("File Backup Essential Edition billing basis: {0}".format(
        DOC_LINKS["essential_edition_billing_basis"]))
    ev.note("Stop Cloud Backup billing: {0}".format(DOC_LINKS["hbr_stop_billing"]))
    ev.note("Expense centre balance and top-up: {0}".format(DOC_LINKS["recharge_entry"]))


# ---------------------------------------------------------------------------
# Class B/C helpers
# ---------------------------------------------------------------------------
class CommandPolicyError(ValueError):
    pass


def _validate_target(target):
    if not target:
        raise CommandPolicyError("--target is required for this probe")
    if len(target) > 512:
        raise CommandPolicyError("--target is too long")
    if any(ch in target for ch in SHELL_METACHARACTERS):
        raise CommandPolicyError("--target contains a rejected character")
    if ".." in target or " " in target:
        raise CommandPolicyError("--target may not contain '..' or whitespace")
    is_drive = len(target) == 2 and target[0].isalpha() and target[1] == ":"
    is_windows_path = (len(target) >= 3 and target[0].isalpha()
                       and target[1] == ":" and target[2] == "\\")
    if not (target.startswith("/") or is_drive or is_windows_path):
        raise CommandPolicyError("--target must be a POSIX absolute path, a drive letter "
                                 "like C:, or a drive-rooted Windows path like C:\\dir")
    return target


def _validate_command_string(command_string):
    """A whitelist match is necessary but not sufficient: the assembled string is
    re-checked so no side effect can ride in on a parameter."""
    if any(meta in command_string for meta in SHELL_METACHARACTERS):
        raise CommandPolicyError("the assembled command contains a shell metacharacter")
    for token in command_string.split():
        if token.lstrip("-").lower() in _REJECTED_TOKENS:
            raise CommandPolicyError("the assembled command contains the rejected token "
                                     "'{0}'".format(token))
    return command_string


def build_guest_command(key, target=None):
    """Return (command_type, command_string) for one whitelisted probe."""
    spec = GUEST_COMMANDS.get(key)
    if spec is None:
        raise CommandPolicyError("'{0}' is not a whitelisted probe".format(key))
    argv = list(spec["argv"])
    if spec["target_required"]:
        argv.append(_validate_target(target))
    elif target:
        raise CommandPolicyError("--target is not accepted for probe '{0}'".format(key))
    return spec["type"], _validate_command_string(" ".join(argv))


def guest_ack(region_id, instance_id, key, target):
    rendered = "{0}:{1}".format(key, target) if target else key
    return "GUESTPROBE:{0}:{1}:{2}".format(region_id, instance_id, rendered)


def snapshot_ack(region_id, disk_id):
    return "CREATESNAPSHOT:{0}:{1}".format(region_id, disk_id)


def _decode_output(value):
    """The CLI may honour or ignore the requested encoding, so decode when the
    body is base64 and fall back to the raw text otherwise."""
    if not value:
        return ""
    text = value if isinstance(value, str) else str(value)
    try:
        return base64.b64decode(text.strip(), validate=True).decode("utf-8", "strict")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return text


def poll_invocation(ev, region_id, invoke_id):
    for attempt in range(GUEST_POLL_MAX_ATTEMPTS):
        rows, error = query_invocations(ev, region_id, invoke_id=invoke_id, include_output=True)
        if error is not None:
            return None, "the result could not be read back: {0}".format(mask_secrets(str(error)))
        for row in rows or []:
            if (row.get("InvocationStatus") or row.get("InvokeRecordStatus")) in _FINISHED_STATES:
                return row, None
        if attempt < GUEST_POLL_MAX_ATTEMPTS - 1:
            time.sleep(GUEST_POLL_INTERVAL_SECONDS)
    return None, "no final state within the polling budget"


def _is_error_authorisation(error):
    text = str(error)
    return any(token in text for token in AUTH_ERROR_TOKENS)


def _permission_hint(ev, missing_action):
    ev.finding(
        "The identity in use is not permitted to call {0} (NoPermission / ImplicitDeny). Report "
        "the missing action and hand the customer the minimal statement from "
        "references/ram-policies.md. Do not widen permissions or substitute a broader policy."
        .format(missing_action)
    )


# ---------------------------------------------------------------------------
# triage
# ---------------------------------------------------------------------------
def cmd_triage(args):
    ev = Evidence("ECS CLOUD BACKUP (HBR) TRIAGE REPORT")
    category, hits = classify(args.alert_text, args.category)
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id or "not supplied",
        "alert-text": _truncate(args.alert_text),
        "category": args.category or "auto",
        "classified-as": "{0} (matched: {1})".format(category, ", ".join(hits) or "none"),
    }
    identity, _ = _resolve_identity()
    ev.finding("Symptom class: {0}".format(category))
    if category == CATEGORY_UNKNOWN:
        ev.degrade()
        ev.note("The console localises its message text, so an alarm that is neither English nor "
                "carrying a recognised product token cannot be classified. Re-run with "
                "--category from: {0}".format(", ".join(ALL_CATEGORIES)))

    add_region_note(ev, args.region_id, args.alarm_region)
    instance = query_instance(ev, args.region_id, args.instance_id) if args.instance_id else None

    if category == CATEGORY_ECS_RELEASED:
        next_action = _triage_released(ev, args, instance)
    elif category == CATEGORY_CLOUD_ASSISTANT:
        next_action = _triage_cloud_assistant(ev, args, instance)
    elif category == CATEGORY_DISK_SPACE:
        next_action = _triage_disk_space(ev, args, instance)
    elif category == CATEGORY_RESTORE_SKIPPED:
        next_action = _triage_restore(ev, args)
    elif category == CATEGORY_ROLE_OR_BILLING:
        next_action = _triage_billing(ev, args)
    else:
        next_action = _triage_generic(ev, args, category)

    return ev, inputs, identity, next_action


def _triage_released(ev, args, instance):
    if instance:
        ev.finding("Instance '{0}' is still reported by the control plane in '{1}' with status "
                   "{2}, so an EcsReleased alarm contradicts reality. Trust the API and re-check "
                   "the region.".format(args.instance_id, args.region_id,
                                        instance.get("Status")))
        ev.degrade()
    else:
        ev.finding("Confirmed: instance '{0}' does not exist in region '{1}'. The alarm is the "
                   "historical record emitted at the release moment, not a live job."
                   .format(args.instance_id, args.region_id))
        ev.finding("Deleting a protection policy does not erase historical alarm records, and the "
                   "console list refreshes lazily. Once zero resources are protected, no new "
                   "alarm is produced.")
    add_candidates(ev, CATEGORY_ECS_RELEASED)
    ev.manual("To retire the leftovers: open {0} in region {1}, find the plan and vault attached "
              "to the released instance, delete the backup plan first and the backup vault "
              "second. WARNING: deleting a plan or vault permanently destroys the stored backup "
              "data and it cannot be recovered. {2}".format(
                  DOC_LINKS["hbr_console"], args.region_id, CLEANUP_MANUAL_WARNING))
    ev.manual("If the historical alarm entry itself must be cleared, raise a ticket with the "
              "Cloud Backup service; there is no customer-facing control for it.")
    add_billing_pointers(ev)
    return ("Tell the customer the instance is gone and the alarm is historical; if billing is "
            "the concern, run billing-attribution for this region.")


def _triage_cloud_assistant(ev, args, instance):
    if instance is None:
        ev.degrade()
    elif not instance:
        ev.finding("Instance '{0}' was not found in '{1}'. Fix the region or the id before "
                   "diagnosing the agent.".format(args.instance_id, args.region_id))
        ev.degrade()
        return "Correct --region-id / --instance-id and re-run triage."
    else:
        ev.finding("The control plane still sees the instance ({0}), so the failure is inside the "
                   "guest network or agent path, not the backup plan definition."
                   .format(instance.get("Status")))

    if args.instance_id:
        rows, error = query_invocations(ev, args.region_id, args.instance_id)
        if error is None:
            if rows:
                ev.finding("Cloud Assistant has invocation history for this instance. Check "
                           "whether the recent records reached a final Success; a stuck or failed "
                           "record is what blocks the backup helper.")
            else:
                ev.finding("No Cloud Assistant invocation history at all, which is consistent "
                           "with the agent being unreachable rather than the plan being wrong.")

    add_candidates(ev, CATEGORY_CLOUD_ASSISTANT)
    ev.note("Guest probes are deliberately NOT attempted for this class: RunCommand travels over "
            "the very channel that is failing, so a probe would produce a false negative. In-guest "
            "route, resolver and service inspection is done by the customer, or by a support "
            "engineer after explicit login authorisation.")
    ev.manual("Cloud Assistant status check and exception handling: {0}".format(
        DOC_LINKS["cloud_assistant_status_and_exceptions"]))
    ev.manual("If remote login is needed and the password is unknown, the customer resets it "
              "self-service: {0}".format(DOC_LINKS["reset_instance_password"]))
    ev.manual("Route-table and resolver comparison against the Alibaba Cloud reserved service "
              "ranges is a manual inspection: see references/hbr-backup-diagnosis__guest-commands.md section 'Network "
              "and resolver checks are not whitelisted'.")
    ev.manual("Stopping or disabling a third-party tunnel service, changing the system resolver, "
              "reinstalling the agent or rebooting are service changes and are never automated.")
    ev.manual("Sustained CPU saturation cannot be measured by this version: CloudMonitor is not "
              "part of the verified API set for this tier. Ask the customer to compare the "
              "failure timestamps with the busiest window of the workload.")
    return ("Give the customer the candidate list with its self-check commands and ask them to "
            "paste the route and resolver output from the instance.")


def _triage_disk_space(ev, args, instance):
    disks = query_disks(ev, args.region_id, args.instance_id)
    if disks:
        ev.finding("Provisioned capacity baseline from the control plane: {0}.".format(
            "; ".join("{0}={1}GB({2})".format(d.get("DiskId"), d.get("Size"), d.get("Type"))
                      for d in disks)))
        ev.finding("The cloud API exposes provisioned size only. Used space inside the guest is "
                   "not a cloud attribute, so it has to be measured - that is the next step.")
    ev.finding("'Insufficient disk space' in a file-backup alarm means the volume inside the "
               "instance, not the backup storage quota. These are unrelated, and conflating them "
               "costs the most turns of any case in this tier.")
    add_candidates(ev, CATEGORY_DISK_SPACE)

    if not args.instance_id:
        ev.degrade()
        ev.note("--instance-id is required to probe the guest.")
        return "Re-run triage with --instance-id, then probe the guest."

    probe_key = "get_volume" if _looks_windows(args, instance) else "df_h"
    ack = guest_ack(args.region_id, args.instance_id, probe_key, None)
    ev.manual("Freeing space is manual. {0}".format(CLEANUP_MANUAL_WARNING))
    ev.manual("Windows volumes specifically: {0}".format(DOC_LINKS["windows_low_disk_space"]))
    ev.manual("A snapshot must exist before any cleanup: python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py "
              "snapshot-guard --region-id {0} --disk-id <disk-id>".format(args.region_id))
    return ("After telling the customer what the probe runs and that it changes nothing, execute "
            "it with: python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py guest-probe --region-id {0} "
            "--instance-id {1} --command {2} --confirm {3}".format(
                args.region_id, args.instance_id, probe_key, ack))


def _triage_restore(ev, args):
    ev.finding("A restore reporting completion can still have skipped files. Read the skipped "
               "count in the restore result details before concluding anything about the backup.")
    add_candidates(ev, CATEGORY_RESTORE_SKIPPED)
    ev.manual("Verify content before restoring: in the backup point list use Browse and expand "
              "level by level down to the exact path.")
    ev.manual("Manual restore SOP in this order: (1) snapshot the target disk first; (2) stop "
              "the service holding the files, for example the database engine - stopping a "
              "service is never automated; (3) re-run the restore in overwrite mode, not skip; "
              "(4) restart the service; (5) verify inside the application, not in the console.")
    ev.manual("If the deletion predates every retained backup point, the data is physically "
              "absent from the backup. Say so plainly instead of retrying restores.")
    ev.note("Essential Edition enable and restore walkthrough: {0}".format(
        DOC_LINKS["configure_essential_edition"]))
    ev.note("Retention and free-quota specifics must be read from {0}, never quoted from "
            "memory.".format(DOC_LINKS["essential_edition_benefit"]))
    return ("Walk the customer through the Browse check, then the snapshot / stop-service / "
            "overwrite-restore SOP.")


def _triage_billing(ev, args):
    _run_billing_inventory(ev, args)
    add_candidates(ev, CATEGORY_ROLE_OR_BILLING)
    return ("Report the listed resources to the customer and send them to the expense centre for "
            "amounts; per-line billing attribution is outside this skill.")


def _triage_generic(ev, args, category):
    if category != CATEGORY_UNKNOWN:
        add_candidates(ev, category)
    ev.degrade()
    ev.finding("No automated signal in the verified API set explains a bare '{0}'. Cloud Backup "
               "plan, task and restore state have no verified query action for this tier, so the "
               "console half of the picture has to come from the customer.".format(category))
    ev.note("Collect in this order: the full alarm or SMS text, a console screenshot, the backup "
            "plan id (plan-...), the instance id, the region, and the request id shown in the "
            "console error dialog.")
    if args.instance_id:
        ev.manual("Instance backup tab: {0}".format(
            DOC_LINKS["instance_backup_console"].format(instance_id=args.instance_id,
                                                        region_id=args.region_id)))
    ev.manual("File backup page for the region: {0}".format(
        DOC_LINKS["file_backup_console"].format(region_id=args.region_id)))
    ev.manual("Cloud Backup console: {0}".format(DOC_LINKS["hbr_console"]))
    ev.manual("DeleteBackupPlan is offered only as a manual advanced path and is never automated "
              "here: {0} - deleting the plan permanently destroys all of its backup data."
              .format(DOC_LINKS["delete_backup_plan_api"]))
    return ("Collect the listed evidence; if nothing new emerges, hand off to the Cloud Backup "
            "service with the request id.")


def _looks_windows(args, instance):
    if args.os_type:
        return args.os_type == "windows"
    if isinstance(instance, dict):
        return str(instance.get("OSType", "")).lower() == "windows"
    return False


# ---------------------------------------------------------------------------
# billing-attribution
# ---------------------------------------------------------------------------
def cmd_billing_attribution(args):
    ev = Evidence("ECS CLOUD BACKUP (HBR) BILLING ATTRIBUTION REPORT")
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id or "all instances in region",
        "alarm-region": args.alarm_region or "not supplied",
    }
    identity, _ = _resolve_identity()
    _run_billing_inventory(ev, args)
    add_candidates(ev, CATEGORY_ROLE_OR_BILLING)
    next_action = ("Map each listed resource to references/hbr-backup-diagnosis__billing-map.md, then send the "
                   "customer to the expense centre for the amounts.")
    return ev, inputs, identity, next_action


def _run_billing_inventory(ev, args):
    add_region_note(ev, args.region_id, args.alarm_region)
    instances = query_instance(ev, args.region_id, args.instance_id)
    if isinstance(instances, list):
        ev.finding("{0} instance(s) exist in '{1}'.".format(len(instances), args.region_id))
    elif isinstance(instances, dict):
        ev.finding("Instance '{0}' exists with charge type {1}.".format(
            args.instance_id, instances.get("InstanceChargeType")))

    disks = query_disks(ev, args.region_id, args.instance_id)
    snapshots = query_snapshots(ev, args.region_id, args.instance_id)

    payg = [d for d in disks if d.get("DiskChargeType") == "PostPaid"]
    burst = [d for d in disks if d.get("BurstingEnabled")]
    if payg:
        ev.finding("Pay-as-you-go disks bill independently of a subscription instance and are the "
                   "usual suspect behind 'my subscription ECS still shows extra charges': {0}"
                   .format(", ".join("{0}({1}, {2}GB)".format(d.get("DiskId"), d.get("Category"),
                                                              d.get("Size")) for d in payg)))
    if burst:
        ev.finding("Burst-capable disks listed: {0}. Burst performance is its own billable line."
                   .format(", ".join(d.get("DiskId", "?") for d in burst)))
    if snapshots:
        ev.finding("Snapshot storage exists in '{0}' and is billed by used capacity, separately "
                   "from Cloud Backup. Deleting snapshots is the only way to stop that line."
                   .format(args.region_id))
    elif snapshots == []:
        ev.finding("No snapshot in '{0}', so no snapshot storage charge can originate here."
                   .format(args.region_id))

    ev.finding("Snapshot, Cloud Backup (HBR), ApsaraDB RDS backup and block storage are separate "
               "products with separate billing lines. Cloud Backup cannot be switched off as a "
               "whole: billing stops only by deleting the backup plans and then the vaults, which "
               "permanently destroys the stored data.")
    ev.note("No billing, balance or overdue-payment query is available in the verified API set "
            "for this tier. Arrears must be read by the customer in the expense centre; a "
            "negative balance is what blocks creation of the service-linked role "
            "AliyunServiceRoleForHbrEcsBackup and makes console functions vanish.")
    ev.manual("Stop-billing walkthrough plus the permanent-data-loss warning: {0}".format(
        DOC_LINKS["hbr_stop_billing"]))
    ev.manual("Deleting a snapshot is manual and irreversible for its data: {0} | {1}".format(
        DOC_LINKS["delete_snapshot"], DOC_LINKS["delete_snapshot_console"]))
    ev.manual("Database-backup resource plans: {0}".format(DOC_LINKS["database_resource_plan"]))
    add_billing_pointers(ev)


# ---------------------------------------------------------------------------
# guest-probe (class B)
# ---------------------------------------------------------------------------
def cmd_guest_probe(args):
    ev = Evidence("ECS CLOUD BACKUP (HBR) GUEST PROBE")
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    ack = guest_ack(args.region_id, args.instance_id, args.command, args.target)
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id,
        "probe": args.command,
        "target": args.target or "n/a",
        "consent": "given" if args.confirm else "NOT GIVEN",
    }
    spec = GUEST_COMMANDS.get(args.command)

    try:
        command_type, command_string = build_guest_command(args.command, args.target)
    except CommandPolicyError as exc:
        ev.fail()
        ev.finding("Rejected by the command policy: {0}".format(exc))
        ev.note("Whitelisted probes: {0}".format(", ".join(sorted(GUEST_COMMANDS))))
        return (ev, inputs, identity,
                "Pick a whitelisted --command and re-run; semantics are in "
                "references/hbr-backup-diagnosis__guest-commands.md.")

    ev.record("command-policy", {"probe": args.command}, "OK",
              "single assembled command accepted by the whitelist")

    if not args.confirm:
        for line in [
            "WHAT WILL RUN     : {0}".format(command_string),
            "GUEST OS          : {0}".format(spec["os"]),
            "DELIVERY          : ecs:{0} Type={1}, one command, one instance".format(
                API_ECS_RUN_COMMAND, command_type),
            "AFFECTS           : instance {0} alone; it inspects state inside it and modifies "
            "nothing".format(args.instance_id),
            "SIDE EFFECTS      : none; the command reports usage or metadata and writes nothing",
            "REVERSIBLE        : n/a, nothing is modified",
            "COST              : this probe itself is not billed",
            "PRECONDITION      : the Cloud Assistant agent must be online in the instance",
            "PURPOSE           : {0}".format(spec["purpose"]),
            "REPORTS           : {0}".format(spec["reports"]),
            "SCOPE OF CONSENT  : the token below authorises exactly this region/instance/command "
                              "and expires with it; a second command needs a second consent",
        ]:
            ev.manual(line)
        ev.finding("Nothing has been executed yet; this is the pre-execution disclosure.")
        return (ev, inputs, identity,
                "Read the lines above to the customer and get their agreement, then re-run with "
                "--confirm {0}".format(ack))

    if args.confirm != ack:
        ev.fail()
        ev.finding("The supplied --confirm is not the consent token for this exact operation. "
                   "Consent is single-use and bound to region, instance, probe and target.")
        return (ev, inputs, identity, "Re-run with --confirm {0}".format(ack))

    params = {
        "RegionId": args.region_id,
        "Type": command_type,
        "CommandContent": command_string,
        "InstanceId.1": args.instance_id,
    }
    payload, error = call_soft(API_ECS_RUN_COMMAND, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_RUN_COMMAND, {"RegionId": args.region_id, "Type": command_type,
                                       "CommandContent": command_string}, "WARN", str(error))
        ev.degrade()
        if _is_error_authorisation(error):
            _permission_hint(ev, "ecs:{0}".format(API_ECS_RUN_COMMAND))
        else:
            ev.finding("The probe could not be delivered. The commonest reason in this tier is "
                       "that the Cloud Assistant agent is itself unreachable, which is the "
                       "failure under diagnosis.")
        ev.note("Degraded mode: give the customer `{0}` to run in the instance and have them "
                "paste the raw output; then continue the same decision tree. See "
                "references/hbr-backup-diagnosis__guest-commands.md section 'Degraded mode'.".format(command_string))
        ev.manual("Agent-side triage: python3 scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py triage --region-id "
                  "{0} --instance-id {1} --category {2}".format(
                      args.region_id, args.instance_id, CATEGORY_CLOUD_ASSISTANT))
        return (ev, inputs, identity,
                "Degrade to customer-pasted output for `{0}`.".format(command_string))

    invoke_id = payload.get("InvokeId")
    ev.record(API_ECS_RUN_COMMAND, {"RegionId": args.region_id, "InstanceId.1": args.instance_id},
              "OK", "dispatched, InvokeId={0}".format(invoke_id))

    row, poll_error = poll_invocation(ev, args.region_id, invoke_id)
    if poll_error is not None:
        ev.record("read-back", {"InvokeId": invoke_id}, "WARN", poll_error)
        ev.degrade()
        return (ev, inputs, identity,
                "Re-read the result once the agent reports in: python3 "
                "scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py guest-probe --region-id {0} --instance-id {1} "
                "--command {2} --confirm {3} (a fresh consent is required)".format(
                    args.region_id, args.instance_id, args.command, ack))

    status = row.get("InvocationStatus") or row.get("InvokeRecordStatus") or "Unknown"
    output = _decode_output(row.get("Output") or "")
    ev.record("guest-output", {"InvokeId": invoke_id}, str(status),
              "ExitCode={0}, output lines={1}".format(row.get("ExitCode"),
                                                     len(output.splitlines())))
    if status in ("Failed", "Stopped", "Timeout", "Invalid", "Aborted", "Error"):
        ev.degrade()
        ev.finding("The command did not complete cleanly in the guest (status {0}).".format(status))
    else:
        ev.finding("Guest reading collected with no side effect.")

    print("=" * 72)
    print("GUEST OUTPUT :: {0}".format(command_string))
    print("=" * 72)
    print(output.rstrip() or "(empty output)")
    print("")

    return (ev, inputs, identity,
            "Interpret the output above; run snapshot-guard before any manual cleanup.")


# ---------------------------------------------------------------------------
# snapshot-guard (class C)
# ---------------------------------------------------------------------------
def cmd_snapshot_guard(args):
    ev = Evidence("ECS CLOUD BACKUP (HBR) SNAPSHOT GUARD")
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    ack = snapshot_ack(args.region_id, args.disk_id)
    inputs = {
        "region-id": args.region_id,
        "disk-id": args.disk_id,
        "reason": args.reason or "pre-cleanup safety copy",
        "consent": "given" if args.confirm else "NOT GIVEN",
    }

    if not args.confirm:
        for line in [
            "WHAT WILL RUN     : ecs:{0} with RegionId={1} DiskId={2}; no other parameter is "
            "sent".format(API_ECS_CREATE_SNAPSHOT, args.region_id, args.disk_id),
            "AFFECTS           : adds one snapshot for disk {0}".format(args.disk_id),
            "SIDE EFFECTS      : creates a billable resource; it writes nothing to the disk",
            "REVERSIBLE        : yes - the snapshot can be deleted afterwards; deleting it "
            "destroys its data irreversibly",
            "COST              : snapshots are billed by used capacity. Read the current price "
            "at {0} or {1} and state it to the customer before creating one.".format(
                DOC_LINKS["snapshot_billing"], DOC_LINKS["snapshot_billing_overview"]),
            "WHY THIS GATE     : every case in this tier that touched data inside an instance "
            "took a snapshot first; that habit is the reason this gate exists",
        ]:
            ev.manual(line)
        ev.finding("Nothing has been created yet; this is the pre-execution disclosure.")
        return (ev, inputs, identity,
                "After the customer agrees, re-run with --confirm {0}".format(ack))

    if args.confirm != ack:
        ev.fail()
        ev.finding("The supplied --confirm is not the consent token for this disk. Consent is "
                   "single-use and bound to region and disk.")
        return (ev, inputs, identity, "Re-run with --confirm {0}".format(ack))

    params = {"RegionId": args.region_id, "DiskId": args.disk_id}
    payload, error = call_soft(API_ECS_CREATE_SNAPSHOT, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_CREATE_SNAPSHOT, params, "WARN", str(error))
        if _is_error_authorisation(error):
            _permission_hint(ev, "ecs:{0}".format(API_ECS_CREATE_SNAPSHOT))
        else:
            ev.finding("Snapshot creation failed.")
        ev.degrade()
        return (ev, inputs, identity,
                "Resolve the reported error and retry; until a snapshot exists, no cleanup or "
                "in-guest change may proceed.")

    snapshot_id = payload.get("SnapshotId")
    ev.record(API_ECS_CREATE_SNAPSHOT, params, "OK", "SnapshotId={0}".format(snapshot_id))
    query_snapshots(ev, args.region_id, args.instance_id, disk_id=args.disk_id)
    ev.finding("Safety copy requested (SnapshotId={0}); wait until it reports accomplished "
               "before touching any data.".format(snapshot_id))
    ev.manual("Progress can be watched in the console: {0}".format(
        DOC_LINKS["snapshot_console"].format(region_id=args.region_id)))
    ev.manual("Retention of a snapshot can be extended manually: {0}".format(
        DOC_LINKS["extend_snapshot_retention"]))
    ev.manual(CLEANUP_MANUAL_WARNING)
    return (ev, inputs, identity,
            "Confirm the snapshot reached accomplished, then hand the cleanup itself to the "
            "customer.")


# ---------------------------------------------------------------------------
# check-env
# ---------------------------------------------------------------------------
def cmd_check_env(_args):
    import sts_token
    ev = Evidence("ECS CLOUD BACKUP (HBR) CREDENTIAL SELF-CHECK")
    ev.show_handoff = False
    inputs = {"credential-source": "default aliyun CLI credential chain",
              "profile-scope": sts_token.profile_scope()}
    record, error = sts_token.resolve_identity(use_cache=False)
    if error is not None:
        ev.record("sts/get-caller-identity", {}, "WARN", str(error))
        ev.fail()
        ev.finding("No usable credentials were found through the default credential chain.")
        ev.manual("Verify the default credential chain with `aliyun sts get-caller-identity`; no interactive setup is needed. This skill never "
                  "asks for, accepts, reads or stores a credential value.")
        if _is_error_authorisation(error):
            _permission_hint(ev, "sts:get-caller-identity")
        return (ev, inputs, "account=unverified",
                "Configure the default credential chain, then re-run check-env.")

    tag = sts_token.uid_tag(record)
    ev.record("sts/get-caller-identity", {}, "OK",
              "account tail {0}, identity type {1}".format(record.get("account_suffix"),
                                                           record.get("identity_type")))
    ev.finding("Credentials resolve to {0}.".format(tag))
    ev.note("Every call in this session carries the User-Agent above, so a report can be traced "
            "back to one run of this skill.")
    ev.note("The identity is resolved once and cached in .hbr-diagnosis-identity.json in the "
            "user home directory, which holds no credential material and stays out of the "
            "package working tree.")
    return (ev, inputs, tag,
            "Re-run triage with --region-id set to the region the alarm names.")


# ---------------------------------------------------------------------------
# explain
# ---------------------------------------------------------------------------
TOPIC_LOADERS = {}


def _topic(name):
    def decorator(func):
        TOPIC_LOADERS[name] = func
        return func
    return decorator


@_topic("concepts")
def _topic_concepts(args):
    return [
        "Snapshot - a point-in-time copy of a block-storage disk, in-region, billed by used "
        "capacity. This is the right answer for 'before I resize or upgrade the instance' and "
        "for ransomware containment, because it is taken at the disk layer.",
        "ECS File Backup Essential Edition - scheduled file-level backup and restore of paths "
        "inside the instance, driven by the Cloud Assistant agent. It restores single files; it "
        "does not rebuild a machine.",
        "Whole-instance backup (Cloud Backup) - orchestrates disk-level copies so an instance "
        "can be rebuilt. It is not a file-level undo button.",
        "ApsaraDB RDS backup - a different product with its own billing and console; it never "
        "shows up under an ECS backup page.",
        "The single most common misconception in this tier is treating those four as one "
        "feature. Always name the mechanism you mean.",
        "Official comparison: {0}".format(DOC_LINKS["protection_scheme_comparison"]),
        "Backup mechanism background: {0}".format(DOC_LINKS["ecs_backup_and_ha_architecture"]),
        "Local instance store disks are not covered the way cloud disks are - read this before "
        "promising protection: {0}".format(DOC_LINKS["backup_local_disk_data"]),
        "Ransomware or repeat intrusion: a file backup can be re-infected along with the system. "
        "Prefer a snapshot plus cross-region replication: {0}".format(
            DOC_LINKS["disaster_recovery_solutions"]),
    ]


@_topic("enable")
def _topic_enable(args):
    region = args.region_id or "<region-id>"
    return [
        "1. Open the ECS console set to the region that owns the instance, not the default one.",
        "2. Instance list -> the instance -> Backup tab: {0}".format(
            DOC_LINKS["instance_backup_console"].format(instance_id="<instance-id>",
                                                        region_id=region)),
        "3. Region-wide file backup page: {0}".format(
            DOC_LINKS["file_backup_console"].format(region_id=region)),
        "4. Activate the Essential Edition service. First activation auto-creates the "
        "service-linked role AliyunServiceRoleForHbrEcsBackup; with any outstanding balance that "
        "step fails and the console then shows nothing useful.",
        "5. Create the backup plan: choose paths, set the schedule, list excluded directories. "
        "Excluding caches and logs is what keeps the plan from failing on space.",
        "6. Full walkthrough: {0}".format(DOC_LINKS["configure_essential_edition"]),
        "7. Cloud Backup console: {0}".format(DOC_LINKS["hbr_console"]),
        "Owning a resource plan configures nothing. Enablement and the plan are separate steps, "
        "and several cases in this tier were only closed by walking a customer through these "
        "screens one at a time.",
    ]


@_topic("restore")
def _topic_restore(args):
    return [
        "1. Read the restore result details, including the tooltip behind the result icon: "
        "'completed' can mean 'completed, some files skipped'.",
        "2. Open the backup point and use Browse, expanding level by level to the exact path, "
        "before restoring anything.",
        "3. If the path is not in the point, no restore mode will create it. Check the earliest "
        "retained point before promising data.",
        "4. If the path is present but skipped, a process holds the files open - a running "
        "database engine is the classic case.",
        "5. Manual SOP: snapshot the target disk, stop the holding service, restore in overwrite "
        "mode, restart the service, verify inside the application.",
        "6. Stopping or restarting a service is never automated by this skill.",
        "7. Essential Edition restore reference: {0}".format(DOC_LINKS["configure_essential_edition"]),
        "8. Retention and free-quota specifics: {0}".format(DOC_LINKS["essential_edition_benefit"]),
    ]


@_topic("upgrade")
def _topic_upgrade(args):
    return [
        "1. Protect with a disk snapshot before a configuration change, not a file backup - the "
        "risk sits at the disk layer. Create it with the gated command: python3 "
        "scripts/areas/hbr_backup_diagnosis/hbr_backup_diagnosis.py snapshot-guard --region-id <region-id> "
        "--disk-id <disk-id>",
        "2. Wait until the snapshot reports accomplished. A first snapshot is a full copy and "
        "takes minutes to hours depending on how much was written; later ones are incremental.",
        "3. Creation guide: {0}".format(DOC_LINKS["create_snapshot"]),
        "4. Pricing: {0}".format(DOC_LINKS["snapshot_billing"]),
        "5. Deleting it afterwards is manual: {0}".format(DOC_LINKS["delete_snapshot"]),
        "6. A manual restart from the console takes effect immediately and voids a previously "
        "scheduled restart window.",
        "7. Before any reboot, state the three standing risks: business interruption, data still "
        "in the page cache and unwritten, and no safety copy taken.",
        "8. Configuration change overview: {0}".format(DOC_LINKS["instance_configuration_change"]),
    ]


@_topic("retention")
def _topic_retention(args):
    return [
        "Do not quote a retention day count, a version count or a free-quota size from memory or "
        "from a historical case. Two source cases for this tier stated conflicting figures, so "
        "the only acceptable answer is the current official page.",
        "Authoritative for retention, default policy and free quota: {0}".format(
            DOC_LINKS["essential_edition_benefit"]),
        "Authoritative for what the Essential Edition is billed on: {0}".format(
            DOC_LINKS["essential_edition_billing_basis"]),
        "Authoritative for every Cloud Backup billing item: {0}".format(
            DOC_LINKS["hbr_billing_methods"]),
        "Qualitative facts that are safe to state: the Essential Edition keeps a rolling set of "
        "points, expires them automatically, and offers no per-point delete because points are "
        "locked. 'I want fewer versions' is therefore not actionable, and the billing basis is "
        "tied to the block storage attached to the instance.",
        "Snapshot retention extension is a separate manual action: {0}".format(
            DOC_LINKS["extend_snapshot_retention"]),
    ]


@_topic("alarm-states")
def _topic_alarm_states(args):
    region = args.region_id or "<region-id>"
    return [
        "'Resource does not exist' plus a real bill: switch the console region selector through "
        "each region named on the bill. Console defaults are the biggest false negative in this "
        "tier.",
        "'Jobs are not listed, nothing I click works': check the account balance first. An "
        "outstanding balance blocks the automatic creation of the service-linked role "
        "AliyunServiceRoleForHbrEcsBackup and console functions silently vanish. It is not a "
        "browser, cache or incognito-mode problem.",
        "'EcsReleased, and the warning stays after I deleted everything': the entry is a "
        "historical record from the release moment. Deleting policies does not clear history and "
        "the list refreshes lazily. With zero protected resources no new alarm is produced.",
        "'There is a request id in the error dialog': collect it verbatim. Support escalated on "
        "the request id; nothing customer-side fixes an internal task error.",
        "File backup page for the region: {0}".format(
            DOC_LINKS["file_backup_console"].format(region_id=region)),
        "Cloud Backup console: {0}".format(DOC_LINKS["hbr_console"]),
        "Advanced manual path (never automated, and it permanently destroys data): {0} with "
        "RegionId={1}, planId=<plan-...>, sourceType=ECS_FILE, edition=BASIC".format(
            DOC_LINKS["delete_backup_plan_api"], region),
    ]


@_topic("guest-fallback")
def _topic_guest_fallback(args):
    return [
        "When no in-guest channel works, print the exact side-effect-free command, ask the "
        "customer to run it and paste the raw output, then continue the same decision tree. That "
        "is a legitimate degraded path, not a failure.",
        "Whitelisted probes: {0}".format(", ".join(sorted(GUEST_COMMANDS))),
        "Command semantics and how to read each output: references/hbr-backup-diagnosis__guest-commands.md",
        "Network-range, resolver and service-state inspection is deliberately outside the "
        "whitelist even though support engineers used it in the source cases: those readings "
        "belong to the customer or to an authorised engineer.",
        "Never substitute an improvised command. A command that is not on the list is rejected, "
        "however harmless it looks.",
        "One document is named by alarm text as a title only and no URL appeared in the source "
        "material, so none is invented here: {0}".format("; ".join(DOC_TITLES_WITHOUT_URL)),
    ]


def cmd_explain(args):
    ev = Evidence("ECS CLOUD BACKUP (HBR) GUIDANCE")
    ev.show_handoff = False
    inputs = {"topic": args.topic, "region-id": args.region_id or "not supplied",
              "instance-id": args.instance_id or "not supplied"}
    for line in TOPIC_LOADERS[args.topic](args):
        ev.manual(line)
    ev.finding("Guidance only: no cloud query was issued and nothing was changed.")
    return (ev, inputs, "not queried (guidance only)",
            "Ask which of the steps above the customer can see on their screen, then continue.")


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def _add_common(parser):
    parser.add_argument("--region-id", required=True,
                        help="the region the alarm or bill names, e.g. cn-hangzhou; always "
                             "confirm it with the customer")
    parser.add_argument("--instance-id", help="ECS instance id, i-...")
    parser.add_argument("--alarm-region",
                        help="region stated in the alarm text, used only for a mismatch check")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="hbr_backup_diagnosis.py",
        description="Diagnose Alibaba Cloud ECS Cloud Backup (HBR) file and whole-instance "
                    "backup failures, restore surprises, alarm states and billing attribution.",
    )
    sub = parser.add_subparsers(dest="subcommand")
    sub.required = True

    env = sub.add_parser("check-env",
                         help="verify the default credential chain and print the identity tag")
    env.set_defaults(func=cmd_check_env)

    triage = sub.add_parser("triage",
                            help="classify an alarm and run the informational queries")
    _add_common(triage)
    triage.add_argument("--alert-text", help="alarm or SMS text as the customer phrased it")
    triage.add_argument("--category", choices=ALL_CATEGORIES,
                        help="skip text classification when the class is already known")
    triage.add_argument("--os-type", choices=("linux", "windows"),
                        help="override guest OS detection when picking the first probe")
    triage.set_defaults(func=cmd_triage)

    probe = sub.add_parser("guest-probe",
                           help="run one whitelisted side-effect-free guest command")
    probe.add_argument("--region-id", required=True)
    probe.add_argument("--instance-id", required=True)
    probe.add_argument("--command", required=True,
                       help="probe key, e.g. df_h; see references/hbr-backup-diagnosis__guest-commands.md")
    probe.add_argument("--target",
                       help="absolute path or drive letter, for probes that take one")
    probe.add_argument("--confirm", help="single-use consent token printed by a prior run")
    probe.set_defaults(func=cmd_guest_probe)

    snap = sub.add_parser("snapshot-guard",
                          help="create the pre-cleanup snapshot, consent-gated")
    snap.add_argument("--region-id", required=True)
    snap.add_argument("--disk-id", required=True)
    snap.add_argument("--instance-id", help="scopes the follow-up read")
    snap.add_argument("--reason", help="why the snapshot is needed; printed in the report")
    snap.add_argument("--confirm", help="single-use consent token printed by a prior run")
    snap.set_defaults(func=cmd_snapshot_guard)

    billing = sub.add_parser("billing-attribution",
                             help="list the real instances, disks and snapshots behind a charge")
    _add_common(billing)
    billing.set_defaults(func=cmd_billing_attribution)

    explain = sub.add_parser("explain", help="print a guidance block for a support question")
    explain.add_argument("--topic", required=True, choices=sorted(TOPIC_LOADERS))
    explain.add_argument("--region-id", help="used only to build console deep links")
    explain.add_argument("--instance-id", help="used only to build console deep links")
    explain.set_defaults(func=cmd_explain)
    return parser


def _run_selftest():
    """Offline boundary locks for the guest-probe command policy gate.

    These are fail-closed security gates: a single dropped metacharacter check
    or a widened path rule would let a customer-supplied ``--target`` ride a
    shell injection into a Cloud Assistant RunCommand. The probes are also the
    only place a target string reaches the guest, so the rejection cases matter
    as much as the accepted ones. Pure logic only - no cloud, no credentials.
    """
    import argparse

    rc = 0

    def expect(name, cond):
        nonlocal rc
        print("PASS" if cond else "FAIL", name)
        if not cond:
            rc = 1

    def rejects_target(value):
        try:
            _validate_target(value)
            return False
        except CommandPolicyError:
            return True

    # _validate_target: accept the three legitimate path forms only.
    expect("tgt_posix", _validate_target("/srv/backups") == "/srv/backups")
    expect("tgt_root", _validate_target("/") == "/")
    expect("tgt_drive", _validate_target("C:") == "C:")
    expect("tgt_winpath", _validate_target("C:\\dir") == "C:\\dir")
    expect("tgt_reject_empty", rejects_target(""))
    expect("tgt_reject_semicolon", rejects_target("/tmp;a"))
    expect("tgt_reject_pipe", rejects_target("/tmp|x"))
    expect("tgt_reject_space", rejects_target("/tmp a"))
    expect("tgt_reject_dotdot", rejects_target("../../etc/passwd"))
    expect("tgt_reject_relative", rejects_target("relative/path"))

    # _validate_command_string: no metacharacter, no rejected token survives.
    expect("cmd_ok", _validate_command_string("du -x --max-depth=1 /data/x")
           == "du -x --max-depth=1 /data/x")

    def rejects_cmd(value):
        try:
            _validate_command_string(value)
            return False
        except CommandPolicyError:
            return True
    expect("cmd_reject_meta", rejects_cmd("du /x; rm -rf /"))
    expect("cmd_reject_token", rejects_cmd("chmod 777 /data"))

    # build_guest_command: whitelist + target-required / target-rejected pairing.
    expect("bgc_target", build_guest_command("du_top", "/data/x")
           == ("RunShellScript", "du -x --max-depth=1 /data/x"))

    def bgc_raises(key, target):
        try:
            build_guest_command(key, target)
            return False
        except CommandPolicyError:
            return True
    expect("bgc_reject_unknown_key", bgc_raises("not-a-probe", "/x"))
    expect("bgc_reject_extra_target", bgc_raises("df_h", "/x"))
    expect("bgc_require_missing_target", bgc_raises("du_top", None))

    # classify: never guesses, forced passthrough.
    expect("cls_backup", classify("backup job failed")[0] == "BACKUP_TASK_ABNORMAL")
    expect("cls_empty_unknown", classify("")[0] == "UNKNOWN")
    expect("cls_nomatch_unknown", classify("zzz nothing here")[0] == "UNKNOWN")
    expect("cls_forced", classify("whatever", forced="ROLE_OR_BILLING_BLOCKED")[0]
           == "ROLE_OR_BILLING_BLOCKED")

    # _decode_output: base64 body decoded, non-base64 returned raw.
    expect("dec_b64", _decode_output("aGVsbG8=") == "hello")
    expect("dec_raw", _decode_output("plain text not b64") == "plain text not b64")
    expect("dec_empty", _decode_output("") == "")

    # auth detection and OS shaping.
    expect("auth_noperm", _is_error_authorisation("NoPermission: ImplicitDeny") is True)
    expect("auth_other", _is_error_authorisation("Throttling.User") is False)
    expect("win_osflag", _looks_windows(argparse.Namespace(os_type="windows"), None) is True)
    expect("win_instance", _looks_windows(argparse.Namespace(os_type=None), {"OSType": "windows"}) is True)
    expect("win_default_linux", _looks_windows(argparse.Namespace(os_type=None), {}) is False)

    print("SELFTEST:", "PASS" if rc == 0 else "FAIL")
    return rc


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        ev, inputs, identity, next_action = args.func(args)
    except CliError as exc:
        sys.stderr.write("[WARN] {0}\n".format(mask_secrets(str(exc))))
        print("STATUS: FAIL")
        print("NEXT_ACTION: resolve the reported error, then re-run the same command.")
        return 1

    print(ev.render(identity, inputs, next_action))
    return {"OK": 0, "DEGRADED": 2}.get(ev.status, 1)


if __name__ == "__main__":
    sys.exit(main())
