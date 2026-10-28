"""Shared constants for the ECS snapshot policy check skill.

All reference data lives here as code constants: nothing under ``scripts/`` is
allowed to be a standalone data file.
"""

SKILL_NAME = "alibabacloud-ecs-snapshot-policy-check"

# Observability: one 32-hex session id per process run, attached to every call.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

CLI_BIN = "aliyun"
ECS_PRODUCT = "ecs"
ECS_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_VERSION = "2015-04-01"
# Plugin-style invocation (lowercase-hyphenated) is only used for STS; RPC
# products keep the PascalCase action name.
STS_IDENTITY_COMMAND = [CLI_BIN, STS_PRODUCT, "GetCallerIdentity"]

# Timeouts (seconds) and paging limits.
CLI_TIMEOUT_SECONDS = 60
CLI_TIMEOUT_WRITE_SECONDS = 120
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.5
PAGE_SIZE = 50
MAX_PAGES = 40

RETRYABLE_MARKERS = (
    "Throttling",
    "ThrottlingUser",
    "SystemBusy",
    "ServiceUnavailable",
    "InternalError",
    "SDK.ServerUnreachable",
    "RequestTimeout",
    "5xx",
    "timed out",
    "timeout",
    "connection reset",
)

# Credential material must never reach logs or reports.
SECRET_KEY_MARKERS = (
    "AccessKeyId",
    "AccessKeySecret",
    "SecurityToken",
    "Signature",
    "PrivateKey",
    "Password",
)

# Actions this skill may invoke. Anything outside this set is refused.
ALLOWED_ACTIONS = frozenset(
    {
        "DescribeInstances",
        "DescribeDisks",
        "DescribeSnapshots",
        "DescribeInvocations",
        "CreateSnapshot",
        "GetCallerIdentity",
    }
)

# Write actions require the explicit confirmation gate described in SKILL.md.
WRITE_ACTIONS = frozenset({"CreateSnapshot"})

# Snapshot states as returned by DescribeSnapshots.
SNAPSHOT_STATUS_PROGRESSING = "progressing"
SNAPSHOT_STATUS_ACCOMPLISHED = "accomplished"
SNAPSHOT_STATUS_FAILED = "failed"

# Progress has not moved for this many minutes before the report calls it out.
STALLED_PROGRESS_MINUTES = 30
# A snapshot older than this many hours at a single percentage is reported as a
# candidate for a support ticket rather than normal queueing.
LONG_RUNNING_HOURS = 24

# In guest instances the skill only ever suggests side-effect-free inspection
# commands. Any command that is not provably on this list is refused.
GUEST_COMMAND_ALLOWLIST = (
    "df -h",
    "df -i",
    "du -x --max-depth=1",
    "lsof +L1",
    "findmnt",
    "stat",
    "ls -l",
    "Get-Volume",
    "Get-PSDrive",
    "Get-ChildItem",
    "fsutil volume diskfree",
)

# Characters that turn any allowlisted prefix into a side effect.
COMMAND_META_CHARS = (
    ";",
    "&",
    "|",
    "`",
    "$(",
    ">",
    "<",
    "\n",
    "\r",
    "&&",
    "||",
)

# Auth failures must be described with these literals only.
PERMISSION_DENIED_CODES = ("NoPermission", "ImplicitDeny")

# Report contract.
STATUS_OK = "STATUS: OK"
STATUS_DEGRADED = "STATUS: DEGRADED"
STATUS_FAIL = "STATUS: FAIL"

DEFAULT_RETENTION_DAYS = 7
ARCHIVE_MIN_STANDARD_DAYS = 14
ARCHIVE_MIN_RETENTION_HOURS = 1440  # 60 days at the archive layer
SNAPSHOT_UNIT_PRICE_CNY_PER_GB_MONTH = 0.12

# Console entry points used in guided (human-executed) steps.
CONSOLE_SNAPSHOT_LIST = "https://ecs.console.aliyun.com/snapshot/region/{region_id}"
CONSOLE_AUTO_POLICY = "https://ecs.console.aliyun.com/autoSnapshotPolicy/region/{region_id}"
CONSOLE_DISK_LIST = "https://ecs.console.aliyun.com/disk/region/{region_id}"
