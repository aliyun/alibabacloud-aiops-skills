#!/usr/bin/env python3
"""Entry point for database-on-ECS connectivity, availability and performance
triage (skill: alibabacloud-ecs-app-deploy-and-site-build).

The agent runs only this script; it never assembles aliyun CLI calls by hand.
Every cloud fact in a report comes from the calls below, every judgement comes
from the tables in ``_constants.py`` or from output the customer pasted in,
and every run ends with a ``STATUS:`` / ``NEXT_ACTION:`` contract.

Permission model (see SKILL.md "Operation classes"):
  * queries run without a per-call confirmation;
  * a guest command is dispatched ONLY after the caller passes --confirm on
    top of a whitelist check that stays binding even without any confirmation
    for anything off the list;
  * a snapshot is created ONLY after --confirm-cost, with the billing and
    reversibility disclosure echoed first;
  * everything else is refused mechanically, confirmation included.
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
import sys
import time

import _constants as C
import sts_token
from _cli import CliError, call_cms, call_ecs, new_session_id, user_agent_for


# ---------------------------------------------------------------------------
# generic helpers
# ---------------------------------------------------------------------------
def _first(mapping, *keys, **kwargs):
    default = kwargs.get("default", "UNKNOWN")
    if not isinstance(mapping, dict):
        return default
    for key in keys:
        if key in mapping and mapping[key] not in (None, ""):
            return mapping[key]
    return default


def _dig(obj, *path):
    current = obj
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _first_list(obj, *alternatives):
    """Return the first list found under any of the given path alternatives."""
    for path in alternatives:
        found = _dig(obj, *path)
        if isinstance(found, list):
            return found
        if isinstance(found, dict):
            for key in sorted(found.keys()):
                if isinstance(found[key], list):
                    return found[key]
    return []


def _as_number(value, default=None):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def call_ecs_guarded(action, params, session_id, write=False):
    """Every ECS call goes through this gate: whitelist, then transport."""
    if action not in C.AUTO_ALLOWED_ACTIONS and action not in C.CONFIRM_GATED_ACTIONS:
        raise CliError("ActionRefused",
                       "{0} is outside this skill's whitelist".format(action))
    for refused_prefix in C.NEVER_ALLOWED_ACTION_PREFIXES:
        if action.startswith(refused_prefix):
            raise CliError("ActionRefused",
                           "{0} belongs to a refused family".format(action))
    return call_ecs(action, params, session_id, write=write)


class Run(object):
    """Accumulates findings, verdicts and gates for one invocation."""

    def __init__(self, session_id):
        self.session_id = session_id
        self.status = C.STATUS_OK
        self.next_action = C.NEXT_ACTION_NONE
        self.findings = []
        self.layers = []
        self.signals = []
        self.verdicts = []
        self.manual_steps = []
        self.handoffs = []
        self.gated_offers = []
        self.assumptions = []
        self.limits = []
        self.guest = {}
        self.metrics = []

    def _lower(self, new_status):
        order = {C.STATUS_OK: 0, C.STATUS_DEGRADED: 1, C.STATUS_FAILED: 2}
        if order[new_status] > order[self.status]:
            self.status = new_status

    def evidence(self, line):
        self.findings.append(line)

    def assume(self, line):
        self.assumptions.append(line)

    def limit(self, line):
        self.limits.append(line)

    def manual(self, line):
        self.manual_steps.append(line)

    def verdict(self, verdict_id, note):
        if verdict_id not in [v[0] for v in self.verdicts]:
            self.verdicts.append((verdict_id, note))

    def handoff(self, target, cause, evidence_line):
        phrase = C.HANDOFF_PHRASE_TEMPLATE.format(
            cause=cause, evidence=evidence_line, target=target)
        self.handoffs.append({"target": target, "phrase": phrase})

    def gate_offer(self, text):
        self.gated_offers.append(text)

    def layer(self, name, state, detail):
        self.layers.append({"name": name, "state": state, "detail": detail})

    def degrade(self, next_action, reason):
        self._lower(C.STATUS_DEGRADED)
        self.next_action = next_action
        self.limits.append(reason)

    def fail(self, next_action, reason):
        self._lower(C.STATUS_FAILED)
        self.next_action = next_action
        self.limits.append(reason)


# ---------------------------------------------------------------------------
# cloud queries
# ---------------------------------------------------------------------------
def fetch_instances(region, instance_id, public_ip, session_id):
    params = {"RegionId": region, "PageSize": 50}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    elif public_ip:
        params["PublicIpAddresses"] = public_ip
    body = call_ecs_guarded("DescribeInstances", params, session_id)
    return _first_list(body, ("Instances", "Instance")) or []


def fetch_full_status(region, instance_id, session_id):
    params = {"RegionId": region, "InstanceId.1": instance_id, "PageSize": 20}
    body = call_ecs_guarded("DescribeInstancesFullStatus", params, session_id)
    return _first_list(body,
                       ("InstanceFullStatusSet", "FullStatusInstance"),
                       ("InstanceFullStatusSet", "Item"),
                       ("InstanceFullStatusSet", "FullStatusInstanceType"))


def fetch_instance_type_detail(instance_type, session_id):
    params = {"InstanceTypes.1": instance_type}
    body = call_ecs_guarded("DescribeInstanceTypes", params, session_id)
    items = _first_list(body, ("InstanceTypes", "InstanceType"))
    return items[0] if items else {}


def fetch_assistant_status(region, instance_id, session_id):
    params = {"RegionId": region, "InstanceId.1": instance_id}
    body = call_ecs_guarded("DescribeCloudAssistantStatus", params, session_id)
    items = _first_list(body,
                        ("InstanceCloudAssistantStatusSet",
                         "InstanceCloudAssistantStatus"))
    return items[0] if items else {}


def fetch_recent_invocations(region, instance_id, session_id):
    """Cloud Assistant task history for this instance (read-only listing)."""
    params = {"RegionId": region, "InstanceId": instance_id, "PageSize": 10}
    body = call_ecs_guarded("DescribeInvocations", params, session_id)
    return _first_list(body, ("Invocation",), ("Invocations", "Invocation"))


def submit_guest_command(region, instance_id, command, os_type, session_id):
    script_type = "RunPowerShellScript" if str(os_type).lower() == "windows" \
        else "RunShellScript"
    params = {
        "RegionId": region,
        "Type": script_type,
        "CommandContent": command,
        "ContentEncoding": "PlainText",
        "InstanceId.1": instance_id,
        "Timeout": C.GUEST_COMMAND_TIMEOUT_SECONDS,
        "Name": "{0}-inspect".format(C.SKILL_NAME),
        "Description": "Non-mutating inspection issued by {0}".format(C.SKILL_NAME),
    }
    return call_ecs_guarded("RunCommand", params, session_id, write=True)


def poll_invocation(region, invoke_id, instance_id, session_id):
    """Bounded polling; returns (record, timed_out). record may be None."""
    params = {
        "RegionId": region,
        "InvokeId": invoke_id,
        "InstanceId": instance_id,
        "IncludeOutput": True,
    }
    for attempt in range(C.INVOCATION_POLL_MAX_ATTEMPTS):
        body = call_ecs_guarded("DescribeInvocations", params, session_id)
        invocations = _first_list(body, ("Invocation",), ("Invocations", "Invocation"))
        if invocations:
            instances = _first_list(invocations[0],
                                    ("InvokeInstances", "InvokeInstance"))
            record = instances[0] if instances else invocations[0]
            state = str(_first(record, "InvocationStatus", "InvokeStatus",
                               default="")).lower()
            if state in ("running", "pending", "scheduled", "invoking"):
                time.sleep(C.INVOCATION_POLL_INTERVAL_SECONDS)
                continue
            return record, False
        time.sleep(C.INVOCATION_POLL_INTERVAL_SECONDS)
    return None, True


def decode_output(raw):
    if not raw:
        return ""
    try:
        return base64.b64decode(raw, validate=True).decode("utf-8", "replace")
    except (binascii.Error, ValueError):
        return str(raw)


def fetch_metric(region, metric_key, instance_id, session_id):
    spec = C.CMS_METRICS.get(metric_key)
    if not spec:
        return None
    params = {
        "Namespace": C.CMS_NAMESPACE,
        "MetricName": spec["metric_name"],
        "Dimensions": json.dumps([{"instanceId": instance_id}]),
        "Period": C.CMS_PERIOD_SECONDS,
    }
    body = call_cms("DescribeMetricLast", params, session_id)
    points_raw = _dig(body, "Datapoints")
    if isinstance(points_raw, str) and points_raw.strip():
        try:
            points_raw = json.loads(points_raw)
        except ValueError:
            points_raw = []
    points = points_raw if isinstance(points_raw, list) else \
        _first_list(body, ("Datapoints", "Datapoint"))
    return {"key": metric_key, "spec": spec, "points": points or []}


# ---------------------------------------------------------------------------
# error-signature classification
# ---------------------------------------------------------------------------
def scan_error_text(text):
    matches = []
    lowered = (text or "").lower()
    if not lowered.strip():
        return matches
    for signature in C.ERROR_SIGNATURES:
        if re.search(signature["pattern"], lowered):
            matches.append(signature)
    return matches


# ---------------------------------------------------------------------------
# guest readings parsing (shared by explain paste and probe output)
# ---------------------------------------------------------------------------
def parse_guest_readings(text):
    readings = {"df_lines": [], "inode_lines": [], "listen": [],
                "deleted_open": [], "firewall_off": [], "firewall_drop": [],
                "oom": [],
                "full_percent_mounts": [], "inode_full_mounts": []}
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        lowered = stripped.lower()
        if re.match(r"^(?:filesystem|file system)\b", lowered):
            continue
        percent_match = re.findall(C.DF_USAGE_RE, stripped)
        if lowered.startswith("df") or ("mounted on" in lowered):
            continue
        if percent_match and ("/" in stripped or "disk" in lowered or
                              "volume" in lowered or "size" in lowered):
            try:
                values = [int(p) for p in percent_match]
            except ValueError:
                values = []
            if values:
                top = max(values)
                if "ifound" in lowered or "iuse" in lowered or \
                        "inodes" in lowered:
                    readings["inode_lines"].append(stripped)
                    if top >= C.CAPACITY_WARN_PCT:
                        readings["inode_full_mounts"].append(stripped)
                else:
                    readings["df_lines"].append(stripped)
                    if top >= C.CAPACITY_WARN_PCT:
                        readings["full_percent_mounts"].append(stripped)
        if re.search(C.LISTEN_LINE_RE, stripped, re.IGNORECASE):
            readings["listen"].append(stripped)
        if "+l1" in lowered or ("deleted" in lowered and "lsof" in lowered):
            readings["deleted_open"].append(stripped)
        if re.search(C.FIREWALL_OFF_RE, stripped, re.IGNORECASE):
            readings["firewall_off"].append(stripped)
        elif (re.search(C.FIREWALL_DROP_RE, stripped, re.IGNORECASE)
                and re.search(C.FIREWALL_PORT_RE, stripped, re.IGNORECASE)):
            readings["firewall_drop"].append(stripped)
        if re.search(r"killed process|oom-killer", lowered):
            readings["oom"].append(stripped)
    return readings


def listening_ports(readings):
    ports = set()
    for line in readings.get("listen", []):
        for match in re.finditer(r":(\d{2,5})\b", line):
            ports.add(match.group(1))
    return sorted(ports)


def _run_selftest():
    """Offline regression locks for the read-only safety gate and the guest
    output parsers. A weakened gate could dispatch a mutating command; a wrong
    parser mis-reports listeners/capacity. Both are pinned to real behaviour.
    No cloud call; returns 0 when all hold."""
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # safety gate: only an exact-approved listing is auto-dispatched
    expect("gate: approved 'df -h' allowed",
           check_command_gate("df -h")[0] is True)
    for bad, why in (("ss -tlnp", "human-only, not auto"),
                     ("df -h; rm -rf /", "shell metacharacter"),
                     ("sudo df -h", "privilege wrapper"),
                     ("rm -rf /tmp", "state-changing"),
                     ("", "empty")):
        expect("gate refuses %-18s (%s)" % (repr(bad), why),
               check_command_gate(bad)[0] is False)

    # guest-output parsers
    parsed = parse_guest_readings(
        'tcp LISTEN 0 128 0.0.0.0:3306 0.0.0.0:* users:(("mysqld",pid=901))\n'
        "/dev/vda1        98G   95G  3.0G  97% /\n"
        "Sep 1 00:00 kernel: Out of memory: Killed process 1234 (mysqld)\n")
    expect("parse: listener captured and port extracted",
           len(parsed["listen"]) == 1
           and listening_ports(parsed) == ["3306"])
    expect("parse: near-full disk flagged",
           len(parsed["df_lines"]) == 1
           and len(parsed["full_percent_mounts"]) == 1)
    expect("parse: OOM kill detected", len(parsed["oom"]) == 1)
    empty = parse_guest_readings("")
    expect("parse: empty input -> all buckets empty, no crash",
           all(len(v) == 0 for v in empty.values()))
    return rc


# ---------------------------------------------------------------------------
# guest command gate
# ---------------------------------------------------------------------------
def check_command_gate(command):
    """Decide whether one guest command may be dispatched automatically."""
    text = " ".join((command or "").split()).strip()
    if not text or len(text) > 200:
        return False, "No single whitelisted command (200 chars max) was supplied."
    if text.lower().startswith("sudo "):
        return False, ("Privilege wrappers are refused: a whitelist command that "
                       "needs sudo is not a state-free listing, it is a change "
                       "attempt in disguise.")
    for meta in C.SHELL_METACHARACTERS:
        if meta in text:
            return False, ("The input contains {0!r}. Anything with shell "
                           "composition is refused, so no mutating step can "
                           "ride along inside a listing command.".format(meta))
    argv = text.split()
    program = argv[0].lower()
    if program == "sudo" or program in C.NEVER_AUTO_GUEST_COMMANDS:
        return False, ("`{0}` changes filesystem, service, firewall, process or "
                       "package state. This skill documents it as a human step "
                       "and never executes it.".format(argv[0]))
    for human_only in C.HUMAN_ONLY_GUEST_COMMANDS:
        if program == human_only.lower().split(" ")[0] and \
                text.lower().startswith(human_only.lower()):
            return False, ("`{0}` is not on the batch whitelist for automated "
                           "execution in this tier. Run it yourself inside the "
                           "instance and paste the raw output back; the "
                           "diagnosis continues from there via explain.".format(
                               human_only))
    if text.lower() in [exact.lower() for exact in C.AUTO_GUEST_COMMAND_EXACT]:
        return True, "exact non-mutating command on the approved list"
    for prefix in C.AUTO_FSUTIL_QUERY_PREFIXES:
        if text.lower().startswith(prefix.lower() + " "):
            extra = argv[1:]
            if all(re.match(r"^(?:[A-Za-z]:|/?[A-Za-z0-9._-]*)$", token)
                   for token in extra):
                return True, "non-mutating fsutil query subcommand"
            return False, "fsutil arguments outside a drive or plain token are refused."
    allowed_options = C.AUTO_GUEST_COMMAND_FAMILIES.get(argv[0])
    if allowed_options is None:
        allowed_options = C.AUTO_GUEST_COMMAND_FAMILIES.get(program)
    if allowed_options is None:
        return False, ("`{0}` is outside the approved non-mutating command set "
                       "for this skill.".format(argv[0]))
    for token in argv[1:]:
        if token.startswith("-") or token.startswith("+"):
            name = token.split("=", 1)[0]
            if name.lower() not in [str(opt).lower() for opt in allowed_options]:
                return False, ("Option `{0}` is not on the approved list for "
                               "`{1}`.".format(token.split("=", 1)[0], argv[0]))
        else:
            if not (re.match(C.GUEST_PATH_RE, token) or
                    re.match(r"^[A-Za-z0-9._-]{1,120}$", token)):
                return False, ("Argument `{0}` is not an accepted plain path or "
                               "name token.".format(token))
    return True, "single non-mutating command from the approved set"


def gate_disclosure(command, instance_id, region):
    return ("Pre-execution disclosure: exactly ONE command will be dispatched "
            "through Cloud Assistant to instance {0} in region {1}. Command "
            "text: `{2}`. It only reads state and writes nothing; a failed "
            "dispatch costs nothing but time. Your acknowledgement covers "
            "this one command only - every further reading needs a fresh "
            "disclosure and confirmation. Re-run with --confirm after telling "
            "the customer exactly the above.".format(instance_id, region, command))


def snapshot_disclosure(disk_id):
    return ("Pre-write disclosure: a snapshot of disk {0} will be created. It "
            "bills by stored capacity and retention time (reference caliber "
            "from the ticket practice: about 0.016 yuan per 100 GB for one "
            "hour; official page: {1}). It alters no existing data, needs no "
            "instance stop, and can be deleted later by the customer - "
            "deletion itself always stays a human decision. Re-run with "
            "--confirm-cost after relaying this to the customer.".format(
                disk_id, C.DOC_LINKS["snapshot_billing"]))


# ---------------------------------------------------------------------------
# report rendering
# ---------------------------------------------------------------------------
def render(run, args):
    lines = ["=== DATABASE ON ECS DIAGNOSIS ==="]
    lines.append("session_id: {0}".format(run.session_id))
    lines.append("user_agent: {0}".format(user_agent_for(run.session_id)))
    lines.append("api_versions: ecs={0} cms={1} sts={2}".format(
        C.ECS_API_VERSION, C.CMS_API_VERSION, C.STS_API_VERSION))
    for attr in ("region_id", "instance_id", "public_ip", "db_type", "port",
                 "symptom"):
        value = getattr(args, attr, None)
        if value:
            lines.append("{0}: {1}".format(attr, value))

    lines.append("")
    lines.append("[Evidence]")
    lines.extend("  - {0}".format(f) for f in (run.findings or ["none collected"]))

    if run.layers:
        lines.append("")
        lines.append("[Layer walk]")
        for layer in run.layers:
            lines.append("  - {0}: {1} - {2}".format(
                layer["name"], layer["state"], layer["detail"]))

    lines.append("")
    lines.append("[Matched error signals]")
    if run.signals:
        for signal in run.signals:
            quote_kind = "tier-quotable" if signal["quotable"] else "ticket sample"
            lines.append("  - {0} ({1}, confidence {2})".format(
                signal["id"], quote_kind, signal["confidence"]))
            lines.append("      meaning: {0}".format(signal["meaning"]))
            lines.append("      next layer: {0}".format(signal["layer"]))
    else:
        lines.append("  - no known error signal string appeared in the input")

    lines.append("")
    lines.append("[Verdicts]")
    if run.verdicts:
        for verdict_id, note in run.verdicts:
            lines.append("  - {0}: {1}".format(verdict_id, note))
    else:
        lines.append("  - {0}: no layer produced a confirmed verdict yet".format(
            C.VERDICT_UNKNOWN))

    if run.metrics:
        lines.append("")
        lines.append("[Metric readings]")
        for entry in run.metrics:
            points = entry["points"]
            if not points:
                lines.append("  - {0}: no datapoints ({1})".format(
                    entry["key"],
                    "in-guest agent required" if entry["spec"]["agent_required"]
                    else "empty window"))
                continue
            lines.append("  - {0} ({1}):".format(
                entry["key"], entry["spec"]["metric_name"]))
            for point in points[:C.CMS_MAX_POINTS_SHOWN]:
                shown = dict((k, point[k]) for k in
                             ("Average", "Maximum", "Minimum", "timestamp")
                             if k in point)
                lines.append("      {0}".format(json.dumps(shown)))

    if run.manual_steps:
        lines.append("")
        lines.append("[Manual steps, for a human to execute]")
        for index, step in enumerate(run.manual_steps, start=1):
            lines.append("  {0}. {1}".format(index, step))

    if run.gated_offers:
        lines.append("")
        lines.append("[Pending gated actions (not executed)]")
        for offer in run.gated_offers:
            lines.append("  - {0}".format(offer))

    if run.handoffs:
        lines.append("")
        lines.append("[Outside this tier: hand off]")
        for handoff in run.handoffs:
            lines.append("  - {0}".format(handoff["phrase"]))

    lines.append("")
    lines.append("[Assumptions and auto-filled inputs]")
    lines.extend("  - {0}".format(a) for a in (run.assumptions or ["none"]))

    lines.append("")
    lines.append("[Confidence and limits]")
    lines.extend("  - {0}".format(l) for l in (run.limits or ["none recorded"]))

    lines.append("")
    lines.append("STATUS: {0}".format(run.status))
    lines.append("NEXT_ACTION: {0}".format(run.next_action))
    return "\n".join(lines)


def to_json(run, args):
    return {
        "session_id": run.session_id,
        "user_agent": user_agent_for(run.session_id),
        "api_versions": {"ecs": C.ECS_API_VERSION, "cms": C.CMS_API_VERSION,
                         "sts": C.STS_API_VERSION},
        "region": getattr(args, "region_id", None),
        "instance": getattr(args, "instance_id", None),
        "findings": run.findings,
        "layers": run.layers,
        "signals": [
            {key: signal[key] for key in
             ("id", "quotable", "confidence", "meaning", "layer")}
            for signal in run.signals
        ],
        "verdicts": [{"id": v[0], "note": v[1]} for v in run.verdicts],
        "metrics": [
            {"key": m["key"], "metric_name": m["spec"]["metric_name"],
             "points": m["points"][:C.CMS_MAX_POINTS_SHOWN]}
            for m in run.metrics
        ],
        "guest": run.guest,
        "manual_steps": run.manual_steps,
        "gated_offers": run.gated_offers,
        "handoffs": run.handoffs,
        "assumptions": run.assumptions,
        "limits": run.limits,
        "STATUS": run.status,
        "NEXT_ACTION": run.next_action,
    }


def emit(run, args):
    if getattr(args, "json", False):
        print(json.dumps(to_json(run, args), indent=2, ensure_ascii=False))
    else:
        print(render(run, args))
    if run.status == C.STATUS_OK:
        return 0
    return 2 if run.status == C.STATUS_FAILED else 1


# ---------------------------------------------------------------------------
# shared instance context for diagnose
# ---------------------------------------------------------------------------
def collect_instance_context(run, args):
    """Fetch instance facts; return the instance dict or None."""
    region = args.region_id
    try:
        instances = fetch_instances(region, args.instance_id, args.public_ip,
                                    run.session_id)
    except CliError as exc:
        if exc.is_auth_denied:
            run.fail(C.NEXT_ACTION_VERIFY_CREDENTIALS,
                     "DescribeInstances denied: {0}. Missing action: {1} "
                     "under the ecs code - see references/ram-policies.md for "
                     "the fragment.".format(exc, "DescribeInstances"))
        else:
            run.fail(C.NEXT_ACTION_RETRY_LATER,
                     "DescribeInstances failed: {0}".format(exc))
        return None
    if not instances:
        run.verdict(C.VERDICT_INSTANCE_NOT_FOUND,
                    "no instance came back for this region and identifier; "
                    "check the region spelling and the owning account")
        run.layer("instance state", "NOT FOUND",
                  "DescribeInstances returned 0 rows")
        run.degrade(C.NEXT_ACTION_ASK_REGION,
                    "Nothing was confirmed about the instance; the owning "
                    "account may differ - the identity preflight label above "
                    "names the account actually queried.")
        return None
    instance = instances[0]
    instance_id = str(_first(instance, "InstanceId"))
    args.instance_id = instance_id
    status = str(_first(instance, "Status"))
    run.evidence("instance {0} status={1} type={2} zone={3}".format(
        instance_id, status, str(_first(instance, "InstanceType")),
        _first(instance, "ZoneId")))
    sg_ids = _first_list(instance, ("SecurityGroupIds", "SecurityGroupId"))
    run.evidence("bound security groups: {0}".format(
        ", ".join(sg_ids) if sg_ids else "none listed"))
    public_ips = _first_list(instance, ("PublicIpAddress", "IpAddress"))
    eip = _first(_first(instance, "EipAddress", default={}) or {}, "IpAddress")
    run.evidence("public addresses: {0}".format(
        ", ".join(public_ips) if public_ips else
        (str(eip) if eip and eip != "UNKNOWN" else "none")))
    os_type = str(_first(instance, "OSType", "OSName")).lower()
    run.evidence("guest OS family: {0}".format("windows" if "win" in os_type
                                               else os_type))
    run.guest["os_family"] = "windows" if "win" in os_type else "linux"

    if status != "Running":
        run.verdict(C.VERDICT_INSTANCE_STOPPED,
                    "instance is {0}, so no guest service can accept "
                    "connections until a human starts it".format(status))
        run.layer("instance state", "STOPPED", "Status={0}".format(status))

    try:
        full_statuses = fetch_full_status(region, instance_id, run.session_id)
    except CliError as exc:
        run.limit("DescribeInstancesFullStatus failed: {0}; expiry and "
                  "scheduled-event checks are unavailable.".format(exc))
        full_statuses = []
    retirement = []
    for record in full_statuses:
        scheduled = _first_list(record,
                                ("ScheduledSystemEventSet",
                                 "ScheduledSystemEventType"))
        for event in scheduled:
            event_name = str(_first(
                _first(event, "EventType", default={}) or {}, "Name", "Code"))
            run.evidence("scheduled event: {0} (reason {1}) not before {2}".format(
                event_name, _first(event, "Reason"), _first(event, "NotBefore")))
            retirement.append(event_name)
        run.evidence("instance health status: {0}".format(
            _first(_first(record, "HealthStatus", default={}) or {}, "Code")))
    if retirement:
        run.verdict(C.VERDICT_EXPIRY_PENDING,
                    "pending scheduled event(s) {0}: an unreachable database "
                    "can be the instance being retired, not a software "
                    "fault".format(", ".join(sorted(set(retirement)))))
        run.manual(C.COMMERCIAL_PHRASE)
        run.limit("an event name does not separate a release for expiry from a "
                  "maintenance reboot; the console event list is authoritative "
                  "and renewal or release stays a human console action")

    # Cloud Assistant reachability and task history are plain Describe reads;
    # diagnose reports them so the guest layer starts from facts, not only
    # from the (separately consent-gated) probe dispatch path.
    try:
        assistant = fetch_assistant_status(region, instance_id, run.session_id)
    except CliError as exc:
        run.limit("DescribeCloudAssistantStatus failed: {0}; the agent "
                  "reachability reading is unavailable.".format(exc))
        assistant = {}
    if assistant:
        ready = str(_first(assistant, "CloudAssistantStatus",
                           default="false")).lower() == "true"
        run.evidence("cloud assistant agent: {0} (version {1})".format(
            "online" if ready else "offline",
            _first(assistant, "CloudAssistantVersion")))
        if not ready:
            run.limit("the Cloud Assistant agent is not answering; until it is "
                      "fixed, guest-side readings below stay a manual step for "
                      "the customer")
    else:
        run.evidence("cloud assistant agent: no status row returned for this "
                     "instance")
    try:
        history = fetch_recent_invocations(region, instance_id, run.session_id)
    except CliError as exc:
        run.limit("DescribeInvocations failed: {0}; the command-history "
                  "reading is unavailable.".format(exc))
        history = []
    if history:
        states = "; ".join("{0}={1}".format(
            str(_first(inv, "InvokeId", default="task")),
            str(_first(inv, "InvocationStatus", "InvokeStatus",
                       default="unknown"))) for inv in history[:5])
        run.evidence("recent cloud assistant invocations: {0} task(s): "
                     "{1}".format(len(history), states))
    else:
        run.evidence("recent cloud assistant invocations: none returned")
    return instance


def add_shared_family_note(run, args, instance):
    instance_type = str(_first(instance, "InstanceType"))
    if not instance_type or instance_type == "UNKNOWN":
        return
    try:
        detail = fetch_instance_type_detail(instance_type, run.session_id)
    except CliError as exc:
        run.limit("DescribeInstanceTypes failed: {0}; the spec-family reading "
                  "is unavailable.".format(exc))
        return
    if not detail:
        run.limit("DescribeInstanceTypes returned no row for {0}.".format(
            instance_type))
        return
    family = str(_first(detail, "InstanceTypeFamily", default=""))
    level = str(_first(detail, "InstanceFamilyLevel", default="UNKNOWN"))
    run.evidence("spec {0}: family={1} vCPU={2} memoryGiB={3} "
                 "familyLevel={4}".format(
                     instance_type, family,
                     _first(detail, "CpuCoreCount"),
                     _first(detail, "MemorySize"), level))
    shared_markers = ("burstable", "shared", "entry")
    if any(marker in level.lower() for marker in shared_markers) or \
            family.startswith(("ecs.t5", "ecs.t6", "ecs.n1", "ecs.n2", "ecs.e4",
                               "ecs.mn2", "ecs.s2", "ecs.s3", "ecs.c1", "ecs.c2")):
        run.verdict(C.VERDICT_SHARED_FAMILY_RISK,
                    "familyLevel {0}: vCPUs can be contested by neighbours; a "
                    "database on this class has no performance SLA - see "
                    "{1}".format(level, C.DOC_LINKS["shared_instance_families"]))


# ---------------------------------------------------------------------------
# layer builders for the connect symptom
# ---------------------------------------------------------------------------
def connect_layers(run, args, instance):
    db_type = (args.db_type or "").lower()
    port = args.port
    if port is None and db_type:
        try:
            port = C.resolve_default_port(db_type)
        except ValueError as exc:
            run.limit("{0}".format(exc))
        else:
            run.assume("port {0} auto-filled from db-type {1}".format(
                port, db_type))
    if not port:
        run.limit("no usable port: the allow-list and listener checks stay "
                  "generic until the customer states the port the client dials")

    client_ip = args.client_ip
    signals = run.signals
    refused = any(s["id"] == "SIG_REFUSED" for s in signals)
    timeout_like = any(s["id"] == "SIG_TIMEOUT" for s in signals)

    run.layer("L0 account/instance state",
              "CHECKED" if instance else "NOT VISIBLE",
              "DescribeInstances/FullStatus rows above; overdue-bill state is "
              "not queryable here - confirm in the billing console")
    sg_ids = _first_list(instance or {}, ("SecurityGroupIds", "SecurityGroupId"))
    run.layer("L2 cloud allow-list",
              "PARTIAL" if sg_ids else "NOT VISIBLE",
              "bound groups {0}; rule detail is not queryable with this "
              "tier's verified surface - paste the ingress rows for port "
              "{1}".format(",".join(sg_ids) or "none", port or "<port>"))
    run.manual("Security group console: verify an ingress rule allows TCP "
               "{0} from {1}; check the port number matches what the client "
               "dials (tickets proved 'opened 40731 while dialing 3306' and "
               "third-party platform approval flows).".format(
                   port or "<port>", client_ip or "<client egress IP>"))
    if args.recent_change and args.recent_change.lower() != "none":
        run.verdict(C.VERDICT_PROPAGATION_DELAY,
                    "a recent change was declared ({0}); freshly added rules "
                    "can take minutes - retest before deeper digging".format(
                        args.recent_change))
        run.layer("L2 propagation", "PROVISIONAL",
                  "recent change declared; confidence LOW until retest")

    if refused:
        run.verdict(C.VERDICT_REFUSED,
                    "the pasted error is a refusal: skip 'the SG blocked me' "
                    "and go straight to listener, bind and grant layers")
    if timeout_like:
        run.verdict(C.VERDICT_TIMEOUT,
                    "the pasted error is a timeout: allow-list and guest "
                    "filter layers first")
    signal_ids = [s["id"] for s in signals]
    if "SIG_NAME_RESOLUTION" in signal_ids:
        run.verdict(C.VERDICT_NAME_RESOLUTION,
                    "the client never opened a socket: its own name "
                    "resolution failed, so no instance-side check explains "
                    "this - verify the host the client dials and its DNS")
    if "SIG_ACCESS_DENIED" in signal_ids:
        run.verdict(C.VERDICT_HOST_GRANT,
                    "the server answered and rejected the account: the "
                    "network path worked, so this is the credential or "
                    "host-grant layer, not the allow-list")
    if "SIG_SQLSERVER_LOGIN" in signal_ids:
        run.verdict(C.VERDICT_AUTH_MODE,
                    "a login-level rejection: mixed-mode authentication, the "
                    "account's enabled state, or the restore target database "
                    "are the ticket-proven causes")

    run.layer("L3 listener/bind", "NOT VISIBLE",
              "requires the customer to run the ss/netstat line below")
    run.manual("Inside the instance run and paste: ss -antp | grep -w {0} "
               "(or netstat -antlp | grep {0}; Windows: "
               "Get-NetTCPConnection -LocalPort {0}). Then feed the output "
               "back to this skill's explain subcommand.".format(port or "<port>"))
    run.layer("L4 guest filters", "NOT VISIBLE",
              "firewalld/iptables/third-party suite readings are human-run")
    run.manual("Inside the instance run and paste: firewall-cmd --list-all; "
               "iptables -nL; and any third-party security suite's port "
               "allow-list screen.")
    run.layer("L5 authentication/grant", "ASK",
              "network-level questions must be settled first; then engine "
              "grants per references/db-on-ecs-diagnosis__database-engine-checks.md")
    if db_type in C.DB_PORTS:
        run.manual("Engine check ({0}): bind address not loopback-only, host "
                   "grant covers the client IP or a wildcard, authentication "
                   "mode allows non-Windows logins (SQL Server: mixed mode + "
                   "enabled account), redis protected-mode/requirepass "
                   "consistent with the client. All changes are the "
                   "customer's to make and restart. {1}".format(
                       C.DB_ENGINE_LABELS.get(db_type, db_type),
                       C.ENGINE_DOC_GAP_NOTE))
    run.layer("L7 client path", "ASK",
              "once the cloud and guest layers above are cleared the "
              "remaining candidates are on the client side")
    if port in C.EXPOSED_DB_PORTS:
        run.manual("Exposure check (hardening item 2): confirm in the "
                   "security-group ingress list that {0} is not open to "
                   "0.0.0.0/0; a database port published to the whole "
                   "internet is the pre-condition on every intrusion ticket "
                   "in this set. Standard set and the platform hardening "
                   "guide: {1}, {2}".format(
                       port, C.DOC_LINKS["security_knowledge"],
                       C.HARDENING_ITEMS[1]))
    if instance and client_ip:
        public_ips = _first_list(instance, ("PublicIpAddress", "IpAddress"))
        eip = _first(_first(instance, "EipAddress", default={}) or {}, "IpAddress")
        if not public_ips and (not eip or eip == "UNKNOWN") and \
                str(_first(instance, "InstanceNetworkType")).lower() == "vpc":
            run.verdict(C.VERDICT_NO_PUBLIC_IP,
                        "the instance carries no public address in this "
                        "region: a remote internet client cannot reach it "
                        "directly, so a public-IP connection attempt was "
                        "never going to land")
            run.layer("L1 reachability/address", "NO PUBLIC ADDRESS",
                      "DescribeInstances returned no public IP and no EIP; "
                      "confirm the intranet or mapping path the client "
                      "actually uses")


# ---------------------------------------------------------------------------
# subcommands
# ---------------------------------------------------------------------------
def cmd_check_auth(args):
    run = Run(new_session_id())
    identity, error = sts_token.preflight(run.session_id)
    if error is not None:
        run.fail(C.NEXT_ACTION_VERIFY_CREDENTIALS,
                 "identity preflight failed: {0}: {1}. Re-authenticate with "
                 "`aliyun sts get-caller-identity`; never paste a key pair into this "
                 "session.".format(error.code, error.message))
        return emit(run, args)
    run.evidence("identity preflight ok: {0}".format(
        json.dumps(sts_token.masked_identity(identity))))
    run.assume("all queries in this session run against the account above; "
               "cross-check it owns the instance")
    return emit(run, args)


def cmd_diagnose(args):
    run = Run(new_session_id())
    identity, error = sts_token.preflight(run.session_id)
    if error is not None:
        run.fail(C.NEXT_ACTION_VERIFY_CREDENTIALS,
                 "identity preflight failed: {0}: {1}".format(error.code,
                                                              error.message))
        return emit(run, args)
    run.evidence("account under diagnosis: {0}".format(
        sts_token.account_label(identity)))
    if not args.region_id:
        args.region_id = C.DEFAULT_REGION
        run.assume("region auto-filled as {0} because none was supplied; "
                   "confirm it with the customer, the queries below are "
                   "regional".format(C.DEFAULT_REGION))
    if not args.instance_id and not args.public_ip:
        run.fail(C.NEXT_ACTION_ASK_REGION,
                 "an instance id or public ip is required")
        return emit(run, args)
    if args.public_ip and not args.instance_id:
        run.assume("instance resolved from public ip {0} in region {1}".format(
            args.public_ip, args.region_id))

    instance = collect_instance_context(run, args)
    if instance is not None:
        add_shared_family_note(run, args, instance)

    if args.error_text:
        run.signals = scan_error_text(args.error_text)
    symptom = args.symptom or "connect"

    if symptom == "connect":
        connect_layers(run, args, instance)
    elif symptom == "performance":
        performance_leg(run, args, instance)
    elif symptom == "availability":
        availability_leg(run, args, instance)
    elif symptom == "deploy":
        deploy_leg(run, args, instance)
    else:
        run.fail(C.NEXT_ACTION_STOP_AND_REPORT,
                 "unknown symptom {0}".format(symptom))
        return emit(run, args)

    run.gate_offer(
        "guest capacity triage (optional, one command at a time): "
        "`python3 scripts/axes/db_on_ecs_diagnosis/db_on_ecs_diagnosis.py probe --region-id {0} "
        "--instance-id {1} --command \"df -h\" --confirm` (and `df -i` for "
        "inodes; Windows equivalents per references/db-on-ecs-diagnosis__guest-commands.md). "
        "Each dispatch needs the disclosure above relayed and its own "
        "confirmation.".format(args.region_id, args.instance_id or "<id>"))

    if run.next_action == C.NEXT_ACTION_NONE:
        verdict_ids = [v[0] for v in run.verdicts]
        capacity_open = any(name in verdict_ids for name in (
            C.VERDICT_CAPACITY_FULL, C.VERDICT_INODE_FULL,
            C.VERDICT_DELETED_OPEN))
        if capacity_open:
            run.next_action = C.NEXT_ACTION_SNAPSHOT_FIRST
        elif run.handoffs:
            run.next_action = C.NEXT_ACTION_HANDOFF
        elif run.manual_steps:
            run.next_action = C.NEXT_ACTION_MANUAL_COMMANDS

    if run.status == C.STATUS_OK and not run.verdicts:
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "cloud side produced no verdict on its own; the "
                    "paste-back readings decide the remaining layers.")
    return emit(run, args)


def performance_leg(run, args, instance):
    metric_keys = [m.strip() for m in (args.metrics or "cpu").split(",")
                   if m.strip()]
    instance_id = args.instance_id or "<id>"
    for key in metric_keys:
        if key not in C.CMS_METRICS:
            run.limit("metric key {0} not on this tier's small allow-list "
                      "(cpu, memory, disk).".format(key))
            continue
        try:
            entry = fetch_metric(args.region_id, key, instance_id, run.session_id)
        except CliError as exc:
            if exc.is_auth_denied:
                run.limit("metric {0} denied: {1}. Missing: the cms query "
                          "permission point cms:QueryMetricLast per "
                          "references/ram-policies.md.".format(key, exc))
            else:
                run.limit("metric {0} failed: {1}".format(key, exc))
            continue
        if entry:
            run.metrics.append(entry)
            for point in entry["points"][:C.CMS_MAX_POINTS_SHOWN]:
                average = _as_number(_first(point, "Average", "Value"))
                if average is not None and key == "cpu" and average >= 90.0:
                    run.verdict(C.VERDICT_CPU_SATURATED,
                                "CPU averaged {0}% in the last window; "
                                "sustained saturation needs attribution: "
                                "business SQL vs shared-neighbour contention "
                                "vs a resource chain".format(average))
    run.layer("metric context",
              "OK" if run.metrics else "DEGRADED",
              "hypervisor CPU always available; in-guest memory/disk series "
              "exist only when the CloudMonitor agent is installed")
    run.manual("Process attribution is a human step this tier's whitelist "
               "does not cover: run and paste top -bn1 | head -25 (Linux) or "
               "tasklist (Windows), plus the engine's own slow log. Without "
               "atop installed beforehand, post-reboot history is gone: "
               "{0}".format(C.DOC_LINKS["atop_monitoring"]))
    run.manual("If the trail points at disk latency rather than CPU, that is "
               "the disk-io tier's measurement surface: "
               "{0}".format(C.DOC_LINKS["block_storage_performance"]))
    if run.verdicts and any(v[0] == C.VERDICT_SHARED_FAMILY_RISK
                            for v in run.verdicts):
        run.limit("on a shared/burstable class, contention verdicts carry "
                  "MEDIUM confidence: no per-neighbour attribution exists at "
                  "the platform layer.")
    verdict_ids = [v[0] for v in run.verdicts]
    if C.VERDICT_CPU_SATURATED in verdict_ids:
        run.handoff(C.HANDOFF_SKILLS["io"],
                    "measured CPU saturation that the shared-class and "
                    "capacity findings above do not account for; disk-latency "
                    "attribution is that tier's measurement surface",
                    "metric rows and spec note above")
    else:
        run.limit("no saturation in the last window, so no performance "
                  "hand-off is asserted; a complaint about an earlier window "
                  "is not confirmed by this reading.")


def availability_leg(run, args, instance):
    run.manual("Engine won't start checklist (all human-run): free -m; df -h; "
               "df -i; the engine's own error log tail; systemctl status "
               "<service> output pasted back.")
    run.gate_offer(
        "capacity triage in one confirmed dispatch: probe with --command "
        "\"df -h\", then --command \"df -i\" after a fresh confirmation; "
        "Windows uses Get-Volume.")
    run.manual("Ticket-proven small-memory path: available memory near zero "
               "with the engine never writing its pid file. Interim: add "
               "swap ({0}); real fix: change the instance spec in the "
               "console ({1}) - a purchase action this skill never "
               "performs.".format(C.DOC_LINKS["swap_knowledge"],
                                  C.DOC_LINKS["change_spec_subscription"]))
    run.layer("capacity chain", "PROBE PROPOSED",
              "a df -h / df -i hit routes to the capacity tier with "
              "snapshot-first; the cleanup itself is never executed here")
    if instance and str(_first(instance, "Status")) != "Running":
        run.handoff(C.HANDOFF_SKILLS["boot"],
                    "instance not Running", "DescribeInstances Status row")


def deploy_leg(run, args, instance):
    run.manual("Product boundary first: an ECS instance ships with no "
               "database; installing one is the customer's own software "
               "work (panel wizards included).")
    run.manual("Pre-checks before any install or restore: (1) free space at "
               "the target path >= backup size plus 20 percent headroom - "
               "pass --backup-size-mb to compare; (2) engine port free; "
               "(3) login path works: {0}".format(C.DOC_LINKS["login_methods"]))
    if args.backup_size_mb:
        run.assume("backup size {0} MB supplied; compare against df -h "
                   "output via probe or paste".format(args.backup_size_mb))
        run.gate_offer(
            "one confirmed dispatch of `df -h` compares free space against "
            "the supplied backup size on the pasted output.")
    run.manual("Migration between servers: clone/custom-image path "
               "({0}) or cross-zone spec change ({1}) stay console "
               "actions; a database restore is business-layer work the "
               "customer performs.".format(C.DOC_LINKS["clone_instances"],
                                           C.DOC_LINKS["change_spec_crosszone"]))
    run.manual(C.BUSINESS_PHRASE)
    run.limit("migration/restore execution itself is out of this tier: the "
              "skill prepares and verifies the environment only.")


def cmd_probe(args):
    run = Run(new_session_id())
    if not args.region_id:
        args.region_id = C.DEFAULT_REGION
        run.assume("region auto-filled as {0} because none was supplied; a "
                   "dispatch targets one instance in one region, so confirm "
                   "it".format(C.DEFAULT_REGION))
    if not args.instance_id:
        run.fail(C.NEXT_ACTION_ASK_REGION, "probe needs --instance-id")
        return emit(run, args)
    allowed, reason = check_command_gate(args.command)
    run.evidence("requested guest command: {0}".format(args.command))
    if not allowed:
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS, reason)
        run.manual("Run this yourself inside the instance and paste the raw "
                   "output back, then feed it to the explain subcommand: "
                   "{0}".format(args.command or "<the command above>"))
        return emit(run, args)
    run.evidence("whitelist check: {0}".format(reason))

    if not args.confirm:
        run.verdict(C.VERDICT_GATE_NOT_ACKNOWLEDGED,
                    "the confirm gate was not passed; nothing was dispatched")
        run.gate_offer(gate_disclosure(args.command, args.instance_id,
                                       args.region_id))
        run.degrade(C.NEXT_ACTION_CONFIRM_GATE,
                    "relay the disclosure, get a yes for THIS command, then "
                    "re-run with --confirm")
        return emit(run, args)

    try:
        instances = fetch_instances(args.region_id, args.instance_id, None,
                                    run.session_id)
    except CliError as exc:
        run.fail(C.NEXT_ACTION_VERIFY_CREDENTIALS if exc.is_auth_denied
                 else C.NEXT_ACTION_RETRY_LATER,
                 "DescribeInstances failed before dispatch: {0}".format(exc))
        return emit(run, args)
    if not instances:
        run.fail(C.NEXT_ACTION_ASK_REGION,
                 "instance {0} not found in region {1}; dispatch "
                 "aborted".format(args.instance_id, args.region_id))
        return emit(run, args)
    instance = instances[0]
    os_type_field = str(_first(instance, "OSType", "OSName")).lower()
    os_family = "windows" if "win" in os_type_field else "linux"
    run.guest["os_family"] = os_family
    run.evidence("guest OS family: {0}".format(os_family))
    command = args.command.strip()
    if os_family == "windows" and command.split()[0].lower() in (
            "df", "du", "findmnt", "lsof", "stat", "ls", "wc"):
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "the instance is Windows but the command is a Linux "
                    "form; use Get-Volume / Get-PSDrive / fsutil instead")
        return emit(run, args)

    try:
        assistant = fetch_assistant_status(args.region_id, args.instance_id,
                                           run.session_id)
    except CliError as exc:
        run.fail(C.NEXT_ACTION_RETRY_LATER,
                 "DescribeCloudAssistantStatus failed: {0}".format(exc))
        return emit(run, args)
    ready = str(_first(assistant, "CloudAssistantStatus",
                       default="false")).lower() == "true"
    run.evidence("cloud assistant status: {0} (version {1})".format(
        "ready" if ready else "not ready",
        _first(assistant, "CloudAssistantVersion")))
    if not ready:
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "the Cloud Assistant agent is not answering; dispatch "
                    "is pointless until the agent is fixed (boot-stuck "
                    "instances route to the instance-state tier). Use the "
                    "paste-back path meanwhile.")
        return emit(run, args)

    try:
        submitted = submit_guest_command(args.region_id, args.instance_id,
                                         command, os_family, run.session_id)
    except CliError as exc:
        run.fail(C.NEXT_ACTION_VERIFY_CREDENTIALS if exc.is_auth_denied
                 else C.NEXT_ACTION_RETRY_LATER,
                 "RunCommand failed: {0}. If denied, the gated write "
                 "permission point is missing - see "
                 "references/ram-policies.md.".format(exc))
        return emit(run, args)
    invoke_id = str(_first(submitted, "InvokeId"))
    run.evidence("command dispatched, invoke id {0}".format(invoke_id))

    try:
        record, timed_out = poll_invocation(args.region_id, invoke_id,
                                            args.instance_id, run.session_id)
    except CliError as exc:
        run.degrade(C.NEXT_ACTION_RETRY_LATER,
                    "DescribeInvocations failed after dispatch: {0}; the "
                    "command did run or failed in the guest - read the "
                    "invocation record in the console before re-sending."
                    .format(exc))
        return emit(run, args)
    if timed_out or not record:
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "the invocation did not finish within the bounded "
                    "window; the guest may be stalled itself (a strong "
                    "resource-pressure hint). Re-run the result read later "
                    "or paste manually.")
        return emit(run, args)

    exit_code = _first(record, "ExitCode", default="0")
    output = decode_output(_first(record, "Output", default=""))
    status_field = str(_first(record, "InvocationStatus", default="UNKNOWN"))
    run.evidence("invocation status {0}, exit code {1}".format(status_field,
                                                               exit_code))
    if output:
        run.guest["raw"] = output[:4000]
        readings = parse_guest_readings(output)
        apply_readings(run, readings, args.port, args.db_type, source="probe")
    if str(exit_code) not in ("0", "UNKNOWN") or \
            status_field.lower() not in ("finished", "success"):
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "the command exited nonzero or did not finish cleanly; "
                    "read the error text in the output above before "
                    "inferring anything.")
    else:
        run.next_action = C.NEXT_ACTION_NONE
    return emit(run, args)


def apply_readings(run, readings, port, db_type, source):
    if readings.get("full_percent_mounts"):
        run.verdict(C.VERDICT_CAPACITY_FULL,
                    "at least one filesystem is at or above {0}% used "
                    "({1} source: {2})".format(
                        C.CAPACITY_WARN_PCT, source,
                        "; ".join(readings["full_percent_mounts"][:3])))
        run.handoff(C.HANDOFF_SKILLS["capacity"],
                    "byte-full disk behind the database symptom",
                    "df reading above; snapshot first before any cleanup")
        run.next_action = C.NEXT_ACTION_SNAPSHOT_FIRST
    if readings.get("inode_full_mounts"):
        run.verdict(C.VERDICT_INODE_FULL,
                    "inode exhaustion with bytes left ({0} source)".format(
                        source))
        run.handoff(C.HANDOFF_SKILLS["capacity"],
                    "inode exhaustion behind the database symptom",
                    "df -i reading above; snapshot first; NTFS has no "
                    "inode equivalent, so this verdict is Linux-only")
        run.next_action = C.NEXT_ACTION_SNAPSHOT_FIRST
    if readings.get("deleted_open"):
        run.verdict(C.VERDICT_DELETED_OPEN,
                    "deleted-but-still-open files hold space: a restart of "
                    "the holding process releases them - that restart is a "
                    "human step")
    if port:
        wanted = str(port)
        listen_ports = listening_ports(readings)
        if wanted in listen_ports:
            run.verdict(C.VERDICT_PORT_LISTENING,
                        "the guest does listen on {0} per the {1} output".format(
                            wanted, source))
        elif listen_ports:
            run.verdict(C.VERDICT_PORT_MISMATCH,
                        "listeners exist on {0} but not on the dialled {1}: "
                        "the client reaches a port nothing is bound to".format(
                            ", ".join(listen_ports), wanted))
            run.verdict(C.VERDICT_DYNAMIC_PORT,
                        "if {0} is the engine's documented default port, a "
                        "listener set that excludes it is the ticket-proven "
                        "dynamic-port drift; the customer pins the port or "
                        "corrects the client string".format(wanted))
    for line in readings.get("listen", []):
        if re.search(C.PUBLIC_BIND_RE, line):
            run.layer("L3 listener/bind", "PUBLIC BIND", line[:160])
            everywhere = re.findall(C.PUBLIC_BIND_PORT_RE, line)
            published = [p for p in everywhere
                         if int(p) in C.EXPOSED_DB_PORTS
                         or p == str(port or "")]
            if published:
                run.verdict(C.VERDICT_PUBLIC_DB_PORT,
                            "the {0} output binds {1} to every address, not "
                            "to one interface: any allow-list entry for it "
                            "makes the database directly reachable, which is "
                            "the pre-condition on the intrusion tickets in "
                            "this set. Console fix, hardening item 2: "
                            "{2}".format(
                                source,
                                ", ".join(sorted(set(published), key=int)),
                                C.HARDENING_ITEMS[1]))
        elif re.search(C.LOCALHOST_BIND_RE, line) and port and str(port) in line:
            run.verdict(C.VERDICT_BIND_LOCALHOST,
                        "the listener is loopback-only: remote clients "
                        "cannot reach it regardless of the cloud allow-list")
    if readings.get("firewall_drop"):
        run.verdict(C.VERDICT_GUEST_FIREWALL,
                    "the pasted filter output drops or rejects traffic that "
                    "names a port ({0} source): {1}".format(
                        source, "; ".join(readings["firewall_drop"][:3])[:200]))
        run.layer("L4 guest filters", "BLOCKING LINE SEEN",
                  "opening the port there is a customer change; the report "
                  "names the missing allow-entry, never a flush command")
    if readings.get("firewall_off"):
        run.layer("L4 guest filters", "FILTER NOT RUNNING",
                  "the in-guest filter is off, so it is not the blocker; the "
                  "timeout branches to the cloud allow-list instead "
                  "(paste source: {0})".format(
                      "; ".join(readings["firewall_off"][:2])[:160]))
    if readings.get("oom"):
        run.verdict(C.VERDICT_OOM_PRESSURE,
                    "memory starvation lines present in the {0} reading".format(
                        source))


def cmd_explain(args):
    run = Run(new_session_id())
    try:
        text = read_paste(args.paste)
    except (IOError, OSError) as exc:
        run.fail(C.NEXT_ACTION_STOP_AND_REPORT,
                 "could not read the pasted file: {0}".format(exc))
        return emit(run, args)
    if not text.strip():
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "no pasted output was supplied; explain interprets ss/"
                    "netstat/firewall/df/engine-log text the customer ran "
                    "themselves.")
        return emit(run, args)
    run.signals = scan_error_text(text)
    readings = parse_guest_readings(text)
    run.guest = dict((k, v) for k, v in readings.items() if v)
    apply_readings(run, readings, args.port, args.db_type, source="paste")
    for signature in run.signals:
        if signature["id"] == "SIG_CONNTRACK_FULL":
            run.verdict(C.VERDICT_CONNTRACK_FULL,
                        "connection-tracking overflow lines seen; kernel "
                        "tuning is a customer change")
        if signature["id"] == "SIG_RANSOM_NOTE":
            run.verdict(C.VERDICT_RANSOMWARE_PATTERN,
                        "attacker note text seen in the paste")
            run.manual(C.INTRUSION_PHRASE)
            run.gate_offer("evidence-preservation snapshot via the "
                           "create-snapshot subcommand after --confirm-cost")
            run.manual("After the snapshot exists and recovery is handled: "
                       "apply the whole hardening set before the workload "
                       "goes back online - {0}. Rebuild via re-initialize "
                       "system disk is a destructive manual step the skill "
                       "documents only: {1}. Alerts for the next attempt: "
                       "{2}".format(
                           "; ".join(C.HARDENING_ITEMS),
                           C.DOC_LINKS["reinit_system_disk"],
                           C.DOC_LINKS["security_center_console"]))
            run.limit("decryption and forensic timelines are never done here; "
                      "recovery goes to a specialist: {0}".format(
                          C.DOC_LINKS["marketplace_recovery"]))
    if not run.verdicts and not run.signals and not readings["listen"]:
        run.verdict(C.VERDICT_NEEDS_CLIENT_EVIDENCE,
                    "the pasted text matched no signature and carried no "
                    "parseable listener, df or firewall reading")
        run.degrade(C.NEXT_ACTION_ASK_GUEST_READINGS,
                    "the paste carried nothing this tier recognizes; ask for "
                    "the raw error text and the ss -antp | grep <port> line.")
    run.assume("explain ran with no cloud access: every conclusion is from "
               "the pasted text alone")
    return emit(run, args)


def cmd_create_snapshot(args):
    run = Run(new_session_id())
    if not args.confirm_cost:
        run.verdict(C.VERDICT_GATE_NOT_ACKNOWLEDGED,
                    "the cost/reversibility gate was not passed; nothing was "
                    "created")
        run.gate_offer(snapshot_disclosure(args.disk_id))
        run.degrade(C.NEXT_ACTION_CONFIRM_GATE,
                    "relay the disclosure, get a yes, then re-run with "
                    "--confirm-cost")
        return emit(run, args)
    run.evidence("snapshot creation confirmed by the operator for disk {0}".format(
        args.disk_id))
    params = {
        "DiskId": args.disk_id,
        "SnapshotName": args.name or "{0}-pre-change".format(C.SKILL_NAME),
        "Description": args.description or "created via {0} at the operator's "
                       "confirmed request".format(C.SKILL_NAME),
    }
    try:
        body = call_ecs_guarded("CreateSnapshot", params, run.session_id,
                                write=True)
    except CliError as exc:
        run.fail(C.NEXT_ACTION_VERIFY_CREDENTIALS if exc.is_auth_denied
                 else C.NEXT_ACTION_RETRY_LATER,
                 "CreateSnapshot failed: {0}. If denied, the gated write "
                 "permission point is missing - see "
                 "references/ram-policies.md.".format(exc))
        return emit(run, args)
    snapshot_id = str(_first(body, "SnapshotId"))
    run.evidence("snapshot requested: {0}".format(snapshot_id))
    run.limit("creation is asynchronous: verify availability in the console "
              "before any cleanup step; deletion of old snapshots stays a "
              "human decision (guide {0})".format(
                  C.DOC_LINKS["delete_snapshot"]))
    run.next_action = C.NEXT_ACTION_NONE
    return emit(run, args)


def read_paste(location):
    if not location:
        return ""
    if location == "-":
        return sys.stdin.read()
    with open(location, "r") as handle:
        return handle.read()


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------
def build_parser():
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--json", action="store_true",
                        help="emit the machine-readable form")

    parser = argparse.ArgumentParser(
        prog="db_on_ecs_diagnosis.py",
        description="Database-on-ECS diagnosis: connectivity, availability, "
                    "performance triage with confirmation gates",
    )
    sub = parser.add_subparsers(dest="command_name")

    auth = sub.add_parser("check-auth", parents=[shared],
                          help="credential preflight and account label")
    auth.set_defaults(func=cmd_check_auth)

    diag = sub.add_parser("diagnose", parents=[shared],
                          help="full layered triage")
    diag.add_argument("--region-id", default=None)
    diag.add_argument("--instance-id", default=None)
    diag.add_argument("--public-ip", default=None)
    diag.add_argument("--symptom", choices=C.SYMPTOMS, default="connect")
    diag.add_argument("--db-type", default=None,
                      help="one of: " + ", ".join(sorted(C.DB_PORTS)))
    diag.add_argument("--port", type=int, default=None)
    diag.add_argument("--error-text", default=None,
                      help="raw error the customer pasted, verbatim")
    diag.add_argument("--client-ip", default=None)
    diag.add_argument("--recent-change", default=None,
                      help="e.g. 'sg rule added minutes ago' or 'none'")
    diag.add_argument("--backup-size-mb", type=int, default=None)
    diag.add_argument("--metrics", default=None,
                      help="comma list of cpu,memory,disk (default cpu)")
    diag.set_defaults(func=cmd_diagnose)

    probe = sub.add_parser("probe", parents=[shared],
                           help="dispatch ONE whitelisted non-mutating guest "
                                "command after confirmation")
    probe.add_argument("--region-id", default=None)
    probe.add_argument("--instance-id", required=True)
    probe.add_argument("--command", required=True)
    probe.add_argument("--port", type=int, default=None)
    probe.add_argument("--db-type", default=None)
    probe.add_argument("--confirm", action="store_true",
                       help="acknowledge the pre-execution disclosure")
    probe.set_defaults(func=cmd_probe)

    explain = sub.add_parser("explain", parents=[shared],
                             help="interpret pasted guest output or raw error "
                                  "text, no cloud access")
    explain.add_argument("--paste", default="-",
                         help="file path or - for stdin")
    explain.add_argument("--port", type=int, default=None)
    explain.add_argument("--db-type", default=None)
    explain.set_defaults(func=cmd_explain)

    snap = sub.add_parser("create-snapshot", parents=[shared],
                          help="gated pre-cleanup / evidence snapshot")
    snap.add_argument("--disk-id", required=True)
    snap.add_argument("--name", default=None)
    snap.add_argument("--description", default=None)
    snap.add_argument("--confirm-cost", action="store_true",
                      help="acknowledge the billing and reversibility "
                           "disclosure")
    snap.set_defaults(func=cmd_create_snapshot)

    return parser


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("STATUS: FAILED\nNEXT_ACTION: STOP_AND_REPORT", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
