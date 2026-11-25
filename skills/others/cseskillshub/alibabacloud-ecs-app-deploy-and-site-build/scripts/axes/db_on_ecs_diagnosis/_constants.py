"""Static constants for the ECS database-on-ECS diagnosis skill.

Every lookup table the diagnosis needs lives here as a code constant so that
``scripts/`` holds executable code only. Nothing in this module reads, stores
or transmits credential material; the aliyun CLI default credential chain is
the only authentication path used at runtime.

Tier facts encoded below come from the merged ticket set for this tier
(1009 tickets) and from the batch verified low-risk operation list; the two
tier-quotable error strings are ``timed out`` and ``Connection refused``.
"""

SKILL_NAME = "alibabacloud-ecs-db-on-ecs-diagnosis"

# ---------------------------------------------------------------------------
# Observability (User-Agent attached to every single CLI invocation)
# ---------------------------------------------------------------------------
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"
SESSION_ID_LENGTH = 32

# ---------------------------------------------------------------------------
# API surface (kept three-way aligned with related_apis.yaml and
# references/ram-policies.md; see SKILL.md "API whitelist")
# ---------------------------------------------------------------------------
ECS_PRODUCT = "ecs"
ECS_API_VERSION = "2014-05-26"
STS_PRODUCT = "sts"
STS_API_VERSION = "2015-04-01"
CMS_PRODUCT = "cms"
CMS_API_VERSION = "2019-01-01"
DEFAULT_REGION = "cn-hangzhou"

# Query actions may run without a per-call confirmation.
AUTO_ALLOWED_ACTIONS = (
    "GetCallerIdentity",
    "DescribeInstances",
    "DescribeInstancesFullStatus",
    "DescribeInstanceTypes",
    "DescribeCloudAssistantStatus",
    "DescribeInvocations",
    "DescribeMetricLast",
)

# Write-class actions that require the explicit confirm gate described in
# SKILL.md before any call is made.
CONFIRM_GATED_ACTIONS = (
    "RunCommand",
    "CreateSnapshot",
)

# Action name prefixes that must never be issued by this skill, even after a
# customer confirmation. Console entry points and human steps only.
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
# Cloud Assistant execution budget for one dispatched whitelist command.
GUEST_COMMAND_TIMEOUT_SECONDS = 60
# Bounded polling of one invocation result: attempts x interval seconds.
INVOCATION_POLL_INTERVAL_SECONDS = 5
INVOCATION_POLL_MAX_ATTEMPTS = 12
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

# Authentication vocabulary. These are the only literals this skill uses for a
# denied call; the platform rejects the other common HTTP-denied wording.
AUTH_DENIED_CODES = ("NoPermission", "ImplicitDeny")

# ---------------------------------------------------------------------------
# Status / contract tokens
# ---------------------------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAILED = "FAILED"

NEXT_ACTION_NONE = "NONE"
NEXT_ACTION_ASK_REGION = "ASK_REGION_OR_RESOURCE_ID"
NEXT_ACTION_ASK_GUEST_READINGS = "ASK_CUSTOMER_TO_RUN_AND_PASTE"
NEXT_ACTION_CONFIRM_GATE = "AWAIT_EXPLICIT_CONFIRMATION"
NEXT_ACTION_MANUAL_COMMANDS = "CUSTOMER_RUNS_GENERATED_COMMANDS"
NEXT_ACTION_SNAPSHOT_FIRST = "ENSURE_FRESH_SNAPSHOT_BEFORE_CHANGE"
NEXT_ACTION_VERIFY_CREDENTIALS = "RUN_ALIYUN_CONFIGURE"
NEXT_ACTION_RETRY_LATER = "RETRY_TRANSIENT_FAILURE"
NEXT_ACTION_STOP_AND_REPORT = "STOP_AND_REPORT_LIMITATIONS"
NEXT_ACTION_HANDOFF = "HAND_OFF_TO_TARGET_TIER"

VERDICT_UNKNOWN = "UNKNOWN"

# ---------------------------------------------------------------------------
# Database engines and default ports on this tier (ticket-proven set)
# ---------------------------------------------------------------------------
DB_PORTS = {
    "mysql": 3306,
    "mariadb": 3306,
    "sqlserver": 1433,
    "redis": 6379,
    "postgresql": 5432,
    "mongodb": 27017,
}

DB_ENGINE_LABELS = {
    "mysql": "MySQL",
    "mariadb": "MariaDB",
    "sqlserver": "SQL Server",
    "redis": "Redis",
    "postgresql": "PostgreSQL",
    "mongodb": "MongoDB",
}

# Ports whose wide-open ingress is a hardening finding (checklist item 2).
EXPOSED_DB_PORTS = (3306, 6379, 1433, 5432, 27017)

SYMPTOMS = ("connect", "performance", "availability", "deploy")

# ---------------------------------------------------------------------------
# CloudMonitor metrics used for the performance leg.
# Namespace/MetricName set is the small documented core for ECS host metrics;
# memory and disk series only exist when the in-guest CloudMonitor agent
# reports them, so an empty datapoint list is a DEGRADED reading, not a fault.
# ---------------------------------------------------------------------------
CMS_NAMESPACE = "acs_ecs_dashboard"
CMS_METRICS = {
    "cpu": {
        "metric_name": "CPUUtilization",
        "agent_required": False,
        "meaning": "hypervisor-visible CPU utilization percent",
    },
    "memory": {
        "metric_name": "memory_usedutilization",
        "agent_required": True,
        "meaning": "used memory percent reported by the in-guest agent",
    },
    "disk": {
        "metric_name": "diskusage_utilization",
        "agent_required": True,
        "meaning": "filesystem usage percent reported by the in-guest agent",
    },
}
CMS_PERIOD_SECONDS = "300"
CMS_MAX_POINTS_SHOWN = 5

# ---------------------------------------------------------------------------
# Guest command policy.
#
# AUTO_* may be dispatched inside the instance after the confirm gate - ONE
# command per submission, only to read state. HUMAN_ONLY must never be
# dispatched by the skill: they are the batch-approved whitelist gap for this
# tier, so the customer runs them and pastes the output back. State-changing
# commands are refused outright, confirmation included.
# ---------------------------------------------------------------------------
AUTO_GUEST_COMMAND_EXACT = (
    "df -h",
    "df -i",
    "findmnt",
    "lsof +L1",
    "Get-Volume",
    "Get-PSDrive",
)

AUTO_GUEST_COMMAND_FAMILIES = {
    "df": ("-h", "-i", "-P", "--output", "--block-size", "--total", "--no-truncate"),
    "findmnt": ("--target", "--fstab", "--list", "--realpath", "--nofsroot"),
    "stat": (),
    "ls": ("-l", "-1", "-a", "-h", "-d", "-L"),
    "wc": ("-l",),
    "du": ("-x", "-s", "-h", "--max-depth", "--inodes", "--apparent-size"),
    "lsof": ("+L1", "-b"),
    "Get-ChildItem": (
        "-Path", "-Recurse", "-Force", "-File", "-Directory",
        "-Depth", "-ErrorAction",
    ),
}

AUTO_FSUTIL_QUERY_PREFIXES = (
    "fsutil volume diskfree",
    "fsutil fsinfo",
    "fsutil file query",
)

NEVER_AUTO_GUEST_COMMANDS = (
    "rm", "rmdir", "mv", "dd", "truncate", "mkfs", "fdisk", "parted", "fsck",
    "xfs_growfs", "e2fsck", "tune2fs", "growpart", "resize2fs", "mount",
    "umount", "kill", "killall", "pkill", "systemctl", "service", "reboot",
    "shutdown", "halt", "poweroff", "iptables", "ip6tables", "nft",
    "firewall-cmd", "ufw", "chmod", "chown", "useradd", "userdel",
    "usermod", "passwd", "yum", "dnf", "apt", "apt-get", "rpm", "dpkg",
    "crontab", "reg", "netsh", "Stop-Process", "Restart-Service",
    "Stop-Service", "Start-Service", "Set-ItemProperty", "New-Item",
    "Remove-Item", "Format-Volume", "Clear-EventLog",
)

HUMAN_ONLY_GUEST_COMMANDS = (
    "ss -antp", "netstat -antlp", "netstat -an", "systemctl status",
    "free", "free -m", "top", "ps", "dmesg", "last", "iostat", "sar",
    "atop", "vmstat", "pidstat", "mysql", "mysqladmin", "redis-cli",
    "psql", "mongo", "ss -lntup", "Get-Service", "Get-NetTCPConnection",
    "Test-NetConnection", "tasklist", "services.msc",
)

SHELL_METACHARACTERS = (
    ";", "&&", "||", "|", "`", "$(", "${", ">", ">>", "<", "<<", "\n",
    "\\", "\r", "&",
)

# Paths accepted as an argument for whitelist families (du/stat/ls/wc).
GUEST_PATH_RE = r"^/[A-Za-z0-9._/-]{0,120}$"

# ---------------------------------------------------------------------------
# Error-signature table. ``quotable`` marks the two tier-approved strings
# that may be quoted to the customer verbatim; ``ticket-sample`` entries are
# input-matching patterns observed verbatim in customer logs on the source
# tickets and are cited as pasted text only.
# ---------------------------------------------------------------------------
ERROR_SIGNATURES = (
    {
        "id": "SIG_REFUSED",
        "quotable": True,
        "pattern": r"connection refused|refused by|wsaeconnrefused|\b10061\b",
        "meaning": "something answered the connection and rejected it: no "
                   "listener on that port, service down, port number drift, "
                   "or the server-level grant rejects the source host",
        "layer": "listener/bind, then authentication and grant layer",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_TIMEOUT",
        "quotable": True,
        "pattern": r"timed out|\btimeout\b|\b10060\b|etimedout|couldn.t connect|connection attempt failed",
        "meaning": "packets die quietly: a security-group or in-guest "
                   "firewall drop, a third-party filter suite, a stopped "
                   "instance, or a rule that has not propagated yet",
        "layer": "cloud allow-list, then guest packet filters",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_NAME_RESOLUTION",
        "quotable": False,
        "pattern": r"getaddrinfo|temporary failure in name resolution|name or service not known",
        "meaning": "client-side name resolution failed before any connection; "
                   "not an instance fault",
        "layer": "client and DNS",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_LINK_FAILURE",
        "quotable": False,
        "pattern": r"communications link failure",
        "meaning": "driver-level link dropped mid-session (JDBC family); "
                   "service restart, capacity stall or network blip all fit",
        "layer": "availability, then capacity",
        "confidence": "MEDIUM",
    },
    {
        "id": "SIG_HY000_2002",
        "quotable": False,
        "pattern": r"sqlstate\[hy000\] \[2002\]",
        "meaning": "PHP cannot open the connection socket or pipe; classify "
                   "the tail of the pasted line as refused or timeout",
        "layer": "same split as refused vs timeout",
        "confidence": "MEDIUM",
    },
    {
        "id": "SIG_CONNTRACK_FULL",
        "quotable": False,
        "pattern": r"nf_conntrack: table full|dropping packet",
        "meaning": "kernel connection-tracking table overflow drops new "
                   "connections; intermittent timeouts on busy hosts",
        "layer": "guest kernel network stack",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_NO_SPACE",
        "quotable": False,
        "pattern": r"no space left on device",
        "meaning": "byte-full or inode-full: the database cannot open or "
                   "extend its files; often rendered as a connection error",
        "layer": "capacity triage (df -h then df -i)",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_TOO_MANY_CONN",
        "quotable": False,
        "pattern": r"too many connections",
        "meaning": "server connection limit reached; the engine refuses after "
                   "authenticating or before",
        "layer": "database configuration, customer-side",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_ACCESS_DENIED",
        "quotable": False,
        "pattern": r"access denied for user",
        "meaning": "credentials or host grants rejected by MySQL; the "
                   "network path already worked",
        "layer": "authentication and grant layer",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_SQLSERVER_LOGIN",
        "quotable": False,
        "pattern": r"login failed for user|cannot open database requested by the login",
        "meaning": "SQL Server login or default-database mismatch; mixed "
                   "authentication and the account enabled state are the "
                   "ticket-proven causes",
        "layer": "authentication mode, then restore target",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_SERVICE_CRASH",
        "quotable": False,
        "pattern": r"os error 1067|process terminated abortively",
        "meaning": "Windows service crash-loop; the engine error log path is "
                   "in the message tail",
        "layer": "service availability, then capacity",
        "confidence": "MEDIUM",
    },
    {
        "id": "SIG_OOM",
        "quotable": False,
        "pattern": r"killed process|out of memory|oom-killer",
        "meaning": "memory starvation chain: the kernel killed the database; "
                   "small instances hosting real workloads are the pattern",
        "layer": "resource chain (memory), then capacity",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_LOCK_PRESSURE",
        "quotable": False,
        "pattern": r"deadlock found|lock wait timeout",
        "meaning": "business SQL locking, not infrastructure",
        "layer": "database business layer",
        "confidence": "HIGH",
    },
    {
        "id": "SIG_RANSOM_NOTE",
        "quotable": False,
        "pattern": r"your (?:files|databases|data) (?:have been|are) (?:encrypted|backed up)|we have backed up your databases|\.onion",
        "meaning": "attacker note found in the data directory: treat as a "
                   "ransom pattern, preserve the scene first",
        "layer": "security incident",
        "confidence": "HIGH",
    },
)

# ---------------------------------------------------------------------------
# Pasted-output parsing for ``explain`` (and probe results reuse it).
# ---------------------------------------------------------------------------
DF_USAGE_RE = r"(\d{1,3})%"
LISTEN_LINE_RE = r"\b(LISTENING|LISTEN)\b"
LOCALHOST_BIND_RE = r"\b127\.0\.0\.1:\d+|\[::1\]:\d+"
PUBLIC_BIND_RE = r"\b0\.0\.0\.0:\d+|\[::\]:\d+"
# Same match with the port captured, so an exposure verdict can name the number
# instead of just observing that some line looked public.
PUBLIC_BIND_PORT_RE = r"\b(?:0\.0\.0\.0|\[::\]):(\d{1,5})\b"
# A stopped in-guest filter rules it OUT as the blocker; a DROP/REJECT line for
# the port under test implicates it. The two must not share one bucket, and a
# bare chain header is neither - the parser pairs the drop match with a port.
FIREWALL_OFF_RE = (
    r"FirewallD is not running|firewalld is not running"
    r"|Status:\s*not running|Firewall is not operational"
)
FIREWALL_DROP_RE = r"\b(drop|reject)\b"
FIREWALL_PORT_RE = r"\bdpt:\s*\d|\bport\s*=?\s*\d|--dport\b|\b\d{2,5}/tcp\b"

CAPACITY_WARN_PCT = 95

# ---------------------------------------------------------------------------
# Verdict ids used in reports
# ---------------------------------------------------------------------------
VERDICT_INSTANCE_NOT_FOUND = "VERDICT_INSTANCE_NOT_FOUND"
VERDICT_INSTANCE_STOPPED = "VERDICT_INSTANCE_STOPPED"
VERDICT_EXPIRY_PENDING = "VERDICT_EXPIRY_PENDING"
VERDICT_REFUSED = "VERDICT_REFUSED"
VERDICT_TIMEOUT = "VERDICT_TIMEOUT"
VERDICT_NAME_RESOLUTION = "VERDICT_NAME_RESOLUTION"
VERDICT_NO_PUBLIC_IP = "VERDICT_NO_PUBLIC_IP"
VERDICT_SG_PORT_BLOCKED = "VERDICT_SG_PORT_BLOCKED"
VERDICT_PORT_MISMATCH = "VERDICT_PORT_MISMATCH"
VERDICT_PROPAGATION_DELAY = "VERDICT_PROPAGATION_DELAY"
VERDICT_NOT_LISTENING = "VERDICT_NOT_LISTENING"
VERDICT_PORT_LISTENING = "VERDICT_PORT_LISTENING"
VERDICT_BIND_LOCALHOST = "VERDICT_BIND_LOCALHOST"
VERDICT_DYNAMIC_PORT = "VERDICT_DYNAMIC_PORT"
VERDICT_GUEST_FIREWALL = "VERDICT_GUEST_FIREWALL"
VERDICT_THIRD_PARTY_FW = "VERDICT_THIRD_PARTY_FW"
VERDICT_CONNTRACK_FULL = "VERDICT_CONNTRACK_FULL"
VERDICT_HOST_GRANT = "VERDICT_HOST_GRANT"
VERDICT_AUTH_MODE = "VERDICT_AUTH_MODE"
VERDICT_REQUIREPASS = "VERDICT_REQUIREPASS"
VERDICT_CREDENTIAL_DRIFT = "VERDICT_CREDENTIAL_DRIFT"
VERDICT_CAPACITY_FULL = "VERDICT_CAPACITY_FULL"
VERDICT_INODE_FULL = "VERDICT_INODE_FULL"
VERDICT_DELETED_OPEN = "VERDICT_DELETED_OPEN"
VERDICT_OOM_PRESSURE = "VERDICT_OOM_PRESSURE"
VERDICT_CPU_SATURATED = "VERDICT_CPU_SATURATED"
VERDICT_SHARED_FAMILY_RISK = "VERDICT_SHARED_FAMILY_RISK"
VERDICT_PUBLIC_DB_PORT = "VERDICT_PUBLIC_DB_PORT"
VERDICT_RANSOMWARE_PATTERN = "VERDICT_RANSOMWARE_PATTERN"
VERDICT_NEEDS_CLIENT_EVIDENCE = "VERDICT_NEEDS_CLIENT_EVIDENCE"
VERDICT_GATE_NOT_ACKNOWLEDGED = "VERDICT_GATE_NOT_ACKNOWLEDGED"

# These five are declared for spelling parity with
# references/db-on-ecs-diagnosis__connectivity-decision-tree.md and are asserted by the agent after
# reading customer-supplied console rows, listener output, suite answers or
# config checks. The scripts never emit them: absent evidence is reported as
# "not visible at this layer", which is a different statement.
VERDICT_AGENT_ASSERTED_ONLY = (
    "VERDICT_SG_PORT_BLOCKED",
    "VERDICT_NOT_LISTENING",
    "VERDICT_THIRD_PARTY_FW",
    "VERDICT_REQUIREPASS",
    "VERDICT_CREDENTIAL_DRIFT",
)

# ---------------------------------------------------------------------------
# Hand-off targets
# ---------------------------------------------------------------------------
# Skill identifiers are written only where this tier's evidence supplied the
# name. The capacity/inode tier's skill id was never supplied for this tier, so
# it is named by its scope and flagged for confirmation rather than invented.
HANDOFF_SKILLS = {
    "boot": "alibabacloud-ecs-high-frequency-issues",
    "expand": "alibabacloud-ecs-high-frequency-issues",
    "io": "alibabacloud-ecs-high-frequency-issues",
    "capacity": "the ECS disk-capacity and inode tier (skill id to confirm)",
    "generic": "alibabacloud-ecs-diagnose",
}

HANDOFF_PHRASE_TEMPLATE = (
    "Detected problem root cause is {cause} (evidence: {evidence}); that "
    "belongs to {target}. This skill completed the database-side triage, so "
    "the conclusions and evidence list above can be carried into that "
    "session directly."
)

COMMERCIAL_PHRASE = (
    "Changes to packages, refunds and bill detail are handled by the "
    "commercial channel in the billing console - this skill does not act on "
    "orders."
)

INTRUSION_PHRASE = (
    "Suspected intrusion: let a third-party data-recovery specialist handle "
    "decryption, do not pay the ransom note, and do not delete, clean or "
    "reinstall before a snapshot preserving the scene exists."
)

BUSINESS_PHRASE = (
    "SQL tuning, restore wizards and panel or ERP product internals belong "
    "to the customer's DBA or the software vendor; this skill stops at the "
    "platform boundary."
)

# ---------------------------------------------------------------------------
# Hardening standard set (short form for reports; full text in
# references/db-on-ecs-diagnosis__security-hardening-checklist.md)
# ---------------------------------------------------------------------------
HARDENING_ITEMS = (
    "Restrict SSH 22 / RDP 3389 ingress to specific source IPs",
    "Never publish 1433/3306/6379/5432/27017 to 0.0.0.0/0; allow named client IPs",
    "Strong unique passwords; disable unused accounts including sa when unused",
    "Non-default port only together with source restriction, never alone",
    "Rotate credentials after any attack or leaked connection string",
    "Regular disk snapshots plus an automatic snapshot policy",
    "Patch OS and engine; remove unused panels, web and middleware listeners",
    "Cloud Security Center agent on at least the basic tier for alerts",
)

# ---------------------------------------------------------------------------
# Documentation links verified for this tier (from the injected evidence set
# only; nothing below is guessed).
# ---------------------------------------------------------------------------
DOC_LINKS = {
    "login_methods": "https://help.aliyun.com/zh/ecs/user-guide/guide-and-best-practices-for-logging-into-ecs-5-methods-and-how-to-choose.md",
    "free_trial_expiry": "https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md",
    "clone_instances": "https://help.aliyun.com/zh/ecs/user-guide/clone-instances.md",
    "change_spec_crosszone": "https://help.aliyun.com/zh/ecs/user-guide/change-instance-types-across-zones.md",
    "create_snapshot": "https://help.aliyun.com/document_detail/25455.html",
    "snapshot_billing": "https://help.aliyun.com/document_detail/56159.html",
    "delete_snapshot": "https://help.aliyun.com/document_detail/128131.html",
    "auto_snapshot_policy": "https://help.aliyun.com/zh/ecs/user-guide/automatically-create-snapshots/",
    "security_knowledge": "https://help.aliyun.com/knowledge_list/60787.html",
    "security_center_console": "https://yundun.console.aliyun.com/",
    "marketplace_recovery": "https://market.aliyun.com/products/?keywords=%E5%8B%92%E7%B4%A2%E7%97%85%E6%AF%92",
    "shared_instance_families": "https://help.aliyun.com/zh/ecs/user-guide/shared-instance-families",
    "block_storage_performance": "https://help.aliyun.com/zh/ecs/user-guide/block-storage-performance",
    "atop_monitoring": "https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics",
    "swap_knowledge": "https://help.aliyun.com/knowledge_detail/42534.html",
    "reinit_system_disk": "https://help.aliyun.com/zh/ecs/user-guide/re-initialize-a-system-disk",
    "change_spec_subscription": "https://help.aliyun.com/zh/ecs/user-guide/change-the-instance-types-of-subscription-instances",
}

# Honest gap flag for engine-side procedures: no official customer doc URL
# was verified for SQL Server mixed auth, MySQL host grants, redis
# protected-mode or pg_hba (see references/db-on-ecs-diagnosis__database-engine-checks.md).
ENGINE_DOC_GAP_NOTE = (
    "Engine-side procedures come from ticket practice; no official help-doc "
    "URL was verified for them - search before quoting one, never invent."
)


def resolve_default_port(db_type):
    """Return the documented default port for one engine name.

    Pure lookup over ``DB_PORTS``: no I/O and no guessing. An unknown engine
    raises ``ValueError`` on purpose so that a caller can never silently fall
    back to an invented port; the caller turns that into an explicit "ask the
    customer which port the client dials" step instead.
    """
    key = str(db_type or "").strip().lower()
    if key not in DB_PORTS:
        raise ValueError(
            "unsupported database type {0!r}; expected one of: {1}".format(
                db_type, ", ".join(sorted(DB_PORTS))))
    return DB_PORTS[key]
