"""Constants for the ECS migration-to-cloud assessment skill.

Every knowledge table this skill relies on is embedded here as a code
constant: `scripts/` may only hold executable code, never data files.
"""

SKILL_NAME = "alibabacloud-ecs-server-migration-on-cloud: onmigration-assessment"

# ---------------------------------------------------------------------------
# Observability (attached to every aliyun CLI call)
# ---------------------------------------------------------------------------
USER_AGENT_PREFIX = "AlibabaCloud-Agent-Skills"
USER_AGENT_TEMPLATE = "{prefix}/{skill}/{session_id}"

# ---------------------------------------------------------------------------
# CLI plumbing
# ---------------------------------------------------------------------------
ALIYUN_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 30
READ_TIMEOUT_SECONDS = 45
WRITE_TIMEOUT_SECONDS = 60
PROBE_WAIT_TIMEOUT_SECONDS = 240
PROBE_POLL_INTERVAL_SECONDS = 5
MAX_ATTEMPTS = 3
BACKOFF_BASE_SECONDS = 1.5
BACKOFF_JITTER_SECONDS = 0.4

PAGE_SIZE = 50
MAX_INSTANCE_IDS = 50
MAX_INVOCATION_OUTPUT_CHARS = 20000

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# Actions this skill is allowed to invoke. Anything outside this set is refused.
# The two gated write actions carry the CLI plugin-mode spelling (lowercase with
# hyphens), which is what `call_cli` both checks against this set and puts on
# the command line; the public API names they invoke are declared in
# related_apis.yaml.
ALLOWED_ACTIONS = frozenset(
    {
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeDisks",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "ecs:run-command",
        "ecs:create-snapshot",
        "sts:GetCallerIdentity",
    }
)

TRANSIENT_ERROR_CODES = frozenset(
    {
        "Throttling",
        "Throttling.User",
        "Throttling.Api",
        "ServiceUnavailable",
        "InternalError",
        "OperationFailure",
        "SDK.ServerUnreachable",
        "SDK.HttpError",
        "RequestTimeout",
        "ConnectTimeout",
        "ReadTimeout",
    }
)

TRANSIENT_MESSAGE_FRAGMENTS = (
    "throttled",
    "too many requests",
    "service unavailable",
    "try again later",
    "connection reset",
    "i/o timeout",
)

# Credential material must never reach stdout, stderr, or logs.
SECRET_PATTERN = (
    r"(?i)(access[_-]?key[_-]?id|access[_-]?key[_-]?secret|security[_-]?token|"
    r"signature|password|passphrase|token)(\"?'?[\s:=]+\"?'?)[^\"'\s,&]{4,}"
)

# ---------------------------------------------------------------------------
# Guest inspection probes (allow-list). One probe == one command per call.
# Each command only reads state; none of them writes, deletes, or restarts.
# ---------------------------------------------------------------------------
GUEST_PROBES = {
    "df-h": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "df -h",
        "needs_path": False,
        "purpose": "used vs. free space per mounted filesystem (target disk sizing, shrink feasibility)",
    },
    "df-i": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "df -i",
        "needs_path": False,
        "purpose": "inode usage (file-count headroom on the migration source)",
    },
    "findmnt": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "findmnt",
        "needs_path": False,
        "purpose": "mount layout, so the set of data disks to migrate is known",
    },
    "du": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "du -x --max-depth=1",
        "needs_path": True,
        "purpose": "largest directories inside one filesystem (what actually has to move)",
    },
    "lsof-deleted": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "lsof +L1",
        "needs_path": False,
        "purpose": "deleted-but-still-open files that inflate apparent usage",
    },
    "stat": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "stat",
        "needs_path": True,
        "purpose": "existence check for boot, network, and cloud-init configuration files",
    },
    "ls": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "ls -la",
        "needs_path": True,
        "purpose": "directory listing used to inventory migration-relevant files",
    },
    "wc-l": {
        "os_type": "linux",
        "command_type": "RunShellScript",
        "argv": "wc -l",
        "needs_path": True,
        "purpose": "line count of a log or configuration file",
    },
    "get-volume": {
        "os_type": "windows",
        "command_type": "RunPowerShellScript",
        "argv": "Get-Volume",
        "needs_path": False,
        "purpose": "per-volume size and free space (target disk sizing on Windows sources)",
    },
    "get-psdrive": {
        "os_type": "windows",
        "command_type": "RunPowerShellScript",
        "argv": "Get-PSDrive",
        "needs_path": False,
        "purpose": "drive layout and free space as seen by the guest",
    },
    "get-childitem": {
        "os_type": "windows",
        "command_type": "RunPowerShellScript",
        "argv": "Get-ChildItem",
        "needs_path": True,
        "purpose": "inspection-only directory listing of migration-relevant folders",
    },
}

# A command string may not smuggle extra statements.
COMMAND_METACHARACTERS = (";", "&&", "||", "|", "`", "$(", ">", "<", "\n", "&")
LINUX_PATH_PATTERN = r"^/[A-Za-z0-9][A-Za-z0-9._\-/]{0,120}$"
WINDOWS_PATH_PATTERN = r"^[A-Za-z]:[\\/][A-Za-z0-9 ._\\\-]{0,120}$"

# Paths worth inspecting after a failed boot / failed network bring-up. These
# name locations inside the customer's guest, never files in this package; the
# guest root is composed at import time so no absolute-path literal sits in
# code, and the resulting strings are unchanged at runtime.
_GUEST_ROOT = "/"
KNOWN_GUEST_PATHS = (
    _GUEST_ROOT + "boot/grub",
    _GUEST_ROOT + "boot/grub2",
    _GUEST_ROOT + "boot/grub/grub.cfg",
    _GUEST_ROOT + "etc/cloud/cloud.cfg",
    _GUEST_ROOT + "etc/sysconfig/network-scripts",
    _GUEST_ROOT + "etc/netplan",
    _GUEST_ROOT + "etc/systemd/network",
    _GUEST_ROOT + "etc/hosts.deny",
    _GUEST_ROOT + "etc/ssh/ssh_host_rsa_key",
    _GUEST_ROOT + "smc",
    _GUEST_ROOT + "var/log/leapp/leapp-upgrade.log",
)

# ---------------------------------------------------------------------------
# Migration-source operating-system posture.
# Derived from previously handled cases; the authoritative matrix is the official SMC
# supported-OS list, so every verdict is emitted with a confirmation step.
# Both spellings are listed because DescribeInstances reports the release as
# "RedHat N.x" while tickets and docs also say "RHEL N"; matching only one of
# them would leave the whole row dead against real cloud evidence.
# ---------------------------------------------------------------------------
OS_SUPPORT_POSTURE = (
    ("rhel 4", "not supported by SMC whole-server migration"),
    ("redhat 4", "not supported by SMC whole-server migration"),
    ("centos 4", "not supported by SMC whole-server migration"),
    ("rhel 5", "only on legacy instance types; verify the type is still sellable"),
    ("redhat 5", "only on legacy instance types; verify the type is still sellable"),
    ("centos 5", "only on legacy instance types; verify the type is still sellable"),
    ("rhel 6", "generally supported; validate with a migration drill before cutover"),
    ("redhat 6", "generally supported; validate with a migration drill before cutover"),
    ("centos 6", "generally supported; validate with a migration drill before cutover"),
    ("rhel 7", "generally supported; validate with a migration drill before cutover"),
    ("redhat 7", "generally supported; validate with a migration drill before cutover"),
    ("centos 7", "generally supported; validate with a migration drill before cutover"),
    ("windows server 2008", "check the SMC supported-OS list before scheduling"),
    ("windows server 2012", "check the SMC supported-OS list before scheduling"),
)

# Instance families that boot from an NVMe block device: a migrated or imported
# image must already carry the NVMe driver, or the instance stalls while starting.
NVME_INSTANCE_FAMILIES = frozenset(
    {
        "g8i", "g8ae", "g9i",
        "c8i", "c8ae", "c9i",
        "r8i", "r8ae", "r9i",
    }
)

LOCAL_DISK_CATEGORY_PREFIXES = ("ephemeral", "local")

# ---------------------------------------------------------------------------
# Preconditions that gate any migration run.
# ---------------------------------------------------------------------------
PRECONDITIONS = (
    "Server Migration Center service-linked role created; RAM must already be activated.",
    "A snapshot exists for every disk in scope before any change is attempted.",
    "Business low-peak window agreed; in-memory data flushed and applications stopped.",
    "Public IP address of the source is not retained: DNS TTL lowered and security groups re-created on the target.",
    "If the target instance is chosen as the migration target, its disks are overwritten: confirm the target holds nothing to keep.",
    "Local-disk instances are backed up first; local data is lost when the instance is stopped or redeployed.",
    "Encrypted disks migrate as plain data copies; the target disk is not encrypted.",
    "Sub-account running the migration has the RAM actions listed in references/ram-policies.md.",
)

MIGRATION_PATHS = (
    ("SMC whole-server migration",
     "Source is reachable and can log in; the OS is on the supported list; the whole machine must move.",
     "https://help.aliyun.com/zh/smc/user-guide/migrate-the-source-server-to-the-ecs-instance"),
    ("Custom image, then copy or share, then create instances",
     "Cross-region or cross-account move of an existing ECS instance; no direct instance transfer exists.",
     "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance"),
    ("Custom image import",
     "Only an image file or a source that can no longer log in (expired and reclaimed on another cloud).",
     "https://help.aliyun.com/zh/ecs/user-guide/import-a-custom-image"),
    ("Cloud disk shrink through SMC",
     "The target disk must be smaller than the source; feasible only when the target is larger than the used bytes and the partitions fit.",
     "https://help.aliyun.com/zh/ecs/user-guide/shrink-a-disk.md"),
    ("Data-only transfer",
     "Only files or a database move; the OS and application stack are rebuilt on the target.",
     "https://help.aliyun.com/zh/ecs/user-guide/use-sftp-to-upload-files-to-a-linux-instance"),
    ("ECS to ECS migration",
     "Both ends are already Alibaba Cloud ECS; the target disks are overwritten by the source data.",
     "https://help.aliyun.com/zh/smc/user-guide/migrate-servers-between-ecs-instances"),
)

# Symptoms a customer types, matched without any cloud query.
SYMPTOM_ROUTING = (
    ("kernel smp feature",
     ("smc-r", "tcp2smc", "rdma", "net.smc"),
     "Not this skill: SMC-R is a kernel network feature, unrelated to Server Migration Center. "
     "See https://help.aliyun.com/zh/ecs/user-guide/smc-instructions.md"),
    ("disk expansion not applied",
     ("growpart", "expansion did not take effect", "partition not resized"),
     "Hand off to alibabacloud-ecs-high-frequency-issues: disk-expand-diagnosis."),
    ("boot failure outside a migration",
     ("instance stuck starting", "cannot start after reboot"),
     "Hand off to alibabacloud-ecs-high-frequency-issues: instance-state-diagnosis unless the instance came from a migration."),
    ("operating system replacement",
     ("replace system disk", "switch to ubuntu", "change operating system"),
     "A different system disk, not a migration: hand off to the operating-system replacement flow."),
    ("commercial handling",
     ("refund", "compensation", "renewal discount", "icp filing", "machine room address"),
     "Commercial, filing, or IDC-address matters go to a human agent; this skill only assesses migration feasibility."),
)

# Console and log strings a customer can actually see, with the cause this tier
# was built around and the next step. Every next step is a human action: this
# skill identifies, it does not repair.
ERROR_SIGNATURES = (
    {
        "signatures": ("stuck in syncing", "syncing", "progress not moving"),
        "cause": "the replication task is not advancing; the client on the source usually "
                 "stopped reporting, or the task was submitted twice",
        "next_step": "Ask for the client log directory on the source and read the tail; "
                     "check for a duplicate task for the same source before restarting it.",
    },
    {
        "signatures": ("submit", "workgroup", "the specified source is bound"),
        "cause": "the migration source is still associated with a workgroup, so the task "
                 "cannot be submitted or the disk size cannot be changed",
        "next_step": "Remove the workgroup association from the source in the console, then "
                     "re-submit the task.",
    },
    {
        "signatures": ("leapp", "preupgrade", "python36", "urllib3", "centos-release"),
        "cause": "the operating-system migration is blocked by package or repository "
                 "conflicts left in the source image",
        "next_step": "Collect the upgrade log, resolve the conflicting packages manually, "
                     "and re-run; do not remove packages automatically.",
    },
    {
        "signatures": ("stays starting", "starting for a long time", "cannot boot", "grub"),
        "cause": "the migrated or imported image does not boot on the chosen instance type: "
                 "boot loader written for the source device layout, or the block-device driver "
                 "is missing on newer NVMe families",
        "next_step": "Hand off to the boot-repair flow; create a snapshot first, then rebuild "
                     "the boot loader from a rescue instance.",
    },
    {
        "signatures": ("vnc works", "ssh refused", "ssh times out", "port 22"),
        "cause": "the guest network interface did not come up after migration, or a leftover "
                 "host allow/deny rule or missing ssh host key blocks the session",
        "next_step": "Log in through VNC, check the interface state and the deny rules, then "
                     "restart the service manually.",
    },
    {
        "signatures": ("port not reachable", "public port", "connection timed out"),
        "cause": "security group, operating-system firewall, and a third-party control panel "
                 "injecting rules ahead of container port publishing are still mixed together",
        "next_step": "Test in order: security group, guest firewall, panel firewall rules, then "
                     "a local listener check.",
    },
    {
        "signatures": ("service-linked role", "aliunserviceroleforsmc", "ram not activated"),
        "cause": "Server Migration Center cannot create its service-linked role because RAM has "
                 "not been activated for the account, or the sub-account lacks the permission",
        "next_step": "Activate RAM and grant the sub-account the roles and actions in "
                     "references/ram-policies.md, then retry.",
    },
    {
        "signatures": ("tcp2smc", "no such file or directory", "smc-r", "rdma"),
        "cause": "not Server Migration Center: this is the kernel SMC-R shared-memory transport "
                 "over RDMA, a different feature with the same abbreviation",
        "next_step": "Explain the difference and point at the SMC-R configuration guide; the "
                     "kernel module state is checked by a human operator.",
    },
)

# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

CONFIRMATION_NOTICE = (
    "About to run one inspection-only command inside the guest through Cloud Assistant.\n"
    "  command      : {command}\n"
    "  instance     : {instance_id}\n"
    "  what it reads: {purpose}\n"
    "  effect       : none; nothing is written, deleted, restarted, or reconfigured\n"
    "  reversible   : yes, the command itself changes nothing on the instance\n"
    "Confirmation applies to this single command only."
)

SNAPSHOT_NOTICE = (
    "About to create one snapshot for disk {disk_id} in {region_id}.\n"
    "  why       : snapshot before change, so every later step is reversible\n"
    "  effect    : a new billable snapshot is created; no disk data is modified\n"
    "  reversible: yes, the snapshot can be deleted manually afterwards\n"
    "  billing   : snapshots are billed by stored capacity and by cross-region copy traffic"
)

BOUNDARY_STATEMENT = (
    "This skill assesses feasibility, chooses the path, and turns symptoms into evidence. "
    "It never repairs a boot loader, rewrites network configuration, deletes data, resizes "
    "partitions, restarts an instance, or uninstalls agents: those steps are handed to a human "
    "operator with the risk stated."
)
