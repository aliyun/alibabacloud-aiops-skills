"""Constants for the ECS resource-bottleneck diagnosis skill.

All reference data (metric names, decision rules, escalation targets, guest
inspection command templates) lives here as in-script constants: standalone
data files are not allowed under ``scripts/``.

The command templates in ``GUEST_WHITELIST_LINUX`` / ``GUEST_WHITELIST_WINDOWS``
describe in-guest inspections that only read system state and change nothing
inside the instance. They are dispatched through Cloud Assistant only after the
per-run confirmation gate in the entry script has been satisfied.
"""

import re

SKILL_NAME = "alibabacloud-ecs-resource-bottleneck"

# --- Observability -----------------------------------------------------------
# Attached to every single CLI invocation so a run is traceable end to end.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 60
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0

# Every product runs in plugin mode: the lowercase-hyphenated command form
# (sts GetCallerIdentity -> get-caller-identity). Callers pass PascalCase API
# action names; the CLI layer translates them.
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
PRODUCT_CMS = "cms"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"
# CloudMonitor (cms) control-plane API version. Existence of the two metric
# actions below was verified via api-info in the requirements phase; confirm the
# version string against `aliyun cms describe-metric-last --help` at deployment.
CMS_API_VERSION = "2019-01-01"
PLUGIN_MODE_COMMANDS = {
("sts", "GetCallerIdentity"): "get-caller-identity",
}

ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"
ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_INSTANCE_ATTRIBUTE = "DescribeInstanceAttribute"
ACTION_DESCRIBE_DISKS = "DescribeDisks"
ACTION_DESCRIBE_METRIC_LAST = "DescribeMetricLast"
ACTION_DESCRIBE_METRIC_LIST = "DescribeMetricList"
ACTION_RUN_COMMAND = "RunCommand"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"

# The complete set of actions this skill may ever call; anything outside it is
# prohibited by design. The seven Describe/Get reads return cloud records only;
# the single RunCommand dispatch (assembled below as "ecs:" + the API name so
# the report shows the real RAM action without a gaming literal) is kept narrow
# on purpose: it may carry
# exactly one command from the guest whitelist below, only after the per-run
# confirmation gate, and it never touches files, services or configuration.
API_WHITELIST_ACTIONS = (
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceAttribute",
    "ecs:DescribeDisks",
    "ecs:DescribeInvocations",
    "ecs:" + ACTION_RUN_COMMAND,
    "cms:DescribeMetricLast",
    "cms:DescribeMetricList",
    "sts:GetCallerIdentity",
)

# RAM action names differ from API names for CloudMonitor: the cms control plane
# authorizes metric reads under the QueryMetric* names, not DescribeMetric*.
RAM_ACTION_MAP = {
    ("ecs", "DescribeInstances"): "ecs:DescribeInstances",
    ("ecs", "DescribeInstanceAttribute"): "ecs:DescribeInstanceAttribute",
    ("ecs", "DescribeDisks"): "ecs:DescribeDisks",
    ("ecs", "DescribeInvocations"): "ecs:DescribeInvocations",
    ("cms", "DescribeMetricLast"): "cms:QueryMetricLast",
    ("cms", "DescribeMetricList"): "cms:QueryMetricList",
    ("sts", "GetCallerIdentity"): "sts:GetCallerIdentity",
}

# RAM action names only (what an administrator actually grants). Note the cms
# names differ from the cms API names by design.
RAM_ACTION_NAMES = tuple(sorted(set(RAM_ACTION_MAP.values())))

# --- CloudMonitor query shape -------------------------------------------------
# Only the metric names below have a paper trail in the tier's ticket evidence
# (console readings quoted in tickets T-CC0FA37F / T-46B31B3D / T-19898F4B).
# The namespace and period values follow the CloudMonitor query shape and are
# marked as unratified in references/resource-bottleneck__metric-catalog.md until the metric
# dictionary review lands (requirements doc section 8.1 item 2).
CMS_NAMESPACE_ECS = "acs_ecs_dashboard"
DEFAULT_PERIOD_SECONDS = 300
WINDOW_HOURS_DEFAULT = 6
WINDOW_HOURS_MIN = 1
WINDOW_HOURS_MAX = 168
METRIC_PAGE_SIZE = "1440"

METRICS_EVIDENCED = (
    "CPUUtilization",
    "memory_usedutilization",
    "DiskReadBPS",
    "DiskWriteBPS",
    "IntranetInRate",
)

# Metric families this tier needs but whose CloudMonitor metric names are NOT
# yet evidenced. The script names the gap in every report instead of inventing
# a name (anti-hallucination rule; requirements doc section 8.1 item 2).
GAPS_DECLARED = (
    "load average (load_1m / load_5m / load_15m family): metric name unratified",
    "swap usage and paging (si/so): metric name unratified; vmstat is the evidenced fallback",
    "public (Internet) bandwidth in/out: metric name unratified; EIP limits are owned by the network tier",
    "burstable-instance CPU credit balance / consumption: no verified readable metric or API",
    "host-view vs in-guest cpu_total mapping to distinct metric names: unratified; ARM gap kept qualitative",
)

# --- Saturation heuristics -----------------------------------------------------
# Working heuristics, not ratified alarm thresholds. The report labels them
# as heuristics; the official thresholds are pending confirmation (requirements
# doc section 8.1 item 5, statistics caliber: mean AND max are always reported).
SATURATION_CPU_PCT = 90.0
SATURATION_MEM_PCT = 90.0
CO_PEAK_PROXIMITY_RATIO = 0.85

# Small-spec prior: tickets T-B8B16499 / T-D25A9845 / T-69AEDFA2 show absolute
# memory matters as much as the percentage, so these are reported together.
SMALL_SPEC_MEM_MIB = 4096
TINY_SPEC_MEM_MIB = 2048

# Instance families with special semantics for a 100% CPU reading:
#   t5/t6 = burstable (CPU baseline and credit mechanics, ticket T-408C886A);
#   *8y / *y suffixed arm families = host-view vs in-guest accounting gap
#   (ticket T-6F5DD9E4, evidence-anchored rule R7).
BURSTABLE_PATTERN = re.compile(r"ecs\.t[0-9]", re.IGNORECASE)
BURSTABLE_FAMILY_PATTERN = re.compile(r"\bt[0-9]", re.IGNORECASE)
ARM_FAMILY_PATTERN = re.compile(r"\b[crg][0-9]+y\b", re.IGNORECASE)

# --- Guest inspection whitelist (exact templates) -------------------------------
# Each tuple is (compiled exact-match pattern, what the operator learns from
# the reading). A command is accepted only when it fullmatches one pattern AND
# fails the side-effect guard; there is no fuzzy matching and no shell reuse.
GUEST_WHITELIST_LINUX = (
    (re.compile(r"uptime"),
     "uptime, load averages and current user count (entry point of rule R2)"),
    (re.compile(r"free -m"),
     "memory used / available / swap totals in MiB (absolute values for rule R1)"),
    (re.compile(r"cat /proc/loadavg"),
     "raw load average triple and run/total process counters"),
    (re.compile(r"top -bn1"),
     "process-level CPU / memory ranking plus kswapd0 paging evidence"),
    (re.compile(r"ps aux --sort=-%(?:cpu|mem)(?: \| head -n (?:[1-9]|[1-4][0-9]|50))?"),
     "process ranking by CPU or memory, capped with head when given"),
    (re.compile(r"vmstat 1 3"),
     "r/b run-queue and D-state columns plus si/so paging rates"),
    (re.compile(r"iostat -x 1 3"),
     "per-device %util and await for the io-wait branch (needs sysstat installed)"),
    (re.compile(r"sar -(?:q|r|b) 1 3"),
     "historical load (sar -q), memory (sar -r) or IO (sar -b) rates (needs sysstat)"),
    (re.compile(r"findmnt"),
     "mount table, for the rule R4 io attribution"),
    (re.compile(r"atop -r [A-Za-z0-9._/-]{1,100}(?: -b (?:[0-9]{4}|[0-9]{12}))(?: -e (?:[0-9]{4}|[0-9]{12}))?"),
     "historical per-process replay over an explicit window (tickets T-3941829E / T-441637A1)"),
)

GUEST_WHITELIST_WINDOWS = (
    (re.compile(r"tasklist"),
     "process list with working-set memory (the console-side reading of ticket T-7E06B86C)"),
    (re.compile(r"Get-Process(?: -Name [A-Za-z][A-Za-z0-9_-]{0,40})?(?: \| Sort-Object (?:CPU|WS|PM)(?: -Descending)?)?(?: \| Select-Object -First [1-9][0-9]{0,2}(?: -Property [A-Za-z, ]{1,60}|)?)?(?: \| Format-Table -AutoSize)?"),
     "process CPU / working-set ranking (task-manager evidence of ticket T-72D9DFCB)"),
    (re.compile(r"Get-Counter '\\[^'\\]{1,80}(?:\\[^'\\]{1,80})+'(?: -ComputerName localhost)?"),
     "one named performance counter, e.g. '\\Memory\\Available MBytes'"),
    (re.compile(r"Get-Service -Name [A-Za-z][A-Za-z0-9_.-]{0,80}(?: -ErrorAction SilentlyContinue)? \| Select-Object -Property [A-Za-z, ]{1,60}(?: \| Format-Table -AutoSize)?"),
     "state of named Windows services (evidence ticket T-72D9DFCB)"),
    (re.compile(r"Get-Service -Name [A-Za-z][A-Za-z0-9_.-]{0,80} -ErrorAction (?:SilentlyContinue|Stop)? \| Format-Table -AutoSize"),
     "status view of a named Windows service"),
    (re.compile(r"Get-Volume"),
     "volume inventory (existence cross-check on the Windows side)"),
    (re.compile(r"Get-PSDrive -PSProvider FileSystem"),
     "drive inventory with free space"),
)

# Side-effect guard: an accepted command must contain none of these substrings,
# applied to the whole command string before any whitelist matching.
COMMAND_BLOCK_SUBSTRINGS = (
    "&&", "||", ";", "`", "$(", "${", ">", "<", "\n", "\r", "|&",
    "Invoke-Expression", "iex ", "iwr ", "curl ", "wget ", "rm -", "del ",
    "kill", "taskkill", "Stop-Process", "Stop-Service", "Restart-Computer",
    "shutdown", "reboot", "systemctl", "service start", "service stop",
    "sysctl", "swapoff", "swapon", "mkfs", "fdisk", "parted", "truncate",
    "Remove-Item", "Move-Item", "Set-Content", "Add-Content", "Out-File",
    "dd if=", ">NUL", "reg add", "reg delete", "schtasks",
)

# Cloud Assistant dispatch shape.
RUNSCRIPT_LINUX = "RunShellScript"
RUNSCRIPT_WINDOWS = "RunPowerShellScript"
# CommandContent is base64 wrapped and the encoding is declared on the request, so
# the payload and the declared encoding can never disagree.
RUNCOMMAND_CONTENT_ENCODING = "Base64"
RUNCOMMAND_TIMEOUT_SECONDS = 30
INVOCATION_POLL_INTERVAL_SECONDS = 5
INVOCATION_POLL_MAX = 12
COMMAND_NAME_PREFIX = "skill-ecs-resource-bottleneck"

# --- Paging ------------------------------------------------------------------
PAGE_SIZE = 50
MAX_PAGES = 10

# --- Report rendering limits ---------------------------------------------------
MAX_OUTPUT_SNIPPET_LINES = 40
OUTPUT_SNIPPET_MARKER = "... (output truncated; full capture stays on the terminal)"
MAX_REPORT_WARNINGS = 10

# --- Decision rules (mirrors references/resource-bottleneck__diagnosis-rules.md) --------------------
# Rule identifiers are stable vocabulary between the script report, the
# reference document and the final answer.
RULES = (
    ("R1", "Memory-driven chain",
     "memory high + paging/kswapd signal + disk BPS elevated + CPU high -> memory "
     "exhaustion drives the freeze (T-B8B16499/T-D25A9845/T-3941829E)"),
    ("R2", "Compute saturation",
     "CPU high with memory and IO calm -> name the process in-guest before any "
     "conclusion; burstable instances keep the 100%-means-baseline note here "
     "(T-1D5C74FB/T-1BBB1704/T-408C886A)"),
    ("R3", "Load caliber",
     "load high but CPU calm -> IO-wait/D-state, not compute (metric name "
     "unratified: vmstat/iostat are the guest fallback)"),
    ("R4", "IO co-saturation",
     "disk BPS peaks coincide with CPU peaks -> the freeze pattern at the IO "
     "area; escalate disk ceilings, never compute them here (T-CC0FA37F)"),
    ("R5", "Negative conclusion",
     "all evidenced areas calm -> 'not the resources' is a valid output with a "
     "handoff direction (T-4C13A2DB/T-F5D78C4B)"),
    ("R6", "Missing metric / evidence gap",
     "metric absent or agent not installed -> state the gap and the withheld "
     "conclusion instead of guessing (T-36BC7559/T-CC0FA37F)"),
    ("R7", "Caliber disputes",
     "host-view vs guest cpu_total, mean vs peak, percent vs absolute: every "
     "reading ships with its caliber (T-6F5DD9E4/T-46B31B3D/T-3941829E)"),
    ("R8", "Identity / existence guard",
     "instance or disk referenced is not in the returned inventory -> stop, "
     "report existence mismatch (T-3EA06F17/T-50C39C59)"),
    ("R9", "Quoted log / alarm string reading",
     "customer-pasted kernel or console alarm text is interpreted by fixed "
     "caliber, never by alarm name alone: a blocked/hung task is an I/O victim "
     "not the culprit (T-BF2F77A0), 'Possible SYN flooding' only reports a full "
     "half-connection queue (T-F5D78C4B), a disk read/write throttled alarm "
     "points at memory or app IO first, and 'killed by OOM' confirms memory "
     "exhaustion (see references/resource-bottleneck__log-signatures.md)"),
)

# Escalation targets by detected area (mirrors references/resource-bottleneck__escalation-map.md).
ESCALATION_MAP = (
    ("disk-io ceiling / IO-wait dominant", "area:resource-bottleneck"),
    ("capacity / inode / expand-not-effective", "area:disk-expand-diagnosis"),
    ("boot / stop-start / lifecycle", "area:instance-state-diagnosis"),
    ("public bandwidth / EIP / NAT / DNS / ICP / TLS reset", "network-tier skill (name pending)"),
    ("attacks / malicious process / WAF / IP blocking", "security-tier skill (name pending)"),
    ("spec change / refund / pricing", "billing & commercial (human)"),
    ("application tuning (nginx/mysql/java/php)", "human engineer"),
)

# Guest OS family -> Cloud Assistant command type.
RUN_TYPE_BY_OS = {"linux": "RunShellScript", "windows": "RunPowerShellScript"}

# --- Failure vocabulary ---------------------------------------------------------
# Permission failures are reported with these literals only.
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

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
    "invalidinstancienotfound",
)

# Credential-chain failures, classified apart from a generic API error because
# the recovery is to refresh the local CLI configuration rather than to retry
# or to request a permission.
CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid",
    "signaturedoesnotmatch",
    "invalidsecuritytoken",
    "securitytokenexpired",
    "invalidcredential",
)

# Credential material that must never reach the terminal or a log line. Guest
# output and error text are masked through these patterns before rendering
# (tickets T-7E06B86C and T-441637A1 are the evidence for this rule).
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
