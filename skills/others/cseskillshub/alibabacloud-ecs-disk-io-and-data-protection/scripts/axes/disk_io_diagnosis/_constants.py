"""Static knowledge and transport constants for the skill.

All reference data is embedded here as constants: the scripts/ directory must not
carry standalone data files.
"""

SKILL_NAME = "alibabacloud-ecs-disk-io-diagnosis"
API_USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}"

ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
CMS_PRODUCT = "cms"
CMS_API_VERSION = "2019-01-01"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"

# CloudMonitor exposes no per-disk IOPS/BPS metric name that was verified for this
# problem tier, so metric selection is an explicit operator input and its absence is
# reported as a limitation instead of being guessed.
CMS_NAMESPACE_HELP = (
    "CloudMonitor namespace and metric names for per-disk IOPS, throughput and "
    "latency are not verified inside this package; pass --namespace and --metric, or "
    "read the console pages listed in references/help-topics.md."
)
CMS_DEFAULT_PERIOD_SECONDS = 60

# Peak sampling windows reused from the multi-window manual review pattern.
DEFAULT_WINDOWS = ["1h", "3h", "12h", "1d", "7d", "14d"]
WINDOW_SECONDS = {
    "1h": 3600,
    "3h": 3 * 3600,
    "12h": 12 * 3600,
    "1d": 24 * 3600,
    "7d": 7 * 24 * 3600,
    "14d": 14 * 24 * 3600,
}

DEFAULT_TIMEOUT = 30
MAX_TIMEOUT = 300
MAX_ATTEMPTS = 3
RETRY_BASE_SECONDS = 1.0
RETRY_MAX_SECONDS = 8.0

# ---------------------------------------------------------------------------
# Interpretation thresholds (fixed so conclusions do not depend on who reviews)
# ---------------------------------------------------------------------------
SATURATION_RATIO = 0.95
NEAR_CEILING_RATIO = 0.80
WELL_BELOW_CEILING_RATIO = 0.50
CLOUD_MONITOR_BASIC_GRANULARITY_SECONDS = 15

VERDICT_AT_CEILING = "at-ceiling"
VERDICT_NEAR_CEILING = "near-ceiling"
VERDICT_WELL_BELOW = "well-below-ceiling"
VERDICT_PARTIAL = "mid-range"
VERDICT_INDETERMINATE = "indeterminate"

VERDICT_WORDING = {
    VERDICT_AT_CEILING: (
        "Measured load reaches the computed ceiling for this disk. Sustained or "
        "repeated occurrence justifies evaluating a higher performance level; an "
        "isolated spike justifies business-side review first."
    ),
    VERDICT_NEAR_CEILING: (
        "Measured load sits close to the computed ceiling without proving it. Treat "
        "as possible throttling only together with an alarm for the same disk and window."
    ),
    VERDICT_WELL_BELOW: (
        "Measured load stays far below the computed ceiling, so this disk was not "
        "throttled by its own specification. Look for memory pressure, a specific "
        "process, or a threshold configured outside Alibaba Cloud."
    ),
    VERDICT_PARTIAL: (
        "Measured load sits in the mid range of the computed ceiling. Ceiling limits "
        "do not explain the reported symptom on their own."
    ),
    VERDICT_INDETERMINATE: (
        "No comparison was possible because either the ceiling or the measurement is "
        "unavailable. See the limitations section of this report."
    ),
}

# ---------------------------------------------------------------------------
# Disk performance ceilings
#
# Provenance and confidence for every number below is recorded in
# references/disk-performance-baseline.md. Values marked PROVENANCE_AGENT_NOTE come
# from support-engineer statements in the source material and still have to be
# confirmed against the block storage performance document before being quoted to a
# customer as a contract figure. Values marked PROVENANCE_NO_GUIDANCE must be
# reported as "no official figure" rather than substituted from a similar disk type.
# ---------------------------------------------------------------------------
PROVENANCE_NO_GUIDANCE = "no-official-guidance"
PROVENANCE_AGENT_NOTE = "agent-stated-needs-doc-confirmation"
PROVENANCE_DERIVED_FROM_SIZE = "formula-stated-in-source-material"

ESSD_CATEGORY = "cloud_essd"
ELASTIC_EPHEMERAL_DISK_CATEGORY = "elastic_ephemeral_disk"
CLOUD_AUTO_CATEGORY = "cloud_auto"
CLOUD_EFFICIENCY_CATEGORY = "cloud_efficiency"
CLOUD_SSD_CATEGORY = "cloud_ssd"
CLOUD_CATEGORY = "cloud"
LOCAL_SSD_CATEGORY = "local_ssd"
LOCAL_HDD_CATEGORIES = ("local_hdd_pro", "local_hdd")

PL0_MAX_IOPS = 10000
PL0_IOPS_BASE = 1800
PL0_IOPS_PER_GB = 12
PL0_IOPS_CAPACITY_FOR_MAX_GB = 684
PL0_MAX_THROUGHPUT_MBPS = 180
PL1_MAX_IOPS = 50000
PL1_MAX_THROUGHPUT_MBPS = 350
PL2_MAX_THROUGHPUT_MBPS = 750
PREVIOUS_GENERATION_LOCAL_SSD_MAX_RANDOM_IOPS = 12000

PERFORMANCE_LEVEL_CEILINGS = {
    "PL0": {
        "max_iops": PL0_MAX_IOPS,
        "max_throughput_mbps": PL0_MAX_THROUGHPUT_MBPS,
        "iops_formula": "min(10000, 1800 + 12 * capacity_GiB)",
        "capacity_for_max_iops_gib": PL0_IOPS_CAPACITY_FOR_MAX_GB,
        "provenance": PROVENANCE_AGENT_NOTE,
    },
    "PL1": {
        "max_iops": PL1_MAX_IOPS,
        "max_throughput_mbps": PL1_MAX_THROUGHPUT_MBPS,
        "iops_formula": None,
        "capacity_for_max_iops_gib": None,
        "provenance": PROVENANCE_AGENT_NOTE,
    },
    "PL2": {
        "max_iops": None,
        "max_throughput_mbps": PL2_MAX_THROUGHPUT_MBPS,
        "iops_formula": None,
        "capacity_for_max_iops_gib": None,
        "provenance": PROVENANCE_AGENT_NOTE,
    },
    "PL3": {
        "max_iops": None,
        "max_throughput_mbps": None,
        "iops_formula": None,
        "capacity_for_max_iops_gib": None,
        "provenance": PROVENANCE_NO_GUIDANCE,
    },
}

CATEGORY_CEILINGS = {
    ESSD_CATEGORY: {"note": "Ceiling depends on performance_level plus size; see PERFORMANCE_LEVEL_CEILINGS."},
    CLOUD_AUTO_CATEGORY: {
        "max_iops": None,
        "max_throughput_mbps": None,
        "note": (
            "ESSD AutoPL decouples capacity from performance and supports provisioned IOPS "
            "and performance burst, so no single ceiling is computed here; read the "
            "provisioned and burst settings for the individual disk."
        ),
        "provenance": PROVENANCE_NO_GUIDANCE,
    },
    LOCAL_HDD_CATEGORIES[0]: {
        "max_iops": None,
        "max_throughput_mbps": None,
        "note": (
            "No official IOPS guidance figure exists for this local HDD generation. Report "
            "'no official IOPS figure' and investigate only throughput SLA claims. Never "
            "substitute a previous-generation local SSD number."
        ),
        "provenance": PROVENANCE_NO_GUIDANCE,
    },
    LOCAL_SSD_CATEGORY: {
        "max_iops": PREVIOUS_GENERATION_LOCAL_SSD_MAX_RANDOM_IOPS,
        "max_throughput_mbps": None,
        "note": (
            "Previous-generation local SSD figure, up to 12000 random IOPS. It is NOT a "
            "local HDD number and must always be labelled by generation."
        ),
        "provenance": PROVENANCE_AGENT_NOTE,
    },
}

SIZE_UNKNOWN_FALLBACK = (
    "Disk size was not returned, so no capacity-derived ceiling could be computed."
)

# ---------------------------------------------------------------------------
# In-guest inspection commands
#
# This is the complete callable set. It mirrors the batch low-risk operation list,
# which is oriented at capacity and mount evidence: it contains no per-process I/O
# attribution tooling, so process-level attribution stays a manual step. Anything
# not listed here is refused.
# ---------------------------------------------------------------------------
GUEST_COMMANDS = {
    "disk-usage": {
        "os": "linux",
        "command": "df -h",
        "needs_path": False,
        "mutates": "no",
        "purpose": "Separate 'the filesystem is full' from 'I/O is slow'.",
    },
    "inode-usage": {
        "os": "linux",
        "command": "df -i",
        "needs_path": False,
        "mutates": "no",
        "purpose": "Separate inode exhaustion from I/O saturation.",
    },
    "mount-map": {
        "os": "linux",
        "command": "findmnt",
        "needs_path": False,
        "mutates": "no",
        "purpose": "Map a device name to its mount point for the disk under review.",
    },
    "deleted-open-files": {
        "os": "linux",
        "command": "lsof +L1",
        "needs_path": False,
        "mutates": "no",
        "purpose": "Show files still held open after removal, a capacity rather than I/O effect.",
    },
    "path-stat": {
        "os": "linux",
        "command": "stat",
        "needs_path": True,
        "mutates": "no",
        "purpose": "Inspect one path's metadata without touching its contents.",
    },
    "directory-volume": {
        "os": "linux",
        "command": "du -h -d 1",
        "needs_path": True,
        "mutates": "no",
        "purpose": "Measure how much one directory level holds, e.g. a log directory.",
    },
    "line-count": {
        "os": "linux",
        "command": "wc -l",
        "needs_path": True,
        "mutates": "no",
        "purpose": "Count lines of one file, e.g. an application log.",
    },
    "directory-listing": {
        "os": "linux",
        "command": "ls -l",
        "needs_path": True,
        "mutates": "no",
        "purpose": "List one directory without following or modifying anything.",
    },
    "windows-volumes": {
        "os": "windows",
        "command": "Get-Volume",
        "needs_path": False,
        "mutates": "no",
        "purpose": "Volume health and free space on a Windows instance.",
    },
    "windows-drives": {
        "os": "windows",
        "command": "Get-PSDrive",
        "needs_path": False,
        "mutates": "no",
        "purpose": "Used and free space per drive on a Windows instance.",
    },
    "windows-listing": {
        "os": "windows",
        "command": "Get-ChildItem -Path",
        "needs_path": True,
        "mutates": "no",
        "purpose": "List one directory on a Windows instance.",
    },
}

# Named in the batch list but with no concrete subcommand confirmed, therefore not callable.
GUEST_COMMANDS_WITHHELD = [
    "fsutil subcommands (the batch list allows non-mutating subcommands, none was verified)",
]

# Rejected outright: kept here so the refusal wording is identical every time.
REFUSED_GUEST_TOOLS = [
    "atop", "iotop", "iftop", "pidstat", "sar", "vmstat", "iostat", "dmesg", "journalctl",
    "systemctl", "service", "kill", "pkill", "mount", "umount", "mkfs", "fsck", "xfs_repair",
    "tune2fs", "fio", "dd", "truncate", "rm", "mv", "echo >", "reboot", "shutdown",
]

RUN_COMMAND_LINUX_TYPE = "RunShellScript"
RUN_COMMAND_WINDOWS_TYPE = "RunPowerShellScript"
RUN_COMMAND_TIMEOUT_SECONDS = 60

LINUX_PATH_PATTERN = r"^/[A-Za-z0-9._+@:,%-]{0,255}$"
WINDOWS_PATH_PATTERN = r"^[A-Za-z]:[A-Za-z0-9._+@:,%-]{0,255}$"

# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
INSTANCE_ID_PATTERN = r"^i-[A-Za-z0-9]{4,40}$"
DISK_ID_PATTERN = r"^d-[A-Za-z0-9]{4,40}$"
DIAGNOSIS_REPORT_ID_PATTERN = r"^dr-[A-Za-z0-9]{4,60}$"
REGION_ID_PATTERN = r"^[A-Za-z]{2}-[A-Za-z0-9-]{2,24}$"
IPV4_PATTERN = r"^(\d{1,3}\.){3}\d{1,3}$"
SNAPSHOT_NAME_PATTERN = r"^[A-Za-z][A-Za-z0-9._:-]{1,127}$"
CLOUD_EVENT_TOKENS = (
    "StoragePerformanceReachLimit",
    "SysDiskIOPS",
    "SysDiskBPS",
)
ALARM_REASON_CODES = {
    "SysDiskIOPS": "system disk IOPS ceiling",
    "SysDiskBPS": "system disk throughput ceiling",
}

# ---------------------------------------------------------------------------
# Routing keywords
# ---------------------------------------------------------------------------
# Keywords that mean "this is capacity/inode usage", not I/O performance.
ROUTE_AWAY_CAPACITY = [
    "disk full", "no space left", "filesystem full", "disk usage 100", "inode",
    "cannot write, disk is full", "clean up", "delete logs to free space",
]
ROUTE_AWAY_EXPAND = [
    "resize did not take effect", "extended the disk but", "partition is still",
    "growpart", "xfs_growfs", "lvextend", "new size not visible",
]
ROUTE_AWAY_STATE = [
    "cannot start the instance", "stuck while stopping", "reboot never finished",
    "instance will not come back", "fstab", "selinux",
]
ROUTE_AWAY_CONNECTIVITY = [
    "ssh refused", "port 22", "rdp", "security group", "password is wrong",
]
ROUTE_AWAY_MANUAL = [
    "snapshot", "backup job", "hbr", "anti-ransomware", "refund", "downgrade",
    "billing dispute", "mining", "attack",
]
IO_AXIS_KEYWORDS = [
    "slow", "latency", "timeout", "hang", "frozen", "unresponsive", "iops",
    "throughput", "io wait", "iowait", "throughput ceiling", "read write limited",
    "storageperformancereachlimit", "benchmark", "fio", "stalled", "busy",
]

# ---------------------------------------------------------------------------
# Console entry points quoted to customers
# ---------------------------------------------------------------------------
CONSOLE_HEALTH_DIAGNOSIS = "https://health.console.aliyun.com/diagnosis-task/list?type=scene"
CONSOLE_HOST_MONITOR = "https://cloudmonitornext.console.aliyun.com/hostMonitor"

# ---------------------------------------------------------------------------
# Report limitations that must be surfaced whenever the matching condition holds
# ---------------------------------------------------------------------------
LIMITATION_GRANULARITY = (
    "CloudMonitor basic monitoring aggregates at a minimum granularity of {seconds}s, so a "
    "one-second burst that touched the disk ceiling may not appear in the charts. Absence of "
    "a peak in the console does not prove the ceiling was never reached."
).format(seconds=CLOUD_MONITOR_BASIC_GRANULARITY_SECONDS)
LIMITATION_AGENT_MISSING = (
    "The CloudMonitor host agent is required for operating-system metrics. When it is missing "
    "or broken, disk and memory series come back empty, which is a collection gap rather than "
    "evidence of a healthy instance."
)
LIMITATION_NO_PROCESS_ATTRIBUTION = (
    "Neither the cloud APIs nor the callable command set in this skill attribute I/O to a "
    "process. Linux keeps no historical record of per-process resource use, so process-level "
    "attribution needs a recorder such as atop installed before the next occurrence."
)
LIMITATION_NO_MEMORY_SERIES = (
    "No memory reading was obtained, so the memory-to-I-O chain could not be confirmed or ruled out."
)
LIMITATION_SMOKE_TEST_ONLY = (
    "In-guest readings cover capacity, inodes and mounts only; they cannot confirm or exclude "
    "per-process I/O load."
)
LIMITATION_EVENT_INTAKE = (
    "Cloud events and diagnosis reports are not read through an API by this skill. Interpretation "
    "uses an event payload pasted by the customer, and the full report stays in the diagnosis console."
)
LIMITATION_NO_PASSWORD_COLLECTED = (
    "This skill never asks for or accepts an instance password; in-guest readings go through the "
    "Cloud Assistant channel the instance already trusts."
)

STATUS_OK = "STATUS: OK"
STATUS_DEGRADED = "STATUS: DEGRADED"
STATUS_FAIL = "STATUS: FAIL"
