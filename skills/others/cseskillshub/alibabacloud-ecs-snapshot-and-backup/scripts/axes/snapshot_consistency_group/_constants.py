#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and domain knowledge for the
alibabacloud-ecs-snapshot-consistency-group skill.
=================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads, writes or caches
any credential; authentication is resolved exclusively by the aliyun CLI
default credential chain. This module NEVER handles AccessKey material.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
ALL static reference data (API metadata, disk-category table, rule answers
distilled from real support tickets and official docs, handoff map) is
embedded here as Python constants. There are NO data files in this skill.

Knowledge provenance: every rule answer below was distilled from the tier's
confirmed requirements document (support-ticket evidence cross-checked
against official Alibaba Cloud help documentation on KNOWLEDGE_VERIFIED_DATE).
Branches whose evidence is thin carry an explicit LOW CONFIDENCE label; they
must be relayed with that label and never upgraded to official fact.
"""

# ---------------------------------------------------------------------------
# Skill / product metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-snapshot-consistency-group"

# Product codes and API versions actually invoked by this skill.
# ecs is an RPC-style product (PascalCase actions, e.g. DescribeInstances);
# sts runs in plugin mode (lowercase-hyphenated, e.g. get-caller-identity).
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# Central (region-less) STS endpoint. ECS regional endpoints are resolved by
# the aliyun CLI from the --region flag; no fixed ECS endpoint is hardcoded.
STS_ENDPOINT = "sts.aliyuncs.com"

# Region used only for the central identity call (STS is region-less).
STS_REGION_FOR_IDENTITY = "cn-hangzhou"

# API whitelist actually invoked by the entry script (informational; the
# entry script never calls anything outside this tuple).
ALLOWED_ECS_ACTIONS = ("DescribeInstances", "DescribeDisks", "DescribeSnapshots")

# ---------------------------------------------------------------------------
# Timeouts / pagination limits (MUST 7.6.1: every CLI call carries a timeout)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60      # seconds, per CLI invocation
MIN_TIMEOUT = 5
MAX_TIMEOUT = 300

PAGE_SIZE = 100           # records per page for PageNumber-style ECS queries
MAX_PAGES = 20            # hard guardrail on pages fetched per query loop

# Cap on per-record detail lines in the human-readable report.
SNAPSHOT_DETAIL_LIMIT = 40

# ---------------------------------------------------------------------------
# Knowledge currency
# ---------------------------------------------------------------------------

# All official wording embedded below was cross-checked on this date; every
# report must echo it, because product support scope can change over time.
KNOWLEDGE_VERIFIED_DATE = "2026-07-31"

# Official help-document sources cited by the embedded rules (verbatim URLs
# from the tier requirements document; do not invent other URLs).
DOC_SOURCES = {
    "group-overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "snapshot-consistency-group-overview.md"
    ),
    "create-group": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "create-a-snapshot-consistent-group.md"
    ),
    "rollback-group": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "roll-back-disks-by-using-a-snapshot-consistent-group.md"
    ),
    "auto-policy-instance": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "apply-an-automatic-snapshot-policy-to-the-instance.md"
    ),
    "what-is-ecs": (
        "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md"
    ),
    "data-protection-compare": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "select-the-appropriate-ecs-data-protection-scheme-snapshot-and-"
        "file-backup-essential-edition.md"
    ),
    "preemptible-recovery": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "preemptible-instance-data-retention-and-data-recovery-after-"
        "interrupt-reclamation.md"
    ),
    "restart-instances": (
        "https://help.aliyun.com/zh/ecs/user-guide/restart-instances.md"
    ),
}

# ---------------------------------------------------------------------------
# Disk-category table (DescribeDisks Category values)
# ---------------------------------------------------------------------------
# category raw value -> (human label, ESSD family?)
# The official consistency-group wording targets multiple ESSD cloud disks
# (support-ticket agent wording cross-checked on KNOWLEDGE_VERIFIED_DATE).
# ESSD-family membership of entry-level / AutoPL categories must still be
# confirmed against the current official documentation before a hard
# support verdict is given to a customer.
DISK_CATEGORY_NOTES = {
    "cloud_essd": ("ESSD", True),
    "cloud_auto": ("ESSD AutoPL (ESSD family)", True),
    "cloud_essd_entry": ("ESSD Entry (ESSD family, entry level)", True),
    "cloud_ssd": ("standard SSD", False),
    "cloud_efficiency": ("ultra disk", False),
    "cloud": ("basic disk", False),
}

# ---------------------------------------------------------------------------
# Environment element of the support-scope verdict (C1)
# ---------------------------------------------------------------------------
# The whitelisted read-only APIs do NOT expose the environment type, so this
# element always depends on the customer's own statement. The government /
# dedicated cloud branches carry LOW CONFIDENCE labels on purpose: the only
# evidence is a single ticket summary with no official documentation hit as
# of KNOWLEDGE_VERIFIED_DATE.
ENVIRONMENT_NOTES = {
    "public": (
        "public cloud environment (customer self-declared): feature "
        "availability follows the official documentation"
    ),
    "gov": (
        "government cloud environment (customer self-declared): ticket "
        "evidence indicates the snapshot consistency group entry may not "
        "exist in government cloud environments - LOW CONFIDENCE (single "
        "ticket summary, no official documentation hit as of "
        + KNOWLEDGE_VERIFIED_DATE
        + "); relay it as ticket experience only and ask the customer to "
        "confirm via the console or a support ticket"
    ),
    "dedicated": (
        "dedicated / private cloud environment (customer self-declared): "
        "feature availability cannot be determined through the whitelisted "
        "APIs or the public documentation; ask the customer to confirm "
        "with the environment operator"
    ),
    "unknown": (
        "environment type is NOT determinable through the whitelisted "
        "read-only APIs; ask the customer whether they use the public "
        "cloud, a government cloud or a dedicated cloud environment"
    ),
}

# ---------------------------------------------------------------------------
# Rule topics (C2 / C4 / C5 knowledge answers, distilled from tickets + docs)
# ---------------------------------------------------------------------------
RULES_TOPICS = {
    "auto-policy-vs-group": {
        "question": (
            "Can an automatic snapshot policy keep multiple disks "
            "consistent, or create snapshot consistency groups "
            "automatically? Is there a script that creates or deletes "
            "groups automatically?"
        ),
        "answer": (
            "Automatic snapshot policies can only be associated with "
            "individual disks or with instance tags; they cannot be bound "
            "to snapshot consistency groups and they never create groups. "
            "When several disks share the same automatic policy, the "
            "policy still snapshots each disk independently, so those "
            "snapshots are NOT point-in-time consistent across disks. "
            "Snapshot consistency groups can only be created manually, and "
            "there is no automation script for creating or deleting "
            "groups. When multi-disk data consistency is required, create "
            "a snapshot consistency group manually: this skill provides "
            "the pre-creation checklist and the official doc pointer, the "
            "customer executes the creation in the console, and this skill "
            "re-verifies completion afterwards (read-only)."
        ),
        "sources": [
            DOC_SOURCES["auto-policy-instance"],
            DOC_SOURCES["create-group"],
        ],
        "confidence": (
            "high (support-ticket agent wording cross-checked against the "
            "official docs on " + KNOWLEDGE_VERIFIED_DATE + ")"
        ),
        "keywords": [
            "automatic snapshot policy", "auto policy", "automatic policy",
            "consistent", "consistency", "script", "automatically",
            "automation", "bind", "policy", "schedule",
        ],
    },
    "group-basics": {
        "question": (
            "What is a snapshot consistency group and what kind of "
            "consistency does it provide?"
        ),
        "answer": (
            "A snapshot consistency group creates snapshots of multiple "
            "cloud disks of one instance at the same point in time, so the "
            "multi-disk data is crash-consistent at that moment. The "
            "consistency point in time is fixed when creation is "
            "initiated; later writes to the disks do not change the "
            "snapshot. The official wording targets multiple ESSD cloud "
            "disks of one instance. By default the group provides "
            "crash / filesystem-level consistency; application-consistent "
            "snapshots require extra preparation inside the guest operating "
            "system (for Linux: upload the official application-consistency "
            "script in advance and install the Cloud Assistant plugin, "
            "otherwise a filesystem-consistency snapshot is created by "
            "default). An equivalent Windows procedure was NOT evidenced in "
            "the material available to this skill, so any answer about "
            "Windows application-consistency preparation is LOW CONFIDENCE "
            "and must be flagged as such."
        ),
        "sources": [
            DOC_SOURCES["group-overview"],
            DOC_SOURCES["create-group"],
        ],
        "confidence": (
            "high for the group semantics; LOW CONFIDENCE for the Windows "
            "application-consistency branch (no evidence as of "
            + KNOWLEDGE_VERIFIED_DATE + ")"
        ),
        "keywords": [
            "what is", "crash-consistent", "crash consistent",
            "application consistent", "application-consistency",
            "file system", "filesystem", "point in time", "time point",
            "essd", "windows", "linux", "basics", "difference",
        ],
    },
    "support-scope": {
        "question": (
            "Why can I not find the snapshot consistency group entry in "
            "the console? Is the feature supported in my environment?"
        ),
        "answer": (
            "Judge support with three elements. (1) Environment type: "
            "public cloud vs government / dedicated cloud - the whitelisted "
            "read-only APIs cannot determine the environment type, so ask "
            "the customer; ticket evidence indicates one government cloud "
            "environment had no consistency-group entry (LOW CONFIDENCE: "
            "single ticket summary, no official documentation hit as of "
            + KNOWLEDGE_VERIFIED_DATE
            + " - relay it as ticket experience, never as official fact). "
            "(2) Region: snapshots and disks are region-isolated, so first "
            "confirm the customer is looking at the correct region in the "
            "console. (3) Disk category: the official wording targets "
            "multiple ESSD cloud disks - run the precheck mode to list "
            "every disk category and size as facts. If all three elements "
            "indicate support but the customer still sees no entry, hand "
            "off to console resource-lookup guidance (see "
            "references/handoff-map.md)."
        ),
        "sources": [
            DOC_SOURCES["group-overview"],
            DOC_SOURCES["create-group"],
            DOC_SOURCES["what-is-ecs"],
        ],
        "confidence": (
            "medium - the government / dedicated environment branch is LOW "
            "CONFIDENCE (no official documentation hit as of "
            + KNOWLEDGE_VERIFIED_DATE + ")"
        ),
        "keywords": [
            "support", "supported", "entry", "cannot find", "can not find",
            "not visible", "missing", "where is", "console", "government",
            "gov", "environment", "region",
        ],
    },
    "completion-criteria": {
        "question": (
            "My snapshot or consistency group shows 'creating' / "
            "'uploading to OSS' - is it complete? How long does creation "
            "take? Is the consistency time point fixed?"
        ),
        "answer": (
            "A snapshot is really complete only when its upload progress "
            "reaches 100 percent (Status becomes 'accomplished'); "
            "'creating' or 'uploading to OSS' states are NOT complete. The "
            "consistency time point is fixed when creation is initiated - "
            "later disk writes do not affect the snapshot. The first "
            "snapshot of a disk is a FULL snapshot and takes much longer "
            "(one real ticket measured roughly 30 minutes for 6 disks on "
            "the first run); subsequent snapshots are INCREMENTAL and "
            "significantly faster. Actual duration depends on data volume "
            "and change rate - this skill never promises a duration; it "
            "re-checks the real Status / Progress facts in verify mode."
        ),
        "sources": [
            DOC_SOURCES["create-group"],
            DOC_SOURCES["group-overview"],
        ],
        "confidence": (
            "high (support-ticket agent wording cross-checked against the "
            "official docs on " + KNOWLEDGE_VERIFIED_DATE + ")"
        ),
        "keywords": [
            "creating", "uploading", "upload", "oss", "progress",
            "complete", "completed", "finish", "how long", "100",
            "full", "incremental", "time point", "slow", "30 minutes",
        ],
    },
    "rollback-prerequisites": {
        "question": (
            "What are the prerequisites for rolling back disks with a "
            "snapshot consistency group? Does the instance need to be "
            "stopped? What if mounting fails after the rollback?"
        ),
        "answer": (
            "Rolling back disks with a consistency group requires the "
            "instance to be STOPPED first, and the customer should take a "
            "fresh snapshot backup before stopping, so the current state "
            "stays recoverable. The rollback itself is executed by the "
            "customer in the console - this skill is strictly read-only: "
            "it states the prerequisites, re-verifies facts afterwards "
            "(instance status, presence of the fresh backup, snapshot "
            "records) and never performs or promises a rollback. If a data "
            "disk fails to mount inside the guest after the rollback, that "
            "is an in-guest configuration matter: have the customer "
            "self-check the fstab entries and the mount order (one real "
            "ticket closed when the customer found their own auto-mount "
            "entry was wrong); this skill does not enter instances - hand "
            "off to disk attach / mount diagnosis."
        ),
        "sources": [
            DOC_SOURCES["rollback-group"],
            DOC_SOURCES["restart-instances"],
        ],
        "confidence": (
            "high for the stop-and-backup prerequisites (ticket wording + "
            "official rollback doc); the in-guest mount branch is "
            "self-check guidance only, never executed by this skill"
        ),
        "keywords": [
            "rollback", "roll back", "restore", "stop", "stopped",
            "shutdown", "shut down", "power off", "mount", "fstab",
            "prerequisite", "backup", "recover",
        ],
    },
    "storage-location": {
        "question": (
            "Where are snapshots stored? Are they in my own OSS bucket or "
            "in my local data center? Why do I only see locally redundant "
            "storage packages?"
        ),
        "answer": (
            "After creation, snapshots are stored in service-managed OSS "
            "buckets that are NOT visible to the user, in the same region "
            "as the source disks; they do not consume disk capacity and "
            "are listed in the ECS console under Storage & Snapshots > "
            "Snapshots. Snapshots are region-isolated: switch the console "
            "region to see that region's snapshots. Storing snapshots in a "
            "customer-created OSS bucket is not supported. In regions "
            "where OSS supports zone-redundant storage, snapshot data is "
            "stored in zone-redundant buckets by default. Questions about "
            "snapshot fees, storage packages, package redundancy coverage "
            "or discounts are BILLING topics outside this read-only skill: "
            "hand off to the billing / support channel (in one real ticket "
            "the agent transferred exactly these questions to the "
            "commercial team)."
        ),
        "sources": [
            DOC_SOURCES["group-overview"],
            DOC_SOURCES["data-protection-compare"],
        ],
        "confidence": (
            "high for the storage-architecture wording (ticket + docs "
            "cross-checked on " + KNOWLEDGE_VERIFIED_DATE + "); billing "
            "and package-coverage questions are handed off, never "
            "answered here"
        ),
        "keywords": [
            "storage", "stored", "where", "oss", "bucket", "region",
            "redundant", "redundancy", "package", "billing", "fee",
            "local", "data center", "capacity",
        ],
    },
    "handoff": {
        "question": (
            "Which neighbouring topics does this skill hand off, and with "
            "what wording?"
        ),
        "answer": (
            "This skill only covers the snapshot-consistency-group / "
            "multi-disk-consistency symptom axis (read-only facts + rule "
            "answers). Everything below is recognized and handed off, "
            "never diagnosed here - see the per-area scripts below and "
            "references/handoff-map.md."
        ),
        "sources": [],
        "confidence": (
            "boundary definitions follow the tier requirements document "
            "(knowledge cross-checked on " + KNOWLEDGE_VERIFIED_DATE
            + "); target skill names follow the current skill catalog - "
            "when a named skill is unavailable, hand off via a support "
            "ticket"
        ),
        "keywords": [
            "billing", "fee", "price", "package", "discount", "refund",
            "single disk", "cross-region", "replication", "mount",
            "commercial", "handoff", "hand off", "ticket", "invoice",
        ],
    },
}

# ---------------------------------------------------------------------------
# Handoff map (C6): neighbouring areas, recognition criteria, customer wording
# ---------------------------------------------------------------------------
HANDOFF_MAP = (
    {
        "area": (
            "Snapshot fees, storage packages, package redundancy coverage, "
            "discounts"
        ),
        "recognize": (
            "the customer's core question is about charges, deduction or "
            "purchasing decisions"
        ),
        "response": (
            "Snapshot storage fees and resource-package deduction are "
            "outside this read-only skill. Please route the question to "
            "snapshot billing consultation, or submit a support ticket so "
            "the commercial team can verify it."
        ),
    },
    {
        "area": (
            "Single-disk snapshot creation, automatic policies, "
            "cross-region replication (no multi-disk consistency need)"
        ),
        "recognize": (
            "only one disk is involved, or the customer does not need a "
            "shared point in time across disks"
        ),
        "response": (
            "Single-disk snapshot operations belong to the disk / snapshot "
            "management skill (for example "
            "alibabacloud-ebs-disk-snapshot-management in the online "
            "catalog); this skill only covers multi-disk consistency."
        ),
    },
    {
        "area": "Executing a rollback, a group creation or any other change",
        "recognize": (
            "the customer asks this skill to perform the rollback or to "
            "create / delete the group for them"
        ),
        "response": (
            "This skill is strictly read-only and never executes changes. "
            "The customer performs the operation in the ECS console; this "
            "skill states the prerequisites (stop the instance first and "
            "take a fresh snapshot backup before stopping) and "
            "re-verifies the facts afterwards."
        ),
    },
    {
        "area": "In-guest mount or partition problems after a rollback",
        "recognize": (
            "the problem is only visible inside the operating system "
            "(fstab entries, mount points, partitions)"
        ),
        "response": (
            "In-guest mount configuration must be self-checked inside the "
            "instance (fstab entries and mount order). This skill does not "
            "enter instances; hand off to a disk attach / mount diagnosis "
            "skill, or guide the customer through the self-check."
        ),
    },
    {
        "area": (
            "Console entry not visible although every support element "
            "indicates support"
        ),
        "recognize": (
            "environment / region / disk-category elements all indicate "
            "support, yet the customer still sees no entry"
        ),
        "response": (
            "Hand off to console resource-lookup and status-checking "
            "guidance; first confirm the console region selection, "
            "because snapshot resources are region-isolated."
        ),
    },
    {
        "area": "Commercial callbacks, discount applications, refunds",
        "recognize": "any commercial or approval process",
        "response": (
            "Commercial requests are handled through the support ticket / "
            "commercial channel; this skill never simulates or promises a "
            "commercial outcome."
        ),
    },
)
