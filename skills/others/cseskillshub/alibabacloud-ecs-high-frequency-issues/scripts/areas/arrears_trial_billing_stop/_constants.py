#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS Arrears / Trial / Billing-Stop
============================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads, writes or caches
any AccessKey ID / Secret / STS token; authentication is resolved exclusively
by the aliyun CLI default credential chain. No AK/SK handling in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (endpoints, region sweep list, console paths,
official document links, guidance texts, the mandatory risk-disclosure gate,
handoff keyword map) is embedded here as Python constants.
"""

# ---------------------------------------------------------------------------
# Skill identity / observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-arrears-trial-billing-stop"

# ---------------------------------------------------------------------------
# API metadata (all five actions below were verified against the batch
# api-info contract and against `aliyun <product> <action> --help` metadata;
# versions are the ones the aliyun CLI itself reports for each product).
# ---------------------------------------------------------------------------

# Central BSS (billing) endpoint -- region-less service.
BSS_ENDPOINT = "business.aliyuncs.com"
# Central STS endpoint -- region-less service.
STS_ENDPOINT = "sts.aliyuncs.com"

API_VERSIONS = {
    "bssopenapi": "2017-12-14",
    "sts": "2015-04-01",
    "ecs": "2014-05-26",
    "cms": "2019-01-01",
}

# Default region used only for the region-less central services (BSS/STS);
# region-scoped calls always carry their own RegionId.
DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Query limits / timeouts
# ---------------------------------------------------------------------------

# Per-call subprocess timeout for one aliyun CLI invocation (7.6.1).
DEFAULT_TIMEOUT = 60
# Hard guardrail on pagination loops.
MAX_PAGES = 20
# DescribeInstances page size (API maximum is 100).
PAGE_SIZE = 100
# Max number of instances one metric-evidence loop will check.
MAX_USAGE_CHECK_INSTANCES = 10

# ---------------------------------------------------------------------------
# Region sweep list (EMBEDDED CONSTANT -- not an API call)
# ---------------------------------------------------------------------------
# Why a constant: the billable resource for this tier is very often in a
# region OUTSIDE the customer's default console view (observed repeatedly in
# support tickets: snapshots left in North China, South China, etc.), and
# DescribeInstances requires an explicit RegionId. A region-enumeration API
# (DescribeRegions) is NOT part of this skill's authorized action set, so the
# sweep walks this built-in list instead. The list covers the mainland-China
# regions plus the most-used overseas regions; it can be overridden with
# --regions. Users are told in the report that the list is a fixed default.
SWEEP_REGIONS = [
    "cn-hangzhou",
    "cn-shanghai",
    "cn-beijing",
    "cn-shenzhen",
    "cn-zhangjiakou",
    "cn-huhehaote",
    "cn-wulanchabu",
    "cn-chengdu",
    "cn-heyuan",
    "cn-guangzhou",
    "cn-qingdao",
    "cn-hongkong",
    "ap-southeast-1",
]

# ---------------------------------------------------------------------------
# Official documentation and console links
# (every URL below was really cited by support engineers in the underlying
# tickets of this tier -- never add unverified links elsewhere)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    # Overdue-payment explanation for ECS.
    "overdue": "https://help.aliyun.com/zh/ecs/overdue-payments",
    # Pay-as-you-go starter guide (billing composition, arrears flow).
    "payg-guide":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "ecs-pay-as-you-go-starter-guide.md",
    # Instance lifecycle states overview (stopped vs expired vs released).
    "instance-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-52.md",
    # Stop an instance (console).
    "stop-instance":
        "https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md",
    # Start an instance (console).
    "start-instance":
        "https://help.aliyun.com/zh/ecs/user-guide/start-an-instance.md",
    # Economical mode (no-charges while stopped) -- conditions and exceptions.
    "economical-mode":
        "https://help.aliyun.com/zh/ecs/user-guide/economical-mode.md",
    # Release an instance.
    "release-instance":
        "https://help.aliyun.com/zh/ecs/user-guide/release-an-instance",
    # Create a single snapshot (backup before destructive cleanup).
    "create-snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    # Delete a snapshot (irreversible).
    "delete-snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1",
    # Snapshot billing / overview.
    "snapshot-billing": "https://help.aliyun.com/zh/ecs/snapshots-1",
    "snapshot-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview",
    # Pay-as-you-go billing explanation.
    "payg-billing": "https://help.aliyun.com/zh/ecs/pay-as-you-go-1",
    # Billing-method best practice (pay-as-you-go vs subscription).
    "billing-best-practice":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "best-practices-for-ecs-billing-methods.md",
    # Change billing method: subscription -> pay-as-you-go. NOTE: this is the
    # direction OPPOSITE to "convert a pay-as-you-go trial instance to
    # subscription"; pick the doc that matches the customer's direction.
    "convert-sub-to-payg":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "change-the-billing-method-of-an-instance-from-subscription-to-"
        "pay-as-you-go",
    # Create a custom image (data migration between instances).
    "create-custom-image":
        "https://help.aliyun.com/document_detail/35109.html",
    # VPC and vSwitch deletion.
    "vpc-delete": "https://help.aliyun.com/zh/vpc/vpc-and-vswitch",
    # Bills of a burstable instance (example of reading bills per item).
    "view-bills":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "view-bills-of-a-burstable-instance.md",
    # What is ECS (resource composition).
    "what-is-ecs": "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md",
}

CONSOLE_LINKS = {
    # ECS console home.
    "ecs-home": "https://ecs.console.aliyun.com/home",
    # Snapshot console (region-scoped page; region token switches per view).
    "snapshot": "https://ecs.console.aliyun.com/snapshot",
    # Bill / expense detail export.
    "expense-detail":
        "https://usercenter2.aliyun.com/finance/expense-report/expense-detail",
    # My orders list (order vs account-ID confusion countermeasure).
    "orders": "https://billing-cost.console.aliyun.com/order/list",
    # Security Center (SAS) pay-as-you-go items page (cross-product handoff;
    # tracking parameters of the ticket-cited URL stripped, same entry).
    "sas": "https://yundun.console.aliyun.com/?p=sas",
}

# ---------------------------------------------------------------------------
# Mandatory risk-disclosure gate (replaces a write-confirmation gate, because
# this skill performs zero writes; support engineers stated every one of
# these in the underlying tickets). Whenever the report outputs any
# release / delete / cleanup guidance, ALL of these MUST be shown together.
# ---------------------------------------------------------------------------

RISK_GATE = [
    "Release/delete operations are irreversible: instance disks, released "
    "cloud disks and deleted snapshots lose their data permanently; "
    "unrecoverable even by Alibaba Cloud support.",
    "Back up first: create a snapshot or a custom image before any release "
    "or deletion; the support process always asks the customer to do this.",
    "Backups are not free: snapshots bill storage charges on their own, and "
    "deleting a snapshot is itself irreversible.",
    "Deleting snapshots alone is not enough: also delete the auto snapshot "
    "policy that created them, otherwise new snapshots keep being created "
    "and charges recur.",
    "Expect delayed statements: after cleanup you may still receive bills "
    "for usage accrued before release (billing statement delay), which does "
    "NOT mean billing continued.",
    "Nobody executes release/deletion for you: this skill (and support "
    "engineers) never operate these destructive actions on your behalf; the "
    "console steps below are for you to perform manually.",
]

# ---------------------------------------------------------------------------
# Console self-check paths for resources this skill cannot enumerate via the
# authorized read set (their query APIs are not part of the verified
# contract). Every degraded conclusion must point at these instead of
# guessing.
# ---------------------------------------------------------------------------

DEGRADED_ENUMERATION = [
    "Snapshots per region: ECS console > Storage & Snapshots > Snapshots "
    "(switch the region selector top-left through every region you have "
    "ever used) -- " + CONSOLE_LINKS["snapshot"],
    "Auto snapshot policies per region: ECS console > Storage & Snapshots > "
    "Auto Snapshot Policy -- resources created by a policy keep charging "
    "even after manual deletion of the snapshots.",
    "Standalone (unattached) pay-as-you-go disks per region: ECS console > "
    "Storage & Snapshots > Disks. A detached disk keeps billing until "
    "released.",
    "Elastic IP addresses (EIP) per region: VPC console > Elastic IP "
    "Addresses. An EIP not bound to an instance keeps billing.",
    "Custom images: ECS console > Images > Custom Images (images beyond the "
    "free quota can incur charges).",
    "VPC / vSwitch leftovers: VPC console > VPCs per region.",
]

# ---------------------------------------------------------------------------
# Evidence-claim policy strings (anti-hallucination): numeric retention
# periods seen only in ticket wording stay qualitative until an authoritative
# document confirms them.
# ---------------------------------------------------------------------------

RETENTION_QUALIFIED = (
    "After an account becomes overdue, pay-as-you-go resources enter "
    "restricted states and, beyond the retention window stated in the "
    "official overdue-payment document, resources and snapshots may be "
    "released/deleted automatically and irreversibly. Exact day counts are "
    "NOT stated here: the authoritative figure must be read from the "
    "official document below (ticket wording alone is not quoted as fact)."
)

# ---------------------------------------------------------------------------
# Handoff keyword map: symptom keywords in the customer's own wording that
# belong to an ADJACENT skill / channel (identify + hand off; this skill
# still completes the account-side exclusion first when possible).
# ---------------------------------------------------------------------------

HANDOFF_MAP = {
    "connectivity / security group / route / SSH password": [
        "ssh", "cannot connect", "can't connect", "connect timed out",
        "security group", "port not open", "password", "vnc", "route",
        "website unreachable after restart",
    ],
    "instance start/stop state diagnosis "
    "(area:instance-state-diagnosis)": [
        "stuck starting", "stuck stopping", "boot fail", "cannot start",
        "does not boot", "restart loop",
    ],
    "disk expansion diagnosis "
    "(area:disk-expand-diagnosis)": [
        "expansion not effective", "partition not extended", "disk resize",
        "growpart",
    ],
    "disk IO diagnosis (area:resource-bottleneck)": [
        "io slow", "high iops", "disk latency", "performance not reach",
    ],
    "disk capacity cleanup (disk-capacity tier skill)": [
        "disk full", "inode", "no space left on device", "too many files",
    ],
    "network attack response (DDoS / blackhole / tampering)": [
        "ddos", "blackhole", "黑洞", "hacked", "tampered", "attack",
    ],
    "ICP filing (record-keeping) consultation": [
        "filing", "beian", "icp", "备案",
    ],
    "commercial support: refund / unsubscription / account cancellation / "
    "subject transfer / payment restriction": [
        "refund", "unsubscribe", "cancel my account", "close my account",
        "transfer the account", "entity change", "cannot pay", "payment "
        "failed", "退费", "注销",
    ],
    "Security Center (SAS) trial / pay-as-you-go entitlement": [
        "security protection free trial", "security center expir",
        "云安全中心",
    ],
    "free-trial campaign page eligibility (image/region/plan choices)": [
        "no windows option", "campaign page", "trial page has no",
        "99 activity", "199 activity",
    ],
}

# ---------------------------------------------------------------------------
# Guidance texts (manual steps only -- this skill executes nothing)
# ---------------------------------------------------------------------------

GUIDE_RESUME = [
    "1. Top up the account until the available amount is positive again "
    "(Expenses and Costs console > Account > top up).",
    "2. Keep a buffer balance: pay-as-you-go items (instance if not in "
    "economical mode, EIP retention, snapshots) keep deducting from the "
    "balance, and a new shortfall re-triggers the stop/lock.",
    "3. After the balance recovers, check whether the stopped instance can "
    "be started again in the ECS console (start action is the customer's; "
    "see the start-instance doc).",
    "4. If the instance has already been auto-released past the retention "
    "window, the data is gone; the service cannot be 'restored' -- rebuild "
    "from any backup you kept.",
]

GUIDE_STOP_BILLING = [
    "Order matters: back up -> release the instance -> release standalone "
    "disks -> delete snapshots -> delete the auto snapshot policy -> "
    "release EIP -> remove VPC/vSwitch leftovers.",
    "Stop != no charges: stopping a pay-as-you-go instance only stops some "
    "items under the economical mode; disks, snapshots, EIP and images keep "
    "billing while they exist. Only release/delete stops billing.",
    "Detach != release: a data disk detached from an instance keeps "
    "charging until it is released in the ECS console (Block Storage).",
    "Delete the generating policy too: remove the auto snapshot policy, or "
    "deleted snapshots come back and keep charging.",
    "Re-verify next cycle: run this script again with the next "
    "BillingCycle; residual product rows with new charges mean something "
    "is still alive in some region.",
]

# ---------------------------------------------------------------------------
# Common CloudMonitor items for the OPTIONAL usage-evidence step (cms
# DescribeMetricLast). Only items listed here are sent; any other metric
# name must come from the CloudMonitor metric documentation, never be
# invented on the fly.
# ---------------------------------------------------------------------------

CMS_ECS_NAMESPACE = "acs_ecs_dashboard"
CMS_ALLOWED_METRICS = [
    "CPUUtilization",     # agent-level CPU usage %
    "InternetOutRate",    # public-network outbound bits per second
    "IntranetOutRate",    # private-network outbound bits per second
    "DiskReadBPS",        # disk read bytes per second
    "DiskWriteBPS",       # disk write bytes per second
]
