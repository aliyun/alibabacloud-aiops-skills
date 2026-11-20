#!/usr/bin/env python3
"""
_constants.py -- Embedded static data for the ECS Compliance & Security-
Qualification Evidence Guide
===========================================================================
SECURITY: This skill is strictly READ-ONLY. Nothing in this module performs
any call; authentication is resolved exclusively by the aliyun CLI default
credential chain, and this module never touches any credential value.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (API whitelist, official document list, control
mapping, material buckets, self-audit checklist, handoff rules) is embedded
here as Python constants. There are no data files in this skill directory.

Provenance discipline (anti-hallucination, KB-04):
  * The document URLs below are ONLY the official help-center pages that
    were verified as search hits for this tier during development. No other
    URL may ever be added from memory.
  * The S2 official download channels were NOT verified for this tier; the
    pending note below is a mandatory part of every material-scope answer.
"""

# ---------------------------------------------------------------------------
# Skill identity & observability
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-compliance-cert-guide"

# ---------------------------------------------------------------------------
# ECS OpenAPI metadata (verified surface for this tier)
# ---------------------------------------------------------------------------

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"

# API WHITELIST: the ONLY actions this skill may ever call. Enforced by
# _cli.call() before any subprocess is spawned.
WHITELISTED_ACTIONS = frozenset({
    "DescribeInstances",       # instance inventory + bound security groups
    "DescribeInstanceStatus",  # running-state cross-check
})
# DescribeAvailableResource is deliberately NOT whitelisted (weak relevance
# to the compliance-evidence axis; its RAM permission point was never
# verified for this tier).

# ---------------------------------------------------------------------------
# CLI / retry / pagination limits
# ---------------------------------------------------------------------------

# Per-subprocess-call timeout in seconds (platform rule 7.6.1: every call
# must carry an explicit timeout).
DEFAULT_TIMEOUT = 60
CLI_MAX_ATTEMPTS = 3            # 1 try + 2 retries for transient errors
BACKOFF_BASE_SECONDS = 2        # retry N waits N * 2s
MAX_PAGES = 50                  # hard pagination guardrail per list query
INSTANCE_PAGE_SIZE = 100        # MaxResults for DescribeInstances
STATUS_PAGE_SIZE = 50           # PageSize for DescribeInstanceStatus (max 50)

# Error-code substrings that mean "the credential lacks the read grant".
# The canonical literals for this product family are NoPermission and
# ImplicitDeny; the other markers are matched case-insensitively on the
# extracted code only.
PERMISSION_MARKERS = ("nopermission", "implicitdeny", "accessdenied",
                      "unauthorized", "not authorized")
# Substrings treated as transient (retry) vs permanent.
TRANSIENT_MARKERS = ("throttling", "serviceunavailable", "internalerror",
                     "internal error", "timed out", "timeout",
                     "connection reset", "temporarily unavailable",
                     "http 500", "http 502", "http 503", "http 504",
                     "statuscode: 5")

# ---------------------------------------------------------------------------
# Citable official documents (verified search hits for this tier ONLY)
# ---------------------------------------------------------------------------

DOC_URLS = {
    "bastionhost-equal-protection": {
        "title": ("Bastionhost operations and maintenance meeting the "
                  "equal-protection (Dengbao) 2.0 requirements"),
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/use-the-bastion"
                "-machine-for-operation-and-maintenance-to-meet-the-"
                "requirements-of-equal-protection-2-0.md"),
        "use": ("S1: operations-audit control area - session recording and "
                "centralized O&M evidence"),
    },
    "monitoring-and-logging": {
        "title": "ECS monitoring and logging overview",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "monitoring-and-logging.md"),
        "use": ("S1: audit / log-retention control areas - what ECS "
                "monitoring and logging provides"),
    },
    "security-overview": {
        "title": "ECS security overview",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "security-overview.md"),
        "use": ("S1: shared-responsibility baseline - where platform duties "
                "end and customer duties begin"),
    },
    "alibaba-cloud-linux": {
        "title": "Alibaba Cloud Linux image overview",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "alibaba-cloud-linux.md"),
        "use": "S1: host-layer (secure computing environment) OS baseline",
    },
    "what-is-ecs": {
        "title": "Elastic Compute Service overview",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md"),
        "use": ("S1/S3: product positioning and responsibility-boundary "
                "explanation start"),
    },
    "product-functions": {
        "title": "ECS feature and function overview",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "product-function-custom-node-ecs-normal.md"),
        "use": "S3: feature areas a self-audit can reference",
    },
    "console-windows-iis": {
        "title": "Quickly purchase a Windows instance and build IIS",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/quickly-purchase-"
                "a-windows-instance-and-build-an-iis-service.md"),
        "use": ("console operation baseline only - weak relevance; never "
                "present as compliance evidence"),
    },
    "console-linux-apache": {
        "title": "Purchase a Linux instance in the console and build Apache",
        "url": ("https://help.aliyun.com/zh/ecs/user-guide/"
                "use-the-ecs-instance-in-the-console.md"),
        "use": ("console operation baseline only - weak relevance; never "
                "present as compliance evidence"),
    },
}

# S2 channels: NOT verified for this tier. This note must be delivered
# verbatim whenever material channels are discussed (DEGRADED protocol).
CHANNEL_PENDING_NOTE = (
    "NOTE: official self-service download-channel links for platform "
    "qualification materials of THIS tier are pending human verification "
    "and are intentionally not cited by this skill. Until they are "
    "verified: use the Alibaba Cloud official website / help portal "
    "search (terms: Dengbao, classified protection, compliance "
    "certificate, qualifications) at https://help.aliyun.com, and open a "
    "support ticket for stamped, paper, or bespoke documents."
)

# ---------------------------------------------------------------------------
# S1: control-area mapping (starting set; expand only with verified docs)
# ---------------------------------------------------------------------------

MLPS_CONTROL_MAP = [
    {
        "area": "Operations and maintenance audit",
        "customer_wording": ("who logs into the servers; can sessions be "
                             "replayed; centralized O&M"),
        "capability": "Bastionhost session recording and O&M audit trail",
        "docs": ["bastionhost-equal-protection"],
        "boundary": "customer procures/configures the product (manual)",
    },
    {
        "area": "Security auditing and log retention",
        "customer_wording": ("are logs collected, kept, and tamper-evident "
                             "for the assessed period"),
        "capability": "ECS monitoring and logging capabilities",
        "docs": ["monitoring-and-logging"],
        "boundary": ("retention length and delivery are customer policy "
                     "(manual)"),
    },
    {
        "area": "Shared responsibility baseline",
        "customer_wording": ("what does the platform already cover vs my "
                             "side"),
        "capability": "ECS security shared-responsibility framing",
        "docs": ["security-overview", "what-is-ecs"],
        "boundary": "platform duties are inherited; customer duties are not",
    },
    {
        "area": "Secure computing environment (host layer)",
        "customer_wording": ("OS baseline, patches, malicious code "
                             "prevention on hosts"),
        "capability": "Alibaba Cloud Linux hardened-image capabilities",
        "docs": ["alibaba-cloud-linux", "product-functions"],
        "boundary": ("in-guest hardening checks are manual; this skill "
                     "never runs guest commands"),
    },
    {
        "area": "Network access control (secure area boundary)",
        "customer_wording": ("security groups, exposure of management "
                             "ports"),
        "capability": ("security groups bound per instance (inventory "
                       "lists the IDs)"),
        "docs": ["product-functions"],
        "boundary": ("rule review is manual in the console; the "
                     "rule-listing API is outside this skill's whitelist"),
    },
]

RESPONSIBILITY_SPLIT_TEXT = (
    "Platform qualifications do NOT make a customer system compliant: the "
    "MLPS 2.0 (Dengbao) assessment targets the customer's own information "
    "system and is performed by an accredited assessment body. The platform "
    "provides inheritable controls and capability evidence; the customer "
    "owns instance configuration, security-group design, OS hardening, "
    "account design, log retention, backup policy, and the assessment "
    "process itself."
)

CRYPTO_ASSESSMENT_TEXT = (
    "A cryptographic-application security assessment is a SEPARATE "
    "evaluation from MLPS 2.0 with its own criteria and assessment process. "
    "No official document for it was verified for this skill: clarify which "
    "evaluation the customer means, state that platform-side cryptographic "
    "capability mapping is pending human verification, and route item-level "
    "questions to a support ticket."
)

# ---------------------------------------------------------------------------
# S2: material buckets
# ---------------------------------------------------------------------------

MATERIAL_BUCKETS = [
    {
        "bucket": "A. Platform-side qualification evidence",
        "examples": ("Alibaba Cloud compliance/qualification materials for "
                     "the platform itself"),
        "owner": "the cloud platform publishes them",
        "how": ("self-service on the official website / help portal; "
                "tier-specific channel links: PENDING verification"),
    },
    {
        "bucket": "B. Customer-system assessment report",
        "examples": ("the level-3 assessment report and filing records of "
                     "the customer's own system"),
        "owner": ("an accredited assessment body; filing handled by the "
                  "customer with the local cybersecurity authority"),
        "how": ("contract an assessment body; use this skill's S3 "
                "inventory as factual input"),
    },
    {
        "bucket": "C. Legal-grade / bespoke documents",
        "examples": ("stamped originals, paper certificates, NDAs, custom "
                     "attestation letters"),
        "owner": "commercial / legal channel",
        "how": "open a support ticket; human handling only",
    },
]

# ---------------------------------------------------------------------------
# S3: manual checklist (mirror of references/self-audit-checklist.md)
# ---------------------------------------------------------------------------

SELF_AUDIT_AREAS = [
    {
        "area": "Identity and access management",
        "auto_basis": "instance list and count per region from the table",
        "items": [
            ("IAM-01", "RAM users (not root) operate the listed instances; "
                       "no shared logins", "RAM console -> Users"),
            ("IAM-02", "MFA enabled for administrative console identities",
                       "RAM console -> Users -> Authentication"),
            ("IAM-03", "Key pairs preferred over passwords; unused keys "
                       "handled by customer policy",
                       "ECS console -> Key Pairs; guest SSH config (manual)"),
            ("IAM-04", "Least-privilege grants for operating identities",
                       "RAM console -> Permissions"),
        ],
    },
    {
        "area": "Network exposure and boundary protection",
        "auto_basis": ("security-group IDs, network type, public-IP/EIP "
                       "flags per instance from the table"),
        "items": [
            ("NET-01", "Review every security group listed: management "
                       "ports not open to broad sources",
                       "ECS console -> Security Groups -> rules"),
            ("NET-02", "Each 'public exposure: yes' row is justified for "
                       "the assessed design",
                       "ECS console -> Instances -> network details"),
            ("NET-03", "Legacy network-type rows migrated per plan",
                       "inventory Network column; migration manual"),
        ],
    },
    {
        "area": "Operations audit",
        "auto_basis": "instance inventory scope the assessor will sample",
        "items": [
            ("OMA-01", "Server operations go through a bastion host with "
                       "session records kept for the window",
                       "Bastionhost console (manual setup)"),
            ("OMA-02", "Account-level administrative actions recorded and "
                       "queryable", "ActionTrail / operation logs (manual)"),
        ],
    },
    {
        "area": "Logging and monitoring",
        "auto_basis": "Running vs stopped states in the table",
        "items": [
            ("LOG-01", "Monitoring agent and metric collection active on "
                       "assessed instances", "CloudMonitor console"),
            ("LOG-02", "Log retention window meets the assessor's "
                       "requirement", "customer log pipeline (manual)"),
        ],
    },
    {
        "area": "Data backup and recovery",
        "auto_basis": "which instances/disks belong to the assessed system",
        "items": [
            ("BKU-01", "A backup plan exists and backups exist in the "
                       "assessment window",
                       "ECS console -> Snapshots (manual review)"),
            ("BKU-02", "Restore procedure tested and recorded",
                       "customer runbook"),
        ],
    },
    {
        "area": "Host / OS",
        "auto_basis": "OS type and image field in the table",
        "items": [
            ("HOS-01", "Images are official or self-audited; hardened "
                       "baseline used where applicable",
                       "ECS console -> Images"),
            ("HOS-02", "Password policy, audit switches, patch level per "
                       "guest", "in-guest check by customer admins - NOT "
                       "performed by this skill"),
        ],
    },
    {
        "area": "Availability",
        "auto_basis": "status column of the table",
        "items": [
            ("AVA-01", "Non-Running rows explained; redundancy expected by "
                       "the target protection level",
                       "inventory Status column + architecture notes"),
        ],
    },
]

# ---------------------------------------------------------------------------
# Handoff rules (mirror of references/handoff-matrix.md)
# ---------------------------------------------------------------------------

HANDOFF_RULES = [
    {
        "keywords": ["disk full", "inode", "file count limit",
                     "cannot create new file", "free space", "clean up"],
        "target": ("disk space and inode governance capability "
                   "(alibabacloud-ecs-diagnose family line)"),
        "sentence": ("Disk usage and cleanup is handled by our "
                     "disk-capacity diagnostics capability, not this "
                     "compliance guide; nothing in this audit needs to "
                     "change first."),
    },
    {
        "keywords": ["expansion not applied", "partition not grown",
                     "disk size did not change"],
        "target": "alibabacloud-ecs-disk-expand-diagnosis",
        "sentence": ("That looks like an expansion-not-applied issue, which "
                     "has its own diagnosis skill "
                     "(alibabacloud-ecs-disk-expand-diagnosis)."),
    },
    {
        "keywords": ["will not start", "stuck starting", "stuck stopping",
                     "restart loop"],
        "target": "alibabacloud-ecs-instance-state-diagnosis",
        "sentence": ("Instance start/stop anomalies belong to the "
                     "instance-state diagnosis skill "
                     "(alibabacloud-ecs-instance-state-diagnosis); we can "
                     "resume the compliance inventory afterwards."),
    },
    {
        "keywords": ["disk io slow", "io latency", "performance below spec"],
        "target": "alibabacloud-ecs-disk-io-diagnosis",
        "sentence": ("Slow disk IO needs the disk-IO diagnosis skill "
                     "(alibabacloud-ecs-disk-io-diagnosis)."),
    },
    {
        "keywords": ["apply the fix", "change my security group",
                     "turn on for me", "delete these", "clean up for me"],
        "target": "manual console steps / human support",
        "sentence": ("I can only guide you through the change - this skill "
                     "never applies changes. Console steps and risk notes "
                     "are given instead."),
    },
    {
        "keywords": ["stamped", "paper original", "nda", "attestation",
                     "sealed copy"],
        "target": "commercial / legal channel (support ticket)",
        "sentence": ("Stamped, paper, or bespoke documents go through the "
                     "commercial channel: open a support ticket describing "
                     "the exact document your auditor requires."),
    },
    {
        "keywords": ["inside the instance", "guest os check",
                     "password policy check", "audit switch"],
        "target": "customer system administrators (in-guest, manual)",
        "sentence": ("In-guest configuration checks are performed by your "
                     "administrators inside the instance; this read-only "
                     "guide lists them as manual items only."),
    },
]

# ---------------------------------------------------------------------------
# Report text constants
# ---------------------------------------------------------------------------

ACCOUNT_SCOPE_NOTE = (
    "Results reflect only the account behind the current default-chain "
    "credential."
)

TABLE_HEADER = ("| InstanceId | Name | Status | Zone | Type | OS | Network |"
                " VPC | SecurityGroups | PublicIP | EIP |")
TABLE_DIVIDER = "|---|---|---|---|---|---|---|---|---|---|---|"
