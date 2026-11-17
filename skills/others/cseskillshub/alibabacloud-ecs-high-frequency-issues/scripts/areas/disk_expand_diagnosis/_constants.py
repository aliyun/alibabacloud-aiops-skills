"""Static constants for the ECS disk expand diagnosis skill.

Every lookup table the diagnosis needs lives here as a code constant so that
``scripts/`` holds executable code only. Nothing in this module reads, stores or
transmits credential material; the aliyun CLI default credential chain is the
only authentication path used at runtime.
"""

SKILL_NAME = "alibabacloud-ecs-disk-expand-diagnosis"

# ---------------------------------------------------------------------------
# Observability (User-Agent attached to every single CLI invocation)
# ---------------------------------------------------------------------------
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"
SESSION_ID_LENGTH = 32

# ---------------------------------------------------------------------------
# API surface
# ---------------------------------------------------------------------------
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# Actions the skill may issue without a per-call confirmation.
AUTO_ALLOWED_ACTIONS = (
    "GetCallerIdentity",
    "DescribeDisks",
    "DescribeInstances",
)

# Actions that require the explicit confirm gate described in SKILL.md.
CONFIRM_GATED_ACTIONS = (
    "CreateSnapshot",
    "ResizeDisk",
    "RunCommand",
)

# Action name prefixes that must never be issued by this skill, even after a
# customer confirmation. Guidance and console entry points only.
NEVER_ALLOWED_ACTION_PREFIXES = (
    "Delete",
    "Release",
    "Remove",
    "Modify",
    "Replace",
    "Reset",
    "Attach",
    "Detach",
    "Reboot",
    "Start",
    "Stop",
    "Authorize",
    "Revoke",
    "Bind",
    "Unbind",
    "Assign",
    "Unassign",
    "Join",
    "Leave",
    "Import",
    "Export",
    "Cancel",
    "Add",
    "Put",
    "Lock",
    "Unlock",
    "Tag",
    "Untag",
)

# ---------------------------------------------------------------------------
# Timeouts / retry
# ---------------------------------------------------------------------------
CLI_TIMEOUT_SECONDS = 30
CLI_TIMEOUT_WRITE_SECONDS = 90
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 1.5
RETRYABLE_ERROR_CODES = (
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
    "SystemBusy",
    "SDK.ServerUnreachable",
    "SDK.HttpError",
)

# ---------------------------------------------------------------------------
# Guest command policy
#
# AUTO_* may be dispatched inside the instance after the confirm gate.
# HUMAN_ONLY must never be dispatched by the skill; the customer runs them and
# pastes the output back. This split is a hard acceptance constraint for this
# tier: device-level listing tools are not yet approved for automated execution,
# so the skill degrades to "ask for the readings" instead of fetching them.
# ---------------------------------------------------------------------------
AUTO_GUEST_COMMAND_EXACT = (
    "df -h",
    "df -i",
    "findmnt",
    "Get-Volume",
    "Get-PSDrive",
    "lsof +L1",
)

AUTO_GUEST_COMMAND_FAMILIES = {
    "df": ("-h", "-i", "-P", "--output", "--block-size", "--total", "--no-truncate"),
    "findmnt": ("--target", "--fstab", "--list", "--realpath", "--nofsroot"),
    "stat": (),
    "ls": ("-l", "-1", "-a", "-h", "-d", "-L"),
    "wc": ("-l",),
    "du": ("-x", "-s", "-h", "--max-depth", "--inodes", "--apparent-size"),
    "lsof": ("+L1",),
    "Get-Volume": ("-DriveLetter", "-FriendlyName", "-PartitionNumber"),
    "Get-PSDrive": ("-Name", "-PSProvider"),
    "Get-ChildItem": ("-Recurse", "-Directory", "-File"),
}

# Non-mutating fsutil query subcommands (fsutil also has mutating ones).
AUTO_FSUTIL_QUERY_PREFIXES = (
    "fsutil fsinfo volumeinfo",
    "fsutil fsinfo drivers",
    "fsutil volume diskfree",
    "fsutil dirty query",
)

# Characters/tokens that immediately disqualify a command from auto execution.
SHELL_METACHARACTERS = (";", "&&", "||", "|", "`", "$(", ">", "<", "\n", "\r", "&")

HUMAN_ONLY_GUEST_COMMANDS = (
    "lsblk",
    "lsblk -f",
    "lsblk -n",
    "lsblk && lsblk -f",
    "blkid",
    "fdisk -l",
    "fdisk -lu",
    "df -Th",
    "mount",
    "dmesg",
    "xfs_info",
    "dumpe2fs",
    "tune2fs -l",
    "pvs",
    "vgs",
    "lvs",
    "cat /etc/resolv.conf",
    "cat /etc/fstab",
    "Get-Partition",
    "Get-Disk",
    "Get-PartitionSupportedSize",
)

# Mutating or destructive operations: never auto executed, guidance only, and
# always preceded by a snapshot of the target disk.
NEVER_AUTO_GUEST_COMMANDS = (
    "growpart",
    "resize2fs",
    "xfs_growfs",
    "parted",
    "fdisk",
    "cfdisk",
    "sfdisk",
    "sgdisk",
    "mkfs",
    "mkswap",
    "fsck",
    "e2fsck",
    "xfs_repair",
    "partprobe",
    "kpartx",
    "wipefs",
    "blockdev",
    "pvresize",
    "vgextend",
    "lvextend",
    "mount",
    "umount",
    "swapon",
    "swapoff",
    "dd",
    "diskpart",
    "rescan",
    "reboot",
    "shutdown",
    "poweroff",
    "systemctl",
    "yum",
    "dnf",
    "apt",
    "apt-get",
)

# ---------------------------------------------------------------------------
# Verdicts emitted by the decision tree
# ---------------------------------------------------------------------------
VERDICT_CLOUD_NOT_RESIZED = "CLOUD_SIDE_NOT_RESIZED"
VERDICT_CLOUD_RESIZED_OS_STUCK = "CLOUD_RESIZED_GUEST_NOT_APPLIED"
VERDICT_SUSPECTED_NEW_DISK = "SUSPECTED_NEW_DISK_INSTEAD_OF_RESIZE"
VERDICT_DISK_NOT_ATTACHED = "TARGET_DISK_NOT_ATTACHED"
VERDICT_TARGET_NOT_FOUND = "TARGET_NOT_FOUND_IN_REGION"
VERDICT_INSTANCE_STATE_BLOCKED = "INSTANCE_STATE_BLOCKED"
VERDICT_FS_HEALTH_BLOCKED = "FILESYSTEM_HEALTH_BLOCKED"
VERDICT_CAPACITY_OR_INODE_BLOCKED = "CAPACITY_OR_INODE_BLOCKED"
VERDICT_PARTITION_TABLE_INCONSISTENT = "PARTITION_TABLE_METADATA_INCONSISTENT"
VERDICT_PARTITION_LAYER_NOT_ENLARGED = "PARTITION_LAYER_NOT_ENLARGED"
VERDICT_SPECIAL_LAYOUT = "SPECIAL_LAYOUT_LVM_OR_EXTENDED_PARTITION"
VERDICT_GUEST_TOOLING_MISSING = "GUEST_RESIZE_TOOLING_MISSING"
VERDICT_WINDOWS_ADJACENCY_LIMIT = "WINDOWS_ADJACENCY_LIMIT"
VERDICT_NOT_AN_ECS_DISK_RESIZE = "NOT_AN_ECS_DISK_RESIZE"
VERDICT_INIT_OR_MOUNT_AREA = "NEW_DISK_INITIALIZATION_AREA"
VERDICT_READY_TO_APPLY = "GUEST_RESIZE_READY"
VERDICT_UNKNOWN = "UNDETERMINED"

# ---------------------------------------------------------------------------
# Error / symptom signals.
#
# ``pattern`` is matched case-insensitively against customer-pasted guest
# output. Only strings that have been observed verbatim are listed as
# ``observed``; the rest are ``defensive`` matches on the documented message
# shape and are reported to the customer with lower confidence.
# ---------------------------------------------------------------------------
ERROR_SIGNALS = (
    {
        "id": "disk-category-not-supported-by-instancetype",
        "pattern": "InvalidInstanceType.NotSupportDiskCategory",
        "confidence": "observed",
        "verdict": VERDICT_DISK_NOT_ATTACHED,
        "meaning": (
            "The instance type does not support the cloud disk category being "
            "attached or resized, so the disk never became In_use and no new "
            "capacity ever arrived - this is not a billing delay. Verified live "
            "2026-10-20: ecs.t5 economy family rejects attach of "
            "cloud_essd_entry and cloud_efficiency (this exact error code) but "
            "accepts cloud_ssd, and cloud_ssd online resize 20->40 GiB succeeded."
        ),
        "disposition": (
            "Explain the instance-type x disk-category support matrix instead of "
            "the 'paid but not effective' framing. Check the category against the "
            "instance family (DescribeAvailableResource or the family documentation), "
            "then either re-create/re-attach a disk of a supported category or plan "
            "an instance-type change. No filesystem commands are relevant at this "
            "tier because the capacity never reached the instance."
        ),
        "secondary_causes": (
            "wrong zone combination between disk and instance",
            "category sold out in the zone",
        ),
        "handoff": None,
    },
    {
        "id": "resize-refused-fs-errors",
        "pattern": "Permission denied to resize filesystem",
        "confidence": "observed",
        "verdict": VERDICT_FS_HEALTH_BLOCKED,
        "meaning": (
            "The kernel refused an online resize because the filesystem carries "
            "errors. This is a data-integrity guard, not a wrong command."
        ),
        "disposition": (
            "Stop re-running the resize command. Snapshot the disk first, then a "
            "human checks and repairs the filesystem offline (e2fsck from a "
            "rescue/repair disk, or a controlled reboot where the boot-time check "
            "repairs it). Only resume the resize afterwards."
        ),
        "secondary_causes": (
            "inode table exhausted (check df -i)",
            "command not run as root (check sudo)",
        ),
        "handoff": None,
    },
    {
        "id": "already-blocks-nothing-to-do",
        "pattern": "Nothing to do!",
        "confidence": "observed",
        "verdict": VERDICT_PARTITION_LAYER_NOT_ENLARGED,
        "meaning": (
            "The filesystem already fills its partition, so resize2fs had nothing "
            "to do. The partition layer is the step that did not move."
        ),
        "disposition": (
            "Do not repeat the filesystem command. Establish the partition "
            "hierarchy with lsblk -f, fdisk -lu and blkid pasted back by the "
            "customer. Extended-partition plus logical-partition layouts and LVM "
            "layouts need their own procedure, so this tier escalates to a human "
            "instead of emitting a generic growpart command."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "gpt-pmb-mismatch",
        "pattern": "GPT PMBR size mismatch",
        "confidence": "observed",
        "verdict": VERDICT_PARTITION_TABLE_INCONSISTENT,
        "meaning": (
            "The backup GPT table and the protective MBR still describe the old, "
            "smaller disk size, so partition-table metadata disagrees with the "
            "actual device size."
        ),
        "disposition": (
            "Identify and escalate to a human engineer. Standard resize "
            "walkthroughs do not cover reconciling the backup GPT header, and "
            "improvising with fdisk or parted write mode here can destroy the "
            "partition table."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "backup-gpt-not-at-end",
        "pattern": "The backup GPT table is not at the end of the device",
        "confidence": "observed",
        "verdict": VERDICT_PARTITION_TABLE_INCONSISTENT,
        "meaning": "Backup GPT table located where the old disk end used to be.",
        "disposition": (
            "Escalate to a human, same as the PMBR mismatch signal. Do not run "
            "any partition-table writer."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "unknown-filesystem-type",
        "pattern": "unknown filesystem type",
        "confidence": "observed",
        "verdict": VERDICT_INIT_OR_MOUNT_AREA,
        "meaning": (
            "The block device carries no filesystem yet. This is a brand-new or "
            "just-attached disk that needs initialization, not a resize that "
            "failed."
        ),
        "disposition": (
            "Say plainly that this is the initialization area. Formatting a device "
            "erases it, so this tier never issues it; hand the customer the "
            "attach-and-initialize documentation and a data-loss warning."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "directory-index-full",
        "pattern": "Directory index full",
        "confidence": "observed",
        "verdict": VERDICT_FS_HEALTH_BLOCKED,
        "meaning": "ext4 directory index has hit its limit or is damaged.",
        "disposition": (
            "Filesystem health issue. Snapshot first, then human repair; the "
            "resize cannot be trusted until the check passes."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "delayed-block-allocation",
        "pattern": "Delayed block allocation failed",
        "confidence": "observed",
        "verdict": VERDICT_FS_HEALTH_BLOCKED,
        "meaning": "ext4 could not commit delayed allocation, pointing at metadata damage.",
        "disposition": (
            "Snapshot first, human filesystem repair, and check whether free "
            "space or inode exhaustion is the trigger before blaming metadata."
        ),
        "secondary_causes": ("space exhausted", "inode exhausted"),
        "handoff": None,
    },
    {
        "id": "errors-remount-ro",
        "pattern": "errors=remount-ro",
        "confidence": "observed",
        "verdict": VERDICT_FS_HEALTH_BLOCKED,
        "meaning": (
            "The mount options tell the kernel to switch the filesystem into the "
            "non-writable ro state as soon as ext4 reports an error, which is why "
            "both writes and resizes fail."
        ),
        "disposition": (
            "Report the filesystem as unhealthy and pause the resize plan. "
            "Repair must come first; that is a human operation with the instance "
            "in a controlled state."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "online-resizing-required",
        "pattern": "on-line resizing required",
        "confidence": "defensive",
        "verdict": VERDICT_FS_HEALTH_BLOCKED,
        "meaning": (
            "The filesystem was created without the feature flags that allow an "
            "online grow, so the kernel asks for an offline resize."
        ),
        "disposition": (
            "Confirm with tune2fs -l output pasted back by the customer, then plan "
            "an offline resize window. Reported with reduced confidence because "
            "this message shape is matched defensively."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "growpart-missing",
        "pattern": "growpart: command not found",
        "confidence": "observed",
        "verdict": VERDICT_GUEST_TOOLING_MISSING,
        "meaning": "The guest resize helper is not installed.",
        "disposition": (
            "Installing a package is a mutating change and stays manual. The usual "
            "root cause is an unreachable name resolver or repository, so ask the "
            "customer to run cat /etc/resolv.conf and the package manager "
            "themselves; neither is auto-executable here."
        ),
        "secondary_causes": ("missing /etc/resolv.conf", "repository unreachable"),
        "handoff": None,
    },
    {
        "id": "resolve-or-package-failure",
        "pattern": "Cannot find a valid base URL",
        "confidence": "defensive",
        "verdict": VERDICT_GUEST_TOOLING_MISSING,
        "meaning": "Package installation failed, so the resize helper never arrived.",
        "disposition": (
            "Name resolution and software repositories are outside this tier; hand "
            "the customer the manual check and keep the resize blocked until the "
            "helper is present."
        ),
        "secondary_causes": ("dns unreachable", "repo mirror removed"),
        "handoff": None,
    },
    {
        "id": "no-space-left",
        "pattern": "No space left on device",
        "confidence": "observed",
        "verdict": VERDICT_CAPACITY_OR_INODE_BLOCKED,
        "meaning": (
            "The filesystem has no free blocks, which blocks the resize tooling "
            "itself and is frequently mistaken for a failed expansion."
        ),
        "disposition": (
            "Free space first, then resize. Space and inode cleanup belongs to the "
            "disk capacity tier, so this skill states the blocker and hands off."
        ),
        "secondary_causes": (),
        "handoff": "disk-capacity",
    },
    {
        "id": "inode-100-percent",
        "pattern": "IUse%",
        "confidence": "observed",
        "verdict": VERDICT_CAPACITY_OR_INODE_BLOCKED,
        "meaning": (
            "A df -i line at 100 percent inode usage prevents metadata "
            "operations, including some resize paths."
        ),
        "disposition": (
            "Hand off to the disk capacity tier for inode cleanup. This tier only "
            "records that the blocker exists and refuses to call the resize a "
            "command failure."
        ),
        "secondary_causes": (),
        "handoff": "disk-capacity",
    },
    {
        "id": "emergency-mode",
        "pattern": "Entering emergency mode",
        "confidence": "observed",
        "verdict": VERDICT_INSTANCE_STATE_BLOCKED,
        "meaning": "Boot fell into emergency/maintenance mode.",
        "disposition": (
            "Stop the resize flow. Startup problems, including fstab entries that "
            "cannot be mounted, belong to the instance state tier. Warn the "
            "customer not to touch partitions until boot is healthy."
        ),
        "secondary_causes": ("stale fstab entry", "failed boot filesystem check"),
        "handoff": "area:instance-state-diagnosis",
    },
    {
        "id": "sulogin",
        "pattern": "sulogin",
        "confidence": "observed",
        "verdict": VERDICT_INSTANCE_STATE_BLOCKED,
        "meaning": "The boot process is asking for maintenance-shell login.",
        "disposition": "Hand off to the instance state tier before any partition work.",
        "secondary_causes": (),
        "handoff": "area:instance-state-diagnosis",
    },
    {
        "id": "startup-diagnosis-code",
        "pattern": "1662001149",
        "confidence": "observed",
        "verdict": VERDICT_INSTANCE_STATE_BLOCKED,
        "meaning": "Self-service diagnosis reported a startup or filesystem-check fault.",
        "disposition": "Hand off to the instance state tier.",
        "secondary_causes": (),
        "handoff": "area:instance-state-diagnosis",
    },
    {
        "id": "bad-superblock",
        "pattern": "bad superblock",
        "confidence": "observed",
        "verdict": VERDICT_FS_HEALTH_BLOCKED,
        "meaning": "The filesystem superblock is unusable.",
        "disposition": (
            "Human repair only, from a detached disk or rescue environment, after a "
            "snapshot. Never suggest a write-mode filesystem tool from this skill."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "windows-extend-greyed",
        "pattern": "Extend Volume",
        "confidence": "observed",
        "verdict": VERDICT_WINDOWS_ADJACENCY_LIMIT,
        "meaning": (
            "Disk Management only extends a volume into unallocated space that is "
            "immediately to its right on the same disk."
        ),
        "disposition": (
            "State the adjacency constraint, show where the unallocated space sits, "
            "and name the non-native alternatives as manual options carrying data "
            "loss risk plus a mandatory fresh snapshot."
        ),
        "secondary_causes": ("unallocated space on the left", "space on another disk"),
        "handoff": None,
    },
    {
        "id": "cross-disk-allocation",
        "pattern": "give space from",
        "confidence": "defensive",
        "verdict": VERDICT_WINDOWS_ADJACENCY_LIMIT,
        "meaning": (
            "Capacity cannot be moved from one cloud disk to another, and an "
            "existing partition cannot be shrunk or moved by the platform."
        ),
        "disposition": (
            "Say the request is not supported and offer the supported shapes: grow "
            "the disk then grow its partition, or pool several disks with LVM."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
    {
        "id": "mbr-four-partition-limit",
        "pattern": "cannot allocate more than",
        "confidence": "defensive",
        "verdict": VERDICT_SPECIAL_LAYOUT,
        "meaning": "An MBR disk holds at most four primary partitions.",
        "disposition": (
            "Report the limit. A system disk must not be converted to GPT because "
            "that breaks boot; route layout redesign to a human plan."
        ),
        "secondary_causes": (),
        "handoff": None,
    },
)

# ---------------------------------------------------------------------------
# Handoff matrix: symptom family -> owning tier -> wording
# ---------------------------------------------------------------------------
HANDOFFS = {
    "disk-capacity": {
        "target": "disk capacity and inode usage tier",
        "phrase": (
            "The blocking condition here is exhausted space or inodes, which "
            "prevents the resize commands from running. Freeing capacity comes "
            "first, so this case goes to the disk capacity and inode usage "
            "diagnosis; return to the resize once usage drops."
        ),
    },
    "area:instance-state-diagnosis": {
        "target": "ECS instance start and stop state diagnosis",
        "phrase": (
            "The instance will not boot normally or is parked in an "
            "intermediate power state, and that has to be resolved before any "
            "partition work. This case goes to the instance state diagnosis; do "
            "not continue resizing until boot is healthy."
        ),
    },
    "area:resource-bottleneck": {
        "target": "ECS disk IO performance diagnosis",
        "phrase": (
            "The reported symptom is sustained disk IO saturation or latency "
            "rather than capacity that failed to appear. This case goes to the "
            "disk IO performance diagnosis."
        ),
    },
    "alibabacloud-ecs-disaster-recovery-snapshot": {
        "target": "ECS snapshot and backup disaster recovery diagnosis",
        "phrase": (
            "The question is about backup coverage, retention or restorability, "
            "not about a resize. This tier only checks that a fresh snapshot of "
            "the target disk exists before a change, so the case goes to the "
            "snapshot and backup disaster recovery diagnosis."
        ),
    },
    "human-commercial": {
        "target": "manual support and commercial channel",
        "phrase": (
            "Billing, refunds, unsubscription, payment method, unrecoverable "
            "data or liability judgements are outside an automated diagnosis and "
            "need a human engineer to pick this up."
        ),
    },
    "security": {
        "target": "security incident response",
        "phrase": (
            "The evidence points at compromise rather than storage changes, so "
            "this needs the security incident response channel."
        ),
    },
    "migration": {
        "target": "server migration support",
        "phrase": (
            "The layout problem came from a migration job, so it belongs to "
            "migration support; this tier keeps only the partition-table and "
            "partition-count facts relevant to a later resize."
        ),
    },
}

# ---------------------------------------------------------------------------
# Customer-facing clarifying questions, in the order the decision tree asks
# them. Both exist because support cases show the ambiguity repeatedly.
# ---------------------------------------------------------------------------
CLARIFYING_QUESTIONS = (
    "Is the capacity you extended the disk size or the instance memory (RAM)?",
    "Did you grow an existing disk, or buy an additional data disk?",
    "Which region is the instance in, and can you share the instance ID or the "
    "disk ID?",
    "Has a snapshot of the target disk been taken, and at what time?",
    "Can the workload tolerate an instance stop, if an offline route becomes "
    "necessary?",
)

# Cloud console entry points that support cases actually used.
CONSOLE_LINKS = {
    "disk_list": "https://ecs.console.aliyun.com/disk/region/{region_id}",
    "resize_filesystem_tool": "https://ebs.console.aliyun.com/tools/resizeFileSystem",
}

# ---------------------------------------------------------------------------
# Documentation references. Only links that were resolved by the help search in
# the requirements phase are listed; anything unverified is marked as a gap
# rather than being guessed.
# ---------------------------------------------------------------------------
HELP_DOCUMENTS = {
    "offline_extend_linux_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "offline-extend-partitions-and-file-systems-on-a-data-disk-of-a-linux-instance.md"
    ),
    "extend_lv_with_lvm": (
        "https://help.aliyun.com/zh/ecs/user-guide/extend-an-lv-by-using-lvm.md"
    ),
    "disk_resize_and_shrink_faqs": (
        "https://help.aliyun.com/zh/ecs/disk-resizing-and-shrinking-faqs.md"
    ),
    "windows_data_restore": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "best-practices-for-restoring-data-on-windows-instances.md"
    ),
    "lock_snapshot": (
        "https://help.aliyun.com/zh/ecs/user-guide/lock-snapshot.md"
    ),
    "attach_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk.md"
    ),
    "initialize_linux_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "initialize-a-data-disk-whose-size-does-not-exceed-2-tib-on-a-linux-instance.md"
    ),
    "initialize_data_disk_overview": (
        "https://help.aliyun.com/zh/ecs/user-guide/overview-27.md"
    ),
    "use_lvm_create_logical_volume": (
        "https://help.aliyun.com/zh/ecs/user-guide/use-lvm-to-create-a-logical-volume.md"
    ),
}

# ---------------------------------------------------------------------------
# Next-action codes used in the STATUS / NEXT_ACTION contract
# ---------------------------------------------------------------------------
NEXT_ACTION_NONE = "NONE"
NEXT_ACTION_ASK_REGION = "ASK_REGION_OR_RESOURCE_ID"
NEXT_ACTION_ASK_GUEST_READINGS = "ASK_CUSTOMER_TO_RUN_AND_PASTE"
NEXT_ACTION_CONFIRM_GATE = "AWAIT_EXPLICIT_CONFIRMATION"
NEXT_ACTION_MANUAL_COMMANDS = "CUSTOMER_RUNS_GENERATED_COMMANDS"
NEXT_ACTION_SNAPSHOT_FIRST = "ENSURE_FRESH_SNAPSHOT_BEFORE_CHANGE"
NEXT_ACTION_VERIFY_CREDENTIALS = "RUN_ALIYUN_CONFIGURE"
# A refused read is not a broken credential: the identity authenticated and one
# RAM action is missing, so the remedy is a grant, not a re-configuration.
NEXT_ACTION_GRANT_PERMISSION = "GRANT_MISSING_RAM_PERMISSION"
NEXT_ACTION_RETRY_LATER = "RETRY_TRANSIENT_FAILURE"
NEXT_ACTION_STOP_AND_REPORT = "STOP_AND_REPORT_LIMITATIONS"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAILED = "FAILED"

# Authentication vocabulary. These are the only literals this skill uses for a
# denied call; the platform rejects the other common HTTP-denied wording.
AUTH_DENIED_CODES = ("NoPermission", "ImplicitDeny")
