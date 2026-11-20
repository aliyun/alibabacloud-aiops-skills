#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for ECS IDC Address Query
================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AK/SK handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (endpoints, limits, the public region table,
confidentiality / handoff wording) is embedded here as Python constants.
There are NO data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-idc-address-query"

REPORT_BANNER = "READ-ONLY SKILL - NO CHANGES WERE MADE"

# ---------------------------------------------------------------------------
# Endpoints and API versions
# ---------------------------------------------------------------------------

# Central STS endpoint (region-less identity service). ECS itself is a
# regional service: the aliyun CLI resolves the regional ECS endpoint from
# the --region flag, so no fixed ECS endpoint constant is needed here.
STS_ENDPOINT = "sts.aliyuncs.com"

# Informational only; the aliyun CLI carries its own API metadata.
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Timeouts, retries and query limits
# ---------------------------------------------------------------------------

# Per-call timeout in seconds for every CLI subprocess invocation (MUST 7.6.1).
DEFAULT_TIMEOUT = 60

# Transient-error retry policy (linear backoff: 2s, then 4s).
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 2

# DescribeInstances accepts up to 100 instance IDs per call (JSON array)
# and a PageSize of up to 100.
MAX_IDS_PER_CALL = 100

# DescribeInstanceStatus page-size ceiling used for InstanceId.N batching.
STATUS_PAGE_SIZE = 50

# Hard guardrail on the number of pages fetched per pagination loop.
MAX_PAGES = 20

# ---------------------------------------------------------------------------
# Public region table (city-level public geographic names)
# ---------------------------------------------------------------------------
# Source: the public Alibaba Cloud region naming (the region list published
# in the official documentation and shown in the console region selector).
# HARD LIMIT: this table is CITY-LEVEL ONLY. District/street-level data-center
# addresses, facility names and rack positions are confidential and MUST
# NEVER be added here or stated by this skill. Regions not present in this
# table fall back to the raw-RegionId rule (never guess a city name).

REGION_CITY_MAP = {
    # Regions in mainland China
    "cn-qingdao": "Qingdao, mainland China",
    "cn-beijing": "Beijing, mainland China",
    "cn-zhangjiakou": "Zhangjiakou, mainland China",
    "cn-huhehaote": "Hohhot, mainland China",
    "cn-wulanchabu": "Ulanqab, mainland China",
    "cn-hangzhou": "Hangzhou, mainland China",
    "cn-shanghai": "Shanghai, mainland China",
    "cn-nanjing": "Nanjing, mainland China",
    "cn-fuzhou": "Fuzhou, mainland China",
    "cn-shenzhen": "Shenzhen, mainland China",
    "cn-heyuan": "Heyuan, mainland China",
    "cn-guangzhou": "Guangzhou, mainland China",
    "cn-chengdu": "Chengdu, mainland China",
    "cn-wuhan-lr": "Wuhan, mainland China",
    "cn-hongkong": "Hong Kong, China",
    # International regions
    "ap-southeast-1": "Singapore",
    "ap-southeast-2": "Sydney, Australia",
    "ap-southeast-3": "Kuala Lumpur, Malaysia",
    "ap-southeast-5": "Jakarta, Indonesia",
    "ap-southeast-6": "Manila, Philippines",
    "ap-southeast-7": "Bangkok, Thailand",
    "ap-northeast-1": "Tokyo, Japan",
    "ap-northeast-2": "Seoul, South Korea",
    "ap-south-1": "Mumbai, India",
    "us-west-1": "Silicon Valley, United States",
    "us-east-1": "Virginia, United States",
    "eu-west-1": "London, United Kingdom",
    "eu-central-1": "Frankfurt, Germany",
    "me-east-1": "Dubai, United Arab Emirates",
    "me-central-1": "Riyadh, Saudi Arabia",
    "na-south-1": "Mexico City, Mexico",
}

# Public enum semantics of DescribeAvailableResource zone categories
# (values are echoed verbatim; unknown categories are reported raw).
ZONE_STATUS_MEANINGS = {
    "WithStock": "resources are in stock and available for purchase in this zone",
    "ClosedWithStock": "sale is closed in this zone; existing stock remains",
    "WithoutStock": "no stock in this zone at query time",
}

# ---------------------------------------------------------------------------
# Canonical customer-facing wording (relayed verbatim by the reports)
# ---------------------------------------------------------------------------

CONFIDENTIALITY_NOTICE = (
    "Disclosure boundary: this report states region, zone and the public "
    "city-level geographic name of the region only. District-level or "
    "street-level data-center addresses, data-center facility or building "
    "names, and building/floor/rack/slot positions are confidential "
    "information: they are disclosed only by official support through the "
    "ticket channel after ownership verification. This tool never outputs "
    "or guesses them.")

CROSS_ACCOUNT_NOTICE = (
    "The target resource is not visible under the current credential "
    "(account UID {uid}). Resources of other accounts cannot be verified "
    "here for privacy and security reasons. Please open a support ticket "
    "from the account that owns the resource.")

RELEASED_INSTANCE_NOTICE = (
    "If the instance was released or expired, note that location details "
    "of released instances are not retained in queryable form and cannot "
    "be recovered through this tool. For historical proofs (contracts, "
    "stamped documents) use the order/contract channel with human support.")

DATA_SAFETY_REMINDER = (
    "Treat the returned location information as sensitive operational data "
    "and use it only for the stated compliance or operations purpose.")

TICKET_GUIDANCE = (
    "For the confidential detailed address, open a support ticket from the "
    "owning account (console: Support > Open Ticket). Official support "
    "verifies ownership and provides the disclosure permitted by policy; "
    "rack-level positions remain confidential in all cases.")

INPUT_GUIDANCE = (
    "To locate a physical deployment position, one resource identifier is "
    "required: an ECS instance ID (format i-xxxxxxxx, up to 100 IDs per "
    "run) or one public IP address of the instance. Both are visible in "
    "the ECS console under Instances (Instance ID column; public IP / EIP "
    "column). Please run the query with the credential of the account that "
    "owns the resource. The region ID is optional but narrows and speeds "
    "up the query.")

# ---------------------------------------------------------------------------
# Handoff matrix (adjacent requests recognized and routed, never answered
# from memory here). Mirrors references/handoff-and-inputs.md section 2.
# ---------------------------------------------------------------------------

HANDOFF_RULES = [
    {
        "request": "ICP filing process, filing blocking or filing status",
        "route_to": "alibabacloud-ecs-icp-filing-guide",
        "sentence": (
            "The ICP filing process itself is handled by the dedicated "
            "filing skill alibabacloud-ecs-icp-filing-guide; this skill "
            "provides the instance location evidence you can attach to the "
            "filing."),
    },
    {
        "request": "Recovering a released/expired instance or its data; "
                   "data-retention windows",
        "route_to": "the ECS instance lifecycle and data-retention skill "
                    "of the platform catalog",
        "sentence": (
            "Recovering released instances or data is a lifecycle topic; "
            "this skill only states that location details of released "
            "instances are not retained in queryable form."),
    },
    {
        "request": "Stamped location certificate, lease contract, official "
                   "paper document",
        "route_to": "offline human support (senior engineer via the ticket "
                    "channel)",
        "sentence": (
            "Such documents must be issued officially and are beyond this "
            "read-only tool; please open a ticket and request the document "
            "workflow. I can first prepare the instance and region "
            "evidence list for you."),
    },
    {
        "request": "Physical location of RDS, Redis, SLB or any non-ECS "
                   "resource",
        "route_to": "the support channel of that product",
        "sentence": (
            "This skill covers ECS instances only; for another product's "
            "resource location please use that product's console or "
            "support channel."),
    },
    {
        "request": "ISP/carrier access information or MAC-level disclosure",
        "route_to": "the ticket channel (no public self-service data "
                    "source in this iteration)",
        "sentence": (
            "Carrier/ISP access details have no public self-service data "
            "source in this iteration; please request them through a "
            "support ticket. No verified API field exists here, so this "
            "tool states that honestly instead of guessing."),
    },
    {
        "request": "Purchase, orders, contracts or pre-sales region "
                   "selection logistics",
        "route_to": "console purchase page / pre-sales channel",
        "sentence": (
            "Purchasing and contract logistics stay with the console and "
            "the pre-sales channel; this skill only reports zone "
            "availability as public information."),
    },
]
