#!/usr/bin/env python3
"""
_constants.py -- Embedded constants and static knowledge for the
area:custom-image-lifecycle skill
====================================================================
SECURITY: this skill is NOT limited to non-mutating evidence. Its evidence
queries run automatically, and it executes the five confirmation-gated
image-chain actions listed in WRITE_ACTIONS below ONLY when the caller
explicitly passes --confirm after the end user approved the announced
impact (see SKILL.md, "User Confirmation"). Authentication is resolved
exclusively by the aliyun CLI default credential chain; this module never
reads, prints, caches or transports any AccessKey / Secret / token value.

Per platform rule 1.1.2, scripts/ may only contain executable code, so all
static reference knowledge (action whitelists, guest-inspection command
whitelist, mechanism explanations distilled from real support tickets,
error-code guidance, handoff table) is embedded here as Python constants.
There are no data files in this skill.
"""

# ---------------------------------------------------------------------------
# Skill identity & API metadata
# ---------------------------------------------------------------------------

SKILL_NAME = "alibabacloud-ecs-custom-image-lifecycle"

ECS_PRODUCT = "ecs"
STS_PRODUCT = "sts"

# API versions actually invoked (verified tier contract, pop 2014-05-26 /
# 2015-04-01). The aliyun CLI carries its own request metadata; these values
# are informational and mirror related_apis.yaml.
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# Central STS endpoint (region-less). The ecs product is regional and is
# routed by the CLI itself from --region / RegionId, so no endpoint override
# is needed for ecs.
STS_ENDPOINT = "sts.aliyuncs.com"

DEFAULT_REGION = "cn-hangzhou"

# ---------------------------------------------------------------------------
# Timeout / pagination limits (rule 7.6.1: every call carries a timeout)
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60   # seconds, per CLI invocation
PAGE_SIZE = 50         # PageSize for Describe* list queries (max allowed 100)
MAX_PAGES = 10         # guardrail: stop paging after this many pages

# Regions swept by report mode with --all-regions (the "image disappeared"
# class of tickets is frequently a wrong-region-view problem). A region whose
# query fails is recorded as a [WARN] line; nothing is fabricated.
REGION_SWEEP = [
    "cn-qingdao", "cn-beijing", "cn-zhangjiakou", "cn-huhehaote",
    "cn-wulanchabu", "cn-hangzhou", "cn-shanghai", "cn-shenzhen",
    "cn-heyuan", "cn-guangzhou", "cn-chengdu", "cn-hongkong",
    "ap-northeast-1", "ap-southeast-1", "ap-southeast-2", "ap-south-1",
    "us-west-1", "us-east-1", "eu-central-1", "eu-west-1", "me-east-1",
]

# ---------------------------------------------------------------------------
# API whitelists (single source of truth, three-way aligned with
# related_apis.yaml and references/ram-policies.md)
# ---------------------------------------------------------------------------

# Group A: automatic non-mutating evidence queries.
READ_ACTIONS = [
    "DescribeImages",
    "DescribeImageSharePermission",
    "DescribeInstanceAttribute",
    "DescribeDisks",
    "DescribeSnapshots",
    "DescribeTasks",
]

# Identity pre-check (central service, plugin-mode CLI command style).
IDENTITY_ACTION = "GetCallerIdentity"

# Group C: confirmation-gated low-risk writes of the custom-image chain.
# The agent MUST relay impact + reversibility and obtain the user's
# confirmation BEFORE running plan mode with --confirm.
WRITE_ACTIONS = [
    "CreateImage",
    "CopyImage",
    "ModifyImageSharePermission",
    "ImportImage",
    "ExportImage",
]

# Everything outside READ_ACTIONS + IDENTITY_ACTION + WRITE_ACTIONS is
# out of scope for this skill, in particular every delete / cancel / start /
# stop / attach / detach / release / refund style operation.
NEVER_EXECUTE_NOTE = (
    "Deleting images or snapshots, cancelling tasks, starting or stopping "
    "instances, detaching or releasing disks, unsubscribing or refunding are "
    "NEVER automated by this skill; they receive manual guidance and a risk "
    "notice only."
)

# ---------------------------------------------------------------------------
# Write-action metadata used by plan mode (confirmation gate text)
# ---------------------------------------------------------------------------

WRITE_OPS = {
    "create-image": {
        "action": "CreateImage",
        "purpose": ("Create a custom image from a running/normal instance or "
                    "from an existing snapshot."),
        "impact": ("Creates one new custom image plus one snapshot per disk "
                   "covered; snapshot storage is billed pay-as-you-go. No "
                   "existing resource is modified."),
        "reversibility": ("Reversible by manually deleting the image (and "
                          "its snapshots) later; deleted snapshots and "
                          "images are NOT recoverable, so keep the image id "
                          "record."),
        "required_any": ["InstanceId", "SnapshotId"],
        "required": ["RegionId", "ImageName"],
        "optional": ["Description", "ImageFamily", "Architecture",
                     "Platform", "BootMode", "Tags"],
    },
    "copy-image": {
        "action": "CopyImage",
        "purpose": ("Copy a custom image to another region (cross-region "
                    "instance creation, off-region backup)."),
        "impact": ("Creates a new image in the destination region; copy "
                   "traffic and the destination image's underlying "
                   "snapshots are billed. Only one in-progress copy task is "
                   "allowed per source image at a time."),
        "reversibility": ("Reversible by manually deleting the copied "
                          "image in the destination region."),
        "required": ["RegionId", "ImageId", "DestinationRegionId",
                     "DestinationImageName"],
        "optional": ["DestinationDescription", "ClientToken"],
    },
    "share-image": {
        "action": "ModifyImageSharePermission",
        "purpose": ("Share a self-owned custom image with other Alibaba "
                    "Cloud accounts (or revoke an earlier grant of the same "
                    "kind) inside the SAME region."),
        "impact": ("The listed accounts can then create instances from the "
                   "image in this region; sharing itself is free but the "
                   "receiver's usage is billed to them. Sharing is region-"
                   "scoped: for another region, copy the image first."),
        "reversibility": ("Fully reversible: share again with the same "
                          "account removed to withdraw the grant."),
        "required": ["RegionId", "ImageId"],
        "optional": ["AddAccount.n", "RemoveAccount.n", "IsPublic"],
    },
    "import-image": {
        "action": "ImportImage",
        "purpose": ("Import a local image file (already uploaded to an OSS "
                    "bucket) as a custom image."),
        "impact": ("Creates one custom image from the OSS object; import "
                   "consumes time proportional to image size and the guest "
                   "boot mode / drivers inside the file are NOT visible "
                   "from the cloud side (run the compatibility precheck "
                   "first)."),
        "reversibility": ("Reversible by manually deleting the imported "
                          "image afterwards."),
        "required": ["RegionId", "ImageName", "OSType", "Platform",
                     "DiskDeviceMapping.n.OSSBucket",
                     "DiskDeviceMapping.n.OSSObject"],
        "optional": ["Description", "Architecture", "BootMode",
                     "DiskDeviceMapping.n.Format",
                     "DiskDeviceMapping.n.DiskImageSize", "LicenseType"],
    },
    "export-image": {
        "action": "ExportImage",
        "purpose": ("Export a self-owned custom image to an OSS bucket as "
                    "an image file."),
        "impact": ("Produces one OSS object per disk; OSS storage and "
                   "export traffic are billed. Windows images CANNOT be "
                   "exported for local use because of licensing "
                   "restrictions (policy block, see MECHANISM_NOTES)."),
        "reversibility": ("Reversible by manually deleting the exported OSS "
                          "objects afterwards (file deletion is manual)."),
        "required": ["RegionId", "ImageId", "OSSBucket"],
        "optional": ["OSSPrefix", "ImageFormat", "RoleName"],
    },
}

# Phrase the agent passes to unlock execution; the script refuses to run any
# write action without it. One approval covers exactly one operation.
CONFIRM_PHRASE = "USER-CONFIRMED"

# ---------------------------------------------------------------------------
# Guest-inspection whitelist (inspection-only commands; they change nothing
# on the disk). Anything outside this list is refused with manual guidance.
# ---------------------------------------------------------------------------

GUEST_COMMANDS = {
    "linux": [
        {"check": "space", "cmd": "df -h",
         "purpose": "filesystem usage of every mount point"},
        {"check": "inode", "cmd": "df -i",
         "purpose": "inode usage (file-count limit), the Linux 'cannot "
                    "create new file' suspect"},
        {"check": "mount", "cmd": "findmnt",
         "purpose": "what is actually mounted where after the system disk "
                    "was replaced (data disks are NOT remounted "
                    "automatically)"},
        {"check": "data-size", "cmd": "du -sh / <major-data-dir>",
         "purpose": "order-of-magnitude data volume that explains image / "
                    "snapshot creation time"},
        {"check": "deleted-open-files", "cmd": "lsof +L1",
         "purpose": "space still held by deleted-but-open files"},
        {"check": "file-stat", "cmd": "stat <path>",
         "purpose": "metadata of one specific file"},
    ],
    "windows": [
        {"check": "space", "cmd": "Get-Volume",
         "purpose": "volume usage"},
        {"check": "mount", "cmd": "Get-PSDrive",
         "purpose": "drive visibility after a system-disk replacement"},
        {"check": "data-size", "cmd": "Get-ChildItem -Recurse (inspection-only "
                    "listing of one folder)",
         "purpose": "spot-check folder contents"},
    ],
}

# NTFS has no df -i equivalent: any Windows inode/MFT-style conclusion must
# carry an explicit confidence note.
WINDOWS_CONFIDENCE_NOTE = (
    "Windows NTFS has no direct df -i equivalent; file-count exhaustion "
    "conclusions on Windows are low-confidence and MUST be labelled as "
    "such in the report."
)

GUEST_OUT_OF_SCOPE = [
    ("inspect or install nvme/virtio drivers",
     "manual steps + adapt-linux-custom-images-to-nvme-based-system-disks "
     "documentation"),
    ("view or change grub / boot mode / EFI entries",
     "manual steps + instance-startup-mode documentation"),
    ("read or edit sshd configuration or reset the root password inside "
     "the image",
     "manual VNC login steps + the permission-denied troubleshooting "
     "documentation (see references/custom-image-lifecycle__console-guides.md)"),
    ("anything that writes, deletes, formats, repartitions or reboots",
     "never executed; manual human guidance only"),
]

# ---------------------------------------------------------------------------
# Mechanism knowledge (customer-facing wording distilled from real support
# tickets; every conclusion in a report must cite these or live API evidence)
# ---------------------------------------------------------------------------

MECHANISM_NOTES = {
    "image-needs-snapshot": (
        "A custom image is a packaged view over snapshots: an image can "
        "only exist while the snapshots behind it exist. Snapshots are "
        "billed pay-as-you-go by stored capacity; the custom image itself "
        "adds no separate item beyond the snapshots it depends on."),
    "overdue-release": (
        "When the account has been in arrears beyond the retention window "
        "(observed ticket wording: over 15 days), pay-as-you-go snapshots "
        "are auto-released and every custom image that depends on them is "
        "invalidated. Released snapshot data is NOT recoverable."),
    "auto-backup-myth": (
        "The platform does not automatically back up instance disks. With "
        "no snapshot or image of your own, there is nothing to roll back "
        "to after data loss."),
    "stopped-or-expired-block": (
        "An instance that is expired / overdue-locked (stopped for that "
        "reason) cannot produce a custom image until the subscription is "
        "renewed and the lock clears. Ordinary Running or normally "
        "Stopped instances can produce images."),
    "target-disk-must-be-at-least-image-size": (
        "The target system disk must be >= the image's system-disk size. "
        "A 100 GB image can never be restored onto a 60 GB system disk; "
        "resize the disk first or buy a larger instance."),
    "disk-shrink-unsupported": (
        "Cloud disks never shrink. The only supported path to a smaller "
        "system disk is a migration that creates the new smaller disk "
        "(SMC or a new purchase); uninstalling a system disk to swap a "
        "smaller one leaves the instance without a system disk."),
    "replace-os-touches-system-disk-only": (
        "Replacing the OS of an existing instance with a custom image "
        "replaces the SYSTEM disk content only. Data disks are untouched "
        "and must be remounted; the old system-disk data is overwritten "
        "and unrecoverable, so back it up first."),
    "new-instance-includes-checked-data-disks": (
        "Creating a NEW instance from an image carries the data disks "
        "that were checked at image-creation time; the image listing "
        "shows the system-disk size only until creation reaches 100%, "
        "then the image detail page lists the associated data disks."),
    "copy-concurrency": (
        "Only ONE in-progress copy task is allowed per source image; the "
        "account-level concurrency (observed ticket wording: 5) counts "
        "tasks across DIFFERENT images, not parallel copies of one image. "
        "A second copy submitted while the first runs fails immediately, "
        "and failed tasks may not be visible in the console task list."),
    "creation-time-no-sla": (
        "Custom-image creation is a snapshot pipeline: duration depends "
        "on data volume, concurrent snapshot tasks in the region and "
        "regional peak load. No fixed minutes or SLA can be promised; a "
        "freshly created instance is best snapshotted about 20 minutes "
        "after creation."),
    "windows-export-not-allowed-by-license": (
        "Windows custom images cannot be exported for local use because "
        "of licensing restrictions; they are usable inside Alibaba Cloud "
        "only. Snapshots themselves are not exportable either."),
    "delete-consequences": (
        "Deleting a custom image and its snapshots does not affect "
        "already-running instances, but afterwards the instance system "
        "disk can no longer be re-initialized from that image and the "
        "deleted data is unrecoverable. Deletion is never automated here."),
    "community-image-lock": (
        "An image published as a community image carries extra "
        "lifecycle coupling; removal requires the community-image flow "
        "in the console, which this skill explains but never executes."),
    "marketplace-image": (
        "Images with a cloud-marketplace origin are the vendor's "
        "responsibility for compatibility and repair; hand the customer "
        "to the image service provider / vendor support."),
    "container-image-not-ecs": (
        "Docker / ACR / ghcr.io registry pulls, pushes and 401 registry "
        "auth failures are CONTAINER images, a different product line "
        "(Container Registry); this skill does not diagnose them."),
    "public-image-selection-limits": (
        "Public images do not include Windows 10 (only Windows Server); "
        "Windows needs at least 1 GiB memory (2 GiB+ recommended); "
        "Linux <-> Windows mutual OS replacement is restricted in some "
        "region classes - verify in the console before planning."),
    "lightweight-not-compatible": (
        "ECS custom images cannot be used on Simple Application Server "
        "and vice versa; migrate data manually."),
}

# ---------------------------------------------------------------------------
# Error-code guidance (codes below are documented ECS/console failure
# strings for this chain; they are matched case-insensitively against live
# API error text; nothing is inferred beyond what is written here)
# ---------------------------------------------------------------------------

ERROR_GUIDANCE = {
    "IncorrectInstanceStatus": (
        "The instance is in a state that blocks the operation (e.g. "
        "expired and stopped by an overdue lock, or mid-transition). "
        "Evidence query: DescribeInstanceAttribute Status and "
        "OperationLocks; guidance: settle the renewal / wait for the "
        "state to settle, then retry."),
    "QuotaExceeded.Snapshot": (
        "The snapshot quota of the account / region is exhausted, which "
        "also blocks image creation (an image is built on snapshots). "
        "Evidence query: DescribeSnapshots inventory; guidance: review "
        "old snapshots in the Billing & Cost console and remove unneeded "
        "ones manually (deletion is never automated here)."),
    "InvalidDiskId.NotFound": (
        "The disk id given is wrong or lives in another region / account "
        "view. Evidence query: DescribeDisks with the corrected region; "
        "guidance: re-check the region selector and the account."),
    "NoPermission": (
        "The credential lacks the exact action named in the message. "
        "Output format: 'NoPermission - missing action: <action>; minimal "
        "policy snippet: see references/ram-policies.md' and continue with "
        "the remaining queries."),
    "ImplicitDeny": (
        "A RAM control-policy / role boundary denies the action even "
        "though no explicit deny exists. Same output format as "
        "NoPermission (name the missing action, point to the minimal "
        "policy snippet) and continue."),
    "Throttling": (
        "Transient flow control; retried automatically with backoff, then "
        "recorded as [WARN] and the run continues."),
    "InternalError": (
        "Transient service-side failure; retried automatically, then "
        "recorded as [WARN]; never conclude 'no resources' from a failed "
        "call."),
}

# ---------------------------------------------------------------------------
# Image / snapshot / task status semantics (echo live values; never map a
# status that was not returned)
# ---------------------------------------------------------------------------

IMAGE_STATUS_NOTES = {
    "Creating": ("image creation in progress; the listing may show only "
                 "the system-disk size until it reaches Available"),
    "Available": ("usable: can create instances, replace a system disk, "
                  "copy, share or export"),
    "Unavailable": ("creation failed or the image is degraded; check the "
                    "underlying snapshots' progress and tasks"),
    "CreateFailed": ("see the paired snapshot status and task records "
                     "for the failure layer"),
}

# ---------------------------------------------------------------------------
# Handoff table (recognition signal -> where the case goes). Skill names
# listed here exist in the same ECS skill family; the last three rows have
# NO same-family counterpart and are handed to the stated console / vendor
# direction without inventing a skill name.
# ---------------------------------------------------------------------------

HANDOFFS = [
    ("OS-replacement failure details (the replace-OS action itself "
     "errors out)", "area:instance-state-diagnosis",
     "This skill only explains image-side constraints; the replacement "
     "action diagnosis belongs to the OS-replace skill."),
    ("Disk space / inode exhaustion, 'no space left', 'cannot create "
     "new file'", "area:disk-expand-diagnosis",
     "In-disk capacity problems are a different area; hand over with the "
     "df output already collected."),
    ("Expansion applied but OS still shows the old size",
     "area:disk-expand-diagnosis",
     "Partition/file-system growth after a purchase is the disk-expand "
     "area."),
    ("Instance stuck in starting/stopping, will not boot",
     "area:instance-state-diagnosis",
     "State-machine diagnosis belongs to the instance-state skill; this "
     "skill adds the image-side note (boot mode / drivers) when the root "
     "cause is an image used to create it."),
    ("Image billing attribution, unsubscription, image deletion blocked "
     "by occupancy", "image billing & cleanup direction (console: Billing "
     "and Cost)",
     "This skill only clarifies that an image depends on snapshots and "
     "that snapshots are billed; the billing/cleanup lifecycle belongs "
     "elsewhere."),
    ("Deleting images/snapshots, refunds, contract, transfer-of-account "
     "approvals", "human / console process",
     "Irreversible or commercial actions are never automated; give the "
     "console path and the risk notice."),
    ("Docker / ACR / registry pull-push 401 or slow transfers",
     "Container Registry product line",
     "Container images are not ECS custom images."),
    ("Cloud-marketplace image compatibility complaints",
     "the image vendor behind the marketplace listing",
     "Marketplace image quality is the provider's responsibility."),
]

# ---------------------------------------------------------------------------
# Official documentation links (verbatim from the requirement evidence; the
# report may only cite these or URLs the live console itself shows)
# ---------------------------------------------------------------------------

HELP_LINKS = {
    "custom-image-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-36.md",
    "create-image-from-instance":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance",
    "replace-os":
        "https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance",
    "create-instance-from-custom-image":
        "https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image",
    "create-disk-from-snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot",
    "detach-data-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk",
    "release-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/release-a-disk",
    "modify-private-ip":
        "https://help.aliyun.com/zh/ecs/user-guide/modify-a-private-ip-address#e7d205ebfa1m8",
    "shrink-disk":
        "https://help.aliyun.com/zh/ecs/user-guide/shrink-a-disk",
    "resize-step1":
        "https://help.aliyun.com/zh/ecs/user-guide/step-1-resize-a-disk-to-extend-its-capacity",
    "resize-step2":
        "https://help.aliyun.com/zh/ecs/user-guide/step-2-resize-partitions-and-file-systems/",
    "re-init-system-disk":
        "https://help.aliyun.com/document_detail/25449.html",
    "instance-start-stop-status":
        "https://help.aliyun.com/zh/ecs/support/when-an-ecs-instance-is-stopped-or-restarted-in-the",
    "windows-usage-notes":
        "https://help.aliyun.com/document_detail/25430.html#section-ajc-kdx-wdb",
    "share-custom-image":
        "https://help.aliyun.com/zh/ecs/user-guide/share-a-custom-image/",
    "copy-image":
        "https://help.aliyun.com/zh/ecs/user-guide/copy-an-image",
    "instance-transfer-notice":
        "https://help.aliyun.com/document_detail/151401.htm",
    "instance-startup-mode":
        "https://help.aliyun.com/zh/ecs/user-guide/instance-startup-mode.md",
    "nvme-adapt":
        "https://help.aliyun.com/zh/ecs/adapt-linux-custom-images-to-nvme-based-system-disks",
    "virtualbox-make-image":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-virtual-machine-and-install-an-operating-system-1.md",
    "ssh-permission-denied":
        "https://help.aliyun.com/zh/ecs/user-guide/what-do-i-do-if-the-permission-denied-please-try-again-error-message-appears-when-i-log-on-to-a-linux-instance-as-the-root-user-by-using-ssh",
    "data-protection-schemes":
        "https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md",
    "create-snapshot":
        "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "snapshot-billing":
        "https://help.aliyun.com/document_detail/56159.html",
    "shared-responsibility":
        "https://help.aliyun.com/zh/ecs/user-guide/ecs-shared-responsibility-model",
    "community-image-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-12.md",
}

CONSOLE_LINKS = {
    "ecs-instance-list": "https://ecs.console.aliyun.com/server/region",
    "ecs-image-list": "https://ecs.console.aliyun.com/image",
    "ecs-snapshot-list": "https://ecs.console.aliyun.com/snapshot",
    "instance-type-by-region": "https://ecs-buy.aliyun.com/ecs#/instanceTypeByRegion",
    "billing-center": "https://usercenter2.aliyun.com/home",
    "vnc-login": "https://ecs.console.aliyun.com/vnc/index.htm",
}
