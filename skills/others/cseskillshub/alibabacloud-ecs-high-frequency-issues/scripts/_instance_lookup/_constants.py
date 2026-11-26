#!/usr/bin/env python3
"""
_constants.py -- embedded static data for ECS console resource lookup
=====================================================================
SECURITY: This skill is strictly READ-ONLY. Authentication is resolved by the
aliyun CLI default credential chain only. This module never reads, prints,
caches or passes any key material, and contains no credential literals.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
every static table this skill relies on (region sweep list, status semantics,
console entry map, concept glossary, button-gating rules, error cards, handoff
routes) is embedded here as Python constants. No data files exist in scripts/.

Knowledge provenance: root causes, console paths and URLs below were distilled
from real support-ticket conversations and the verified console links they
contain (requirements doc sections 2, 4 and 6). Anything without a ticket or
api-info source is deliberately absent -- never fabricated.
"""

# ---------------------------------------------------------------------------
# Skill identity and observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-high-frequency-issues"

# User-Agent attached to every CLI call of a run (observability rule SA-2.11).
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill-name}/{session-id}"

# ---------------------------------------------------------------------------
# API metadata (verified api-info surface for this tier)
# ---------------------------------------------------------------------------

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# Central, region-less STS endpoint.
STS_ENDPOINT = "sts.aliyuncs.com"

# ---------------------------------------------------------------------------
# Timeouts and limits (MUST 7.6.1: every CLI call carries a timeout)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60          # per-call timeout seconds, every subprocess run
CLI_TIMEOUT = 60              # alias used by callers building one command
STS_TIMEOUT = 30              # identity pre-flight is a single small call
PAGE_SIZE = 50                # DescribeInstances page size
MAX_PAGES = 10                # pagination guardrail per region+filter query
MAX_SWEEP_REGIONS = 40        # guardrail on --regions overrides
MAX_INSTANCE_IDS = 10         # status cross-check batch cap per API call

# ---------------------------------------------------------------------------
# Region sweep list (cross-region exhaustive lookup: core action C1)
# ---------------------------------------------------------------------------
# Embedded snapshot of commonly available public ECS region ids. The list is a
# convenience default, not an authority: `--region-hint` is queried FIRST and
# `--regions` replaces or extends the sweep, and every report states the exact
# list that was queried (no silent scope claims). Regions retired for an
# account answer with an API error that the sweep records and continues past.
DEFAULT_SWEEP_REGIONS = [
    "cn-hangzhou", "cn-shanghai", "cn-beijing", "cn-qingdao",
    "cn-zhangjiakou", "cn-huhehaote", "cn-wulanchabu", "cn-heyuan",
    "cn-guangzhou", "cn-shenzhen", "cn-chengdu", "cn-nanjing",
    "cn-fuzhou", "cn-wuhan-lr", "cn-hongkong", "ap-northeast-1",
    "ap-northeast-2", "ap-southeast-1", "ap-southeast-2",
    "ap-southeast-3", "ap-southeast-5", "ap-southeast-6",
    "ap-southeast-7", "us-east-1", "us-west-1", "eu-central-1",
    "eu-west-1", "me-east-1", "me-central-1",
]

# ---------------------------------------------------------------------------
# Instance status semantics (C2: control-plane reading vs console display)
# ---------------------------------------------------------------------------
# DescribeInstances / DescribeInstanceStatus return the control-plane
# (management) state. A console display is a view of that same state; the two
# agree once the right region/account view is selected. OS-level reality
# (booted, services up, disk mounted inside the OS) is a SECOND layer the
# cloud state does not prove.
INSTANCE_STATUS_MEANING = {
    "Pending": "created, waiting for the start workflow to take it over",
    "Running": "control plane reports running; it does NOT prove the OS, a "
               "service, or a mounted disk is usable inside the instance",
    "Starting": "start in progress",
    "Stopping": "stop in progress",
    "Stopped": "stopped (a stopped subscription instance still bills)",
}

# A banner or card in the console can lag the control-plane state after an
# appeal/release is processed on the security side; the queried status is the
# objective anchor, the banner is display-side residue to verify there.
STATUS_SYNC_NOTE = (
    "Console banners and security/disposal reminders can lag the control-plane "
    "state that DescribeInstanceStatus reports; treat the queried status as "
    "the objective reading and verify any lingering banner in the console "
    "module that owns it."
)

# ---------------------------------------------------------------------------
# Charge-type gating (why buttons exist or do not: A6 evidence)
# ---------------------------------------------------------------------------
CHARGE_TYPE_NOTE = {
    "PrePaid": "subscription (package). Console actions gated by it: a "
               "subscription data disk cannot be detached until its billing "
               "method is converted to pay-as-you-go first; unsubscription "
               "eligibility is a commercial rule, not an API finding.",
    "PostPaid": "pay-as-you-go. Detach and release actions exist in the "
                "console but are customer-side, destructive, and never "
                "executed by this skill.",
}

# LockReason semantics (returned by DescribeInstances when locked).
LOCK_REASON_MEANING = {
    "Financial": "locked for overdue payment; settle the balance first, "
                 "resources may enter the expiry/release timeline afterwards",
    "Security": "locked by a security disposal; the disposal itself is owned "
                "by the security module / security console, not by ECS",
}

# ---------------------------------------------------------------------------
# Intake: the minimum question card (anti-pattern: ticket T-19C9B029 closed
# unanswered because "cannot find the entry" named no function at all)
# ---------------------------------------------------------------------------
INTAKE_QUESTIONS = [
    "Which resource is missing: instance, disk, snapshot, image, or a console "
    "page/entry?",
    "The exact identifier if known (instance id i-..., disk id d-..., "
    "snapshot id s-...), or the instance name / IP address.",
    "Which region does the console currently show in its top-left region "
    "switcher, and did the resource live in another region?",
    "Are there several accounts (different login phone numbers / member "
    "accounts), and is the resource possibly under one you are not logged "
    "into right now?",
    "Is the console the ECS console at all, or could the resource be a "
    "Simple Application Server (SAS/SWAS), an order, or another product?",
    "For a missing button/entry: the exact button text or menu you expected, "
    "the device (PC browser or phone app), and any error text shown.",
]

# Asked when the sweep finds nothing anywhere (A1 residual causes).
NOT_FOUND_FOLLOWUPS = [
    "Wrong account: buy and creation actions under another account place the "
    "resource in that account's console; log out and check each account.",
    "Wrong product: Simple Application Server instances never appear in the "
    "ECS instance list -- open the SAS console instead.",
    "Already expired or released: resources past their expiry enter the "
    "release timeline and disappear from lists; this is a lifecycle question "
    "(see the handoff route), not a lookup failure.",
    "Auto snapshot policies paused by overdue payment plus short auto-snapshot "
    "retention can leave 'missing snapshots' with nothing left to find.",
    "Resource group filter: a resource-group filter stuck in the console "
    "hides resources outside it; switch the view to the account scope.",
]

# ---------------------------------------------------------------------------
# Console entry map (C3 data source: ONLY links actually verified in real
# ticket conversations; requirements doc section 4.2)
# ---------------------------------------------------------------------------
ENTRY_MAP = {
    "ecs-instance-list": {
        "title": "ECS instance list (one region at a time)",
        "say": "The instance list always shows ONE region: switch the region "
               "in the top-left corner; the list is region-scoped, not "
               "account-global.",
        "url": "https://ecs.console.aliyun.com/server/region/cn-hangzhou#/",
        "tickets": ["T-69E628E3", "T-804A0640"],
    },
    "ecs-snapshot-list": {
        "title": "ECS snapshot list",
        "say": "Snapshots are also region-scoped: check each region the "
               "source disk lived in.",
        "url": "https://ecs.console.aliyun.com/snapshot",
        "tickets": ["T-D52AE555"],
    },
    "ecs-security-groups": {
        "title": "ECS security group list",
        "say": "Security groups live per region and per VPC.",
        "url": "https://ecs.console.aliyun.com/securityGroup/region/cn-hangzhou",
        "tickets": ["T-A250313A"],
    },
    "purchasable-region-spec": {
        "title": "Purchasable regions and instance types for this account",
        "say": "When a region is not selectable on the buy page, check which "
               "regions/specs the current account may buy before assuming a "
               "console bug; real-name verification status and overdue "
               "balance also gate visibility.",
        "url": "https://ecs-buy.aliyun.com/instanceTypes/#/instanceTypeByRegion",
        "tickets": ["T-8D8F2AD9"],
    },
    "ram-console": {
        "title": "RAM console overview (users, roles, policies)",
        "say": "RAM users are created in the RAM console, not in the ECS "
               "console; an ECS-side search for a RAM user always comes back "
               "empty.",
        "url": "https://ram.console.aliyun.com/overview?activeTab=overview",
        "tickets": ["T-8AA82DFC"],
    },
    "order-list": {
        "title": "Order list (billing center)",
        "say": "Purchases such as saved plans appear as orders here, not in "
               "the ECS console.",
        "url": "https://billing-cost.console.aliyun.com/order/list",
        "tickets": ["T-DF87AF28"],
    },
    "refund-page": {
        "title": "Unsubscription / refund self-service",
        "say": "Refunds and unsubscription run through the billing self-"
               "service channel and remain commercial processes; this skill "
               "only navigates, it never executes them.",
        "url": "https://billing-cost.console.aliyun.com/refund/refund",
        "tickets": ["T-B2672FDF"],
    },
    "contract-management": {
        "title": "Contract management (server access agreement for ICP "
                 "filing)",
        "say": "The ICP-filing 'server access agreement' is a service "
               "contract, generated in the billing console, not an ECS page.",
        "url": "https://billing-cost.console.aliyun.com/contract/manage",
        "tickets": ["T-2000646E"],
    },
    "eip-console": {
        "title": "EIP list (VPC console)",
        "say": "Elastic IP addresses are managed in the VPC console, not the "
               "ECS console.",
        "url": "https://vpc.console.aliyun.com/eip/cn-shenzhen/eips",
        "tickets": ["T-AB34E2B9"],
    },
    "dns-console": {
        "title": "Alibaba Cloud DNS domain list",
        "say": "A domain is never 'bound' to a server to unbind; pointing a "
               "domain at or away from an instance means editing DNS "
               "resolution records here.",
        "url": "https://dns.console.aliyun.com/#/dns/domainList",
        "tickets": ["T-F66F330B"],
    },
    "dns-probe": {
        "title": "Public DNS propagation probe",
        "say": "Check whether a resolution change is already visible "
               "publicly before suspecting the server.",
        "url": "https://boce.aliyun.com/detect/dns",
        "tickets": ["T-F66F330B"],
    },
    "wanxiaozhi-console": {
        "title": "Wanxiaozhi website builder console",
        "say": "Domain binding for Wanxiaozhi-built sites happens in the "
               "site's own console, not in ECS.",
        "url": "https://dc.console.aliyun.com/next/index#/xiaozhi",
        "tickets": ["T-AFD53C57"],
    },
}

# ---------------------------------------------------------------------------
# DescribeAvailableResource usage note (buy-page visibility, C5)
# ---------------------------------------------------------------------------
# DestinationResource values accepted by the verified parameter surface; keep
# to the common ones the tickets actually discuss.
DESTINATION_RESOURCES = [
    "Zone", "InstanceType", "SystemDisk", "DataDisk", "Network",
    "ReservedInstance", "DDH", "ElasticStorage",
]

AVAILABILITY_NOTE = (
    "DescribeAvailableResource reports what the account may CREATE in the "
    "given region for the destination resource; it is queried here only to "
    "answer 'is this region/spec visible to me at all'. It never books, "
    "orders or changes anything, and purchasability of campaign prices is "
    "outside its scope."
)
