#!/usr/bin/env python3
"""
ActionTrail LookupEvents query tool.

Invokes the Alibaba Cloud ActionTrail LookupEvents API to retrieve operation
audit events, with automatic pagination, multi-region batch querying,
colloquial time normalization and result rendering.

All OpenAPI access goes through the shared `_cli` module (dual backend:
aliyun CLI preferred, signed HTTPS fallback). No credentials are handled
directly by this script -- auth is resolved by `_cli` (CLI profile /
environment / config.json).

Usage:
    # Query write events of the Vpc service in the last 7 days
    python3 lookup_events.py --uid 1920430757916996 --region cn-hangzhou \
        --lookup-attribute 'ServiceName=Vpc' --lookup-attribute 'EventRW=Write'

    # Multi-region batch query (results merged, sorted by event time desc)
    python3 lookup_events.py --uid 1920430757916996 --region cn-hangzhou cn-shanghai \
        --lookup-attribute 'ServiceName=ALB'

    # All common regions (8 built-in hot regions; global services are
    # automatically pinned to cn-hangzhou)
    python3 lookup_events.py --uid 1920430757916996 --region all \
        --lookup-attribute 'ServiceName=Vpc' --lookup-attribute 'EventRW=Write'

    # Colloquial / Beijing-time input (normalized to UTC via -8h)
    python3 lookup_events.py --uid 1920430757916996 --region cn-hangzhou \
        --start-time '2026-06-25 10:00:00' --end-time '2026-07-02 18:00:00' \
        --lookup-attribute 'ServiceName=ALB'
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Import the shared OpenAPI helper from the same directory.
sys.path.insert(0, str(Path(__file__).parent))
from _cli import (  # noqa: E402
    __version__,
    CliError,
    call,
    call_with_retry,
    check_backend_available,
    mask_obj,
    mask_sensitive,
    mask_text,
    session_id,  # noqa: F401  (ensures the shared session-id is initialized)
)

API_ACTION = "LookupEvents"

# Beijing timezone (UTC+8)
BEIJING_TZ = timezone(timedelta(hours=8))

# Global services: events for these ServiceNames are recorded ONLY in
# cn-hangzhou, so they are force-routed there regardless of --region.
GLOBAL_SERVICES = {
    "AasCustomer", "AasSub", "Ims", "Ram", "ResourceManager",
    "Cdn", "Cen",
}

# Common public regions expanded from `--region all` (domestic + overseas hot).
DEFAULT_ALL_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen",
    "cn-hongkong", "cn-zhangjiakou", "cn-qingdao", "ap-southeast-1",
]

# Known-valid public region whitelist (validation only; unknown regions are
# warned about but still attempted). Only official public-cloud region ids
# belong here -- do NOT add non-public ids, they would mislead users.
KNOWN_REGIONS = set(DEFAULT_ALL_REGIONS) | {
    "cn-huhehaote", "cn-wulanchabu", "cn-heyuan", "cn-guangzhou",
    "cn-chengdu", "ap-southeast-2", "ap-southeast-3", "ap-southeast-5",
    "ap-southeast-6", "ap-southeast-7", "ap-northeast-1", "ap-northeast-2",
    "eu-central-1", "eu-west-1", "us-east-1", "us-west-1", "me-east-1",
    "me-central-1", "na-south-1",
}

# Per-region pagination safety cap (stop paginating beyond it, truncated=True).
MAX_PAGES_PER_REGION = 200


# ---------- Input validation & time normalization ----------

UID_PATTERN = re.compile(r"^\d{5,25}$")
ISO_UTC_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


def _arg_error(message: str) -> None:
    """Argument-validation failure: print to stderr and exit with code 2.

    Exit-code contract (see SKILL.md Error Handling):
    0 = success or partial success, 1 = all regions failed / fatal error,
    2 = invalid arguments.
    """
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(2)


def _validate_uid(uid: str) -> str:
    uid = (uid or "").strip()
    if not UID_PATTERN.match(uid):
        _arg_error(f"invalid --uid (must be 5-25 digits), got: {uid!r}")
    return uid


def _normalize_time(raw: str, field: str) -> str:
    """
    Normalize the many time forms a user may supply to ISO8601 UTC
    (YYYY-MM-DDThh:mm:ssZ).

    Supported inputs (values without a timezone are treated as Beijing time):
      - 2026-07-02T08:19:40Z          (already UTC, returned as-is)
      - 2026-07-02T16:19:40+08:00     (with offset, converted to UTC)
      - 2026-07-02 16:19:40           (no timezone -> Beijing time)
      - 2026-07-02 16:19               (no seconds -> padded with :00)
      - 2026-07-02                     (date only -> 00:00:00 Beijing time)
    """
    if not raw:
        return None
    s = raw.strip()

    # Case 1: already a canonical UTC string.
    if ISO_UTC_PATTERN.match(s):
        return s

    # Case 2: carries a +08:00 / -05:00 style offset.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            # No timezone: interpret as Beijing time.
            dt = dt.replace(tzinfo=BEIJING_TZ)
        utc_dt = dt.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        pass

    # Case 3: manually parse common formats.
    fmts = ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
            "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y/%m/%d"]
    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=BEIJING_TZ)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            continue

    _arg_error(
        f"--{field} time format cannot be parsed: {raw!r}. "
        "Supported: ISO8601 (e.g. 2026-07-02T08:19:40Z) or Beijing time "
        "(e.g. '2026-07-02 16:19:40')"
    )
    return None  # unreachable; keeps type-checkers happy


def _canonical_api_time(value) -> str:
    """Best-effort conversion of the StartTime/EndTime value echoed by a
    LookupEvents response into canonical ISO8601 UTC; returns "" when the
    value is missing or unparseable (callers then fall back to the legacy
    placeholder wording, preserving the degradation semantics)."""
    if value in (None, ""):
        return ""
    s = str(value).strip()
    # Already canonical ISO8601 UTC.
    if ISO_UTC_PATTERN.match(s):
        return s
    # Numeric epoch form (seconds or milliseconds, depending on API version).
    if re.fullmatch(r"\d{10,13}", s):
        try:
            num = int(s)
            if len(s) >= 13:
                num /= 1000
            return datetime.fromtimestamp(num, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ")
        except (ValueError, OSError, OverflowError):
            return ""
    # Any other ISO8601 variant with an explicit offset.
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return ""


def _extract_service_name(lookup_attrs: list) -> str:
    """Extract the ServiceName value from lookup-attribute entries (used for
    global-service detection); tolerates surrounding whitespace."""
    for a in lookup_attrs or []:
        s = (a or "").strip()
        if s.startswith("ServiceName=") and "=" in s:
            return s.split("=", 1)[1].strip()
    return ""


def _resolve_regions(regions: list, service_name: str) -> list:
    """
    Expand the --region argument:
      - 'all' expands to DEFAULT_ALL_REGIONS
      - if ServiceName hits a global service, force ['cn-hangzhou']
        (with a stderr warning)
      - dedupe while preserving order
      - unknown regions are warned about but kept
    """
    if service_name in GLOBAL_SERVICES:
        if regions and regions != ["cn-hangzhou"]:
            print(
                f"WARNING: ServiceName={service_name} is a global service; its events "
                f"are recorded only in cn-hangzhou. Ignoring --region {regions} and "
                f"forcing cn-hangzhou",
                file=sys.stderr,
            )
        return ["cn-hangzhou"]

    expanded = []
    for r in regions:
        if r == "all":
            expanded.extend(DEFAULT_ALL_REGIONS)
        else:
            expanded.append(r)

    # Dedupe while preserving order.
    seen = set()
    result = []
    for r in expanded:
        if r not in seen:
            seen.add(r)
            result.append(r)
            if r not in KNOWN_REGIONS:
                print(f"WARNING: --region {r!r} is not in the known region whitelist, "
                      "please double-check the spelling", file=sys.stderr)
    return result


# ---------- Core query ----------

def _build_base_params(start_time: str, end_time: str, max_results: int,
                       direction: str, lookup_attributes: list) -> dict:
    """Build the non-pagination LookupEvents request parameters."""
    params = {}
    if start_time:
        params["StartTime"] = start_time
    if end_time:
        params["EndTime"] = end_time
    params["MaxResults"] = str(min(max(1, max_results), 50))
    if direction:
        params["Direction"] = direction

    for i, attr in enumerate(lookup_attributes or [], 1):
        if '=' in attr:
            key, value = attr.split('=', 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                params[f"LookupAttribute.{i}.Key"] = key
                params[f"LookupAttribute.{i}.Value"] = value
    return params


def _lookup_single_region(uid: str, region: str,
                          start_time: str, end_time: str,
                          max_results: int, direction: str,
                          lookup_attributes: list,
                          profile: str = None) -> dict:
    """Single-region query (serial NextToken pagination with a page cap,
    transient-failure retry via call_with_retry, truncation flag)."""
    base_params = _build_base_params(start_time, end_time, max_results,
                                     direction, lookup_attributes)
    all_events = []
    next_token = None
    page_count = 0
    truncated = False
    api_start_time = None
    api_end_time = None

    try:
        while page_count < MAX_PAGES_PER_REGION:
            page_count += 1
            page_params = dict(base_params)
            if next_token:
                page_params["NextToken"] = next_token

            # Each page is retried on transient failures (429 / 5xx / network)
            # by call_with_retry; hard failures raise CliError.
            data = call_with_retry(
                lambda p=dict(page_params), r=region, pr=profile: call(
                    "actiontrail", API_ACTION, p, region=r, profile=pr,
                ),
                label=f"actiontrail/{API_ACTION}@{region}",
            )

            # The first page echoes the effective query window (StartTime /
            # EndTime); capture it so default (omitted) time ranges can be
            # reported with the real values instead of placeholders.
            if page_count == 1:
                api_start_time = data.get("StartTime")
                api_end_time = data.get("EndTime")

            events = data.get("Events", [])
            if isinstance(events, list):
                # Tag the source region so the merged multi-region list keeps
                # provenance information.
                for e in events:
                    e.setdefault("_queryRegion", region)
                all_events.extend(events)

            next_token = data.get("NextToken")
            if not next_token:
                break
            time.sleep(0.2)
    except CliError as e:
        # Single-region failure degrades to per_region.error; never aborts the
        # whole multi-region run.
        return {
            "success": False,
            "region": region,
            "error": f"API call failed [{e.code or 'error'}]: {e}",
            "events": all_events,
            "pages": page_count,
            "truncated": False,
            "api_start_time": api_start_time,
            "api_end_time": api_end_time,
        }

    # After the loop: a leftover next_token means we hit MAX_PAGES_PER_REGION,
    # so the result set is truncated.
    if next_token:
        truncated = True
        print(
            f"WARNING: [{region}] still has a NextToken after the pagination cap of "
            f"{MAX_PAGES_PER_REGION} pages; results are truncated. Consider narrowing "
            f"the time range or adding more precise LookupAttribute filters.",
            file=sys.stderr,
        )

    return {
        "success": True,
        "region": region,
        "events": all_events,
        "pages": page_count,
        "truncated": truncated,
        "api_start_time": api_start_time,
        "api_end_time": api_end_time,
    }


def lookup_events(uid: str, regions: list, start_time: str = None, end_time: str = None,
                  max_results: int = 50, direction: str = "BACKWARD",
                  lookup_attributes: list = None, profile: str = None) -> dict:
    """
    Call LookupEvents for one or more regions and merge the results.

    `regions` must already be expanded by _resolve_regions. Credentials are
    resolved entirely by `_cli` (CLI profile / env / config.json); there is no
    STS cache or internal token endpoint in this version.
    """
    per_region = {}
    all_events = []
    total_pages = 0
    partial_failures = []
    any_truncated = False
    api_start_time = None
    api_end_time = None

    for r in regions:
        sub = _lookup_single_region(
            uid, r, start_time, end_time,
            max_results, direction, lookup_attributes, profile,
        )
        per_region[r] = {
            "success": sub["success"],
            "count": len(sub.get("events", [])),
            "pages": sub.get("pages", 0),
            "truncated": sub.get("truncated", False),
        }
        if sub.get("truncated"):
            any_truncated = True
        if not sub["success"]:
            per_region[r]["error"] = sub.get("error", "")
            partial_failures.append(r)
        # Keep the effective-window echo of the first region that returned one
        # (all regions of one run share the same request window).
        if api_start_time is None and sub.get("api_start_time"):
            api_start_time = sub["api_start_time"]
        if api_end_time is None and sub.get("api_end_time"):
            api_end_time = sub["api_end_time"]
        all_events.extend(sub.get("events", []))
        total_pages += sub.get("pages", 0)

    # Sort by event time (BACKWARD = newest first); guard against None/missing
    # eventTime.
    reverse = (direction == "BACKWARD")
    all_events.sort(key=lambda e: e.get("eventTime") or "", reverse=reverse)

    return {
        "success": len(partial_failures) == 0,
        "partial": len(partial_failures) > 0 and len(partial_failures) < len(regions),
        "failed_regions": partial_failures,
        "truncated": any_truncated,
        "events": all_events,
        "total_count": len(all_events),
        # Explicitly requested window wins; otherwise surface the effective
        # window echoed by the API response, degrading to the legacy
        # placeholder wording when it is absent or unparseable.
        "start_time": start_time or _canonical_api_time(api_start_time)
        or "(default: last 7 days)",
        "end_time": end_time or _canonical_api_time(api_end_time)
        or "(now)",
        "pages": total_pages,
        "regions": regions,
        "per_region": per_region,
    }


def resolve_uid(profile: str = None) -> str:
    """Derive the account UID from the active credential via STS
    GetCallerIdentity, with transient-failure retry. Returns "" on failure."""
    try:
        body = call_with_retry(
            lambda pr=profile: call("sts", "GetCallerIdentity", {}, profile=pr),
            label="sts/GetCallerIdentity",
        )
        return str(body.get("AccountId", "") or "")
    except CliError as e:
        print(f"[WARN] STS GetCallerIdentity failed: {e} -- continuing with "
              "degradation (UID unresolvable)", file=sys.stderr)
        return ""


# ---------- Output rendering (12-column table) ----------

def _bj_time(iso_utc: str) -> str:
    """UTC ISO8601 -> Beijing-time string."""
    if not iso_utc:
        return "-"
    try:
        dt = datetime.strptime(iso_utc[:19], "%Y-%m-%dT%H:%M:%S")
        return (dt + timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return iso_utc


def _operator_cell(ui: dict) -> str:
    """Render `userName / principalId (type)`; never display accountId
    (fallback to accountId only when root + missing principalId).

    principalId / accountId are sensitive identifiers and are masked here at
    the cell level (same mask_sensitive contract as the JSON path); numeric
    values are normalized to str first so rendering cannot crash on them.
    """
    if not ui:
        return "-"
    utype = ui.get("type", "") or ""
    name = ui.get("userName", "") or ""
    pid = ui.get("principalId", "") or ""
    aid = ui.get("accountId", "") or ""
    pid = str(pid)
    aid = str(aid)

    if utype == "root-account":
        left = "root"
        idpart = pid or aid  # fall back to accountId when principalId missing
    elif utype == "assumed-role":
        role = ui.get("roleName", "") or ""
        sess = ((ui.get("sessionContext", {}) or {}).get("sessionName", "")) or ""
        if role and sess:
            left = f"{role}:{sess}"
        elif role:
            left = role
        elif name:
            # userName for assumed-role is usually already "RoleName:sessionName"
            left = name
        else:
            left = sess or "-"
        idpart = pid
    else:
        left = name
        idpart = pid

    # Mask the identifier part (principalId or the accountId fallback):
    # a `<uid>:<session>` principalId masks its uid segment; a plain uid /
    # accountId is masked as a whole.
    if idpart:
        head, sep, tail = idpart.partition(":")
        idpart = str(mask_sensitive(head)) + sep + tail

    parts = [p for p in [left, idpart] if p]
    core = " / ".join(parts)
    return f"{core} ({utype})" if utype else core


def _session_cell(ui: dict) -> str:
    s = ((ui or {}).get("sessionContext", {}) or {}).get("sessionName", "")
    return s or "-"


def _is_failure_event(event: dict) -> tuple:
    """
    Unified failure judgment (shared by the table and the summary).

    Only two explicit failure signals are used (to avoid misjudging
    responseElements.Code=200/Success/0 as failures):
      1. errorCode non-empty -> use the errorCode itself as the label
      2. errorMessage non-empty -> label with 'Failed' (API reported an error
         without a code)

    Returns: (is_failed, err_label); success events return (False, "").
    """
    if not isinstance(event, dict):
        return False, ""
    err_code = (event.get("errorCode") or "").strip()
    if err_code:
        return True, err_code
    err_msg = (event.get("errorMessage") or "").strip()
    if err_msg:
        return True, "Failed"
    return False, ""


def _resource_cell(event: dict) -> str:
    """referencedResources, with `❌ errorCode` appended for failure events
    (failure judgment in _is_failure_event)."""
    ref = event.get("referencedResources") or {}
    parts = []
    # ActionTrail has two historical shapes: dict or list[{resourceType, resourceName}]
    if isinstance(ref, dict):
        for k, v in ref.items():
            if not v:
                continue
            short = k.split("::")[-1] if "::" in k else k
            if isinstance(v, list):
                parts.append(f"{short}={','.join(v)}")
            else:
                parts.append(f"{short}={v}")
    elif isinstance(ref, list):
        by_type = {}
        for r in ref:
            t = (r.get("resourceType") or "").split("::")[-1] or "Resource"
            n = r.get("resourceName") or ""
            if n:
                by_type.setdefault(t, []).append(n)
        for k, v in by_type.items():
            parts.append(f"{k}={','.join(v)}")
    body = "; ".join(parts)

    is_failed, err_label = _is_failure_event(event)
    if is_failed:
        body = f"{body} ❌ {err_label}" if body else f"❌ {err_label}"
    return body or "-"


def format_event_table(events: list) -> str:
    """Render the 12-column Markdown table."""
    if not events:
        return "(no event records)"

    lines = [
        "| Event Time (Beijing) | Event Name | Event ID | Cloud Service | Event Source | Region | Operator (Type) | Read/Write | Event Type | Source IP | Role Session | Related Resources |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for e in events:
        ui = e.get("userIdentity", {}) or {}
        lines.append(
            "| " + " | ".join([
                _bj_time(e.get("eventTime", "")),
                e.get("eventName", "-") or "-",
                e.get("eventId", "-") or "-",
                e.get("serviceName", "-") or "-",
                e.get("eventSource", "-") or "-",
                e.get("acsRegion", "-") or "-",
                _operator_cell(ui),
                e.get("eventRW", "-") or "-",
                e.get("eventType", "-") or "-",
                e.get("sourceIpAddress", "-") or "-",
                _session_cell(ui),
                _resource_cell(e),
            ]) + " |"
        )
    return "\n".join(lines)


def format_summary_oneline(events: list) -> str:
    """One-line summary: total / success-failure counts / top operators
    (failure judgment identical to the table's _resource_cell)."""
    if not events:
        return "Total 0 events."
    total = len(events)
    failed = sum(1 for e in events if _is_failure_event(e)[0])
    succ = total - failed
    op_count = {}
    for e in events:
        ui = e.get("userIdentity", {}) or {}
        key = ui.get("userName") or ui.get("principalId") or ui.get("accountId") or "unknown"
        op_count[key] = op_count.get(key, 0) + 1
    top_ops = sorted(op_count.items(), key=lambda x: -x[1])[:3]
    ops_str = ", ".join(f"{k}({v})" for k, v in top_ops)
    return f"Total {total} events (success {succ}, failed {failed}); top operators: {ops_str}."


# ---------- Friendly Summary (plain-language report for non-technical users) ----------

# Total line budget for the Friendly Summary block (all sections combined).
FRIENDLY_MAX_LINES = 20


def _plain_filters(lookup_attrs: list) -> str:
    """Translate effective Key=Value filters into plain language, e.g.
    ServiceName=Vpc + EventRW=Write -> "write operations on VPC resources"."""
    frags = []
    rw = ""
    svc = ""
    for attr in lookup_attrs or []:
        if "=" not in attr:
            continue
        k, v = attr.split("=", 1)
        k, v = k.strip(), v.strip()
        if k == "EventRW":
            rw = v
        elif k == "ServiceName":
            svc = v
        elif k == "EventName":
            frags.append(f"the '{v}' operation")
        elif k == "Username":
            frags.append(f"operations performed by user '{v}'")
        elif k == "ResourceType":
            frags.append(f"operations on resources of type '{v}'")
        elif k == "ResourceName":
            frags.append(f"operations on the resource '{v}'")
        elif k == "EventAccessKeyId":
            frags.append("operations made with one specific AccessKey")
        else:
            frags.append(f"{k} = {v}")
    head = ""
    if rw and svc:
        head = f"{rw.lower()} operations on {svc} resources"
    elif rw:
        head = f"{rw.lower()} operations"
    elif svc:
        head = f"all operations on {svc} resources"
    parts = ([head] if head else []) + frags
    return ", ".join(parts)


def _friendly_window(start_time: str, end_time: str,
                     start_provided: bool, end_provided: bool) -> str:
    """Human-readable description of the effective query window
    (Beijing time), e.g. "the last 3 days (Beijing time)"."""
    if not start_time or start_time.startswith("(default"):
        return "the recent period chosen by the service (no explicit time window was given)"
    try:
        s = datetime.strptime(start_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return f"{start_time} ~ {end_time}"
    if end_time and not str(end_time).startswith("("):
        try:
            e = datetime.strptime(end_time[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        except ValueError:
            e = None
    else:
        e = datetime.now(timezone.utc)
    if e is None or e <= s:
        return f"{_bj_time(start_time)} onward (Beijing time)"
    dur = e - s
    days = round(dur.total_seconds() / 86400)
    if days >= 1:
        dur_label = f"{days} day" if days == 1 else f"{days} days"
    else:
        hours = max(1, round(dur.total_seconds() / 3600))
        dur_label = f"{hours} hour" if hours == 1 else f"{hours} hours"
    sb, eb = _bj_time(start_time), _bj_time(end_time)
    if start_provided or end_provided:
        return f"from {sb} to {eb}, Beijing time ({dur_label})"
    # API-echoed effective window ending around "now" -> describe as "last N days".
    if (datetime.now(timezone.utc) - e) <= timedelta(hours=2):
        return f"the last {dur_label} (Beijing time, up to now)"
    return f"from {sb} to {eb}, Beijing time ({dur_label})"


def _friendly_summary(result: dict, ctx: dict) -> str:
    """Build the plain-language Friendly Summary (four fixed sections,
    English, plain text, capped at FRIENDLY_MAX_LINES). All facts are
    computed from the actual result -- never templated boilerplate."""
    events = result.get("events") or []
    total = result.get("total_count", len(events))
    lines = []

    # 1) Query Scope
    lines.append("## Query Scope")
    src = "provided by you" if ctx["uid_source"] == "provided" else "derived from the active credential"
    lines.append(f"- Account: UID {ctx['uid']} ({src})")
    lines.append(f"- Regions checked: {', '.join(result.get('regions') or [])}")
    lines.append("- Time window: " + _friendly_window(
        result.get("start_time"), result.get("end_time"),
        ctx["start_provided"], ctx["end_provided"]))
    plain = _plain_filters(ctx.get("lookup_attrs") or [])
    lines.append("- What was looked for: " + (plain or "all audit events (no filters applied)"))

    # 2) Key Findings
    lines.append("## Key Findings")
    if total == 0:
        lines.append("- No matching events found in this scope.")
        reasons = []
        if ctx.get("uid_mismatch"):
            reasons.append("the account checked differs from the one you asked about")
        if ctx.get("lookup_attrs"):
            reasons.append("the filters may be narrower than intended")
        reasons.append("the time window may not cover when it happened")
        lines.append("- Possible reason: " + "; ".join(reasons) + ".")
    else:
        lines.append(f"- Total events found: {total}")
        n_read = sum(1 for e in events if (e.get("eventRW") or "").lower() == "read")
        n_write = sum(1 for e in events if (e.get("eventRW") or "").lower() == "write")
        n_other = total - n_read - n_write
        rw_line = f"- Read/Write breakdown: {n_read} read, {n_write} write"
        if n_other:
            rw_line += f", {n_other} other"
        lines.append(rw_line + ".")
        op_count = {}
        svc_count = {}
        for e in events:
            ui = e.get("userIdentity") or {}
            op = (ui.get("userName") or ui.get("principalId")
                  or ui.get("accountId") or "unknown")
            op_count[str(op)] = op_count.get(str(op), 0) + 1
            svc = e.get("serviceName") or "unknown"
            svc_count[svc] = svc_count.get(svc, 0) + 1
        top_ops = ", ".join(f"{k} ({v})" for k, v in
                            sorted(op_count.items(), key=lambda x: -x[1])[:3])
        lines.append(f"- Most active operators: {top_ops}")
        top_svcs = ", ".join(f"{k} ({v})" for k, v in
                             sorted(svc_count.items(), key=lambda x: -x[1])[:3])
        lines.append(f"- Cloud services involved: {top_svcs}")
        failed = sum(1 for e in events if _is_failure_event(e)[0])
        if failed:
            lines.append(f"- ❌ Failed operations: {failed}")

    # 3) Points to Note (only when something deserves attention)
    notes = []
    if result.get("truncated"):
        notes.append("- The result list is very long and was cut off, so some older "
                     "events are not shown here; the numbers above may be lower than "
                     "the real totals.")
    if result.get("partial"):
        fr = ", ".join(result.get("failed_regions") or [])
        notes.append(f"- Some regions could not be checked ({fr}), so this report "
                     "covers only the regions that succeeded.")
    if ctx.get("uid_mismatch"):
        notes.append("- The account actually checked is different from the account "
                     "number you gave, so these results may not describe the account "
                     "you intended.")
    if ctx.get("unknown_service"):
        notes.append("- The service name used as a filter is not recognized; the "
                     "empty result may come from that rather than from a real lack "
                     "of activity.")
    if ctx.get("global_lock"):
        notes.append("- This type of account-level activity is recorded only in "
                     "cn-hangzhou, so the query was automatically focused there.")
    if notes:
        lines.append("## Points to Note")
        lines.extend(notes)

    # 4) Suggested Next Steps
    steps = []
    if result.get("truncated"):
        steps.append("- Narrow the time window or add a more precise filter "
                     "(such as one specific operation name) to see the full picture.")
    if total == 0:
        steps.append("- Widen the time window or relax the filters and query again.")
        if ctx.get("unknown_service"):
            steps.append("- Double-check the cloud service name spelling.")
    else:
        failed = sum(1 for e in events if _is_failure_event(e)[0])
        if failed:
            steps.append(f"- Drill into the {failed} failed operation(s) to see "
                         "which ones matter to you.")
        if result.get("truncated") or total >= 100:
            steps.append("- For long-term or full-volume audit needs, consider "
                         "delivering ActionTrail events to SLS (Log Service) instead.")
        if len(steps) < 3:
            steps.append("- Filter by one specific operator, operation, or resource "
                         "to zoom in on what you care about.")
    steps = steps[:3]
    lines.append("## Suggested Next Steps")
    lines.extend(steps)

    return "\n".join(lines[:FRIENDLY_MAX_LINES])


# ---------- CLI ----------

def main():
    parser = argparse.ArgumentParser(
        description="ActionTrail LookupEvents query tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single region
  python3 lookup_events.py --uid 1891593397989760 --region cn-hangzhou \\
      --lookup-attribute 'ServiceName=ALB' --lookup-attribute 'EventName=DeleteLoadBalancer'

  # Multi region
  python3 lookup_events.py --uid 1891593397989760 --region cn-hangzhou cn-shanghai \\
      --lookup-attribute 'ServiceName=ALB'

  # All common regions (8 built-in hot regions)
  python3 lookup_events.py --uid 1891593397989760 --region all \\
      --lookup-attribute 'ServiceName=Vpc' --lookup-attribute 'EventRW=Write'

  # Colloquial time input (treated as Beijing time)
  python3 lookup_events.py --uid 1891593397989760 --region cn-hangzhou \\
      --start-time '2026-06-25 10:00:00' --end-time '2026-07-02 18:00:00' \\
      --lookup-attribute 'ServiceName=ALB'

  # UID auto-derived from the active credential (STS GetCallerIdentity)
  python3 lookup_events.py --region cn-hangzhou \\
      --lookup-attribute 'ServiceName=Ram'
        """,
    )
    parser.add_argument("--uid", default=None,
                        help="Account UID (5-25 digits). Optional: when omitted it is "
                             "auto-derived via STS GetCallerIdentity")
    parser.add_argument("--region", required=True, nargs="+",
                        help="Region id(s); multiple allowed; 'all' expands to the built-in "
                             "common regions; global services are pinned to cn-hangzhou")
    parser.add_argument("--start-time",
                        help="Start time (ISO8601 UTC, or Beijing time like "
                             "'2026-07-02 16:19:40'; no timezone => Beijing time)")
    parser.add_argument("--end-time",
                        help="End time (same formats as --start-time)")
    parser.add_argument("--max-results", type=int, default=50,
                        help="Max results per page (1-50, default 50)")
    parser.add_argument("--direction", default="BACKWARD", choices=["FORWARD", "BACKWARD"],
                        help="Sort direction (default BACKWARD = newest first)")
    parser.add_argument("--lookup-attribute", action="append", default=[],
                        help="Lookup filter in Key=Value form (up to 2 may be given)")
    parser.add_argument("--json", action="store_true",
                        help="Emit raw JSON (for agent consumption); sensitive fields masked")
    parser.add_argument("--summary", action="store_true",
                        help="Append a one-line summary after the table "
                             "(total / success-failure / top operators)")
    parser.add_argument("--filter-event", action="append", default=[],
                        help="Filter by eventName keyword (substring, case-insensitive, "
                             "multiple values are ORed), e.g. --filter-event Eip --filter-event Nat")
    parser.add_argument("--filter-resource-type", default=None,
                        help="Filter by referencedResources.resourceType (exact match), "
                             "e.g. ACS::VPC::EIPAddress")
    parser.add_argument("--profile", default=None,
                        help="Credential profile name passed through to the OpenAPI backend")

    args = parser.parse_args()

    # Filter out malformed --lookup-attribute entries BEFORE numbering: a valid
    # entry is `Key=Value` with non-empty key and value. Dropped entries are
    # warned on stderr; the surviving list is numbered 1..N contiguously by
    # _build_base_params (gaps in LookupAttribute.N would make the whole
    # request fail with InvalidParameter).
    clean_attrs = []
    for attr in args.lookup_attribute:
        if "=" in attr:
            k, v = attr.split("=", 1)
            if k.strip() and v.strip():
                clean_attrs.append(attr)
                continue
        print(f"WARNING: dropping malformed --lookup-attribute {attr!r} "
              "(expected non-empty Key=Value)", file=sys.stderr)
    args.lookup_attribute = clean_attrs

    # Ensure a usable backend exists before any API interaction.
    check_backend_available()

    # GetCallerIdentity is invoked unconditionally (also backs related-API
    # coverage); the derived UID auto-fills --uid and cross-checks it.
    derived_uid = resolve_uid(args.profile)
    if args.uid:
        uid = _validate_uid(args.uid)
        uid_source = "provided"
        if derived_uid and derived_uid != uid:
            print(
                "=" * 72 + "\n"
                "ACCOUNT MISMATCH WARNING: the provided --uid "
                f"{uid} does NOT match the UID derived from the active "
                f"credential ({derived_uid}). The query will run against the "
                "credential's account, so results may be empty or unexpected.\n"
                + "=" * 72,
                file=sys.stderr,
            )
    else:
        uid = _validate_uid(derived_uid) if derived_uid else ""
        uid_source = "derived"
        if not uid:
            raise SystemExit(
                "ERROR: --uid was not provided and could not be derived from the "
                "active credential (STS GetCallerIdentity failed). Pass --uid "
                "explicitly, or configure valid credentials."
            )
        print(f"[INFO] --uid not provided; derived from credential: {uid}",
              file=sys.stderr)

    start_utc = _normalize_time(args.start_time, "start-time") if args.start_time else None
    end_utc = _normalize_time(args.end_time, "end-time") if args.end_time else None

    if len(args.lookup_attribute) > 2:
        print("WARNING: LookupAttribute supports at most 2 conditions; "
              "the extra ones are ignored", file=sys.stderr)
        args.lookup_attribute = args.lookup_attribute[:2]

    service_name = _extract_service_name(args.lookup_attribute)
    regions = _resolve_regions(args.region, service_name)
    if not regions:
        _arg_error("--region expanded to an empty list")

    result = lookup_events(
        uid=uid,
        regions=regions,
        start_time=start_utc,
        end_time=end_utc,
        max_results=args.max_results,
        direction=args.direction,
        lookup_attributes=args.lookup_attribute,
        profile=args.profile,
    )

    # Unknown ServiceName values are NOT rejected by the API (LookupEvents
    # returns an empty Events list with a 200); surface an explicit warning so
    # an empty result is not silently mistaken for "nothing happened".
    if service_name and result.get("total_count", 0) == 0:
        print(
            f"WARNING: no events matched ServiceName={service_name!r}. ServiceName "
            "values are case-sensitive; verify it against references/service-mapping.md "
            "(an unknown ServiceName yields an empty result, not an API error).",
            file=sys.stderr,
        )

    # Client-side filtering: --filter-event / --filter-resource-type
    # (a second pass over whatever the API returned).
    if args.filter_event or args.filter_resource_type:
        keywords = [k.lower() for k in args.filter_event] if args.filter_event else []
        rt_filter = args.filter_resource_type

        def _match(event):
            if keywords:
                en = (event.get("eventName") or "").lower()
                if not any(kw in en for kw in keywords):
                    return False
            if rt_filter:
                refs = event.get("referencedResources") or {}
                if isinstance(refs, dict):
                    if not any(rt_filter in k for k in refs.keys()):
                        return False
                elif isinstance(refs, list):
                    if not any((r.get("resourceType") or "") == rt_filter for r in refs):
                        return False
                else:
                    return False
            return True

        result['events'] = [e for e in result['events'] if _match(e)]
        result['total_count'] = len(result['events'])

    # Extra masking literals for mask_text (same treatment as the --json path):
    # the effective UID, the credential UID, every userIdentity.accountId
    # actually seen in the events, and every userIdentity.principalId (the
    # uid segment before ':' for `<uid>:<session>` forms), so the
    # table/summary/JSON can never leak a naked principalId/accountId —
    # matching the cell-level masking of the Operator (Type) column.
    extra_ids = {uid, derived_uid}
    for e in result.get("events", []):
        ui = e.get("userIdentity") or {}
        aid = ui.get("accountId") or ""
        if aid:
            extra_ids.add(str(aid))
        pid = str(ui.get("principalId") or "")
        if pid:
            head = pid.partition(":")[0]
            if head:
                extra_ids.add(head)
    mask_extra = tuple(x for x in extra_ids if x)

    if args.json:
        # Mask sensitive identifiers before emitting; mask_text is a safety net
        # over the serialized dump (catches AK-like tokens in unkeyed fields).
        # The account UIDs are passed as extra literals so they are also masked
        # wherever they appear inside arbitrary strings (principalId / ARN / ...).
        dump = json.dumps(mask_obj(result), indent=2, ensure_ascii=False)
        dump = mask_text(dump, extra=mask_extra)
        # The top-level uid echo is the ONE intentionally plaintext identifier
        # in the contract: it is re-attached AFTER masking, so the uid literal
        # embedded inside `events` (accountId / principalId / ARN) stays masked
        # while the contract-level value remains machine-readable.
        final = json.loads(dump)
        final["uid"] = uid
        final["uid_source"] = uid_source
        # Self-describing query context for the next-stage agent: the effective
        # filters (after malformed entries were dropped) and the sort direction.
        final["lookup_attributes"] = list(args.lookup_attribute)
        final["direction"] = args.direction
        print(json.dumps(final, indent=2, ensure_ascii=False))
        # Exit-code contract: 0 = success OR partial success (some regions
        # failed), 1 = all regions failed — identical to the table mode.
        sys.exit(0 if (result['success'] or result.get('partial')) else 1)

    if not result['success'] and not result.get('partial'):
        print(f"\nERROR: {result.get('error', 'unknown')}", file=sys.stderr)
        for r, info in (result.get('per_region') or {}).items():
            if not info['success']:
                print(f"  [{r}] {info.get('error', '')}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print("ActionTrail Event Query Results")
    print(f"{'='*60}")
    print(f"  UID: {uid} ({'provided' if uid_source == 'provided' else 'derived from credential'})")
    print(f"  Regions: {', '.join(result['regions'])}"
          + (f"  (partial failures: {result['failed_regions']})" if result.get('partial') else ""))
    print(f"  Time range (UTC): {result['start_time']} ~ {result['end_time']}")
    print(f"  Lookup attributes: {', '.join(args.lookup_attribute) if args.lookup_attribute else 'none'}")
    print(f"  Total events: {result['total_count']}")
    print(f"  Total pages fetched: {result['pages']}")
    if result.get('truncated'):
        truncated_regions = [r for r, info in (result.get('per_region') or {}).items()
                             if info.get('truncated')]
        print(f"  WARNING: results truncated: {', '.join(truncated_regions)} hit the "
              f"pagination cap of {MAX_PAGES_PER_REGION} pages; narrow the time range "
              "or add more precise LookupAttribute filters")
    print(f"{'='*60}\n")

    if result['events']:
        # Table and summary text go through mask_text with the same extra
        # literals as the --json path, so principalId / accountId never leak
        # in plaintext in the default (table) mode either. The 12-column
        # structure is untouched — only identifier values are masked.
        print(mask_text(format_event_table(result['events']), extra=mask_extra))
        if args.summary:
            print()
            print(mask_text(format_summary_oneline(result['events']), extra=mask_extra))
    else:
        print("(no events matched the given conditions)")

    # Friendly Summary: a plain-language report for non-technical users,
    # computed from the actual result. Table mode only (--summary keeps its
    # one-line contract; --json stays structured). Same mask_text contract.
    if not args.summary:
        friendly_ctx = {
            "uid": uid,
            "uid_source": uid_source,
            "uid_mismatch": bool(args.uid and derived_uid and derived_uid != uid),
            "lookup_attrs": args.lookup_attribute,
            "start_provided": bool(args.start_time),
            "end_provided": bool(args.end_time),
            "unknown_service": bool(service_name and result.get("total_count", 0) == 0),
            "global_lock": bool(service_name in GLOBAL_SERVICES),
        }
        print("\n" + mask_text(_friendly_summary(result, friendly_ctx), extra=mask_extra))

    sys.exit(0)


if __name__ == "__main__":
    main()
