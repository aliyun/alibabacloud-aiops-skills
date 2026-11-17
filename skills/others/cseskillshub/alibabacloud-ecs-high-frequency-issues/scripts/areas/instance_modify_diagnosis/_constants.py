#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Instance-Modify Diagnosis
=======================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so all
static reference data (API metadata, spec-change feasibility rules, error-code
semantics distilled from real ECS support tickets) is embedded here as Python
constants. There are NO data files in this skill.
"""

# ---------------------------------------------------------------------------
# API metadata (verified real via `aliyun ecs <Action> --help`, CLI 3.4.5)
# ---------------------------------------------------------------------------

# ECS is a regional service: the CLI resolves ecs.<region>.aliyuncs.com from
# --region, so no fixed endpoint is pinned here. STS is central (region-less).
STS_ENDPOINT = "sts.aliyuncs.com"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

SKILL_NAME = "alibabacloud-ecs-instance-modify-diagnosis"

DEFAULT_REGION = "cn-hangzhou"

# Pagination guardrails (ECS DescribeInstances uses PageNumber/PageSize).
MAX_RESULTS = 100
MAX_PAGES = 20

# ---------------------------------------------------------------------------
# DescribeResourcesModification / DescribeAvailableResource enums (verified
# from the CLI --help parameter documentation)
# ---------------------------------------------------------------------------

# DestinationResource accepted values for the two feasibility APIs.
DESTINATION_RESOURCE_INSTANCE_TYPE = "InstanceType"
DESTINATION_RESOURCE_SYSTEM_DISK = "SystemDisk"

# OperationType for a spec change (DescribeResourcesModification).
OPERATION_TYPE_UPGRADE = "Upgrade"
OPERATION_TYPE_DOWNGRADE = "Downgrade"

# ---------------------------------------------------------------------------
# Instance charge types (DescribeInstances InstanceChargeType)
# ---------------------------------------------------------------------------
INSTANCE_CHARGE_TYPES = {
    "PrePaid": "Subscription (prepaid). Spec change follows the upgrade/downgrade "
               "order flow; a downgrade may be restricted by the discount window.",
    "PostPaid": "Pay-as-you-go. Spec change takes effect after the instance is "
                "stopped (Stopped) and then started again; the new spec bills "
                "from the next start.",
}

# Instance status values that gate a spec change (DescribeInstances Status).
STATUS_RUNNING = "Running"
STATUS_STOPPED = "Stopped"
MODIFY_REQUIRES_STOP = {
    "PostPaid": ("A pay-as-you-go instance must be in Stopped status (and stopped "
                 "in the console with 'No Fees for Stopped Instances' considered) "
                 "before most spec changes; a Running instance returns "
                 "IncorrectInstanceStatus."),
    "PrePaid": ("A subscription upgrade can run while Running but the instance is "
                "restarted during the change; plan a maintenance window."),
}

# ---------------------------------------------------------------------------
# Error codes / customer-visible error strings for this tier (from the ticket
# analysis: OperationDenied.NoStock and StoragePerformanceReachLimit are the
# quotable strings; the others are the standard spec-change blockers).
# ---------------------------------------------------------------------------
ERROR_CODES = {
    "OperationDenied.NoStock": {
        "meaning": "The requested instance type / zone has no available stock "
                   "(sold out), so a new purchase or a spec change to that target "
                   "cannot be fulfilled right now.",
        "guidance": "Try another zone in the same region, another instance type of "
                    "the same family, or a different charge type; stock refills over "
                    "time. This skill only reports availability -- it never places "
                    "an order.",
    },
    "StoragePerformanceReachLimit": {
        "meaning": "A disk/performance-level limit was reached for the target "
                   "configuration (e.g. the ESSD performance level cap for the "
                   "chosen instance type / disk size).",
        "guidance": "Choose a target instance type or disk performance level within "
                    "the allowed ceiling; check the instance-type family limits "
                    "before retrying the change.",
    },
    "IncorrectInstanceStatus": {
        "meaning": "The instance is not in a status that allows the requested "
                   "operation (e.g. a spec change on a Running pay-as-you-go "
                   "instance that must be Stopped first).",
        "guidance": "Confirm the instance status from DescribeInstances and follow "
                    "the stop/start requirement for the charge type before "
                    "retrying (manual action by the user; this skill is read-only).",
    },
    "InvalidInstanceId.NotFound": {
        "meaning": "The instance id does not exist in the given region for the "
                   "current credential.",
        "guidance": "Verify the instance id AND the region (a wrong --region is the "
                    "most common cause); the credential's account must own the "
                    "instance.",
    },
    "OperationDenied": {
        "meaning": "The operation is denied for the current instance state or "
                   "account (generic denial).",
        "guidance": "Read the returned Message for the specific reason; common "
                    "causes are an in-progress order, an unpaid renewal, or a "
                    "change-window restriction.",
    },
}

# Resource-quota scenario: DescribeAccountAttributes returns account-level
# attributes (region-scoped). Per-instance-type purchase quota lives in the
# Quotas Center console; this skill reports the returned attributes and points
# there rather than guessing attribute names.
QUOTA_CONSOLE_PATH = (
    "Console > ECS > Instance Quota / Quotas Center, or the account "
    "real-name and resource limits shown by DescribeAccountAttributes."
)

# ---------------------------------------------------------------------------
# Feasibility knowledge (root causes distilled from real tickets; readable
# version in references/instance-modify-diagnosis__spec-modify-guide.md)
# ---------------------------------------------------------------------------
MODIFY_NOT_EFFECTIVE_RULES = [
    "A spec change (upgrade/downgrade) does NOT take effect until the instance "
    "is restarted (pay-as-you-go) or the change order completes and the instance "
    "reboots (subscription). If vCPU/memory still show the old values inside the "
    "OS, the change has not been applied yet -- re-check DescribeInstances "
    "InstanceType and the instance Status.",
    "Inside the OS, confirm the new vCPU/memory with the system profiler; the "
    "control-plane InstanceType is authoritative for what was actually changed.",
    "A downgrade may be blocked by the discount window of a subscription "
    "instance or by the target type being unavailable in the zone (NoStock).",
]

PURCHASE_FAILURE_RULES = [
    "Purchase/create failures are dominated by stock (OperationDenied.NoStock) "
    "and by account quota/real-name limits, not by the order UI.",
    "Check availability of the target instance type in the target zone "
    "(DescribeAvailableResource) BEFORE concluding that a purchase should work.",
    "If the account is not real-name verified or a quota is reached, the create "
    "call is denied; DescribeAccountAttributes surfaces the account-level "
    "attributes and the Quotas Center holds the per-type purchase quota.",
]
