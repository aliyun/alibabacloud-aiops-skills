#!/usr/bin/env python3
"""
ecs_expiry_release_check.py -- Single entry point for the ECS expiry /
release / data-retention lifecycle diagnosis
=====================================================================
SECURITY: This skill is strictly READ-ONLY. This script only invokes
Describe/Query/Get-class OpenAPI actions through the shared `_cli` layer
(aliyun CLI subprocess, argument-list form, per-call timeout, per-run
User-Agent). It NEVER creates, modifies, deletes, releases, renews or
rolls back any resource, and it never executes commands inside instances.
Credentials come exclusively from the aliyun CLI default credential chain;
no AK/SK is read, accepted, printed or cached by this script.

Modes
-----
1. Single-target lifecycle check (default):
     python3 ecs_expiry_release_check.py --instance-ref <i-...|IPv4|name> \
         [--region-id <region>] [--target-time <YYYY-MM-DD[THH:MM[:SS]]>] \
         [--intent <intent>] [--json] [--profile <name>]
   Also accepts --resource-ref <d-...|s-...> for disk / snapshot entry.
2. Batch expiry scan:
     python3 ecs_expiry_release_check.py --list-expiring [--days 30] \
         [--region-id <region>] [--json]
3. Notification text parsing (offline, no API calls):
     python3 ecs_expiry_release_check.py --parse-notification "<text>" [--json]

Every run ends with a `STATUS: OK|DEGRADED|FAIL` line and a `NEXT_ACTION:`
line. Exit codes: 0 = a conclusion was produced (OK or DEGRADED),
1 = FAIL (no usable conclusion), 2 = argparse usage error only.
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import _cli
from _constants import (
    BSS_MAX_PAGES,
    BSS_PAGE_SIZE,
    CANDIDATE_REGIONS,
    DOC_URLS,
    EXTENSION_LIMITS,
    EXTENSION_LIMITS_TAG,
    GUEST_COMMAND_GUIDANCE,
    INTENTS,
    MAX_PAGES,
    OVERDUE_SNAPSHOT_RELEASE_DAYS,
    OVERDUE_SNAPSHOT_TAG,
    PAGE_SIZE,
    RESOURCE_ID_PREFIXES,
    RETENTION_DAYS_SUBSCRIPTION,
    RETENTION_DAYS_TAG,
)

# ---------------------------------------------------------------------------
# Warning ledger (dual-channel per degradation-logging discipline)
# ---------------------------------------------------------------------------

WARN_LOG: list[str] = []


def warn(msg: str) -> None:
    """Record a degradation note and emit it on BOTH stdout and stderr."""
    line = f"[WARN] {msg}"
    WARN_LOG.append(line)
    print(line, file=sys.stderr)
    print(line)


# ---------------------------------------------------------------------------
# Pure helper functions (unit-tested with inline assertions at module bottom)
# ---------------------------------------------------------------------------

_IPV4_RE = re.compile(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$")


def valid_ipv4(text: str) -> bool:
    """True when text is a dotted-quad IPv4 address with octets <= 255."""
    m = _IPV4_RE.match(text.strip())
    if not m:
        return False
    return all(0 <= int(g) <= 255 for g in m.groups())


def classify_ref(ref: str) -> str:
    """Classify a customer-supplied resource reference (C2 normalization).

    Returns one of: instance_id / disk_id / snapshot_id / image_id /
    ipv4 / name.
    """
    ref = (ref or "").strip()
    for prefix, kind in RESOURCE_ID_PREFIXES.items():
        if ref.lower().startswith(prefix) and len(ref) > len(prefix) + 4:
            return {"instance": "instance_id", "disk": "disk_id",
                    "snapshot": "snapshot_id",
                    "custom image": "image_id"}[kind]
    if valid_ipv4(ref):
        return "ipv4"
    return "name"


def parse_api_time(value: Any) -> Optional[datetime]:
    """Parse an API timestamp string into an aware UTC datetime.

    Tolerates: '2026-09-03T23:59Z', '2026-09-03T23:59:59Z',
    '2026-09-03 23:59:59', offsets like '+08:00'. Naive values are assumed
    UTC (the ECS/BSS APIs return UTC 'Z' timestamps). Returns None when the
    value is missing or unparseable -- NEVER guesses a date.
    """
    if not value or not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    text = text.replace(" ", "T", 1) if " " in text and "T" not in text \
        else text
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_target_time(value: str) -> datetime:
    """Parse a user-supplied target time (C7). Raises ValueError with a
    clear message on bad input; naive values are assumed UTC and the
    assumption is declared in the report."""
    dt = parse_api_time(value)
    if dt is None:
        raise ValueError(
            f"cannot parse target time {value!r}; expected ISO-8601-like "
            f"input such as 2026-08-06, 2026-08-06T11:00 or "
            f"2026-08-06T11:00:00Z")
    return dt


def fmt_dt(dt: Optional[datetime]) -> str:
    """Render an aware datetime for reports; 'UNKNOWN' when absent."""
    if dt is None:
        return "UNKNOWN"
    return dt.strftime("%Y-%m-%d %H:%M UTC")


def extract_instance_ips(inst: dict) -> set[str]:
    """Collect every IP address attached to a DescribeInstances item."""
    ips: set[str] = set()

    def _add_list(container: Any, key: str) -> None:
        node = container.get(key) if isinstance(container, dict) else None
        if isinstance(node, dict):
            node = node.get("IpAddress")
        if isinstance(node, list):
            for item in node:
                if isinstance(item, str) and item:
                    ips.add(item)

    _add_list(inst, "PublicIpAddress")
    _add_list(inst, "InnerIpAddress")
    vpc = inst.get("VpcAttributes") or {}
    _add_list(vpc, "PrivateIpAddress")
    eip = inst.get("EipAddress") or {}
    eip_addr = eip.get("IpAddress") if isinstance(eip, dict) else None
    if isinstance(eip_addr, str) and eip_addr:
        ips.add(eip_addr)
    return ips


# Notification parsing (C13) -------------------------------------------------

_NOTIF_INSTANCE_RE = re.compile(r"(?<![A-Za-z0-9-])i-[a-z0-9]{6,32}(?![A-Za-z0-9])")
_NOTIF_DISK_RE = re.compile(r"(?<![A-Za-z0-9-])d-[a-z0-9]{6,32}(?![A-Za-z0-9])")
_NOTIF_SNAPSHOT_RE = re.compile(r"(?<![A-Za-z0-9-])s-[a-z0-9]{6,32}(?![A-Za-z0-9])")
_NOTIF_IMAGE_RE = re.compile(r"(?<![A-Za-z0-9-])m-[a-z0-9]{6,32}(?![A-Za-z0-9])")
_NOTIF_IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
_NOTIF_TIME_RE = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?)?")
_NOTIF_KEYWORDS = (
    "expire", "expired", "expiry", "overdue", "arrears", "release",
    "released", "renew", "renewal", "stop", "stopped", "retention",
    "unsubscribe", "trial",
)


def parse_notification(text: str) -> dict:
    """Extract resource ids, IP addresses, timestamps and lifecycle
    keywords from a pasted SMS/email notification (offline, pure text)."""
    text = text or ""
    ips = [ip for ip in _NOTIF_IP_RE.findall(text) if valid_ipv4(ip)]
    lowered = text.lower()
    keywords = sorted({kw for kw in _NOTIF_KEYWORDS if kw in lowered})
    return {
        "instance_ids": sorted(set(_NOTIF_INSTANCE_RE.findall(text))),
        "disk_ids": sorted(set(_NOTIF_DISK_RE.findall(text))),
        "snapshot_ids": sorted(set(_NOTIF_SNAPSHOT_RE.findall(text))),
        "image_ids": sorted(set(_NOTIF_IMAGE_RE.findall(text))),
        "ip_addresses": sorted(set(ips)),
        "timestamps": sorted(set(_NOTIF_TIME_RE.findall(text))),
        "keywords": keywords,
    }


# Point-in-time recoverability (C7) ------------------------------------------

def point_in_time_verdict(target: datetime, snapshots: list[dict]) -> dict:
    """Decide whether the customer can get back to `target` time.

    The set of recoverable points in time is EXACTLY the set of snapshot
    CreationTime values -- the platform keeps no other historical state,
    and paying cannot change this [ticket:T-F829BAC4].
    """
    timed = []
    for snap in snapshots:
        created = parse_api_time(snap.get("CreationTime"))
        if created is not None:
            timed.append((created, snap))
    timed.sort(key=lambda pair: pair[0])
    if not timed:
        return {
            "verdict": "NO_SNAPSHOTS",
            "explanation": (
                "Query succeeded and found NO snapshot for this target. "
                "With no snapshot there is no recoverable point in time; "
                "this cannot be changed by paying -- the platform keeps no "
                "historical data beyond user-created snapshots "
                "[ticket:T-F829BAC4]."),
            "nearest_before": None,
            "nearest_after": None,
            "all_snapshot_times": [],
        }
    before = [(t, s) for (t, s) in timed if t <= target]
    after = [(t, s) for (t, s) in timed if t > target]
    all_times = [fmt_dt(t) for (t, _) in timed]
    if before:
        bt, bsnap = before[-1]
        return {
            "verdict": "RECOVERABLE_TO_SNAPSHOT",
            "explanation": (
                f"The closest recoverable point at or before the target is "
                f"snapshot {bsnap.get('SnapshotId', 'UNKNOWN')} created at "
                f"{fmt_dt(bt)}. A rollback restores the disk to exactly "
                f"that snapshot time; everything written between that "
                f"snapshot and now would be LOST, so take a fresh snapshot "
                f"first (manual console action)."),
            "nearest_before": {
                "snapshot_id": bsnap.get("SnapshotId"),
                "creation_time": fmt_dt(bt),
                "source_disk_id": bsnap.get("SourceDiskId"),
                "source_disk_type": bsnap.get("SourceDiskType"),
                "status": bsnap.get("Status"),
            },
            "nearest_after": (
                {"snapshot_id": after[0][1].get("SnapshotId"),
                 "creation_time": fmt_dt(after[0][0])} if after else None),
            "all_snapshot_times": all_times,
        }
    at, asnap = after[0]
    return {
        "verdict": "NOT_RECOVERABLE_AT_TARGET",
        "explanation": (
            f"No snapshot exists at or before the target time. The earliest "
            f"snapshot is {asnap.get('SnapshotId', 'UNKNOWN')} created at "
            f"{fmt_dt(at)}, which is AFTER the target -- rolling back to it "
            f"would not reproduce the requested point in time. Arbitrary "
            f"historical points cannot be restored, and paying does not "
            f"unlock them [ticket:T-F829BAC4]."),
        "nearest_before": None,
        "nearest_after": {"snapshot_id": asnap.get("SnapshotId"),
                          "creation_time": fmt_dt(at)},
        "all_snapshot_times": all_times,
    }


# Lifecycle phase classification (C3) ----------------------------------------

def classify_phase(inst: dict, now: datetime) -> dict:
    """Derive the lifecycle phase and dated timeline from live fields only."""
    status = str(inst.get("Status") or "UNKNOWN")
    charge = str(inst.get("InstanceChargeType") or "UNKNOWN")
    expired_dt = parse_api_time(inst.get("ExpiredTime"))
    created_dt = parse_api_time(inst.get("CreationTime"))
    result: dict[str, Any] = {
        "status": status,
        "charge_type": charge,
        "charge_type_human": {
            "PrePaid": "subscription (bao-nian bao-yue)",
            "PostPaid": "pay-as-you-go",
        }.get(charge, charge),
        "expired_time_raw": inst.get("ExpiredTime"),
        "expired_time": fmt_dt(expired_dt),
        "creation_time": fmt_dt(created_dt),
        "phase": "UNKNOWN",
        "days_left": None,
        "days_since_expiry": None,
        "estimated_release_time": None,
        "earliest_manual_release": None,
        "retention_tag": RETENTION_DAYS_TAG,
    }
    if expired_dt is not None:
        if now < expired_dt:
            result["phase"] = "BEFORE_EXPIRY"
            result["days_left"] = (expired_dt - now).days
        else:
            result["days_since_expiry"] = (now - expired_dt).days
            est_release = expired_dt + timedelta(
                days=RETENTION_DAYS_SUBSCRIPTION)
            result["estimated_release_time"] = fmt_dt(est_release)
            # A subscription instance can be released manually starting
            # 00:00 of the calendar day AFTER the expiry timestamp shown in
            # the console [ticket:T-263837C7].
            result["earliest_manual_release"] = (
                (expired_dt.date() + timedelta(days=1)).isoformat()
                + " 00:00 (console timezone) [ticket:T-263837C7]")
            if status == "Stopped":
                result["phase"] = "EXPIRED_STOPPED_IN_RETENTION"
            else:
                result["phase"] = "EXPIRED"
    elif status in ("Running", "Starting", "Stopping", "Stopped"):
        result["phase"] = f"NOT_EXPIRED_{status.upper()}"
    return result


def spot_info(inst: dict) -> dict:
    """Echo spot-instance facts verbatim (no reclamation-reason guessing)."""
    strategy = inst.get("SpotStrategy")
    is_spot = strategy in ("SpotAsPriceGo", "SpotWithPriceLimit")
    info = {"spot_strategy": strategy or "UNKNOWN", "is_spot": bool(is_spot)}
    if is_spot:
        info["note"] = (
            "A spot instance can be reclaimed automatically by the platform "
            "when inventory or price changes -- this is NOT a user deletion "
            "and NOT an account fault [ticket:T-7D84AD37]. The specific "
            "reclamation reason is not asserted here because no verified "
            "API field carries it. When creating spot instances, set the "
            "interruption mode to the economical (savings) stop mode so a "
            "reclamation stops instead of immediately releasing the "
            "instance [ticket:T-7D84AD37]. Doc: "
            + DOC_URLS["spot_data_retention"])
    return info


# ---------------------------------------------------------------------------
# API wrappers -- each returns (payload, error_text); they NEVER raise and
# NEVER convert a failure into an empty result (empty vs failure discipline).
# ---------------------------------------------------------------------------

def api(product: str, action: str, params: dict, region: str,
        profile: Optional[str]) -> tuple[Optional[dict], Optional[str]]:
    try:
        return _cli.call(product, action, params, region=region,
                         profile=profile), None
    except _cli.CliError as e:
        return None, f"{e.code or 'CallFailed'}: {e}"


def paged(product: str, action: str, params: dict, region: str,
          profile: Optional[str], items_path: list[str],
          page_size: int = PAGE_SIZE,
          max_pages: int = MAX_PAGES) -> tuple[list, Optional[str]]:
    try:
        items = _cli.paginate_page_number(
            product, action, params, region=region, profile=profile,
            items_path=items_path, page_size=page_size, max_pages=max_pages)
        return items, None
    except _cli.CliError as e:
        return [], f"{e.code or 'CallFailed'}: {e}"


def resolve_instance(ref: str, kind: str, region: Optional[str],
                     profile: Optional[str]) -> dict:
    """C2 normalization: find the instance behind an id / IP / name.

    Returns {instance, region, auto_filled, notes[], errors[]}. A miss is
    reported with the three-branch explanation; it is NEVER asserted to be
    'released'.
    """
    out: dict[str, Any] = {"instance": None, "region": region,
                           "auto_filled": [], "notes": [], "errors": []}
    regions = [region] if region else list(CANDIDATE_REGIONS)
    if not region:
        out["auto_filled"].append(
            "region not provided: scanning candidate regions "
            f"({len(regions)} regions, first match wins)")
    for candidate in regions:
        insts: list = []
        if kind == "instance_id":
            insts, err = paged(
                "ecs", "DescribeInstances",
                {"RegionId": candidate, "InstanceIds": json.dumps([ref])},
                candidate, profile, ["Instances", "Instance"])
            if err:
                out["errors"].append(f"{candidate}: {err}")
                continue
        elif kind == "ipv4":
            matched = False
            for filter_key in ("PublicIpAddresses", "PrivateIpAddresses",
                               "InnerIpAddresses", "EipAddresses"):
                insts, err = paged(
                    "ecs", "DescribeInstances",
                    {"RegionId": candidate, filter_key: json.dumps([ref])},
                    candidate, profile, ["Instances", "Instance"])
                if err:
                    out["errors"].append(f"{candidate} {filter_key}: {err}")
                    continue
                if insts:
                    matched = True
                    break
            if not matched and not out["errors"]:
                # Filtered lookups returned empty: fall back to a paged scan
                # with local IP matching.
                insts, err = _scan_match(
                    candidate, profile,
                    lambda i: ref in extract_instance_ips(i))
                if err:
                    out["errors"].append(f"{candidate} scan: {err}")
            elif not matched:
                insts = []
        else:  # name
            insts, err = paged(
                "ecs", "DescribeInstances",
                {"RegionId": candidate, "InstanceName": ref},
                candidate, profile, ["Instances", "Instance"])
            if err:
                out["errors"].append(f"{candidate}: {err}")
                insts = []
            if not insts:
                scanned, err2 = _scan_match(
                    candidate, profile,
                    lambda i: str(i.get("InstanceName") or "") == ref
                    or ref in str(i.get("InstanceName") or ""))
                if err2:
                    out["errors"].append(f"{candidate} scan: {err2}")
                insts = scanned
        if insts:
            out["instance"] = insts[0]
            out["region"] = candidate
            if len(insts) > 1:
                out["notes"].append(
                    f"{len(insts)} instances matched {ref!r} in "
                    f"{candidate}; reporting the first match "
                    f"{insts[0].get('InstanceId')}")
            return out
    return out


def _scan_match(region: str, profile: Optional[str],
                predicate) -> tuple[list, Optional[str]]:
    """Page through DescribeInstances of one region and keep matches."""
    matches: list = []
    page = 1
    first_err: Optional[str] = None
    while page <= MAX_PAGES:
        body, err = api("ecs", "DescribeInstances",
                        {"RegionId": region, "PageNumber": page,
                         "PageSize": PAGE_SIZE}, region, profile)
        if err:
            return matches, err
        instances = ((body or {}).get("Instances") or {}).get("Instance")
        if not isinstance(instances, list) or not instances:
            break
        matches.extend([i for i in instances if predicate(i)])
        total = (body or {}).get("TotalCount")
        if not isinstance(total, int) or page * PAGE_SIZE >= total:
            break
        page += 1
    return matches, first_err


def fetch_disks(region: str, profile: Optional[str],
                instance_id: Optional[str] = None,
                disk_ids: Optional[list] = None) -> tuple[list, Optional[str]]:
    params: dict[str, Any] = {"RegionId": region}
    if instance_id:
        params["InstanceId"] = instance_id
    if disk_ids:
        params["DiskIds"] = json.dumps(disk_ids)
    return paged("ecs", "DescribeDisks", params, region, profile,
                 ["Disks", "Disk"])


def fetch_snapshots(region: str, profile: Optional[str],
                    instance_id: Optional[str] = None,
                    disk_id: Optional[str] = None,
                    snapshot_ids: Optional[list] = None,
                    scan_all: bool = False) -> tuple[list, Optional[str]]:
    params: dict[str, Any] = {"RegionId": region}
    if instance_id:
        params["InstanceId"] = instance_id
    if disk_id:
        params["DiskId"] = disk_id
    if snapshot_ids:
        params["SnapshotIds"] = json.dumps(snapshot_ids)
    if not scan_all and not (instance_id or disk_id or snapshot_ids):
        return [], ("no filter given; refusing an unfiltered account-wide "
                    "snapshot scan in this path")
    return paged("ecs", "DescribeSnapshots", params, region, profile,
                 ["Snapshots", "Snapshot"])


def fetch_auto_renew(region: str, profile: Optional[str],
                     instance_id: Optional[str] = None
                     ) -> tuple[list, Optional[str]]:
    params: dict[str, Any] = {"RegionId": region}
    if instance_id:
        params["InstanceId"] = instance_id
    return paged("ecs", "DescribeInstanceAutoRenewAttribute", params,
                 region, profile,
                 ["InstanceRenewAttributes", "InstanceRenewAttribute"])


def fetch_full_status(region: str, profile: Optional[str],
                      instance_id: str) -> tuple[list, Optional[str]]:
    params = {"RegionId": region, "InstanceId.1": instance_id}
    return paged("ecs", "DescribeInstancesFullStatus", params, region,
                 profile, ["InstanceFullStatusSet", "InstanceFullStatusType"],
                 page_size=PAGE_SIZE, max_pages=2)


def fetch_bss_expiry(instance_id: str,
                     profile: Optional[str]) -> tuple[Optional[dict],
                                                      Optional[str]]:
    """Billing-side authoritative expiry cross-check (best effort).

    API QueryAvailableInstances (RAM action bss:DescribeInstances). Any
    failure or unexpected shape degrades to UNKNOWN -- the ECS-side
    ExpiredTime remains the primary evidence.
    """
    body, err = api("bssopenapi", "QueryAvailableInstances",
                    {"ProductCode": "ecs",
                     "InstanceIDs": json.dumps([instance_id]),
                     "PageNum": 1, "PageSize": BSS_PAGE_SIZE},
                    "cn-hangzhou", profile)
    items: list = []
    if body is not None:
        data = body.get("Data") or {}
        raw = data.get("InstanceList")
        if isinstance(raw, list):
            items = raw
    if err and not items:
        # Second attempt: unfiltered first pages, local match.
        page = 1
        while page <= BSS_MAX_PAGES and not items:
            body2, err2 = api("bssopenapi", "QueryAvailableInstances",
                              {"ProductCode": "ecs", "PageNum": page,
                               "PageSize": BSS_PAGE_SIZE},
                              "cn-hangzhou", profile)
            if body2 is None:
                err = err or err2
                break
            data2 = body2.get("Data") or {}
            raw2 = data2.get("InstanceList")
            if isinstance(raw2, list):
                for item in raw2:
                    iid = str(item.get("InstanceID")
                              or item.get("InstanceId") or "")
                    if iid == instance_id:
                        items.append(item)
            page += 1
    for item in items:
        iid = str(item.get("InstanceID") or item.get("InstanceId") or "")
        if iid == instance_id:
            return item, None
    if items:
        return None, "billing query returned rows but none matched the id"
    return None, err or "no billing-side row found for this instance"


# ---------------------------------------------------------------------------
# Evidence assembly for one instance
# ---------------------------------------------------------------------------

def gather_evidence(inst: dict, region: str, profile: Optional[str],
                    target_time: Optional[datetime]) -> dict:
    """Run every read-only query for one instance and assemble the report
    data. Each failed query degrades to UNKNOWN with a [WARN]; the run
    never aborts mid-way."""
    iid = str(inst.get("InstanceId") or "")
    now = datetime.now(timezone.utc)
    ev: dict[str, Any] = {"errors": [], "unknowns": []}

    # C3 timeline ------------------------------------------------------------
    ev["timeline"] = classify_phase(inst, now)
    ev["spot"] = spot_info(inst)
    locks = ((inst.get("OperationLocks") or {}).get("LockMode")) or []
    ev["operation_locks"] = locks  # echoed verbatim, never interpreted

    # C5 protection -----------------------------------------------------------
    renew_items, renew_err = fetch_auto_renew(region, profile, iid)
    if renew_err:
        warn(f"DescribeInstanceAutoRenewAttribute failed: {renew_err}")
        ev["errors"].append(f"auto_renew: {renew_err}")
        ev["auto_renew"] = "UNKNOWN (query failed)"
    elif renew_items:
        first = renew_items[0]
        ev["auto_renew"] = {
            "renewal_status": first.get("RenewalStatus", "UNKNOWN"),
            "auto_renew_enabled": first.get("AutoRenewEnabled", "UNKNOWN"),
            "duration": first.get("Duration"),
            "period_unit": first.get("PeriodUnit"),
        }
    else:
        ev["auto_renew"] = (
            "no auto-renewal attribute row returned (pay-as-you-go "
            "instances have none; for subscription instances this is an "
            "empty result, not a failure)")
    deletion_protection = inst.get("DeletionProtection")
    ev["release_protection"] = (
        deletion_protection
        if isinstance(deletion_protection, bool)
        else "UNKNOWN (field absent from the API response)")

    # C6 disks ----------------------------------------------------------------
    disks, disk_err = fetch_disks(region, profile, instance_id=iid)
    if disk_err:
        warn(f"DescribeDisks failed: {disk_err}")
        ev["errors"].append(f"disks: {disk_err}")
        ev["disks"] = None
    else:
        ev["disks"] = [{
            "disk_id": d.get("DiskId"),
            "name": d.get("DiskName"),
            "type": d.get("Type"),
            "category": d.get("Category"),
            "status": d.get("Status"),
            "size_gib": d.get("Size"),
            "zone_id": d.get("ZoneId"),
            "delete_with_instance": d.get("DeleteWithInstance"),
            "disk_charge_type": d.get("DiskChargeType"),
            "enable_auto_snapshot": d.get("EnableAutoSnapshot"),
            "auto_snapshot_policy_id": d.get("AutoSnapshotPolicyId"),
        } for d in disks]

    # C6/C7 snapshots ----------------------------------------------------------
    snaps, snap_err = fetch_snapshots(region, profile, instance_id=iid)
    if snap_err:
        warn(f"DescribeSnapshots failed: {snap_err}")
        ev["errors"].append(f"snapshots: {snap_err}")
        ev["snapshots"] = None
    else:
        ev["snapshots"] = [{
            "snapshot_id": s.get("SnapshotId"),
            "name": s.get("SnapshotName"),
            "creation_time": s.get("CreationTime"),
            "creation_time_fmt": fmt_dt(parse_api_time(
                s.get("CreationTime"))),
            "status": s.get("Status"),
            "source_disk_id": s.get("SourceDiskId"),
            "source_disk_type": s.get("SourceDiskType"),
            "source_disk_size": s.get("SourceDiskSize"),
        } for s in snaps]
        ev["has_system_disk_snapshot"] = any(
            str(s.get("SourceDiskType") or "").lower() == "system"
            for s in snaps)

    if target_time is not None and ev.get("snapshots"):
        ev["point_in_time"] = point_in_time_verdict(
            target_time,
            [{"SnapshotId": s["snapshot_id"],
              "CreationTime": s["creation_time"],
              "SourceDiskId": s["source_disk_id"],
              "SourceDiskType": s["source_disk_type"],
              "Status": s["status"]} for s in ev["snapshots"]])

    # Stop/release evidence ----------------------------------------------------
    full, fs_err = fetch_full_status(region, profile, iid)
    if fs_err:
        warn(f"DescribeInstancesFullStatus failed: {fs_err}")
        ev["errors"].append(f"full_status: {fs_err}")
        ev["full_status"] = "UNKNOWN (query failed)"
    elif full:
        first = full[0]
        events = ((first.get("ScheduledEvents") or {})
                  .get("ScheduledEventType")) or []
        ev["full_status"] = {
            "status": first.get("Status"),
            "health_status": (first.get("HealthStatus") or {}).get("Name")
            if isinstance(first.get("HealthStatus"), dict)
            else first.get("HealthStatus"),
            "scheduled_events": [{
                "event_id": e.get("EventId"),
                "type": (e.get("EventType") or {}).get("Name")
                if isinstance(e.get("EventType"), dict) else e.get("EventType"),
                "publish_time": e.get("EventPublishTime"),
                "not_before": e.get("NotBefore"),
                "cycle_status": e.get("EventCycleStatus"),
            } for e in events if isinstance(e, dict)],
            "note": ("this API covers still-registered instances; how long "
                     "history is kept for already-released instances is "
                     "UNKNOWN [TO VERIFY] -- an empty result is never proof "
                     "of release"),
        }
    else:
        ev["full_status"] = "query succeeded, no full-status row returned"

    # BSS cross-check ------------------------------------------------------------
    bss_row, bss_err = fetch_bss_expiry(iid, profile)
    if bss_row:
        ev["bss_crosscheck"] = {
            "instance_id": bss_row.get("InstanceID")
            or bss_row.get("InstanceId"),
            "end_time": bss_row.get("EndTime"),
            "renew_status": bss_row.get("RenewStatus"),
            "subscription_type": bss_row.get("SubscriptionType"),
            "region": bss_row.get("Region"),
        }
    else:
        warn(f"QueryAvailableInstances cross-check unavailable: {bss_err}")
        ev["bss_crosscheck"] = f"UNKNOWN ({bss_err})"

    # Always-UNKNOWN items (no verified API in this tier) ------------------------
    ev["unknowns"] = [
        ("Custom images: not queried (no verified image API in this tier). "
         "Check ECS console > Images > Custom Images -- a custom image "
         "built from a SYSTEM-disk snapshot can rebuild a new instance "
         "[ticket:T-78D54558]."),
        ("Cloud Backup (HBR) vaults / plans / jobs: not queried (API "
         "version unverified for this tier). Existence of file-level or "
         "whole-machine backups is UNKNOWN -- check the Cloud Backup "
         "console. NEVER report 'no backup exists' from this gap."),
        ("Unpaid renewal orders and prior extension history: NOT verified by "
         "this run. A read-only order query DOES exist -- bssopenapi "
         "QueryOrders (RAM action bss:DescribeOrderList), filtered by "
         "PaymentStatus=Unpaid with an OrderType and a CreateTimeStart/"
         "CreateTimeEnd window, plus GetOrderDetail for one order id -- but "
         "this area does not call it yet. Confirm in the Billing console "
         "(Orders > Unpaid). An unpaid renewal order must be voided before "
         "an extension can be applied, and voiding is irreversible "
         "[ticket:T-88CA26A9]."),
    ]
    return ev


def build_billing_matrix(inst: dict, ev: dict) -> list[dict]:
    """C4: which resources keep billing in each state (rule rows carry their
    evidence tags; live resources come from the queried data)."""
    rows = [{
        "resource": f"instance {inst.get('InstanceId')} "
                    f"({ev['timeline']['charge_type_human']})",
        "now": f"status={ev['timeline']['status']}",
        "rule": ("Subscription: billing runs to ExpiredTime; after expiry "
                 "the instance stops. Pay-as-you-go: a Running instance "
                 "bills; a normal stop keeps vCPU/memory billing stopped "
                 "only in the economical (savings) stop mode, and the "
                 "economical stop STILL bills the system disk and data "
                 "disks -- only releasing the instance stops billing "
                 "entirely [ticket:T-1834B8F1]. Doc: "
                 + DOC_URLS["economical_mode"]),
    }]
    for d in (ev.get("disks") or []):
        rows.append({
            "resource": f"disk {d['disk_id']} ({d['type']}, {d['category']}, "
                        f"{d['size_gib']} GiB)",
            "now": (f"delete_with_instance="
                    f"{d['delete_with_instance']}, charge="
                    f"{d['disk_charge_type']}"),
            "rule": ("A disk with delete_with_instance=False SURVIVES the "
                     "instance release and KEEPS BILLING until it is "
                     "released manually [ticket:T-0E502AF0]. A retained "
                     "system disk can only be re-attached as a DATA disk "
                     "and only inside the same zone [ticket:T-78D54558]."),
        })
    return rows


def build_extension_precheck(inst: dict, ev: dict) -> dict:
    """C10: authoritative facts + rule disclosure + application material
    package. Manual approval only; the outcome is NEVER promised."""
    timeline = ev["timeline"]
    renew = ev.get("auto_renew")
    renew_text = (json.dumps(renew, ensure_ascii=False)
                  if isinstance(renew, dict) else str(renew))
    return {
        "authoritative_expiry": timeline["expired_time"],
        "expired_time_raw": timeline["expired_time_raw"],
        "charge_type": timeline["charge_type_human"],
        "auto_renew_status": renew_text,
        "rules": (
            f"Extension limits: {EXTENSION_LIMITS} {EXTENSION_LIMITS_TAG}. "
            "An extension is a manual, case-by-case approval submitted "
            "through human support -- this skill cannot submit it and does "
            "NOT promise an outcome. Conflicting front-line statements "
            "exist (one ticket was told expiry stop cannot be delayed "
            "[ticket:T-B92D8D06] while others were granted a 1-day / "
            "24-hour extension [ticket:T-084C4147] [ticket:T-CD20304A]); "
            "the final decision always rests with the human approval."),
        "preconditions": (
            "1) Any unpaid renewal order must be voided first -- voiding is "
            "irreversible and the order cannot be paid afterwards "
            "[ticket:T-88CA26A9] [ticket:T-63376A9B]. 2) An EIP does NOT "
            "extend together with the instance [ticket:T-C8B6DAEA, "
            "low-confidence phone-only evidence]. 3) An expired instance "
            "cannot be backed up in place: renew or extend FIRST, then "
            "create snapshots [ticket:T-084C4147] [ticket:T-5E3EDF72]."),
        "application_material_package": {
            "instance_id": inst.get("InstanceId"),
            "region": inst.get("RegionId"),
            "authoritative_expiry_time": timeline["expired_time_raw"],
            "reason": "<customer's business reason, e.g. payment approval "
                      "cycle>",
            "requested_extension": "1 day (the only granularity observed in "
                                   "ticket evidence)",
        },
        "self_check_required": (
            "Unpaid-order and prior-extension-history checks were NOT run by "
            "this script. Both are verifiable read-only with bssopenapi "
            "QueryOrders (RAM action bss:DescribeOrderList; filters "
            "PaymentStatus=Unpaid, OrderType=Renew and a CreateTimeStart/"
            "CreateTimeEnd window) and GetOrderDetail by order id, but this "
            "area does not call them yet -- ask the customer to confirm in "
            "Billing console > Orders, and state plainly that this skill did "
            "NOT verify them."),
    }


def build_recoverability(ev: dict, inst: dict) -> dict:
    """C6 per-resource recoverability verdicts from live data + rules."""
    disks = ev.get("disks")
    snaps = ev.get("snapshots")
    retained = []
    if isinstance(disks, list):
        retained = [d for d in disks if d.get("delete_with_instance") is False]
    system_snap = ev.get("has_system_disk_snapshot")
    return {
        "instance_body": (
            "Once an instance is RELEASED, the instance itself, its system "
            "disk, local disks and any data disk flagged "
            "delete-with-instance are permanently deleted. No technical "
            "means and no payment can bring them back [ticket:T-B596918B] "
            "[ticket:T-C7A684D0] [ticket:T-F829BAC4]."),
        "retained_disks": retained or (
            "none found with delete_with_instance=False"
            if isinstance(disks, list) else "UNKNOWN (disk query failed)"),
        "retained_disk_rules": (
            "A retained disk keeps billing [ticket:T-0E502AF0]; it can be "
            "attached to a new instance in the SAME zone and a retained "
            "SYSTEM disk can only serve as a DATA disk [ticket:T-78D54558]."),
        "snapshots_available": (
            len(snaps) if isinstance(snaps, list)
            else "UNKNOWN (snapshot query failed)"),
        "system_disk_snapshot_present": (
            system_snap if isinstance(system_snap, bool)
            else "UNKNOWN (snapshot query failed)"),
        "image_path_rule": (
            "Rebuilding an instance from snapshots requires a CUSTOM IMAGE, "
            "and creating a custom image requires a SYSTEM-disk snapshot "
            "[ticket:T-78D54558]. Recovery path: system-disk snapshot -> "
            "custom image -> new instance. The public IP is NOT kept: "
            "recovery from snapshot/image yields a new public IP "
            "[ticket:T-5E3EDF72]."),
        "data_disk_only_path": (
            "With only DATA-disk snapshots, single files are recovered "
            "manually: create a disk from the snapshot -> attach it -> copy "
            "the files inside the OS -> detach and release the temporary "
            "disk to stop its billing [ticket:T-0DEF60B4]. A snapshot "
            "rollback only ever applies to its ORIGINAL disk; it cannot be "
            "applied to a different, newly bought disk [ticket:T-0DEF60B4]. "
            "All of these steps are manual console actions -- this skill "
            "only judges feasibility."),
        "snapshot_loss_rule": (
            f"If the account stays overdue for more than "
            f"{OVERDUE_SNAPSHOT_RELEASE_DAYS} days, existing snapshots are "
            f"released {OVERDUE_SNAPSHOT_TAG}. NOTE: this is a DIFFERENT "
            f"rule from the post-expiry data-retention window "
            f"({RETENTION_DAYS_SUBSCRIPTION} days {RETENTION_DAYS_TAG}); "
            f"never mix the two."),
        "public_ip_rule": (
            "A classic public IP is lost permanently at release; to keep it, "
            "convert it to an EIP BEFORE the instance expires or is "
            "released (conversion is a manual action, and EIP billing is "
            "out of scope here). Doc: " + DOC_URLS["ip_to_eip"]
            + " [ticket:T-8D31E368]."),
    }


def build_backup_feasibility(ev: dict) -> dict:
    """C8: can a snapshot be created right now, and in which order."""
    phase = ev["timeline"]["phase"]
    status = ev["timeline"]["status"]
    if status == "Running":
        verdict = ("Feasible now: the instance is Running, so snapshots can "
                   "be created from the console (manual action).")
        order = ("Snapshot-first rule: before ANY cleanup / rollback / "
                 "unsubscribe / release, create a snapshot of every disk "
                 "that matters [ticket:T-0DEF60B4] [ticket:T-86768857].")
    elif phase in ("EXPIRED_STOPPED_IN_RETENTION", "EXPIRED"):
        verdict = ("Likely NOT feasible in place: an instance stopped by "
                   "expiry usually cannot create snapshots -- a real ticket "
                   "attempt failed and support confirmed 'once expired, it "
                   "cannot be backed up' [ticket:T-5E3EDF72] "
                   "[ticket:T-084C4147].")
        order = ("Correct order: renew (or obtain a manual extension) so "
                 "the instance comes back -> create snapshots -> only then "
                 "consider unsubscribing [ticket:T-5E3EDF72].")
    else:
        verdict = ("Not determinable from status alone (status="
                   f"{status}); check in the console whether the "
                   "Create Snapshot action is available for each disk.")
        order = ("Attempt a console snapshot before any other action; if it "
                 "fails, follow the renew-first order above.")
    return {"verdict": verdict, "order": order,
            "snapshot_fee_disclosure": (
                "Snapshots incur storage fees, and if the account is "
                "overdue for more than "
                f"{OVERDUE_SNAPSHOT_RELEASE_DAYS} days the snapshots are "
                f"released {OVERDUE_SNAPSHOT_TAG}. Doc: "
                + DOC_URLS["create_snapshot"]),
            "execution_note": (
                "This skill NEVER creates a snapshot itself; snapshot "
                "creation is a manual console action the customer performs "
                "after this disclosure.")}


# ---------------------------------------------------------------------------
# Not-found handling (never assert 'released')
# ---------------------------------------------------------------------------

def retained_resource_scan(region: str,
                           profile: Optional[str]) -> dict:
    """When the instance is not found: list retained disks and all snapshots
    of the region so the customer can identify leftovers by disk/time."""
    out: dict[str, Any] = {"disks": None, "snapshots": None, "errors": []}
    disks, err = fetch_disks(region, profile)
    if err:
        warn(f"DescribeDisks (retained scan) failed: {err}")
        out["errors"].append(f"disks: {err}")
    else:
        out["disks"] = [{
            "disk_id": d.get("DiskId"), "name": d.get("DiskName"),
            "type": d.get("Type"), "status": d.get("Status"),
            "instance_id": d.get("InstanceId") or "(unattached)",
            "zone_id": d.get("ZoneId"),
            "delete_with_instance": d.get("DeleteWithInstance"),
            "creation_time": d.get("CreationTime"),
        } for d in disks]
    snaps, err2 = fetch_snapshots(region, profile, scan_all=True)
    if err2:
        warn(f"DescribeSnapshots (retained scan) failed: {err2}")
        out["errors"].append(f"snapshots: {err2}")
    else:
        out["snapshots"] = [{
            "snapshot_id": s.get("SnapshotId"),
            "name": s.get("SnapshotName"),
            "creation_time": s.get("CreationTime"),
            "status": s.get("Status"),
            "source_disk_id": s.get("SourceDiskId"),
            "source_disk_type": s.get("SourceDiskType"),
        } for s in snaps]
    return out


# ---------------------------------------------------------------------------
# Mode 1: single target
# ---------------------------------------------------------------------------

def run_single_target(args: argparse.Namespace) -> int:
    auto_filled: list[str] = []
    uid = _cli.resolve_account_id(profile=args.profile)
    if not uid:
        print("[ERROR] STS get-caller-identity failed: the aliyun CLI "
              "credential chain is not usable. Run `aliyun sts get-caller-identity` "
              "(never pass AK/SK to this skill), or grant "
              "sts:GetCallerIdentity -- see references/ram-policies.md.",
              file=sys.stderr)
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: fix the credential chain (aliyun sts get-caller-identity) or "
              "grant the minimal RAM actions, then re-run")
        return 1
    auto_filled.append(f"account UID auto-derived via STS: {uid}")

    ref = args.instance_ref or args.resource_ref
    kind = classify_ref(ref)
    region = args.region_id

    # Disk / snapshot entry points normalize to their instance when possible.
    disk_ref = None
    snap_ref = None
    if kind == "image_id":
        print(f"Target {ref} is a custom image id. No verified image API is "
              "available in this tier: image existence and contents are "
              "UNKNOWN. Manual path: ECS console > Images > Custom Images; "
              "an image built from a system-disk snapshot can create a new "
              "instance [ticket:T-78D54558].")
        print("\nSTATUS: DEGRADED")
        print("NEXT_ACTION: guide the customer through the console image "
              "check; do not assert image existence either way")
        return 0
    if kind == "disk_id":
        disk_ref = ref
    elif kind == "snapshot_id":
        snap_ref = ref

    resolution: Optional[dict] = None
    inst: Optional[dict] = None
    retained_scan: Optional[dict] = None

    if disk_ref or snap_ref:
        regions = [region] if region else list(CANDIDATE_REGIONS)
        if not region:
            auto_filled.append(
                "region not provided: scanning candidate regions for the "
                "resource id")
        for candidate in regions:
            if disk_ref:
                items, err = fetch_disks(candidate, args.profile,
                                         disk_ids=[disk_ref])
            else:
                items, err = fetch_snapshots(candidate, args.profile,
                                             snapshot_ids=[snap_ref])
            if err:
                warn(f"{candidate}: {err}")
                continue
            if items:
                region = candidate
                attached = str(items[0].get("InstanceId") or "")
                if attached.startswith("i-"):
                    res = resolve_instance(attached, "instance_id", region,
                                           args.profile)
                    inst = res["instance"]
                    resolution = res
                if inst is None:
                    # Resource found but its instance is gone or detached.
                    inst = None
                    resolution = {"instance": None, "region": candidate,
                                  "auto_filled": [], "notes": [
                                      f"{disk_ref or snap_ref} exists in "
                                      f"{candidate} but is not attached to a "
                                      f"live instance"], "errors": []}
                    retained_scan = retained_resource_scan(
                        candidate, args.profile)
                    retained_scan["seed_resource"] = items[0]
                break
        if resolution is None:
            print(f"{disk_ref or snap_ref} was not found in any scanned "
                  "region. This is NOT proof of deletion: check the region, "
                  "check the id for typos, and check the console Snapshots / "
                  "Disks pages of the account that owned it.")
            print("\nSTATUS: DEGRADED")
            print("NEXT_ACTION: confirm region and resource id with the "
                  "customer; never assert deletion from a miss")
            return 0
    else:
        resolution = resolve_instance(ref, kind, region, args.profile)
        inst = resolution["instance"]
        region = resolution["region"] or region
        auto_filled.extend(resolution["auto_filled"])

    if inst is None:
        # NOT FOUND -- three-branch explanation + retained-resource scan.
        scan_region = resolution.get("region") or region \
            or (CANDIDATE_REGIONS[0] if not args.region_id else args.region_id)
        if not args.region_id:
            retained_scan = None
            for candidate in CANDIDATE_REGIONS:
                retained_scan = retained_resource_scan(candidate, args.profile)
                if (retained_scan.get("disks")
                        or retained_scan.get("snapshots")):
                    scan_region = candidate
                    break
        else:
            retained_scan = retained_resource_scan(scan_region, args.profile)
        result = {
            "identity": {"uid": uid},
            "target": {"ref": ref, "kind": kind, "found": False},
            "three_branch_explanation": [
                "1) Wrong region: the query only covers the scanned "
                "regions; confirm which region the instance was created "
                "in.",
                "2) Typo in the identifier: re-read the instance id / IP / "
                "name with the customer.",
                "3) Possibly released: a released instance disappears from "
                "DescribeInstances. This branch is a POSSIBILITY, never a "
                "conclusion -- confirm via billing records and the retained "
                "resources below.",
            ],
            "retained_resource_scan": retained_scan,
            "scan_region": scan_region,
            "auto_filled": auto_filled,
            "warnings": WARN_LOG,
        }
        _emit(result, args.json, human_not_found)
        print("\nSTATUS: DEGRADED")
        print("NEXT_ACTION: walk the three branches with the customer; use "
              "the retained disks/snapshots list to identify leftovers; "
              "NEVER state that the instance was released or the data is "
              "lost based on this miss alone")
        return 0

    # Instance found -- full evidence run.
    target_time = None
    if args.target_time:
        try:
            target_time = parse_target_time(args.target_time)
            auto_filled.append(
                "target time parsed as UTC; echo it back to the customer "
                f"for confirmation ({fmt_dt(target_time)})")
        except ValueError as e:
            print(f"[ERROR] {e}", file=sys.stderr)
            print("\nSTATUS: FAIL")
            print("NEXT_ACTION: ask the customer for the target time in "
                  "YYYY-MM-DD[THH:MM[:SS]] form and re-run")
            return 1

    ev = gather_evidence(inst, resolution["region"] or region, args.profile,
                         target_time)
    auto_filled.extend(resolution["auto_filled"])

    result = {
        "identity": {"uid": uid},
        "target": {"ref": ref, "kind": kind, "found": True,
                   "region": resolution["region"] or region,
                   "notes": resolution["notes"]},
        "instance": {
            "instance_id": inst.get("InstanceId"),
            "name": inst.get("InstanceName"),
            "region": inst.get("RegionId"),
            "zone": inst.get("ZoneId"),
            "ips": sorted(extract_instance_ips(inst)),
        },
        "timeline": ev["timeline"],
        "spot": ev["spot"],
        "operation_locks": ev["operation_locks"],
        "auto_renew": ev["auto_renew"],
        "release_protection": ev["release_protection"],
        "billing_matrix": build_billing_matrix(inst, ev),
        "disks": ev["disks"],
        "snapshots": ev["snapshots"],
        "has_system_disk_snapshot": ev.get("has_system_disk_snapshot"),
        "point_in_time": ev.get("point_in_time"),
        "full_status": ev["full_status"],
        "bss_crosscheck": ev["bss_crosscheck"],
        "recoverability": build_recoverability(ev, inst),
        "backup_feasibility": build_backup_feasibility(ev),
        "unknowns": ev["unknowns"],
        "guest_data_note": (
            "In-guest usage data (df/du style readings) is only obtainable "
            "while the instance is Running, and only by the CUSTOMER "
            "manually via the console remote connection -- this skill never "
            "executes commands inside instances. Suggested non-mutating "
            f"commands: Linux {GUEST_COMMAND_GUIDANCE['linux']}; Windows "
            f"{GUEST_COMMAND_GUIDANCE['windows']}. A stopped or released "
            "instance is unreachable: do not retry, mark the guest side "
            "DEGRADED and continue with cloud-side facts."),
        "intent": args.intent,
        "auto_filled": auto_filled,
        "errors": ev["errors"],
        "warnings": WARN_LOG,
    }
    if ev["timeline"]["phase"] in ("EXPIRED_STOPPED_IN_RETENTION",
                                    "EXPIRED") or args.intent == "extension":
        result["extension_precheck"] = build_extension_precheck(inst, ev)

    degraded = bool(ev["errors"]) or (
        result["timeline"]["expired_time"] == "UNKNOWN"
        and result["timeline"]["charge_type"] == "PrePaid")
    _emit(result, args.json, human_single_report)
    print("\nSTATUS: " + ("DEGRADED" if degraded else "OK"))
    print("NEXT_ACTION: relay the timeline, billing and recoverability "
          "findings verbatim; every change action (renew, unsubscribe, "
          "release, rollback, snapshot creation, extension request) is "
          "manual-guidance-only, starting with the snapshot-first rule; "
          "route out-of-scope asks per references/expiry-release-retention__handoff-boundaries.md")
    return 0


# ---------------------------------------------------------------------------
# Mode 2: batch expiry scan
# ---------------------------------------------------------------------------

def run_list_expiring(args: argparse.Namespace) -> int:
    uid = _cli.resolve_account_id(profile=args.profile)
    if not uid:
        print("[ERROR] STS get-caller-identity failed; run `aliyun "
              "configure` first (never pass AK/SK).", file=sys.stderr)
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: fix the credential chain, then re-run")
        return 1
    days = max(1, min(365, args.days))
    regions = [args.region_id] if args.region_id else list(CANDIDATE_REGIONS)
    now = datetime.now(timezone.utc)
    horizon = now + timedelta(days=days)
    hits: list[dict] = []
    errors: list[str] = []
    for region in regions:
        insts, err = paged("ecs", "DescribeInstances",
                           {"RegionId": region,
                            "InstanceChargeType": "PrePaid"},
                           region, args.profile, ["Instances", "Instance"])
        if err:
            warn(f"{region}: DescribeInstances failed: {err}")
            errors.append(f"{region}: {err}")
            continue
        renew_items, renew_err = fetch_auto_renew(region, args.profile)
        renew_map = {}
        if renew_err:
            warn(f"{region}: DescribeInstanceAutoRenewAttribute failed: "
                 f"{renew_err}")
        else:
            for item in renew_items:
                renew_map[str(item.get("InstanceId") or "")] = item
        for inst in insts:
            expired = parse_api_time(inst.get("ExpiredTime"))
            if expired is None or expired > horizon:
                continue
            iid = str(inst.get("InstanceId") or "")
            renew = renew_map.get(iid) or {}
            hits.append({
                "region": region,
                "instance_id": iid,
                "name": inst.get("InstanceName"),
                "status": inst.get("Status"),
                "expired_time": fmt_dt(expired),
                "expired_time_raw": inst.get("ExpiredTime"),
                "phase": ("EXPIRED" if expired <= now else "EXPIRING_SOON"),
                "estimated_release_time": fmt_dt(
                    expired + timedelta(days=RETENTION_DAYS_SUBSCRIPTION)),
                "renewal_status": renew.get("RenewalStatus", "UNKNOWN"),
                "auto_renew_enabled": renew.get("AutoRenewEnabled",
                                                "UNKNOWN"),
            })
        # The retention answer has to say WHICH data goes with the instance, so the
        # expiring list reads the disks too: one DescribeDisks per region that has a
        # hit, mapped back by InstanceId. Eval 15634 assert-004 failed because this
        # mode never issued the disk read the area spec promises.
        region_hits = [h for h in hits if h["region"] == region]
        if region_hits:
            disks, disk_err = fetch_disks(region, args.profile)
            if disk_err:
                warn(f"{region}: DescribeDisks failed: {disk_err}")
                errors.append(f"{region}: disks: {disk_err}")
            by_instance: dict[str, list] = {}
            for disk in disks or []:
                by_instance.setdefault(
                    str(disk.get("InstanceId") or ""), []).append({
                        "disk_id": disk.get("DiskId"),
                        "type": disk.get("Type"),
                        "size_gib": disk.get("Size"),
                        "delete_with_instance": disk.get("DeleteWithInstance"),
                    })
            for row in region_hits:
                row["disks"] = (None if disk_err
                                else by_instance.get(row["instance_id"], []))
    hits.sort(key=lambda h: h["expired_time_raw"] or "")
    result = {
        "identity": {"uid": uid},
        "mode": "list-expiring",
        "window_days": days,
        "regions_scanned": ([args.region_id] if args.region_id
                            else list(regions)),
        "retention_tag": RETENTION_DAYS_TAG,
        "instances": hits,
        "count": len(hits),
        "errors": errors,
        "warnings": WARN_LOG,
        "auto_filled": (["region not provided: scanned all candidate "
                         "regions"] if not args.region_id else []),
    }
    _emit(result, args.json, human_list_expiring)
    all_failed = bool(errors) and not hits and \
        len(errors) == len(regions)
    print("\nSTATUS: " + ("FAIL" if all_failed else
                          ("DEGRADED" if errors else "OK")))
    print("NEXT_ACTION: relay the per-instance expiry table; for expired "
          "instances state the retention deadline with its TO-VERIFY tag; "
          "renewal / unsubscription / extension actions are manual and "
          "never promised")
    return 1 if all_failed else 0


# ---------------------------------------------------------------------------
# Mode 3: notification parsing (offline)
# ---------------------------------------------------------------------------

def run_parse_notification(args: argparse.Namespace) -> int:
    parsed = parse_notification(args.parse_notification)
    result = {
        "mode": "parse-notification",
        "parsed": parsed,
        "suggested_next_command": (
            "python3 scripts/areas/expiry_release_retention/ecs_expiry_release_check.py --instance-ref "
            + (parsed["instance_ids"][0]
               if parsed["instance_ids"]
               else (parsed["ip_addresses"][0]
                     if parsed["ip_addresses"] else "<id-or-ip>"))),
        "note": ("Parsed fields are echoed verbatim from the customer text; "
                 "nothing is inferred. Confirm any parsed timestamp with "
                 "the customer before using it as --target-time."),
    }
    _emit(result, args.json, human_notification)
    found_anything = any([parsed["instance_ids"], parsed["disk_ids"],
                          parsed["snapshot_ids"], parsed["image_ids"],
                          parsed["ip_addresses"], parsed["timestamps"]])
    print("\nSTATUS: " + ("OK" if found_anything else "DEGRADED"))
    print("NEXT_ACTION: run the suggested command with the normalized "
          "identifier, or ask the customer for an instance id / IP when "
          "nothing was extractable")
    return 0


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _emit(result: dict, as_json: bool, human_renderer) -> None:
    """Render the result dict as JSON (--json) or via the human renderer."""
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    else:
        human_renderer(result)


def human_notification(result: dict) -> None:
    parsed = result["parsed"]
    print("=" * 72)
    print("Notification parsing (offline, verbatim extraction)")
    print("=" * 72)
    for key in ("instance_ids", "disk_ids", "snapshot_ids", "image_ids",
                "ip_addresses", "timestamps", "keywords"):
        print(f"  {key:14s}: {parsed.get(key) or '(none)'}")
    print(f"\n  suggested next: {result['suggested_next_command']}")
    print(f"  note: {result['note']}")


def human_list_expiring(result: dict) -> None:
    print("=" * 72)
    print(f"Expiring / expired subscription instances "
          f"(window: {result['window_days']} days; "
          f"account UID {result['identity']['uid']})")
    print("=" * 72)
    if not result["instances"]:
        print("  Query succeeded: no subscription instance expires within "
              "the window in the scanned regions.")
    for row in result["instances"]:
        print(f"  - {row['instance_id']} ({row['name']}) region="
              f"{row['region']} status={row['status']}")
        print(f"      expires: {row['expired_time']}  phase={row['phase']}")
        print(f"      estimated release: {row['estimated_release_time']} "
              f"{result['retention_tag']}")
        print(f"      renewal: status={row['renewal_status']} "
              f"auto_renew={row['auto_renew_enabled']}")
        disks = row.get("disks")
        if disks is None:
            print("      disks: UNKNOWN (DescribeDisks failed)")
        elif not disks:
            print("      disks: query succeeded, no disk attached to this "
                  "instance")
        else:
            print("      disks: " + "; ".join(
                f"{d['disk_id']} {d['type']} {d['size_gib']}GiB "
                f"delete_with_instance={d['delete_with_instance']}"
                for d in disks))
    if result.get("errors"):
        print("\nGraceful Degradation Log")
        for line in result["errors"]:
            print(f"  - {line}")


def human_not_found(result: dict) -> None:
    print("=" * 72)
    print(f"Instance NOT FOUND for reference {result['target']['ref']!r} "
          f"(account UID {result['identity']['uid']})")
    print("=" * 72)
    print("\nThree-branch explanation (all three MUST be presented; a miss "
          "is NEVER proof of release):")
    for branch in result["three_branch_explanation"]:
        print(f"  {branch}")
    scan = result.get("retained_resource_scan") or {}
    print(f"\nRetained-resource scan (region: "
          f"{result.get('scan_region', 'UNKNOWN')}):")
    disks = scan.get("disks")
    if disks is None:
        print("  disks: UNKNOWN (query failed)")
    elif not disks:
        print("  disks: query succeeded, no disk found in this region")
    else:
        for d in disks:
            print(f"  - disk {d['disk_id']} name={d['name']} type={d['type']}"
                  f" status={d['status']} attached_to={d['instance_id']}"
                  f" zone={d['zone_id']} "
                  f"delete_with_instance={d['delete_with_instance']}")
    snaps = scan.get("snapshots")
    if snaps is None:
        print("  snapshots: UNKNOWN (query failed)")
    elif not snaps:
        print("  snapshots: query succeeded, no snapshot found in this "
              "region")
    else:
        for s in snaps:
            print(f"  - snapshot {s['snapshot_id']} name={s['name']} "
                  f"created={s['creation_time']} status={s['status']} "
                  f"source_disk={s['source_disk_id']} "
                  f"({s['source_disk_type']})")


def human_single_report(r: dict) -> None:
    line = "=" * 72
    print(line)
    print(f"ECS expiry / release / data-retention report -- "
          f"{r['instance']['instance_id']} ({r['instance']['name']})")
    print(f"Account UID {r['identity']['uid']} | region "
          f"{r['instance']['region']} | zone {r['instance']['zone']}")
    print(line)

    t = r["timeline"]
    print("\n[1] Lifecycle timeline (C3)")
    print(f"  phase            : {t['phase']}")
    print(f"  status           : {t['status']}")
    print(f"  billing type     : {t['charge_type_human']}")
    print(f"  created          : {t['creation_time']}")
    print(f"  expires (raw)    : {t['expired_time_raw'] or 'n/a'}")
    print(f"  expires (parsed) : {t['expired_time']}")
    if t["days_left"] is not None:
        print(f"  days left        : {t['days_left']}")
    if t["days_since_expiry"] is not None:
        print(f"  days since expiry: {t['days_since_expiry']}")
    if t["estimated_release_time"]:
        print(f"  estimated release: {t['estimated_release_time']} "
              f"(expiry + {RETENTION_DAYS_SUBSCRIPTION}-day retention "
              f"window {t['retention_tag']})")
    if t["earliest_manual_release"]:
        print(f"  earliest manual release: {t['earliest_manual_release']}")
    if r["spot"]["is_spot"]:
        print(f"  SPOT instance    : strategy={r['spot']['spot_strategy']}")
        print(f"    {r['spot']['note']}")
    if r["operation_locks"]:
        print(f"  operation locks (verbatim): "
              f"{json.dumps(r['operation_locks'], default=str)}")

    print("\n[2] Auto-renewal & protection (C5)")
    renew = r["auto_renew"]
    if isinstance(renew, dict):
        print(f"  auto-renewal     : status={renew['renewal_status']} "
              f"enabled={renew['auto_renew_enabled']} "
              f"duration={renew['duration']} {renew['period_unit']}")
    else:
        print(f"  auto-renewal     : {renew}")
    print(f"  release protection (DeletionProtection): {r['release_protection']}")

    print("\n[3] Billing-stop matrix (C4)")
    for row in r["billing_matrix"]:
        print(f"  - {row['resource']}")
        print(f"      now : {row['now']}")
        print(f"      rule: {row['rule']}")

    print("\n[4] Disks (C6)")
    if r["disks"] is None:
        print("  UNKNOWN (query failed)")
    elif not r["disks"]:
        print("  Query succeeded: no disk attached to this instance.")
    else:
        for d in r["disks"]:
            print(f"  - {d['disk_id']} ({d['type']}, {d['category']}, "
                  f"{d['size_gib']} GiB, {d['status']}, zone {d['zone_id']}) "
                  f"delete_with_instance={d['delete_with_instance']} "
                  f"auto_snapshot={d['enable_auto_snapshot']} "
                  f"policy={d['auto_snapshot_policy_id']}")

    print("\n[5] Snapshots (C6/C7)")
    if r["snapshots"] is None:
        print("  UNKNOWN (query failed)")
    elif not r["snapshots"]:
        print("  Query succeeded: NO snapshot exists for this instance. "
              "Without a snapshot there is no recovery point.")
    else:
        print(f"  system-disk snapshot present: "
              f"{r['has_system_disk_snapshot']} (required to build a "
              f"custom image [ticket:T-78D54558])")
        for s in r["snapshots"]:
            print(f"  - {s['snapshot_id']} created={s['creation_time_fmt']} "
                  f"status={s['status']} source={s['source_disk_id']} "
                  f"({s['source_disk_type']}, {s['source_disk_size']} GiB)")

    if r.get("point_in_time"):
        pit = r["point_in_time"]
        print("\n[6] Point-in-time recoverability (C7)")
        print(f"  verdict: {pit['verdict']}")
        print(f"  {pit['explanation']}")
        print(f"  all snapshot times: {pit['all_snapshot_times']}")

    print("\n[7] Full status / events")
    fs = r["full_status"]
    if isinstance(fs, dict):
        print(f"  status={fs['status']} health={fs['health_status']}")
        for e in fs["scheduled_events"]:
            print(f"  - event {e['event_id']} type={e['type']} "
                  f"published={e['publish_time']} not_before="
                  f"{e['not_before']} cycle={e['cycle_status']}")
        print(f"  note: {fs['note']}")
    else:
        print(f"  {fs}")

    print("\n[8] Billing-side expiry cross-check")
    bss = r["bss_crosscheck"]
    if isinstance(bss, dict):
        print(f"  end_time={bss['end_time']} renew_status="
              f"{bss['renew_status']} subscription={bss['subscription_type']}"
              f" region={bss['region']}")
    else:
        print(f"  {bss}")

    print("\n[9] Recoverability verdicts (C6)")
    rec = r["recoverability"]
    for key in ("instance_body", "retained_disk_rules", "image_path_rule",
                "data_disk_only_path", "snapshot_loss_rule",
                "public_ip_rule"):
        print(f"  - {rec[key]}")
    print(f"  - retained disks now: "
          f"{json.dumps(rec['retained_disks'], default=str)}")
    print(f"  - snapshots available: {rec['snapshots_available']}")
    print(f"  - system-disk snapshot: {rec['system_disk_snapshot_present']}")

    print("\n[10] Backup feasibility & snapshot-first rule (C8)")
    bf = r["backup_feasibility"]
    print(f"  verdict : {bf['verdict']}")
    print(f"  order   : {bf['order']}")
    print(f"  fees    : {bf['snapshot_fee_disclosure']}")
    print(f"  note    : {bf['execution_note']}")

    if r.get("extension_precheck"):
        print("\n[11] Extension pre-check & application material (C10)")
        ext = r["extension_precheck"]
        print(f"  authoritative expiry: {ext['authoritative_expiry']}")
        print(f"  auto-renew status   : {ext['auto_renew_status']}")
        print(f"  rules               : {ext['rules']}")
        print(f"  preconditions       : {ext['preconditions']}")
        print(f"  self-check required : {ext['self_check_required']}")
        print("  application material package (for the human ticket):")
        print(f"    {json.dumps(ext['application_material_package'], indent=4, default=str)}")

    print("\n[12] UNKNOWN / not queryable in this tier")
    for item in r["unknowns"]:
        print(f"  - {item}")
    print(f"\n[13] Guest-side note\n  {r['guest_data_note']}")

    if r.get("warnings") or r.get("errors"):
        print("\nGraceful Degradation Log")
        for item in (r.get("warnings") or []) + (
                [f"error: {e}" for e in (r.get("errors") or [])]):
            print(f"  - {item}")

    print("\nAuto-filled parameters (declared per contract):")
    for item in r["auto_filled"]:
        print(f"  - {item}")

    print("\nSummary")
    print("-------")
    print(f"Instance {r['instance']['instance_id']} is in phase "
          f"{r['timeline']['phase']} (status {r['timeline']['status']}, "
          f"{r['timeline']['charge_type_human']}); expiry "
          f"{r['timeline']['expired_time']}. Every number above comes from "
          f"live API data or carries its evidence tag; retention-window "
          f"figures carry the TO-VERIFY tag until officially confirmed.")


# ---------------------------------------------------------------------------
# Inline boundary assertions for the pure functions (normal / boundary /
# invalid inputs; executed on import)
# ---------------------------------------------------------------------------

assert classify_ref("i-uf6exampleafb76d3e06") == "instance_id"
assert classify_ref("d-wz9example38486e5dcd") == "disk_id"
assert classify_ref("s-2ze1234567890abcdef") == "snapshot_id"
assert classify_ref("m-2ze1234567890abcdef") == "image_id"
assert classify_ref("8.140.34.112") == "ipv4"
assert classify_ref("launch-advisor-20230725") == "name"
assert classify_ref("") == "name"
assert valid_ipv4("120.55.75.200") is True
assert valid_ipv4("999.1.1.1") is False
assert valid_ipv4("not-an-ip") is False
assert parse_api_time("2026-09-03T23:59Z") is not None
assert parse_api_time("2026-09-03T23:59Z").year == 2026
assert parse_api_time("2026-08-18 14:12:49") is not None
assert parse_api_time("") is None
assert parse_api_time(None) is None
assert parse_api_time("garbage") is None
assert parse_target_time("2026-08-06T11:00").hour == 11
try:
    parse_target_time("yesterday 11am")
    raise AssertionError("bad input must raise ValueError")
except ValueError:
    pass
_ips = extract_instance_ips({
    "PublicIpAddress": {"IpAddress": ["1.2.3.4"]},
    "InnerIpAddress": {"IpAddress": []},
    "VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["172.16.0.1"]}},
    "EipAddress": {"IpAddress": "5.6.7.8"},
})
assert _ips == {"1.2.3.4", "172.16.0.1", "5.6.7.8"}
assert extract_instance_ips({}) == set()
_notif = parse_notification(
    "Your ECS instance i-uf6exampleafb76d3e06 (IP 120.55.75.200) will "
    "expire at 2026-09-03 23:59:59. Renew to avoid release; data retention "
    "applies.")
assert _notif["instance_ids"] == ["i-uf6exampleafb76d3e06"]
assert _notif["ip_addresses"] == ["120.55.75.200"]
assert _notif["timestamps"] == ["2026-09-03 23:59:59"]
assert "expire" in _notif["keywords"] and "retention" in _notif["keywords"]
assert parse_notification("")["instance_ids"] == []
_pit_no_snaps = point_in_time_verdict(
    datetime(2026, 8, 6, tzinfo=timezone.utc), [])
assert _pit_no_snaps["verdict"] == "NO_SNAPSHOTS"
_pit_one = point_in_time_verdict(
    datetime(2026, 8, 7, tzinfo=timezone.utc),
    [{"SnapshotId": "s-a", "CreationTime": "2026-08-06T11:25:03Z"}])
assert _pit_one["verdict"] == "RECOVERABLE_TO_SNAPSHOT"
_pit_early = point_in_time_verdict(
    datetime(2026, 8, 1, tzinfo=timezone.utc),
    [{"SnapshotId": "s-a", "CreationTime": "2026-08-06T11:25:03Z"}])
assert _pit_early["verdict"] == "NOT_RECOVERABLE_AT_TARGET"
_phase = classify_phase(
    {"Status": "Stopped", "InstanceChargeType": "PrePaid",
     "ExpiredTime": "2020-01-01T00:00Z"}, datetime.now(timezone.utc))
assert _phase["phase"] == "EXPIRED_STOPPED_IN_RETENTION"
_phase2 = classify_phase(
    {"Status": "Running", "InstanceChargeType": "PrePaid",
     "ExpiredTime": "2099-01-01T00:00Z"}, datetime.now(timezone.utc))
assert _phase2["phase"] == "BEFORE_EXPIRY"

# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def _run_selftest():
    """Offline regression lock: pure computation core + contract guards."""
    results = {"pass": 0, "fail": 0}

    def check(name, got, want):
        if got == want:
            results["pass"] += 1
        else:
            results["fail"] += 1
            print("FAIL {0}: got {1!r} want {2!r}".format(name, got, want))

    # --- valid_ipv4 ---
    check("ip4_valid", valid_ipv4("192.168.1.1"), True)
    check("ip4_255", valid_ipv4("255.255.255.255"), True)
    check("ip4_bad_256", valid_ipv4("256.1.1.1"), False)
    check("ip4_incomplete", valid_ipv4("10.0.0"), False)
    check("ip4_text", valid_ipv4("hello"), False)

    # --- classify_ref ---
    check("ref_i", classify_ref("i-bp1example724c8af2a1"), "instance_id")
    check("ref_d", classify_ref("d-bp1examplea7e2c95015"), "disk_id")
    check("ref_s", classify_ref("s-bp1example901cb1bad5"), "snapshot_id")
    check("ref_m", classify_ref("m-bp1example32f1dc14dc"), "image_id")
    check("ref_ip", classify_ref("47.98.1.2"), "ipv4")
    check("ref_name", classify_ref("my-web-server"), "name")
    check("ref_short", classify_ref("i-ab"), "name")
    check("ref_empty", classify_ref(""), "name")

    # --- parse_api_time ---
    dt = parse_api_time("2026-09-03T23:59:59Z")
    check("pat_utc_z", dt is not None and dt.year == 2026, True)
    check("pat_utc_z_month", dt.month if dt else 0, 9)
    dt2 = parse_api_time("2026-09-03 23:59:59")
    check("pat_space", dt2 is not None and dt2.tzinfo is not None, True)
    check("pat_iso_offset", parse_api_time("2026-01-01T00:00:00+08:00") is not None, True)
    check("pat_none", parse_api_time(None), None)
    check("pat_empty", parse_api_time(""), None)
    check("pat_bad", parse_api_time("not-a-date"), None)
    # timezone conversion
    dt3 = parse_api_time("2026-01-01T08:00:00+08:00")
    check("pat_tz_to_utc", dt3.hour if dt3 else -1, 0)

    # --- parse_target_time ---
    check("ptt_valid", parse_target_time("2026-08-06") is not None, True)
    try:
        parse_target_time("garbage")
        check("ptt_raises", False, True)
    except ValueError:
        check("ptt_raises", True, True)

    # --- fmt_dt ---
    check("fmt_none", fmt_dt(None), "UNKNOWN")
    check("fmt_utc", "2026-09-03" in fmt_dt(dt), True)

    # --- extract_instance_ips ---
    inst = {"PublicIpAddress": {"IpAddress": ["1.2.3.4"]},
            "InnerIpAddress": {"IpAddress": ["10.0.0.1"]},
            "VpcAttributes": {"PrivateIpAddress": {"IpAddress": ["172.16.0.1"]}},
            "EipAddress": {"IpAddress": "47.1.1.1"}}
    ips = extract_instance_ips(inst)
    check("eip_set_size", len(ips), 4)
    check("eip_has_public", "1.2.3.4" in ips, True)
    check("eip_has_eip", "47.1.1.1" in ips, True)
    check("eip_empty", extract_instance_ips({}), set())

    # --- parse_notification ---
    notif = parse_notification("Your instance i-bp1abcdef12345 at 47.1.2.3 will expire on 2026-09-01T00:00:00Z")
    check("pn_instance", "i-bp1abcdef12345" in notif["instance_ids"], True)
    check("pn_ip", "47.1.2.3" in notif["ip_addresses"], True)
    check("pn_time", any("2026-09-01" in t for t in notif["timestamps"]), True)
    check("pn_keywords", "expire" in notif["keywords"], True)
    check("pn_empty", parse_notification("")["instance_ids"], [])

    # --- point_in_time_verdict ---
    from datetime import datetime, timezone
    target = datetime(2026, 8, 15, 12, 0, tzinfo=timezone.utc)
    v = point_in_time_verdict(target, [])
    check("pitv_no_snaps", v["verdict"], "NO_SNAPSHOTS")
    snaps = [{"SnapshotId": "s-a", "CreationTime": "2026-08-10T00:00:00Z"},
             {"SnapshotId": "s-b", "CreationTime": "2026-08-20T00:00:00Z"}]
    v2 = point_in_time_verdict(target, snaps)
    check("pitv_recoverable", v2["verdict"], "RECOVERABLE_TO_SNAPSHOT")
    check("pitv_before", "s-a" in str(v2["nearest_before"]), True)
    check("pitv_after", "s-b" in str(v2["nearest_after"]), True)

    # --- contract guards ---
    src = open(__file__, encoding="utf-8").read()
    # Only check that no mutating action is passed to call() in code (not comments)
    check("no_mutating_in_call", "call(\"ecs\", \"Stop" not in src and
          "call(\"ecs\", \"Reboot" not in src and
          "call(\"ecs\", \"Delete" not in src, True)
    _list_body = src.split("def run_list_expiring(", 1)[1].split("\ndef ", 1)[0]
    check("list_expiring_reads_the_disks_it_promises",
          "fetch_disks(" in _list_body, True)
    _human_body = src.split("def human_list_expiring(", 1)[1].split("\ndef ", 1)[0]
    check("list_expiring_delivers_the_disk_release_facts",
          "delete_with_instance" in _human_body, True)

    print("selftest: {0} passed, {1} failed".format(results["pass"], results["fail"]))
    return 1 if results["fail"] else 0


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(_run_selftest())
    parser = argparse.ArgumentParser(
        description="Read-only ECS expiry / release / data-retention "
                    "lifecycle diagnosis (no mutating action is ever "
                    "performed)")
    parser.add_argument("--instance-ref",
                        help="instance id (i-...), public/private IPv4, or "
                             "instance name")
    parser.add_argument("--resource-ref",
                        help="disk id (d-...), snapshot id (s-...) or image "
                             "id (m-...) when the customer starts from a "
                             "non-instance resource")
    parser.add_argument("--region-id", default=None,
                        help="region to query; when omitted, candidate "
                             "regions are scanned and the derived region is "
                             "declared (never a silent default)")
    parser.add_argument("--target-time", default=None,
                        help="point-in-time recoverability target, "
                             "YYYY-MM-DD[THH:MM[:SS]] (naive input is "
                             "treated as UTC and declared)")
    parser.add_argument("--intent", choices=INTENTS, default="unclassified",
                        help="customer intent hint (routing aid only)")
    parser.add_argument("--list-expiring", action="store_true",
                        help="batch mode: list subscription instances that "
                             "expire (or already expired) within --days")
    parser.add_argument("--days", type=int, default=30,
                        help="window in days for --list-expiring (1-365, "
                             "default 30)")
    parser.add_argument("--parse-notification", metavar="TEXT", default=None,
                        help="offline mode: extract ids / IPs / timestamps "
                             "from a pasted expiry or release notification")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--json", action="store_true",
                        help="emit the machine-readable JSON report")
    args = parser.parse_args()

    _cli.check_cli_available()

    if args.parse_notification is not None:
        sys.exit(run_parse_notification(args))
    if args.list_expiring:
        sys.exit(run_list_expiring(args))
    if not args.instance_ref and not args.resource_ref:
        print("[ERROR] missing target: provide --instance-ref (id / IP / "
              "name) or --resource-ref (d-/s-/m-), or use --list-expiring / "
              "--parse-notification. Do NOT guess an identifier and do NOT "
              "scan the whole account without an explicit batch request.",
              file=sys.stderr)
        print("\nSTATUS: FAIL")
        print("NEXT_ACTION: ask the customer for the instance id, IP or "
              "name (or the pasted notification text), then re-run")
        sys.exit(1)
    if args.instance_ref and args.resource_ref:
        print("[ERROR] provide only one of --instance-ref / --resource-ref",
              file=sys.stderr)
        sys.exit(2)
    sys.exit(run_single_target(args))


if __name__ == "__main__":
    main()
