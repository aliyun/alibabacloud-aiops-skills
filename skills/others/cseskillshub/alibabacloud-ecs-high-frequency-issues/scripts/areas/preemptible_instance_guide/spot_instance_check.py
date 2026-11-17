#!/usr/bin/env python3
"""
spot_instance_check.py -- Single entry point of the read-only spot guide
=========================================================================
SECURITY: This skill is strictly READ-ONLY. Every request goes through `api()`
below, which refuses any action that is not whitelisted AND not read-only by name
shape, and through `scripts/areas/preemptible_instance_guide/_cli.py`, which resolves credentials with the aliyun
CLI default credential chain only. This script never reads, writes, caches,
echoes or accepts AccessKey material.

What it does (nothing more):
  * instance mode  -- read existence, status, zone, billing type and spot bidding
                      mode of the instances the customer names
                      (`DescribeInstances` + a `DescribeInstanceStatus` cross-check).
  * sweep mode     -- list the spot instances of one region (`--all-spot`).
  * inventory mode -- ask whether a region/zone/instance-type is sellable today,
                      spot included (`DescribeAvailableResource`).
  * explain mode   -- print the bundled rule statements without any cloud call.

It never runs a command inside an instance, never changes cloud state, and never
reads bill amounts. Findings are facts, causes are rules, and the fix is always a
step the customer performs.

Usage examples (placeholders only, never a real resource id):
  python3 spot_instance_check.py --region <RegionId> --instance-id <instance-id>
  python3 spot_instance_check.py --region <RegionId> --all-spot
  python3 spot_instance_check.py --region <RegionId> --inventory \
      --instance-type <instance-type> --zone-id <zone-id>
  python3 spot_instance_check.py --explain [--json]

Contract: every run prints Summary / ASSUMPTIONS / FINDINGS / RULES / LIMITATIONS
and ends with
  STATUS: OK|DEGRADED|FAIL
  NEXT_ACTION: <single next step>
"""

from __future__ import annotations
# A scanner that runs this entry directly must not leave bytecode in
# scripts/, where only scripts belong: set before this file imports.
import sys
sys.dont_write_bytecode = True

import argparse
import json
import sys
from typing import Any, Optional

import _cli
from _cli import CliError
from _constants import (
    DESCRIBE_IDS_CHUNK,
    DOC_EVIDENCE_NOTE,
    INVENTORY_IN_STOCK,
    INVENTORY_LIMITED,
    INVENTORY_NO_DATA,
    INVENTORY_SOLD_OUT,
    MAX_PAGES,
    MAX_SWEEP_INSTANCES,
    MAX_TARGET_IDS,
    NO_SPOT,
    PAGE_SIZE,
    RECYCLING_LOCK_TOKEN,
    RULE_ATTRIBUTION_LIMIT,
    RULE_BALANCE_IRRELEVANT,
    RULE_BILLING_SCOPE,
    RULE_DATA_RETENTION,
    RULE_INTERRUPTION_MODES,
    RULE_INVENTORY_SUPPLY,
    RULE_MECHANISM,
    RULE_NOTIFICATION,
    RULE_OS_CONFIDENCE,
    RULE_SUITABILITY,
    RULE_USAGE_DURATION,
    SKILL_NAME,
    SPOT_STRATEGIES,
    SPOT_STRATEGY_MEANINGS,
    STATUS_CATEGORY_MEANINGS,
    STATUS_CATEGORY_MEANING_FALLBACK,
    STATUS_RUNNING,
    STATUS_STOPPED,
    STATUS_STOPPING,
    TRANSITIONAL_STATUSES,
    VERDICT_NOT_FOUND,
    VERDICT_NOT_SPOT_OTHER,
    VERDICT_NOT_SPOT_STOPPED,
    VERDICT_SPOT_RUNNING,
    VERDICT_SPOT_STOPPED,
    VERDICT_SPOT_TRANSITIONAL,
    VERDICT_UNKNOWN,
)

# ---------------------------------------------------------------------------
# Whitelist: a read-only skill must not be able to reach anything else
# ---------------------------------------------------------------------------

ACTION_WHITELIST = frozenset({
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeInstanceStatus"),
    ("ecs", "DescribeAvailableResource"),
    ("sts", "GetCallerIdentity"),
})

READ_ONLY_PREFIXES = ("Describe", "Get", "List")

# DescribeAvailableResource .Status values (raw values are always echoed as well).
RESOURCE_STATUS_MEANINGS = {
    "Available": "sellable at query time",
    "SoldOut": "sold out at query time",
    "Unavailable": "not sellable at query time, for a reason the API does not detail",
}

# DestinationResource values this skill answers with; anything else would ask a
# different question than the customer posed.
DESTINATION_RESOURCES = ("InstanceType", "Zone")

UNMAPPED_NOTE = STATUS_CATEGORY_MEANING_FALLBACK


class ReadOnlyViolation(RuntimeError):
    """Raised when a caller tries to reach an action outside the whitelist."""


def assert_read_only(product: str, action: str) -> None:
    """Guard every outbound call: whitelisted AND read-only by name shape."""
    if (product, action) not in ACTION_WHITELIST:
        raise ReadOnlyViolation(
            f"{product} {action} is not on this skill's read-only whitelist "
            f"({SKILL_NAME}); refuse it and stay inside the documented flow.")
    if not action.startswith(READ_ONLY_PREFIXES):
        raise ReadOnlyViolation(
            f"{product} {action} is not a read-only action name; this skill answers "
            "with facts and guidance only.")


# Guard assertions (normal / boundary / invalid), run at import time.
# The whitelist is read-only by construction, so the name-shape check cannot be
# reached from it; asserting that is the point of the first line.
assert all(action.startswith(READ_ONLY_PREFIXES)
           for _, action in ACTION_WHITELIST)
assert_read_only("ecs", "DescribeInstances")
for _bad_product, _bad_action in (
    ("ecs", "DescribeInstancesExtra"),   # plausible name, not on the whitelist
    ("ecs", "GetAnythingUnlisted"),      # read-only shape, still not whitelisted
    ("sts", "GetCallerIdentityExtra"),
    ("ecs", ""),                         # invalid: empty action
):
    try:
        assert_read_only(_bad_product, _bad_action)
    except ReadOnlyViolation:
        pass
    else:  # pragma: no cover - the guard must never let these through
        raise AssertionError(f"whitelist failed to reject {_bad_action!r}")


# ---------------------------------------------------------------------------
# Defensive JSON helpers (no assumed nesting depth)
# ---------------------------------------------------------------------------

def dig(obj: Any, *keys: str) -> Any:
    """Walk nested dicts, returning None on the first miss."""
    node = obj
    for key in keys:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node


def as_list(value: Any) -> list[Any]:
    """Normalize ECS list shapes: list, {"Item": [...]}, single dict, None."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        inner = value.get("Item")
        if isinstance(inner, list):
            return inner
        return [value]
    return [value]


assert dig({"a": {"b": 1}}, "a", "b") == 1
assert dig({"a": None}, "a", "b") is None          # boundary: missing leaf
assert dig("scalar", "a") is None                  # invalid: non-dict root
assert as_list([1, 2]) == [1, 2]
assert as_list({"LockReason": ["recycling"]}) == [{"LockReason": ["recycling"]}]
assert as_list("Recycling") == ["Recycling"]
assert as_list(None) == []


# ---------------------------------------------------------------------------
# Pure judgement functions (rule application, no I/O)
# ---------------------------------------------------------------------------

def is_spot(instance: dict) -> Optional[bool]:
    """True/False when the bidding mode is readable, None when it is absent."""
    strategy = str(instance.get("SpotStrategy") or "").strip()
    if not strategy:
        return None
    return strategy in SPOT_STRATEGIES


def has_recycling_lock(instance: dict) -> bool:
    """True when any operation-lock reason carries the recycling token."""
    for lock in as_list(dig(instance, "OperationLocks")):
        candidates: list[Any] = []
        if isinstance(lock, str):
            candidates = [lock]
        elif isinstance(lock, dict):
            candidates = as_list(lock.get("LockReason")) or list(lock.values())
        if any(RECYCLING_LOCK_TOKEN in str(reason).lower() for reason in candidates):
            return True
    return False


def unrecognized_verdict(status: str) -> str:
    """Unknown status string: echo it back instead of interpreting it."""
    return f"SPOT_STATUS_UNRECOGNIZED({status or 'empty'})"


def instance_verdict(instance: dict) -> str:
    """Classify one DescribeInstances record against this tier's question."""
    status = str(instance.get("Status") or "").strip()
    spot = is_spot(instance)
    if spot is not False and spot is not True:
        return VERDICT_UNKNOWN
    if spot is False:
        return (VERDICT_NOT_SPOT_STOPPED if status == STATUS_STOPPED
                else VERDICT_NOT_SPOT_OTHER)
    if status in TRANSITIONAL_STATUSES:
        return VERDICT_SPOT_TRANSITIONAL
    if status in (STATUS_STOPPED, STATUS_STOPPING):
        return VERDICT_SPOT_STOPPED
    if status == STATUS_RUNNING:
        return VERDICT_SPOT_RUNNING
    return unrecognized_verdict(status)


VERDICT_MEANINGS = {
    VERDICT_SPOT_STOPPED: ("stopped or stopping while billed as preemptible: "
                           "consistent with a spot interruption"),
    VERDICT_SPOT_RUNNING: ("running as a preemptible instance: no interruption has "
                           "taken effect on this instance so far"),
    VERDICT_SPOT_TRANSITIONAL: ("transitional status; re-check shortly, since a spot "
                                "instance passes through Stopping while being "
                                "reclaimed"),
    VERDICT_NOT_SPOT_STOPPED: ("stopped but NOT billed as preemptible: this is not a "
                               "spot reclamation question"),
    VERDICT_NOT_SPOT_OTHER: ("not billed as preemptible: outside this skill's scope"),
    VERDICT_UNKNOWN: ("the bidding mode was not returned, so the billing type is "
                      "unknown; do not assert a spot reclamation"),
    VERDICT_NOT_FOUND: ("no matching instance in this region and account; consistent "
                        "with a reclamation but equally consistent with a wrong "
                        "region, a wrong id, or another account"),
}

assert is_spot({"SpotStrategy": "SpotWithPriceLimit"}) is True
assert is_spot({"SpotStrategy": NO_SPOT}) is False
assert is_spot({}) is None                         # invalid: field absent
assert is_spot({"SpotStrategy": "  "}) is None     # boundary: whitespace only
assert instance_verdict({"Status": STATUS_STOPPED,
                         "SpotStrategy": "SpotAsPriceGo"}) == VERDICT_SPOT_STOPPED
assert instance_verdict({"Status": STATUS_STOPPING,
                         "SpotStrategy": "SpotWithPriceLimit"}) == VERDICT_SPOT_STOPPED
assert instance_verdict({"Status": STATUS_STOPPED,
                         "SpotStrategy": NO_SPOT}) == VERDICT_NOT_SPOT_STOPPED
assert instance_verdict({"Status": STATUS_RUNNING,
                         "SpotStrategy": "SpotAsPriceGo"}) == VERDICT_SPOT_RUNNING
assert instance_verdict({"Status": "Pending",
                         "SpotStrategy": "SpotAsPriceGo"}) == VERDICT_SPOT_TRANSITIONAL
assert instance_verdict({"Status": STATUS_RUNNING}) == VERDICT_UNKNOWN
assert instance_verdict({"Status": "Weird", "SpotStrategy": "SpotAsPriceGo"}).startswith(
    "SPOT_STATUS_UNRECOGNIZED")
assert has_recycling_lock({"OperationLocks": {"LockReason": ["recycling"]}}) is True
assert has_recycling_lock({"OperationLocks": [{"LockReason": "Recycling"}]}) is True
assert has_recycling_lock({"OperationLocks": {"LockReason": ["financial"]}}) is False
assert has_recycling_lock({"OperationLocks": []}) is False
assert has_recycling_lock({}) is False             # boundary: no locks at all


def inventory_verdict(entries: list[dict], zone_filter: str = "") -> str:
    """Collapse harvested inventory rows into one headline verdict.

    Raw values are echoed alongside, so the headline never hides a surprise.
    """
    scope = [e for e in entries
             if not zone_filter or str(e.get("zone") or "") == zone_filter] or entries
    if not scope:
        return INVENTORY_NO_DATA
    categories = {str(e.get("category") or "").strip() for e in scope}
    statuses = {str(e.get("status") or "").strip() for e in scope}
    if "WithStock" in categories or "Available" in statuses:
        return INVENTORY_IN_STOCK
    if "ClosedWithStock" in categories:
        return INVENTORY_LIMITED
    if "WithoutStock" in categories or "SoldOut" in statuses:
        return INVENTORY_SOLD_OUT
    return INVENTORY_NO_DATA


INVENTORY_MEANINGS = {
    INVENTORY_IN_STOCK: ("sellable at query time; preemptible capacity is idle "
                         "inventory and can change minute to minute"),
    INVENTORY_LIMITED: "listed but restricted or low-stock; treat as unreliable",
    INVENTORY_SOLD_OUT: "not sellable at query time; there is no committed restock time",
    INVENTORY_NO_DATA: "no resource rows returned, so no conclusion about stock",
}

assert inventory_verdict([]) == INVENTORY_NO_DATA
assert inventory_verdict([{"category": "WithStock"}]) == INVENTORY_IN_STOCK
assert inventory_verdict([{"category": "WithoutStock"}]) == INVENTORY_SOLD_OUT
assert inventory_verdict([{"status": "SoldOut"}]) == INVENTORY_SOLD_OUT
assert inventory_verdict([{"category": "ClosedWithStock"}]) == INVENTORY_LIMITED
# boundary: the requested zone's own rows win over other zones
assert inventory_verdict([{"zone": "z-a", "category": "WithStock"},
                          {"zone": "z-b", "category": "WithoutStock"}],
                         zone_filter="z-b") == INVENTORY_SOLD_OUT
# invalid: unrecognised values degrade to "no conclusion" rather than a guess
assert inventory_verdict([{"category": "Whatever"}]) == INVENTORY_NO_DATA


# ---------------------------------------------------------------------------
# Run context: query accounting, warnings, limitations, declared assumptions
# ---------------------------------------------------------------------------

class Run:
    """Everything one diagnosis needs in order to report honestly."""

    def __init__(self, region: str = "", profile: Optional[str] = None,
                 timeout: int = 60) -> None:
        self.region = region
        self.profile = profile
        self.timeout = timeout
        self.warnings: list[str] = []
        self.limitations: list[str] = []
        self.assumptions: list[str] = []
        self.queries_ok = 0
        self.queries_failed = 0

    @property
    def status(self) -> str:
        if self.queries_ok and not self.queries_failed:
            return "OK"
        if self.queries_ok:
            return "DEGRADED"
        if self.queries_failed:
            return "FAIL"
        return "OK"              # explain mode: no cloud query was needed


def api(run: Run, action: str, params: dict[str, Any],
        product: str = "ecs") -> Optional[dict[str, Any]]:
    """The only cloud exit of this script: whitelisted, timed, never fatal."""
    assert_read_only(product, action)
    try:
        body = _cli.call(product, action, params, region=run.region,
                         profile=run.profile, timeout=run.timeout)
        run.queries_ok += 1
        return body if isinstance(body, dict) else {}
    except CliError as err:
        run.queries_failed += 1
        code = err.code or "unknown"
        run.warnings.append(f"{product} {action} failed: {code}: {err}")
        print(f"[WARN] {product} {action} failed: {code}: {err}", file=sys.stderr)
        if _cli.is_permission_error(err):
            run.limitations.append(
                f"{product} {action} was denied (NoPermission / ImplicitDeny). Grant "
                f"that read-only action to the credential in use; see "
                f"references/ram-policies.md. No substitute call was attempted.")
        elif "timed out" in str(err).lower():
            run.limitations.append(
                f"{product} {action} timed out after {run.timeout}s (retries "
                "included); no conclusion was drawn from the missing data.")
        else:
            run.limitations.append(
                f"{product} {action} returned an error (Code={code}); the message is "
                "in WARNINGS, quoted exactly as received.")
        return None


def paged_items(run: Run, action: str, params: dict[str, Any],
                items_path: tuple[str, ...],
                max_items: Optional[int] = None) -> list[dict[str, Any]]:
    """Follow PageNumber pagination under a page guardrail and an item cap."""
    items: list[dict[str, Any]] = []
    exhausted = False
    for page in range(1, MAX_PAGES + 1):
        page_params = dict(params)
        page_params["PageNumber"] = page
        page_params["PageSize"] = PAGE_SIZE
        body = api(run, action, page_params)
        if body is None:
            run.limitations.append(
                f"{action} stopped at page {page}; the list may be incomplete.")
            return items
        rows = [row for row in as_list(dig(body, *items_path))
                if isinstance(row, dict)]
        items.extend(rows)
        if max_items is not None and len(items) >= max_items:
            items = items[:max_items]
            run.limitations.append(
                f"{action} holds more records than the {max_items}-record cap of this "
                "script, so only the first ones were read; narrow the request for a "
                "complete answer.")
            return items
        if not rows:
            exhausted = True
            break
        total = body.get("TotalCount")
        try:
            total_int = int(total) if total is not None else None
        except (TypeError, ValueError):
            total_int = None
        if total_int is not None and len(items) >= total_int:
            exhausted = True
            break
    if not exhausted:
        run.limitations.append(
            f"{action} stopped at the {MAX_PAGES}-page guardrail; results are partial; "
            "narrow the request to complete it.")
    return items


# ---------------------------------------------------------------------------
# Mode implementations
# ---------------------------------------------------------------------------

def collect_instances(run: Run, instance_ids: list[str], name: str,
                      all_spot: bool) -> tuple[list[dict[str, Any]], list[str]]:
    """Read DescribeInstances records; return (records, ids not visible)."""
    if instance_ids:
        records: list[dict[str, Any]] = []
        for start in range(0, len(instance_ids), DESCRIBE_IDS_CHUNK):
            chunk = instance_ids[start:start + DESCRIBE_IDS_CHUNK]
            records.extend(paged_items(
                run, "DescribeInstances",
                {"RegionId": run.region, "InstanceIds": json.dumps(chunk)},
                ("Instances", "Instance")))
        seen = {str(r.get("InstanceId") or "") for r in records}
        missing = [i for i in instance_ids if i not in seen]
        if missing:
            run.limitations.append(
                "Not visible to these queries: " + ", ".join(missing) + ". "
                + VERDICT_MEANINGS[VERDICT_NOT_FOUND] + ".")
        return records, missing

    params: dict[str, Any] = {"RegionId": run.region}
    if name:
        params["InstanceName"] = name
        run.assumptions.append(
            "InstanceName was passed through exactly as supplied; this script does "
            "not widen a partial name into a wildcard match.")
    elif all_spot:
        run.assumptions.append(
            f"Sweep reads at most {MAX_SWEEP_INSTANCES} instances of {run.region} to "
            "bound the query, then keeps the preemptible ones.")
    records = paged_items(run, "DescribeInstances", params,
                          ("Instances", "Instance"),
                          max_items=MAX_SWEEP_INSTANCES if not name else None)
    if all_spot:
        records = [r for r in records if is_spot(r) is True]
    if not records and not run.warnings:
        run.limitations.append(
            "No matching instance was returned in this region for this account. "
            + VERDICT_MEANINGS[VERDICT_NOT_FOUND] + ".")
    return records, []


def cross_check_status(run: Run, records: list[dict[str, Any]]) -> dict[str, str]:
    """DescribeInstanceStatus cross-check for the ids actually in scope."""
    ids = [str(r.get("InstanceId") or "") for r in records][:MAX_TARGET_IDS]
    ids = [i for i in ids if i]
    if not ids:
        return {}
    params: dict[str, Any] = {"RegionId": run.region}
    for index, instance_id in enumerate(ids, start=1):
        params[f"InstanceId.{index}"] = instance_id
    run.assumptions.append(
        f"DescribeInstanceStatus was cross-checked for {len(ids)} of the returned "
        f"instance ids (up to {MAX_TARGET_IDS}).")
    body = api(run, "DescribeInstanceStatus", params)
    if body is None:
        return {}
    statuses: dict[str, str] = {}
    for row in as_list(dig(body, "InstanceStatuses", "InstanceStatus")):
        if isinstance(row, dict):
            statuses[str(row.get("InstanceId") or "")] = str(row.get("Status") or "")
    return statuses


def describe_one(record: dict[str, Any],
                 status_crosscheck: dict[str, str]) -> dict[str, Any]:
    """Distil one DescribeInstances row into the fields this tier reasons about."""
    instance_id = str(record.get("InstanceId") or "")
    status = str(record.get("Status") or "") or "not returned"
    cross = status_crosscheck.get(instance_id) or "not returned"
    strategy = str(record.get("SpotStrategy") or "")
    verdict = instance_verdict(record)
    detail: dict[str, Any] = {
        "instance_id": instance_id,
        "instance_name": record.get("InstanceName") or "not returned",
        "status": status,
        "status_crosscheck": cross,
        "zone_id": record.get("ZoneId") or "not returned",
        "region_id": record.get("RegionId") or "not returned",
        "instance_charge_type": record.get("InstanceChargeType") or "not returned",
        "spot_strategy": strategy or "not returned",
        "spot_strategy_meaning": SPOT_STRATEGY_MEANINGS.get(strategy, UNMAPPED_NOTE),
        "recycling_lock_seen": has_recycling_lock(record),
        "operation_locks_raw": dig(record, "OperationLocks"),
        "verdict": verdict,
        "verdict_meaning": VERDICT_MEANINGS.get(verdict, "raw verdict echoed above"),
    }
    if cross != "not returned" and status != "not returned" and cross != status:
        detail["status_note"] = (
            "The two read-only queries disagree (DescribeInstances reported "
            f"'{status}', DescribeInstanceStatus reported '{cross}'), so the instance "
            "is changing state; re-run before concluding.")
    return detail


def collect_inventory(run: Run, instance_type: str, zone_id: str,
                      spot_strategy: str, destination: str) -> list[dict[str, Any]]:
    """Harvest (zone, resource, status, category) rows from the availability query.

    The response is walked generically instead of assuming a fixed nesting, so only
    values the API really returned are reported.
    """
    params: dict[str, Any] = {
        "RegionId": run.region,
        "DestinationResource": destination,
        "InstanceChargeType": "PostPaid",
    }
    run.assumptions.append(
        "InstanceChargeType=PostPaid was auto-filled: preemptible capacity is sold on "
        "the pay-as-you-go charging type, so subscription rows would answer a "
        "different question.")
    if spot_strategy:
        params["SpotStrategy"] = spot_strategy
        run.assumptions.append(
            f"SpotStrategy={spot_strategy} was applied, so the rows describe "
            "preemptible capacity.")
    else:
        run.assumptions.append(
            "SpotStrategy was not set, so the rows describe capacity in general; "
            "preemptible supply can be narrower than the general rows suggest.")
    if instance_type:
        params["InstanceType"] = instance_type
    if zone_id:
        params["ZoneId"] = zone_id
    body = api(run, "DescribeAvailableResource", params)
    if body is None:
        return []
    rows: list[dict[str, Any]] = []
    harvest(body, {}, rows)
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        key = json.dumps(row, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(row)
    if not unique:
        run.limitations.append(
            "The availability query returned no resource rows carrying a status, so "
            "this skill cannot state whether the capacity is sellable. Retry with "
            "--destination Zone, or read the console purchase page.")
    return unique


HARVEST_KEYS = ("RegionId", "ZoneId", "Type", "Value", "Status", "StatusCategory",
                "InstanceType", "SpotStrategy")


def harvest(node: Any, context: dict[str, Any], out: list[dict[str, Any]]) -> None:
    """Collect every dict that carries a resource status of its own.

    A row is emitted only when the node itself has `Status` or `StatusCategory`;
    the enclosing context is still used for labelling, so a child never inherits a
    parent's availability as if it were its own.
    """
    if isinstance(node, list):
        for item in node:
            harvest(item, context, out)
        return
    if not isinstance(node, dict):
        return
    scope = dict(context)
    for key in HARVEST_KEYS:
        value = node.get(key)
        if value is not None and not isinstance(value, (dict, list)):
            scope[key] = value
    if "Status" in node or "StatusCategory" in node:
        status = str(node.get("Status") or "")
        category = str(node.get("StatusCategory") or "")
        out.append({
            "region": str(scope.get("RegionId") or ""),
            "zone": str(scope.get("ZoneId") or ""),
            "resource_type": str(scope.get("Type") or ""),
            "value": str(scope.get("Value") or scope.get("InstanceType") or ""),
            "status": status,
            "category": category,
            "status_meaning": RESOURCE_STATUS_MEANINGS.get(status, UNMAPPED_NOTE),
            "category_meaning": STATUS_CATEGORY_MEANINGS.get(category,
                                                             UNMAPPED_NOTE),
        })
    for value in node.values():
        if isinstance(value, (dict, list)):
            harvest(value, scope, out)


# Walker boundary: a child without its own status is not reported as available.
_rows: list[dict[str, Any]] = []
harvest({"ZoneId": "z-a", "StatusCategory": "WithStock",
         "Children": [{"Value": "type-x"}]}, {}, _rows)
assert len(_rows) == 1 and _rows[0]["zone"] == "z-a", _rows
_rows = []
harvest({"AvailableZones": [{"ZoneId": "z-b", "Status": "SoldOut"}]}, {}, _rows)
assert len(_rows) == 1 and _rows[0]["status"] == "SoldOut", _rows
_rows = []
harvest({"Nothing": {"Nested": [1, "two"]}}, {}, _rows)
assert _rows == []                                  # invalid: no status anywhere


# ---------------------------------------------------------------------------
# Rules, summary, next action, rendering
# ---------------------------------------------------------------------------

def rules_for_mode(mode: str, details: list[dict[str, Any]],
                   missing: list[str]) -> list[str]:
    """Which bundled rule statements this answer must carry."""
    if mode == "explain":
        return [RULE_MECHANISM, RULE_INTERRUPTION_MODES, RULE_USAGE_DURATION,
                RULE_BALANCE_IRRELEVANT, RULE_NOTIFICATION,
                RULE_ATTRIBUTION_LIMIT, RULE_DATA_RETENTION, RULE_INVENTORY_SUPPLY,
                RULE_BILLING_SCOPE, RULE_SUITABILITY, RULE_OS_CONFIDENCE,
                DOC_EVIDENCE_NOTE]
    if mode == "inventory":
        return [RULE_INVENTORY_SUPPLY, RULE_SUITABILITY, RULE_MECHANISM,
                RULE_INTERRUPTION_MODES, RULE_USAGE_DURATION, DOC_EVIDENCE_NOTE]

    rules = [DOC_EVIDENCE_NOTE]
    spot_seen = any(str(d.get("spot_strategy")) in SPOT_STRATEGIES for d in details)
    stopped_seen = any(d.get("verdict") == VERDICT_SPOT_STOPPED for d in details)
    if spot_seen or stopped_seen or not details:
        rules += [RULE_MECHANISM, RULE_INTERRUPTION_MODES, RULE_USAGE_DURATION,
                  RULE_ATTRIBUTION_LIMIT, RULE_NOTIFICATION,
                  RULE_DATA_RETENTION, RULE_BALANCE_IRRELEVANT]
    if stopped_seen or (not details and missing):
        rules.append(
            "Stability option, customer-executed only: keeping a stateful workload on "
            "a preemptible instance means accepting repeated interruption, so moving to "
            "a stable charging type is the usual answer. This skill does not perform "
            "that change and does not promise it is available for every instance; the "
            "impact must be stated first: data on disks released together with the "
            "instance is already unrecoverable.")
    if not details and missing:
        rules.append(
            "Absence result: no read-only query returned the instance. Do not "
            "attribute that to a specific cause; reclaimed preemptible instances stop "
            "appearing in query results, and so do ids of another region or account.")
    if details and not spot_seen:
        rules.append(
            "Identification result: the billing type read back is not a preemptible "
            "bidding mode, so the stop is not a spot reclamation. Route it to the tier "
            "for the actual stop cause (references/preemptible-instance-guide__ref-handoff.md).")
    rules.append(RULE_OS_CONFIDENCE)
    return rules


HANDOFF_NOTES = [
    "Bill amounts, refunds, invoices and voucher coverage are not answered here: give "
    "the cost-composition rules and the self-check path, then route to the billing "
    "tier.",
    "Taking or rolling back snapshots and images, and their pricing, belong to the "
    "snapshot tier; this skill only states what survives a reclamation.",
    "Auto Scaling and comparable architecture work is a solution-tier question.",
    "Open questions with no bundled evidence, which must never be answered here: "
    "converting a preemptible instance to a subscription one, swapping its public IP, "
    "and any claim that the undiscounted price is charged first and refunded later.",
]


def next_action_for(mode: str, details: list[dict[str, Any]], verdict: str,
                    missing: list[str]) -> str:
    if mode == "explain":
        return ("Answer with the rule statements above, cite references/ref-*.md, and "
                "ask for RegionId plus an instance id when a live check would settle "
                "the question.")
    if mode == "inventory":
        if verdict in (INVENTORY_SOLD_OUT, INVENTORY_NO_DATA):
            return ("Tell the customer preemptible capacity is idle inventory with no "
                    "committed restock time, then give the low-interruption selection "
                    "self-check in references/preemptible-instance-guide__ref-inventory-advisor.md.")
        return ("Report the sellable rows read back and remind the customer that "
                "preemptible supply changes minute to minute before the order is "
                "placed.")
    if any(d["verdict"] == VERDICT_SPOT_STOPPED for d in details):
        return ("State the reclamation mechanism and the attribution limit, then give "
                "the retention guidance in references/preemptible-instance-guide__ref-data-retention.md and let "
                "the customer choose the stability option.")
    if details and not any(str(d["spot_strategy"]) in SPOT_STRATEGIES
                           for d in details):
        return ("Tell the customer this is not a spot reclamation and route the stop "
                "cause to the matching tier (references/preemptible-instance-guide__ref-handoff.md).")
    if details:
        return ("Report that the instance is still present, then quote the "
                "interruption rules so the customer can prepare retention before the "
                "next interruption.")
    return ("Tell the customer the instance"
            + (f"s ({', '.join(missing)})" if missing else "")
            + " is not visible to these read-only queries, confirm the region and the "
            "account, and route any request for platform-side evidence to a support "
            "ticket.")


def summary_for(run: Run, mode: str, details: list[dict[str, Any]],
                missing: list[str], verdict: str) -> str:
    if mode == "explain":
        return ("No cloud query was needed: bundled rule statements on reclamation, "
                "notification, attribution limits, retention, inventory, billing "
                "scope and suitability, each traceable to references/ref-*.md.")
    if mode == "inventory":
        return (f"Queried sellable resources in {run.region}: headline {verdict} "
                f"({INVENTORY_MEANINGS.get(verdict, 'no conclusion')}); "
                f"{len(run.assumptions)} auto-filled parameter(s) declared, "
                f"{len(run.limitations)} limitation(s).")
    head = ("Read 1 read-only query" if run.queries_ok == 1
            else f"Read {run.queries_ok} read-only queries")
    parts = [head]
    if run.queries_failed:
        parts.append(f"; {run.queries_failed} failed")
    if details:
        parts.append(f"; classified {len(details)} instance record(s)")
    if missing:
        parts.append(f"; {len(missing)} id(s) not visible")
    parts.append(". Every conclusion below comes from those returned values or from a "
                 "cited rule; nothing was filled in from memory.")
    return "".join(parts)


def render_human(payload: dict[str, Any]) -> None:
    print("=" * 72)
    print(f" {SKILL_NAME} (read-only)")
    print("=" * 72)
    print(f"Mode   : {payload['mode']}")
    if payload.get("region"):
        print(f"Region : {payload['region']}")
    if payload.get("account_uid"):
        print(f"Account: {payload['account_uid']} (visible scope of these queries)")
    print(f"Scope  : {payload['permission_scope']}")
    print(f"Summary: {payload['summary']}")

    if payload.get("assumptions"):
        print("\nASSUMPTIONS")
        for item in payload["assumptions"]:
            print(f"  - {item}")

    if payload.get("instances"):
        print("\nFINDINGS")
        for row in payload["instances"]:
            print(f"  - {row['instance_id'] or '(no id returned)'} "
                  f"[{row['status']}, cross-check {row['status_crosscheck']}] "
                  f"name={row['instance_name']} zone={row['zone_id']} "
                  f"charge={row['instance_charge_type']} spot={row['spot_strategy']}")
            print(f"      verdict : {row['verdict']} - {row['verdict_meaning']}")
            print(f"      bidding : {row['spot_strategy_meaning']}")
            print(f"      locks   : recycling seen={row['recycling_lock_seen']} "
                  f"raw={json.dumps(row['operation_locks_raw'], ensure_ascii=False)}")
            if row.get("status_note"):
                print(f"      note    : {row['status_note']}")

    inventory = payload.get("inventory")
    if inventory:
        print("\nINVENTORY")
        print(f"  headline : {inventory['verdict']} - {inventory['verdict_meaning']}")
        for row in inventory["rows"][:20]:
            print(f"  - zone={row['zone'] or '?'} type={row['resource_type'] or '?'} "
                  f"value={row['value'] or '?'} status={row['status'] or '?'} "
                  f"category={row['category'] or '?'} ({row['category_meaning']})")
        if len(inventory["rows"]) > 20:
            print(f"  ... {len(inventory['rows']) - 20} more row(s) in --json")

    print("\nRULES")
    for rule in payload["rules"]:
        print(f"  - {rule}")

    if payload.get("limitations"):
        print("\nLIMITATIONS")
        for item in payload["limitations"]:
            print(f"  - {item}")
    if payload.get("warnings"):
        print("\nWARNINGS (verbatim API errors, credential material masked)")
        for item in payload["warnings"]:
            print(f"  - {item}")
    print("\nHANDOFF")
    for item in payload["handoff"]:
        print(f"  - {item}")

    print(f"\nSTATUS: {payload['status']}")
    print(f"NEXT_ACTION: {payload['next_action']}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spot_instance_check.py",
        description="Read-only checks and rule answers for ECS preemptible (spot) "
                    "instances that were interrupted or reclaimed.",
        epilog="This tool never changes cloud state and never runs a command inside "
               "an instance.",
    )
    parser.add_argument("--region", default="",
                        help="required for cloud queries; never guessed")
    parser.add_argument("--instance-id", action="append", default=[],
                        help=f"instance id, repeatable (max {MAX_TARGET_IDS})")
    parser.add_argument("--name", default="",
                        help="match by instance name instead of ids")
    parser.add_argument("--all-spot", action="store_true",
                        help="sweep the region and keep only preemptible instances")
    parser.add_argument("--inventory", action="store_true",
                        help="query sellable capacity instead of instances")
    parser.add_argument("--instance-type", default="",
                        help="instance type for --inventory")
    parser.add_argument("--zone-id", default="", help="zone for --inventory")
    parser.add_argument("--spot-strategy", default="",
                        choices=["", NO_SPOT, *SPOT_STRATEGIES],
                        help="bidding mode to ask capacity about")
    parser.add_argument("--destination", default="InstanceType",
                        choices=list(DESTINATION_RESOURCES),
                        help="DestinationResource for the availability query")
    parser.add_argument("--explain", action="store_true",
                        help="print the bundled rules; makes no cloud call")
    parser.add_argument("--profile", default=None,
                        help="optional aliyun CLI credential profile name")
    parser.add_argument("--timeout", type=int, default=60,
                        help="per-attempt timeout in seconds (default 60)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--no-identity", action="store_true",
                        help="skip the account-identity label")
    return parser


def resolve_mode(args: argparse.Namespace,
                 parser: argparse.ArgumentParser) -> str:
    if args.explain:
        return "explain"
    if args.inventory:
        return "inventory"
    if args.instance_id or args.name or args.all_spot:
        return "instance"
    parser.error("nothing to do: pass --instance-id, --name, --all-spot, "
                 "--inventory or --explain")
    return "explain"  # unreachable: parser.error exits


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    mode = resolve_mode(args, parser)

    if mode != "explain" and not args.region:
        print("[ERROR] --region is required for cloud queries; ask the customer for "
              "it instead of defaulting it. Next step: re-run with --region "
              "<RegionId>.", file=sys.stderr)
        return 2
    if len(args.instance_id) > MAX_TARGET_IDS:
        print(f"[ERROR] too many --instance-id values (max {MAX_TARGET_IDS}); split "
              "the request into runs.", file=sys.stderr)
        return 2

    run = Run(region=args.region, profile=args.profile, timeout=args.timeout)
    run.assumptions.append(
        f"RegionId={args.region or 'not applicable'} came from the caller; this "
        "script never defaults the region for a data query.")

    if mode != "explain":
        _cli.check_cli_available()

    uid = ""
    if mode != "explain" and not args.no_identity:
        uid = _cli.resolve_account_id(profile=args.profile)
        if uid:
            run.assumptions.append(
                f"Account UID {uid} came from the identity query and only labels the "
                "visible scope of these queries.")
        else:
            run.limitations.append(
                "The account behind the credential could not be identified, so an "
                "empty result cannot be told apart from a wrong-account lookup.")

    details: list[dict[str, Any]] = []
    missing: list[str] = []
    inventory_rows: list[dict[str, Any]] = []
    verdict = ""

    if mode == "instance":
        records, missing = collect_instances(run, args.instance_id, args.name,
                                             args.all_spot)
        cross = cross_check_status(run, records)
        details = [describe_one(record, cross) for record in records]
    elif mode == "inventory":
        inventory_rows = collect_inventory(run, args.instance_type, args.zone_id,
                                           args.spot_strategy, args.destination)
        verdict = inventory_verdict(inventory_rows, zone_filter=args.zone_id)

    payload: dict[str, Any] = {
        "skill": SKILL_NAME,
        "mode": mode,
        "region": args.region or None,
        "account_uid": uid or None,
        "permission_scope": "read-only queries only; no access inside the instance; "
                            "no cloud changes; no bill amounts",
        "summary": summary_for(run, mode, details, missing, verdict),
        "assumptions": run.assumptions,
        "instances": details,
        "not_found": missing,
        "inventory": {
            "verdict": verdict,
            "verdict_meaning": INVENTORY_MEANINGS.get(verdict, "not queried"),
            "rows": inventory_rows,
        } if mode == "inventory" else None,
        "rules": rules_for_mode(mode, details, missing),
        "limitations": run.limitations,
        "warnings": run.warnings,
        "handoff": HANDOFF_NOTES,
        "status": run.status,
        "next_action": next_action_for(mode, details, verdict, missing),
    }

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        render_human(payload)
    return 1 if payload["status"] == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
