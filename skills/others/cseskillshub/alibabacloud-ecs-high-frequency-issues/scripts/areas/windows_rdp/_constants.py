"""Embedded constants for the Windows RDP diagnosis skill.

Per platform rule MUST 1.1.2, ``scripts/`` may only hold executable code, so
every static reference table (decision tree, error-code taxonomy, guest query
command whitelist, thresholds, failure vocabulary) is embedded here as Python
constants rather than shipped as a separate data file.

This module never reads, prints, stores or passes any credential material.
Authentication is resolved exclusively by the aliyun CLI default credential
chain. The action whitelist is expressed as ``(product, action)`` tuples so the
single write-class dispatch action is named explicitly and unambiguously.
"""

SKILL_NAME = "alibabacloud-ecs-windows-rdp"

# --- Observability -----------------------------------------------------------
# Attached to every CLI invocation so one diagnosis is traceable end to end.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# --- aliyun CLI transport ----------------------------------------------------
CLI_BINARY = "aliyun"
CLI_TIMEOUT_SECONDS = 30
# The guest query dispatch is polled separately, so it gets a longer budget.
CLI_GUEST_POLL_TIMEOUT_SECONDS = 25
CLI_MAX_RETRIES = 3
CLI_BACKOFF_BASE_SECONDS = 1.0
CLI_BACKOFF_MAX_SECONDS = 8.0

# --- Product / API versions --------------------------------------------------
# Every product runs in plugin mode: the CLI subcommand is the
# lowercase-hyphenated form of the PascalCase API action name (the STS identity
# check becomes get-caller-identity).
PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"
PRODUCT_CMS = "cms"
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

PLUGIN_MODE_COMMANDS = {
("sts", "GetCallerIdentity"): "get-caller-identity",
}

# Individual action names (bare, no "product:" prefix, to keep them usable as
# CLI subcommands and safe to echo).
ACTION_DESCRIBE_INSTANCES = "DescribeInstances"
ACTION_DESCRIBE_SECURITY_GROUP_ATTRIBUTE = "DescribeSecurityGroupAttribute"
ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS = "DescribeCloudAssistantStatus"
ACTION_DESCRIBE_INSTANCE_VNC_URL = "DescribeInstanceVncUrl"
ACTION_RUN_COMMAND = "RunCommand"
ACTION_DESCRIBE_INVOCATIONS = "DescribeInvocations"
ACTION_GET_CALLER_IDENTITY = "GetCallerIdentity"

# The complete set of actions this skill may call. Everything outside it is
# refused by the entry script. The one write-class action
# (ecs / RunCommand) is used ONLY to dispatch a single whitelisted non-mutating
# diagnostic command inside the guest, after explicit confirmation.
API_WHITELIST = (
    ("sts", ACTION_GET_CALLER_IDENTITY),
    ("ecs", ACTION_DESCRIBE_INSTANCES),
    ("ecs", ACTION_DESCRIBE_SECURITY_GROUP_ATTRIBUTE),
    ("ecs", ACTION_DESCRIBE_CLOUD_ASSISTANT_STATUS),
    ("ecs", ACTION_DESCRIBE_INSTANCE_VNC_URL),
    ("ecs", ACTION_DESCRIBE_INVOCATIONS),
    ("ecs", ACTION_RUN_COMMAND),  # write-class; gated, non-mutating payload only
)
WHITELIST_DISPLAY = tuple("{0}:{1}".format(p, a) for p, a in API_WHITELIST)

# --- Paging / limits ---------------------------------------------------------
PAGE_SIZE = 50
MAX_PAGES = 10

# --- Network / RDP defaults --------------------------------------------------
DEFAULT_RDP_PORT = 3389
# Ports seen in real tickets as non-default RDP listeners (evidence anchors).
KNOWN_NONDEFAULT_RDP_PORTS = (33890, 16909)

# Mainland-China regions. A Windows instance outside this set, diagnosed for a
# customer connecting from mainland China, is a possible cross-border link case.
MAINLAND_CN_REGION_PREFIX = "cn-"
OVERSEAS_CN_REGIONS = {"cn-hongkong"}  # cn-hongkong is treated as cross-border

# --- Resource-exhaustion thresholds (distilled from ticket readings) ---------
# High memory utilisation is the dominant cause behind "black screen / frozen
# remote desktop" tickets; the operator quotes in the tickets clustered at:
MEMORY_HIGH_PCT = 85
MEMORY_CRITICAL_PCT = 90
# Windows 2025 / 11 images recommend at least this much RAM for the desktop
# stack to render reliably (operator guidance captured from a real ticket).
WINDOWS_DESKTOP_RECOMMENDED_RAM_GIB = 4

# --- Decision tree (fixed order, reproducible) -------------------------------
# Each node: (id, title, what it proves, evidence source). The full prose lives
# in references/windows-rdp__rdp-layered-checklist.md; kept here so report text and the doc
# quote the same node ids.
DIAGNOSIS_STEPS = (
    ("0", "Product and OS disambiguation",
     "Is the target a Windows ECS instance (not Linux, not SWAS/Wuying)?",
     "DescribeInstances OSName/OSType"),
    ("1", "Evidence intake",
     "Error screenshot/code, the exact ip:port dialed, instance id/region, client public IP",
     "operator supplied; missing items are marked, never guessed"),
    ("2", "Cloud-side connection surface",
     "Instance Running, public IP present, region (cross-border), security-group ingress for the target port and its source scope",
     "DescribeInstances + DescribeSecurityGroupAttribute"),
    ("3", "In-guest channel gate",
     "Is Cloud Assistant ready? If not, degrade to client evidence collection",
     "DescribeCloudAssistantStatus"),
    ("4", "In-guest query-only check (one confirmed command)",
     "RDP service stack, actual listener port, internal firewall, local account state, sessions, TerminalServices log",
     "RunCommand (gated) + DescribeInvocations output"),
    ("5", "Resource watermark",
     "CPU / memory saturation behind black-screen and slow-desktop symptoms",
     "in-guest process Top or CloudMonitor console"),
    ("6", "Wrap-up",
     "Root cause, evidence chain, repair-owner attribution, risk and snapshot advice",
     "composed report"),
)

# --- Error-code / error-text taxonomy ----------------------------------------
# Keys are the customer-observable, ASCII error strings and codes only (no
# model-invented codes). Each maps to the known root-cause branch and the
# skill action. The readable version is references/windows-rdp__error-code-taxonomy.md.
ERROR_TAXONOMY = {
    "0xd07": {
        "means": "The sign-in attempt was rejected because the user account is locked.",
        "branch": "account-lockout",
        "action": "query local account state in-guest; guide rescue sign-in + narrow 3389 source; never auto-unlock",
        "confidence": "high for local accounts; domain-joined policy is not visible to these queries",
    },
    "0x204": {
        "means": "The client could not establish an RDP connection to the server.",
        "branch": "client-or-path",
        "action": "verify cloud side + in-guest listener, then emit the client-side evidence checklist",
        "confidence": "medium; often the client device or its network, not the instance",
    },
    "function requested is not supported": {
        "means": "CredSSP / NLA oracle mismatch between the mstsc client and the server.",
        "branch": "nla-credssp",
        "action": "query NLA registry values (read-only); advise the client-side fix manually",
        "confidence": "medium; NLA/certificate causes were operator-inferred in the source tickets",
    },
    "security layer": {
        "means": "Negotiation of the RDP security layer failed.",
        "branch": "nla-credssp",
        "action": "query SecurityLayer / UserAuthentication values; suggest Workbench/VNC bypass",
        "confidence": "medium",
    },
    "an internal error has occurred": {
        "means": "Generic authentication-layer failure surfaced by mstsc.",
        "branch": "sam-lsa",
        "action": "classify as a probable SAM/LSA service state issue; advise rescue sign-in, manual restart and patching",
        "confidence": "low; the source tickets treated this as operator-inferred",
    },
    "sam": {
        "means": "Security Account Manager / Local Security Authority reported it is in an error state.",
        "branch": "sam-lsa",
        "action": "explain the Kerberos/patch/security-software branch; restart + update are manual, never executed here",
        "confidence": "medium",
    },
    "local security authority": {
        "means": "The client could not reach the Local Security Authority during authentication.",
        "branch": "sam-lsa",
        "action": "same branch as SAM/LSA; confirm reachability via a bypass channel",
        "confidence": "medium",
    },
    "credssp": {
        "means": "Credential Security Support Provider negotiation failed.",
        "branch": "nla-credssp",
        "action": "NLA/CredSSP branch; give the client-side remediation as manual guidance",
        "confidence": "medium",
    },
    "nla": {
        "means": "Network Level Authentication is failing or is unsupported by the client.",
        "branch": "nla-credssp",
        "action": "query the server NLA values (read-only); recommend the client adjustment manually",
        "confidence": "medium",
    },
    "password": {
        "means": "Credential reset / password-related failure, including an online reset that failed.",
        "branch": "credential",
        "action": "check Cloud Assistant status (explains online reset failure); give console reset steps (requires console restart)",
        "confidence": "high",
    },
    "please wait": {
        "means": "The session is stuck at 'Please wait' after the password stage.",
        "branch": "session-conflict",
        "action": "query RDP sessions (read-only); advise a manual restart to free the session",
        "confidence": "medium",
    },
    "black screen": {
        "means": "The remote desktop (RDP or VNC) shows a black / blank screen.",
        "branch": "resource-exhaustion",
        "action": "read resource watermark + TerminalServices log; if the guest is wedged, degrade",
        "confidence": "medium",
    },
}

# Branch -> short label used in the report so the reader sees a consistent name.
BRANCH_LABELS = {
    "account-lockout": "Account lockout (often from external brute-force)",
    "client-or-path": "Client device / local network / carrier path",
    "nla-credssp": "NLA / CredSSP security-layer mismatch",
    "sam-lsa": "SAM / LSA (SamSs) service state",
    "credential": "Logon credential / password reset path",
    "session-conflict": "RDP session conflict / resource hold",
    "resource-exhaustion": "CPU / memory saturation of the desktop stack",
    "cloud-side-policy": "Security group or instance state on the cloud side",
    "cross-border": "Mainland <-> overseas public path quality",
    "out-of-scope": "Belongs to another diagnosis area",
}

# --- In-guest query-only command whitelist -----------------------------------
# The ONLY commands this skill may dispatch through the gated Cloud Assistant
# channel. Every payload is a non-mutating query: it lists state and reads logs
# and never changes configuration. The entry script refuses anything not keyed
# here. Full rationale and the operator-run fallback are in
# references/windows-rdp__guest-query-commands.md.
GUEST_QUERY_WHITELIST = {
    "rdp-services": {
        "type": "RunPowerShellScript",
        "description": "Status and startup type of the Remote Desktop service stack.",
        "command": (
            "Get-Service -Name TermService,UmRdpService,SessionEnv,RemoteRegistry "
            "| Format-Table Name,Status,StartType -AutoSize"
        ),
    },
    "rdp-listeners": {
        "type": "RunPowerShellScript",
        "description": "Which local ports are actually listening (find the real RDP port).",
        "command": (
            "Get-NetTCPConnection -State Listen "
            "| Select-Object LocalAddress,LocalPort,OwningProcess "
            "| Sort-Object LocalPort"
        ),
    },
    "rdp-port-registry": {
        "type": "RunPowerShellScript",
        "description": "Configured RDP listener port (read-only registry query).",
        "command": (
            "Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\Wds\\rdpwd\\Tds\\tcp' "
            "| Select-Object -ExpandProperty PortNumber"
        ),
    },
    "rdp-firewall": {
        "type": "RunPowerShellScript",
        "description": "Internal firewall profile state and the Remote Desktop rule group (read-only).",
        "command": (
            "netsh advfirewall show allprofiles state; "
            "Get-NetFirewallRule -DisplayGroup 'Remote Desktop' "
            "| Format-Table Name,Enabled,Direction,Action -AutoSize"
        ),
    },
    "rdp-account": {
        "type": "RunPowerShellScript",
        "description": "Local account enabled state and the local lockout policy (read-only).",
        "command": (
            "Get-LocalUser | Select-Object Name,Enabled; net accounts"
        ),
    },
    "rdp-lockout-events": {
        "type": "RunPowerShellScript",
        "description": "Recent account-lockout security events 4740 (read-only).",
        "command": (
            "Get-WinEvent -FilterHashtable @{LogName='Security';Id=4740} -MaxEvents 10 "
            "| Format-List TimeCreated,Message"
        ),
    },
    "rdp-sessions": {
        "type": "RunPowerShellScript",
        "description": "Current console and RDP sessions (read-only).",
        "command": "query session",
    },
    "rdp-eventlog": {
        "type": "RunPowerShellScript",
        "description": "Recent TerminalServices-LocalSessionManager entries (read-only).",
        "command": (
            "Get-WinEvent -LogName 'Microsoft-Windows-TerminalServices-LocalSessionManager/Operational' "
            "-MaxEvents 15 | Format-List TimeCreated,LevelDisplayName,Message"
        ),
    },
    "rdp-nla": {
        "type": "RunPowerShellScript",
        "description": "RDP-Tcp security layer and NLA values (read-only registry query).",
        "command": (
            "Get-ItemProperty -Path 'HKLM:\\SYSTEM\\CurrentControlSet\\Control\\Terminal Server\\WinStations\\RDP-Tcp' "
            "| Select-Object SecurityLayer,UserAuthentication"
        ),
    },
    "resource-top": {
        "type": "RunPowerShellScript",
        "description": "Top processes by working set and OS memory watermark (read-only).",
        "command": (
            "Get-CimInstance Win32_OperatingSystem "
            "| Select-Object @{N='TotalGB';E={[math]::Round($_.TotalVisibleMemorySize/1MB,1)}},@{N='FreeGB';E={[math]::Round($_.FreePhysicalMemory/1MB,1)}}; "
            "Get-Process | Sort-Object WorkingSet64 -Descending "
            "| Select-Object -First 10 Name,Id,@{N='WorkingSetMB';E={[math]::Round($_.WorkingSet64/1MB,1)}}"
        ),
    },
}
GUEST_WHITELIST_DISPLAY = tuple(sorted(GUEST_QUERY_WHITELIST.keys()))

# --- Handoff matrix (out-of-scope symptom areas) ------------------------------
# Only recognize + hand off; this skill never implements these.
HANDOFF_MATRIX = (
    ("Disk full / OOM root cause / inode", "disk capacity and inode diagnosis area",
     "capacity is another symptom area; hand off after recognizing the trigger"),
    ("Resize requested but partition not applied", "area:disk-expand-diagnosis",
     "expand-effectiveness area"),
    ("Instance will not start / stuck in a transitional state", "area:instance-state-diagnosis",
     "instance lifecycle-state area"),
    ("Disk IO slow / performance below spec", "area:resource-bottleneck",
     "block storage IO area"),
    ("Linux instance / SSH / Workbench timeout", "Linux remote-connection (SSH) diagnosis skill",
     "mstsc cannot connect to a Linux host; protocol and OS do not match"),
    ("Simple Application Server or Wuying Cloud Desktop", "the matching product console / skill",
     "different product; disambiguate first (ticket T-E663A142 mis-routed twice)"),
    ("Snapshot billing / per-usage switch off / refund", "billing and commercial process (human)",
     "commercial flow, out of scope"),
    ("Change OS / change instance spec / add memory", "manual change by the operator",
     "write operations; the skill only states the constraints"),
)

# --- Failure vocabulary ------------------------------------------------------
# Permission failures are reported with these literals ONLY (never a generic
# permission wording).
CODE_NO_PERMISSION = "NoPermission"
CODE_IMPLICIT_DENY = "ImplicitDeny"
CODE_INVALID_CREDENTIAL = "InvalidCredential"
CODE_MISSING_PARAMETER = "MissingParameter"
CODE_CLI_TIMEOUT = "CliTimeout"
CODE_CLI_UNAVAILABLE = "CliUnavailable"
CODE_API_ERROR = "ApiError"
CODE_PARSE_ERROR = "ResponseParseError"
CODE_COMMAND_REFUSED = "CommandNotWhitelisted"
CODE_NOT_CONFIRMED = "ConfirmationRequired"

STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

# Transient conditions worth retrying.
RETRYABLE_MARKERS = (
    "throttling", "throttlingexception", "systembusy", "serviceunavailable",
    "internalerror", "internal failure", "temporar", "connection reset",
    "connection refused", "timed out", "timeout",
    "500", "502", "503", "429",
)

# Conditions that must never be retried.
NON_RETRYABLE_MARKERS = (
    "missingparameter", "invalidparameter", "signaturedoesnotmatch",
    "invalidaccesskeyid", "no permission", "nopermission", "implicitdeny",
    "accessdenied", "notfound", "invalidinstancenotfound",
)

# Credential-chain failures (recovery is to refresh the local CLI config).
CREDENTIAL_ERROR_MARKERS = (
    "invalidaccesskeyid", "signaturedoesnotmatch", "invalidsecuritytoken",
    "securitytokenexpired", "invalidcredential",
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

# --- Manual remediation guidance (never executed by this skill) --------------
# These are console paths / advisory strings the report quotes.
CONSOLE_ENTRIES = {
    "connect_methods": "https://help.aliyun.com/zh/ecs/user-guide/connect-to-instance.md",
    "workbench_windows": "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-windows-instance-through-workbench.md",
    "credentials": "https://help.aliyun.com/zh/ecs/user-guide/instance-logon-credential-management.md",
    "reset_password": "https://help.aliyun.com/zh/ecs/user-guide/reset-the-logon-password-of-an-instance",
    "security_group": "https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md",
    "account_lockout": "https://help.aliyun.com/zh/ecs/for-safety-consideration-have-lock-the-user-account-the-reason-is-that-login-attempt-or-password-change-try-too-much",
    "create_snapshot": "https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot",
    "restart_instances": "https://help.aliyun.com/zh/ecs/user-guide/restart-instances",
    "tracetcp_method": "https://developer.aliyun.com/article/59067",
    "cloudmonitor_agent": "https://help.aliyun.com/zh/cms/cloudmonitor-1-0/user-guide/install-and-uninstall-the-cloudmonitor-agent-for-cpp",
    "my_public_ip_a": "https://cip.cc",
    "my_public_ip_b": "https://ip.elisky.cn",
}

SNAPSHOT_ADVISORY = (
    "Before any manual fix that can interrupt the instance or touch data "
    "(restart, configuration change, spec or OS change), create a snapshot of "
    "the system disk and wait for it to reach 100%. Snapshots are billed until "
    "deleted."
)
