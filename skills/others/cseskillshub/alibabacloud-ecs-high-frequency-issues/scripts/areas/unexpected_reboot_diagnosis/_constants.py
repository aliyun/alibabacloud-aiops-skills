"""Frozen constants for the unexpected-reboot diagnosis skill.

Everything the entry script knows without touching the network lives here:
the guest command whitelist, the system-event taxonomy, the CloudMonitor
metric set, thresholds, handoff targets and official documentation links.

All API facts recorded in this module were verified in development against
the aliyun CLI metadata (action existence and parameter names) and against
live read-only calls (response shapes, metric names, event type enum).
Nothing here is estimated or invented.

SECURITY: no credential of any kind is stored or read from this module.
"""

SKILL_NAME = "alibabacloud-ecs-unexpected-reboot-diagnosis"

# ---------------------------------------------------------------------------
# Products and API versions (verified via aliyun CLI metadata)
# ---------------------------------------------------------------------------
ECS_PRODUCT = "ecs"
ECS_VERSION = "2014-05-26"
CMS_PRODUCT = "cms"
CMS_VERSION = "2019-01-01"
STS_PRODUCT = "sts"

# CloudMonitor namespace for ECS metrics (verified live).
CMS_NAMESPACE_ECS = "acs_ecs_dashboard"

# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------
CLI_TIMEOUT_SECONDS = 30          # per query call
CLI_TIMEOUT_WRITE_SECONDS = 90    # gated write/execution calls
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 2
SESSION_ID_LENGTH = 32

USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

# Transient failure codes worth retrying (verified envelope shapes).
RETRYABLE_ERROR_CODES = (
    "Throttling",
    "Throttling.User",
    "Throttling.Api",
    "ServiceUnavailable",
    "InternalError",
    "SDK.HttpError",
)

# Authorization-failure codes. Reported as NoPermission / ImplicitDeny.
AUTH_DENIED_CODES = ("NoPermission", "ImplicitDeny", "AccessDenied")

# ---------------------------------------------------------------------------
# Polling budgets for a dispatched guest command
# ---------------------------------------------------------------------------
INVOCATION_POLL_INTERVAL_SECONDS = 3
INVOCATION_POLL_BUDGET_SECONDS = 60
GUEST_COMMAND_TIMEOUT_SECONDS = 30   # Timeout parameter sent to RunCommand

# Terminal Cloud Assistant invocation statuses (verified live values).
INVOCATION_TERMINAL_STATUSES = (
    "Success", "Failed", "Error", "Timeout", "Stopped",
    "PartialFailed", "Invalid", "Aborted",
)

# ---------------------------------------------------------------------------
# Guest command whitelist (batch low-risk list, section B, tier subset)
# ---------------------------------------------------------------------------
# Exact single-token commands, keyed by the command string the operator must
# pass. Linux forms go out as shell script, Windows forms as PowerShell.
AUTO_GUEST_COMMANDS_LINUX = (
    "df -h",
    "df -i",
    "findmnt",
    "lsof +L1",
)

AUTO_GUEST_COMMANDS_WINDOWS = (
    "Get-Volume",
    "Get-PSDrive",
    "fsutil fsinfo drives",
)

# Families that accept ONE additional argument (a plain path or volume),
# appended after strict validation. The command token itself must match.
AUTO_GUEST_COMMAND_FAMILIES = {
    "du": {
        "os": "linux",
        "prefix": "du -x -h --max-depth=1",
        "arg_kind": "path",
    },
    "ls": {
        "os": "linux",
        "prefix": "ls -la",
        "arg_kind": "path",
    },
    "stat": {
        "os": "linux",
        "prefix": "stat",
        "arg_kind": "path",
    },
    "wc": {
        "os": "linux",
        "prefix": "wc -l",
        "arg_kind": "path",
    },
    "Get-ChildItem": {
        "os": "windows",
        "prefix": "Get-ChildItem",
        "arg_kind": "path",
    },
    "fsutil volume diskfree": {
        "os": "windows",
        "prefix": "fsutil volume diskfree",
        "arg_kind": "drive",
    },
}

# Characters that can compose a second action onto a command line. Any of
# them makes the submission fail closed.
REFUSED_SHELL_TOKENS = (
    ";", "&&", "||", "|", "`", "$(", "${", ">", "<", "&", "\n", "\\", "'",
    '"',
)

# Directory-name fragments the path argument must not contain: the crash and
# atop log locations are deliberately kept off the auto-execution list for
# this tier (guidance only, see references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md).
REFUSED_PATH_FRAGMENTS = (
    "crash", "atop", "dump", "shadow", "ssh", "passwd",
)

PATH_ARG_PATTERN = r"^/[A-Za-z0-9._/-]{0,120}$"
DRIVE_ARG_PATTERN = r"^[A-Za-z]:\\?$"

# RunCommand invocation types (verified live).
RUN_TYPE_LINUX = "RunShellScript"
RUN_TYPE_WINDOWS = "RunPowerShellScript"

# ---------------------------------------------------------------------------
# System-event taxonomy (EventType.Name enum, verified against the official
# DescribeInstanceHistoryEvents API document)
# ---------------------------------------------------------------------------
EVENT_REBOOT_TYPES = (
    "InstanceFailure.Reboot",
    "SystemFailure.Reboot",
    "SystemMaintenance.Reboot",
)
EVENT_REDEPLOY_TYPES = (
    "SystemMaintenance.Redeploy",
    "SystemFailure.Redeploy",
)
EVENT_LIFECYCLE_TYPES = (
    "InstanceExpiration.Stop",
    "InstanceExpiration.Delete",
    "AccountUnbalanced.Stop",
    "AccountUnbalanced.Delete",
)
# Lifecycle statuses worth flagging as still actionable.
EVENT_ACTIVE_STATUSES = ("Scheduled", "Executing", "Inquiring")
# Every status enum value, passed so the query returns finished AND pending
# events in one call (the API defaults to finished-only otherwise).
EVENT_ALL_STATUSES = (
    "Scheduled", "Avoided", "Executing", "Executed", "Canceled", "Failed",
    "Inquiring",
)

# ---------------------------------------------------------------------------
# CloudMonitor metric set (metric names verified live against the CMS
# meta-list for namespace acs_ecs_dashboard)
# ---------------------------------------------------------------------------
# (metric_name, meaning, aggregation field present in datapoints)
CMS_METRICS = (
    ("CPUUtilization", "host CPU usage, percent", "Average"),
    ("memory_usedutilization", "guest OS memory usage, percent (needs the "
     "CloudMonitor agent inside the instance)", "Average"),
    ("load_1m", "guest OS 1-minute load average (needs the CloudMonitor "
     "agent)", "Average"),
    ("DiskReadIOPS", "disk read IOPS", "Average"),
    ("DiskWriteIOPS", "disk write IOPS", "Average"),
    ("DiskReadBPS", "disk read throughput, bytes per second", "Average"),
    ("DiskWriteBPS", "disk write throughput, bytes per second", "Average"),
    ("DiskReadWriteIOPSUtilization", "IOps as a percent of the instance "
     "spec ceiling", "Value"),
    ("DiskReadWriteBPSUtilization", "throughput as a percent of the "
     "instance spec ceiling", "Value"),
)

# ---------------------------------------------------------------------------
# Thresholds used by the verdict engine (plain decision values, not data)
# ---------------------------------------------------------------------------
MEM_HIGH_PCT = 90.0
CPU_HIGH_PCT = 90.0
DISK_UTIL_CAP_PCT = 95.0        # at/above this the spec ceiling is the story
FS_FULL_PCT = 95.0              # df/df -i usage percent in pasted output
HEARTBEAT_FRESH_MINUTES = 10    # Cloud Assistant heartbeat freshness

# ---------------------------------------------------------------------------
# Disk categories that mean "local disk" (values taken from the DeviceCategory
# enum in the verified event API document and DescribeDisks Category values)
# ---------------------------------------------------------------------------
LOCAL_DISK_CATEGORY_PREFIX = "local_"
EPHEMERAL_CATEGORYS = ("ephemeral", "ephemeral_ssd")

# ---------------------------------------------------------------------------
# Instance power states that indicate a start/stop transition, not a crash
# ---------------------------------------------------------------------------
INTERMEDIATE_STATES = ("Starting", "Stopping", "Pending")

# ---------------------------------------------------------------------------
# Actions this skill never calls, whatever the customer confirms
# ---------------------------------------------------------------------------
NEVER_ALLOWED_ACTION_PREFIXES = (
    "Delete", "Release", "Reset", "Replace", "Attach", "Detach", "Reboot",
    "Start", "Stop", "Modify", "Update", "Import", "Export", "Revoke",
    "Grant", "Authorize", "Leave", "Join", "Unbind", "Bind", "Put",
    "Install", "Uninstall", "Send", "Deregister", "Cancel", "Redeploy",
    "Terminate", "Convert", "Withdraw", "Open", "Clone", "Migrate",
)

# ---------------------------------------------------------------------------
# Handoff targets (skills that exist online or in this batch)
# ---------------------------------------------------------------------------
HANDOFF_SKILLS = {
    "os_fault": "alibabacloud-ecs-linux-os-troubleshooting",
    "instance_state": "area:instance-state-diagnosis",
    "disk_io": "area:resource-bottleneck",
    "disk_capacity": "area:disk-expand-diagnosis",
    "disk_expand": "area:disk-expand-diagnosis",
}

# ---------------------------------------------------------------------------
# Official documentation links (all verified reachable; only URLs that were
# actually fetched or quoted from real support conversations)
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "history-events-api":
        "https://help.aliyun.com/zh/ecs/developer-reference/"
        "api-ecs-2014-05-26-describeinstancehistoryevents",
    "maintenance-attrs-api":
        "https://help.aliyun.com/zh/ecs/developer-reference/"
        "api-ecs-2014-05-26-describeinstancemaintenanceattributes.md",
    "maintenance-attrs-modify":
        "https://help.aliyun.com/zh/ecs/developer-reference/"
        "api-ecs-2014-05-26-modifyinstancemaintenanceattributes.md",
    "maintenance-attrs-console":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "modify-instance-maintenance-attributes.md",
    "kernel-crash-dump":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "enable-or-disable-the-kernel-crash-dump-service-for-an-instance",
    "atop":
        "https://help.aliyun.com/zh/ecs/"
        "how-to-use-the-linux-system-atop-monitoring-tools",
    "service-keepalive":
        "https://help.aliyun.com/zh/ecs/user-guide/"
        "use-the-cloud-assistant-plugin-for-service-keepalive.md",
    "renewal-change":
        "https://help.aliyun.com/zh/ecs/user-guide/renewal-change.md",
    "downtime-drill":
        "https://help.aliyun.com/zh/ecs/user-guide/downtime-drill.md",
    "linux-traffic-load":
        "https://help.aliyun.com/zh/ecs/support/"
        "query-and-case-analysis-of-linux-network-traffic-load",
    "windows-bandwidth":
        "https://help.aliyun.com/zh/ecs/support/"
        "troubleshooting-and-solving-the-problem-of-high-bandwidth-usage-"
        "in-windows-instances",
    "bt-panel-vendor": "https://www.bt.cn/new/index.html",
}

# ---------------------------------------------------------------------------
# Verdict codes emitted by the decision engine (identifiers only; the human
# wording for each lives in references/unexpected-reboot-diagnosis__diagnosis-playbook.md)
# ---------------------------------------------------------------------------
VERDICT_OS_CRASH_EVENT = "A_os_crash_event"
VERDICT_RESOURCE_EXHAUSTION = "B_resource_exhaustion"
VERDICT_STORAGE_CAP = "C_storage_perf_ceiling"
VERDICT_POWER_TRANSITION = "D_power_transition_handoff"
VERDICT_PLANNED = "E_planned_or_login"
VERDICT_HARDWARE_REDEPLOY = "F_hardware_redeploy"
VERDICT_RECOVERY_RISK = "G_backup_gap"
VERDICT_OS_ALIVE = "H_os_alive_app_layer"

# Cloud Assistant statuses (verified live values).
CA_STATUS_ONLINE = "true"
