#!/usr/bin/env python3
"""Single entry point for ECS public network quality and bandwidth saturation diagnosis.

Subcommands:
  preflight  confirm the configured credential profile works and record the account tag;
  collect    gather read-only cloud facts: instance to public IP mapping, bandwidth peak and
             billing mode, EIP and shared bandwidth package settings, optional metric series;
  judge      decide whether measured outbound traffic reached the effective peak, with the
             reading, the threshold, and the time window;
  guide      print the exact measurement command for the customer to run inside their own
             instance, plus what to paste back; nothing is executed by this skill;
  report     assemble findings, evidence, limitations, confidence, and next actions.

Every subcommand prints JSON (report and guide print text) plus a STATUS / NEXT_ACTION pair. The
scripts are read-only: they send no mutating request, run no command in any guest, and never invent
a value. A missing identifier is reported as a limitation instead of being guessed.
"""
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys

import _cli
import sts_token
from _constants import (
    BILLING_MODE_FACTS,
    CMS_API_VERSION,
    CMS_PRODUCT,
    CONCLUSIONS,
    ECS_API_VERSION,
    ECS_PRODUCT,
    HANDOFF_RULES,
    HOSTNAME_SHAPED_VALUES,
    KBPS_PER_MBPS,
    MAX_INSTANCES_DESCRIBED,
    MTR_DEFAULT_COUNT,
    MTR_MAX_COUNT,
    NEAR_LIMIT_RATIO,
    PING_DEFAULT_COUNT,
    PING_MAX_COUNT,
    PING_MAX_PACKET_SAMPLES,
    PING_MAX_PACKET_SIZE,
    PING_MIN_PACKET_SIZE,
    PROBE_MAX_PORT,
    PROBE_MIN_PORT,
    PROBE_TARGET_PATTERN,
    PROBE_TOOLS,
    QUERY_TIMEOUT_SECONDS,
    SATURATION_CONSECUTIVE_POINTS,
    SATURATION_RATIO,
    SKILL_NAME,
    STATUS_DEGRADED,
    STATUS_FAIL,
    STATUS_OK,
    UNIT_TO_MBPS,
    VERDICT_NEAR_LIMIT,
    VERDICT_NOT_SATURATED,
    VERDICT_SATURATED,
    VERDICT_UNKNOWN,
    VPC_API_VERSION,
    VPC_PRODUCT,
)

SHELL_UNSAFE_CHARACTERS = ";|&<>$`*\"'(){}[]\\!\n\r\t"
METRIC_VALUE_FIELDS = ("Maximum", "Average", "Minimum", "Value", "value")
TARGET_PATTERN = re.compile(PROBE_TARGET_PATTERN)


def shell_unsafe(text):
    return any(character in text for character in SHELL_UNSAFE_CHARACTERS)


def as_int(value):
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def as_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def nested_list(container, key, subkey):
    """Read the {Key: {SubKey: [rows]}} envelope these APIs use."""
    section = container.get(key) if isinstance(container, dict) else None
    if isinstance(section, dict):
        rows = section.get(subkey)
    else:
        rows = section
    if isinstance(rows, dict):
        return [rows]
    if isinstance(rows, list):
        return rows
    return []


def string_values(container, key, subkey):
    raw = container.get(key) if isinstance(container, dict) else None
    if isinstance(raw, dict):
        raw = raw.get(subkey)
    if raw is None:
        return []
    if isinstance(raw, str):
        return [raw]
    values = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            value = item.get("IpAddress") or item.get("Value")
            if value:
                values.append(str(value))
        elif item is not None:
            values.append(str(item))
    return values


def emit(payload, next_action):
    json.dump(payload, sys.stdout, indent=2, sort_keys=True, default=str)
    sys.stdout.write("\n")
    sys.stdout.write("STATUS: {0}\n".format(payload.get("status", STATUS_FAIL)))
    sys.stdout.write("NEXT_ACTION: {0}\n".format(next_action))


def load_json_file(path, notes=None):
    """Read a JSON document written by an earlier step.

    The trailing STATUS / NEXT_ACTION lines of a redirected run are tolerated: only the leading JSON
    document is decoded.
    """
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except (IOError, OSError) as exc:
        message = "[WARN] could not read {0}: {1}".format(path, _cli.redact_text(str(exc)))
        sys.stderr.write(message + "\n")
        if notes is not None:
            notes.append(message)
        return None
    starts = [position for position in (text.find("{"), text.find("[")) if position != -1]
    if not starts:
        message = "[WARN] {0} holds no JSON document".format(path)
        sys.stderr.write(message + "\n")
        if notes is not None:
            notes.append(message)
        return None
    try:
        return json.JSONDecoder().raw_decode(text[min(starts):])[0]
    except ValueError as exc:
        message = "[WARN] could not parse {0}: {1}".format(path, _cli.redact_text(str(exc)))
        sys.stderr.write(message + "\n")
        if notes is not None:
            notes.append(message)
        return None


def read_text_file(path, notes=None):
    if not path:
        return None
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return _cli.redact_text(handle.read())
    except (IOError, OSError) as exc:
        message = "[WARN] could not read {0}: {1}".format(path, _cli.redact_text(str(exc)))
        sys.stderr.write(message + "\n")
        if notes is not None:
            notes.append(message)
        return None


def cmd_preflight(args):
    return sts_token.main([])


def summarize_instance(row):
    eip = row.get("EipAddress") if isinstance(row.get("EipAddress"), dict) else {}
    return {
        "instance_id": row.get("InstanceId"),
        "instance_name": row.get("InstanceName"),
        "status": row.get("Status"),
        "instance_type": row.get("InstanceType"),
        "instance_network_type": row.get("InstanceNetworkType"),
        "zone_id": row.get("ZoneId"),
        "internet_charge_type": row.get("InternetChargeType"),
        "internet_max_bandwidth_out_mbps": as_int(row.get("InternetMaxBandwidthOut")),
        "internet_max_bandwidth_in_mbps": as_int(row.get("InternetMaxBandwidthIn")),
        "public_ips": string_values(row, "PublicIpAddress", "IpAddress"),
        "private_ips": string_values(row, "InnerIpAddress", "IpAddress"),
        "eip_allocation_id": eip.get("AllocationId"),
        "eip_address": eip.get("IpAddress"),
        "vpc_id": (row.get("VpcAttributes") or {}).get("VpcId") if isinstance(row.get("VpcAttributes"), dict) else None,
    }


def describe_instances(region_id, extra_params, notes):
    params = {"RegionId": region_id, "PageSize": str(MAX_INSTANCES_DESCRIBED)}
    params.update(extra_params)
    payload = _cli.call_optional(
        ECS_PRODUCT, "DescribeInstances", params, timeout=QUERY_TIMEOUT_SECONDS, notes=notes)
    if payload is None:
        return []
    return [summarize_instance(row) for row in nested_list(payload, "Instances", "Instance")]


def summarize_eip(row):
    return {
        "allocation_id": row.get("AllocationId"),
        "ip_address": row.get("IpAddress"),
        "bandwidth_mbps": as_float(row.get("Bandwidth")),
        "internet_charge_type": row.get("InternetChargeType"),
        "status": row.get("Status"),
        "business_status": row.get("BusinessStatus"),
        "bound_instance_id": row.get("InstanceId"),
        "bandwidth_package_id": row.get("BandwidthPackageId"),
    }


def summarize_package(row):
    return {
        "bandwidth_package_id": row.get("BandwidthPackageId"),
        "name": row.get("Name"),
        "bandwidth_mbps": as_float(row.get("Bandwidth")),
        "internet_charge_type": row.get("InternetChargeType"),
        "status": row.get("Status"),
        "business_status": row.get("BusinessStatus"),
        "service_location": row.get("ServiceLocation"),
    }


def parse_datapoints(payload, notes):
    """Convert a CloudMonitor body into timestamp plus value points, without assuming field names."""
    raw = payload.get("Datapoints") if isinstance(payload, dict) else None
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except ValueError:
            notes.append("[WARN] metric body could not be parsed as a data point list")
            return None
    rows = raw if isinstance(raw, list) else []
    points = []
    used_fields = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        value = None
        field = None
        for candidate in METRIC_VALUE_FIELDS:
            if candidate in item:
                value = as_float(item[candidate])
                field = candidate
                break
        if field and field not in used_fields:
            used_fields.append(field)
        points.append({
            "timestamp_ms": item.get("timestamp") or item.get("Timestamp"),
            "value": value,
            "source_field": field,
            "raw": item,
        })
    if not points:
        notes.append(
            "[WARN] the metric query returned no usable data points; keep the raw request id and "
            "re-read the series from the console monitoring page")
        return None
    return {"count": len(points), "value_fields_seen": used_fields, "points": points}


def cmd_collect(args):
    _cli.announce()
    notes = []
    facts = {
        "command": "collect",
        "skill": SKILL_NAME,
        "session_id": _cli.SESSION_ID,
        "user_agent": _cli.USER_AGENT,
        "api_versions": {"ecs": ECS_API_VERSION, "vpc": VPC_API_VERSION, "cms": CMS_API_VERSION},
        "region_id": args.region_id,
        "requested": {"instance_id": args.instance_id, "public_ip": args.public_ip,
                      "eip_allocation_id": args.eip_allocation_id,
                      "bandwidth_package_id": args.bandwidth_package_id},
        "instances": [],
        "instance_attribute": None,
        "eips": [],
        "shared_bandwidth_packages": [],
        "metrics": None,
        "limitations": notes,
    }
    if not args.region_id:
        notes.append("RegionId is required and is never inferred from an IP address.")
        facts["status"] = STATUS_FAIL
        emit(facts, "Ask for the region plus the instance id or public IP, then rerun collect.")
        return 1

    rows = []
    if args.instance_id:
        if any(args.instance_id.startswith(prefix) for prefix in HOSTNAME_SHAPED_VALUES):
            notes.append(
                "'{0}' has the shape of an OS host name rather than an instance id, so it is unlikely "
                "to match. Ask for the i-... id or the public IP.".format(args.instance_id))
        rows = describe_instances(args.region_id, {"InstanceIds": json.dumps([args.instance_id])}, notes)
        if not rows:
            notes.append(
                "No instance matched that id in {0}. Check the region and the id, and remember that "
                "instance ids are not host names.".format(args.region_id))
    elif args.public_ip:
        rows = describe_instances(args.region_id, {"PublicIpAddresses": json.dumps([args.public_ip])}, notes)
        if not rows:
            notes.append(
                "No instance in {0} owns that address as a fixed public IP. If the address is an EIP, "
                "give the instance id or the allocation id instead; a private address such as "
                "192.168.x.x cannot be used to judge public bandwidth.".format(args.region_id))
    else:
        rows = describe_instances(args.region_id, {}, notes)
        notes.append("No instance id or public IP was given, so the region inventory was listed instead.")

    facts["instances"] = rows[:MAX_INSTANCES_DESCRIBED]
    facts["instance_count"] = len(rows)

    if len(rows) == 1:
        instance_id = rows[0].get("instance_id")
        attribute = _cli.call_optional(
            ECS_PRODUCT, "DescribeInstanceAttribute", {"InstanceId": instance_id},
            timeout=QUERY_TIMEOUT_SECONDS, notes=notes)
        if isinstance(attribute, dict):
            facts["instance_attribute"] = {
                "instance_id": attribute.get("InstanceId") or instance_id,
                "instance_type": attribute.get("InstanceType"),
                "internet_charge_type": attribute.get("InternetChargeType"),
                "internet_max_bandwidth_out_mbps": as_int(attribute.get("InternetMaxBandwidthOut")),
                "internet_max_bandwidth_in_mbps": as_int(attribute.get("InternetMaxBandwidthIn")),
                "instance_network_type": attribute.get("InstanceNetworkType"),
                "status": attribute.get("Status"),
            }

    eip_params = {"RegionId": args.region_id, "PageSize": str(MAX_INSTANCES_DESCRIBED)}
    if args.eip_allocation_id:
        eip_params["AllocationId"] = args.eip_allocation_id
    eip_payload = _cli.call_optional(
        VPC_PRODUCT, "DescribeEipAddresses", eip_params, timeout=QUERY_TIMEOUT_SECONDS, notes=notes)
    if eip_payload is not None:
        facts["eips"] = [summarize_eip(row) for row in nested_list(eip_payload, "EipAddresses", "EipAddress")]
        if not facts["eips"] and (args.public_ip or args.eip_allocation_id):
            notes.append("The EIP query returned no rows for this region, so no EIP peak is available.")
        if args.public_ip and facts["eips"]:
            matched = [eip for eip in facts["eips"] if eip.get("ip_address") == args.public_ip]
            if not matched:
                owner_ids = [row.get("instance_id") for row in rows]
                matched = [eip for eip in facts["eips"] if eip.get("bound_instance_id") in owner_ids]
            facts["eips"] = matched
            if not matched:
                notes.append(
                    "No EIP in this region carries that address, so the instance most likely uses a "
                    "fixed public IP; no EIP peak was taken into account.")

    package_payload = _cli.call_optional(
        VPC_PRODUCT, "DescribeCommonBandwidthPackages",
        {"RegionId": args.region_id, "PageSize": str(MAX_INSTANCES_DESCRIBED)},
        timeout=QUERY_TIMEOUT_SECONDS, notes=notes)
    if package_payload is not None:
        packages = [
            summarize_package(row) for row in
            nested_list(package_payload, "CommonBandwidthPackages", "CommonBandwidthPackage")]
        if args.bandwidth_package_id:
            packages = [pkg for pkg in packages
                        if pkg.get("bandwidth_package_id") == args.bandwidth_package_id]
            if not packages:
                notes.append(
                    "The shared bandwidth package {0} was not returned in {1}; check the id and the "
                    "region before using its peak.".format(args.bandwidth_package_id, args.region_id))
        else:
            notes.append(
                "Shared bandwidth packages of this region are listed as context only. A package peak "
                "is used as a ceiling only after --bandwidth-package-id names the package that serves "
                "this instance.")
        facts["shared_bandwidth_packages"] = packages

    if args.with_metrics:
        if not (args.namespace and args.metric_name):
            notes.append(
                "Metric identifiers were not supplied. This script does not guess a namespace or a "
                "metric name: read them from the console monitoring page or the metric reference and "
                "pass --namespace and --metric-name.")
        else:
            metric_params = {"Namespace": args.namespace, "MetricName": args.metric_name}
            if args.dimensions:
                metric_params["Dimensions"] = args.dimensions
            if args.start:
                metric_params["StartTime"] = args.start
            if args.end:
                metric_params["EndTime"] = args.end
            if args.period:
                metric_params["Period"] = args.period
            metric_payload = _cli.call_optional(
                CMS_PRODUCT, "DescribeMetricList", metric_params, timeout=QUERY_TIMEOUT_SECONDS, notes=notes)
            if metric_payload is not None:
                facts["metrics"] = parse_datapoints(metric_payload, notes)

    if rows:
        facts["status"] = STATUS_OK if not notes else STATUS_DEGRADED
    else:
        facts["status"] = STATUS_DEGRADED if (facts["eips"] or facts["shared_bandwidth_packages"]) else STATUS_FAIL

    if facts["status"] == STATUS_OK:
        next_action = "run judge with this file plus the observed readings or the metric series"
    elif facts["status"] == STATUS_DEGRADED:
        next_action = "resolve the listed limitations, then rerun collect; report what is missing"
    else:
        next_action = "ask the customer for the instance id or public IP and the region"
    emit(facts, next_action)
    return 0 if facts["status"] != STATUS_FAIL else 1


def parse_observed(text, notes):
    """Accept comma or newline separated epochMs=Mbps pairs."""
    samples = []
    for chunk in re.split(r"[,\n;]+", text or ""):
        chunk = chunk.strip()
        if not chunk:
            continue
        if "=" not in chunk:
            notes.append("[WARN] ignored the observation '{0}', expected epochMs=value".format(chunk))
            continue
        left, right = chunk.split("=", 1)
        timestamp = as_int(left)
        value = as_float(right)
        if timestamp is None or value is None:
            notes.append("[WARN] ignored the observation '{0}', unreadable pair".format(chunk))
            continue
        samples.append({"timestamp_ms": timestamp, "mbps": value})
    return samples


def effective_peak(facts, args, notes):
    if args.peak_mbps:
        return {"peak_mbps": float(args.peak_mbps), "basis": "supplied with --peak-mbps"}
    candidates = []
    instance = (facts.get("instances") or [{}])[0] if facts.get("instances") else {}
    attribute = facts.get("instance_attribute") or {}
    instance_peak = attribute.get("internet_max_bandwidth_out_mbps")
    if instance_peak is None:
        instance_peak = instance.get("internet_max_bandwidth_out_mbps")
    if instance_peak:
        candidates.append({
            "source": "instance public bandwidth peak",
            "value_mbps": float(instance_peak),
            "id": instance.get("instance_id"),
        })
    instance_id = instance.get("instance_id")
    for eip in facts.get("eips") or []:
        if instance_id and eip.get("bound_instance_id") not in (None, instance_id):
            continue
        if eip.get("bandwidth_mbps"):
            candidates.append({
                "source": "EIP configured peak",
                "value_mbps": float(eip["bandwidth_mbps"]),
                "id": eip.get("allocation_id") or eip.get("ip_address"),
            })
    requested = facts.get("requested") or {}
    packages = facts.get("shared_bandwidth_packages") or []
    if packages and requested.get("bandwidth_package_id"):
        for package in packages:
            if package.get("bandwidth_mbps"):
                candidates.append({
                    "source": "shared bandwidth package peak",
                    "value_mbps": float(package["bandwidth_mbps"]),
                    "id": package.get("bandwidth_package_id"),
                })
    elif packages:
        notes.append(
            "Shared bandwidth package peaks were ignored because the package serving this instance "
            "was not named during collect; rerun collect with --bandwidth-package-id to include it.")
    if not candidates:
        notes.append(
            "No configured peak was readable, so saturation cannot be judged. Supply --peak-mbps "
            "from the console, or rerun collect with the instance id.")
        return None
    lowest = min(candidates, key=lambda item: item["value_mbps"])
    if len(candidates) > 1:
        notes.append(
            "Several peaks apply to different paths. The effective ceiling is the minimum of the "
            "configured peaks, the instance specification network baseline, the billing mode cap, "
            "and the platform cap; only the configured peaks are machine readable here, so the "
            "specification baseline must be checked against the instance type family documentation.")
    return {
        "peak_mbps": lowest["value_mbps"],
        "basis": "minimum of the configured peaks: {0}".format(
            ", ".join("{0} Mbps on {1}".format(item["value_mbps"], item["id"]) for item in candidates)),
        "candidates": candidates,
    }


def _run_selftest():
    """Offline regression locks for the metric/observation parsers and the
    bandwidth-peak decision. A wrong parser feeds a wrong saturation verdict; the
    'effective peak is the minimum' rule must never flip. No cloud call."""
    import types
    rc = 0

    def expect(name, cond):
        nonlocal rc
        print(("PASS " if cond else "FAIL ") + name)
        if not cond:
            rc = 1

    # parse_datapoints: CloudMonitor body -> timestamp/value points
    notes = []
    good = parse_datapoints({"Datapoints":
        '[{"timestamp":1000,"Average":5.5},{"timestamp":2000,"Maximum":7.25}]'},
        notes)
    expect("datapoints: two rows parsed with values",
           good and good["count"] == 2
           and good["points"][0]["value"] == 5.5
           and good["points"][1]["value"] == 7.25)
    expect("datapoints: empty series -> None + a warning note",
           parse_datapoints({"Datapoints": "[]"}, notes) is None)
    expect("datapoints: unparsable body -> None, no crash",
           parse_datapoints({"Datapoints": "not-json"}, notes) is None)

    # parse_observed: epochMs=Mbps pairs, malformed ignored
    expect("observed: comma pairs parsed to timestamp/mbps",
           parse_observed("1000=5.5, 2000=7.25", [])
           == [{"timestamp_ms": 1000, "mbps": 5.5},
               {"timestamp_ms": 2000, "mbps": 7.25}])
    wn = []
    expect("observed: malformed entries ignored, warned, no samples",
           parse_observed("abc; 2000=x", wn) == [] and wn)

    # effective_peak: explicit arg wins; else minimum of configured peaks; none->None
    expect("peak: --peak-mbps supplied value honoured",
           effective_peak({}, types.SimpleNamespace(peak_mbps=200), [])
           == {"peak_mbps": 200.0, "basis": "supplied with --peak-mbps"})
    pk = effective_peak({
        "instances": [{"instance_id": "i-1",
                       "internet_max_bandwidth_out_mbps": 100}],
        "eips": [{"bandwidth_mbps": 50, "allocation_id": "eip-1"}],
        "requested": {}}, types.SimpleNamespace(peak_mbps=0), [])
    expect("peak: effective ceiling is the MINIMUM (50 not 100)",
           pk and pk["peak_mbps"] == 50.0 and len(pk["candidates"]) == 2)
    n3 = []
    expect("peak: no readable source -> None with a guidance note",
           effective_peak({}, types.SimpleNamespace(peak_mbps=0), n3) is None
           and n3)
    return rc


def cmd_judge(args):
    _cli.announce()
    notes = []
    facts = load_json_file(args.facts_file, notes) or {}
    unit = (args.unit or "mbps").strip().lower()
    if unit not in UNIT_TO_MBPS:
        notes.append("[WARN] unknown unit '{0}'; expected one of {1}".format(unit, ", ".join(sorted(UNIT_TO_MBPS))))
        result = {"command": "judge", "status": STATUS_FAIL, "limitations": notes}
        emit(result, "Pass --unit with a supported value, or restate the reading with its unit.")
        return 1
    factor = UNIT_TO_MBPS[unit]

    samples = parse_observed(args.observed, notes)
    samples.extend(parse_observed(read_text_file(args.observed_file, notes) or "", notes))
    metrics = facts.get("metrics") or {}
    metric_points = [point for point in (metrics.get("points") or []) if point.get("value") is not None]
    for point in metric_points:
        samples.append({"timestamp_ms": point.get("timestamp_ms"), "mbps": point["value"] * factor})
    if metric_points:
        notes.append(
            "{0} metric point(s) were converted with the same factor as the supplied readings, i.e. "
            "as if the series unit were '{1}'. Confirm the series unit on the console monitoring page "
            "and rerun with the matching --unit if it differs.".format(len(metric_points), unit))

    undated = [sample for sample in samples if sample.get("timestamp_ms") is None]
    if undated:
        notes.append("[WARN] {0} sample(s) carry no timestamp, so they cannot be placed in a window".format(
            len(undated)))
    window_start = args.window_start
    window_end = args.window_end
    used = samples
    if window_start is not None or window_end is not None:
        def inside(sample):
            stamp = sample.get("timestamp_ms")
            if stamp is None:
                return False
            if window_start is not None and stamp < window_start:
                return False
            if window_end is not None and stamp > window_end:
                return False
            return True
        used = [sample for sample in samples if inside(sample)]
        if len(used) != len(samples):
            notes.append("{0} of {1} samples fell outside the requested window and were dropped".format(
                len(samples) - len(used), len(samples)))
    if window_start is None and window_end is None:
        notes.append(
            "No window was requested. A saturation verdict without a time range cannot be reviewed, "
            "so state the window in the answer to the customer.")

    peak_info = effective_peak(facts, args, notes)
    values = [sample["mbps"] for sample in used]
    saturated_runs = []
    verdict = VERDICT_UNKNOWN
    threshold_mbps = None
    if peak_info and values:
        peak = peak_info["peak_mbps"]
        threshold_mbps = peak * SATURATION_RATIO
        at_or_over = [sample for sample in used if sample["mbps"] >= threshold_mbps]
        reached_peak = [sample for sample in used if sample["mbps"] >= peak]
        saturated_runs = [[sample.get("timestamp_ms"), sample.get("mbps")] for sample in at_or_over]
        if reached_peak or len(at_or_over) >= SATURATION_CONSECUTIVE_POINTS:
            verdict = VERDICT_SATURATED
        elif max(values) >= peak * NEAR_LIMIT_RATIO:
            verdict = VERDICT_NEAR_LIMIT
        else:
            verdict = VERDICT_NOT_SATURATED
    elif values and not peak_info:
        verdict = VERDICT_UNKNOWN

    result = {
        "command": "judge",
        "session_id": _cli.SESSION_ID,
        "input_unit": unit,
        "window": {"start_ms": window_start, "end_ms": window_end},
        "peak": peak_info,
        "threshold_mbps": threshold_mbps,
        "threshold_rule": "saturated when a reading reaches the configured peak, or when at least "
                          "{0} readings are at or above {1} percent of it".format(
                              SATURATION_CONSECUTIVE_POINTS, int(SATURATION_RATIO * 100)),
        "samples_used": len(used),
        "max_mbps": max(values) if values else None,
        "avg_mbps": (sum(values) / len(values)) if values else None,
        "near_limit_ratio": NEAR_LIMIT_RATIO,
        "saturated_readings": saturated_runs,
        "theoretical_download": None,
        "verdict": verdict,
        "limitations": notes,
    }
    if peak_info:
        result["theoretical_download"] = {
            "kb_per_s": round(peak_info["peak_mbps"] * KBPS_PER_MBPS, 1),
            "mb_per_s": round(peak_info["peak_mbps"] / 8.0, 2),
            "note": "1 Mbps is quoted to customers as about {0} KB/s; the decimal figure is about "
                    "125 kB/s, so treat the two as the same order of magnitude.".format(KBPS_PER_MBPS),
        }

    if verdict == VERDICT_UNKNOWN:
        result["status"] = STATUS_DEGRADED
        next_action = ("collect the configured peak and at least one timestamped reading, or take the "
                       "series from the console monitoring page for the stated window")
    else:
        result["status"] = STATUS_OK if not notes else STATUS_DEGRADED
        next_action = "report the verdict with the reading, the threshold and the window, then continue " \
                      "with the quality area or the matching handoff"
    emit(result, next_action)
    return 0


def validate_target(target):
    text = (target or "").strip()
    if not TARGET_PATTERN.match(text) or shell_unsafe(text):
        raise ValueError(
            "the target must be one hostname or IP address, without spaces, shell metacharacters, "
            "or extra arguments")
    return text


def parse_packet_sizes(spec):
    if not spec:
        return [None]
    sizes = []
    for chunk in spec.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        size = as_int(chunk)
        if size is None or size < PING_MIN_PACKET_SIZE or size > PING_MAX_PACKET_SIZE:
            raise ValueError("packet sizes must be integers between {0} and {1}".format(
                PING_MIN_PACKET_SIZE, PING_MAX_PACKET_SIZE))
        sizes.append(size)
    if not sizes:
        return [None]
    if len(sizes) > PING_MAX_PACKET_SAMPLES:
        raise ValueError("at most {0} packet sizes may be listed".format(PING_MAX_PACKET_SAMPLES))
    return sizes


def build_guide_commands(args):
    """Build the exact measurement command strings from validated parts only.

    The result is text for the customer to run inside their own instance. This skill is read-only:
    it never executes any of it and never sends it to the cloud.
    """
    target = validate_target(args.target)
    default_count = PING_DEFAULT_COUNT if args.tool == "ping" else MTR_DEFAULT_COUNT
    limit = PING_MAX_COUNT if args.tool == "ping" else MTR_MAX_COUNT
    count = args.count or default_count
    if count < 1 or count > limit:
        raise ValueError("probe count must be between 1 and {0} for {1}".format(limit, args.tool))

    commands = []
    if args.tool == "ping":
        base = ["ping", "-n", "-c", str(count)]
        if args.interval:
            if args.interval < 1 or args.interval > 5:
                raise ValueError("the ping interval must be between 1 and 5 seconds")
            base.extend(["-i", str(args.interval)])
        for size in parse_packet_sizes(args.packet_size):
            one = list(base)
            if size:
                one.extend(["-s", str(size)])
            one.append(target)
            commands.append(" ".join(one))
    else:
        one = ["mtr", "-r", "-n", "-c", str(count)]
        if args.tcp_port:
            if args.tcp_port < PROBE_MIN_PORT or args.tcp_port > PROBE_MAX_PORT:
                raise ValueError("the tcp probe port must be between {0} and {1}".format(
                    PROBE_MIN_PORT, PROBE_MAX_PORT))
            one.extend(["--tcp", "-P", str(args.tcp_port)])
        elif args.udp:
            one.append("--udp")
        one.append(target)
        commands.append(" ".join(one))

    for command in commands:
        if shell_unsafe(command):
            raise ValueError("the assembled probe command contained an unsafe character")
    return commands, target, count


def cmd_guide(args):
    _cli.announce()
    try:
        commands, target, count = build_guide_commands(args)
    except ValueError as exc:
        print("REFUSED: {0}".format(exc))
        print("The measurements this skill suggests are ping and mtr only, built from validated "
              "options. Everything else is answered with manual steps instead of a command line.")
        print("STATUS: {0}".format(STATUS_DEGRADED))
        print("NEXT_ACTION: restate the request within that whitelist, or ask the customer which "
              "reading is actually missing.")
        return 1

    print("Customer-side measurement, to run inside the instance. This skill is read-only: it does "
          "not execute the command and cannot see the output until it is pasted back.")
    print("")
    print("target : {0}".format(target))
    print("tool   : {0}, {1} round(s)".format(args.tool, count))
    for command in commands:
        print("command: {0}".format(command))
    if len(commands) > 1:
        print("")
        print("One packet size per command. Run them one at a time and keep the outputs separate, so "
              "the size at which transfers start failing stays visible.")
    print("")
    print("Paste back: the complete output, unedited, plus the wall clock time it was taken, to the "
          "minute. A reading without a timestamp cannot be placed in the incident window.")
    print("Read it with references/network-quality-bandwidth__mtr-interpretation.md: attribute only the first hop that keeps "
          "losing down to the destination, treat a middle hop whose successor recovers as ICMP rate "
          "limiting, and do not read TCP probe loss as application loss.")
    print("")
    print("If the tool is not installed, say so rather than installing it: installation is a human "
          "action, and the Windows equivalent is the resource monitor sorted by network usage "
          "during the incident.")
    print("STATUS: {0}".format(STATUS_OK))
    print("NEXT_ACTION: send the command above to the customer, then interpret the pasted output and "
          "run report with --pasted-output-file.")
    return 0


def match_handoffs(symptom):
    text = (symptom or "").lower()
    matched = []
    for rule in HANDOFF_RULES:
        for keyword in rule["keywords"]:
            if keyword.lower() in text:
                matched.append({"code": rule["code"], "target": rule["target"], "note": rule["note"]})
                break
    return matched


def confidence_of(facts, judgement, pasted_text):
    if judgement.get("verdict") in (VERDICT_SATURATED, VERDICT_NEAR_LIMIT, VERDICT_NOT_SATURATED):
        return "high (cloud side reading and a documented rule agree)"
    if (facts.get("metrics") or {}).get("count"):
        return "medium (a cloud side metric series exists, but no verdict against a confirmed peak)"
    if pasted_text:
        return "low (rests on output the customer pasted, which this skill cannot verify)"
    return "low (no reading backs the conclusion yet)"


def evidence_lines(facts, judgement, pasted_text):
    lines = []
    for instance in facts.get("instances") or []:
        lines.append(
            "DescribeInstances: {0} type={1} status={2} billing={3} peak_out={4} Mbps peak_in={5} Mbps "
            "public_ips={6}".format(
                instance.get("instance_id"), instance.get("instance_type"), instance.get("status"),
                instance.get("internet_charge_type"), instance.get("internet_max_bandwidth_out_mbps"),
                instance.get("internet_max_bandwidth_in_mbps"), ",".join(instance.get("public_ips") or [])))
    attribute = facts.get("instance_attribute") or {}
    if attribute:
        lines.append(
            "DescribeInstanceAttribute: billing={0} peak_out={1} Mbps peak_in={2} Mbps network={3}".format(
                attribute.get("internet_charge_type"), attribute.get("internet_max_bandwidth_out_mbps"),
                attribute.get("internet_max_bandwidth_in_mbps"), attribute.get("instance_network_type")))
    for eip in facts.get("eips") or []:
        lines.append(
            "DescribeEipAddresses: {0} ip={1} peak={2} Mbps status={3} billing={4} bound_to={5} "
            "package={6}".format(
                eip.get("allocation_id"), eip.get("ip_address"), eip.get("bandwidth_mbps"),
                eip.get("status"), eip.get("internet_charge_type"), eip.get("bound_instance_id"),
                eip.get("bandwidth_package_id")))
    for package in facts.get("shared_bandwidth_packages") or []:
        lines.append(
            "DescribeCommonBandwidthPackages: {0} peak={1} Mbps status={2} billing={3}".format(
                package.get("bandwidth_package_id"), package.get("bandwidth_mbps"),
                package.get("status"), package.get("internet_charge_type")))
    metrics = facts.get("metrics") or {}
    if metrics.get("count"):
        lines.append(
            "DescribeMetricList: {0} points, value field(s) {1}".format(
                metrics.get("count"), ", ".join(metrics.get("value_fields_seen") or [])))
    if judgement:
        peak = (judgement.get("peak") or {}).get("peak_mbps")
        lines.append(
            "judge: verdict={0} peak={1} Mbps threshold={2} Mbps max_observed={3} Mbps "
            "samples={4} window={5}..{6}".format(
                judgement.get("verdict"), peak, judgement.get("threshold_mbps"),
                judgement.get("max_mbps"), judgement.get("samples_used"),
                (judgement.get("window") or {}).get("start_ms"),
                (judgement.get("window") or {}).get("end_ms")))
        download = judgement.get("theoretical_download") or {}
        if download.get("kb_per_s"):
            lines.append("conversion: {0} Mbps is about {1} KB/s ({2} MB/s)".format(
                peak, download.get("kb_per_s"), download.get("mb_per_s")))
    if pasted_text:
        excerpt = [line for line in pasted_text.splitlines() if line.strip()][:40]
        lines.append("customer pasted measurement output (credential masked, truncated to 40 lines):")
        lines.extend("  " + line for line in excerpt)
    return lines


def conclusion_lines(facts, judgement, symptom):
    lines = []
    verdict = judgement.get("verdict")
    attribute = facts.get("instance_attribute") or {}
    billing = attribute.get("internet_charge_type") or (
        (facts.get("instances") or [{}])[0].get("internet_charge_type") if facts.get("instances") else None)
    if verdict == VERDICT_SATURATED:
        lines.append(CONCLUSIONS["spec_limit"])
        lines.append("Raising the peak, or moving to another billing mode, is a console action the "
                     "customer performs; this skill does not change it.")
    elif verdict == VERDICT_NEAR_LIMIT:
        lines.append(CONCLUSIONS["near_limit"])
    elif verdict == VERDICT_NOT_SATURATED:
        lines.append(CONCLUSIONS["not_limit"])
        lines.append("Continue on the quality area, or hand off on the compute and storage areas.")
    else:
        lines.append("Saturation could not be judged from the available data, so no capacity "
                     "conclusion is claimed.")
    if billing and "traffic" in str(billing).lower():
        lines.append(" ".join(BILLING_MODE_FACTS))
        lines.append(CONCLUSIONS["overdue_candidate"])
    if any(word in (symptom or "").lower() for word in ("mtu", "large packet", "packet size", "vpn")):
        lines.append(CONCLUSIONS["mtu_candidate"])
        lines.append("Both candidates must be checked before one cause is named.")
    if any(word in (symptom or "").lower() for word in ("ping", "icmp")) and verdict == VERDICT_NOT_SATURATED:
        lines.append("A fast ping only measures small ICMP latency; it does not measure bandwidth, so "
                     "it cannot rule out a capacity or path problem for larger transfers.")
    return lines


def cmd_report(args):
    _cli.announce()
    notes = []
    facts = load_json_file(args.facts_file, notes) or {}
    judgement = load_json_file(args.judge_file, notes) or {}
    pasted_text = read_text_file(args.pasted_output_file, notes)
    symptom = args.symptom or ""

    if not facts and not judgement and not pasted_text:
        print("ECS network quality and bandwidth diagnosis")
        print("No facts, judgement, or pasted customer output could be loaded, so no conclusion is "
              "produced.")
        print("STATUS: {0}".format(STATUS_FAIL))
        print("NEXT_ACTION: collect the region plus instance id or public IP first.")
        return 1

    handoffs = match_handoffs(symptom)
    body = []
    body.append("ECS network quality and bandwidth diagnosis")
    body.append("run: skill={0} session_id={1}".format(SKILL_NAME, _cli.SESSION_ID))
    body.append("scope: region={0} instance={1} window={2}".format(
        facts.get("region_id") or "-",
        (facts.get("instances") or [{}])[0].get("instance_id") if facts.get("instances") else "-",
        args.window or "-"))
    body.append("")
    body.append("FINDINGS")
    for line in conclusion_lines(facts, judgement, symptom):
        body.append("- " + line)
    body.append("")
    body.append("EVIDENCE")
    evidence = evidence_lines(facts, judgement, pasted_text)
    for line in evidence or ["- none collected"]:
        body.append(line if line.startswith("  ") else "- " + line)
    body.append("")
    body.append("NOT COVERED BY THIS RUN")
    gaps = list(facts.get("limitations") or []) + list(judgement.get("limitations") or []) + notes
    limitations = gaps + ["Customer local network, carrier path, and per-connection historical "
                          "attribution are outside cloud visibility."]
    for line in limitations:
        body.append("- " + line)
    body.append("")
    body.append("CONFIDENCE: {0}".format(confidence_of(facts, judgement, pasted_text)))
    body.append("")
    body.append("NEXT STEPS")
    body.append("- this skill (read-only): rerun collect or judge once the missing identifiers are "
                "supplied")
    body.append("- customer manual step: run the measurement printed by guide and paste the output "
                "with its timestamp, check the account balance in the billing center, and rerun the "
                "local test over a different uplink such as a mobile hotspot")
    body.append("- console action by the customer only: bandwidth peak change, billing mode change, "
                "upgrade, security group rule, WAF rule, reboot")
    for handoff in handoffs:
        body.append("- handoff: {0} ({1})".format(handoff["target"], handoff["note"]))
    if args.handoff_note:
        body.append("- handoff note: " + args.handoff_note)

    statuses = [facts.get("status"), judgement.get("status")]
    if STATUS_FAIL in statuses:
        overall = STATUS_FAIL
    elif STATUS_DEGRADED in statuses or gaps or not judgement.get("verdict"):
        overall = STATUS_DEGRADED
    else:
        overall = STATUS_OK
    body.append("")
    body.append("STATUS: {0}".format(overall))
    if overall == STATUS_OK:
        body.append("NEXT_ACTION: deliver the report above; no further cloud action is authorized.")
    else:
        body.append("NEXT_ACTION: close the listed gaps or hand the affected step over, then rerun; "
                    "do not fill a gap with an assumption.")
    sys.stdout.write("\n".join(body) + "\n")
    return 0


def build_parser():
    parser = argparse.ArgumentParser(
        prog="network_quality_bandwidth.py",
        description="Diagnose ECS public network quality and bandwidth saturation without changing anything.")
    subcommands = parser.add_subparsers(dest="command")

    preflight = subcommands.add_parser("preflight", help="verify the credential profile and record the account tag")
    preflight.set_defaults(func=cmd_preflight)

    collect = subcommands.add_parser("collect", help="gather cloud facts for one instance or the region inventory")
    collect.add_argument("--region-id", required=True, help="region of the instance, never inferred from an IP")
    collect.add_argument("--instance-id", help="i-... instance id")
    collect.add_argument("--public-ip", help="EIP or fixed public IP owned by the instance")
    collect.add_argument("--eip-allocation-id", help="narrow the EIP query to one allocation id")
    collect.add_argument("--bandwidth-package-id",
                         help="shared bandwidth package that serves this instance, used to narrow the "
                              "region listing before its peak is treated as a ceiling")
    collect.add_argument("--with-metrics", action="store_true", help="also read one CloudMonitor series")
    collect.add_argument("--namespace", help="CloudMonitor namespace, confirmed by the operator")
    collect.add_argument("--metric-name", help="CloudMonitor metric name, confirmed by the operator")
    collect.add_argument("--dimensions", help="CloudMonitor dimensions as a JSON object string")
    collect.add_argument("--period", help="aggregation period in seconds, only if confirmed")
    collect.add_argument("--start", help="series start time, epoch milliseconds")
    collect.add_argument("--end", help="series end time, epoch milliseconds")
    collect.set_defaults(func=cmd_collect)

    judge = subcommands.add_parser("judge", help="decide whether the measured rate reached the peak")
    judge.add_argument("--facts-file", help="JSON file written by collect")
    judge.add_argument("--observed", help="epochMs=value pairs, comma or newline separated")
    judge.add_argument("--observed-file", help="same format, from a file")
    judge.add_argument("--peak-mbps", type=float, help="override the configured peak")
    judge.add_argument("--unit", default="mbps", help="unit of the supplied readings: mbps kbps bps mb/s kb/s")
    judge.add_argument("--window-start", type=int, help="epoch milliseconds")
    judge.add_argument("--window-end", type=int, help="epoch milliseconds")
    judge.set_defaults(func=cmd_judge)

    guide = subcommands.add_parser(
        "guide", help="print one customer-side ping or mtr measurement; never executed by this skill")
    guide.add_argument("--tool", required=True, choices=PROBE_TOOLS)
    guide.add_argument("--target", required=True, help="hostname or IP to measure toward")
    guide.add_argument("--count", type=int, help="probe repetitions, bounded per tool")
    guide.add_argument("--packet-size", help="ping only: comma separated packet sizes for a sweep")
    guide.add_argument("--interval", type=int, help="ping only: seconds between packets, 1 to 5")
    guide.add_argument("--tcp-port", type=int, help="mtr only: TCP probe port, for example 443")
    guide.add_argument("--udp", action="store_true", help="mtr only: use UDP probing")
    guide.set_defaults(func=cmd_guide)

    report = subcommands.add_parser("report", help="assemble the evidence based report")
    report.add_argument("--facts-file", help="JSON file written by collect")
    report.add_argument("--judge-file", help="JSON file written by judge")
    report.add_argument("--pasted-output-file", help="text file holding the measurement output the customer pasted back")
    report.add_argument("--symptom", help="the customer's own wording, used for area routing")
    report.add_argument("--window", help="human readable time window of the incident")
    report.add_argument("--handoff-note", help="extra handoff context to carry into the report")
    report.set_defaults(func=cmd_report)
    return parser


def main(argv=None):
    if "--selftest" in (argv if argv is not None else sys.argv):
        return _run_selftest()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not getattr(args, "command", None):
        parser.print_help()
        return 2
    try:
        return args.func(args)
    except KeyboardInterrupt:
        sys.stderr.write("[WARN] interrupted\n")
        return 130
    except _cli.CliError as exc:
        sys.stderr.write("[WARN] {0}\n".format(exc))
        print("STATUS: {0}".format(STATUS_FAIL))
        if exc.is_permission():
            print("NEXT_ACTION: grant the missing action listed in references/ram-policies.md; the "
                  "caller received NoPermission or ImplicitDeny.")
        else:
            print("NEXT_ACTION: report the failure with its code and message; do not substitute a "
                  "guessed value or a broader permission.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
