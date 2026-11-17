#!/usr/bin/env python3
"""
_constants.py -- Embedded constants for ECS Expiry / Release / Data-Retention
=============================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (endpoints, query limits, lifecycle-rule constants
with their evidence tags, region scan candidates, verified help-doc URLs and
the guest-side non-mutating command guidance list) is embedded here as Python
constants. There are NO data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity & service endpoints
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-expiry-release-retention"

# Central (region-less) endpoints; regional ECS endpoints are resolved by the
# aliyun CLI from the --region flag.
STS_ENDPOINT = "sts.aliyuncs.com"
BSS_ENDPOINT = "business.aliyuncs.com"

# API versions (informational; the aliyun CLI carries its own metadata).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "bssopenapi": "2017-12-14",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# READ-ONLY whitelist note: order queries that this area does NOT call yet
# ---------------------------------------------------------------------------
# The entry script reaches the cloud only through the read actions it issues
# itself (Describe* / Query* above). Two further BSS actions are read-only and
# verified, but are deliberately kept OUT of the call surface for now, so the
# issued set stays exactly what references/ram-policies.md declares:
#
#   bssopenapi QueryOrders      (2017-12-14, RAM bss:DescribeOrderList, read)
#     aliyun bssopenapi query-orders --product-code ecs --payment-status Unpaid \
#         --order-type Renew --create-time-start 2026-01-01T00:00:00Z \
#         --create-time-end 2026-10-28T00:00:00Z --page-num 1 --page-size 50
#     Verified 2026-10-28 on aliyun CLI 3.4.5: --help confirms the parameter
#     names above; a live call returns Code=Success with
#     Data.TotalCount and Data.OrderList.Order[] rows carrying OrderId,
#     OrderType, PaymentStatus, CreateTime, SubscriptionType. The value is
#     spelled "Unpaid" / "Paid" / "Cancelled" (case-sensitive: "UNPAID" is
#     silently not applied and the unfiltered page comes back).
#   bssopenapi GetOrderDetail   (2017-12-14, RAM bss:DescribeOrderList, read)
#     aliyun bssopenapi get-order-detail --order-id <id>
#
# Wiring either one in requires the matching RAM grant to be declared first
# (it lives in references/ram-policies.md), and the "not verified by this
# run" wording in the entry script must be dropped in the same change.

# ---------------------------------------------------------------------------
# Timeouts / pagination limits (MUST 7.6.1: every external call is bounded)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60        # seconds, per CLI invocation
PAGE_SIZE = 100             # items per page for ECS PageNumber-style queries
MAX_PAGES = 20              # hard guardrail per pagination loop
BSS_PAGE_SIZE = 100
BSS_MAX_PAGES = 5           # BSS cross-check is best-effort; keep it small

# ---------------------------------------------------------------------------
# Lifecycle-rule constants (each carries its evidence tag; surfaced verbatim
# in reports so no number is ever presented without a source)
# ---------------------------------------------------------------------------

# Data-retention window after a SUBSCRIPTION instance expires and stops.
# Source: consistent front-line support statements [ticket:T-5E3EDF72]
# [ticket:T-263837C7] [ticket:T-63376A9B] [ticket:T-CD20304A]; the official
# subscription doc anchor is listed in DOC_URLS but its body was not
# crawled -> the value MUST always be rendered with the TO-VERIFY tag.
RETENTION_DAYS_SUBSCRIPTION = 15
RETENTION_DAYS_TAG = "[TO VERIFY: official subscription-doc confirmation pending]"

# SEPARATE rule (never mix with the retention window above): when the ACCOUNT
# is overdue for more than 15 days, existing SNAPSHOTS are released.
# Source: [ticket:T-0E502AF0].
OVERDUE_SNAPSHOT_RELEASE_DAYS = 15
OVERDUE_SNAPSHOT_TAG = "[ticket:T-0E502AF0]"

# Expiry-extension limits (manual, case-by-case approval; never promised).
# Source: [ticket:T-63376A9B].
EXTENSION_LIMITS = (
    "one account / one calendar year / one time / one day / one instance"
)
EXTENSION_LIMITS_TAG = "[ticket:T-63376A9B]"

# ---------------------------------------------------------------------------
# Region scan candidates (used ONLY when the user does not provide a region;
# a best-effort ordered list, never a silent single-region default). Regions
# that error during the scan are skipped with a [WARN] and the scan continues.
# ---------------------------------------------------------------------------

CANDIDATE_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-shenzhen",
    "cn-qingdao", "cn-zhangjiakou", "cn-huhehaote", "cn-wulanchabu",
    "cn-chengdu", "cn-guangzhou", "cn-heyuan", "cn-fuzhou",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3", "ap-southeast-5",
    "ap-northeast-1", "ap-south-1", "us-west-1", "us-east-1",
    "eu-central-1", "eu-west-1", "me-east-1", "me-central-1",
]

# ---------------------------------------------------------------------------
# Resource identifier normalization (C2)
# ---------------------------------------------------------------------------

RESOURCE_ID_PREFIXES = {
    "i-": "instance",
    "d-": "disk",
    "s-": "snapshot",
    "m-": "custom image",
}

# Intent enumeration (C12 routing aid; contains no disk-capacity/inode or
# billing-dispute intents on purpose -- those are handoff targets).
INTENTS = [
    "expiry_timeline",
    "stop_billing",
    "recoverability",
    "point_in_time",
    "extension",
    "backup_feasibility",
    "ip_retention",
    "unclassified",
]

# ---------------------------------------------------------------------------
# Guest-side NON-MUTATING commands (manual guidance only -- this skill never
# executes anything inside the instance; the customer runs these via the
# console remote connection and pastes the output back).
# ---------------------------------------------------------------------------

GUEST_COMMAND_GUIDANCE = {
    "linux": [
        "df -h",
        "df -i",
        "du -x --max-depth=1 <path>",
        "findmnt",
        "stat <path>",
        "ls -l <path>",
    ],
    "windows": [
        "Get-Volume",
        "Get-PSDrive",
        "Get-ChildItem <path>",
    ],
}

# ---------------------------------------------------------------------------
# Verified help-documentation URLs (taken verbatim from the tier evidence;
# documents whose titles were not confirmed are deliberately absent -- never
# fabricate a URL).
# ---------------------------------------------------------------------------

DOC_URLS = {
    "subscription_overview": (
        "https://help.aliyun.com/zh/ecs/product-overview/"
        "subscription#9bfa29b0407gc"
    ),
    "free_trial_expiry": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md"
    ),
    "free_trial_common_ops": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "common-operations-for-the-ecs-free-trial.md"
    ),
    "payg_starter_guide": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "ecs-pay-as-you-go-starter-guide.md"
    ),
    "renewal_change": (
        "https://help.aliyun.com/zh/ecs/user-guide/renewal-change.md"
    ),
    "renewal_downgrade": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "downgrade-instance-configurations-during-renewal.md"
    ),
    "instance_overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/overview-52.md"
    ),
    "spot_data_retention": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "preemptible-instance-data-retention-and-data-recovery-after-"
        "interrupt-reclamation.md"
    ),
    "release_instance": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "release-an-instance#589b9e87d0m16"
    ),
    "stop_instance": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "stop-an-instance#1dbe594a8082k"
    ),
    "economical_mode": (
        "https://help.aliyun.com/zh/ecs/user-guide/economical-mode"
    ),
    "data_protection_comparison": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "select-the-appropriate-ecs-data-protection-scheme-snapshot-and-"
        "file-backup-essential-edition.md"
    ),
    "create_snapshot": (
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot"
    ),
    "snapshot_overview": (
        "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1"
    ),
    "rollback_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "roll-back-a-disk-by-using-a-snapshot-1"
    ),
    "create_disk_from_snapshot": (
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot"
    ),
    "attach_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk"
    ),
    "detach_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk"
    ),
    "create_spot_instance": (
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-spot-instance"
    ),
    "ip_to_eip": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "convert-the-public-ip-address-of-an-instance-in-a-vpc-to-an-eip"
    ),
    "unsubscription_rules": (
        "https://help.aliyun.com/zh/user-center/user-guide/unsubscription-rules"
    ),
    "refund_destinations": (
        "https://help.aliyun.com/zh/user-center/user-guide/refund-destinations"
    ),
}
