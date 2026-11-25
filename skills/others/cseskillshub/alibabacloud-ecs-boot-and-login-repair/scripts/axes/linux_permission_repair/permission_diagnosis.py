#!/usr/bin/env python3
"""Single entry point for alibabacloud-ecs-boot-and-login-repair.

The agent MUST drive this script; it must not assemble cloud CLI calls by itself.

Sub-commands
    identity       check the default credential chain and print the account tag
    preflight      control-plane health of the instance (three non-mutating reads)
    classify       map the customer's own words to a scenario or a handoff
    guest-plan     print the exact single in-guest command to propose for approval
    guest-run      send ONE whitelisted non-mutating command, after confirmation
    guest-result   read back the output of an execution that already ran
    snapshot       create the pre-repair snapshot, after confirmation
    guide          manual repair steps, baseline and documentation for a scenario

Every run ends with a ``STATUS: OK|DEGRADED|FAIL`` line and a
``NEXT_ACTION:`` line.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import base64
import binascii
import json
import re
import shlex
import sys
import time

from _cli import CliError, new_session_id, run_cli
from _constants import (
    API_WHITELIST,
    AUTH_DENIED_CODES,
    BASELINE_STATUS,
    CONFIRMATION_REQUIRED,
    DOCUMENT_LINKS,
    EVIDENCE_RULES,
    GUEST_COMMAND_MAX_ARGS,
    GUEST_COMMAND_MAX_CHARS,
    GUEST_EXECUTION_TIMEOUT_SECONDS,
    GUEST_REJECTED_TOKENS,
    GUEST_TOOL_FLAGS,
    GUEST_WRITING_TOOLS,
    HANDOFF_RULES,
    NON_WHITELIST_REFUSAL,
    OUT_OF_SCOPE_ACTIONS,
    PAGE_SIZE,
    PERMISSION_BASELINE,
    REFUSED_REQUEST_EXAMPLES,
    SCENARIOS,
    SCENARIO_KEYWORDS,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    TICKET_EVIDENCE_GAP,
)
from sts_token import identity_or_warning

_SAFE_PATH_RE = re.compile(r"^/[A-Za-z0-9._/\-]*$")
_SAFE_VALUE_RE = re.compile(r"^[A-Za-z0-9,_=.:/*\-]*$")


# --------------------------------------------------------------------------
# report helpers
# --------------------------------------------------------------------------
class Report(object):
    def __init__(self, session_id):
        self.session_id = session_id
        self.lines = []
        self.status = STATUS_OK
        self.next_action = "no further step"

    def h(self, title):
        self.lines.extend(["", "== %s ==" % title])

    def row(self, field, value, source):
        self.lines.append("  %-34s | %-42s | %s" % (field, str(value), source))

    def line(self, text=""):
        self.lines.append("  %s" % text)

    def note(self, text):
        self.lines.append("  [NOTE] %s" % text)

    def warn(self, text):
        self.status = STATUS_DEGRADED if self.status == STATUS_OK else self.status
        self.lines.append("  [WARN] %s" % text)

    def fail(self, text):
        self.status = STATUS_FAIL
        self.lines.append("  [FAIL] %s" % text)

    def finish(self):
        self.lines.extend(["", "STATUS: %s" % self.status,
                           "NEXT_ACTION: %s" % self.next_action, ""])
        print("\n".join(self.lines))


def _dig(node, *keys):
    """Walk the wrappers ECS returns and always hand back a list.

    ``{"Instances": {"Instance": [...]}}`` and the flatter single-object shapes are
    both accepted; a missing level yields an empty list, never a guess.
    """
    current = node
    for key in keys:
        if isinstance(current, list):
            break
        if not isinstance(current, dict):
            return []
        current = current.get(key)
    if current is None:
        return []
    if isinstance(current, list):
        return current
    if isinstance(current, dict):
        return [current]
    return []


def _named(node):
    """Read a status/health field that may be {Code,Name} or a plain string."""
    if isinstance(node, dict):
        return node.get("Name") or node.get("Code") or "not returned"
    return node or "not returned"


def _describe_error(exc):
    if isinstance(exc, CliError):
        return exc.code, exc.message
    return type(exc).__name__, str(exc)


# --------------------------------------------------------------------------
# in-guest whitelist validation
# --------------------------------------------------------------------------
def validate_guest_command(command):
    """Return ``(argv, reason)``; ``argv`` is None when the command is refused.

    Only one non-mutating inspection tool, no shell syntax, absolute paths only.
    """
    if not command or not command.strip():
        return None, "empty command"
    if len(command) > GUEST_COMMAND_MAX_CHARS:
        return None, "command longer than %s characters" % GUEST_COMMAND_MAX_CHARS
    for token in GUEST_REJECTED_TOKENS:
        if token in command:
            return None, ("shell syntax or wildcard %r is not allowed; the whitelist "
                          "accepts one bare tool plus absolute paths" % token)

    try:
        argv = shlex.split(command)
    except ValueError as exc:
        return None, "command is not parsable: %s" % exc

    if not argv:
        return None, "empty command"
    tool = argv[0]
    if tool not in GUEST_TOOL_FLAGS:
        if tool in GUEST_WRITING_TOOLS:
            return None, ("%r is a changing or content-reading tool and is not on "
                          "the whitelist; give it to the customer to run" % tool)
        return None, ("%r is not one of %s" % (tool, sorted(GUEST_TOOL_FLAGS)))
    if "/" in tool:
        return None, "call the tool by name, not by absolute path"

    spec = GUEST_TOOL_FLAGS[tool]
    allowed = set(spec["allowed_flags"])
    value_flags = {"-o", "-p", "-t", "-M", "-S", "--options", "--target",
                   "--types", "--source"}
    paths = []
    values = []
    expects_value = False
    for arg in argv[1:]:
        if expects_value:
            if not _SAFE_VALUE_RE.match(arg):
                return None, "value %r is not accepted" % arg
            values.append(arg)
            expects_value = False
            continue
        if arg.startswith("-"):
            if arg not in allowed:
                return None, ("flag %r is not allowed for %s (allowed: %s)"
                              % (arg, tool, ", ".join(sorted(a for a in allowed if a))
                                 or "none"))
            expects_value = arg in value_flags
            continue
        if not _SAFE_PATH_RE.match(arg):
            return None, ("%r is not an absolute path made of plain characters" % arg)
        paths.append(arg)
    if expects_value:
        return None, "a flag is missing its value"
    if len(paths) + len(values) > GUEST_COMMAND_MAX_ARGS:
        return None, "too many arguments for one diagnostic command"
    if len(paths) > spec["max_paths"]:
        return None, "%s accepts at most %s paths per request" % (tool, spec["max_paths"])
    if tool != "findmnt" and not paths:
        return None, "%s needs at least one absolute path" % tool
    return argv, None


def build_guest_argv(argv):
    """Rebuild the validated argv into a single shell line for the guest."""
    return " ".join(argv)


# --------------------------------------------------------------------------
# sub-commands
# --------------------------------------------------------------------------
def cmd_identity(args):
    rep = Report(args.session_id)
    rep.h("credential identity (sts:GetCallerIdentity)")
    identity, warning = identity_or_warning(session_id=args.session_id,
                                            writer=lambda msg: rep.warn(msg.strip()))
    if identity:
        rep.row("account", identity["identity_tag"], "GetCallerIdentity")
        rep.row("principal", identity["Arn"] or "not returned", "GetCallerIdentity")
        rep.next_action = ("run preflight, then classify the customer's wording; "
                           "state the account used for every cloud read")
    else:
        rep.fail("identity could not be read")
        rep.line(warning or "")
        rep.next_action = ("ask the customer's administrator to run `aliyun sts get-caller-identity` "
                           "with the default credential chain; never request an "
                           "AccessKey pair")
    rep.finish()
    return 0 if identity else 2


def cmd_preflight(args):
    rep = Report(args.session_id)
    session = args.session_id
    rep.h("control-plane pre-flight")
    rep.line("parameters used: RegionId=%s, InstanceId=%s, PageSize=%s"
             % (args.region_id, args.instance_id, PAGE_SIZE))
    rep.line("evidence rules: " + EVIDENCE_RULES[0])

    identity, _ = identity_or_warning(session_id=session, writer=lambda _m: None)
    if identity:
        rep.row("caller account", identity["identity_tag"], "GetCallerIdentity")

    payload, error = None, None
    try:
        payload = run_cli("DescribeInstances", {
            "RegionId": args.region_id,
            "InstanceIds": json.dumps([args.instance_id]),
            "PageSize": PAGE_SIZE,
        }, session_id=session)
    except CliError as exc:
        error = exc

    instance = None
    if error is not None:
        code, message = _describe_error(error)
        rep.fail("DescribeInstances failed (%s): %s" % (code, message))
        if code in AUTH_DENIED_CODES:
            rep.line("missing action: ecs:DescribeInstances - see references/ram-policies.md")
        rep.next_action = ("resolve the API error above, then re-run preflight; do "
                           "not continue to in-guest checks")
        rep.finish()
        return 2

    instances = _dig(payload, "Instances", "Instance")
    for item in instances:
        if item.get("InstanceId") == args.instance_id:
            instance = item
            break
    if instance is None and instances:
        instance = instances[0]

    if instance is None:
        rep.row("instance found", "no", "DescribeInstances")
        rep.note("the instance is not in this region, or the id is wrong, or the "
                 "account above does not own it - nothing further can be read")
        rep.next_action = ("confirm RegionId and InstanceId with the customer (or "
                           "search by private IP with AdditionalAttributes), then "
                           "re-run; do not switch to another region silently")
        rep.finish()
        return 2

    status = instance.get("Status") or "unknown"
    rep.row("instance status", status, "DescribeInstances")
    rep.row("zone", instance.get("ZoneId") or "not returned", "DescribeInstances")
    rep.row("image", "%s / %s" % (instance.get("ImageId") or "-",
                                 instance.get("OSName") or instance.get("OSType") or "-"),
            "DescribeInstances")
    rep.row("network", instance.get("InstanceNetworkType") or "not returned",
            "DescribeInstances")
    groups = ", ".join(str(item) for item in
                       _dig(instance.get("SecurityGroupIds"), "SecurityGroupId")) or "none"
    rep.row("security groups bound", groups, "DescribeInstances")
    rep.row("instance charge / expired", "%s / %s" % (instance.get("InstanceChargeType")
                                                       or "-", instance.get("ExpiredTime")
                                                       or "-"), "DescribeInstances")
    rep.note("security group RULES are not read by this skill; port 22 reachability "
             "is a manual console check (DescribeSecurityGroupAttribute is out of scope)")

    full, ferr = None, None
    try:
        full = run_cli("DescribeInstancesFullStatus", {
            "RegionId": args.region_id,
            "InstanceId.1": args.instance_id,
        }, session_id=session)
    except CliError as exc:
        ferr = exc
    if ferr is not None:
        code, message = _describe_error(ferr)
        rep.warn("DescribeInstancesFullStatus failed (%s): %s" % (code, message))
    else:
        entries = _dig(full, "FullStatusInstances", "FullStatusInstance")
        events = []
        health = "not returned"
        for entry in entries:
            read = _named(entry.get("HealthStatus"))
            if read != "not returned":
                health = read
            events.extend(_dig(entry.get("Events"), "Event"))
        rep.row("health status", health, "DescribeInstancesFullStatus")
        rep.row("scheduled / published events", len(events), "DescribeInstancesFullStatus")
        for event in events[:5]:
            rep.line("event code=%s reason=%s not-before=%s"
                     % (event.get("Code") or event.get("EventType") or "-",
                        event.get("Reason") or "-", event.get("NotBefore") or "-"))
        if events or health not in ("Ok", "NotApplicable", "Normal", "not returned"):
            rep.note("an expiry, a scheduled stop or an unhealthy event can look like "
                     "a logon or sudo failure - settle this before any guest check")

    ca, cerr = None, None
    try:
        ca = run_cli("DescribeCloudAssistantStatus", {
            "RegionId": args.region_id,
            "InstanceId.1": args.instance_id,
        }, session_id=session)
    except CliError as exc:
        cerr = exc
    assistant_ready = False
    if cerr is not None:
        code, message = _describe_error(cerr)
        rep.warn("DescribeCloudAssistantStatus failed (%s): %s" % (code, message))
        if code in AUTH_DENIED_CODES:
            rep.line("missing action: ecs:DescribeCloudAssistantStatus - see "
                     "references/ram-policies.md")
    else:
        rows = []
        for wrapper, item in (("InstanceCloudAssistantStatusSet",
                               "InstanceCloudAssistantStatus"),
                              ("CloudAssistantStatuses", "CloudAssistantStatus")):
            rows = _dig(ca, wrapper, item)
            if rows:
                break
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        raw = str(row.get("CloudAssistantStatus") or row.get("Status") or "unknown").lower()
        assistant_ready = raw in ("true", "1", "ready", "running")
        rep.row("cloud assistant agent", raw, "DescribeCloudAssistantStatus")
        rep.row("last agent invocation", row.get("LastInvokedTime") or "not returned",
                "DescribeCloudAssistantStatus")

    rep.h("reading")
    if status not in ("Running",):
        rep.warn("instance is %s, so guest diagnosis is impossible right now" % status)
    if not assistant_ready:
        rep.line("the in-guest channel is unavailable: the agent is not ready, or the "
                 "read failed")
        rep.line("fall back to: the customer runs the whitelisted command themselves "
                 "and pastes the output")

    rep.h("evidence rules")
    for rule in EVIDENCE_RULES:
        rep.line("- " + rule)
    rep.line("- " + TICKET_EVIDENCE_GAP)

    if status != "Running":
        rep.next_action = ("hand off to alibabacloud-ecs-high-frequency-issues for "
                           "the %s state; permission checks resume only once Running"
                           % status)
    elif not assistant_ready:
        rep.next_action = ("run guest-plan for the matched scenario and ask the "
                           "customer to execute those commands and paste the output")
    else:
        rep.next_action = ("run guest-plan, read the command to the customer, obtain "
                           "confirmation, then guest-run --confirm (one command each)")
    rep.finish()
    return 0


def cmd_classify(args):
    rep = Report(args.session_id)
    text = " ".join(args.text).lower()
    rep.h("symptom routing (customer wording)")
    rep.line("input recorded verbatim from the customer: %s" % " ".join(args.text))

    matched_handoff = []
    for kind, rule in sorted(HANDOFF_RULES.items()):
        hits = [k for k in rule["keywords"] if k in text]
        if hits:
            matched_handoff.append((kind, rule, hits))
    matched_scenarios = []
    for code in sorted(SCENARIO_KEYWORDS):
        hits = [k for k in SCENARIO_KEYWORDS[code] if k in text]
        if hits:
            matched_scenarios.append((code, hits))

    if matched_handoff:
        rep.line("this wording leaves the permission area:")
        for kind, rule, hits in matched_handoff:
            rep.row(rule["target"], "keywords: " + ", ".join(hits), "handoff rule %s" % kind)
            rep.note(rule["note"])
        rep.warn("do not diagnose an out-of-area symptom here; hand it off")

    if matched_scenarios:
        rep.line("permission-area scenarios to work, most explicit first:")
        for code, hits in sorted(matched_scenarios, key=lambda item: -len(item[1])):
            rep.row(code, SCENARIOS[code]["title"], "matched: " + ", ".join(hits))
    elif not matched_handoff:
        rep.warn("no keyword matched; ask the customer for the exact error line and "
                 "which account runs which command before routing")
        rep.line("do not classify from assumed wording: record the customer's own "
                 "error text and route on it")

    if "ram" in text or "initial user" in text or "policy" in text:
        rep.line("check the cloud-side interpretation first: a RAM policy can prohibit "
                 "root as the initial user of a Linux instance, which is a control, "
                 "not a fault")
    if "avoid" in text and "root" in text:
        rep.line("hardening guidance may also explain a refused root logon")

    rep.h("known gaps")
    rep.line("- " + TICKET_EVIDENCE_GAP)
    rep.next_action = ("run preflight for the instance, then guest-plan for the "
                       "highest-ranked scenario code")
    rep.finish()
    return 0


def cmd_guest_plan(args):
    rep = Report(args.session_id)
    rep.h("in-guest inspection plan (one command per approval)")
    if args.list:
        for tool in sorted(GUEST_TOOL_FLAGS):
            spec = GUEST_TOOL_FLAGS[tool]
            rep.row(tool, spec["purpose"], "flags: " + (", ".join(
                f for f in spec["allowed_flags"] if f) or "none"))
        rep.line("")
        rep.line("requests that are refused on purpose:")
        for sample in REFUSED_REQUEST_EXAMPLES:
            rep.line("  - " + sample)
        rep.next_action = NON_WHITELIST_REFUSAL
        rep.finish()
        return 0

    paths = args.path or []
    commands = []
    if paths:
        for path in paths:
            commands.extend(["stat %s" % path, "ls -l %s" % path])
        rep.line("customer supplied path, checked for mode and owner only")
    else:
        scenario = (args.scenario or "").upper()
        if scenario not in SCENARIOS:
            rep.fail("give --scenario (S1|S2|S3|S4) or at least one --path")
            rep.next_action = "re-run guest-plan with a scenario code or a path"
            rep.finish()
            return 2
        data = SCENARIOS[scenario]
        rep.line("scenario %s: %s" % (scenario, data["title"]))
        commands = list(data.get("plan_commands") or [])
        if not commands:
            rep.line(data.get("plan_note") or "no fixed path for this scenario")

    for command in commands:
        argv, reason = validate_guest_command(command)
        if reason:
            rep.warn("refused %r: %s" % (command, reason))
            continue
        rep.row("propose", build_guest_argv(argv), "changes nothing in the guest")
    rep.line("")
    rep.next_action = CONFIRMATION_REQUIRED
    rep.finish()
    return 0


def cmd_guest_run(args):
    rep = Report(args.session_id)
    session = args.session_id
    command = " ".join(args.command) if isinstance(args.command, list) else args.command
    rep.h("send ONE whitelisted non-mutating command")
    rep.line("target: RegionId=%s InstanceId=%s" % (args.region_id, args.instance_id))
    rep.line("requested command: %s" % command)

    argv, reason = validate_guest_command(command)
    if reason:
        rep.fail("not sent: %s" % reason)
        rep.line(NON_WHITELIST_REFUSAL)
        rep.row("hand to customer", command, "manual execution, then paste the output")
        rep.next_action = ("offer the command for the customer to run themselves, or "
                           "run guest-plan --list to see what is allowed")
        rep.finish()
        return 2

    line = build_guest_argv(argv)
    if not args.confirm:
        rep.warn("execution gate closed")
        rep.line("will run exactly: %s" % line)
        rep.line("scope: one instance, reads metadata only, changes no file, no "
                 "service and no setting; reversible by definition because nothing "
                 "is written")
        rep.line("the approval is valid for this command only")
        rep.next_action = CONFIRMATION_REQUIRED + " (re-run with --confirm)"
        rep.finish()
        return 1

    try:
        payload = run_cli("RunCommand", {
            "RegionId": args.region_id,
            "Type": "RunShellScript",
            "CommandContent": line,
            "ContentEncoding": "PlainText",
            "InstanceId.1": args.instance_id,
            "Name": "%s-guest-inspect" % SKILL_NAME,
            "Description": "single whitelisted metadata read, no change",
            "Timeout": GUEST_EXECUTION_TIMEOUT_SECONDS,
        }, session_id=session, timeout=60)
    except CliError as exc:
        code, message = _describe_error(exc)
        rep.fail("RunCommand failed (%s): %s" % (code, message))
        if code in AUTH_DENIED_CODES:
            rep.line("missing action: RunCommand plus DescribeInvocations, both under "
                     "the ecs RAM code, for "
                     "the output - attach the minimal policy from "
                     "references/ram-policies.md")
        rep.line("fall back to manual execution by the customer and read the pasted "
                 "output")
        rep.next_action = ("report STATUS: DEGRADED with the refused step named, then "
                           "ask the customer to run: %s" % line)
        rep.finish()
        return 2

    invoke_id = payload.get("InvokeId") or ""
    rep.row("InvokeId", invoke_id or "not returned", "RunCommand")
    rep.row("command sent", line, "approved by the customer for this request only")

    output = None
    exec_status = "not polled"
    if not invoke_id:
        rep.warn("RunCommand returned no InvokeId, so the output cannot be read back")
    elif not args.no_fetch:
        for _ in range(6):
            time.sleep(5)
            try:
                read = run_cli("DescribeInvocations", {
                    "RegionId": args.region_id,
                    "InvokeId": invoke_id,
                    "InstanceId": args.instance_id,
                    "IncludeOutput": True,
                    "ContentEncoding": "PlainText",
                }, session_id=session)
            except CliError as exc:
                code, message = _describe_error(exc)
                rep.warn("DescribeInvocations failed (%s): %s" % (code, message))
                exec_status = "read failed"
                break
            invocations = [item for item in _dig(read, "Invocations", "Invocation")
                           if isinstance(item, dict)]
            if not invocations:
                continue
            per_instance = [item for item in
                            _dig(invocations[0].get("InvokeInstances"), "InvokeInstance")
                            if isinstance(item, dict)]
            entry = per_instance[0] if per_instance else invocations[0]
            exec_status = (entry.get("InvocationStatus") or
                           entry.get("InvokeStatus") or "unknown")
            output = entry.get("Output")
            if output:
                break

    if invoke_id and not args.no_fetch:
        rep.row("execution status", exec_status, "DescribeInvocations")

    if output:
        rep.row("raw guest output", _decode_output(output)[:1500], "approved command %s" % line)
        rep.note("read the values as they are; compare against "
                 "references/linux-permission-repair__perm-baseline.md and quote the baseline status to the "
                 "customer")
        rep.next_action = ("interpret the reading against the baseline, then run "
                           "guide --scenario for the repair steps (manual only)")
        rep.finish()
        return 0

    if args.no_fetch:
        rep.next_action = ("read the output later with: python3 "
                           "scripts/axes/linux_permission_repair/permission_diagnosis.py guest-result --region-id "
                           "%s --instance-id %s --invoke-id %s"
                           % (args.region_id, args.instance_id, invoke_id or "<invoke-id>"))
        rep.finish()
        return 0

    rep.warn("no output collected yet; DescribeInvocations only shows executions that "
             "already finished")
    rep.next_action = ("re-run: python3 scripts/axes/linux_permission_repair/permission_diagnosis.py guest-result "
                       "--region-id %s --instance-id %s --invoke-id %s"
                       % (args.region_id, args.instance_id, invoke_id or "<invoke-id>"))
    rep.finish()
    return 1


_B64ISH_RE = re.compile(r"^[A-Za-z0-9+/]+={0,2}$")


def _decode_output(value):
    """Return readable text; decode base64 only when the payload really is base64.

    The guest commands are sent and requested as plain text, so a value such as
    ``stat /usr/bin/sudo`` must be echoed unchanged.
    """
    text = str(value or "").strip()
    if not text or not _B64ISH_RE.match(text):
        return text
    try:
        decoded = base64.b64decode(text).decode("utf-8", "strict")
    except (binascii.Error, ValueError, UnicodeError):
        return text
    if not decoded.strip() or any(ord(ch) < 9 for ch in decoded):
        return text
    return decoded


def cmd_guest_result(args):
    rep = Report(args.session_id)
    rep.h("read back a finished execution")
    params = {"RegionId": args.region_id, "IncludeOutput": True,
              "ContentEncoding": "PlainText", "PageSize": PAGE_SIZE}
    if args.invoke_id:
        params["InvokeId"] = args.invoke_id
    if args.instance_id:
        params["InstanceId"] = args.instance_id
    try:
        payload = run_cli("DescribeInvocations", params, session_id=args.session_id)
    except CliError as exc:
        code, message = _describe_error(exc)
        rep.fail("DescribeInvocations failed (%s): %s" % (code, message))
        if code in AUTH_DENIED_CODES:
            rep.line("missing action: ecs:DescribeInvocations - see "
                     "references/ram-policies.md")
        rep.next_action = "grant the minimal policy, or fall back to manual output"
        rep.finish()
        return 2

    invocations = [item for item in _dig(payload, "Invocations", "Invocation")
                   if isinstance(item, dict)]
    if not invocations:
        rep.row("executions found", 0, "DescribeInvocations")
        rep.note("this API lists past executions only; live state needs a new "
                 "guest-run")
        rep.next_action = "run guest-plan and then guest-run --confirm"
        rep.finish()
        return 1

    for invocation in invocations[:5]:
        rep.row("invoke id", invocation.get("InvokeId") or "-", "DescribeInvocations")
        rep.row("command sent", _decode_output(invocation.get("CommandContent") or ""),
                "DescribeInvocations")
        rep.row("status", invocation.get("InvokeStatus") or "-", "DescribeInvocations")
        for entry in [item for item in
                      _dig(invocation.get("InvokeInstances"), "InvokeInstance")
                      if isinstance(item, dict)][:5]:
            rep.row("output %s" % (entry.get("InstanceId") or "-"),
                    _decode_output(entry.get("Output") or "none")[:800],
                    "DescribeInvocations")
    rep.next_action = ("compare the readings with references/linux-permission-repair__perm-baseline.md, then "
                       "guide --scenario for manual repair steps")
    rep.finish()
    return 0


def cmd_snapshot(args):
    rep = Report(args.session_id)
    rep.h("pre-repair snapshot (optional, one disk)")
    rep.row("disk", args.disk_id, "provided by the customer")
    rep.line("purpose: a rollback point BEFORE the customer applies a manual "
             "permission repair")
    if not args.confirm:
        rep.warn("execution gate closed")
        rep.next_action = CONFIRMATION_REQUIRED + " (re-run with --confirm)"
        rep.finish()
        return 1
    params = {"DiskId": args.disk_id}
    if args.snapshot_name:
        params["SnapshotName"] = args.snapshot_name
    try:
        payload = run_cli("CreateSnapshot", params, session_id=args.session_id,
                          timeout=60)
    except CliError as exc:
        code, message = _describe_error(exc)
        rep.fail("CreateSnapshot failed (%s): %s" % (code, message))
        if code in AUTH_DENIED_CODES:
            rep.line("missing action: CreateSnapshot under the ecs RAM code - "
                     "see references/ram-policies.md")
        rep.next_action = "create the snapshot in the console instead, then continue"
        rep.finish()
        return 2
    rep.row("snapshot id", payload.get("SnapshotId") or "not returned", "CreateSnapshot")
    rep.row("request id", payload.get("RequestId") or "not returned", "CreateSnapshot")
    rep.next_action = ("ask the customer to confirm, in the console, that the snapshot "
                       "is accomplished before changing any permission; this skill "
                       "does not poll snapshot progress")
    rep.finish()
    return 0


def cmd_guide(args):
    rep = Report(args.session_id)
    scenario = (args.scenario or "").upper()
    if scenario not in SCENARIOS:
        rep.fail("unknown scenario %r (use S1, S2, S3 or S4)" % args.scenario)
        rep.next_action = "run classify first"
        rep.finish()
        return 2

    data = SCENARIOS[scenario]
    rep.h("%s - %s" % (scenario, data["title"]))
    rep.line("This skill never applies a repair. Every step below is executed by the "
             "customer, ideally after a snapshot.")
    rep.line("")
    rep.line("evidence to collect first")
    for item in data["evidence_control_plane"]:
        rep.line("  - [cloud] " + item)
    for item in data["evidence_guest"]:
        rep.line("  - [guest, one approval each] " + item)
    rep.line("")
    rep.line("expected values (%s)" % BASELINE_STATUS)
    for path in sorted(PERMISSION_BASELINE):
        rep.row(path, PERMISSION_BASELINE[path]["expected"],
                PERMISSION_BASELINE[path]["why"])
    rep.line("")
    rep.line("manual steps")
    for index, step in enumerate(data["manual_steps"], start=1):
        rep.line("  %d) %s" % (index, step))
    rep.line("")
    rep.line("documentation (only links verified for this tier)")
    for label, url in DOCUMENT_LINKS:
        rep.line("  - %s: %s" % (label, url))
    rep.line("")
    rep.line("refused automatically (offer as manual commands instead)")
    for sample in REFUSED_REQUEST_EXAMPLES:
        if any(verb in sample.split()[0] for verb in
               ("chmod", "chown", "usermod", "passwd", "systemctl", "visudo", "cat",
                "grep", "sudo", "find", "rpm", "lsattr", "getfacl")):
            rep.line("  - " + sample)
    rep.line("")
    rep.line("- " + TICKET_EVIDENCE_GAP)
    rep.next_action = ("offer snapshot --confirm before the customer repairs, then "
                       "hand the repair commands over for manual execution")
    rep.finish()
    return 0


def cmd_boundary(args):
    rep = Report(args.session_id)
    rep.h("allowed API surface (nothing else may be called)")
    for action in sorted(API_WHITELIST):
        meta = API_WHITELIST[action]
        gate = "confirmation per request" if meta["mutating"] else "unattended"
        rep.row("%s:%s" % (meta["product"], action), gate, meta["version"])
    rep.h("boundary: actions this skill will not take")
    for action in sorted(OUT_OF_SCOPE_ACTIONS):
        rep.row(action, "refused", OUT_OF_SCOPE_ACTIONS[action])
    rep.line("")
    rep.line("Anything outside API_WHITELIST is refused before a request is built; "
             "repairs, credential changes and service restarts are handed to the "
             "customer.")
    rep.next_action = "report the boundary and, if asked, the console entry point"
    rep.finish()
    return 0


# --------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="permission_diagnosis.py",
        description="ECS Linux root/sudo permission diagnosis (evidence + manual "
                    "guidance; one approved non-mutating guest command at a time).")
    parser.add_argument("--session-id", default=None,
                        help="reuse a session id for the Observability User-Agent")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("identity", help="verify the default credential chain")
    p.set_defaults(func=cmd_identity)

    p = sub.add_parser("preflight", help="control-plane reads for one instance")
    p.add_argument("--region-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.set_defaults(func=cmd_preflight)

    p = sub.add_parser("classify", help="route the customer's own wording")
    p.add_argument("--text", nargs="+", required=True)
    p.set_defaults(func=cmd_classify)

    p = sub.add_parser("guest-plan", help="print commands to propose for approval")
    p.add_argument("--scenario", help="S1|S2|S3|S4")
    p.add_argument("--path", action="append", help="absolute path to inspect")
    p.add_argument("--list", action="store_true", help="show the whitelist")
    p.set_defaults(func=cmd_guest_plan)

    p = sub.add_parser("guest-run", help="send ONE whitelisted command")
    p.add_argument("--region-id", required=True)
    p.add_argument("--instance-id", required=True)
    p.add_argument("--command", nargs="+", required=True)
    p.add_argument("--confirm", action="store_true",
                   help="set only after the customer approved this exact command")
    p.add_argument("--no-fetch", action="store_true", help="do not read the output")
    p.set_defaults(func=cmd_guest_run)

    p = sub.add_parser("guest-result", help="read a finished execution")
    p.add_argument("--region-id", required=True)
    p.add_argument("--instance-id")
    p.add_argument("--invoke-id")
    p.set_defaults(func=cmd_guest_result)

    p = sub.add_parser("snapshot", help="pre-repair snapshot of one disk")
    p.add_argument("--disk-id", required=True)
    p.add_argument("--snapshot-name")
    p.add_argument("--confirm", action="store_true")
    p.set_defaults(func=cmd_snapshot)

    p = sub.add_parser("guide", help="manual steps for one scenario")
    p.add_argument("--scenario", required=True)
    p.set_defaults(func=cmd_guide)

    p = sub.add_parser("boundary", help="list refused actions")
    p.set_defaults(func=cmd_boundary)
    return parser


def _run_selftest():
    """Offline regression locks for validate_guest_command, the security gate
    that decides which single command may be dispatched into the guest. It is
    the only write-class boundary in this skill, so its allow-list and every
    rejection class are pinned here with no cloud call. Returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    def allowed(cmd):
        argv, reason = validate_guest_command(cmd)
        return argv is not None and reason is None

    def rejected(cmd, needle):
        argv, reason = validate_guest_command(cmd)
        return argv is None and needle in (reason or "")

    # allow-list: bare whitelisted tools with absolute paths, and the findmnt
    # zero-path exception.
    expect("allow: ls -l /etc/passwd and stat -L /etc", allowed("ls -l /etc/passwd")
           and allowed("stat -L /etc"))
    expect("allow: findmnt with a path, and findmnt with none (mount table)",
           allowed("findmnt /") and allowed("findmnt"))
    # shell syntax / wildcard token is refused before any parsing of intent
    expect("reject: shell chaining and glob tokens", rejected("ls ; rm -rf /", "not allowed")
           and rejected("ls *", "not allowed"))
    # content-reading / mutating tools are handed to the customer, never dispatched
    expect("reject: content-reading cat and mutating rm are off-whitelist",
           rejected("cat /etc/passwd", "content-reading tool")
           and rejected("rm -f /tmp/x", "content-reading tool"))
    # an absolute-path invocation or an unknown tool is not on the whitelist
    expect("reject: absolute-path tool and disallowed flag", rejected("/usr/bin/ls /etc", "is not one of")
           and rejected("ls -x /etc", "flag '-x' is not allowed"))
    # only absolute plain-character paths, no relative traversal
    expect("reject: relative path is not accepted",
           rejected("ls relative/path", "not an absolute path"))
    # per-tool path cap and command length cap and dangling value flag
    expect("reject: ls path count cap, over-length, value flag missing its value",
           rejected("ls -l /a /b /c /d /e", "at most 4 paths")
           and rejected("ls " + "a" * 600, "longer than 512 characters")
           and rejected("findmnt -t", "missing its value"))
    # empty command short-circuits
    expect("reject: empty command", rejected("", "empty command"))
    return rc


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        print("STATUS: FAIL")
        print("NEXT_ACTION: choose a sub-command; start with identity then preflight")
        return 2
    if not args.session_id:
        args.session_id = new_session_id()
    print("skill: %s" % SKILL_NAME)
    print("observability session id: %s" % args.session_id)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
