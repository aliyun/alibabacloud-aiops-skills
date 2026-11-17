#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS DDH / Capacity Guide skill
============================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so all
static reference data (query constants, instance-family classification rules,
host-event semantics, SLA / maintenance / isolation guidance distilled from the
tier requirements document and real support tickets) is embedded here as Python
constants. There are NO data files in this skill.
"""

from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Skill / API metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-ddh-capacity-guide"

# ECS read-only OpenAPI version (regional endpoints; plugin-mode commands).
ECS_API_VERSION = "2014-05-26"
# STS is a central, region-less service used only for the identity pre-check.
STS_API_VERSION = "2015-04-01"
STS_ENDPOINT = "sts.aliyuncs.com"

# ---------------------------------------------------------------------------
# Query limits / timeouts
# ---------------------------------------------------------------------------

# Every aliyun CLI subprocess carries this per-call timeout (MUST 7.6.1).
DEFAULT_TIMEOUT = 60
# Page size for DescribeInstances / DescribeInstanceStatus (max 100).
PAGE_SIZE = 100
# Hard guardrail on the number of pages fetched per query loop.
MAX_PAGES = 10
# Fallback region only used to keep the CLI happy when the caller omits one;
# RegionId is a REQUIRED user input for every real query.
DEFAULT_REGION = "cn-hangzhou"

# DescribeInstanceHistoryEvents: MaxResults range is 10~100 (verified against
# `aliyun ecs describe-instance-history-events --help`, CLI 3.4.5).
HISTORY_EVENT_MAX_RESULTS = 50
# DescribeDedicatedHosts: MaxResults maximum is 100 (same verification).
DDH_MAX_RESULTS = 50
# Guardrail on how many disks get a DescribeDiskMonitorData call per run.
MAX_MONITORED_DISKS = 3
# DescribeDiskMonitorData window. The API accepts Period in {60, 600, 3600} and
# requires (EndTime - StartTime) / Period <= 400; 60 minutes at 60s = 60 points.
MONITOR_WINDOW_MINUTES = 60
MONITOR_PERIOD_SECONDS = 60

# ---------------------------------------------------------------------------
# RAM action names (used only to print the missing read-only action and the
# minimal policy snippet on a permission failure; this skill never calls IAM).
# ---------------------------------------------------------------------------

RAM_ACTION_BY_API = {
    "GetCallerIdentity": "sts:GetCallerIdentity",
    "DescribeInstances": "ecs:DescribeInstances",
    "DescribeInstanceStatus": "ecs:DescribeInstanceStatus",
    "DescribeInstanceHistoryEvents": "ecs:DescribeInstanceHistoryEvents",
    "DescribeDedicatedHosts": "ecs:DescribeDedicatedHosts",
    "DescribeDisks": "ecs:DescribeDisks",
    "DescribeDiskMonitorData": "ecs:DescribeDiskMonitorData",
}

# ---------------------------------------------------------------------------
# Instance-family classification (CPU isolation model)
# ---------------------------------------------------------------------------
# Source: official ECS instance-family documentation and real support tickets
# in this tier (e.g. a customer asking whether e / s6 / xn4 / n4 / mn4 / e4 / t
# are shared while g / c / r / u are dedicated). The family token is matched by
# prefix; rules are evaluated IN ORDER and the first match wins, so the
# bare-metal rule must precede the shared rule (the "ebm" prefix would otherwise
# be caught by the shared "e" prefix).
FAMILY_CLASSIFICATION = (
    (
        ("ebm", "scc"),
        "dedicated",
        "Elastic Bare Metal / Super Computing Cluster - a dedicated physical "
        "host, strongest isolation",
    ),
    (
        ("t",),
        "burstable",
        "Burstable performance instance - CPU-credit based (baseline plus "
        "burst); the physical CPU is shared, so sustained load can be limited",
    ),
    (
        ("e", "s6", "xn4", "n4", "mn4", "e4"),
        "shared",
        "Shared / economy instance - the physical CPU is shared with other "
        "instances on the same host, so a noisy neighbor can slow it down",
    ),
    (
        ("g", "c", "r", "u", "hf", "i", "d", "gn", "vgn", "sgn",
         "re", "se", "ic", "lr", "sn"),
        "dedicated",
        "Dedicated instance - vCPU is exclusively scheduled and not shared "
        "with other tenants on the host",
    ),
)

_FAMILY_TOKEN_RE = re.compile(r"([a-z]+[0-9]*)")


def parse_family_token(instance_type: str) -> str:
    """Return the family token of an ECS instance type.

    Examples: "ecs.g7.large" -> "g7"; "ecs.e-c1m2.xlarge" -> "e";
    "ecs.u1-c1m2.xlarge" -> "u1"; "ecs.t6-c1m1.large" -> "t6";
    "ecs.s6-c1m1.small" -> "s6". Returns "" when nothing can be parsed.
    """
    if not instance_type:
        return ""
    token = str(instance_type).strip().lower()
    if token.startswith("ecs."):
        token = token[4:]
    match = _FAMILY_TOKEN_RE.match(token)
    return match.group(1) if match else ""


def classify_instance_family(instance_type: str) -> tuple:
    """Classify an instance type into (class, family_token, note).

    class is one of: "shared", "burstable", "dedicated", "unknown".
    Pure function; never raises. Used to answer "is this instance shared or
    dedicated" and "which families avoid CPU contention" without guessing.
    """
    family = parse_family_token(instance_type)
    if not family:
        return (
            "unknown",
            "",
            "Instance type could not be parsed; verify the family in the ECS "
            "console instance-type documentation",
        )
    for prefixes, klass, note in FAMILY_CLASSIFICATION:
        if family.startswith(prefixes):
            return (klass, family, note)
    return (
        "unknown",
        family,
        "Family not in the embedded classification table; verify it in the "
        "ECS console instance-type documentation before concluding",
    )


# Inline boundary assertions (executed on import; a failure means the
# classifier is broken and must not run). normal / boundary / invalid inputs.
assert classify_instance_family("ecs.g7.large")[0] == "dedicated"
assert classify_instance_family("ecs.c7.large")[0] == "dedicated"
assert classify_instance_family("ecs.r7.large")[0] == "dedicated"
assert classify_instance_family("ecs.u1-c1m2.xlarge")[0] == "dedicated"
assert classify_instance_family("ecs.e-c1m2.xlarge")[0] == "shared"
assert classify_instance_family("ecs.s6-c1m1.small")[0] == "shared"
assert classify_instance_family("ecs.n4.small")[0] == "shared"
assert classify_instance_family("ecs.xn4.small")[0] == "shared"
assert classify_instance_family("ecs.e4.small")[0] == "shared"
assert classify_instance_family("ecs.t6-c1m1.large")[0] == "burstable"
assert classify_instance_family("ecs.ebmhfg7.xlarge")[0] == "dedicated"
assert parse_family_token("ecs.g7.large") == "g7"
assert parse_family_token("ecs.e-c1m2.xlarge") == "e"
# invalid / empty degrade gracefully (never raise)
assert classify_instance_family("")[0] == "unknown"
assert classify_instance_family(None)[0] == "unknown"

# ---------------------------------------------------------------------------
# Host-event semantics (the event variants this tier actually receives)
# ---------------------------------------------------------------------------
# Quoted verbatim from customer-visible notification text and engineer replies
# in real tickets. These are the customer-facing event type strings. The event
# type names are the documented `InstanceEventType.N` values of
# DescribeInstanceHistoryEvents (`aliyun ecs describe-instance-history-events
# --help`, CLI 3.4.5): SystemMaintenance.Reboot, SystemMaintenance.Redeploy,
# SystemMaintenance.IsolateErrorDisk, SystemMaintenance.ReInitErrorDisk,
# SystemFailure.Reboot, SystemFailure.Redeploy, SystemFailure.Delete, ...
HOST_EVENTS = {
    "SystemMaintenance.Reboot": {
        "kind": "planned",
        "title": "Planned maintenance reboot",
        "explanation": (
            "Alibaba Cloud detected a potential software/hardware risk on the "
            "underlying host of the instance and scheduled a planned "
            "maintenance reboot. The event notification is normally sent 24 to "
            "48 hours before execution. The notified time is a WINDOW, not a "
            "hard deadline: within that window you may reboot the instance "
            "yourself at a low-traffic time. During the maintenance the "
            "instance is migrated to a healthy host."
        ),
        "customer_misconception": (
            "This is a PLANNED event, not an unplanned forced reboot. The "
            "maintenance time is a window in which you can choose your own "
            "low-peak reboot moment."
        ),
    },
    "SystemMaintenance.Redeploy": {
        "kind": "planned",
        "title": "Planned maintenance redeploy (moves the instance to another host)",
        "explanation": (
            "The underlying host of the instance needs maintenance that a "
            "reboot alone cannot cover, so the event asks for the instance to "
            "be REDEPLOYED onto another physical host. This is a self-service "
            "action: from the ECS console event entry, or with the "
            "RedeployInstance operation, the instance is restarted on a healthy "
            "host. Prerequisites: the instance is Running or Stopped, it is not "
            "hosted on a Dedicated Host, it carries no security lock, and the "
            "account / instance is not in arrears past expiry. Redeploying "
            "restarts the instance, so in-memory data is lost and local disks "
            "may be re-initialized."
        ),
        "customer_misconception": (
            "A redeploy is not an outage the customer has to wait for a ticket "
            "to clear: the event tells you the instance must move, and the move "
            "can be started by the customer inside the notified window."
        ),
    },
    "SystemFailure.Redeploy": {
        "kind": "unexpected",
        "title": "Unexpected host failure redeploy (moves the instance to another host)",
        "explanation": (
            "The underlying host failed in a way that a reboot cannot recover "
            "from, so the instance must be redeployed onto a healthy host. The "
            "same self-service path as the planned redeploy applies: start the "
            "redeploy from the ECS console event entry or with the "
            "RedeployInstance operation. The same prerequisites apply (Running "
            "or Stopped, not on a Dedicated Host, no security lock, not in "
            "arrears past expiry) and the same risk applies (the instance "
            "restarts, in-memory data is lost, local disks may be "
            "re-initialized)."
        ),
        "customer_misconception": (
            "If the event is still Scheduled the customer can run the redeploy "
            "at a low-traffic moment; waiting does not repair the failed host."
        ),
    },
    "SystemMaintenance.IsolateErrorDisk": {
        "kind": "planned",
        "title": "Planned maintenance: faulty local disk isolated",
        "explanation": (
            "The platform detected a faulty LOCAL disk on the underlying host "
            "of this instance and isolates that disk as part of planned "
            "maintenance. Isolation protects the instance from further I/O "
            "errors on the faulty disk. This applies to instances that use "
            "local disks; cloud disks are not affected by this event. Follow "
            "the event notification: isolate the risk first if the instance "
            "still has data you need on that local disk, back up before any "
            "further maintenance step."
        ),
        "customer_misconception": (
            "This is not a reboot request and not a billing event: it is the "
            "platform removing a failing local disk from service."
        ),
    },
    "SystemMaintenance.ReInitErrorDisk": {
        "kind": "planned",
        "title": "Planned maintenance: faulty local disk re-initialized",
        "explanation": (
            "As a follow-up to isolating a faulty local disk, the platform "
            "re-initializes that disk during planned maintenance so the host "
            "returns to a healthy state. Re-initialization ERASES the data on "
            "the affected local disk, so any data still needed must be copied "
            "off the instance before the notified maintenance window. Cloud "
            "disks are not affected by this event."
        ),
        "customer_misconception": (
            "Re-initialization is destructive for the faulty local disk: "
            "treat the notification as a data-preservation deadline, not as a "
            "routine notice."
        ),
    },
    "SystemFailure.Reboot": {
        "kind": "unexpected",
        "title": "Unexpected host failure reboot",
        "explanation": (
            "The underlying host suffered an unexpected software/hardware "
            "failure, and the system force-rebooted the instance to recover "
            "it. The reboot usually completes within 2 to 5 minutes. Typical "
            "notification wording: the instance was rebooted to recover from "
            "an unexpected host software/hardware failure."
        ),
        "customer_misconception": (
            "An unexpected host failure cannot be fully prevented. You can "
            "reduce impact with a planned maintenance window, event "
            "notification subscription, multi-zone / multi-instance redundancy "
            "and regular data backups."
        ),
    },
}

# DescribeInstanceHistoryEvents defaults to "finished / non-active" events
# only, so every documented lifecycle status is sent explicitly: a still
# Scheduled maintenance event is exactly the case this tier asks about.
EVENT_CYCLE_STATUSES = (
    "Scheduled", "Avoided", "Executing", "Executed", "Canceled", "Failed",
    "Inquiring",
)

# DescribeDedicatedHosts `Status` is a SINGLE-value filter whose default is
# Available, so a host in a fault state never shows up in a default call.
# LIVE VERIFICATION (2026-10, CLI 3.4.5): only the three values below are
# accepted by the service. TempUnavailable and Redeploying are listed in the
# CLI help but the service answers InvalidStatus.ValueNotSupported for them
# ("The specified dedicated host status is not supported"), so they are NOT
# queried and must never be reported as checked.
DDH_STATUSES = ("Available", "UnderAssessment", "PermanentFailure")

# Documented but rejected by the live service - kept for reference only.
DDH_STATUS_NOT_QUERYABLE = ("TempUnavailable", "Redeploying")

# Plain-language meaning of each queryable DDH status (documented values only).
DDH_STATUS_NOTES = {
    "Available": "running normally",
    "UnderAssessment": (
        "physical-host risk: the host is still usable but a latent fault may "
        "already affect instances on it"
    ),
    "PermanentFailure": "permanent failure: the host is not usable",
}

# Inline assertions for the event / status tables (executed on import).
assert "SystemMaintenance.Reboot" in HOST_EVENTS
assert "SystemFailure.Reboot" in HOST_EVENTS
assert "SystemMaintenance.Redeploy" in HOST_EVENTS
assert "SystemFailure.Redeploy" in HOST_EVENTS
assert "SystemMaintenance.IsolateErrorDisk" in HOST_EVENTS
assert "SystemMaintenance.ReInitErrorDisk" in HOST_EVENTS
assert "SystemFailure.Reboot.Redeploy" not in HOST_EVENTS
for _event_name, _event in HOST_EVENTS.items():
    assert _event["kind"] in ("planned", "unexpected"), _event_name
    assert _event["title"] and _event["explanation"], _event_name
    assert _event["explanation"].lower().count("only a backend") == 0, _event_name
assert set(DDH_STATUSES) == set(DDH_STATUS_NOTES)
assert not set(DDH_STATUSES) & set(DDH_STATUS_NOT_QUERYABLE)
assert len(EVENT_CYCLE_STATUSES) == 7
assert set(RAM_ACTION_BY_API) >= {
    "DescribeInstanceHistoryEvents", "DescribeDedicatedHosts",
    "DescribeDiskMonitorData",
}

# ---------------------------------------------------------------------------
# Rule-based guidance blocks (the RO_QUERY "official answer" knowledge)
# ---------------------------------------------------------------------------

SLA_GUIDANCE = (
    "ECS availability compensation is APPLICATION-BASED, not automatic. Under "
    "the ECS service-level agreement in effect since 2018-02-01, you may apply "
    "for compensation for an instance that did not meet the committed "
    "availability AFTER the 5th business day of each month, for the previous "
    "month. Applying does not guarantee approval; the final decision is made by "
    "a human reviewer. This skill only explains the conditions and points to "
    "the self-service SLA claim entry; it never submits a claim, promises a "
    "payout, or performs any commercial / approval action."
)

MAINTENANCE_WINDOW_GUIDANCE = (
    "To reduce the impact of host maintenance: configure a planned maintenance "
    "window in the ECS console so reboots land in your low-traffic period; "
    "subscribe to instance event notifications so you receive "
    "SystemMaintenance.Reboot / SystemFailure.Reboot messages in advance; keep "
    "regular data backups; and for critical workloads use multi-instance / "
    "multi-zone redundancy. These are self-service configuration steps that the "
    "customer performs; this skill only lists the steps and never changes any "
    "setting."
)

HOST_MIGRATION_GUIDANCE = (
    "Moving an instance to a different host has TWO customer self-service "
    "paths, so a support ticket is NOT the normal route. Path 1 - after a "
    "SystemMaintenance.Redeploy or SystemFailure.Redeploy system event, "
    "redeploy the instance yourself: use the redeploy entry of that event in "
    "the ECS console, or call the RedeployInstance operation. Prerequisites: "
    "the instance is Running or Stopped, it is NOT hosted on a Dedicated Host, "
    "it carries no security lock, and the account / instance is not in arrears "
    "past expiry. Path 2 - to move an instance ONTO or BETWEEN Dedicated Hosts "
    "(or onto a deployment set), optionally changing the instance type in the "
    "same operation, call the ModifyInstanceDeployment operation with "
    "InstanceId and the target DedicatedHostId. Both paths restart the "
    "instance: in-memory data is lost and local disks may be re-initialized, "
    "the underlying hardware fingerprint changes, and third-party "
    "license-bound software may need re-activation - back up first. Raise a "
    "human support ticket only when the platform itself has to investigate the "
    "host hardware fault (for example the host is under assessment or in "
    "permanent failure and the customer cannot move off it), or when the "
    "instance is in a locked state that blocks self-service redeployment. This "
    "skill never performs either operation: it explains the paths and their "
    "prerequisites and leaves the execution to the customer."
)

STORAGE_CEILING_GUIDANCE = (
    "Every instance type and every cloud disk has a specification ceiling for "
    "IOPS and throughput (BPS). When a guest workload (for example heavy "
    "sequential reads) reaches that ceiling, I/O is throttled and ALL guest "
    "processes that read or write block: SSH may not return its banner, Cloud "
    "Assistant calls fail, and VNC becomes unresponsive, while the instance "
    "still shows as running. This is throttling at the specification ceiling, "
    "NOT necessarily a host failure. Check CloudMonitor for a 'performance "
    "reached the specification ceiling' style alarm. This skill reads the "
    "cloud-disk IOPS / BPS / latency series with DescribeDiskMonitorData "
    "(read-only) for a short recent window, so a live reading can be quoted "
    "instead of guessed. Per-process guest I/O is NOT available from any "
    "read-only API: install the CloudMonitor agent plus a process-level "
    "history tool (for example atop) on the instance, or read the console "
    "CloudMonitor chart, so the process that drove the I/O can be identified. "
    "The customer may also send a console screenshot back for interpretation."
)

ACCOUNT_VISIBILITY_GUIDANCE = (
    "Read-only Describe APIs only see resources inside the CURRENT credential "
    "account AND the specified RegionId. An empty result therefore does NOT "
    "prove the instance does not exist; it means the instance is not visible "
    "under this account/region. The two common causes are: the ticket was filed "
    "from a different account than the one that owns the instance, or the wrong "
    "region was queried. Re-run with the owning account's credential and the "
    "correct RegionId. This skill states this boundary honestly and never "
    "fabricates instance data."
)

DDH_GUIDANCE = (
    "Dedicated Host (DDH) is a physical server dedicated to a single customer "
    "account. You control which instances are placed on it, so no other "
    "tenant's workload shares the physical CPU. DDH suits strict isolation, "
    "compliance / licensing (bring-your-own-license) and eliminating "
    "noisy-neighbor contention. Creating or managing a Dedicated Host is a "
    "write / purchase action outside this read-only skill; this skill only "
    "explains the concept and the selection path, and points to the console."
)

CAPACITY_RESERVATION_GUIDANCE = (
    "A capacity reservation reserves instance capacity in a specific zone for a "
    "period, so the resources are guaranteed available when you launch "
    "instances. Elasticity assurance is the related guarantee for elastic "
    "scaling scenarios. Both are capacity-assurance products rather than "
    "diagnostic objects; purchasing or modifying a reservation is a write "
    "action outside this read-only skill. This skill only explains when each "
    "option fits and points to the console entry."
)

ISOLATION_SELECTION_GUIDANCE = (
    "To completely avoid CPU contention from other tenants, choose one of three "
    "isolation paths: (1) a DEDICATED instance family (g / c / r / u and "
    "similar) whose vCPU is exclusively scheduled; (2) Dedicated Host (DDH) for "
    "a whole physical host under your control; or (3) a capacity reservation / "
    "elasticity assurance to guarantee capacity in a zone. Shared families "
    "(e / s6 / xn4 / n4 / mn4 / e4) and burstable families (t series) share the "
    "physical CPU and can be slowed by noisy neighbors. Changing an instance "
    "type (reconfiguration) or purchasing DDH / reservations are write actions "
    "the customer performs in the console; this skill only compares the options "
    "and lists the steps, and never submits a change."
)

# ---------------------------------------------------------------------------
# Symptom routing keywords (lowercased substring match on the customer's own
# wording). Each entry maps to a guidance block key.
# ---------------------------------------------------------------------------
SYMPTOM_ROUTES = (
    (
        ("reboot", "restart", "maintenance", "systemmaintenance",
         "systemfailure", "host failure", "host-machine", "host machine",
         "underlying host", "crash", "down", "downtime", "compensation",
         "sla", "notification", "event", "redeploy", "re-deploy",
         "isolate", "reinit", "re-init", "error disk", "local disk"),
        "host_event",
    ),
    (
        ("contention", "noisy", "neighbor", "shared", "slow", "performance",
         "cpu", "dedicated", "family", "instance type", "instance-type",
         "selection", "burstable"),
        "isolation",
    ),
    (
        ("unresponsive", "frozen", "freeze", "hang", "ssh", "banner",
         "cloud assistant", "vnc", "iops", "bps", "throttl", "disk",
         "io ", "i/o", "stuck", "lag"),
        "storage_ceiling",
    ),
    (
        ("ddh", "dedicated host", "capacity reservation", "reservation",
         "elasticity assurance", "capacity", "byol", "license", "isolation"),
        "ddh_capacity",
    ),
    (
        ("not found", "cannot see", "can not see", "invisible", "missing",
         "wrong account", "which account", "visibility", "does not exist",
         "doesn't exist"),
        "visibility",
    ),
)
