#!/usr/bin/env python3
"""Single entry point for ECS Cloud Assistant command and agent diagnosis.

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
from datetime import datetime, timedelta, timezone

from _cli import (
    call_soft,
    mask_secrets,
    paginate_page_number,
    session_id,
    user_agent,
)
from _constants import (
    ALL_CATEGORIES,
    API_ECS_CREATE_SNAPSHOT,
    API_ECS_DESCRIBE_INSTANCE_STATUS,
    API_ECS_DESCRIBE_INSTANCES,
    API_ECS_DESCRIBE_INVOCATIONS,
    API_ECS_RUN_COMMAND,
    AUTH_ERROR_TOKENS,
    CATEGORY_AGENT_NOT_READY,
    CATEGORY_AK_ABUSE,
    CATEGORY_CLIENT_RESTARTED,
    CATEGORY_COMMAND_TIMEOUT,
    CATEGORY_DEPENDENCY_BLOCKED,
    CATEGORY_EXPAND_TASK_FAILED,
    CATEGORY_GUEST_ENV_BROKEN,
    CATEGORY_SOFTWARE_INSTALL_FAILED,
    CATEGORY_TASK_CONFLICT,
    CATEGORY_UNKNOWN,
    CATEGORY_VERSION_UPGRADE,
    DEFAULT_PAGE_SIZE,
    DEPENDENCY_FEATURES,
    DOC_LINKS,
    ECS_API_VERSION,
    FAILURE_CLASS_GUIDE,
    FINISHED_STATES,
    GUEST_COMMANDS,
    GUEST_POLL_INTERVAL_SECONDS,
    GUEST_POLL_MAX_ATTEMPTS,
    HANDOFF_RULES,
    INVOCATION_MAX_PAGES,
    NON_RUNNING_STATES,
    PRODUCT_ECS,
    READINESS_STEPS_LINUX,
    READINESS_STEPS_WINDOWS,
    REJECTED_COMMAND_TOKENS,
    ROOT_CAUSE_CANDIDATES,
    SHELL_METACHARACTERS,
    SKILL_NAME,
    STS_API_VERSION,
    SYMPTOM_PATTERNS,
)

MAX_ERROR_FIELD_CHARS = 220
MAX_OUTPUT_DIGEST_CHARS = 700
RECENT_ROWS_IN_SUMMARY = 8

_REJECTED_TOKENS = frozenset(token.lower() for token in REJECTED_COMMAND_TOKENS)

_NEXT_BY_CATEGORY = {
    CATEGORY_AGENT_NOT_READY:
        "Give the customer the readiness steps printed above (service start and "
        "installation are customer actions), then re-run triage to verify from "
        "new history.",
    CATEGORY_VERSION_UPGRADE:
        "Have the customer upgrade the agent from the installation page; for a "
        "blocked password change meanwhile use the offline reset with a snapshot "
        "first.",
    CATEGORY_COMMAND_TIMEOUT:
        "Confirm the saturation or volume hypotheses: read the monitor curves "
        "for the failure window, then offer a whitelisted df_h guest-probe with "
        "consent.",
    CATEGORY_CLIENT_RESTARTED:
        "Ask for monitor evidence around the interrupt time; where the customer "
        "declines instance operations, use the degraded-mode reading list.",
    CATEGORY_GUEST_ENV_BROKEN:
        "Hand off to the instance-state / OS repair area with this report "
        "attached; advise a snapshot before repair attempts.",
    CATEGORY_SOFTWARE_INSTALL_FAILED:
        "State plainly that the channel worked and the software content failed; "
        "software setup stays a customer action.",
    CATEGORY_EXPAND_TASK_FAILED:
        "Hand off to area:disk-expand-diagnosis for the partition "
        "and filesystem growth itself; this report covers only why the "
        "assistant task failed.",
    CATEGORY_TASK_CONFLICT:
        "Point at the in-flight conflicting task; lifecycle force actions are "
        "customer decisions.",
    CATEGORY_AK_ABUSE:
        "Run the invocations evidence list per affected region and move it to "
        "the security response flow; disable the leaked key first.",
    CATEGORY_DEPENDENCY_BLOCKED:
        "Restore agent health via the readiness steps, or take the documented "
        "offline fallback for the blocked feature.",
    CATEGORY_UNKNOWN:
        "Collect the full console error text, the invoke id and the time "
        "window, then re-run triage with --error-text quoting it verbatim.",
}


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
            out.append("  {0:<18}: {1}".format(key, mask_secrets(str(inputs[key]))))
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


def _truncate(text, limit=MAX_ERROR_FIELD_CHARS):
    if not text:
        return "-"
    text = str(text)
    return text if len(text) <= limit else text[:limit] + "..."


# ---------------------------------------------------------------------------
# Symptom classification
# ---------------------------------------------------------------------------
def classify(error_text, forced=None):
    """Return (category, matched_tokens). Never guesses: no match -> UNKNOWN."""
    if forced and forced != CATEGORY_UNKNOWN:
        return forced, ["--category given"]
    if not error_text:
        return CATEGORY_UNKNOWN, []
    haystack = error_text.lower()
    for category, patterns in SYMPTOM_PATTERNS:
        hits = [token for token in patterns if token in haystack]
        if hits:
            return category, sorted(set(hits))[:6]
    return CATEGORY_UNKNOWN, []


def _instances_of(payload):
    return (payload.get("Instances") or {}).get("Instance") or []


def _invocation_rows(payload):
    """Merge invocation-level fields into each instance-level record so one
    row carries command name, status, exit code and output together."""
    collected = []
    for invocation in (payload.get("Invocations") or {}).get("Invocation") or []:
        base = {
            "InvokeId": invocation.get("InvokeId"),
            "CommandName": invocation.get("CommandName"),
            "CommandType": invocation.get("CommandType"),
            "Username": invocation.get("Username"),
            "InvocationStatus": invocation.get("InvocationStatus"),
            "CreationTime": invocation.get("CreationTime"),
        }
        for instance in (invocation.get("InvokeInstances") or {}).get("InvokeInstance") or []:
            merged = dict(base)
            # The instance record carries the per-machine status, exit code,
            # error info and output, so it overlays the invocation summary.
            merged.update(instance)
            collected.append(merged)
    return collected


def _is_windows(instance):
    blob = " ".join(str(instance.get(key) or "") for key in
                    ("OSType", "OSName", "OSNameEn", "ImageId")).lower()
    return "windows" in blob


def _row_status(row):
    return str(row.get("InvocationStatus") or row.get("InvokeRecordStatus") or "Unknown")


def _row_text(row):
    parts = [_row_status(row), row.get("ErrorInfo"), row.get("Output"),
             row.get("CommandName")]
    return " ".join(str(p or "") for p in parts).lower()


def _row_line(row, with_output=False):
    line = ("[{0}] {1} invoke={2} command={3} exit={4} time={5} error={6}".format(
        _row_status(row),
        row.get("InstanceId", "?"),
        row.get("InvokeId", "?"),
        row.get("CommandName", "-"),
        row.get("ExitCode", "-"),
        row.get("StartTime") or row.get("CreationTime") or "-",
        _truncate(row.get("ErrorInfo")),
    ))
    if with_output:
        digest = _decode_output(row.get("Output") or "").replace("\r", " ").replace(
            "\n", " / ")
        line += " | output: {0}".format(_truncate(digest, MAX_OUTPUT_DIGEST_CHARS))
    return line


def _parse_utc(value):
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%MZ"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            continue
    return None


def _within_window(row, hours):
    """True when the row's timestamps fall inside the last N hours. A row
    whose time cannot be parsed is KEPT: dropping data silently is worse than
    a slightly wide window."""
    if not hours:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    for key in ("StartTime", "FinishTime", "CreationTime"):
        stamp = _parse_utc(row.get(key))
        if stamp is not None:
            return stamp >= cutoff
    return True


def derive_category(category, rows, history_available):
    """When the customer's wording matched nothing, let the history speak."""
    if category != CATEGORY_UNKNOWN:
        return category
    if not history_available:
        return CATEGORY_UNKNOWN
    if not rows:
        return CATEGORY_AGENT_NOT_READY
    for row in rows:
        text = _row_text(row)
        if "client_restarted" in text or "clientrestarted" in text:
            return CATEGORY_CLIENT_RESTARTED
        if "timeout" in text:
            return CATEGORY_COMMAND_TIMEOUT
    for row in rows:
        text = _row_text(row)
        for needle, target in (
                ("internal or external command", CATEGORY_GUEST_ENV_BROKEN),
                ("cannot find the file specified", CATEGORY_GUEST_ENV_BROKEN),
                ("install", CATEGORY_SOFTWARE_INSTALL_FAILED),
                ("yum", CATEGORY_SOFTWARE_INSTALL_FAILED),
                ("growpart", CATEGORY_EXPAND_TASK_FAILED),
                ("resize2fs", CATEGORY_EXPAND_TASK_FAILED),
        ):
            if needle in text:
                return target
    return CATEGORY_UNKNOWN


# ---------------------------------------------------------------------------
# Class A queries
# ---------------------------------------------------------------------------
def query_instance(ev, region_id, instance_id):
    """Returns a dict when visible, {} when not found, None on error."""
    params = {"RegionId": region_id, "InstanceIds": json.dumps([instance_id]),
              "PageSize": DEFAULT_PAGE_SIZE}
    payload, error = call_soft(API_ECS_DESCRIBE_INSTANCES, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_INSTANCES, {"RegionId": region_id}, "WARN", str(error))
        ev.degrade()
        return None
    instances = _instances_of(payload)
    if not instances:
        ev.record(API_ECS_DESCRIBE_INSTANCES, params, "EMPTY",
                  "no such instance visible to this account in {0}".format(region_id))
        return {}
    inst = instances[0]
    ev.record(API_ECS_DESCRIBE_INSTANCES, params, "OK", "{0} Status={1} OS={2} "
              "Name={3} ChargeType={4}".format(
                  inst.get("InstanceId"), inst.get("Status"),
                  "windows" if _is_windows(inst) else "linux",
                  _truncate(inst.get("InstanceName"), 60),
                  inst.get("InstanceChargeType")))
    return inst


def query_instance_status(ev, region_id, instance_id):
    params = {"RegionId": region_id, "InstanceId.1": instance_id}
    payload, error = call_soft(API_ECS_DESCRIBE_INSTANCE_STATUS, params,
                               product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_DESCRIBE_INSTANCE_STATUS, params, "WARN", str(error))
        ev.degrade()
        return None
    statuses = (payload.get("InstanceStatuses") or {}).get("InstanceStatus") or []
    for entry in statuses:
        if entry.get("InstanceId") == instance_id:
            ev.record(API_ECS_DESCRIBE_INSTANCE_STATUS, params, "OK",
                      "Status={0}".format(entry.get("Status")))
            return entry.get("Status")
    ev.record(API_ECS_DESCRIBE_INSTANCE_STATUS, params, "EMPTY",
              "no lifecycle status returned for the instance")
    return None


def query_invocations(ev, region_id, instance_id=None, invoke_id=None,
                      include_output=False, hours=None):
    """Return (rows, error). Rows is the merged per-instance history."""
    params = {"RegionId": region_id}
    if instance_id:
        params["InstanceId"] = instance_id
    if invoke_id:
        params["InvokeId"] = invoke_id
    if include_output:
        params["IncludeOutput"] = True
        params["ContentEncoding"] = "PlainText"
    scope = {k: v for k, v in params.items() if k != "IncludeOutput"}
    invocations, page_note = paginate_page_number(API_ECS_DESCRIBE_INVOCATIONS, params,
                                                 ["Invocations", "Invocation"],
                                                 "Invocation",
                                                 product=PRODUCT_ECS,
                                                 page_size=DEFAULT_PAGE_SIZE,
                                                 max_pages=INVOCATION_MAX_PAGES)
    rows = _invocation_rows({"Invocations": {"Invocation": invocations}})
    if page_note is not None and not rows:
        ev.record(API_ECS_DESCRIBE_INVOCATIONS, scope, "WARN", page_note)
        ev.degrade()
        return None, page_note
    if hours:
        rows = [r for r in rows if _within_window(r, hours)]
    if page_note is not None:
        ev.note("History pagination: {0}".format(page_note))
    if not rows:
        if invocations:
            ev.note("The history query returned {0} invocation record(s) but none carried "
                    "a per-instance record, so status, exit code and output could not be "
                    "read; the empty-history inference below is weaker than a real "
                    "no-records result.".format(len(invocations)))
        ev.record(API_ECS_DESCRIBE_INVOCATIONS, scope, "EMPTY",
                  "{0} invocation record(s), no per-instance record".format(len(invocations))
                  if invocations else "no Cloud Assistant invocation history matched")
        return [], None
    ev.record(API_ECS_DESCRIBE_INVOCATIONS, scope, "OK", "{0} record(s) in view; "
              "latest: {1}".format(len(rows), "; ".join(
                  "{0} status={1} exit={2}".format(r.get("InvokeId"),
                                                   _row_status(r),
                                                   r.get("ExitCode"))
                  for r in rows[:RECENT_ROWS_IN_SUMMARY])))
    return rows, None


def add_region_note(ev, region_id):
    ev.note(
        "Region under query: {0}. State it back to the customer and confirm it is the "
        "region the console error names. A wrong console region is a confirmed cause of "
        "'the instance does not exist' answers in this scenario.".format(region_id)
    )


def add_candidates(ev, category):
    for candidate in ROOT_CAUSE_CANDIDATES.get(category, ()):
        ev.candidate(candidate)


def add_gap_notes(ev):
    ev.note(
        "No verified agent-online-status query exists for this scenario "
        "(the status API was not verified), so readiness is inferred from command "
        "history plus the customer's error wording; say so in the report rather than "
        "claiming a live status."
    )
    ev.note(
        "CloudMonitor metrics are not part of this skill's verified API surface, so "
        "CPU/IO saturation stays a hypothesis to confirm in the console, never a "
        "reading taken here."
    )


def add_readiness_manuals(ev, is_win):
    steps = READINESS_STEPS_WINDOWS if is_win else READINESS_STEPS_LINUX
    for step in steps:
        ev.manual(step)
    ev.manual(
        "Workbench-side command management (creating and running Cloud Assistant "
        "scripts interactively): {0}".format(DOC_LINKS["workbench_script_library"])
    )
    ev.manual(
        "Running an already-created command without the API: {0}".format(
            DOC_LINKS["run_existing_command"])
    )


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
        rows, page_note = paginate_page_number(
            API_ECS_DESCRIBE_INVOCATIONS,
            {"RegionId": region_id, "InvokeId": invoke_id,
             "IncludeOutput": True, "ContentEncoding": "PlainText"},
            ["Invocations", "Invocation"], "Invocation",
            product=PRODUCT_ECS, page_size=DEFAULT_PAGE_SIZE,
            max_pages=2)
        if page_note is not None:
            return None, "the result could not be read back: {0}".format(page_note)
        merged = _invocation_rows({"Invocations": {"Invocation": rows}}) \
            if rows else []
        for row in merged:
            if _row_status(row) in FINISHED_STATES:
                return row, None
        if attempt < GUEST_POLL_MAX_ATTEMPTS - 1:
            time.sleep(GUEST_POLL_INTERVAL_SECONDS)
    return None, "no final state within the polling budget (the agent may be " \
                 "exactly the thing that is down)"


def _is_error_authorisation(error):
    text = str(error)
    return any(token in text for token in AUTH_ERROR_TOKENS)


def _permission_hint(ev, action_name):
    ev.finding(
        "The identity in use is not permitted to call {0} (NoPermission / ImplicitDeny). "
        "Report the missing action and hand the customer the minimal statement from "
        "references/ram-policies.md. Do not widen permissions or substitute a broader "
        "policy.".format(action_name)
    )


# ---------------------------------------------------------------------------
# triage
# ---------------------------------------------------------------------------
def cmd_triage(args):
    ev = Evidence("ECS CLOUD ASSISTANT DIAGNOSIS REPORT")
    category, hits = classify(args.error_text, args.category)
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id or "not supplied",
        "error-text": _truncate(args.error_text or "not supplied", 160),
        "category": args.category or "auto",
        "classified-as": "{0} (matched: {1})".format(category, ", ".join(hits) or "none"),
        "history-window": ("last {0}h".format(args.hours) if args.hours
                           else "no time filter"),
        "invocation-id": args.invocation_id or "not supplied",
    }
    identity, _ = _resolve_identity()
    add_region_note(ev, args.region_id)

    if not args.instance_id:
        ev.fail()
        ev.finding("Without an instance id there is nothing to attribute: every branch "
                   "of this scenario's tree starts at one concrete instance.")
        return (ev, inputs, identity,
                "Ask the customer for the instance id and the region named in the "
                "console error, then re-run triage with both.")

    instance = query_instance(ev, args.region_id, args.instance_id)
    if instance is None:
        return (ev, inputs, identity,
                "Fix the failed query first (see the WARN line above): most often this "
                "is a denied action or a bad region. Nothing was concluded yet.")
    if not instance:
        ev.finding(
            "The instance id is NOT visible to the account this session resolves to, in "
            "this region. Case T-D87E8F47 ended at exactly this point: before touching "
            "the agent, the instance must be confirmed in the right region and owned by "
            "the right account. Two explanations remain: wrong region, or a different "
            "account."
        )
        ev.note("The session resolves to {0}; this skill cannot and must not diagnose "
                "another account's instance blind.".format(identity))
        ev.manual("Ask the customer to switch the console region selector and confirm "
                  "the owning account, then re-run against the corrected region.")
        return (ev, inputs, identity,
                "Have the customer confirm region and owning account, then re-run "
                "triage with the corrected --region-id.")

    is_win = _is_windows(instance)
    ev.finding("Instance {0} is visible; guest OS read as {1}. The guest command "
               "dialect follows from this field.".format(
                   args.instance_id, "Windows" if is_win else "Linux"))

    lifecycle = query_instance_status(ev, args.region_id, args.instance_id)
    if lifecycle in NON_RUNNING_STATES:
        ev.finding(
            "The instance lifecycle state is '{0}', not Running. While the machine is "
            "stopped or in a transition, no Cloud Assistant verdict is trustworthy: "
            "several source cases chased an agent symptom that was really a boot or "
            "shutdown problem (cases T-DE98E694, T-75912401).".format(lifecycle)
        )
        ev.note("Hand off to the instance-state area; carry this report with you, the "
                "ownership and OS checks are already done.")
        return (ev, inputs, identity,
                "Transfer to area:instance-state-diagnosis (or the console "
                "boot checks in references/cloud-assistant-diagnosis__handoff-matrix.md); revisit Cloud Assistant "
                "only once the instance is Running.")

    rows, query_error = query_invocations(ev, args.region_id,
                                          instance_id=args.instance_id,
                                          invoke_id=args.invocation_id,
                                          include_output=True,
                                          hours=args.hours)
    history_available = query_error is None
    if history_available and args.invocation_id and not rows:
        ev.finding("No history row carries invoke id {0} in this region - the id may be "
                   "mistyped or belong to another region.".format(args.invocation_id))

    derived = derive_category(category, rows or [], history_available)
    inputs["derived-class"] = derived

    if history_available:
        if not rows:
            ev.finding(
                "The instance exists and (per the lifecycle check) runs, but Cloud "
                "Assistant has NO execution history here. Either the agent has never "
                "checked in (missing, stopped, or blocked from its endpoint) or the "
                "requested window is empty. Readiness is the branch to work."
            )
            add_readiness_manuals(ev, is_win)
        else:
            ev.finding("{0} invocation record(s) in view; the decisive evidence is the "
                       "status / exit code / error-info triple of the failing run.".format(
                           len(rows)))
            for row in (rows or [])[:RECENT_ROWS_IN_SUMMARY]:
                ev.note(_row_line(row, with_output=True))

    add_candidates(ev, derived)
    add_gap_notes(ev)

    if derived == CATEGORY_AK_ABUSE:
        ev.manual("Switch to the invocations evidence mode to list the full history "
                  "for this instance or region; keep the output as the evidence list.")
        ev.manual("Enable automatic saving of Cloud Assistant command results so future "
                  "tasks are archived on the instance: {0}".format(
                      DOC_LINKS["assistant_command_autosave"]))
    if derived == CATEGORY_DEPENDENCY_BLOCKED:
        for feature in DEPENDENCY_FEATURES:
            ev.manual("{0} -> depends on: {1} (case {2})".format(
                feature["feature"], feature["depends"], feature["case"]))
        ev.manual("Offline fallback for a blocked password change (reboot involved - "
                  "snapshot first): {0} | {1}".format(
                      DOC_LINKS["reset_password_offline"],
                      DOC_LINKS["logon_credential_management"]))
    if derived == CATEGORY_EXPAND_TASK_FAILED:
        ev.manual("The growth itself is the disk-expand area; this report answers only "
                  "why the dispatched task failed. Linux page for the hand-off: {0} | "
                  "Windows: {1}".format(DOC_LINKS["expand_partition_linux"],
                                        DOC_LINKS["resize_windows_disks"]))
    if derived in (CATEGORY_COMMAND_TIMEOUT, CATEGORY_CLIENT_RESTARTED):
        ev.manual("Whitelisted environment exclusion (one consent each): run "
                  "guest-probe --command df_h and, on Linux, --command df_i.")
    if derived == CATEGORY_GUEST_ENV_BROKEN:
        ev.manual("Before any repair, snapshot the disk (snapshot-guard, consented); "
                  "if a detach-and-fix path is chosen, see "
                  "{0}".format(DOC_LINKS["detach_attach_system_disk"]))

    return (ev, inputs, identity, _NEXT_BY_CATEGORY.get(derived, _NEXT_BY_CATEGORY[
        CATEGORY_UNKNOWN]))


# ---------------------------------------------------------------------------
# invocations (evidence list)
# ---------------------------------------------------------------------------
def cmd_invocations(args):
    ev = Evidence("ECS CLOUD ASSISTANT EXECUTION-HISTORY EVIDENCE LIST")
    ev.show_handoff = False
    inputs = {
        "region-id": args.region_id,
        "instance-id": args.instance_id or "whole region",
        "history-window": ("last {0}h".format(args.hours) if args.hours
                           else "no time filter (newest first)"),
        "include-output": "yes" if args.include_output else "no",
    }
    identity, _ = _resolve_identity()
    rows, query_error = query_invocations(ev, args.region_id,
                                          instance_id=args.instance_id,
                                          include_output=args.include_output,
                                          hours=args.hours)
    if query_error is not None:
        return (ev, inputs, identity,
                "The history query failed (see the WARN line): resolve the denied or "
                "unreachable query before treating the evidence list as complete.")
    if not rows:
        ev.finding("No Cloud Assistant execution history matched this scope. For a "
                   "suspected abuse case that is itself evidence: the attacker's "
                   "commands may be under another region - repeat per region.")
    else:
        ev.finding("{0} record(s) listed. Every line the customer does not recognise "
                   "is abuse evidence: preserve it verbatim.".format(len(rows)))

    print("=" * 72)
    print("EXECUTION HISTORY :: {0}".format(
        args.instance_id or ("region " + args.region_id)))
    print("=" * 72)
    for row in rows[:200]:
        print(_row_line(row, with_output=args.include_output))
    if len(rows) > 200:
        print("(list truncated at 200 rows; narrow with --instance-id or --hours)")
    print("")

    ev.manual("Order of response is a security decision, not this skill's: disable the "
              "leaked access key in the RAM console first, then snapshot, then clean "
              "persistence. This skill only supplies the evidence list above.")
    ev.manual("Archive future command output on the instance automatically: {0}".format(
        DOC_LINKS["assistant_command_autosave"]))
    ev.note("No credential material appears in this list; the query ran through the "
            "default credential chain and error text is masked.")
    ev.note("Query limitations: the list reflects retained history visible to the API "
            "page guard above, not a full audit trail, and the full text of one-shot "
            "commands may only be archived if automatic saving was enabled "
            "beforehand.")
    return (ev, inputs, identity,
            "Hand the history above to the customer's security owner (or the "
            "responder), then continue with the AK-abuse branch in "
            "references/cloud-assistant-diagnosis__agent-readiness.md.")


# ---------------------------------------------------------------------------
# guest-probe (class B)
# ---------------------------------------------------------------------------
def cmd_guest_probe(args):
    ev = Evidence("ECS CLOUD ASSISTANT GUEST PROBE")
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
        ev.note("Agent-service state (systemctl), agent log reads, and partition-table "
                "readers (lsblk/fdisk/blkid) are deliberately NOT whitelisted in this "
                "scenario: they are printed as customer-run steps in "
                "references/cloud-assistant-diagnosis__guest-commands.md, never executed.")
        return (ev, inputs, identity,
                "Pick a whitelisted --command and re-run; semantics are in "
                "references/cloud-assistant-diagnosis__guest-commands.md.")

    ev.record("command-policy", {"probe": args.command}, "OK",
              "single assembled command accepted by the whitelist")

    if not args.confirm:
        for line in [
            "WHAT WILL RUN     : {0}".format(command_string),
            "GUEST OS          : {0}".format(spec["os"]),
            "DELIVERY          : ecs {0} Type={1}, one command, one instance".format(
                API_ECS_RUN_COMMAND, command_type),
            "AFFECTS           : instance {0} alone; it inspects state inside it and "
            "modifies nothing".format(args.instance_id),
            "SIDE EFFECTS      : none; the command reports usage or metadata and "
            "writes nothing",
            "REVERSIBLE        : n/a, nothing is modified",
            "COST              : this probe itself is not billed",
            "PRECONDITION      : the Cloud Assistant agent must be reachable inside "
            "the instance - this scenario's subject is often exactly that failing",
            "PURPOSE           : {0}".format(spec["purpose"]),
            "REPORTS           : {0}".format(spec["reports"]),
            "SCOPE OF CONSENT  : the token below authorises exactly this "
            "region/instance/command and expires with it; a second command needs a "
            "second consent",
        ]:
            ev.manual(line)
        ev.finding("Nothing has been executed yet; this is the pre-execution "
                   "disclosure.")
        return (ev, inputs, identity,
                "Read the lines above to the customer and get their agreement, then "
                "re-run with --confirm {0}".format(ack))

    if args.confirm != ack:
        ev.fail()
        ev.finding("The supplied --confirm is not the consent token for this exact "
                   "operation. Consent is single-use and bound to region, instance, "
                   "probe and target.")
        return (ev, inputs, identity, "Re-run with --confirm {0}".format(ack))

    params = {
        "RegionId": args.region_id,
        "Type": command_type,
        "CommandContent": command_string,
        "ContentEncoding": "PlainText",
        "InstanceId.1": args.instance_id,
    }
    payload, error = call_soft(API_ECS_RUN_COMMAND, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_RUN_COMMAND, {"RegionId": args.region_id,
                                        "Type": command_type,
                                        "CommandContent": command_string},
                  "WARN", str(error))
        ev.degrade()
        if _is_error_authorisation(error):
            _permission_hint(ev, API_ECS_RUN_COMMAND)
        else:
            ev.finding("The probe could not be delivered. The commonest reason in this "
                       "scenario is that the Cloud Assistant agent is itself unreachable - "
                       "which is the failure under diagnosis, and the report must say "
                       "so rather than retry.")
        ev.note("Degraded mode: give the customer `{0}` to run in the instance and "
                "have them paste the raw output; then continue the same decision tree. "
                "See references/cloud-assistant-diagnosis__guest-commands.md section 'Degraded mode'.".format(
                    command_string))
        return (ev, inputs, identity,
                "Degrade to customer-pasted output for `{0}`; do not retry the "
                "dispatch against a downed agent.".format(command_string))

    invoke_id = payload.get("InvokeId")
    if not invoke_id:
        ev.record(API_ECS_RUN_COMMAND, {"RegionId": args.region_id,
                                        "InstanceId.1": args.instance_id},
                  "WARN", "the dispatch returned no invoke id, so this probe's own "
                          "result cannot be read back without picking up unrelated "
                          "history records")
        ev.degrade()
        return (ev, inputs, identity,
                "Read the task result in the console command-execution list, or have "
                "the customer run `{0}` in an interactive session and paste it; do not "
                "re-dispatch blind.".format(command_string))
    ev.record(API_ECS_RUN_COMMAND, {"RegionId": args.region_id,
                                    "InstanceId.1": args.instance_id},
              "OK", "dispatched, InvokeId={0}".format(invoke_id))

    row, poll_error = poll_invocation(ev, args.region_id, invoke_id)
    if poll_error is not None:
        ev.record("read-back", {"InvokeId": invoke_id}, "WARN", poll_error)
        ev.degrade()
        return (ev, inputs, identity,
                "Re-read the result once the agent reports in (fresh consent needed "
                "for any re-dispatch): guest-probe --region-id {0} --instance-id {1} "
                "--command {2}".format(args.region_id, args.instance_id, args.command))

    status = _row_status(row)
    output = _decode_output(row.get("Output") or "")
    ev.record("guest-output", {"InvokeId": invoke_id}, status,
              "ExitCode={0}, output lines={1}".format(row.get("ExitCode"),
                                                      len(output.splitlines())))
    if status in ("Failed", "Stopped", "Timeout", "Invalid", "Aborted", "Error"):
        ev.degrade()
        ev.finding("The probe did not complete cleanly in the guest (status {0}). A "
                   "failing inspection command is itself a finding about the guest "
                   "environment.".format(status))
    else:
        ev.finding("Guest reading collected with no side effect.")

    print("=" * 72)
    print("GUEST OUTPUT :: {0}".format(command_string))
    print("=" * 72)
    print(output.rstrip() or "(empty output)")
    print("")

    return (ev, inputs, identity,
            "Interpret the output above against the triage findings; if cleanup "
            "follows, run snapshot-guard first.")


# ---------------------------------------------------------------------------
# snapshot-guard (class C)
# ---------------------------------------------------------------------------
def cmd_snapshot_guard(args):
    ev = Evidence("ECS CLOUD ASSISTANT PRE-DIAGNOSIS SNAPSHOT")
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    ack = snapshot_ack(args.region_id, args.disk_id)
    inputs = {
        "region-id": args.region_id,
        "disk-id": args.disk_id,
        "consent": "given" if args.confirm else "NOT GIVEN",
    }

    if not args.confirm:
        for line in [
            "WHAT WILL HAPPEN  : one snapshot of disk {0} in region {1}".format(
                args.disk_id, args.region_id),
            "WHY               : snapshot-first is the condition for every cleanup, "
            "repair or expand step the customer might take after a diagnosis",
            "AFFECTS           : the disk is read at the moment of capture; no "
            "existing data changes",
            "REVERSIBLE        : the snapshot can be deleted later; deleting it is "
            "the customer's decision (see the retention warning below)",
            "COST              : snapshots are billed by stored capacity and "
            "retention time - {0}".format(DOC_LINKS["snapshot_billing"]),
            "SCOPE OF CONSENT  : the token below authorises exactly this "
            "region/disk pair once",
        ]:
            ev.manual(line)
        ev.finding("Nothing has been created yet; this is the pre-execution "
                   "disclosure.")
        return (ev, inputs, identity,
                "Read the disclosure to the customer (the billing line is not "
                "optional), get agreement, then re-run with --confirm {0}".format(ack))

    if args.confirm != ack:
        ev.fail()
        ev.finding("The supplied --confirm is not the consent token for this exact "
                   "disk. Consent is single-use.")
        return (ev, inputs, identity, "Re-run with --confirm {0}".format(ack))

    params = {"RegionId": args.region_id, "DiskId": args.disk_id}
    payload, error = call_soft(API_ECS_CREATE_SNAPSHOT, params, product=PRODUCT_ECS)
    if error is not None:
        ev.record(API_ECS_CREATE_SNAPSHOT, params, "WARN", str(error))
        ev.degrade()
        if _is_error_authorisation(error):
            _permission_hint(ev, API_ECS_CREATE_SNAPSHOT)
        return (ev, inputs, identity,
                "Resolve the failed call (permission or a busy disk); the customer "
                "can always create the snapshot in the console meanwhile: {0}".format(
                    DOC_LINKS["create_snapshot"]))
    ev.record(API_ECS_CREATE_SNAPSHOT, params, "OK",
              "SnapshotId={0}".format(payload.get("SnapshotId")))
    ev.finding("Snapshot requested for {0}. Capture runs in the background: the "
               "console shows progress; this skill has no verified snapshot-status "
               "query, so completion is read by the customer.".format(args.disk_id))
    ev.manual("Retention warning learned from case T-75912401: a snapshot released "
              "past its retention window cannot come back - {0}".format(
                  DOC_LINKS["delete_snapshot"]))
    return (ev, inputs, identity,
            "Continue with the diagnosis-driven manual steps, knowing the rollback "
            "point exists.")


# ---------------------------------------------------------------------------
# explain (knowledge answers from embedded case material)
# ---------------------------------------------------------------------------
def _topic_concepts():
    lines = [
        "Cloud Assistant is the built-in operations channel of ECS: the console, the "
        "OpenAPI and Workbench all dispatch commands through the agent that runs "
        "inside the instance.",
        "What depends on it (all seen fail together in the source cases):",
    ]
    for feature in DEPENDENCY_FEATURES:
        lines.append("  - {0}: {1} [case {2}]".format(feature["feature"],
                                                      feature["depends"],
                                                      feature["case"]))
    lines.append("Docs: {0} | {1}".format(DOC_LINKS["logon_credential_management"],
                                          DOC_LINKS["workbench_passwordless_principle"]))
    lines.append("So when any of them reports a Cloud Assistant error, the diagnosis "
                 "of THIS scenario is: agent missing, stopped, offline, outdated, or the "
                 "channel is fine and the guest itself is the problem - the triage "
                 "tree separates those.")
    return lines


def _topic_readiness():
    lines = ["Agent readiness, customer-side steps (this skill never runs service "
             "or install commands):"]
    lines.append("Linux:")
    lines.extend("  - {0}".format(step) for step in READINESS_STEPS_LINUX)
    lines.append("Windows:")
    lines.extend("  - {0}".format(step) for step in READINESS_STEPS_WINDOWS)
    lines.append("Verify afterwards with: triage (new successful history lines are "
                 "the proof).")
    return lines


def _topic_failure_classes():
    lines = ["The five failure classes this scenario separates, and the first move for "
             "each:"]
    for entry in FAILURE_CLASS_GUIDE:
        lines.append("  - {0}".format(entry["class"]))
        lines.append("      signal     : {0}".format(entry["signal"]))
        lines.append("      first move : {0}".format(entry["first-move"]))
    return lines


def _topic_dependency_features():
    lines = _topic_concepts()
    lines.append("Blocked password change, verified workaround order (case "
                 "T-1A68E453): snapshot first, then offline reset (reboots the "
                 "instance), upgrade the agent, and only afterwards use the online "
                 "reset again.")
    lines.append("Console paths for creating and running commands by hand: {0} | "
                 "{1}".format(DOC_LINKS["create_command"],
                              DOC_LINKS["run_existing_command"]))
    return lines


def _topic_forensics():
    return [
        "Suspected abuse (leaked key running commands): the evidence THIS skill can "
        "produce is the execution history - run the invocations mode per region.",
        "Then, in order, all manual: disable the leaked access key in the RAM "
        "console, snapshot affected disks (snapshot-guard, consented), remove "
        "persistence with a security responder, restrict the new key (network "
        "conditions, least privilege).",
        "Process kills, file deletion and cron cleanup are never executed by this "
        "skill (case T-2A028B99: a security responder did them under VNC).",
        "No official AK-leak runbook URL was verified for this scenario; the console "
        "paths above are the guidance (see SKILL.md 'Known gaps').",
        "Archive future command output: {0}".format(
            DOC_LINKS["assistant_command_autosave"]),
    ]


def _topic_degraded():
    return [
        "When the channel is down or the customer declines instance operations, the "
        "report degrades to a reading list the CUSTOMER runs and pastes back:",
        "  Linux: df -h ; df -i ; findmnt ; systemctl status aliyun.service ; and "
        "the agent log under the agent's install directory around the failure time.",
        "  Windows: Get-Volume ; Get-PSDrive ; services.msc status of 'Aliyun Assist "
        "Service' ; the agent log files similarly.",
        "Paste the raw output, do not summarize it; the readings feed the same "
        "classification as a successful guest-probe would.",
        "State which evidence is missing and why (agent down / permission denied / "
        "customer declined) inside the DEGRADED banner.",
    ]


def _topic_expand_handoff():
    return [
        "Expansion tasks dispatched through Cloud Assistant: this skill answers ONLY "
        "why the task failed (load, missing tool, resolver, OS not covered by the "
        "auto path).",
        "The growth itself goes to the disk-expand area, snapshot first: {0} | "
        "Windows {1} | Linux data-disk offline path {2}".format(
            DOC_LINKS["expand_partition_linux"], DOC_LINKS["resize_windows_disks"],
            DOC_LINKS["offline_extend_linux_data_disk"]),
        "The console one-click expansion entry was in a limited preview in the "
        "source case (T-79753A0F): where there is no entry, the manual command path "
        "is the documented alternative - never invent a missing console button.",
    ]


TOPIC_BLOCKS = {
    "concepts": _topic_concepts,
    "readiness": _topic_readiness,
    "failure-classes": _topic_failure_classes,
    "dependency-features": _topic_dependency_features,
    "forensics": _topic_forensics,
    "degraded": _topic_degraded,
    "expand-handoff": _topic_expand_handoff,
}


def cmd_explain(args):
    ev = Evidence("ECS CLOUD ASSISTANT GUIDANCE :: {0}".format(args.topic))
    ev.show_handoff = False
    identity, _ = _resolve_identity()
    inputs = {"topic": args.topic}
    for line in TOPIC_BLOCKS[args.topic]():
        ev.finding(line)
    ev.note("These are guidance lines from the embedded case knowledge of this scenario; "
            "where an account-specific fact is needed, run triage instead.")
    return (ev, inputs, identity,
            "Apply the steps as guidance to the customer; run triage for anything "
            "instance-specific.")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def _valid_region(value):
    cleaned = value.strip()
    if not cleaned or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-"
                          for ch in cleaned):
        raise argparse.ArgumentTypeError(
            "region must look like cn-hangzhou, not {0!r}".format(value))
    return cleaned


def _valid_resource_id(value):
    cleaned = value.strip()
    if not cleaned or any(ch not in "abcdefghijklmnopqrstuvwxyz0123456789-"
                          for ch in cleaned):
        raise argparse.ArgumentTypeError(
            "resource id must be alphanumeric with dashes, not {0!r}".format(value))
    return cleaned


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cloud_assistant_diagnosis.py",
        description="Diagnose ECS Cloud Assistant command failures and agent "
                    "abnormalities: class A queries run automatically; class B "
                    "guest probes and the class C snapshot are consent-gated.",
    )
    sub = parser.add_subparsers(dest="mode")

    env = sub.add_parser("check-env",
                         help="verify credentials and stamp the account tail")
    env.set_defaults(func=None)

    triage = sub.add_parser("triage", help="full attribution tree for one instance")
    triage.add_argument("--region-id", type=_valid_region, required=True)
    triage.add_argument("--instance-id", type=_valid_resource_id)
    triage.add_argument("--error-text", default=None,
                        help="the console/customer wording, quoted verbatim")
    triage.add_argument("--category", choices=ALL_CATEGORIES, default=None,
                        help="force a class when the wording is already known")
    triage.add_argument("--hours", type=int, default=None,
                        help="restrict history to the last N hours")
    triage.add_argument("--invocation-id", type=_valid_resource_id, default=None)
    triage.set_defaults(func=cmd_triage)

    inv = sub.add_parser("invocations",
                         help="execution-history evidence list (forensics)")
    inv.add_argument("--region-id", type=_valid_region, required=True)
    inv.add_argument("--instance-id", type=_valid_resource_id)
    inv.add_argument("--hours", type=int, default=None)
    inv.add_argument("--include-output", action="store_true",
                     help="fetch and decode stored command output into the list")
    inv.set_defaults(func=cmd_invocations)

    probe = sub.add_parser("guest-probe",
                           help="one whitelisted side-effect-free guest command "
                                "(consent-gated class B)")
    probe.add_argument("--region-id", type=_valid_region, required=True)
    probe.add_argument("--instance-id", type=_valid_resource_id, required=True)
    probe.add_argument("--command", choices=sorted(GUEST_COMMANDS), required=True)
    probe.add_argument("--target", default=None,
                       help="path or drive for target-taking probes")
    probe.add_argument("--confirm", default=None,
                       help="the exact consent token from the disclosure run")
    probe.set_defaults(func=cmd_guest_probe)

    snap = sub.add_parser("snapshot-guard",
                          help="pre-cleanup snapshot (consent-gated class C)")
    snap.add_argument("--region-id", type=_valid_region, required=True)
    snap.add_argument("--disk-id", type=_valid_resource_id, required=True)
    snap.add_argument("--confirm", default=None,
                      help="the exact consent token from the disclosure run")
    snap.set_defaults(func=cmd_snapshot_guard)

    explain = sub.add_parser("explain", help="print a guidance block for a support "
                                             "question")
    explain.add_argument("--topic", choices=sorted(TOPIC_BLOCKS), required=True)
    explain.set_defaults(func=cmd_explain)
    return parser


def _run_selftest():
    """Offline regression locks for the pure diagnostic cores: symptom
    classification and the two-level DescribeInvocations/DescribeInstances
    descents that build every report row. These decide which attribution the
    customer is shown, so their boolean/shape behaviour is pinned here with no
    cloud call. Every expected value was read off the live functions first.
    Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # classify: a representative pattern from several categories resolves to the
    # right bucket, and nothing is ever guessed (no match -> UNKNOWN).
    expect("classify: distinct symptoms map to their category",
           classify("the command execution has been timeout")[0] == "COMMAND_TIMEOUT"
           and classify("i did not run this command")[0] == "ACCESSKEY_ABUSE"
           and classify("expand partition failed growpart")[0] == "EXPAND_TASK_FAILED"
           and classify("cloud assistant agent is not online")[0] == "AGENT_NOT_READY")
    expect("classify: never guesses - unrelated and empty text -> UNKNOWN",
           classify("totally unrelated sentence") == (CATEGORY_UNKNOWN, [])
           and classify("") == (CATEGORY_UNKNOWN, []))
    expect("classify: forced category wins; forced UNKNOWN falls back to scanning",
           classify("anything", forced="GUEST_ENV_BROKEN")[0] == "GUEST_ENV_BROKEN"
           and classify("cloud assistant offline", forced=CATEGORY_UNKNOWN)[0] == "AGENT_NOT_READY")

    # _instances_of / _invocation_rows: correct two-level descent, no crash on
    # missing containers, and the per-instance record overlays the invocation row.
    expect("instances: descends Instances.Instance; empty payload -> []",
           _instances_of({"Instances": {"Instance": [{"InstanceId": "i-1"}]}}) == [{"InstanceId": "i-1"}]
           and _instances_of({}) == [])
    rows = _invocation_rows({"Invocations": {"Invocation": [{
        "InvokeId": "t1", "CommandName": "c", "InvocationStatus": "Running",
        "InvokeInstances": {"InvokeInstance": [
            {"InstanceId": "i-x", "InvocationStatus": "Success", "ExitCode": 0}]}}]}})
    expect("invocations: flattens to one merged row per instance",
           len(rows) == 1 and rows[0]["InvokeId"] == "t1" and rows[0]["InstanceId"] == "i-x")
    expect("invocations: per-instance status/exit code overlay the invocation summary",
           rows[0]["InvocationStatus"] == "Success" and rows[0]["ExitCode"] == 0)
    expect("invocations: empty payload -> []", _invocation_rows({}) == [])

    # OS / status / truncation helpers feeding the row rendering.
    expect("is_windows: OSType substring, linux and missing are False",
           _is_windows({"OSType": "windows"}) is True
           and _is_windows({"OSType": "linux"}) is False and _is_windows({}) is False)
    expect("row_status: invocation then invoke-record then Unknown",
           _row_status({"InvocationStatus": "Failed"}) == "Failed"
           and _row_status({}) == "Unknown")
    expect("truncate: adds ellipsis past limit, '-' for empty",
           _truncate("abc", 2) == "ab..." and _truncate(None) == "-")
    return rc


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.mode == "check-env":
        import sts_token
        return sts_token.main()
    if args.mode is None:
        parser.print_help()
        return 2
    ev, inputs, identity, next_action = args.func(args)
    print(ev.render(identity, inputs, next_action))
    return 1 if ev.status == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
