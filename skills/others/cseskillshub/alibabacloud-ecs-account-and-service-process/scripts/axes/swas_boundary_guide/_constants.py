#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the SWAS Boundary Guide skill
======================================================================
SECURITY: This skill is strictly READ-ONLY. This module contains only
constants: API metadata, query limits, and the boundary-rule knowledge base
distilled from verified customer-support evidence and official documentation
links. It never reads or writes any credential. No AK/SK handling anywhere.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all reference data (boundary rules, connection matrix, handoff routes, plan
specifications) is embedded here as Python constants. There are NO data files.
"""

# ---------------------------------------------------------------------------
# Skill identity and observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-swas-boundary-guide"

# ---------------------------------------------------------------------------
# OpenAPI metadata (verified via api-info for this tier; read-only only)
# ---------------------------------------------------------------------------

API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# Endpoint template for regional ECS queries (the CLI resolves it from the
# region id when no explicit endpoint is given).
ECS_ENDPOINT_TEMPLATE = "ecs.{region}.aliyuncs.com"

# STS is a central service.
STS_ENDPOINT = "sts.aliyuncs.com"

DEFAULT_REGION = "cn-hangzhou"

# Per-call timeout (seconds) handed to every CLI subprocess invocation.
DEFAULT_TIMEOUT = 60

# Guardrails.
PAGE_SIZE = 50

# ---------------------------------------------------------------------------
# API whitelist: the ONLY OpenAPI actions this skill may invoke.
# Everything else must be refused at the code layer, not just by policy.
# ---------------------------------------------------------------------------

ECS_READ_WHITELIST = {
    "DescribeInstances",
    "DescribeInstanceStatus",
    "DescribeAvailableResource",
}

# ---------------------------------------------------------------------------
# Resource-id shape recognition (evidence-backed, see boundary rule cards)
# ---------------------------------------------------------------------------
# ECS instance ids start with "i-"; Simple Application Server instance ids
# are 32-character lowercase hex strings (e.g. seen in ticket 0001FS19PN).
ECS_ID_PREFIX = "i-"
SWAS_ID_HEX_LENGTH = 32

# ---------------------------------------------------------------------------
# Known subscription plans referenced by tickets (for migration checks on
# targets that are not purchased yet, so they cannot be queried via API).
# ---------------------------------------------------------------------------

KNOWN_PLANS = {
    "99yuan-ecs-economy-e": {
        "label": "99 CNY/year ECS activity plan (economy-type e instance)",
        "system_disk_gb": 40,
        "disk_category": "ESSD Entry",
        "vcpu": 2,
        "memory_gib": 2,
        "bandwidth_mbps": 3,
        "conditions": (
            "real-name verification required; limited to one instance per "
            "person; renewal at the activity price is not guaranteed after "
            "an image-based replacement"
        ),
        "docs": ["ACT99"],
        "evidence": "ticket 0001FS19PN",
    },
}

# ---------------------------------------------------------------------------
# Official documentation links (verified in the Phase-A evidence batch;
# ONLY these URLs may be emitted. Never add an unverified link.)
# ---------------------------------------------------------------------------

DOC_LINKS = {
    "WHAT_IS_SWAS": (
        "https://help.aliyun.com/zh/simple-application-server/"
        "product-overview/what-is-simple-application-server"
    ),
    "SWAS_SPEC_FAMILIES": "https://help.aliyun.com/document_detail/2861773.html",
    "EBM_OVERVIEW": "https://help.aliyun.com/zh/ecs/user-guide/elastic-bare-metal-server-overview",
    "SHARED_INSTANCE_FAMILIES": "https://help.aliyun.com/zh/ecs/user-guide/shared-instance-families.md",
    "MIGRATE_SERVERS": "https://help.aliyun.com/zh/ecs/user-guide/migrate-servers.md",
    "CLIENT_MANAGE_SWAS": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "use-alibaba-cloud-client-to-manage-simple-application-servers.md"
    ),
    "RESET_SWAS": (
        "https://help.aliyun.com/zh/simple-application-server/"
        "user-guide/reset-a-simple-application-server"
    ),
    "REPLACE_ECS_OS": "https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance-1",
    "PING_PROBE": "https://boce.aliyun.com/detect/ping",
    "ACT99": "https://www.aliyun.com/daily-act/ecs/99program",
}

# ---------------------------------------------------------------------------
# Boundary rule knowledge base (capability 2 of the design).
# Each rule carries its evidence ticket(s) and optional doc-link key.
# Rules marked evidence="summary" come from ticket summaries whose full
# dialogue was not yet re-verified; the script labels them as such.
# ---------------------------------------------------------------------------

BOUNDARY_TOPICS = {
    "product-identity": {
        "title": "What Simple Application Server is (product identity)",
        "rules": [
            {
                "text": (
                    "Simple Application Server instances are cloud virtual "
                    "machines, not physical machines."
                ),
                "evidence": ["000ACRDNT2"],
                "docs": ["WHAT_IS_SWAS"],
            },
            {
                "text": (
                    "Simple Application Server and ECS are two different "
                    "products: there is no in-place conversion or plan "
                    "swap between a SWAS instance and an ECS instance."
                ),
                "evidence": ["0001FS19PN"],
                "docs": ["WHAT_IS_SWAS"],
            },
            {
                "text": (
                    "When both products coexist in one account, keep them "
                    "apart when reasoning: ECS ids start with 'i-', SWAS "
                    "ids are 32-character hex strings; the ECS OpenAPI "
                    "surface cannot see SWAS resources."
                ),
                "evidence": ["000EARHWU7", "0005PRAZHW", "000B9RJ2PC"],
                "docs": ["CLIENT_MANAGE_SWAS"],
            },
            {
                "text": (
                    "If a genuinely physical server is wanted, the matching "
                    "product is ECS Elastic Bare Metal Server (priced "
                    "higher than ordinary cloud servers); quoting is a "
                    "commercial conversation, not a technical one."
                ),
                "evidence": ["000ACRDNT2"],
                "docs": ["EBM_OVERVIEW"],
            },
        ],
    },
    "spec-terminology": {
        "title": "Plan terminology: what '2-core 2G' means",
        "rules": [
            {
                "text": (
                    "'2-core 2G' means 2 vCPU and 2 GiB memory. The memory "
                    "figure in a plan name is the instance memory size."
                ),
                "evidence": ["000GJRX0P0"],
                "docs": ["SWAS_SPEC_FAMILIES"],
            },
            {
                "text": (
                    "SWAS memory configuration varies by spec family: "
                    "general-purpose and international families start from "
                    "0.5 GiB and top out at 16 GiB; agent-dedicated and "
                    "CPU-optimized families reach up to 64 GiB."
                ),
                "evidence": ["000GJRX0P0"],
                "docs": ["SWAS_SPEC_FAMILIES"],
            },
            {
                "text": (
                    "ECS economy/shared families (e.g. the economy-type e "
                    "instance behind the 99 CNY activity) are shared-CPU "
                    "families; compare families before judging performance."
                ),
                "evidence": ["0001FS19PN", "00085RZ8GE"],
                "docs": ["SHARED_INSTANCE_FAMILIES"],
            },
        ],
    },
    "migration": {
        "title": "Migration and region-change boundaries",
        "rules": [
            {
                "text": (
                    "SWAS does not support changing the region of an "
                    "existing instance. A region move means purchasing a "
                    "new instance in the target region and migrating data."
                ),
                "evidence": ["00094RH5HX"],
                "docs": ["MIGRATE_SERVERS"],
            },
            {
                "text": (
                    "Cross-region SWAS migration: (1) create a custom image "
                    "from the source SWAS instance, (2) copy that custom "
                    "image to the target region, (3) create a new server "
                    "from the copied image."
                ),
                "evidence": ["00094RH5HX"],
                "docs": ["MIGRATE_SERVERS"],
            },
            {
                "text": (
                    "SWAS-to-ECS migration runs through sharing the custom "
                    "image with ECS and creating an ECS instance from it; "
                    "when created from a SWAS image, the ECS default "
                    "instance family may be lower-spec than expected "
                    "(ecs.sn1.medium was observed in a ticket), which "
                    "explains price and configuration differences."
                ),
                "evidence": ["000DGRCMD9", "00085RZ8GE"],
                "evidence_quality": "summary",
                "docs": ["MIGRATE_SERVERS"],
            },
            {
                "text": (
                    "Hard prerequisite for image-based migration: the "
                    "target system disk must be greater than or equal to "
                    "the source system disk. A 40 GB target disk cannot "
                    "receive a 50 GB source disk, so an image move onto a "
                    "99 CNY activity plan fails this check."
                ),
                "evidence": ["0001FS19PN"],
                "docs": ["MIGRATE_SERVERS"],
            },
            {
                "text": (
                    "Image-based moves may carry a price difference and can "
                    "void renewal at a promotion price; when the customer "
                    "is cost-sensitive, manual migration is the fallback "
                    "path."
                ),
                "evidence": ["0001FS19PN"],
                "docs": [],
            },
            {
                "text": (
                    "Public websites hosted in mainland-China regions need "
                    "ICP filing before serving mainland visitors."
                ),
                "evidence": ["00094RH5HX"],
                "docs": [],
            },
        ],
    },
    "connection": {
        "title": "Remote-connection and OS boundaries",
        "rules": [
            {
                "text": (
                    "Linux instances are connected over SSH; Windows "
                    "instances over the Windows Remote Desktop protocol "
                    "(RDP). Using mstsc against a Linux SWAS instance "
                    "cannot work: the OS must be changed to Windows if a "
                    "desktop session is required."
                ),
                "evidence": ["0003YS837P", "000EARHWU7"],
                "docs": ["RESET_SWAS"],
            },
            {
                "text": (
                    "Changing the OS (SWAS 'reset system' / ECS 'replace "
                    "operating system') replaces the system disk: ALL data "
                    "on it is erased and cannot be recovered by the "
                    "platform; back up first. The public IP address stays "
                    "unchanged."
                ),
                "evidence": ["0003YS837P", "000EARHWU7"],
                "docs": ["RESET_SWAS", "REPLACE_ECS_OS"],
            },
            {
                "text": (
                    "After switching to Windows, the first boot may take "
                    "5-10 minutes before RDP accepts connections; wait "
                    "before concluding the change failed."
                ),
                "evidence": ["000EARHWU7"],
                "evidence_quality": "summary",
                "docs": [],
            },
            {
                "text": (
                    "RDP drive/file mapping requires enabling local drive "
                    "redirection in the client (mstsc: Local Resources -> "
                    "More -> Drives); the message 'the current connection "
                    "cannot use the file-transfer function' points at "
                    "client-side or local-network limits, not cloud-side "
                    "configuration."
                ),
                "evidence": ["0004PS4R06"],
                "evidence_quality": "summary",
                "docs": [],
            },
        ],
    },
    "network-access": {
        "title": "Cross-border reachability and bandwidth boundaries",
        "rules": [
            {
                "text": (
                    "Access between overseas regions and the Chinese "
                    "mainland crosses international links: delay and "
                    "packet loss are expected behaviour of the link, not "
                    "instance load. Collect evidence with the public "
                    "multi-node ping probe before drawing conclusions."
                ),
                "evidence": ["00094RH5HX", "0006SRSDLE"],
                "docs": ["PING_PROBE"],
            },
            {
                "text": (
                    "A provider-side reachability check passing does not "
                    "prove the customer's local network can reach the "
                    "instance, and vice versa; when both sides disagree, "
                    "the dispute is resolved through a support ticket with "
                    "probe evidence attached, not by online assertion."
                ),
                "evidence": ["0005PRAZHW"],
                "docs": ["PING_PROBE"],
            },
            {
                "text": (
                    "SWAS carries a shared peak-bandwidth plan: during "
                    "busy hours contention can throttle effective "
                    "bandwidth (1 Mbps was observed in a ticket), which "
                    "can make management-panel pages fail to load; SWAS "
                    "is not positioned for workloads that need strong "
                    "public-network quality guarantees."
                ),
                "evidence": ["000AWRHMSJ"],
                "evidence_quality": "summary",
                "docs": [],
            },
        ],
    },
    "commerce": {
        "title": "Promotion and refund rule boundaries",
        "rules": [
            {
                "text": (
                    "New-customer promotion tiers (e.g. the 68 CNY/year "
                    "SWAS tier) are limited to accounts that have never "
                    "generated an order record; after a refund, the order "
                    "record remains and re-purchase at the promotion price "
                    "is no longer possible."
                ),
                "evidence": ["000BSRL35W"],
                "docs": [],
            },
            {
                "text": (
                    "The 99 CNY/year ECS activity requires real-name "
                    "verification, is limited to one instance per person, "
                    "and is not renewable at the activity price after an "
                    "image-based replacement; check the activity page for "
                    "the authoritative current terms."
                ),
                "evidence": ["0001FS19PN"],
                "docs": ["ACT99"],
            },
            {
                "text": (
                    "The 5-day unconditional refund benefit is limited to "
                    "one use per year per product per account; using it "
                    "on SWAS excludes reusing it on ECS in the same year."
                ),
                "evidence": ["0001ZSAG86"],
                "evidence_quality": "summary",
                "docs": [],
            },
            {
                "text": (
                    "Restoring promotion eligibility, price negotiation, "
                    "refunds and releases are commercial processes: they "
                    "are never executed by tooling, only escalated to "
                    "human sales/support channels."
                ),
                "evidence": ["000BSRL35W", "000B9RJ2PC"],
                "docs": [],
            },
        ],
    },
    "lifecycle": {
        "title": "Expiration and release self-service",
        "rules": [
            {
                "text": (
                    "Expiration dates and renewal orders are visible in "
                    "the console (instance list / order center) without "
                    "calling support; guide self-service first."
                ),
                "evidence": ["00073S1MFZ"],
                "evidence_quality": "summary",
                "docs": ["CLIENT_MANAGE_SWAS"],
            },
            {
                "text": (
                    "A free-trial instance expiring soon can simply be "
                    "left unrenewed; proactive manual release is not "
                    "required."
                ),
                "evidence": ["000B9RJ2PC"],
                "evidence_quality": "summary",
                "docs": [],
            },
            {
                "text": (
                    "Billing-side states (renewal orders, unsubscribe "
                    "status) are outside the verified read-only surface "
                    "of this skill; they degrade to console guidance."
                ),
                "evidence": [],
                "docs": [],
            },
        ],
    },
}

# ---------------------------------------------------------------------------
# OS-to-connection matrix (capability 4)
# ---------------------------------------------------------------------------

CONNECTION_MATRIX = {
    "linux": {
        "method": "SSH (port 22) or the console terminal",
        "notes": (
            "Windows Remote Desktop (mstsc) does not apply to a Linux "
            "instance; switch the OS first if a desktop is required."
        ),
    },
    "windows": {
        "method": "Remote Desktop / RDP (port 3389) or the console VNC",
        "notes": (
            "First boot after an OS change can take 5-10 minutes; file "
            "transfer needs local drive redirection enabled in the client."
        ),
    },
}

# ---------------------------------------------------------------------------
# Out-of-scope handoff routes (capability 7). Each entry maps a symptom
# category to the neighbouring skill or human channel, with the context the
# handoff report must attach.
# ---------------------------------------------------------------------------

HANDOFF_ROUTES = {
    "disk-expand": {
        "keywords": ["expand", "extend disk", "partition", "resize not applied", "disk still small"],
        "target": "alibabacloud-ecs-disk-expand-diagnosis",
        "note": "Disk resized but the partition / filesystem did not grow.",
    },
    "instance-state": {
        "keywords": ["cannot start", "stuck starting", "stuck stopping", "will not boot", "restarting forever"],
        "target": "alibabacloud-ecs-instance-state-diagnosis",
        "note": "Instance stuck in a start/stop transition or will not boot.",
    },
    "disk-io": {
        "keywords": ["disk io", "io 100", "io saturated", "slow disk", "service hangs daily"],
        "target": "alibabacloud-ecs-disk-io-diagnosis",
        "note": "Disk IO at the ceiling or performance below spec.",
    },
    "resource-usage": {
        "keywords": ["memory usage", "high memory", "disk full", "inode", "cpu full"],
        "target": "alibabacloud-ecs-diagnose",
        "note": "In-guest resource-usage diagnosis is out of scope here; this skill only explains the plan specification.",
    },
    "security": {
        "keywords": ["mining", "virus", "trojan", "intrusion", "abnormal process"],
        "target": "Cloud Security Center / security handling channel",
        "note": (
            "Suspected intrusion: hand off with the detection conclusion and "
            "its source attached; typical manual advice is installing "
            "antivirus and tightening the firewall/security group, never "
            "executed by this skill."
        ),
        "evidence": ["000G2RTD1G"],
    },
    "commercial": {
        "keywords": ["refund", "restore discount", "negotiate price", "release for me", "unsubscribe"],
        "target": "human sales / support ticket channel",
        "note": "Commercial actions are never executed by tooling; escalate with the collected evidence.",
    },
    "reachability-dispute": {
        "keywords": ["ip blocked", "unreachable only in my country", "cross-border dispute"],
        "target": "support ticket (offline engineering escalation)",
        "note": (
            "Online checks can only show the provider side is normal; the "
            "dispute itself is resolved offline with probe evidence attached."
        ),
        "evidence": ["0005PRAZHW"],
    },
}

# Default NEXT_ACTION strings keyed by terminal status.
NEXT_ACTION_BY_STATUS = {
    "OK": "Present the boundary report with its evidence and doc links; keep every recommendation manual-guidance only.",
    "DEGRADED": "Present the report, state each degraded check honestly, and follow the per-line fallback guidance.",
    "FAIL": "Fix the blocking prerequisite (missing input or credentials via 'aliyun configure'); never substitute hand-written calls.",
}

# ---------------------------------------------------------------------------
# Migration decision constants (used by --migration-check; readable version
# in references/migration-paths.md). Wording distilled from real tickets.
# ---------------------------------------------------------------------------

MIGRATION_FACTS = {
    "target_disk_rule": (
        "Image migration requires the TARGET system disk to be greater than "
        "or equal to the SOURCE system disk."
    ),
    "price_difference": (
        "A larger target disk/plan must be paid for; the price difference "
        "is not waived."
    ),
    "promo_renewal": (
        "A migrated or newly purchased instance cannot inherit the source's "
        "promotional renewal price (for example the 99 CNY/year renewal); "
        "state this BEFORE the customer refunds or repurchases."
    ),
    "cross_region_steps": [
        "Create a custom image of the source Simple Application Server.",
        "Copy the custom image to the target region.",
        "In the target region, use the copied image to create a new server "
        "(image row action: create server).",
    ],
    "swas_to_ecs_steps": [
        "Create a custom image of the source Simple Application Server.",
        "Share/export the custom image so ECS can use it (console image "
        "wizard; follow the on-screen steps).",
        "Create the ECS instance from the image and choose the instance "
        "family consciously: the default family may differ from the family "
        "you compare prices with, which explains price/spec surprises.",
        "Verify the target system disk is >= the source system disk before "
        "starting.",
    ],
    "manual_fallback": (
        "When image preconditions fail or the price difference is a "
        "concern, migrate manually: back up data (database dump, files, "
        "configs), provision the target server, restore data, repoint DNS. "
        "Manual effort depends on the data volume, which no cloud API can "
        "assess for you."
    ),
    "icp_note": (
        "Websites served from mainland-China regions require ICP filing "
        "(beian) before public access."
    ),
}
