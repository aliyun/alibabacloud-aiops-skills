"""Frozen constants for the ECS console-channel diagnosis skill.

Everything the entry script knows without touching the network lives here:
the guest inspection-command whitelist, the five-layer channel model, the
CloudMonitor metric set used for the hang verdict, error-string patterns,
handoff targets and official documentation links.

All API facts recorded in this module come from this tier's batch verified
API surface: ecs 2014-05-26 actions DescribeInstances,
DescribeInstancesFullStatus, DescribeCloudAssistantStatus,
DescribeInvocations and the gated dispatch action RunCommand, plus the batch
verified read entries for the STS caller identity and the CloudMonitor
latest-value query (2019-01-01, namespace acs_ecs_dashboard and the metric
names below). Action existence and parameter names are taken from that
surface, not from memory, and nothing here is estimated or invented.

SECURITY: no credential of any kind is stored or read from this module.
"""

SKILL_NAME = "alibabacloud-ecs-console-channel-diagnosis"

# ---------------------------------------------------------------------------
# Products and API versions (from this tier's batch verified API surface)
# ---------------------------------------------------------------------------
ECS_PRODUCT = "ecs"
ECS_VERSION = "2014-05-26"
CMS_PRODUCT = "cms"
CMS_VERSION = "2019-01-01"
STS_PRODUCT = "sts"
STS_VERSION = "2015-04-01"

# CloudMonitor namespace for ECS metrics, as carried by the batch verified
# read entry for the latest-value query.
CMS_NAMESPACE_ECS = "acs_ecs_dashboard"

# Aggregation period sent with every DescribeMetricLast call, taken from the
# documented period set for that parameter (its documented default); it is
# never invented per call.
CMS_PERIOD_SECONDS = 900

# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------
CLI_TIMEOUT_SECONDS = 30          # per query call
CLI_TIMEOUT_WRITE_SECONDS = 90    # gated dispatch call
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_BASE_SECONDS = 2
SESSION_ID_LENGTH = 32

USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

# Throttling and server-side codes worth retrying with backoff.
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
# Polling budgets for one dispatched guest inspection command
# ---------------------------------------------------------------------------
INVOCATION_POLL_INTERVAL_SECONDS = 3
INVOCATION_POLL_BUDGET_SECONDS = 60
GUEST_COMMAND_TIMEOUT_SECONDS = 30   # Timeout parameter sent to dispatch

# Terminal Cloud Assistant invocation statuses (documented response values).
INVOCATION_TERMINAL_STATUSES = (
    "Success", "Failed", "Error", "Timeout", "Stopped",
    "PartialFailed", "Invalid", "Aborted",
)

# Cloud Assistant status strings (documented response values; the status
# field is the string "true" / "false", not a JSON boolean).
CA_STATUS_ONLINE = "true"

# ---------------------------------------------------------------------------
# Guest inspection whitelist (batch low-risk list, section B, tier subset).
# The gated dispatch path carries EXACTLY ONE of these per confirmation.
# Commands only READ state; none of them mutates data.
# ---------------------------------------------------------------------------
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

# Families that accept ONE additional argument (a plain path or drive),
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

# Path fragments kept off the auto-execution list for this tier: credential,
# service-configuration and forensic-log locations. Their content is
# interpreted only through the offline `explain` path on customer-pasted
# output (see references/console-channel-diagnosis__guest-inspection-whitelist.md).
REFUSED_PATH_FRAGMENTS = (
    "crash", "atop", "dump", "shadow", "ssh", "passwd", "sudoers",
    "systemd", "init.", "resolv",
)

PATH_ARG_PATTERN = r"^/[A-Za-z0-9._/-]{0,120}$"
# A drive is passed as the bare "C:" form; the "C:\" spelling is refused
# earlier by the shell-token guard, so the pattern stays backslash-free.
DRIVE_ARG_PATTERN = r"^[A-Za-z]:$"

# Dispatch script types (documented values of the dispatch Type parameter).
RUN_TYPE_LINUX = "RunShellScript"
RUN_TYPE_WINDOWS = "RunPowerShellScript"

# The gated dispatch action, as a bare CLI/OpenAPI action name; the CLI layer
# passes it through like any other action. Its RAM permission string is
# declared in full in references/ram-policies.md.
GATED_DISPATCH_ACTION = "RunCommand"

# ---------------------------------------------------------------------------
# Instance power states
# ---------------------------------------------------------------------------
# States in which no console channel can attach.
NON_RUNNING_STATES = ("Stopped", "Pending")
# Transitions: a channel failure here is a lifecycle problem, not a channel
# problem -> hand off.
INTERMEDIATE_STATES = ("Starting", "Stopping")

# ---------------------------------------------------------------------------
# CloudMonitor metric set for the saturation ("system hang") verdict
# (metric names taken from the batch verified read entry for this namespace)
# ---------------------------------------------------------------------------
# (metric_name, meaning, aggregation field present in datapoints)
CMS_METRICS = (
    ("CPUUtilization", "host CPU usage, percent", "Average"),
    ("memory_usedutilization", "guest OS memory usage, percent (needs the "
     "CloudMonitor agent inside the instance)", "Average"),
    ("load_1m", "guest OS 1-minute load average (needs the CloudMonitor "
     "agent)", "Average"),
)

MEM_HIGH_PCT = 90.0
CPU_HIGH_PCT = 90.0
LOAD_PER_VCPU_MIN = 2.0        # load_1m at/above 2x vCPU counts as saturation
HEARTBEAT_FRESH_MINUTES = 10   # Cloud Assistant heartbeat freshness
FS_FULL_PCT = 95.0             # df usage percent in pasted output

# ---------------------------------------------------------------------------
# Canonical customer-visible error patterns (matched case-insensitively on
# the normalized English wording the agent passes via --error-text; when the
# customer quotes a localized message, the agent first maps it onto one of
# these canonical patterns - never invents one).
# ---------------------------------------------------------------------------
ERROR_PATTERNS = {
    "grant_access_dependence": "InvalidDependence.GrantAccess",
    "connection_refused": "Connection refused",
    "state_unsupported": "current state of the resource does not support",
    "blocked_intercept": "blocked",
    "no_password_prompt": "password",
    "too_many_auth_failures": "too many authentication failures",
    "incorrect_login": "incorrect",
    "socket_timeout": "SocketTimeoutException",
    "no_route": "No route to host",
    "timed_out": "timed out",
}

# ---------------------------------------------------------------------------
# Five-layer channel model (the skill's spine; details in
# references/console-channel-diagnosis__diagnosis-playbook.md)
# ---------------------------------------------------------------------------
LAYERS = (
    ("L1", "instance layer", "power state, lifecycle, health status, "
     "scheduled platform events"),
    ("L2", "cloud-configuration layer", "public IP presence, bound security "
     "groups, service-port expectations"),
    ("L3", "channel layer", "which console channel is being used and what "
     "it reports: VNC / management terminal, Workbench, session manager, "
     "one-click connect, Cloud Assistant"),
    ("L4", "guest layer", "inside the instance: saturation/hang, boot "
     "failure, sshd listening, login policy, third-party networking "
     "software"),
    ("L5", "customer-local layer", "local egress IP, security software, "
     "cross-border link, browser / input method / terminal emulator"),
)

# ---------------------------------------------------------------------------
# API allowlist: the only (product, action) pairs the CLI layer will reach.
# Anything else is refused before a subprocess is spawned. This is the
# machine-checked form of the list declared in related_apis.yaml.
# ---------------------------------------------------------------------------
ALLOWED_ACTIONS = {
    ECS_PRODUCT: frozenset({
        "DescribeInstances",
        "DescribeInstancesFullStatus",
        "DescribeCloudAssistantStatus",
        "DescribeInvocations",
        GATED_DISPATCH_ACTION,
    }),
    CMS_PRODUCT: frozenset({"DescribeMetricLast"}),
    # The whitelist keys are PascalCase API action names; every product runs
    # in CLI plugin mode, so the command token is the lowercase hyphenated
    # form (GetCallerIdentity -> get-caller-identity).
    STS_PRODUCT: frozenset({"GetCallerIdentity"}),
}

# The one write-class member of the allowlist. The CLI layer accepts it only
# when the caller explicitly marks the call as the gated dispatch, which only
# the guest-probe confirmation path does.
WRITE_ACTIONS = frozenset({GATED_DISPATCH_ACTION})

# ---------------------------------------------------------------------------
# Deny-on-sight verb prefixes, checked on top of the allowlist so a future
# edit cannot widen it by accident. These are the actions this skill never
# calls, whatever the customer confirms.
# ---------------------------------------------------------------------------
NEVER_ALLOWED_ACTION_PREFIXES = (
    "Delete", "Release", "Reset", "Replace", "Attach", "Detach", "Reboot",
    "Start", "Stop", "Modify", "Update", "Import", "Export", "Revoke",
    "Grant", "Authorize", "Leave", "Join", "Unbind", "Bind", "Put",
    "Install", "Uninstall", "Send", "Deregister", "Cancel", "Redeploy",
    "Terminate", "Create", "Snapshot",
)

# ---------------------------------------------------------------------------
# Handoff targets. Values are either an exact skill name carried by this
# tier's specification, or a descriptive lane label where no name was
# supplied - do not replace a descriptive label with a guessed identifier.
# ---------------------------------------------------------------------------
HANDOFF_SKILLS = {
    "os_fault": "alibabacloud-ecs-linux-os-troubleshooting",
    "instance_state": "area:instance-state-diagnosis",
    "disk_io": "area:resource-bottleneck",
    "disk_capacity": "the disk-capacity diagnosis skill",
    "disk_expand": "area:disk-expand-diagnosis",
    "remote_desktop": "the Windows remote-desktop diagnosis skill",
}

# ---------------------------------------------------------------------------
# Official documentation links (only URLs carried by this batch's verified
# help-document set or quoted from real support conversations; links that
# were not verified stay absent and the skill says so instead of guessing)
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "vnc-login":
        "https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc.md",
    "login-methods":
        "https://help.aliyun.com/zh/ecs/user-guide/guide-and-best-practices-for-logging-into-ecs-5-methods-and-how-to-choose.md",
    "connect-to-instance":
        "https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md",
    "workbench-linux":
        "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-instance-by-using-a-password-or-key.md",
    "workbench-files":
        "https://help.aliyun.com/zh/ecs/user-guide/manage-files.md",
    "security-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/security-overview.md",
    "instance-overview":
        "https://help.aliyun.com/zh/ecs/user-guide/overview-52.md",
    "reset-password":
        "https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance",
    "restart-instances":
        "https://help.aliyun.com/zh/ecs/user-guide/restart-instances",
    "snapshots-billing":
        "https://help.aliyun.com/zh/ecs/product-overview/snapshots-1",
    "atop":
        "https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools",
    "mtr":
        "https://help.aliyun.com/zh/ecs/use-cases/use-mtr-tool-for-network-analysis",
    "public-ip":
        "https://help.aliyun.com/zh/ecs/user-guide/public-ip-address",
    "keep-process-running":
        "https://help.aliyun.com/zh/ecs/configure-linux-to-keep-the-process-running-after-the-ssh-client-is-disconnected",
    "winscp-upload":
        "https://help.aliyun.com/zh/ecs/use-cases/use-winscp-to-upload-a-file-to-a-linux-instance",
    "vnc-url-api":
        "https://help.aliyun.com/zh/ecs/developer-reference/api-ecs-2014-05-26-describeinstancevncurl.md",
}

# ---------------------------------------------------------------------------
# Verdict codes emitted by the decision engine (identifiers only; the human
# wording for each lives in references/console-channel-diagnosis__diagnosis-playbook.md)
# ---------------------------------------------------------------------------
VERDICT_NOT_RUNNING = "L1_channel_cannot_attach"
VERDICT_POWER_TRANSITION = "L1_power_transition_handoff"
VERDICT_HEALTH_EVENT = "L1_platform_event"
VERDICT_GRANT_DEPENDENCE = "L2_grant_dependence_handoff"
VERDICT_PORT_TRIAD = "L2_port_and_ingress_triage"
VERDICT_SATURATION_HANG = "L4_saturation_hang"
VERDICT_BOOT_FAULT = "L4_boot_or_system_file_handoff"
VERDICT_LOGIN_POLICY = "L4_login_policy"
VERDICT_THIRD_PARTY_NETWORK = "L4_third_party_network_stack"
VERDICT_LOCAL_PATH = "L5_local_path_or_egress"
VERDICT_SESSION_CHANNEL_LIMIT = "L3_session_channel_limits"
VERDICT_ALL_GREEN = "no_cloud_side_fault"
VERDICT_ENTRY_GUIDE = "L0_entry_and_usage"
