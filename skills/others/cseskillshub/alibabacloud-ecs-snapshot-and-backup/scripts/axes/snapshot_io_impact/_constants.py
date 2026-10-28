"""Constants for the alibabacloud-ecs-snapshot-io-impact skill.

Every piece of reference data this skill needs (API metadata, the guest
inspection whitelist, thresholds, hand-off targets, knowledge tables) lives
here as an in-script constant. Standalone data files are not allowed under
``scripts/``.

Permission model of this tier (three classes, decided by the confirmed
requirements document):
  Class 1  automatic cloud inspection  - Describe/Get calls, nothing changes.
  Class 2  one inspection command inside the guest, delivered through the
           Cloud Assistant channel only after an explicit per-command
           customer confirmation (the delivery API itself is state-changing).
  Class 3  one low-risk reversible write (a restore-point snapshot), only
           after an explicit per-call customer confirmation.
Everything outside the tables below is refused by design.
"""

SKILL_NAME = "alibabacloud-ecs-snapshot-io-impact"

# --- Observability -----------------------------------------------------------
# Attached to every single CLI invocation so one diagnosis run is traceable
# end to end. session-id is a 32-char lowercase hex string (uuid.uuid4().hex),
# generated once per run and shared by every call of that run.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0

# RPC-style products keep the PascalCase action name on the command line;
# plugin-style products use the lowercase-hyphenated subcommand form.
PRODUCT_ECS = "ecs"
PRODUCT_CMS = "cms"
PRODUCT_STS = "sts"
ECS_API_VERSION = "2014-05-26"
CMS_API_VERSION = "2019-01-01"
STS_API_VERSION = "2015-04-01"
PLUGIN_MODE_COMMANDS = {
    ("sts", "GetCallerIdentity"): "GetCallerIdentity",
}

# --- Action registry (complete callable surface of this skill) ---------------
ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_DISKS = "DescribeDisks"
ACTION_DESCRIBE_SNAPSHOTS = "DescribeSnapshots"
ACTION_DESCRIBE_INSTANCE_TYPES = "DescribeInstanceTypes"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_DESCRIBE_METRIC_LAST = "DescribeMetricLast"
ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"
# Confirmation-gated actions (Class 2 / Class 3). The scripts refuse both
# unless the customer confirmation flag repeats the exact target id.
ACTION_GUEST_EXEC = "RunCommand"
ACTION_SNAPSHOT_WRITE = "CreateSnapshot"

# Automatic inspection surface. Anything outside the union of these two
# tuples must never be called by this skill.
CLOUD_READ_ACTIONS = (
    ("ecs", ACTION_DESCRIBE_INSTANCES),
    ("ecs", ACTION_DESCRIBE_DISKS),
    ("ecs", ACTION_DESCRIBE_SNAPSHOTS),
    ("ecs", ACTION_DESCRIBE_INSTANCE_TYPES),
    ("ecs", ACTION_DESCRIBE_INVOCATIONS),
    ("cms", ACTION_DESCRIBE_METRIC_LAST),
    ("sts", ACTION_GET_CALLER_IDENTITY),
)
GATED_ACTIONS = (
    ("ecs", ACTION_GUEST_EXEC),
    ("ecs", ACTION_SNAPSHOT_WRITE),
)

# --- Paging ------------------------------------------------------------------
PAGE_SIZE = 50
MAX_PAGES = 10

# --- CloudMonitor readings ---------------------------------------------------
# Namespace and metric names below are the working values used by sibling ECS
# diagnosis skills of this batch; the values are echoed in every report so a
# reviewer can re-check them on the CloudMonitor console.
CMS_NAMESPACE_ECS = "acs_ecs_dashboard"
CMS_METRICS = (
    ("DiskReadBPS", "disk read throughput, bytes per second", "Average"),
    ("DiskWriteBPS", "disk write throughput, bytes per second", "Average"),
    ("DiskReadIOPS", "disk read operations per second", "Average"),
    ("DiskWriteIOPS", "disk write operations per second", "Average"),
)
CMS_PERIOD_SECONDS = "60"
CMS_LENGTH = "1440"

# --- Diagnosis windows -------------------------------------------------------
# Default symptom window when the customer gives no timestamps: the last N
# hours, always declared as auto-filled in the report.
DEFAULT_SYMPTOM_WINDOW_HOURS = 24
# Snapshots older than this many days are out of the correlation scan.
SNAPSHOT_SCAN_DAYS = 7
# Internal heuristic ratio for "IO running close to the published ceiling".
# It is a report-time comparison aid, NOT a service commitment and must never
# be quoted to the customer as an official limit.
NEAR_CEILING_RATIO = 0.8

# --- Snapshot task status tokens ---------------------------------------------
SNAPSHOT_STATUS_PROGRESSING = "progressing"
SNAPSHOT_STATUS_ACCOMPLISHED = "accomplished"
SNAPSHOT_STATUS_FAILED = "failed"
SNAPSHOT_ACTIVE_STATUSES = (SNAPSHOT_STATUS_PROGRESSING,)

# --- Root-cause taxonomy (decision tree of the tier) --------------------------
ROOT_CAUSE_TAXONOMY = (
    ("B1", "Symptom window overlaps one or more snapshot tasks on the "
           "instance's disks; IO readings are at or near the available "
           "ceiling: snapshot window is the dominant amplifier."),
    ("B2", "Symptom window overlaps snapshot tasks but IO readings stay "
           "well below the ceiling: correlation exists, causation not "
           "proven; guest-side latency evidence is still missing."),
    ("B3", "No snapshot task overlaps the symptom window: the slowdown is "
           "not attributable to snapshot activity; route to the disk "
           "performance or capacity tiers as the readings indicate."),
    ("B4", "Evidence incomplete (a required read failed or returned "
           "nothing): report DEGRADED, name the gap, ask the customer for "
           "the reading instead of concluding."),
)

# --- Verdict tokens (machine-readable conclusion of `diagnose`) --------------
VERDICT_SNAPSHOT_AMPLIFIER = "SNAPSHOT_WINDOW_AMPLIFIER"
VERDICT_SNAPSHOT_CORRELATED = "SNAPSHOT_WINDOW_CORRELATED_HEADROOM_UNCLEAR"
VERDICT_NOT_SNAPSHOT = "NOT_ATTRIBUTABLE_TO_SNAPSHOT"
VERDICT_EVIDENCE_INSUFFICIENT = "EVIDENCE_INSUFFICIENT"

# --- Disk categories (qualitative context only, no numeric promises) --------
# The IOPS/throughput ceiling per category is published per region and class
# on the block-storage performance page; this package intentionally ships no
# numeric table so no unverified figure can reach a customer report.
CATEGORY_PROFILE = {
    "cloud": "Previous-generation cloud disk; lowest performance class.",
    "cloud_efficiency": "Efficient cloud disk; throughput scales weakly with size.",
    "cloud_ssd": "SSD cloud disk; balanced general-purpose class.",
    "cloud_essd": "Enhanced SSD; performance tier is tied to size and the "
                  "provisioned performance level.",
    "cloud_auto": "Auto cloud disk; performance provisioned independently of capacity.",
    "cloud_regional_disk_auto": "Regional auto cloud disk; replicated within the region.",
    "local_ssd": "Local SSD on the host; not persistent, snapshot semantics differ.",
    "local_hdd_pro": "Local HDD on the host; not persistent, snapshot semantics differ.",
    "ephemeral": "Ephemeral host disk; never a snapshot target for durable data.",
    "ephemeral_ssd": "Ephemeral host SSD; never a snapshot target for durable data.",
}

# --- In-guest inspection commands (Class 2 callable set) ---------------------
# This is the complete callable set, mirrored from the batch low-risk
# operation list. Honest tier note kept in sync with
# references/guest-inspection-commands.md: every command below reports
# capacity or file-handle state. None of them measures block-device latency,
# so they corroborate context (a nearly full volume slows writes further) and
# never substitute for a monitoring reading.
GUEST_COMMANDS = {
    "disk-usage": {
        "os": "linux",
        "command": "df -h",
        "needs_path": False,
        "purpose": "Capacity context: how full each file system is right now.",
    },
    "inode-usage": {
        "os": "linux",
        "command": "df -i",
        "needs_path": False,
        "purpose": "Capacity context: inode pressure that also slows writes.",
    },
    "directory-volume": {
        "os": "linux",
        "command": "du -x --max-depth=1",
        "needs_path": True,
        "purpose": "Capacity context: how much one directory level holds.",
    },
    "deleted-open-files": {
        "os": "linux",
        "command": "lsof +L1",
        "needs_path": False,
        "purpose": "File-handle context: space held by deleted-but-open files.",
    },
    "mount-map": {
        "os": "linux",
        "command": "findmnt",
        "needs_path": False,
        "purpose": "Maps a device name to its mount point for the disk under review.",
    },
    "path-stat": {
        "os": "linux",
        "command": "stat",
        "needs_path": True,
        "purpose": "Reads one path's metadata without touching its contents.",
    },
    "directory-listing": {
        "os": "linux",
        "command": "ls -l",
        "needs_path": True,
        "purpose": "Lists one directory without following or modifying anything.",
    },
    "line-count": {
        "os": "linux",
        "command": "wc -l",
        "needs_path": True,
        "purpose": "Counts lines of one file, e.g. an application log.",
    },
}

# Tools that answer the latency question directly but are NOT on the callable
# whitelist for this batch: the agent must refuse to dispatch them and instead
# guide the customer to run them and paste the output.
REFUSED_GUEST_TOOLS = (
    "iostat", "iotop", "pidstat", "sar", "vmstat", "dmesg", "journalctl",
    "fio", "dd", "blktrace", "perf", "atop",
)

# Commands carrying side effects: refused outright, never dispatched, never
# offered as an executable line (manual guidance only where legal).
REJECTED_COMMAND_TOKENS = (
    "rm", "mv", "cp", "dd", "truncate", "mkfs", "fsck", "fdisk", "parted",
    "mount", "umount", "kill", "pkill", "reboot", "shutdown", "systemctl",
    "service", "sync", "echo", "cat >", "curl", "wget", "chmod", "chown",
)

LINUX_PATH_PATTERN = r"^/[A-Za-z0-9._+@:,%-]{0,255}$"
SHELL_METACHARACTERS = (";", "&", "|", ">", "<", "`", "$", "(", ")", "\n", "\\")

# Cloud Assistant delivery settings for Class 2.
RUN_COMMAND_LINUX_TYPE = "RunShellScript"
RUN_COMMAND_TIMEOUT_SECONDS = 60
INVOCATION_POLL_ATTEMPTS = 6
INVOCATION_POLL_INTERVAL_SECONDS = 5

# Windows guests are out of scope for the Class 2 channel in this release
# (the confirmed requirements record zero Windows evidence for this tier);
# guidance for Windows stays manual.
WINDOWS_GUEST_CHANNEL_ENABLED = False

# --- Input validation ----------------------------------------------------------
INSTANCE_ID_PATTERN = r"^i-[A-Za-z0-9]{4,40}$"
DISK_ID_PATTERN = r"^d-[A-Za-z0-9]{4,40}$"
SNAPSHOT_ID_PATTERN = r"^s-[A-Za-z0-9]{4,40}$"
REGION_ID_PATTERN = r"^[A-Za-z]{2}-[A-Za-z0-9-]{2,24}$"
ISO_UTC_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?(Z|[+-]\d{2}:\d{2})?$"

# --- Hand-off targets (out-of-scope symptoms) --------------------------------
# Kept identical with references/handoffs.md. The snapshot failure and
# snapshot fee axes intentionally point at the two sibling snapshot tiers.
HANDOFFS = (
    ("disk full, inode exhaustion, cleanup or space release",
     "alibabacloud-ecs-disk-capacity-cleanup"),
    ("slow disk I/O with no snapshot overlap, performance below spec",
     "alibabacloud-ecs-disk-io-diagnosis"),
    ("a resize that never took effect, partition or file system growth",
     "alibabacloud-ecs-disk-expand-diagnosis"),
    ("instance stuck starting, stopping or rebooting",
     "alibabacloud-ecs-instance-state-diagnosis"),
    ("snapshot creation failure, stuck progress, policy configuration",
     "alibabacloud-ecs-snapshot-policy-check"),
    ("snapshot fees, quota, deletion or cleanup",
     "alibabacloud-ecs-snapshot-billing-cleanup"),
    ("restoring a disk or rolling the system back to a snapshot",
     "alibabacloud-ecs-disaster-recovery-snapshot"),
)

# --- Console entry points referenced by manual guidance -----------------------
CONSOLE_ENTRIES = {
    "snapshot_list": "ECS console > Storage & Images > Snapshots (select the region first)",
    "auto_snapshot_policy": "ECS console > Storage & Images > Auto Snapshot Policies (select the region first)",
    "monitoring": "ECS console > Instance detail > Monitoring tab (disk read/write BPS and IOPS charts)",
    "cloud_disk_list": "ECS console > Storage & Images > Cloud Disks (select the region first)",
}

# --- Official documentation (verified URLs from the confirmed requirements) ---
# Only these two URLs may be cited by the report. The confirmed requirements
# record that no official snapshot-performance or snapshot-throttling topic
# was verified for this tier, so any numeric limit statement is withheld.
OFFICIAL_DOCS = (
    ("What is Elastic Compute Service (product overview)",
     "https://help.aliyun.com/zh/ecs/user-guide/what-is-ecs.md"),
    ("ECS data protection scheme selection (snapshot vs file backup)",
     "https://help.aliyun.com/zh/ecs/user-guide/select-the-appropriate-ecs-data-protection-scheme-snapshot-and-file-backup-essential-edition.md"),
)

# --- Failure vocabulary --------------------------------------------------------
# Permission failures are reported with these literals only.
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_RESOURCE_NOT_FOUND = "InvalidResourceIdNotFound"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"
CODE_CONFIRMATION_REQUIRED = "ConfirmationRequired"
CODE_COMMAND_REFUSED = "CommandRefused"

STATUS_OK = "STATUS: OK"
STATUS_DEGRADED = "STATUS: DEGRADED"
STATUS_FAIL = "STATUS: FAIL"

# Transient conditions worth retrying.
RETRYABLE_MARKERS = (
    "throttling",
    "throttlingexception",
    "systembusy",
    "serviceunavailable",
    "internalerror",
    "internal failure",
    "temporar",
    "connection reset",
    "connection refused",
    "timed out",
    "timeout",
    "500",
    "502",
    "503",
    "429",
)

# Conditions that must never be retried.
NON_RETRYABLE_MARKERS = (
    "noparameter",
    "missingparameter",
    "invalidparameter",
    "signaturedoesnotmatch",
    "invalidaccesskeyid",
    "no permission",
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "notfound",
    "invalidinstance",
    "invaliddisk",
    "clientnotrunning",
    "clientnotnetwork",
)

# Credential-chain failures, classified apart from a generic API error: the
# recovery is to refresh the local CLI configuration, not to retry or widen a
# permission.
CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid",
    "signaturedoesnotmatch",
    "invalidsecuritytoken",
    "securitytokenexpired",
    "invalidcredential",
)

# Credential material that must never reach the terminal or a log line.
SENSITIVE_KEY_PATTERNS = (
    r"accesskeyid",
    r"access[-_]key[-_]id",
    r"accesskeysecret",
    r"access[-_]key[-_]secret",
    r"securitytoken",
    r"security[-_]token",
    r"bearer token",
    r"signature",
    r"password",
    r"passwd",
    r"private key",
)
MASKED_VALUE = "***"
