#!/usr/bin/env python3
"""Single entry point for ECS disk performance and I/O diagnosis.

The agent runs this script instead of composing cloud CLI calls by hand. It emits a
markdown report that ends with a `STATUS:` and a `NEXT_ACTION:` line.

Subcommands
  diagnose     specification baseline per disk, optional measurements, interpretation
  guest-cmd    deliver one whitelisted in-guest inspection command (confirmation gated)
  snapshot     create one snapshot before a customer-performed change (confirmation gated)
"""

import argparse
import base64
import datetime
import json
import re
import sys

import _cli
import _constants as C
import sts_token


class InputError(Exception):
    pass


def _info(message):
    sys.stderr.write("[INFO] {0}\n".format(message))


def bounded_timeout(value):
    """Reject any per-call timeout that is missing, non-numeric or unbounded."""
    try:
        seconds = int(value)
    except (TypeError, ValueError):
        raise argparse.ArgumentTypeError("timeout must be a whole number of seconds")
    if seconds < 1 or seconds > C.MAX_TIMEOUT:
        raise argparse.ArgumentTypeError("timeout must be between 1 and {0} seconds".format(
            C.MAX_TIMEOUT))
    return seconds


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def _match(pattern, value, label):
    if value is None or not re.match(pattern, value):
        raise InputError("{0} has an unexpected format: {1!r}".format(label, value))
    return value


def validate_instance_id(value):
    return _match(C.INSTANCE_ID_PATTERN, value, "instance id")


def validate_disk_id(value):
    return _match(C.DISK_ID_PATTERN, value, "disk id")


def validate_region(value):
    return _match(C.REGION_ID_PATTERN, value, "region id")


def validate_ip(value):
    _match(C.IPV4_PATTERN, value, "IP address")
    if any(int(part) > 255 for part in value.split(".")):
        raise InputError("IP address is out of range: {0!r}".format(value))
    return value


def validate_snapshot_name(value):
    return _match(C.SNAPSHOT_NAME_PATTERN, value, "snapshot name")


def validate_path(value, os_type):
    """Accept a plain path and nothing that a shell could reinterpret."""
    if value is None:
        raise InputError("this inspection command needs --path")
    if ".." in value or "\n" in value or "\r" in value:
        raise InputError("path traversal and newlines are not accepted")
    pattern = C.WINDOWS_PATH_PATTERN if os_type == "windows" else C.LINUX_PATH_PATTERN
    if not re.match(pattern, value):
        raise InputError("path contains characters outside the accepted set: {0!r}".format(value))
    return value


def parse_event_time(value):
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(value, fmt)
        except (TypeError, ValueError):
            continue
    raise InputError("event time {0!r} is not one of YYYY-MM-DDTHH:MM:SS, "
                     "YYYY-MM-DD HH:MM[:SS] or YYYY-MM-DD".format(value))


def parse_positive_number(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise InputError("{0} must be a number, got {1!r}".format(label, value))
    if number <= 0:
        raise InputError("{0} must be greater than zero".format(label))
    return number


# ---------------------------------------------------------------------------
# Symptom routing, performed before any cloud call
# ---------------------------------------------------------------------------
def classify_symptom(text):
    haystack = (text or "").lower()
    groups = (
        ("capacity", C.ROUTE_AWAY_CAPACITY, "alibabacloud-ecs-disk-capacity-diagnosis"),
        ("expand", C.ROUTE_AWAY_EXPAND, "alibabacloud-ecs-disk-expand-diagnosis"),
        ("instance-state", C.ROUTE_AWAY_STATE, "alibabacloud-ecs-instance-state-diagnosis"),
        ("connectivity", C.ROUTE_AWAY_CONNECTIVITY,
         "remote connectivity handling; this skill only judges whether I/O wedged the instance"),
        ("manual", C.ROUTE_AWAY_MANUAL, "manual support with the owning product console"),
    )
    hits = []
    for name, needles, target in groups:
        matched = [needle for needle in needles if needle in haystack]
        if matched:
            hits.append({"axis": name, "target": target, "keywords": matched})
    io_matched = [needle for needle in C.IO_AXIS_KEYWORDS if needle in haystack]
    if io_matched and not hits:
        primary = "io-performance"
    elif hits:
        primary = "handoff"
    else:
        primary = "unknown"
    return {"io_keywords": io_matched, "away": hits, "primary": primary}


# ---------------------------------------------------------------------------
# Disk ceiling computation
# ---------------------------------------------------------------------------
def disk_ceiling(category, performance_level, size_gib):
    """Return the computed ceiling for one disk, with None where nothing is supported."""
    result = {
        "expected_iops": None,
        "expected_throughput_mbps": None,
        "basis": [],
        "notes": [],
        "provenance": [],
    }
    seen = set()
    category = (category or "").strip()
    level = (performance_level or "").strip().upper()

    def note(text, provenance=None):
        if text and text not in result["notes"]:
            result["notes"].append(text)
        if provenance:
            seen.add(provenance)

    if category == C.ESSD_CATEGORY:
        entry = C.PERFORMANCE_LEVEL_CEILINGS.get(level)
        if entry is None:
            note("Performance level {0!r} is not in the built-in table; confirm it on the block "
                 "storage performance page before quoting a ceiling.".format(performance_level),
                 C.PROVENANCE_NO_GUIDANCE)
        else:
            seen.add(entry["provenance"])
            if entry.get("iops_formula") and size_gib:
                if level == "PL0":
                    computed = min(C.PL0_MAX_IOPS,
                                   C.PL0_IOPS_BASE + C.PL0_IOPS_PER_GB * int(size_gib))
                    result["expected_iops"] = computed
                    result["basis"].append(
                        "IOPS = min({max}, {base} + {step} x {size} GiB) = {got}".format(
                            max=C.PL0_MAX_IOPS, base=C.PL0_IOPS_BASE, step=C.PL0_IOPS_PER_GB,
                            size=int(size_gib), got=computed))
                    if int(size_gib) < C.PL0_IOPS_CAPACITY_FOR_MAX_GB:
                        note("PL0 reaches {max} IOPS only at {need} GiB or more; at {size} GiB the "
                             "ceiling is {got}. A catalogue maximum is not a guarantee at this "
                             "capacity.".format(max=C.PL0_MAX_IOPS,
                                                need=C.PL0_IOPS_CAPACITY_FOR_MAX_GB,
                                                size=int(size_gib), got=computed))
            elif entry.get("max_iops"):
                result["expected_iops"] = entry["max_iops"]
                result["basis"].append("{level} ceiling {value} IOPS".format(
                    level=level, value=entry["max_iops"]))
            if level == "PL0" and not size_gib:
                note(C.SIZE_UNKNOWN_FALLBACK)
            if entry.get("max_throughput_mbps"):
                result["expected_throughput_mbps"] = entry["max_throughput_mbps"]
                result["basis"].append("{level} ceiling {value} MB/s".format(
                    level=level, value=entry["max_throughput_mbps"]))
                if level == "PL0":
                    note("The per-capacity throughput formula for PL0 is not verified in this "
                         "package, so {value} MB/s is the stated ceiling and may exceed what a "
                         "small volume delivers.".format(value=entry["max_throughput_mbps"]))
                if level == "PL2":
                    note("The IOPS ceiling for PL2 is not carried in this package; read it from the "
                         "block storage performance page before comparing IOPS.")
            if level == "PL3":
                note("No PL3 figure is carried in this package; read it from the block storage "
                     "performance page.", C.PROVENANCE_NO_GUIDANCE)

    elif category in C.LOCAL_HDD_CATEGORIES:
        note(C.CATEGORY_CEILINGS[C.LOCAL_HDD_CATEGORIES[0]]["note"], C.PROVENANCE_NO_GUIDANCE)

    elif category == C.LOCAL_SSD_CATEGORY:
        entry = C.CATEGORY_CEILINGS[C.LOCAL_SSD_CATEGORY]
        result["expected_iops"] = entry["max_iops"]
        result["basis"].append("previous-generation local SSD, up to {0} random IOPS".format(
            entry["max_iops"]))
        note(entry["note"], entry["provenance"])

    elif category in (C.CLOUD_AUTO_CATEGORY, C.ELASTIC_EPHEMERAL_DISK_CATEGORY):
        entry = C.CATEGORY_CEILINGS.get(category)
        if entry:
            note(entry["note"], entry["provenance"])

    elif category in (C.CLOUD_EFFICIENCY_CATEGORY, C.CLOUD_SSD_CATEGORY, C.CLOUD_CATEGORY):
        note("Legacy category {0!r}: no capacity-derived formula is bundled, so read the ceiling "
             "from the block storage performance page.".format(category), C.PROVENANCE_NO_GUIDANCE)

    elif category:
        note("Disk category {0!r} is unknown to this package; no ceiling was computed.".format(
            category), C.PROVENANCE_NO_GUIDANCE)
    else:
        note("The disk category was not returned; no ceiling was computed.",
             C.PROVENANCE_NO_GUIDANCE)

    if result["expected_iops"] is None and result["expected_throughput_mbps"] is None:
        seen.add(C.PROVENANCE_NO_GUIDANCE)
    result["provenance"] = sorted(seen)
    return result


def apply_instance_ceiling(rows, ceilings, label, notes):
    """Attach the instance-side ceiling as a second bound when the operator supplied it."""
    if not ceilings:
        return
    for row in rows:
        ceiling = row["ceiling"]
        kind, value = ceilings
        if kind == "iops" and ceiling["expected_iops"]:
            if value < ceiling["expected_iops"]:
                ceiling["expected_iops"] = int(value)
                ceiling["basis"].append("instance-side ceiling {0} IOPS".format(int(value)))
                notes.append("Disk `{0}`: the effective ceiling came from the instance "
                             "specification, so raising the disk alone cannot help; the instance "
                             "type has to change as well.".format(row["disk_id"]))
        elif kind == "mbps" and ceiling["expected_throughput_mbps"]:
            if value < ceiling["expected_throughput_mbps"]:
                ceiling["expected_throughput_mbps"] = round(value, 2)
                ceiling["basis"].append("instance-side ceiling {0} MB/s".format(round(value, 2)))
                notes.append("Disk `{0}`: the effective throughput ceiling came from the instance "
                             "specification.".format(row["disk_id"]))
    if label:
        for row in rows:
            row["notes"].append(label)


# ---------------------------------------------------------------------------
# Measurements
# ---------------------------------------------------------------------------
def parse_metric_spec(spec):
    """`MetricName`, `MetricName:iops`, `MetricName:mbps` or `MetricName:bytes`."""
    if ":" in spec:
        name, _, kind = spec.rpartition(":")
        kind = kind.strip().lower()
        if kind in ("iops", "mbps", "bytes"):
            return name.strip(), kind
    return spec.strip(), None


def datapoints_of(payload):
    raw = _cli.dig(payload, "Datapoints")
    if raw is None:
        return []
    if isinstance(raw, str):
        try:
            raw = json.loads(raw or "[]")
        except ValueError:
            return []
    if isinstance(raw, dict):
        raw = [raw]
    return raw if isinstance(raw, list) else []


def reduce_points(points):
    """Return (peak, number_of_points, basis) from a CloudMonitor datapoint list."""
    values = []
    for point in points:
        if not isinstance(point, dict):
            continue
        for key in ("Maximum", "maximum", "Average", "average", "Value", "value"):
            if key in point and point[key] is not None:
                try:
                    values.append(float(point[key]))
                except (TypeError, ValueError):
                    pass
                break
    if not values:
        return None, 0, "no numeric field"
    return max(values), len(values), "highest of the Maximum or Average fields returned"


def verdict_for(expected, measured):
    if not expected or measured is None or expected <= 0:
        return C.VERDICT_INDETERMINATE, None
    ratio = measured / float(expected)
    if ratio >= C.SATURATION_RATIO:
        return C.VERDICT_AT_CEILING, ratio
    if ratio >= C.NEAR_CEILING_RATIO:
        return C.VERDICT_NEAR_CEILING, ratio
    if ratio < C.WELL_BELOW_CEILING_RATIO:
        return C.VERDICT_WELL_BELOW, ratio
    return C.VERDICT_PARTIAL, ratio


def detect_periodicity(event_times, tolerance_minutes=30):
    """Cluster alarm times across days to surface scheduled jobs."""
    clusters = []
    for moment in sorted(event_times or []):
        minutes = moment.hour * 60 + moment.minute
        placed = False
        for cluster in clusters:
            if abs(cluster["minutes"] - minutes) <= tolerance_minutes:
                cluster["days"].append(moment.date().isoformat())
                placed = True
                break
        if not placed:
            clusters.append({"minutes": minutes, "days": [moment.date().isoformat()]})
    repeated = []
    for cluster in clusters:
        distinct = sorted(set(cluster["days"]))
        if len(distinct) >= 2:
            repeated.append({
                "time_of_day": "{0:02d}:{1:02d}".format(cluster["minutes"] // 60,
                                                        cluster["minutes"] % 60),
                "days": distinct,
            })
    return repeated


# ---------------------------------------------------------------------------
# Cloud reads
# ---------------------------------------------------------------------------
def fetch_instance(session_id, region_id, instance_id, ip_address, timeout):
    params = {"RegionId": region_id}
    if instance_id:
        params["InstanceIds"] = json.dumps([instance_id])
    elif ip_address:
        if ip_address.split(".")[0] in ("10", "172", "192"):
            params["PrivateIpAddresses"] = json.dumps([ip_address])
        else:
            params["PublicIpAddresses"] = json.dumps([ip_address])
    payload, error = _cli.run_optional("DescribeInstances", product=C.ECS_PRODUCT, params=params,
                                       session_id=session_id, timeout=timeout)
    if error:
        return None, error
    rows = _cli.as_list(payload, "Instances", "Instance")
    if instance_id:
        # Only the record carrying the id this run was asked about counts as a
        # finding; anything else in the response is a different instance.
        rows = [row for row in rows
                if str(_cli.dig(row, "InstanceId") or "") == str(instance_id)]
    return rows, None


def fetch_disks(session_id, region_id, instance_id, timeout):
    payload, error = _cli.run_optional(
        "DescribeDisks", product=C.ECS_PRODUCT,
        params={"RegionId": region_id, "InstanceId": instance_id},
        session_id=session_id, timeout=timeout)
    if error:
        return [], error
    return _cli.as_list(payload, "Disks", "Disk"), []


def fetch_instance_type(session_id, instance_type, timeout):
    params = {"InstanceTypes.1": instance_type} if instance_type else {}
    payload, error = _cli.run_optional("DescribeInstanceTypes", product=C.ECS_PRODUCT,
                                       params=params, session_id=session_id, timeout=timeout)
    if error:
        return [], error
    types = _cli.as_list(payload, "InstanceTypes", "InstanceType")
    target = types[0] if types else {}
    fields = _cli.collect_keys(target, ("iops", "storagebandwidth", "diskbandwidth", "throughput"))
    return fields, None


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------
def render(rows, context, limitations, assumptions, actions, status, next_action):
    routing = context.get("routing") or {}
    out = ["# ECS disk I/O diagnosis", ""]
    out.append("Session: `{0}`".format(context.get("session_id", "-")))
    out.append("")
    out.append("## 1. Scope gate")
    out.append("")
    out.append("- Primary axis: `{0}`".format(routing.get("primary", "unknown")))
    if routing.get("io_keywords"):
        out.append("- I/O wording matched: {0}".format(", ".join(routing["io_keywords"])))
    for hit in routing.get("away", []):
        out.append("- Wording also matches the **{0}** axis -> {1} (matched: {2})".format(
            hit["axis"], hit["target"], ", ".join(hit["keywords"])))
    if routing.get("away"):
        out.append("- Settle the axis with the customer before continuing: a capacity complaint "
                   "must not be answered with a performance analysis.")
    out.append("")
    out.append("## 2. Instance")
    out.append("")
    for line in context.get("instance_lines", ["- not resolved"]):
        out.append("- {0}".format(line.lstrip("- ")))
    out.append("")
    out.append("## 3. Per-disk evidence")
    out.append("")
    if not rows:
        out.append("No disk row was produced, so no disk-level conclusion is available.")
    else:
        out.append("| Disk | Role | Category | Level | Size GiB | Ceiling IOPS | Ceiling MB/s | "
                   "Measured | Ratio | Verdict |")
        out.append("|---|---|---|---|---|---|---|---|---|---|")
        for row in rows:
            ratio = "-" if row.get("ratio") is None else "{0:.0%}".format(row["ratio"])
            out.append("| {disk} | {role} | {category} | {level} | {size} | {iops} | {mbps} | "
                       "{measured} | {ratio} | {verdict} |".format(
                           disk=row.get("disk_id", "-"),
                           role=row.get("role", "-"),
                           category=row.get("category", "-"),
                           level=row.get("performance_level", "-"),
                           size=row.get("size_gib", "-"),
                           iops=row["ceiling"]["expected_iops"] if
                           row["ceiling"]["expected_iops"] is not None else "unknown",
                           mbps=row["ceiling"]["expected_throughput_mbps"] if
                           row["ceiling"]["expected_throughput_mbps"] is not None else "unknown",
                           measured=row.get("measured_text", "no reading"),
                           ratio=ratio,
                           verdict=row.get("verdict", C.VERDICT_INDETERMINATE)))
        out.append("")
        for row in rows:
            if not (row.get("basis") or row.get("notes")):
                continue
            out.append("### Disk `{0}`".format(row.get("disk_id", "-")))
            out.append("")
            for line in row.get("basis", []):
                out.append("- Ceiling basis: {0}".format(line))
            for line in row.get("notes", []):
                out.append("- {0}".format(line))
            for line in row.get("verdict_wording", []):
                out.append("- Reading: {0}".format(line))
            if row.get("provenance"):
                out.append("- Figure provenance: {0}".format(", ".join(row["provenance"])))
            out.append("")
    out.append("## 4. Interpretation")
    out.append("")
    for line in context.get("interpretation_lines", ["- No comparison was available."]):
        out.append("- {0}".format(line.lstrip("- ")))
    out.append("")
    out.append("## 5. Declared parameters and assumptions")
    out.append("")
    for line in assumptions or ["- None"]:
        out.append("- {0}".format(line))
    out.append("")
    out.append("## 6. Limitations")
    out.append("")
    for line in limitations or ["- None recorded."]:
        out.append("- {0}".format(line))
    out.append("")
    out.append("## 7. Next actions")
    out.append("")
    for line in actions or ["- Nothing further could be derived from the available evidence."]:
        out.append("- {0}".format(line))
    out.append("")
    out.append("## 8. Console entry points")
    out.append("")
    out.append("- Cloud service diagnosis tasks: {0}".format(C.CONSOLE_HEALTH_DIAGNOSIS))
    out.append("- CloudMonitor host monitoring: {0}".format(C.CONSOLE_HOST_MONITOR))
    out.append("- Documentation index: references/help-topics.md")
    out.append("- Hand-off routing: references/handoff-map.md")
    out.append("- In-guest command set: references/guest-commands.md")
    out.append("")
    out.append(status)
    out.append(next_action)
    return "\n".join(out)


def build_interpretation(rows, context):
    lines = []
    if not rows:
        return ["- No disk row was produced, so no I/O verdict is issued."]
    verdicts = [row.get("verdict") for row in rows]
    if context.get("event_reasons"):
        reasons = []
        for token in sorted(set(context["event_reasons"])):
            explained = C.ALARM_REASON_CODES.get(token)
            reasons.append("{0} ({1})".format(token, explained) if explained else token)
        lines.append("Customer-supplied event tokens: {0}. A reason code naming the system disk "
                     "means the system disk row is the one to read first.".format(", ".join(reasons)))
    if C.VERDICT_INDETERMINATE in verdicts:
        lines.append("At least one disk could not be compared against a ceiling; treat those rows "
                     "as unproven in both directions rather than normal.")
    if C.VERDICT_AT_CEILING in verdicts:
        lines.append("At least one disk reached its computed ceiling. Check whether the same disk "
                     "keeps doing so over a longer window before proposing a higher performance "
                     "level; when the instance specification is the binding limit, the instance "
                     "type has to change together with the disk.")
    if C.VERDICT_NEAR_CEILING in verdicts:
        lines.append("At least one disk sat close to but not at its ceiling. Call that throttling "
                     "only when an alarm names the same disk and window.")
    if C.VERDICT_WELL_BELOW in verdicts:
        lines.append("Disks marked well-below-ceiling were not limited by their own specification. "
                     "An alert from monitoring outside Alibaba Cloud on those disks is usually a "
                     "threshold that was never calibrated per disk type and capacity.")
    if all(verdict == C.VERDICT_WELL_BELOW for verdict in verdicts):
        lines.append("No disk reached its ceiling in the available readings, which makes a platform "
                     "or hardware fault the least likely explanation.")
    for cluster in context.get("periodic", []):
        lines.append("Alarms repeat at about {time} on {days}. A fixed window points at a scheduled "
                     "job: a snapshot policy, a backup client, a package metadata timer or an "
                     "application cron task. Name the owner of that window before spending on a "
                     "larger disk.".format(time=cluster["time_of_day"],
                                           days=", ".join(cluster["days"])))
    lines.append("The most frequent root cause on this axis is memory pressure surfacing as disk "
                 "I/O, not a disk fault. Confirm the memory watermark on the CloudMonitor "
                 "operating-system page of the instance and check whether a swap area or a Windows "
                 "page file exists before changing any disk setting.")
    lines.append("Process-level attribution is out of reach here: neither the cloud APIs nor the "
                 "callable command set report which process issued the I/O. A history recorder such "
                 "as atop has to be installed before the next occurrence.")
    return lines


def build_actions(context, measured_any):
    actions = ["Keep the evidence table with the case; it names the disk, the metric and the "
               "ceiling that were compared."]
    actions.append("Any performance level change, instance upgrade or restart is a manual "
                   "operation: state the impact and the billing consequence, and take a snapshot "
                   "beforehand.")
    if not measured_any:
        actions.append("Add measured values by re-running with --namespace and --metric once the "
                       "metric names are confirmed, or read the CloudMonitor pages quoted above.")
    if context.get("periodic"):
        actions.append("Identify the scheduled job behind the repeated window before any upgrade.")
    actions.append("If a per-process answer is required, guide the customer to install a history "
                   "recorder such as atop and return after the next occurrence; see "
                   "references/help-topics.md.")
    return actions


# ---------------------------------------------------------------------------
# diagnose
# ---------------------------------------------------------------------------
def cmd_diagnose(args):
    session_id = _cli.new_session_id()
    limitations = []
    assumptions = []
    degradations = []
    notes = []
    rows = []

    instance_id = validate_instance_id(args.instance_id) if args.instance_id else None
    ip_address = validate_ip(args.ip) if args.ip else None
    region_id = validate_region(args.region_id)
    disk_filter = [validate_disk_id(value) for value in (args.disk_id or [])]
    report_id = None
    if args.diagnosis_report_id:
        report_id = _match(C.DIAGNOSIS_REPORT_ID_PATTERN, args.diagnosis_report_id,
                           "diagnosis report id")

    if not instance_id and not ip_address:
        raise InputError("either --instance-id (i-...) or --ip is required")
    if instance_id and ip_address:
        raise InputError("pass --instance-id or --ip, not both")

    windows = args.windows or list(C.DEFAULT_WINDOWS)
    for window in windows:
        if window not in C.WINDOW_SECONDS:
            raise InputError("unknown window {0!r}; choose from {1}".format(
                window, ", ".join(sorted(C.WINDOW_SECONDS))))
    event_times = [parse_event_time(value) for value in (args.event_time or [])]
    metric_specs = [parse_metric_spec(spec) for spec in (args.metric or [])]
    for name, _kind in metric_specs:
        if not re.match(r"^[A-Za-z0-9_.\-]{1,128}$", name):
            raise InputError("metric name {0!r} contains rejected characters".format(name))
    if metric_specs and not args.namespace:
        raise InputError("--namespace is required when --metric is used")
    if args.period is not None and args.period < 1:
        raise InputError("--period must be a positive number of seconds")

    event_reasons = []
    if args.event_json:
        try:
            event_payload = json.loads(args.event_json)
        except ValueError:
            raise InputError("--event-json is not valid JSON")
        blob = json.dumps(event_payload)
        for token in C.CLOUD_EVENT_TOKENS:
            if token in blob:
                event_reasons.append(token)
        for key in ("reasonCode", "reason", "Name", "name", "eventType"):
            value = _cli.dig(event_payload, key)
            if value:
                event_reasons.append(str(value))

    assumptions.append("session id {0} was generated for this run and attached to every "
                       "cloud call".format(session_id))
    assumptions.append("region {0} was supplied by the operator; the region is never guessed".format(
        region_id))
    assumptions.append(C.LIMITATION_NO_PASSWORD_COLLECTED)

    if args.skip_identity:
        assumptions.append("identity pre-flight was skipped with --skip-identity")
    else:
        identity, error = _cli.run_optional("GetCallerIdentity", product=C.STS_PRODUCT, params={},
                                            session_id=session_id, timeout=args.timeout,
                                            hyphenated=True)
        if error:
            degradations.append("identity pre-flight failed ({0})".format(error.code))
            limitations.append("Identity pre-flight failed: {0}. Resource visibility is "
                               "unconfirmed. Configure credentials with `aliyun configure`; this "
                               "skill never asks for an access key, a secret or an instance "
                               "password.".format(_cli.mask_secrets(error)))
        else:
            assumptions.append("caller identity resolved as {0} from the default credential "
                               "chain".format(sts_token.identity_label(identity or {})))

    _info("resolving the instance")
    instances, error = fetch_instance(session_id, region_id, instance_id, ip_address, args.timeout)
    instance_lines = []
    resolved_id = None
    resolved_type = None
    resolved_region = region_id
    if error:
        degradations.append("DescribeInstances failed ({0})".format(error.code))
        limitations.append("DescribeInstances failed: {0}. The region, instance type and operating "
                           "system family are unconfirmed.".format(_cli.mask_secrets(error)))
        instance_lines.append("Instance lookup failed; see limitations.")
    elif not instances:
        limitations.append("No instance matched `{0}` in `{1}`. Verify the identifier and the "
                           "region, and confirm that this account owns the "
                           "resource.".format(instance_id or ip_address, region_id))
    else:
        instance = instances[0]
        resolved_id = _cli.dig(instance, "InstanceId") or instance_id
        resolved_type = _cli.dig(instance, "InstanceType")
        resolved_region = _cli.dig(instance, "RegionId") or region_id
        os_name = _cli.dig(instance, "OSName") or _cli.dig(instance, "OSType") or ""
        os_type = "windows" if "windows" in str(os_name).lower() else "linux"
        instance_lines = [
            "Instance `{0}` in region `{1}`, zone `{2}`, status `{3}`".format(
                resolved_id, resolved_region or "-", _cli.dig(instance, "ZoneId") or "-",
                _cli.dig(instance, "Status") or "-"),
            "Instance type `{0}`".format(resolved_type or "-"),
            "Operating system family taken as `{0}` from `{1}`".format(os_type, os_name or "-"),
        ]
        if resolved_region and resolved_region != region_id:
            degradations.append("region mismatch")
            limitations.append("The instance record reports region {0} while {1} was requested; "
                               "all readings below use {0}.".format(resolved_region, region_id))
        assumptions.append("instance identifier normalised to `{0}`".format(resolved_id))

    if report_id:
        instance_lines.append("Diagnosis report `{0}` quoted by the customer; this skill cannot "
                              "open it, the full report stays in the cloud service diagnosis "
                              "console".format(report_id))

    ceilings_field = []
    if resolved_id:
        _info("reading the instance specification")
        ceilings_field, error = fetch_instance_type(session_id, resolved_type, args.timeout) \
            if resolved_type else ([], None)
        if error:
            degradations.append("DescribeInstanceTypes failed ({0})".format(error.code))
            limitations.append("DescribeInstanceTypes failed: {0}. The instance-side storage "
                               "ceilings are unknown, so disk ceilings below are not lowered by "
                               "the instance specification.".format(_cli.mask_secrets(error)))
        elif ceilings_field:
            for path, value in ceilings_field:
                instance_lines.append("Candidate instance storage field `{0}` = {1}".format(path, value))
            limitations.append("The fields above are listed under the names the API actually "
                               "returned. Which of them binds IOPS and throughput is not confirmed "
                               "inside this package, so they are informational; pass "
                               "--instance-iops-ceiling or --instance-mbps-ceiling to apply a "
                               "confirmed instance bound.")
        else:
            limitations.append("No instance-side storage ceiling field appeared in the response, so "
                               "only the disk ceiling was used. Where an instance type binds the "
                               "disk, upgrading the disk alone will not raise the effective limit.")

    if resolved_id:
        _info("reading disks")
        disks, disk_errors = fetch_disks(session_id, resolved_region or region_id, resolved_id,
                                         args.timeout)
        if disk_errors:
            degradations.append("DescribeDisks failed ({0})".format(disk_errors.code))
            limitations.append("DescribeDisks failed: {0}. No per-disk ceiling could be "
                               "computed.".format(_cli.mask_secrets(disk_errors)))
            disks = []
        if disk_filter:
            disks = [disk for disk in disks if _cli.dig(disk, "DiskId") in disk_filter]
            if not disks:
                limitations.append("None of the requested disk ids belongs to this instance.")
        for disk in disks:
            size = _cli.dig(disk, "Size")
            try:
                size = int(size) if size is not None else None
            except (TypeError, ValueError):
                size = None
            ceiling = disk_ceiling(_cli.dig(disk, "Category"),
                                   _cli.dig(disk, "PerformanceLevel"), size)
            rows.append({
                "disk_id": _cli.dig(disk, "DiskId"),
                "role": _cli.dig(disk, "Type") or "-",
                "category": _cli.dig(disk, "Category") or "-",
                "performance_level": _cli.dig(disk, "PerformanceLevel") or "-",
                "size_gib": size if size is not None else "-",
                "device": _cli.dig(disk, "Device") or "-",
                "ceiling": ceiling,
                "basis": list(ceiling["basis"]),
                "notes": list(ceiling["notes"]),
                "provenance": list(ceiling["provenance"]),
                "measured": {},
            })
    else:
        limitations.append("No disk list could be read because the instance was not resolved.")

    instance_bound = None
    if args.instance_iops_ceiling:
        instance_bound = ("iops", parse_positive_number(args.instance_iops_ceiling,
                                                        "--instance-iops-ceiling"))
    elif args.instance_mbps_ceiling:
        instance_bound = ("mbps", parse_positive_number(args.instance_mbps_ceiling,
                                                        "--instance-mbps-ceiling"))
    if instance_bound and rows:
        apply_instance_ceiling(rows, instance_bound,
                              "The effective ceiling below was set by an operator supplied "
                              "instance-side limit.", notes)
        assumptions.append("instance-side ceiling {0} = {1} was supplied by the operator and "
                           "applied as min(disk, instance)".format(instance_bound[0],
                                                                   instance_bound[1]))

    for line in notes:
        limitations.append(line)

    measured_any = False
    empty_series_seen = False
    if rows and metric_specs:
        _info("reading CloudMonitor values")
        period = args.period or C.CMS_DEFAULT_PERIOD_SECONDS
        now = datetime.datetime.utcnow()
        dimensions = [{"instanceId": resolved_id}]
        assumptions.append("CloudMonitor dimensions were sent as {0}; the dimension key naming for "
                           "per-disk metrics is not verified inside this package".format(
                               json.dumps(dimensions)))
        assumptions.append("CloudMonitor period {0}s was applied where the metric supports it".format(
            period))
        for row in rows:
            if row["disk_id"]:
                dimensions[0]["diskId"] = row["disk_id"]
            else:
                dimensions[0].pop("diskId", None)
            for name, kind in metric_specs:
                for window in windows:
                    start = (now - datetime.timedelta(seconds=C.WINDOW_SECONDS[window])).strftime(
                        "%Y-%m-%dT%H:%M:%SZ")
                    params = {
                        "Namespace": args.namespace,
                        "MetricName": name,
                        "Dimensions": json.dumps(list(dimensions)),
                        "Period": period,
                        "StartTime": start,
                    }
                    payload, error = _cli.run_optional("DescribeMetricLast", product=C.CMS_PRODUCT,
                                                       params=params, session_id=session_id,
                                                       timeout=args.timeout)
                    if error:
                        degradations.append("metric {0} unreadable".format(name))
                        limitations.append("Metric {0} over {1} could not be read: {2}".format(
                            name, window, _cli.mask_secrets(error)))
                        continue
                    peak, count, basis = reduce_points(datapoints_of(payload or {}))
                    if peak is None:
                        empty_series_seen = True
                        limitations.append("Metric {0} over {1} returned no numeric value; an empty "
                                           "series is a collection gap, not a healthy "
                                           "reading.".format(name, window))
                        continue
                    if kind == "bytes":
                        peak = peak / 1048576.0
                    row["measured"].setdefault(name, {})[window] = {
                        "peak": peak,
                        "points": count,
                        "kind": kind or "unspecified",
                        "basis": basis,
                    }
                    measured_any = True

    if empty_series_seen:
        limitations.append(C.LIMITATION_AGENT_MISSING)

    for row in rows:
        texts = []
        best_verdict, best_ratio = None, None
        for name in sorted(row["measured"]):
            for window in sorted(row["measured"][name],
                                 key=lambda item: C.WINDOW_SECONDS.get(item, 0)):
                info = row["measured"][name][window]
                expected = None
                if info["kind"] == "iops":
                    expected = row["ceiling"]["expected_iops"]
                elif info["kind"] in ("mbps", "bytes"):
                    expected = row["ceiling"]["expected_throughput_mbps"]
                verdict, ratio = verdict_for(expected, info["peak"])
                unit = "" if info["kind"] == "iops" else " MB/s"
                share = "" if ratio is None else ", {0:.0%} of ceiling".format(ratio)
                texts.append("{0} {1}: {2:.2f}{3}{4} ({5} points, {6})".format(
                    name, window, info["peak"], unit, share, info["points"], verdict))
                if info["kind"] is None or info["kind"] == "unspecified":
                    texts.append("{0}: the metric kind was not declared, so no ceiling comparison "
                                 "was made; suffix the metric with :iops, :mbps or :bytes".format(name))
                if best_verdict is None or verdict == C.VERDICT_AT_CEILING:
                    best_verdict, best_ratio = verdict, ratio
        row["measured_text"] = "<br>".join(texts) if texts else "no reading"
        row["verdict"] = best_verdict or C.VERDICT_INDETERMINATE
        row["ratio"] = best_ratio
        wording = C.VERDICT_WORDING.get(row["verdict"])
        if wording:
            row["verdict_wording"] = [wording]

    limitations.append(C.LIMITATION_GRANULARITY)
    limitations.append(C.LIMITATION_NO_PROCESS_ATTRIBUTION)
    limitations.append(C.LIMITATION_EVENT_INTAKE)
    limitations.append("Ceiling figures whose provenance is `{0}` come from the source material "
                       "rather than a confirmed document section; verify them on the block storage "
                       "performance page before quoting them as a service commitment.".format(
                           C.PROVENANCE_AGENT_NOTE))
    if not metric_specs:
        limitations.append(C.CMS_NAMESPACE_HELP)
        limitations.append(C.LIMITATION_NO_MEMORY_SERIES)
        limitations.append("No measurement series was read, so this report compares the symptom "
                           "against specification ceilings only.")
    if event_reasons:
        limitations.append("The cloud event content analysed here was pasted by the customer; the "
                           "official description of this event name is not carried in this package.")

    context = {
        "session_id": session_id,
        "routing": classify_symptom(args.symptom),
        "instance_lines": instance_lines or ["Instance not resolved"],
        "periodic": detect_periodicity(event_times),
        "event_reasons": event_reasons,
    }
    context["interpretation_lines"] = build_interpretation(rows, context)
    actions = build_actions(context, measured_any)

    if not rows:
        status = C.STATUS_FAIL
        next_action = ("NEXT_ACTION: re-run with a verified --instance-id and --region-id, or hand "
                       "the case to manual support.")
    elif degradations:
        status = C.STATUS_DEGRADED
        next_action = ("NEXT_ACTION: close the gaps listed under limitations, then re-run; do not "
                       "publish a single-cause conclusion while they remain open.")
    elif measured_any:
        status = C.STATUS_OK
        next_action = ("NEXT_ACTION: send the report, then confirm the memory watermark and the "
                       "presence of a swap area or page file before any disk change.")
    else:
        status = C.STATUS_DEGRADED
        next_action = ("NEXT_ACTION: supply --namespace and --metric to add measured values, or "
                       "read the CloudMonitor pages listed above with the customer.")

    print(render(rows, context, limitations, assumptions, actions, status, next_action))
    return 0


# ---------------------------------------------------------------------------
# guest-cmd
# ---------------------------------------------------------------------------
def cmd_guest_cmd(args):
    session_id = _cli.new_session_id()
    instance_id = validate_instance_id(args.instance_id)
    region_id = validate_region(args.region_id)
    entry = C.GUEST_COMMANDS.get(args.command_key)

    if entry is None:
        print("# In-guest command not available")
        print("")
        print("`{0}` is not part of the callable command set of this skill.".format(
            args.command_key))
        print("")
        print("Callable keys: {0}".format(", ".join(sorted(C.GUEST_COMMANDS))))
        print("")
        print("Tools that are refused on purpose, because they sit outside the batch command list "
              "or change state: {0}.".format(", ".join(C.REFUSED_GUEST_TOOLS)))
        print("")
        print("Also withheld, because no concrete variant was verified: {0}".format(
            "; ".join(C.GUEST_COMMANDS_WITHHELD)))
        print("")
        print("For a per-process I/O answer, guide the customer to install a history recorder such "
              "as atop and read it after the next occurrence; see references/guest-commands.md.")
        print("")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: offer only the keys listed above, or hand the in-guest step to manual "
              "support and state why.")
        return 0

    os_type = args.os or entry["os"]
    if entry["os"] != os_type:
        raise InputError("command key {0!r} targets {1} instances, not {2}".format(
            args.command_key, entry["os"], os_type))

    content = entry["command"]
    if entry["needs_path"]:
        content = "{0} {1}".format(content, validate_path(args.path, os_type))

    print("# Confirmation required before any in-guest execution")
    print("")
    print("- Target instance: `{0}` in `{1}`".format(instance_id, region_id))
    print("- Channel: Cloud Assistant `RunCommand`, one command per invocation")
    print("- Command that would run: `{0}`".format(content))
    print("- What it returns: {0}".format(entry["purpose"]))
    print("- State change: {0}".format("none, the command only prints information"
                                       if entry["mutates"] == "no" else "the command alters state"))
    print("- Reversibility: nothing is written, so no rollback is required")
    print("- Blast radius: one inspection command inside this single instance; it adds a small "
          "amount of load while the instance is already saturated")
    print("")
    if not args.confirm:
        print("Nothing has been executed.")
        print("")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: show the block above to the customer, obtain an explicit yes for this "
              "one command, then re-run the same command with --confirm.")
        return 0

    command_type = (C.RUN_COMMAND_WINDOWS_TYPE if os_type == "windows"
                    else C.RUN_COMMAND_LINUX_TYPE)
    _info("delivering one whitelisted inspection command")
    payload, error = _cli.run_optional(
        "RunCommand", product=C.ECS_PRODUCT, session_id=session_id, timeout=args.timeout,
        params={
            "RegionId": region_id,
            "Type": command_type,
            "CommandContent": content,
            "InstanceId.1": instance_id,
            "Timeout": C.RUN_COMMAND_TIMEOUT_SECONDS,
        })
    if error:
        print("")
        print("- Execution was not delivered: {0}".format(_cli.mask_secrets(error)))
        print("- Usual causes: the Cloud Assistant agent is missing or offline on this instance, "
              "the region does not match the instance, or the caller lacks `run-command`.")
        print("- Fall back to asking the customer to run `{0}` and paste the output.".format(content))
        print("")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: request the pasted output of `{0}`, or open a manual ticket when the "
              "agent is unavailable.".format(content))
        return 0

    invoke_id = _cli.dig(payload or {}, "InvokeId")
    print("")
    print("- Invocation id: `{0}`".format(invoke_id or "-"))
    output_text = None
    status_note = ""
    if invoke_id:
        result, error = _cli.run_optional(
            "DescribeInvocations", product=C.ECS_PRODUCT, session_id=session_id,
            timeout=args.timeout, params={"RegionId": region_id, "InvokeId": invoke_id})
        if error:
            status_note = ("The command was accepted but its result could not be read back: "
                           "{0}".format(_cli.mask_secrets(error)))
        else:
            invocations = _cli.as_list(result, "Invocations", "Invocation")
            if invocations:
                inner = _cli.as_list(invocations[0], "InvokeInstances", "InvokeInstance")
                record = inner[0] if inner else invocations[0]
                output_text = _cli.dig(record, "Output")
                print("- Invocation status: `{0}` (this call returns recorded results, not live "
                      "usage)".format(_cli.dig(record, "InvocationStatus") or "-"))
    if status_note:
        print("- {0}".format(status_note))

    if output_text:
        try:
            decoded = base64.b64decode(str(output_text)).decode("utf-8", "replace")
        except Exception:
            decoded = str(output_text)
        print("")
        print("## Command output")
        print("")
        print("```")
        for line in _cli.mask_secrets(decoded).splitlines():
            print(line)
        print("```")
        print("")
        print(C.LIMITATION_SMOKE_TEST_ONLY)
        print("")
        print(C.STATUS_OK)
        print("NEXT_ACTION: combine this output with the `diagnose` evidence table before drawing "
              "a conclusion.")
    else:
        print("")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: the command was delivered but no output came back; ask the customer to "
              "paste the result or check that the Cloud Assistant agent is online.")
    return 0


# ---------------------------------------------------------------------------
# snapshot
# ---------------------------------------------------------------------------
def cmd_snapshot(args):
    session_id = _cli.new_session_id()
    disk_id = validate_disk_id(args.disk_id)
    name = validate_snapshot_name(args.snapshot_name) if args.snapshot_name else None

    print("# Confirmation required before any snapshot")
    print("")
    print("- Disk: `{0}`".format(disk_id))
    print("- Action: `CreateSnapshot`, one disk per call, a low-risk reversible write")
    print("- Effect: creates a restore point; the instance and the disk contents are untouched")
    print("- Reversibility: the snapshot can be removed later, and it bills for its size until then")
    print("- Why: a restore point is expected before a restart, a performance level change or any "
          "other customer-performed modification")
    print("")
    if not args.confirm:
        print("Nothing has been created.")
        print("")
        print(C.STATUS_DEGRADED)
        print("NEXT_ACTION: state the billing consequence, obtain an explicit yes, then re-run "
              "with --confirm.")
        return 0

    params = {"DiskId": disk_id}
    if name:
        params["SnapshotName"] = name
    _info("creating one snapshot")
    payload, error = _cli.run_optional("CreateSnapshot", product=C.ECS_PRODUCT, params=params,
                                       session_id=session_id, timeout=args.timeout)
    if error:
        print("")
        print("- Snapshot was not created: {0}".format(_cli.mask_secrets(error)))
        print("- Usual causes: the disk is still initialising, a snapshot of this disk is already "
              "in progress, or the caller lacks the permission.")
        print("")
        print(C.STATUS_FAIL)
        print("NEXT_ACTION: resolve the reported cause first; the customer must not proceed with "
              "the pending change while unprotected.")
        return 1

    print("")
    print("- Snapshot id: `{0}`".format(_cli.dig(payload or {}, "SnapshotId") or "-"))
    print("- Assumption: the default region of the CLI profile was used, since the call is scoped "
          "by the disk identifier")
    print("")
    print(C.STATUS_OK)
    print("NEXT_ACTION: wait until the snapshot is finished before the customer restarts or "
          "reconfigures, and remind them to clean up unused snapshots afterwards.")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
def build_parser():
    parser = argparse.ArgumentParser(
        prog="disk_io_diagnosis.py",
        description="Diagnose ECS disk performance and I/O saturation from evidence.",
        epilog="Cloud access goes through the aliyun CLI using the default credential chain. "
               "In-guest execution and snapshots require an explicit confirmation flag.")
    sub = parser.add_subparsers(dest="command")

    diag = sub.add_parser("diagnose", help="compute per-disk ceilings and compare measurements")
    diag.add_argument("--instance-id", help="instance identifier, i-...")
    diag.add_argument("--ip", help="private or public IPv4 address of the instance")
    diag.add_argument("--region-id", required=True, help="region id of the instance")
    diag.add_argument("--disk-id", action="append",
                      help="restrict the analysis to one disk, d-...; repeatable")
    diag.add_argument("--symptom", default="",
                      help="customer wording, used only by the routing gate")
    diag.add_argument("--event-time", action="append",
                      help="alarm or observation time, YYYY-MM-DDTHH:MM:SS; repeatable")
    diag.add_argument("--event-json", help="cloud event payload pasted by the customer, JSON text")
    diag.add_argument("--diagnosis-report-id",
                      help="diagnosis report id quoted by the customer, dr-...; recorded as "
                           "context only")
    diag.add_argument("--namespace", help="CloudMonitor namespace; required with --metric")
    diag.add_argument("--metric", action="append",
                      help="CloudMonitor metric, optionally suffixed :iops, :mbps or :bytes; "
                           "repeatable")
    diag.add_argument("--period", type=int, help="CloudMonitor period in seconds")
    diag.add_argument("--windows", action="append",
                      help="sampling window, one of {0}; repeatable".format(
                          ", ".join(sorted(C.WINDOW_SECONDS))))
    diag.add_argument("--instance-iops-ceiling",
                      help="confirmed instance-side IOPS ceiling, applied as min(disk, instance)")
    diag.add_argument("--instance-mbps-ceiling",
                      help="confirmed instance-side throughput ceiling in MB/s, applied as "
                           "min(disk, instance)")
    diag.add_argument("--skip-identity", action="store_true",
                      help="skip the identity pre-flight call")
    diag.add_argument("--timeout", type=bounded_timeout, default=C.DEFAULT_TIMEOUT,
                      help="per-call timeout in seconds (default %(default)s)")
    diag.set_defaults(handler=cmd_diagnose)

    guest = sub.add_parser("guest-cmd", help="deliver one whitelisted in-guest inspection command")
    guest.add_argument("--instance-id", required=True)
    guest.add_argument("--region-id", required=True)
    guest.add_argument("--command-key", required=True,
                       help="one of: {0}".format(", ".join(sorted(C.GUEST_COMMANDS))))
    guest.add_argument("--path", help="absolute path, required by the keys that take one")
    guest.add_argument("--os", choices=["linux", "windows"],
                       help="instance operating system family, defaults to the key's own family")
    guest.add_argument("--confirm", action="store_true",
                       help="set only after the customer approved this single command")
    guest.add_argument("--timeout", type=bounded_timeout, default=C.DEFAULT_TIMEOUT,
                       help="per-call timeout in seconds (default %(default)s)")
    guest.set_defaults(handler=cmd_guest_cmd)

    snap = sub.add_parser("snapshot", help="create one snapshot before a manual change")
    snap.add_argument("--disk-id", required=True)
    snap.add_argument("--snapshot-name", help="optional name for the snapshot")
    snap.add_argument("--confirm", action="store_true",
                      help="set only after the customer accepted the billing consequence")
    snap.add_argument("--timeout", type=bounded_timeout, default=C.DEFAULT_TIMEOUT,
                      help="per-call timeout in seconds (default %(default)s)")
    snap.set_defaults(handler=cmd_snapshot)

    return parser


def _run_selftest():
    """Offline boundary locks for the pure decision / parse core (no cloud
    calls). Compound guards carry a discriminating case each so a dropped
    sub-condition would fail an assertion (verified by mutation)."""
    results = []

    def expect(name, cond):
        results.append(bool(cond))
        print(("PASS " if cond else "FAIL ") + name)
        return cond

    # --- parse_positive_number: accept a number, reject everything else ---
    expect("parse_positive_number: '5' -> 5.0", parse_positive_number("5", "x") == 5.0)
    for bad in ("0", "-1", "abc", ""):
        try:
            parse_positive_number(bad, "x")
            ok = False
        except InputError:
            ok = True
        expect("parse_positive_number rejects %r" % bad, ok)

    # --- parse_event_time: accepted formats, reject malformed ---
    expect("parse_event_time: ISO datetime", parse_event_time("2026-09-17T08:30:00").hour == 8)
    expect("parse_event_time: date-only -> midnight", parse_event_time("2026-09-17").hour == 0)
    try:
        parse_event_time("17/09/2026")
        ok = False
    except InputError:
        ok = True
    expect("parse_event_time rejects malformed", ok)

    # --- classify_symptom: keyword matching populated from real tables ---
    io_kw = C.IO_AXIS_KEYWORDS[0]
    expect("classify_symptom: io keyword surfaced in io_keywords",
           io_kw in classify_symptom(io_kw)["io_keywords"])
    expect("classify_symptom: capacity keyword routes away",
           bool(classify_symptom(C.ROUTE_AWAY_CAPACITY[0])["away"]))
    expect("classify_symptom: unrelated text -> unknown",
           classify_symptom("xyzzy nothing relevant")["primary"] == "unknown")

    # --- disk_ceiling: PL0 capacity formula, its cap, and fallbacks ---
    want20 = min(C.PL0_MAX_IOPS, C.PL0_IOPS_BASE + C.PL0_IOPS_PER_GB * 20)
    r20 = disk_ceiling(C.ESSD_CATEGORY, "PL0", 20)
    expect("disk_ceiling PL0 applies capacity formula", r20["expected_iops"] == want20)
    expect("disk_ceiling PL0 small volume capped below catalogue max",
           want20 < C.PL0_MAX_IOPS and r20["expected_iops"] < C.PL0_MAX_IOPS)
    rbig = disk_ceiling(C.ESSD_CATEGORY, "PL0", 1000)
    expect("disk_ceiling PL0 large volume clamps to the catalogue max (min cap engaged)",
           (C.PL0_IOPS_BASE + C.PL0_IOPS_PER_GB * 1000) > C.PL0_MAX_IOPS
           and rbig["expected_iops"] == C.PL0_MAX_IOPS)
    expect("disk_ceiling PL0 formula basis recorded",
           any(b.startswith("IOPS = min(") for b in r20["basis"]))
    rnone = disk_ceiling(C.ESSD_CATEGORY, "PL0", None)
    expect("disk_ceiling PL0 unknown size carries the SIZE-unknown caveat",
           C.SIZE_UNKNOWN_FALLBACK in rnone["notes"])
    r1 = disk_ceiling(C.ESSD_CATEGORY, "PL1", 100)
    expect("disk_ceiling PL1 uses table max",
           r1["expected_iops"] == C.PERFORMANCE_LEVEL_CEILINGS["PL1"]["max_iops"])
    rx = disk_ceiling(C.ESSD_CATEGORY, "PLX", 100)
    expect("disk_ceiling unknown level -> no ceiling, a note, no crash",
           rx["expected_iops"] is None and rx["expected_throughput_mbps"] is None and bool(rx["notes"]))
    rc = disk_ceiling(C.CLOUD_EFFICIENCY_CATEGORY, "", 100)
    expect("disk_ceiling legacy category -> no numeric ceiling + note",
           rc["expected_iops"] is None and bool(rc["notes"]))
    expect("disk_ceiling empty category -> note, no crash",
           bool(disk_ceiling("", "", None)["notes"]))

    # --- reduce_points: peak of present fields, junk/None/empty tolerated ---
    peak, cnt, _ = reduce_points([{"Maximum": "1200"}, {"Average": 500}, {}, "junk", {"Maximum": None}])
    expect("reduce_points: max of present fields skips junk/None", peak == 1200.0 and cnt == 2)
    expect("reduce_points: empty -> (None, 0)", reduce_points([]) == (None, 0, "no numeric field"))
    expect("reduce_points: all-nonnumeric -> None", reduce_points([{"Maximum": "n/a"}])[0] is None)

    # --- datapoints_of / parse_metric_spec ---
    expect("datapoints_of: json string parsed", datapoints_of({"Datapoints": '[{"Maximum": 3}]'}) == [{"Maximum": 3}])
    expect("datapoints_of: missing key -> []", datapoints_of({}) == [])
    expect("parse_metric_spec: known kind split", parse_metric_spec("m:iops") == ("m", "iops"))
    expect("parse_metric_spec: unknown kind kept whole", parse_metric_spec("m:junk") == ("m:junk", None))

    # --- verdict_for: thresholds relative to the C ratios ---
    e = 1000
    expect("verdict_for at-ceiling at the saturation ratio",
           verdict_for(e, e * C.SATURATION_RATIO)[0] == C.VERDICT_AT_CEILING)
    expect("verdict_for near-ceiling between near and saturation",
           verdict_for(e, (C.NEAR_CEILING_RATIO + C.SATURATION_RATIO) / 2 * e)[0] == C.VERDICT_NEAR_CEILING)
    expect("verdict_for well-below when measured is 0 (0 valid, not missing)",
           verdict_for(e, 0)[0] == C.VERDICT_WELL_BELOW)
    expect("verdict_for indeterminate when expected <= 0", verdict_for(0, 500)[0] == C.VERDICT_INDETERMINATE)
    expect("verdict_for indeterminate when measured None", verdict_for(e, None)[0] == C.VERDICT_INDETERMINATE)

    # --- detect_periodicity: cross-day repeats only ---
    times = [datetime.datetime(2026, 9, 16, 3, 5), datetime.datetime(2026, 9, 17, 3, 10),
             datetime.datetime(2026, 9, 18, 9, 0)]
    rep = detect_periodicity(times, tolerance_minutes=30)
    expect("detect_periodicity: same time on 2 days is one repeat",
           len(rep) == 1 and rep[0]["time_of_day"] == "03:05" and len(rep[0]["days"]) == 2)
    expect("detect_periodicity: single occurrence not flagged",
           detect_periodicity([datetime.datetime(2026, 9, 16, 3, 5)]) == [])
    expect("detect_periodicity: None/empty safe", detect_periodicity(None) == [])

    passed = sum(results)
    print("SELFTEST: %s (%d/%d)" % ("PASS" if passed == len(results) else "FAIL", passed, len(results)))
    return 0 if passed == len(results) else 1


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    # Intercept before build_parser()/any subcommand-required guard so a bare
    # --selftest runs the pure assertions offline (never shadowed).
    if "--selftest" in argv:
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    handler = getattr(args, "handler", None)
    if handler is None:
        parser.print_help(sys.stderr)
        print(C.STATUS_FAIL)
        print("NEXT_ACTION: choose one of diagnose, guest-cmd, snapshot.")
        return 2
    try:
        return handler(args)
    except InputError as exc:
        _cli.warn(str(exc))
        print("")
        print("The input was rejected before any cloud call: {0}".format(exc))
        print("")
        print(C.STATUS_FAIL)
        print("NEXT_ACTION: ask the customer for the missing or corrected value; never guess an "
              "instance id, a disk id or a region.")
        return 2
    except _cli.CliError as exc:
        _cli.warn(str(exc))
        print("")
        print(C.STATUS_FAIL)
        print("NEXT_ACTION: match the reported error code against references/ram-policies.md; when "
              "it is a permission error, add the missing action to the caller's policy and retry.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
