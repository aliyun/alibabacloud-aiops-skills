"""Constants for the disk attach / OS visibility skill.

All reference data lives here as code constants: no data files are shipped in scripts/.
Every API action listed in ALLOWED_ACTIONS is declared in ../../related_apis.yaml and in
../references/ram-policies.md; anything else is out of scope and must not be invoked.
"""

import re

SKILL_NAME = "alibabacloud-ecs-disk-attach-os-visibility"


# Observability: one 32-hex-char session id per run, attached to every CLI call.
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"

CLI_BINARY = "aliyun"
ECS_PRODUCT = "ecs"
ECS_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_VERSION = "2015-04-01"
STS_ACTION_PLUGIN_MODE = "GetCallerIdentity"

# Transport limits (MUST 7.6.1: no CLI call is made without a timeout).
CLI_TIMEOUT_SECONDS = 60
CLI_POLL_TIMEOUT_SECONDS = 90
PROBE_TIMEOUT_SECONDS = 120
CLI_MAX_ATTEMPTS = 3
CLI_BACKOFF_BASE_SECONDS = 1.5
DESCRIBE_PAGE_SIZE = 100

# Actions this skill is permitted to invoke. Anything outside this set is refused.
ALLOWED_ACTIONS = (
    "DescribeInstances",
    "DescribeDisks",
    "DescribeSnapshots",
    "DescribeInvocations",
    "RunCommand",
    "GetCallerIdentity",
)

# Verb prefixes of every mutating API this skill will never call, even when the customer
# asks. They cover disk placement, disk creation and deletion, snapshot creation and
# deletion, disk initialisation, system-disk replacement, attribute and billing changes,
# capacity change, and instance power operations. Those remain human actions in the
# console, which this skill explains but never performs.
NEVER_INVOKED_VERBS = (
    "Attach",
    "Detach",
    "Create",
    "Delete",
    "Release",
    "Modify",
    "Resize",
    "Reset",
    "ReInit",
    "Replace",
    "Convert",
    "Renew",
    "Start",
    "Stop",
    "Reboot",
)

# ---------------------------------------------------------------------------
# Guest diagnostic commands
#
# RunCommand is a mutating API in the OpenAPI model, so it is used here only to
# deliver commands from the fixed list below. The list contains no command that
# writes, formats, partitions, mounts, unmounts, brings a volume online or
# offline, or restarts anything. Anything not in this list is refused by
# guest_probe.py; see ../references/disk-attach-os-visibility__guest-command-policy.md.
#
# The approved list for this tier is an upper bound; this is a deliberate subset of
# it, covering exactly what the five-step visibility chain needs. blkid, path-scoped
# stat and any read of /etc/fstab are not on the approved list at all: the customer
# runs those by hand and pastes the output.
# ---------------------------------------------------------------------------

GUEST_COMMAND_WHITELIST_LINUX = (
    "lsblk",
    "lsblk -f",
    "fdisk -l",
    "cat /proc/partitions",
    "df -h",
    "findmnt",
)

GUEST_COMMAND_WHITELIST_WINDOWS = (
    "Get-Volume",
    "Get-PSDrive",
    "fsutil fsinfo drives",
    "Get-Disk | Select-Object Number, SerialNumber, OperationalStatus | ConvertTo-Json -Compress",
    "Get-Partition | Select-Object DiskNumber, DriveLetter | ConvertTo-Json -Compress",
)

GUEST_COMMAND_WHITELIST = GUEST_COMMAND_WHITELIST_LINUX + GUEST_COMMAND_WHITELIST_WINDOWS

# Default inspect-only command sequence per OS family (one RunCommand call each,
# each needing its own confirmation). `lsblk` first because `lsblk -f` carries no size
# column and size is the join key against the cloud disk id; findmnt remains available
# as a fourth, separately confirmed command when the mount tree needs more detail.
GUEST_DEFAULT_SEQUENCE_LINUX = ("lsblk", "lsblk -f", "df -h")
GUEST_DEFAULT_SEQUENCE_WINDOWS = (
    "Get-Volume",
    "Get-PSDrive",
    "Get-Disk | Select-Object Number, SerialNumber, OperationalStatus | ConvertTo-Json -Compress",
    "Get-Partition | Select-Object DiskNumber, DriveLetter | ConvertTo-Json -Compress",
)

# Cloud Assistant command type per OS family. Confirm on the operator's CLI build
# with `aliyun ecs run-command --help` before the first probe (see guest-command-policy.md).
COMMAND_TYPE_BY_OS = {
    "linux": "RunShellScript",
    "windows": "RunPowerShellScript",
}

# ---------------------------------------------------------------------------
# Findings vocabulary
# ---------------------------------------------------------------------------

OS_LINUX = "linux"
OS_WINDOWS = "windows"
OS_UNKNOWN = "unknown"

# Control-plane observations (from DescribeDisks / DescribeInstances).
FINDING_INSTANCE_NOT_FOUND = "INSTANCE_NOT_FOUND"
FINDING_INSTANCE_STOPPED = "INSTANCE_NOT_RUNNING"
FINDING_DISK_NOT_FOUND_IN_REGION = "DISK_NOT_FOUND_IN_REGION"
FINDING_DISK_NOT_ATTACHED = "DISK_NOT_ATTACHED_IN_CLOUD"
FINDING_DISK_ATTACHING = "DISK_ATTACH_IN_PROGRESS"
FINDING_DISK_ON_OTHER_INSTANCE = "DISK_ATTACHED_TO_OTHER_INSTANCE"
FINDING_DISK_ATTACHED_TO_THIS_INSTANCE = "DISK_ATTACHED_TO_THIS_INSTANCE"
FINDING_MULTI_ATTACH = "DISK_MULTI_ATTACH_ENABLED"
FINDING_SUBSCRIPTION_PLACEMENT_LOCKED = "SUBSCRIPTION_DISK_PLACEMENT_LOCKED"

# Guest-plane observations (from inspect-only commands).
FINDING_DEVICE_NOT_ENUMERATED = "OS_DOES_NOT_ENUMERATE_DEVICE"
FINDING_NO_PARTITION = "OS_NO_PARTITION_TABLE"
FINDING_NO_FILESYSTEM = "OS_NO_FILESYSTEM"
FINDING_FILESYSTEM_NOT_MOUNTED = "OS_FILESYSTEM_NOT_MOUNTED"
FINDING_MOUNTED_AND_READABLE = "OS_MOUNTED_AND_READABLE"
FINDING_MOUNT_POINT_SHADOWING = "OS_MOUNT_POINT_SHADOWING"
FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED = "OS_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED"
FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS = "OS_WINDOWS_VOLUME_TARGET_AMBIGUOUS"
FINDING_PROBE_NOT_RUN = "OS_READINGS_NOT_COLLECTED"
FINDING_PROBE_UNAVAILABLE = "OS_READINGS_UNAVAILABLE"

# Ordered customer-facing explanation for each step of the chain. The chain is the
# answer to "the console says attached, why can I not use the disk?".
VISIBILITY_CHAIN = (
    {
        "step": 1,
        "name": "disk exists in the region",
        "plane": "cloud",
        "evidence": "DescribeDisks returns a record for the DiskId",
        "blocked_finding": FINDING_DISK_NOT_FOUND_IN_REGION,
    },
    {
        "step": 2,
        "name": "disk is attached to this instance",
        "plane": "cloud",
        "evidence": "DescribeDisks attachment lists this InstanceId",
        "blocked_finding": FINDING_DISK_NOT_ATTACHED,
    },
    {
        "step": 3,
        "name": "guest kernel enumerates the block device",
        "name_windows": "Windows enumerates the disk (Get-Disk, matched by serial)",
        "plane": "os",
        "evidence": "lsblk / fdisk -l / /proc/partitions list a device of that size",
        "evidence_windows": "Get-Disk lists a disk whose SerialNumber matches the cloud disk",
        "blocked_finding": FINDING_DEVICE_NOT_ENUMERATED,
    },
    {
        "step": 4,
        "name": "device has a partition or a whole-disk filesystem",
        "name_windows": "disk has a partition with a drive letter (Get-Partition)",
        "plane": "os",
        "evidence": "lsblk -f shows a child partition or a non-empty FSTYPE",
        "evidence_windows": "Get-Partition shows a partition on that disk number with a DriveLetter",
        "blocked_finding": FINDING_NO_FILESYSTEM,
    },
    {
        "step": 5,
        "name": "filesystem is mounted at a path the application uses",
        "name_windows": "volume is online and readable at its drive letter (Get-Volume)",
        "plane": "os",
        "evidence": "df -h / findmnt show the mount point",
        "evidence_windows": "Get-Volume shows the drive letter with OperationalStatus OK",
        "blocked_finding": FINDING_FILESYSTEM_NOT_MOUNTED,
    },
)

# Windows guest findings do not reuse the Linux blocked_finding constants, so map
# each to the chain step it actually blocks. Without this the chain loop never
# stops on a Windows finding and wrongly marks every OS step "checked and in place"
# even for an offline disk. Offline/unmapped volume => the volume is not readable
# at a drive letter (step 5); ambiguous target => the device cannot be isolated (step 3).
WINDOWS_CHAIN_STOP = {
    FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED: 5,
    FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS: 3,
}

FINDING_EXPLANATION = {
    FINDING_INSTANCE_NOT_FOUND: (
        "No instance with that id was returned in the region queried, so no disk "
        "conclusion can be drawn. Confirm the region and the instance id."
    ),
    FINDING_INSTANCE_STOPPED: (
        "The instance is not Running. Several placement and system-disk actions in the "
        "console are greyed out unless the instance is stopped or running, which customers "
        "often read as a failed operation."
    ),
    FINDING_DISK_NOT_FOUND_IN_REGION: (
        "The disk id was not returned in this region. Disk ids are region scoped: either the "
        "region is wrong or the disk has been released."
    ),
    FINDING_DISK_NOT_ATTACHED: (
        "The control plane reports the disk as not attached to any instance. Nothing the "
        "operating system does can make it visible until placement is done in the console."
    ),
    FINDING_DISK_ATTACHING: (
        "Placement is still in progress. Re-check after the operation settles before probing the OS."
    ),
    FINDING_DISK_ON_OTHER_INSTANCE: (
        "The disk is attached to a different instance than the one inspected, so it cannot appear "
        "inside this one. This is the usual cause of a disk bought for the wrong instance."
    ),
    FINDING_MULTI_ATTACH: (
        "The disk allows attachment to more than one instance. Confirm which instance is expected to "
        "read it before concluding anything about visibility."
    ),
    FINDING_SUBSCRIPTION_PLACEMENT_LOCKED: (
        "A subscription disk inherited its placement from the instance purchase, so the console entry "
        "for changing placement is greyed out. This is a billing-shape restriction, not a failed attach."
    ),
    FINDING_DEVICE_NOT_ENUMERATED: (
        "The cloud side shows the disk attached but the guest does not list a matching block device. "
        "The break is inside the operating system, not in placement."
    ),
    FINDING_NO_PARTITION: (
        "The device is visible with no partition entry. A brand new disk is never partitioned or "
        "formatted by the platform."
    ),
    FINDING_NO_FILESYSTEM: (
        "The device is visible but its filesystem type is empty, so the disk is attached and uninitialised. "
        "This is the most common cause of an attached disk that no tool lists."
    ),
    FINDING_FILESYSTEM_NOT_MOUNTED: (
        "The filesystem exists but no process can reach it, because it is not mounted at any path."
    ),
    FINDING_MOUNTED_AND_READABLE: (
        "The disk is attached, enumerated, has a filesystem and is mounted. The chain is complete."
    ),
    FINDING_MOUNT_POINT_SHADOWING: (
        "Mounting a disk on a non-empty directory hides, but does not delete, what was already there. "
        "The old content returns as soon as the filesystem is unmounted from that path."
    ),
    FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED: (
        "The Windows guest reports a volume that is offline or has no drive letter, so Explorer and "
        "path-based tools cannot see it even though the disk is attached."
    ),
    FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS: (
        "Several Windows volumes share this disk's size and the guest readings do not identify which "
        "volume is this specific disk. Their online/offline states disagree, so a per-disk conclusion "
        "cannot be drawn safely without guessing which volume the disk maps to."
    ),
    FINDING_PROBE_NOT_RUN: (
        "No guest reading was collected, so only the cloud half of the chain has been checked."
    ),
    FINDING_PROBE_UNAVAILABLE: (
        "Guest readings could not be collected through Cloud Assistant, so the OS half has to be "
        "supplied by the customer pasting command output."
    ),
}

# Manual remediation text per finding. Nothing here is executed by this skill.
FINDING_NEXT_STEP = {
    FINDING_DISK_NOT_ATTACHED: "Attach the disk to the instance from the ECS console (manual).",
    FINDING_DISK_ON_OTHER_INSTANCE: "Detach from the current instance and attach to the target one (manual, same zone).",
    FINDING_SUBSCRIPTION_PLACEMENT_LOCKED: "Convert the disk billing shape first, or buy the disk on the right instance (manual).",
    FINDING_DEVICE_NOT_ENUMERATED: (
        "Inside the guest, rescan the bus or reboot only if the customer chooses to; verify NVMe vs virtio "
        "naming before treating the disk as missing (manual)."
    ),
    FINDING_NO_FILESYSTEM: "Create a partition and a filesystem on the correct device name (manual, destructive if the device already holds data).",
    FINDING_FILESYSTEM_NOT_MOUNTED: "Create the mount point and mount the filesystem; persist it with a UUID entry if it must survive reboot (manual).",
    FINDING_MOUNT_POINT_SHADOWING: "Unmount the data disk from that directory to reveal the previous content (manual, reversible).",
    FINDING_WINDOWS_VOLUME_OFFLINE_OR_UNMAPPED: "Bring the volume online and assign a drive letter in Disk Management (manual).",
    FINDING_WINDOWS_VOLUME_TARGET_AMBIGUOUS: (
        "In Disk Management, identify this disk by disk number or serial and confirm its drive letter, "
        "then re-check that specific volume; or paste Get-Disk and Get-Partition output so the disk can "
        "be matched precisely (manual)."
    ),
}

# Guidance-only documentation links (relative-free, official help centre).
DOC_LINKS = {
    "create_and_use_disks": "https://help.aliyun.com/zh/ecs/user-guide/quickly-create-and-use-disks.md",
    "data_disk_guide": "https://help.aliyun.com/zh/ecs/user-guide/create-and-use-a-data-disk.md",
    "attach_data_disk": "https://help.aliyun.com/zh/ecs/user-guide/attach-a-data-disk",
    "detach_data_disk": "https://help.aliyun.com/zh/ecs/user-guide/detach-a-data-disk",
    "fstab_uuid": "https://help.aliyun.com/zh/ecs/user-guide/configure-uuids-in-the-fstab-file-to-automatically-attach-data-disks",
    "nvme_protocol": "https://help.aliyun.com/zh/ecs/user-guide/nvme-protocol.md",
    "limitations": "https://help.aliyun.com/zh/ecs/user-guide/limitations.md",
    "replace_os": "https://help.aliyun.com/zh/ecs/user-guide/replace-the-operating-system-of-an-instance",
    "disk_from_snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-disk-from-a-snapshot.md",
    "restore_after_os_replace": (
        "https://help.aliyun.com/zh/ecs/user-guide/use-a-snapshot-of-the-original-system-disk-to-restore-data"
        "-after-the-operating-system-of-an-ecs-instance-is-replaced"
    ),
    "release_disk": "https://help.aliyun.com/zh/ecs/user-guide/release-a-disk",
    "disk_billing_switch": "https://help.aliyun.com/zh/ecs/switch-the-billing-method-of-a-disk",
    "snapshot_billing": "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "block_storage_performance": "https://help.aliyun.com/zh/ecs/user-guide/block-storage-performance",
}

# Out-of-scope symptom routing. Key is a set of lower-case symptom fragments found in the
# customer request; value is (target skill or destination, handoff wording).
HANDOFF_ROUTES = (
    (
        ("expand", "extension", "capacity not changed", "size not changed", "not take effect", "growpart",
         "扩容", "扩展", "容量没变", "容量没有变", "大小没变", "没生效", "未生效"),
        "area:disk-expand-diagnosis",
        "The disk is attached and visible; the remaining problem is that capacity added at the "
        "control plane has not reached the partition or filesystem. That is disk expansion work.",
    ),
    (
        ("cannot boot", "not starting", "stuck starting", "ro mode", "remounted as ro", "kernel panic",
         "无法启动", "启动不了", "卡在启动", "无法开机", "只读模式", "内核崩溃"),
        "area:instance-state-diagnosis",
        "The instance itself or its root filesystem is the problem, not placement of a data disk.",
    ),
    (
        ("io hang", "iops", "bps", "throttl", "io limited", "disk util", "slow disk",
         "吞吐", "限流", "磁盘慢", "读写慢", "io慢", "io hang"),
        "area:resource-bottleneck",
        "The disk is attached; the reported symptom is throughput or IOPS saturation, which is IO diagnosis work.",
    ),
    (
        ("disk full", "no space left", "inode", "too many files", "usage 100",
         "磁盘满", "磁盘空间满", "空间不足", "没有空间", "文件太多", "使用率100"),
        "disk capacity and inode governance skill",
        "Capacity or inode consumption inside a mounted filesystem is a space-governance problem.",
    ),
    (
        ("rollback", "restore from snapshot", "shared snapshot", "snapshot to disk",
         "回滚", "快照恢复", "用快照恢复", "共享快照", "快照创建磁盘"),
        "alibabacloud-ecs-disaster-recovery-snapshot",
        "Building a disk from a snapshot and restoring data is disaster-recovery work; this skill only checks "
        "the restored disk once it is attached.",
    ),
    (
        ("refund", "renew", "billing", "overdue", "unpaid", "release the instance and get",
         "退款", "续费", "账单", "欠费", "到期"),
        "billing and lifecycle support",
        "Money, renewal and released-data questions are not diagnosable from disk state.",
    ),
    (
        ("nfs", "smb", "cifs", "nas mount", "file storage", "mount target domain",
         "文件存储", "挂载点域名"),
        "network file storage mount support",
        "The object failing to mount is a shared file system endpoint, not a block disk attached to the instance.",
    ),
    (
        ("initialise the disk", "reinit", "reset the system disk", "wipe the disk",
         "初始化磁盘", "重新初始化", "重置系统盘", "清空磁盘"),
        "manual console guidance only",
        "Re-initialising a disk erases the whole device. It is never run by this skill.",
    ),
)

# Phrases that make this skill the right entry point (mirrors the description Triggers).
IN_SCOPE_SYMPTOMS = (
    "attach",
    "attached",
    "placement",
    "cannot see",
    "can not see",
    "not visible",
    "not found",
    "missing",
    "disappear",
    "not shown",
    "not recognise",
    "not recognized",
    "df -h",
    "lsblk",
    "mount",
    "unmount",
    "mount point",
    "filesystem",
    "partition",
    "online",
    "offline",
    "drive letter",
    "system disk replaced",
    "reinstall",
    "挂载",
    "卸载",
    "云盘",
    "数据盘",
    "磁盘",
    "看不到",
    "看不见",
    "不可见",
    "不显示",
    "没有显示",
    "找不到",
    "消失",
    "识别",
    "盘符",
    "分区",
    "文件系统",
    "容量",
    "使用量",
    "已用",
)

STATUS_OK = "STATUS: OK"
STATUS_DEGRADED = "STATUS: DEGRADED"
STATUS_FAIL = "STATUS: FAIL"
STATUS_AWAITING = "STATUS: AWAITING_CONFIRMATION"

DISK_RULE_DOC_LINKS = {
    "resize_shrink_faq": "https://help.aliyun.com/zh/ecs/disk-resizing-and-shrinking-faqs.md",
    "online_extend_linux": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "offline-extend-partitions-and-file-systems-on-a-data-disk-of-a-linux-instance.md"
    ),
    "initialize_linux_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "initialize-a-data-disk-whose-size-does-not-exceed-2-tib-on-a-linux-instance.md"
    ),
    "initialize_windows_data_disk": (
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "initialize-a-data-disk-up-to-2-tib-in-size-on-a-windows-instance.md"
    ),
    "resize_filesystem_tool": "https://ebs.console.aliyun.com/tools/resizeFileSystem",
}

DISK_RULE_TOPIC_DOCS = {
    "shrink-not-supported": "resize_shrink_faq",
    "grow-in-guest": "online_extend_linux",
    "new-disk-init": "initialize_linux_data_disk",
    "snapshot-not-downloadable": "disk_from_snapshot",
    "os-replace-keep-data-disk": "replace_os",
    "attach-eligibility": "attach_data_disk",
}

DISK_RULE_CONCLUSIONS = {
    "zram-not-a-cloud-disk":
        "/dev/zram0 is a RAM-backed swap device, not a cloud disk, so the auto-mount "
        "warning is a false positive for it; validate /etc/fstab with mount -a before editing",
    "consumer-cloud-drive":
        "the wording does not yet distinguish an ECS cloud disk from the consumer "
        "Alibaba Cloud Drive netdisk, and the two have different support paths",
    "snapshot-not-downloadable":
        "a snapshot cannot be downloaded to a local computer; the supported route is "
        "snapshot to new disk, attach, copy the files, then release that disk",
    "snapshot-disk-not-visible":
        "a disk created from a snapshot already carries its partition and filesystem; when "
        "it is not visible the break is the attach or the in-guest online/mount step, not "
        "the snapshot itself",
    "spot-reclaimed-data":
        "a spot reclaim releases the instance and its release-with-instance disks, so "
        "only a pre-reclaim snapshot or a separately kept disk can still carry the data",
    "unknown-disk-origin":
        "the disk's own tags record where it came from; ACK CSI tags mean it is a "
        "dynamically provisioned container volume, not a manually bought disk",
    "attach-eligibility":
        "another data disk can be attached with NO reboot and NO stop - the instance may "
        "stay Running - provided the disk is in the same zone and not expired; the OS "
        "then still needs it initialized, mounted and persisted in /etc/fstab",
    "shrink-not-supported":
        "a cloud disk cannot be shrunk in place and forcing a shrink risks data loss or a "
        "broken filesystem; capacity only grows, so shrinking means snapshotting first, "
        "migrating to a smaller disk or image, and only then releasing the old one",
    "grow-in-guest":
        "an extended disk needs no re-attach and no re-mount; the remaining work is "
        "growing the partition and the filesystem inside the operating system",
    "os-replace-keep-data-disk":
        "replacing the operating system rebuilds the system disk only; data disks "
        "survive, must not be formatted again, and need their fstab entries rewritten",
    "file-back-to-local":
        "the goal is a file transfer back to the customer's own computer; ECS does "
        "not attach a customer-side local disk and does not extend a VPN for this",
    "new-disk-init":
        "a newly attached disk is usable only after the guest half is done, and a "
        "disk that already holds data must never be initialized or formatted",
    "windows-mount-icon":
        "a missing desktop icon is a shell setting, not a missing volume; the volume "
        "itself must be confirmed in Disk Management first",
    "rescue-disk-lib-repair":
        "missing root library directories are repaired from outside the damaged "
        "system, by attaching a rescue disk or booting rescue mode and rebuilding the "
        "merged-usr links",
    "purchase-entry":
        "this is a purchase and disk-category question, answered from the official "
        "purchase entry rather than from a diagnosis of existing resources",
    "eais-discontinued":
        "EAIS has stopped maintenance, so it can no longer be attached; the supported "
        "replacement is a GPU-accelerated ECS instance family",
    "detach-release-billing":
        "detaching a cloud disk does not stop its billing: only releasing the disk does, "
        "and a subscription disk must be converted to pay-as-you-go before it can be "
        "detached or released",
    "reboot-lost-mount":
        "a mount created with `mount` alone is lost at the next boot; a disk that "
        "disappears after a restart was never persisted in /etc/fstab",
    "df-du-mismatch":
        "`df` counts filesystem blocks while `du` counts reachable files, so the gap is "
        "usually deleted files still held open by a running process, not lost capacity",
    "mount-fail-generic":
        "attachability is decided by zone and disk status first, and only then by the "
        "in-guest partition and filesystem chain; a disk carrying data must not be formatted",
    "disk-not-visible":
        "an attached disk is only a presented block device; the OS still needs a "
        "partition, a filesystem and a mount point, and on Windows an existing volume "
        "may only be missing its drive letter",
    "nvme-device-order":
        "the kernel assigns NVMe device names at each boot, so nvme1n1 becoming nvme0n1 "
        "after a restart is normal behaviour, not a lost disk; match the disk by its "
        "WWID and mount it by filesystem UUID",
    "shared-disk-wwid":
        "the WWID under /sys/class/block/<device>/wwid is the stable identifier of the "
        "same shared disk across instances; the by-id name and the SERIAL column carry "
        "the serial number, not the WWID",
}

DISK_RULE_WINDOWS_LINES = {
    "grow-in-guest": (
        "Have the customer use Disk Management on Windows: right-click the volume and "
        "choose Extend Volume, which grows the partition and filesystem together.",
        "Ask the customer to confirm the unallocated space sits immediately after the "
        "volume; Extend Volume stays greyed out when another partition is in between.",
    ),
    "new-disk-init": (
        "Have the customer bring the disk Online in Windows Disk Management, initialize "
        "an EMPTY disk only, then create a volume and assign a drive letter.",
    ),
    "attach-eligibility": (
        "Have the customer use Windows Disk Management: right-click the offline data disk "
        "and choose Online; if it already shows Online and the partition is Healthy, "
        "nothing more is needed.",
        "Have the customer initialize an EMPTY disk only (MBR up to 2 TiB, GPT above "
        "2 TiB), then New Simple Volume, assign a drive letter and format NTFS; "
        "initializing erases the disk, so confirm it is empty first.",
    ),
    "disk-not-visible": (
        "Have the customer read the disk's state in Windows Disk Management: a disk "
        "shown Offline only needs Online, and a Healthy volume with no drive letter "
        "only needs one assigned - neither needs a new filesystem.",
        "Have the customer never initialize or format a disk made from a snapshot: it "
        "already holds a filesystem and initializing erases it.",
        "Have the customer initialize an EMPTY disk only, then New Simple Volume, "
        "assign a drive letter and format NTFS.",
    ),
}
DISK_RULE_WINDOWS_DOCS = {
    "new-disk-init": "initialize_windows_data_disk",
    "attach-eligibility": "initialize_windows_data_disk",
    "disk-not-visible": "initialize_windows_data_disk",
}
DISK_RULE_LINUX_STEP_RE = (
    r"(?i)mkfs|/etc/fstab|lsblk|mount -a|blkid|growpart|resize2fs|xfs_growfs|fdisk"
)

DISK_RULE_CONSENT_TOPICS = (
    "grow-in-guest", "new-disk-init", "zram-not-a-cloud-disk",
    "windows-mount-icon", "rescue-disk-lib-repair",
)
DISK_RULE_CONSENT_LINE = (
    "Ask the customer to approve one read-only in-guest command through Cloud Assistant "
    "so the OS half is read rather than assumed; they may run it themselves and paste "
    "the output instead."
)

DISK_RULE_TOPICS = (
    ("zram-not-a-cloud-disk", (
        "zram",
    ), (
        "Have the customer treat `/dev/zram0` as a zram RAM-backed swap device, not a cloud "
        "disk: it must NOT be written into /etc/fstab, so that inspector warning is a false "
        "positive for this device.",
        "Ask the customer to run and paste `mount -a` first: it validates /etc/fstab without "
        "changing anything, so a real fault is separated from a false alarm before any edit.",
        "Ask the customer to run and paste `lsblk` and `swapon --show` so only real cloud "
        "disks are considered for /etc/fstab.",
        "Ask the customer for consent before any further in-guest read, and for the full "
        "inspector text so the remaining devices are judged one by one.",
    )),
    ("eais-discontinued", (
        "弹性加速", "eais",
    ), (
        "Have the customer know EAIS (Elastic Accelerated Instance Service) has stopped "
        "maintenance, so it can no longer be attached to an instance and the console reports "
        "the service as suspended.",
        "Have the customer move to a GPU-accelerated ECS instance family instead, and choose "
        "the family by the workload's memory and driver needs.",
        "Ask the customer for a screenshot of the exact suspension message so the affected "
        "product is confirmed before any purchase is recommended.",
    )),
    ("windows-mount-icon", (
        "桌面右键", "桌面图标", "desktop icons", "回收站",
    ), (
        "Ask the customer for consent to inspect the guest, and have them snapshot the disks "
        "and pick a low-traffic window before any restart is used to verify a change.",
        "Have the customer open Desktop Icons Settings from the desktop right-click menu and "
        "tick the items they expect to see: Home, Recycle Bin and the mounted-disk entry.",
        "Have the customer create the missing user profile directory (for example /home/<user> "
        "on a Linux desktop) when the icon is absent because the directory does not exist.",
        "Have the customer confirm whether the volume itself is visible in Disk Management "
        "first: a missing desktop icon and a missing volume are different problems.",
    )),
    ("rescue-disk-lib-repair", (
        "库文件缺失", "关键库", "lib64", "/lib缺失",
    ), (
        "Have the customer snapshot the system disk first, then attach a rescue disk or boot "
        "into rescue mode so the damaged root filesystem can be edited from outside it.",
        "Have the customer rebuild the missing links at the rescued root: /lib, /lib64, /bin "
        "and /sbin pointing at their /usr counterparts, which is what a merged-usr image "
        "expects.",
        "Ask the customer to verify a new login works before the rescue disk is detached, so "
        "the repair is proven rather than assumed.",
        "Have the customer rotate any credential that may have leaked and delete the rescue "
        "snapshot only after they confirm the instance is healthy.",
    )),
    ("purchase-entry", (
        "如何购买", "怎么购买", "购买云服务器", "在哪买",
    ), (
        "Have the customer use the official ECS purchase entry: "
        "https://ecs-buy.aliyun.com/instanceTypes/ , choosing region, zone, instance family "
        "and image before the disk step.",
        "Have the customer know the disk categories differ by performance and price: ESSD "
        "offers performance levels PL0 to PL3, while entry-level categories cap IOPS lower; "
        "the category can be changed later, the capacity can only grow.",
        "Have the customer treat any price shown as reference only and confirm it on the "
        "official purchase page, which this skill does not guarantee stays current.",
    )),
    ("consumer-cloud-drive", (
        "阿里云盘", "网盘", "adrive", "aliyundrive", "云盘打不开",
    ), (
        "Ask the customer which product they mean: an ECS cloud disk (block storage attached "
        "to an instance) or Alibaba Cloud Drive (the consumer netdisk app); the support paths "
        "are different.",
        "Ask the customer for a screenshot of the exact error and where it appears: the "
        "console, inside the instance, or the netdisk client.",
        "Have the customer route a netdisk problem to that product's own support: the in-app "
        "or PC client 'submit a problem' entry, service hours 09:00-18:00, mailbox "
        "adrive@service.alibaba.com.",
        "Have the customer keep ECS cloud-disk symptoms here: attach state, device "
        "enumeration and mount are what this diagnosis reads.",
    )),
    ("snapshot-disk-not-visible", (
        "快照挂载", "快照创建的盘", "快照建盘", "快照盘看不到", "快照创建的云盘",
    ), (
        "Have the customer know a disk created from a snapshot already carries its partition "
        "and filesystem: it must NEVER be initialized or formatted again.",
        "Have the customer confirm in the console that this disk is attached to THIS instance "
        "in the same zone, and note the device name it was given.",
        "Have the customer bring it online in Windows Disk Management without initializing, "
        "or mount it by UUID on Linux, persist /etc/fstab with `defaults,nofail` and check "
        "`mount -a`.",
    )),
    ("snapshot-not-downloadable", (
        "快照下载", "快照如何下载", "快照怎么下载", "下载快照", "导出快照",
        "快照到本地", "快照的内容下载", "download a snapshot", "snapshot to local",
        "查看快照", "快照内容", "快照里的数据", "快照的数据", "看快照",
        "view snapshot", "snapshot content",
    ), (
        "Have the customer know a snapshot cannot be downloaded to a local computer "
        "directly: it is not exposed as a file.",
        "Have the customer create a cloud disk from that snapshot in the SAME zone as a "
        "running instance, then attach it as a data disk.",
        "Have the customer bring it online in Windows Disk Management or mount it on Linux "
        "and copy only the files they need, never initializing or formatting it: it already "
        "carries the source filesystem.",
        "Have the customer unmount, detach and release that temporary disk afterwards so it "
        "stops billing; the snapshot itself is kept.",
    )),
    ("spot-reclaimed-data", (
        "抢占式", "spot instance", "竞价实例",
    ), (
        "Have the customer know a spot reclaim releases the instance and every disk set to "
        "release with it: without a snapshot or a separately kept disk, that data cannot be "
        "recovered.",
        "Ask the customer whether a snapshot exists from before the reclaim, or whether the "
        "data disk was created separately with 'release with instance' disabled; only those "
        "two still carry the data.",
        "Have the customer create a disk from the surviving snapshot and attach it to a new "
        "instance in the same zone to read the data back.",
        "Have the customer stop expecting a snapshot of an already released instance: a "
        "snapshot can only be taken from a disk that still exists.",
    )),
    ("unknown-disk-origin", (
        "哪里来的", "哪儿来的", "以前属于", "之前属于", "待挂载的云盘", "这盘是谁",
        "where did this disk", "whose disk",
    ), (
        "Have the customer read the disk tags in the console: `acs:ecs:lastAttachedInstance` "
        "names the instance the disk was last attached to.",
        "Have the customer check the `createdby` tag written by the ACK CSI plugin (its "
        "value ends with `csi-plugin`), `k8s.aliyun.com` and `kubernetes.io/created-for`: "
        "those tags mean the disk is a dynamically provisioned ACK CSI volume, not a "
        "manually bought disk.",
        "Have the customer trace such a disk in the Container Service console by its PVC/PV "
        "instead of attaching it by hand; detaching it from a node can break the workload "
        "that owns it.",
        "Have the customer know an unattached disk still bills until it is released, and it "
        "only attaches to an instance in the same zone.",
    )),
    ("attach-eligibility", (
        "还是否可以", "是否可以挂载", "能不能挂", "可以挂载吗", "能否挂载", "是否可以往",
        "能否再挂", "再挂载", "还能挂", "是否可以再", "只能挂载", "其他区域", "跨区域",
        "跨地域", "同地域", "同一个地域", "有挂在", "挂在实例",
        "过期", "已到期",
    ), (
        "Have the customer know attaching another data disk needs NO reboot and NO stop: "
        "the instance may be Running or Stopped, and the attach takes effect immediately.",
        "Have the customer initialize the disk after the attach: the console Cloud Assistant "
        "one-click init (GPT + ext4) or partition, mkfs and mount by hand; a console-init "
        "mount is temporary, so persist it with a UUID entry in /etc/fstab.",
        "Have the customer confirm the disk is in the SAME zone and its status is "
        "`Available`; an expired or locked disk must be renewed first, and a disk in another "
        "zone cannot be selected on the attach page.",
        "Have the customer stop the billing deliberately: renew if needed (an unrenewed "
        "subscription disk is released about 15 days after expiry, data unrecoverable), "
        "back the data up, then release the disk manually; detaching alone does not stop "
        "disk billing.",
    )),
    ("shrink-not-supported", (
        "缩容", "缩小", "减小", "降容", "变小", "改小", "shrink", "reduce the size",
    ), (
        "Have the customer know no console or API shrinks a disk; for a DATA disk: "
        "snapshot first, buy a smaller disk in the same zone, copy and verify, switch the "
        "mount, then detach, convert to pay-as-you-go and release the old disk.",
        "Have the customer know a SYSTEM disk cannot be reduced: buy a smaller "
        "instance or image and migrate with SMC; it is rebuilt, not shrunk.",
        "Have the customer compare prices on the console disk purchase page without "
        "paying; treat prices and refunds as reference only and re-check them on the "
        "official page.",
    )),
    ("file-back-to-local", (
        "本地硬盘", "传回本地", "本地电脑", "扩展vpn", "挂载本地", "下载到本地",
    ), (
        "Ask the customer to confirm the real goal: copying files from the instance back to "
        "their own computer, rather than attaching a local disk to the instance.",
        "Have the customer know ECS does not attach a customer-side local disk and does not "
        "extend a VPN for this; the supported route is a file transfer.",
        "Have the customer use Windows remote desktop (mstsc) with local drives redirected "
        "on the Local Resources tab, then copy the files across inside that session.",
        "Have the customer use scp or SFTP from their own computer for a Linux instance "
        "instead of a disk mount.",
    )),
    ("grow-in-guest", (
        "扩容", "扩展", "硬盘空间", "存储块", "买了空间", "容量没变", "容量没有变",
        "没加上", "扩容后", "growpart", "resize2fs", "extend the disk", "resize the disk",
        "查询只有", "实际只有", "容量对不上", "大小对不上",
    ), (
        "Have the customer know an extended disk needs NO re-attach or re-mount; approve "
        "one read-only Cloud Assistant command or paste `lsblk`/`df -Th`/`blkid` for the "
        "partition and filesystem type.",
        "Have the customer snapshot the disk first, then grow the partition with "
        "`growpart <device> <partition-number>`, e.g. `growpart /dev/nvme0n1 1`.",
        "Have the customer grow the filesystem: `resize2fs <partition>` for ext4 or "
        "`xfs_growfs <mount-point>` for XFS, then `df -h`; an ADDITIONAL disk needs init "
        "and mount instead.",
    )),
    ("os-replace-keep-data-disk", (
        "更换操作系统", "换系统", "重装系统", "升级到ubuntu", "升级到 ubuntu",
        "系统盘更换", "replace the operating system", "升级系统",
    ), (
        "Have the customer know replacing the OS rebuilds the SYSTEM disk only: data disks "
        "survive and must not be formatted again, everything on the system disk is erased.",
        "Have the customer snapshot the system disk, create a temporary disk from that "
        "snapshot, attach it, mount it at an EMPTY /mnt directory and copy the data off "
        "before replacing.",
        "Have the customer verify the copy and the workload after the replacement, then "
        "unmount, detach and release the temporary disk; re-write /etc/fstab for the data "
        "disks they keep.",
    )),
    ("nvme-device-order", (
        "nvme1n1", "nvme0n1", "磁盘顺序", "设备名", "盘符顺序",
        "device order", "device name",
    ), (
        "Have the customer know the kernel assigns NVMe device names at each boot, so "
        "nvme1n1 becoming nvme0n1 after a restart is normal behaviour, not a lost disk.",
        "Have the customer match the disk by its stable identifier instead: "
        "`lsblk -o NAME,SIZE,WWN,SERIAL` and `cat /sys/class/block/<device>/wwid`.",
        "Have the customer pin /etc/fstab to the filesystem UUID with `defaults,nofail`, "
        "never to a /dev/nvme* name, so an order change cannot break the mount.",
        "Have the customer confirm the data is still readable at the expected directory "
        "after the restart before treating it as a fault.",
    )),
    ("reboot-lost-mount", (
        "重启后", "重启之后", "开机后", "没有自动挂载", "未自动挂载", "不自动挂载",
        "自动挂载", "重启服务器磁盘", "after reboot", "after a restart", "fstab",
    ), (
        "Have the customer know a mount made with `mount` alone is lost at the next boot: "
        "a disk gone after a restart was never persisted in /etc/fstab.",
        "Have the customer approve one read-only Cloud Assistant command or paste "
        "`lsblk -f`/`blkid`/`cat /etc/fstab`: no filesystem means the disk was never "
        "initialized, not a lost mount.",
        "Have the customer snapshot first, back up /etc/fstab, pin the UUID `blkid` "
        "reports with `defaults,nofail` (a stale UUID is itself a cause), and validate "
        "`mount -a` before rebooting.",
    )),
    ("new-disk-init", (
        "怎么挂载", "如何挂载", "帮我挂", "帮忙挂", "帮挂", "挂载上", "初始化",
        "不会配置", "帮我配置", "新的数据盘", "新挂载", "挂到这台实例", "在哪里将",
        "attach a new disk", "mount a new disk",
    ), (
        "Ask the customer whether the disk is brand new and empty or already holds data, and "
        "which directory it should appear at: a disk with data must NEVER be initialized or "
        "formatted.",
        "Have the customer confirm the disk and the instance are in the SAME zone; a disk in "
        "another zone cannot be selected, and moving it means creating a new disk from its "
        "snapshot in the target zone.",
        "Have the customer attach it in the console (ECS console > Disks > Attach), then use "
        "the Cloud Assistant initialize entry, or partition and format an EMPTY disk "
        "themselves.",
        "Ask the customer to run and paste `blkid` and `cat /etc/fstab`, then mount by UUID "
        "and persist it with a `defaults,nofail` entry.",
        "Have the customer validate with `mount -a`, `cat /etc/fstab` and `df -h` before "
        "rebooting, so a wrong entry cannot block the next boot.",
    )),
    ("detach-release-billing", (
        "无法卸载", "不能卸载", "卸载不了", "删不掉", "无法删除", "无法释放", "不能释放",
        "卸载 然后", "卸载后", "卸载再", "先卸载",
        "释放不了", "卸载退订", "退订", "解除挂载", "已经卸载", "卸载了", "转挂",
        "挂到新", "cannot detach", "can't detach",
    ), (
        "Have the customer know detaching a disk does NOT stop its billing: only releasing "
        "it does, release destroys data, and the bill settles 2-3 hours later, so snapshot "
        "first.",
        "Have the customer convert a subscription (包年包月) disk to pay-as-you-go first, "
        "then detach it before releasing: an attached disk cannot be released.",
        "Ask for the detach error text and RequestId; if the console detach fails, unmount "
        "in the guest (Windows: take the disk Offline in Disk Management) or stop the "
        "instance off-peak, then retry.",
    )),
    ("shared-disk-wwid", (
        "wwid", "wwn", "序列号", "serial", "唯一标识", "多重挂载", "共享盘",
    ), (
        "Ask the customer to approve one read-only Cloud Assistant command or paste "
        "`cat /sys/class/block/<device>/wwid` (e.g. nvme3n1): on NVMe shared disks this is "
        "the stable identifier of the same disk across instances.",
        "Ask the customer to run and paste `lsblk -o NAME,SIZE,WWN,SERIAL` to list every "
        "device with its WWN and serial side by side.",
        "Have the customer know the name under /dev/disk/by-id and the SERIAL column carry "
        "the disk's serial number, not its WWID; never match a shared disk by /dev/vdX or "
        "by serial alone.",
    )),
    ("df-du-mismatch", (
        "du -sh", "df -h和du", "df 和 du", "空间被占满", "空间满", "占用不到",
        "查各个文件夹", "deleted", "lsof", "空间不对", "使用不匹配", "不匹配",
        "空间去哪", "不知道用在哪",
    ), (
        "Have the customer know `df` counts blocks while `du` counts reachable files: the "
        "gap is usually deleted files still held open by a process.",
        "Have the customer approve one read-only Cloud Assistant command or paste "
        "`lsof +L1`, a layered `du -sh /path/*` walk and `ls -la` for hidden dirs, including "
        "dirs hidden under a mount point.",
        "Have the customer snapshot the disks, then restart or stop the process holding "
        "those files off-peak to release space; deleting more files does not help.",
    )),
    ("mount-fail-generic", (
        "无法挂载", "不能挂载", "挂载不了", "挂不上", "云盘挂载", "数据盘挂载",
        "拓展盘", "扩展盘", "不影响业务",
        "挂载问题", "协助挂载", "需要挂载", "挂载云盘", "怎么使用数据盘", "使用数据盘",
    ), (
        "Have the customer confirm the SAME region and zone and the disk is unattached; "
        "else copy via snapshot.",
        "Have the customer approve one read-only Cloud Assistant command or paste it "
        "themselves: `lsblk -f`/`blkid` by size (console /dev/xvdb = guest /dev/vdb).",
        "Have the customer mount an existing filesystem at an EMPTY dir by UUID "
        "`defaults,nofail`, then `mount -a`; snapshot first and partition/`mkfs.ext4` ONLY if "
        "`lsblk -f` shows none and they confirm it is new - all data will be lost, NEVER "
        "partition or format a data disk.",
    )),
    ("disk-not-visible", (
        "识别不出", "看不到", "没有了", "不见了", "检测不到", "找不到盘",
        "检测到盘", "检测到磁盘", "能检测到", "识别到盘",
        "没有显示", "没显示",
        "没有用上", "没用上", "显示只有", "未初始化",
    ), (
        "Have the customer approve one read-only Cloud Assistant command or paste "
        "`lsblk -f`: an attached disk is only a block device until mounted.",
        "Have the customer never partition/format a snapshot-made disk (it already has "
        "a filesystem); on Windows assign a drive letter.",
        "Have the customer snapshot first, then initialize ONLY if `lsblk -f` shows none "
        "and it is confirmed new - all data will be lost: console Block Storage > Cloud "
        "Assistant detection > Initialize (temp mount) or partition + `mkfs.ext4`; persist "
        "UUID `defaults,nofail`.",
    )),
)

AGENT_OFFLINE_DOC = (
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "stop-and-uninstall-the-cloud-assistant-agent.md")
AGENT_OFFLINE_RE = re.compile(
    r"(?:云助手|云监控|云安全中心|插件|\bagent\b)[^。；\n]{0,24}"
    r"(?:失效|消失|不见|离线|停止|停了|没了|未运行|掉线|无法连接)"
    r"|(?:失效|消失|不见|离线|停止|停了|没了)[^。；\n]{0,16}"
    r"(?:云助手|云监控|插件|\bagent\b)", re.I)
AGENT_OFFLINE_PROCEDURE_RE = re.compile(
    r"(?:如何|怎么|怎样|能否|可以|想要?)[^。；\n]{0,12}(?:停止|卸载|关闭|禁用)")
AGENT_OFFLINE_LINES = (
    "Have the customer check the Agent first: plugins vanishing after a reboot "
    "usually mean the Cloud Assistant and monitoring agents were stopped.",
    "Have the customer log in over VNC and start BOTH agents on boot: Cloud Assistant "
    "(`systemctl start aliyun.service`; Aliyun Assist Service on Windows) and the "
    "CloudMonitor plugin `argusagent`.",
    "Have the customer read only after the Agent is online: a stopped Agent accepts "
    "no command, and a forced reboot drops writes still only in memory.",
)


def agent_offline_signal(question):
    text = question or ""
    if AGENT_OFFLINE_PROCEDURE_RE.search(text):
        return False
    return bool(AGENT_OFFLINE_RE.search(text))


DISK_RULE_TOPIC_DOCS["agent-offline"] = "agent-offline"
DISK_RULE_DOC_LINKS["agent-offline"] = AGENT_OFFLINE_DOC
