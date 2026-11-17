"""Constants for the ECS Cloud Backup (HBR) diagnosis skill.

Every lookup table this skill uses is embedded here as code. No data files are
shipped under scripts/ (static rule 1.1.2).
"""

SKILL_NAME = "alibabacloud-ecs-hbr-backup-diagnosis"

# Observability: one session id per process, attached to every CLI call.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

# aliyun CLI is invoked in argument-list mode only; never through a shell.
CLI_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 40
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

# ecs / sts RPC API versions actually called by this skill.
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"

# Pagination ceilings for the informational queries.
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100
INVOCATION_LOOKBACK_MINUTES = 60

# RunCommand polling: the guest command is dispatched, then its status is read
# back through DescribeInvocations with IncludeOutput.
GUEST_POLL_INTERVAL_SECONDS = 5
GUEST_POLL_MAX_ATTEMPTS = 12

# Actions whose failures are worth a bounded retry.
TRANSIENT_ERROR_TOKENS = (
    "Throttling",
    "ThrottlingUser",
    "InternalError",
    "ServiceUnavailable",
    "RequestTimeout",
    "SystemBusy",
)

# Authentication failures must be reported with these literals only.
AUTH_ERROR_TOKENS = ("NoPermission", "ImplicitDeny")
CREDENTIAL_ERROR_TOKENS = ("InvalidSecurityToken", "MissingCredential", "NoCredential")

# Redaction applied to every stderr / error message before it reaches output.
SECRET_VALUE_PATTERNS = (
    r"(AccessKeyId\s*[=:]\s*)\S+",
    r"(AccessKeySecret\s*[=:]\s*)\S+",
    r"(SecurityToken\s*[=:]\s*)\S+",
    r"(Signature\s*[=:]\s*)\S+",
)
MASKED = "***REDACTED***"

# ---------------------------------------------------------------------------
# API surface. Params are limited to those verified for this tier; anything not
# listed here is never sent. CloudMonitor metrics were deliberately left out -
# see references/hbr-backup-diagnosis__decision-tree.md "Known gaps".
# ---------------------------------------------------------------------------
API_ECS_DESCRIBE_INSTANCES = "DescribeInstances"
API_ECS_DESCRIBE_DISKS = "DescribeDisks"
API_ECS_DESCRIBE_SNAPSHOTS = "DescribeSnapshots"
API_ECS_DESCRIBE_INVOCATIONS = "DescribeInvocations"
API_ECS_RUN_COMMAND = "RunCommand"
API_ECS_CREATE_SNAPSHOT = "CreateSnapshot"
API_STS_GET_CALLER_IDENTITY = "GetCallerIdentity"

# ---------------------------------------------------------------------------
# Symptom classification. Matching is ASCII-only: the console localises its
# message text, so matching relies on stable product tokens plus the English
# wording a customer dictates or pastes. Unmatched text -> UNKNOWN, and the
# caller is asked to pass --category explicitly.
# ---------------------------------------------------------------------------
CATEGORY_CLOUD_ASSISTANT = "CLOUD_ASSISTANT_UNREACHABLE"
CATEGORY_DISK_SPACE = "DISK_SPACE_INSUFFICIENT"
CATEGORY_ECS_RELEASED = "ECS_RELEASED"
CATEGORY_RESTORE_SKIPPED = "RESTORE_TARGET_OCCUPIED"
CATEGORY_ROLE_OR_BILLING = "ROLE_OR_BILLING_BLOCKED"
CATEGORY_BACKUP_TASK = "BACKUP_TASK_ABNORMAL"
CATEGORY_UNKNOWN = "UNKNOWN"

ALL_CATEGORIES = (
    CATEGORY_CLOUD_ASSISTANT,
    CATEGORY_DISK_SPACE,
    CATEGORY_ECS_RELEASED,
    CATEGORY_RESTORE_SKIPPED,
    CATEGORY_ROLE_OR_BILLING,
    CATEGORY_BACKUP_TASK,
    CATEGORY_UNKNOWN,
)

# Highest priority first; the first category that matches wins.
SYMPTOM_PATTERNS = (
    (
        CATEGORY_ECS_RELEASED,
        (
            "ecsreleased",
            "instance has been released",
            "instance was released",
            "released instance",
        ),
    ),
    (
        CATEGORY_CLOUD_ASSISTANT,
        (
            "cannot access cloud assistant",
            "unable to access cloud assistant",
            "cloud assistant service",
            "cloud assistant agent",
            "aliyun assist",
            "environment is abnormal",
            "internal environment",
            "assist service is not running",
        ),
    ),
    (
        CATEGORY_DISK_SPACE,
        (
            "insufficient disk space",
            "disk space is insufficient",
            "not enough disk space",
            "no space left on device",
            "disk is full",
            "cannot create new file",
            "file count limit",
            "inode exhausted",
            "out of inodes",
        ),
    ),
    (
        CATEGORY_RESTORE_SKIPPED,
        (
            "restore completed",
            "restoration finished",
            "restore succeeded but",
            "files are still missing",
            "data is still missing",
            "file is being used",
            "being used by another process",
            "cannot overwrite",
            "skipped files",
            "skip and overwrite",
        ),
    ),
    (
        CATEGORY_ROLE_OR_BILLING,
        (
            "aliyunserviceroleforhbrecsbackup",
            "service-linked role",
            "service linked role",
            "role cannot be created",
            "failed to create the role",
            "overdue payment",
            "account is in arrears",
            "in debt",
            "billing method",
            "resource plan",
            "resourcepackage",
            "how to stop the billing",
            "cancel the backup",
            "delete the backup plan",
            "delete the backup vault",
            "warehouse rental",
        ),
    ),
    (
        CATEGORY_BACKUP_TASK,
        (
            "backup task",
            "backup job",
            "backup failed",
            "backup keeps failing",
            "backup alarm",
            "backup alert",
            "backup notification",
            "file backup",
            "whole-instance backup",
            "backup plan",
            "backup vault",
            "cloud backup",
        ),
    ),
)

# ---------------------------------------------------------------------------
# Root-cause candidates, keyed by category. Every entry was observed in a real
# historical support case for this tier (provenance: references/hbr-backup-diagnosis__error-catalog.md).
# Candidate text is guidance only - the skill never applies a fix itself.
# ---------------------------------------------------------------------------
ROOT_CAUSE_CANDIDATES = {
    CATEGORY_CLOUD_ASSISTANT: (
        {
            "id": "overlay-network-range-conflict",
            "summary": (
                "A third-party tunnel or mesh product (Tailscale is the most frequent one in "
                "this tier) claims the 100.64.0.0/10 or 100.100.0.0/16 range that Alibaba Cloud "
                "internal service endpoints use, so the instance can no longer reach Cloud "
                "Assistant even though the security group is open."
            ),
            "confidence": "high",
            "case_refs": ("T-0DDE6FAC", "T-29709FD4"),
            "manual_checks": (
                "Compare the route table inside the OS against the reserved ranges before and "
                "after the tunnel client starts.",
                "Self-check commands (customer runs these, the skill does not): ip route / "
                "route -n / ifconfig on Linux, Get-NetRoute on Windows.",
            ),
            "verified_mitigation": (
                "Where the customer must keep the tunnel product, the case-verified workaround "
                "is to stop it from injecting that range, e.g. starting it with "
                "--netfilter-mode=off. Disabling or stopping a third-party service is a "
                "service change and stays manual."
            ),
        },
        {
            "id": "dns-overwritten-by-client",
            "summary": (
                "A VPN or client-software suite rewrites the system resolver, so the Cloud "
                "Assistant service domain stops resolving. Restarting the agent or the instance "
                "only fixes it until the client rewrites DNS again."
            ),
            "confidence": "high",
            "case_refs": ("T-4149C679",),
            "manual_checks": (
                "Inspect /etc/resolv.conf (Linux) or Get-DnsClientServerAddress (Windows) for "
                "an unexpected nameserver.",
                "Resolve the Cloud Assistant endpoint manually to confirm the resolver is the "
                "broken link.",
            ),
            "verified_mitigation": (
                "Restore the nameserver the instance shipped with, or exclude it from the "
                "client's DNS enforcement. Reverting the client's launch flags was sufficient in "
                "the source case but recurs unless the flag is removed from the service."
            ),
        },
        {
            "id": "assist-service-stopped",
            "summary": (
                "The Aliyun Assist service is stopped or disabled inside the OS, so no agent is "
                "present to run the backup helper."
            ),
            "confidence": "high",
            "case_refs": ("T-9005CD95",),
            "manual_checks": (
                "Windows: Server Manager / services.msc, look for Aliyun Assist service and read "
                "its status and startup type. Linux: check the assistant daemon status.",
            ),
            "verified_mitigation": (
                "Starting or enabling the service is a service change and is manual; the case "
                "was resolved after the support engineer logged in with customer authorisation."
            ),
        },
        {
            "id": "resource-saturation",
            "summary": (
                "Sustained CPU saturation prevents the agent process from being scheduled, so "
                "backup fails daily at the scheduled window. CloudMonitor was not queried by "
                "this skill version (see Known gaps), so treat this as a hypothesis to test."
            ),
            "confidence": "medium",
            "case_refs": ("T-9ED3CF6E",),
            "manual_checks": (
                "Compare the failure timestamps with the busiest window of the workload; "
                "identify top consumers with the OS task manager or top.",
            ),
            "verified_mitigation": "Manual: reduce or reschedule the competing workload.",
        },
    ),
    CATEGORY_DISK_SPACE: (
        {
            "id": "guest-volume-full",
            "summary": (
                "The volume inside the instance is full, so the backup helper cannot write its "
                "local working data. This is NOT the backup storage quota; customers conflate "
                "the two constantly."
            ),
            "confidence": "high",
            "case_refs": ("T-2E38E856",),
            "manual_checks": (
                "Confirm which volume is full, then find the large directories, then delete or "
                "grow. The skill supplies the measurements and the manual deletion steps.",
            ),
            "verified_mitigation": (
                "Snapshot first, then free space manually. Support explicitly declined to "
                "delete customer data on the customer's behalf in the source case."
            ),
        },
        {
            "id": "inode-or-file-count-exhausted",
            "summary": (
                "The volume has free bytes but no free inodes (Linux) or an exhausted file "
                "count, so creating new files still fails."
            ),
            "confidence": "high",
            "case_refs": ("T-2E38E856",),
            "manual_checks": ("Run the df_i probe; on Linux compare IUsed with IFree."),
            "verified_mitigation": (
                "Manual: remove many small files, or recreate the volume with more inodes. "
                "NTFS has no inode counter - see references/hbr-backup-diagnosis__guest-commands.md for the Windows "
                "confidence wording."
            ),
        },
    ),
    CATEGORY_ECS_RELEASED: (
        {
            "id": "historical-alarm",
            "summary": (
                "The alarm is the historical record emitted at the moment the instance was "
                "released. Deleting the protection policy does not erase history, and the "
                "console list is not refreshed in real time."
            ),
            "confidence": "high",
            "case_refs": ("T-EF99E331",),
            "manual_checks": (
                "Confirm the instance really is gone (this skill does it with DescribeInstances), "
                "then check that the count of currently protected resources is zero.",
            ),
            "verified_mitigation": (
                "No new alarm is produced once no resource is protected. Removing the historical "
                "alarm entry is a console action with no customer-visible switch; if it must be "
                "cleared, ask the Cloud Backup service through a support ticket."
            ),
        },
    ),
    CATEGORY_RESTORE_SKIPPED: (
        {
            "id": "target-file-locked",
            "summary": (
                "The restore job reports success while the locked files are skipped: the "
                "database service (SQL Server in the source case) held the target files open, so "
                "they were never overwritten."
            ),
            "confidence": "high",
            "case_refs": ("T-BC432E90",),
            "manual_checks": (
                "Read the restore result details, including the tooltip behind the result icon, "
                "for a skipped-file count before concluding the restore worked.",
            ),
            "verified_mitigation": (
                "Manual SOP: stop the service holding the files, restore again in overwrite mode, "
                "restart the service, verify. Stopping a service is never automated by this skill."
            ),
        },
        {
            "id": "deleted-before-backup-point",
            "summary": (
                "The data disappeared before the oldest retained backup point, so no point "
                "contains it. Browsing the backup point content proves this in one step."
            ),
            "confidence": "high",
            "case_refs": ("T-BC432E90",),
            "manual_checks": (
                "In the console, use Browse and expand the point level by level to the exact "
                "path before attempting any restore.",
            ),
            "verified_mitigation": (
                "Data absent from every point is unrecoverable by backup; state this plainly "
                "rather than retrying restores."
            ),
        },
    ),
    CATEGORY_ROLE_OR_BILLING: (
        {
            "id": "arrears-blocks-service-role",
            "summary": (
                "A tiny overdue balance stops the console from auto-creating the service-linked "
                "role AliyunServiceRoleForHbrEcsBackup. Console functions then silently "
                "unavailable: jobs are not listed, not deletable. It is not a browser problem."
            ),
            "confidence": "high",
            "case_refs": ("T-9046C4E1",),
            "manual_checks": (
                "Check the expense centre balance first; this skill has no verified billing API.",
            ),
            "verified_mitigation": (
                "Top up, then retry the console operation. Manual."
            ),
        },
        {
            "id": "wrong-console-region",
            "summary": (
                "The resource exists but in another region, so the console shows nothing and the "
                "customer concludes the charge is phantom."
            ),
            "confidence": "high",
            "case_refs": ("T-8E2E6CDC",),
            "manual_checks": (
                "Switch the console region selector through every region the bill mentions, then "
                "re-list. The skill asks for an explicit region for every query for the same "
                "reason."
            ),
            "verified_mitigation": "Manual: select the correct region.",
        },
        {
            "id": "independent-billing-products",
            "summary": (
                "Snapshot, Cloud Backup (HBR), ApsaraDB RDS backup, pay-as-you-go data disks and "
                "burst-capable disks bill independently of a subscription ECS instance. "
                "Cloud Backup cannot be switched off as a whole - billing stops only by deleting "
                "the backup plans and backup vaults."
            ),
            "confidence": "high",
            "case_refs": ("T-5861B286", "T-8E2E6CDC", "T-C0611EEE", "T-95BF88EB"),
            "manual_checks": (
                "Use the skill's billing-attribution command to list the real instances, disks "
                "and snapshot links in a region, then map each line to references/hbr-backup-diagnosis__billing-map.md.",
            ),
            "verified_mitigation": (
                "Deleting a backup plan or vault permanently destroys the backed-up data. Manual "
                "only, with the risk warning, see references/hbr-backup-diagnosis__billing-map.md."
            ),
        },
    ),
    CATEGORY_BACKUP_TASK: (
        {
            "id": "generic-task-failure",
            "summary": (
                "A backup task failure whose text carries no recognised token. Internal task "
                "state is not exposed by any API verified for this tier."
            ),
            "confidence": "low",
            "case_refs": ("T-9046C4E1",),
            "manual_checks": (
                "Collect the full alarm text, the screenshot, the backup plan id and the request "
                "id shown in the console error, in that order.",
            ),
            "verified_mitigation": (
                "Escalate to the Cloud Backup service; in the source cases even the support "
                "engineer could not inspect task internals and forwarded the request id."
            ),
        },
    ),
}

# ---------------------------------------------------------------------------
# Side-effect-free guest commands. Exactly one command per key; the assembled
# string is re-checked for shell metacharacters before dispatch.
# ---------------------------------------------------------------------------
GUEST_TYPE_LINUX = "RunShellScript"
GUEST_TYPE_WINDOWS = "RunPowerShellScript"

# target_required commands validate --target before assembling the string.
GUEST_COMMANDS = {
    "df_h": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("df", "-h"),
        "target_required": False,
        "purpose": "Byte usage and free space of every mounted volume.",
        "reports": "Which volume is full, and how full.",
    },
    "df_i": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("df", "-i"),
        "target_required": False,
        "purpose": "inode usage per volume.",
        "reports": "Byte-free but inode-exhausted volumes.",
    },
    "findmnt": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("findmnt",),
        "target_required": False,
        "purpose": "Mount table: device, mount point, filesystem, options.",
        "reports": "Which device backs the path the backup job writes to.",
    },
    "du_top": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("du", "-x", "--max-depth=1"),
        "target_required": True,
        "purpose": "Size of each direct child of one directory, without crossing mounts.",
        "reports": "Candidate directories for manual cleanup.",
    },
    "lsof_deleted": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("lsof", "+L1"),
        "target_required": False,
        "purpose": "Files that are deleted but still held open by a process.",
        "reports": "Space that is logically freed but not yet returned to the volume.",
    },
    "stat": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("stat",),
        "target_required": True,
        "purpose": "Metadata, size and block count of one path.",
        "reports": "Whether a specific file is the space consumer.",
    },
    "ls_dir": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("ls", "-lh"),
        "target_required": True,
        "purpose": "Long listing of one directory.",
        "reports": "Individual large or unexpected files.",
    },
    "wc_lines": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("wc", "-l"),
        "target_required": True,
        "purpose": "Line count of one text file, e.g. a log.",
        "reports": "Log volume for a manual truncation decision.",
    },
    "get_volume": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-Volume",),
        "target_required": False,
        "purpose": "Health, size and free space of every volume.",
        "reports": "Which Windows volume is full.",
    },
    "get_psdrive": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-PSDrive",),
        "target_required": False,
        "purpose": "Used and free bytes per drive letter.",
        "reports": "Same reading in drive-letter terms.",
    },
    "get_childitem": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-ChildItem", "-Force"),
        "target_required": True,
        "purpose": "Listing of one directory, including hidden entries.",
        "reports": "Large or hidden consumers under one path.",
    },
    "fsutil_diskfree": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("fsutil", "volume", "diskfree"),
        "target_required": True,
        "purpose": "Reports total, free and available bytes for one volume, changing nothing.",
        "reports": "Precise free-space figures for the system volume.",
    },
}

# Rejected outright, whatever the caller claims. A whitelist match is necessary
# but not sufficient: this list is re-applied to the assembled string.
REJECTED_COMMAND_TOKENS = (
    "rm", "rmdir", "mv", "cp", "dd", "truncate", "mkfs", "format", "fdisk", "parted",
    "kill", "pkill", "killall", "systemctl", "service", "reboot", "shutdown", "halt",
    "poweroff", "init", "chattr", "chmod", "chown", "setfacl", "mount", "umount",
    "echo", "printf", "tee", "sed", "awk", "perl", "python", "sh", "bash", "powershell",
    "curl", "wget", "nc", "ssh", "scp", "yum", "apt", "apt-get", "rpm", "dpkg",
    "reg", "sc", "net", "wmic", "iisreset", "taskkill", "stop-service", "restart-service",
    "remove-item", "new-item", "set-content", "add-content", "clear-content", "move-item",
    "rename-item", "out-file", "invoke-expression", "start-process", "iex", "iwr",
)

SHELL_METACHARACTERS = (";", "|", "&", "$", "`", ">", "<", "*", "?", "(", ")", "{", "}", "\n", "\r")

# ---------------------------------------------------------------------------
# Documentation links. All taken from the requirements document for this tier:
# section 4.1 (help search hits) and 4.2 (links support engineers actually sent
# in the source tickets). Tracking query parameters were stripped.
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "configure_essential_edition":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "configure-automatic-file-backup-and-restoration-for-ecs-instances.md",
    "essential_edition_benefit":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "file-backup-essential-edition-benefit-description.md",
    "protection_scheme_comparison":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md",
    "ecs_backup_and_ha_architecture":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "ecs-data-backup-mechanism-and-high-availability-architecture.md",
    "disaster_recovery_solutions":
        "https://help.aliyun.com/zh/ecs/user-guide/disaster-recovery-solutions.md",
    "backup_local_disk_data":
        "https://help.aliyun.com/zh/ecs/user-guide/backup-local-disk-data.md",
    "extend_snapshot_retention":
        "https://help.aliyun.com/zh/ecs/user-guide/extend-the-snapshot-retention-period.md",
    "delete_snapshot_console":
        "https://help.aliyun.com/zh/ecs/user-guide/delete-a-snapshot-1.md",
    "cloud_assistant_status_and_exceptions":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "check-the-status-of-cloud-assistant-and-handle-exceptions",
    "reset_instance_password":
        "https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance",
    "windows_low_disk_space":
        "https://help.aliyun.com/zh/ecs/user-guide/handle-low-disk-space-on-windows-instances",
    "instance_configuration_change":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-of-instance-configuration-changes",
    "create_snapshot": "https://help.aliyun.com/document_detail/25455.html",
    "snapshot_billing": "https://help.aliyun.com/document_detail/56159.html",
    "snapshot_billing_overview": "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "delete_snapshot": "https://help.aliyun.com/document_detail/128131.html",
    "hbr_billing_methods":
        "https://help.aliyun.com/zh/cloud-backup/product-overview/billing-methods-and-billable-items",
    "block_storage_billing": "https://help.aliyun.com/zh/ecs/block-storage-devices",
    "hbr_stop_billing": "https://help.aliyun.com/document_detail/308385.html",
    "essential_edition_billing_basis":
        "https://help.aliyun.com/zh/cloud-backup/support/"
        "what-is-the-billing-basis-for-ecs-file-backup-essential-edition",
    "hbr_console": "https://hbr.console.aliyun.com/",
    "snapshot_console": "https://ecs.console.aliyun.com/snapshot/region/{region_id}",
    "file_backup_console": "https://ecs.console.aliyun.com/fileBackup/region/{region_id}",
    "instance_backup_console":
        "https://ecs.console.aliyun.com/server/{instance_id}/backup?regionId={region_id}",
    "recharge_entry": "https://billing-cost.console.aliyun.com/fortune/fund-management/recharge",
    "database_resource_plan":
        "https://common-buy.aliyun.com/?commodityCode=hbr_resourceplan_dp_cn",
    "delete_backup_plan_api": "https://next.api.aliyun.com/api/hbr/2017-09-08/DeleteBackupPlan",
}

# Referenced by an alarm message as a document title only. No URL was supplied in
# the source material, so it is never fabricated - see references/hbr-backup-diagnosis__console-paths.md.
DOC_TITLES_WITHOUT_URL = (
    "Configure the RAM permissions used by the Cloud Assistant agent",
)

# ---------------------------------------------------------------------------
# Hand-off targets for adjacent symptom areas.
# ---------------------------------------------------------------------------
HANDOFF_RULES = (
    {
        "when": "A disk was resized but the partition or filesystem did not grow.",
        "target": "area:disk-expand-diagnosis",
    },
    {
        "when": "The instance cannot start, is stuck in an intermediate state, or is stopped "
                "for an overdue balance.",
        "target": "area:instance-state-diagnosis",
    },
    {
        "when": "The complaint is slow disk IO or throughput below the instance specification.",
        "target": "area:resource-bottleneck",
    },
    {
        "when": "Enabling, configuring or browsing the File Backup Essential Edition product "
                "itself, with no failure to diagnose.",
        "target": "alibabacloud-cloudbackup-ecs-file-backup-essential-edition",
    },
    {
        "when": "A specific bill line must be explained to the cent, refunded, unsubscribed or "
                "covered by a resource plan purchase.",
        "target": "manual - the expense centre and a billing specialist",
    },
    {
        "when": "A Cloud Backup internal task or restore error that no informational ECS query "
                "explains.",
        "target": "manual - a support ticket to the Cloud Backup service",
    },
)
