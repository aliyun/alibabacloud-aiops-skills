#!/usr/bin/env python3
"""
_constants.py -- Embedded constants for the ECS disk replication DR guide
==========================================================================
SECURITY: This skill is strictly READ-ONLY. It never reads or writes any
credentials; authentication is resolved exclusively by the aliyun CLI default
credential chain. No AccessKey handling anywhere in this module.

Per platform rule MUST 1.1.2, scripts/ may only contain executable code, so
all static reference data (API metadata, limits, official documentation URLs,
disk-category semantics, visibility notes) is embedded here as Python
constants. There are NO data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-disk-replication-dr-guide"

# ---------------------------------------------------------------------------
# API metadata
# ---------------------------------------------------------------------------

# Central STS endpoint (region-less identity service). ECS regional endpoints
# are derived per region by the shared CLI layer (ecs.<region>.aliyuncs.com).
STS_ENDPOINT = "sts.aliyuncs.com"

# API versions actually used (informational; the aliyun CLI carries its own
# request metadata, and related_apis.yaml declares the same versions).
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# ---------------------------------------------------------------------------
# Limits (every network/CLI call carries a per-call timeout; MUST 7.6.1)
# ---------------------------------------------------------------------------

# Per-call timeout in seconds passed to every subprocess invocation.
DEFAULT_TIMEOUT = 60

# Page size for ECS NextToken pagination (documented maximum: 100).
MAX_RESULTS = 100

# Hard guardrail on the number of pages fetched per query loop.
MAX_PAGES = 50

# Hard guardrail on the number of regions queried per run.
MAX_REGIONS = 20

# ---------------------------------------------------------------------------
# Input validation (defense in depth; CLI calls always use argument lists,
# never a shell, so these patterns guard against typos, not injection)
# ---------------------------------------------------------------------------

REGION_ID_RE = r"^[a-z]{2,3}(-[a-z0-9]+){1,4}$"
INSTANCE_ID_RE = r"^i-[a-z0-9]{8,64}$"
DISK_ID_RE = r"^d-[a-z0-9]{8,64}$"

# ---------------------------------------------------------------------------
# Official documentation URLs
# ---------------------------------------------------------------------------
# Provenance: every URL below was opened and read in the exact form written
# here (English or Chinese, as stated) while this skill was authored; none of
# them was assembled from a slug pattern or "repaired". If a link is
# unreachable, say so and point the customer to the ECS user guide index --
# never invent a replacement URL.
DOC_URLS = {
    # Core disk-DR axis (async replication / consistency group / regional ESSD)
    "dr-overview": "https://help.aliyun.com/zh/ecs/user-guide/overview-8.md",
    "create-replication-pair": "https://help.aliyun.com/zh/ecs/user-guide/create-a-replication-pair.md",
    "create-consistency-group": "https://help.aliyun.com/zh/ecs/user-guide/create-a-replication-pair-consistent-group.md",
    "dr-failover": "https://help.aliyun.com/zh/ecs/user-guide/implement-disaster-recovery.md",
    "delete-replication-pair": "https://help.aliyun.com/zh/ecs/user-guide/delete-a-replication-pair.md",
    "regional-essd": "https://help.aliyun.com/zh/ecs/user-guide/regional-essd-disks.md",
    # Instance-level alternatives (explain the difference, then hand off)
    "clone-instance": "https://help.aliyun.com/zh/ecs/user-guide/clone-instances.md",
    "create-from-custom-image": "https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image.md",
    "same-config-instance": "https://help.aliyun.com/zh/ecs/user-guide/purchase-an-instance-with-the-same-configuration.md",
    "custom-image-overview": "https://help.aliyun.com/zh/ecs/user-guide/overview-36.md",
    # Snapshot cross-region backup: outside this skill's operation surface,
    # cited only as the hand-off target for the "snapshots are region-local"
    # boundary statement (see references/dr-capability-boundary.md).
    "copy-a-snapshot": "https://help.aliyun.com/en/ecs/user-guide/copy-a-snapshot.md",
}

# ---------------------------------------------------------------------------
# Disk-category semantics (echoed next to the raw Category values returned by
# the read-only disk query; unknown categories are echoed as-is with no note)
# ---------------------------------------------------------------------------

DISK_CATEGORY_NOTES = {
    "cloud_regional_disk_auto": (
        "zone-redundant ESSD (regional ESSD): the disk's data is replicated "
        "across multiple zones of the same region, providing built-in "
        "zone-level redundancy at the disk layer (see the regional-essd doc)"
    ),
    "cloud_essd": "ESSD cloud disk (single-zone storage; no built-in cross-zone redundancy)",
    "cloud_auto": "ESSD AutoPL cloud disk (single-zone storage)",
    "cloud_essd_entry": "ESSD Entry cloud disk (single-zone storage)",
    "cloud_ssd": "standard SSD cloud disk (single-zone storage)",
    "cloud_efficiency": "ultra disk (single-zone storage)",
    "cloud": "basic cloud disk (single-zone storage)",
}

# Categories whose data is replicated across zones by the platform itself.
ZONE_REDUNDANT_DISK_CATEGORIES = {"cloud_regional_disk_auto"}

# ---------------------------------------------------------------------------
# Visibility / permission wording shared by the entry script reports
# ---------------------------------------------------------------------------

REPLICA_VISIBILITY_NOTE = (
    "Disk async replication objects (replication pairs and consistency groups) "
    "are NOT visible through this skill's verified read-only API surface "
    "(instances, disks, snapshots only). The Block Storage documentation "
    "describes query operations for these object types, but none of them was "
    "verified for this build, so no action name is derived from an interface "
    "name and none is called. Never guess or invoke a replication-pair query "
    "API. To verify replication state, ask the customer "
    "to open the disk async replication page in the console following the "
    "navigation inside the official replication docs (see guidance_docs) and "
    "paste back the pair status or a console screenshot."
)

PERMISSION_HINT = (
    "Permission-related failure (reported as NoPermission / ImplicitDeny): "
    "grant the read-only actions listed in references/ram-policies.md, then "
    "rerun this script."
)

SCOPE_NOT_COVERED = [
    "billing details, invoices and traffic-fee attribution (no billing API is authorized for this skill)",
    "cloud backup (HBR) and other backup products outside the ECS read-only surface",
    "security-group rules and network access control",
    "guest operating-system state inside customer instances (this skill never runs in-guest commands)",
    "replication pair / consistency group object state (see the visibility note)",
]
