"""Embedded constants for the ECS SSH connection diagnosis skill.

Every table this skill relies on lives here as code constants: no data files are
shipped inside ``scripts/`` (deliverable rule 1.1.2).
"""

SKILL_NAME = "alibabacloud-ecs-ssh-connection"

# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------
# One session id per run, attached to every OpenAPI call so a whole diagnosis
# session can be traced. {skill} / {session_id} are substituted at runtime.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session_id}"

# ---------------------------------------------------------------------------
# CLI behaviour
# ---------------------------------------------------------------------------
ALIYUN_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 60
CLI_MAX_ATTEMPTS = 3
CLI_RETRY_BACKOFF_SECONDS = 1.5
INVOCATION_POLL_ATTEMPTS = 12
INVOCATION_POLL_INTERVAL_SECONDS = 5
MAX_PAGE_SIZE = 50
RAW_OUTPUT_SAMPLE_LIMIT = 3000

# ---------------------------------------------------------------------------
# Products and API versions actually called
# ---------------------------------------------------------------------------
# Single source of truth so related_apis.yaml, references/ram-policies.md and
# the scripts stay aligned.
ECS_PRODUCT = "ecs"
STS_PRODUCT = "sts"
STS_IDENTITY_COMMAND = "GetCallerIdentity"
API_VERSIONS = {
    "ecs": "2014-05-26",
    "sts": "2015-04-01",
}

# (product, cli action) pairs this skill may call. Anything else is out of scope
# and is refused by AliyunCli.call().
CLOUD_API_WHITELIST = frozenset({
    ("ecs", "DescribeInstances"),
    ("ecs", "DescribeSecurityGroupAttribute"),
    ("ecs", "DescribeCloudAssistantStatus"),
    ("ecs", "DescribeInstanceVncUrl"),
    ("ecs", "DescribeInvocations"),
    ("ecs", "RunCommand"),
    (STS_PRODUCT, STS_IDENTITY_COMMAND),
})

# ---------------------------------------------------------------------------
# Credential hygiene
# ---------------------------------------------------------------------------
MASKED = r"\1\2***"
CREDENTIAL_PATTERNS = (
    # key=value, key: value and "key": "value" for every credential-ish key
    r"(?i)([\"']?(?:accesskeyid|accesskeysecret|access_key_id|access_key_secret|"
    r"securitytoken|security_token|bearer_?token|signature|signaturenonce|"
    r"password|passwd)[\"']?\s*[=:]\s*)([^\s,;\"']{4,})",
    # URL query parameters
    r"(?i)([?&](?:accesskeyid|signature|securitytoken|password)=)([^&\s\"']+)",
    # Authorization headers
    r"(?i)(authorization\s*[:=]\s*)([^\s,]+)",
)

# ---------------------------------------------------------------------------
# Transport error handling
# ---------------------------------------------------------------------------
TRANSIENT_ERROR_MARKERS = (
    "throttling",
    "serviceunavailable",
    "internalerror",
    "systembusy",
    "sdk.serverunreachable",
    "read timed out",
    "connection reset by peer",
    "unexpected end of file",
    "http error 429",
    "http error 500",
    "http error 502",
    "http error 503",
    "http error 504",
    "statuscode: 429",
    "statuscode: 5",
)

# Literal service codes quoted when a permission is missing. A denied request is
# reported as NoPermission or ImplicitDeny; no other denial wording is produced.
AUTH_ERROR_MARKERS = (
    "nopermission",
    "implicitdeny",
    "accessdenied",
    "invalidaccesskeyid",
    "unauthorized",
    "securitytokenexpire",
    "missingsecuritytoken",
)

# ---------------------------------------------------------------------------
# Customer-visible error signatures -> triage branch
# ---------------------------------------------------------------------------
# quotable=True marks a string the customer already sees in their own terminal
# and that may therefore be quoted back verbatim in the report.
BRANCH_TCP_UNREACHABLE = "tcp-unreachable"
BRANCH_NO_LISTENER = "no-listener"
BRANCH_RESET = "connection-reset"
BRANCH_AUTHENTICATION = "authentication"
BRANCH_SESSION_DROP = "session-drop"

ERROR_SIGNATURES = (
    ("connection timed out", BRANCH_TCP_UNREACHABLE, True),
    ("operation timed out", BRANCH_TCP_UNREACHABLE, False),
    ("timed out", BRANCH_TCP_UNREACHABLE, True),
    ("timeout", BRANCH_TCP_UNREACHABLE, False),
    ("connection refused", BRANCH_NO_LISTENER, True),
    ("refused", BRANCH_NO_LISTENER, True),
    ("connection reset", BRANCH_RESET, True),
    ("reset by peer", BRANCH_RESET, True),
    ("kex_exchange_identification", BRANCH_RESET, False),
    ("ssh_dispatch_run_fatal", BRANCH_RESET, False),
    ("client_loop: send disconnect", BRANCH_SESSION_DROP, False),
    ("broken pipe", BRANCH_SESSION_DROP, False),
    ("permission denied", BRANCH_AUTHENTICATION, True),
    ("no supported authentication methods", BRANCH_AUTHENTICATION, False),
    ("server refused our key", BRANCH_AUTHENTICATION, False),
    ("invalid user", BRANCH_AUTHENTICATION, False),
    ("too many authentication failures", BRANCH_AUTHENTICATION, False),
    ("host key verification failed", BRANCH_AUTHENTICATION, False),
    ("too many failed logons", BRANCH_AUTHENTICATION, False),
)

BRANCH_ORDER = (
    BRANCH_TCP_UNREACHABLE,
    BRANCH_NO_LISTENER,
    BRANCH_RESET,
    BRANCH_AUTHENTICATION,
    BRANCH_SESSION_DROP,
)

BRANCH_LABELS = {
    BRANCH_TCP_UNREACHABLE: "TCP never reached the SSH port",
    BRANCH_NO_LISTENER: "Reached the host, nothing listening on that port",
    BRANCH_RESET: "Connection was reset after being established",
    BRANCH_AUTHENTICATION: "Authentication was refused",
    BRANCH_SESSION_DROP: "Session drops while connected or when idle",
}

# Quotable strings the report may echo back to the customer.
QUOTABLE_ERROR_STRINGS = (
    "Connection reset",
    "permission denied",
    "Permission denied",
    "timed out",
    "Connection timed out",
    "Connection refused",
)

# sshd_config options this skill interprets.
SSHD_KEY_OPTIONS = (
    "port",
    "passwordauthentication",
    "pubkeyauthentication",
    "permitrootlogin",
    "kbdinteractiveauthentication",
    "usepam",
    "clientaliveinterval",
    "clientalivecountmax",
    "logingracetime",
    "maxstartups",
    "allowusers",
    "allowgroups",
    "denyusers",
)

# ---------------------------------------------------------------------------
# Guest evidence: non-mutating commands this skill may deliver
# ---------------------------------------------------------------------------
# Each entry is one whole command selected by key. The literal is delivered
# verbatim through Cloud Assistant RunCommand (Linux only). A key that is not in
# this table is refused and echoed back as manual guidance instead.
GUEST_COMMAND_WHITELIST = {
    "listening-sockets": {
        "command": "ss -tlnp",
        "category": "port",
        "purpose": "Show every TCP port the instance listens on and which "
                   "process owns it, so port 22 or a custom SSH port can be "
                   "confirmed.",
        "side_effect": "None: query only.",
    },
    "sshd-config": {
        "command": "cat /etc/ssh/sshd_config",
        "category": "sshd",
        "purpose": "Read the SSH daemon configuration so Port, "
                   "PasswordAuthentication, PubkeyAuthentication and "
                   "PermitRootLogin can be evaluated.",
        "side_effect": "None: the file is only read.",
    },
    "ssh-dir-listing": {
        "command": "ls -l /etc/ssh /etc/ssh/sshd_config.d",
        "category": "sshd",
        "purpose": "Confirm whether drop-in configuration files exist and list "
                   "their owners and modes.",
        "side_effect": "None: listing only.",
    },
    "authorized-keys-mode": {
        "command": "ls -ld /root/.ssh /root/.ssh/authorized_keys",
        "category": "file",
        "purpose": "Check the root authorized_keys file exists with a mode SSH "
                   "accepts; a group or world writable path makes key login "
                   "fail.",
        "side_effect": "None: listing only.",
    },
    "login-binary-presence": {
        "command": "ls -l /bin/bash /usr/sbin/sshd "
                   "/usr/lib64/linux-x86-64.so.2",
        "category": "file",
        "purpose": "Confirm the login shell, the SSH daemon binary and the "
                   "runtime helper file are still present after a security "
                   "clean-up.",
        "side_effect": "None: listing only.",
    },
    "firewalld-state": {
        "command": "firewall-cmd --state",
        "category": "firewall",
        "purpose": "Report whether firewalld is running on the instance.",
        "side_effect": "None: status query.",
    },
    "firewalld-ports": {
        "command": "firewall-cmd --list-all",
        "category": "firewall",
        "purpose": "List the zone, services and ports firewalld allows.",
        "side_effect": "None: list query.",
    },
    "ufw-status": {
        "command": "ufw status",
        "category": "firewall",
        "purpose": "List the rules Ubuntu ufw applies to inbound traffic.",
        "side_effect": "None: status query.",
    },
    "nftables-ruleset": {
        "command": "nft list ruleset",
        "category": "firewall",
        "purpose": "List the active nftables ruleset covering the SSH port.",
        "side_effect": "None: rule listing.",
    },
    "iptables-rules": {
        "command": "iptables -S",
        "category": "firewall",
        "purpose": "List the active iptables rules covering the SSH port.",
        "side_effect": "None: rule listing; nothing is flushed or added.",
    },
    "auth-failure-history": {
        "command": "lastb -n 15",
        "category": "auth",
        "purpose": "Show the most recent failed login attempts (username and "
                   "time) recorded by the SSH daemon, so a port that is being "
                   "reached but denied at the authentication layer (brute force, "
                   "or an account locked after repeated failures) can be told "
                   "apart from a port that no traffic ever reaches.",
        "side_effect": "None: reads /var/log/btmp only; unlocks nothing.",
    },
}

GUEST_COMMAND_CATEGORIES = ("port", "sshd", "firewall", "file", "auth")

# Fragments that may never appear in a command this skill runs. Checked against
# the requested command and against the whitelisted literal, so a tampered
# whitelist entry is still refused.
MUTATING_COMMAND_FRAGMENTS = (
    "rm ", "rmdir ", "mv ", "cp ", "dd ", "truncate", "> ", "< ", ">>",
    ";", "&&", "||", "|", "`", "$(", "${", "\n", "\r", "&",
    "kill", "pkill", "reboot", "shutdown", "halt", "poweroff", "init ",
    "systemctl", "service ", "sed -i", "tee ", "chmod", "chown", "chattr",
    "mkfs", "fdisk", "parted", "umount", "mount", "swapoff", "swapon",
    "useradd", "userdel", "usermod", "adduser", "deluser", "passwd",
    "ssh-keygen", "crontab", "docker", "kubectl",
    "iptables -f", "iptables -x", "iptables -d", "iptables -a", "iptables -i",
    "ufw deny", "ufw allow", "ufw limit", "ufw insert", "ufw delete",
    "firewall-cmd --add", "firewall-cmd --remove", "firewall-cmd --change",
    "nft add", "nft delete", "nft flush", "nft create",
    "yum ", "apt ", "apt-get", "dnf ", "pip ", "curl ", "wget", "nc ",
    "history -c", "> /var", "> /etc", "> /root", "sh -c", "bash -c",
)

# ---------------------------------------------------------------------------
# Network classification used for security-group authorization objects
# ---------------------------------------------------------------------------
UNIVERSE_IPV4 = "0.0.0.0/0"
PRIVATE_IPV4_PREFIXES = (
    "0.", "10.", "127.", "169.254.", "192.0.0.", "192.168.", "198.18.",
    "224.", "240.",
) + tuple("172.%d." % second for second in range(16, 32))
# 100.64.0.0/10 is carrier-grade NAT and 100.100.0.0/16 Alibaba Cloud internal
# services: neither is the public address of a customer laptop, so an allow-list
# entry built on them never matches real Internet traffic.
CGNAT_PREFIXES = ("100.64.", "100.100.")
CONSOLE_ORIGIN_PREFIXES = ("100.104.", "100.105.")

DEFAULT_SSH_PORT = 22
DEFAULT_RDP_PORT = 3389

IP_WHY_TOOLS = (
    "https://ip.cn/",
    "https://myip.ipip.net",
    "https://cip.cc/",
)

# ---------------------------------------------------------------------------
# Handoff routing (symptom areas this skill does not own)
# ---------------------------------------------------------------------------
HANDOFFS = {
    "instance-state": "area:instance-state-diagnosis",
    "disk-io": "area:resource-bottleneck",
    "disk-expand": "area:disk-expand-diagnosis",
    "general-inspection": "alibabacloud-ecs-diagnose",
}
HANDOFF_SECURITY = (
    "Alibaba Cloud Security Center or a human security engineer: this skill does "
    "not clean, quarantine, restore or trace intrusions"
)
HANDOFF_CROSS_ACCOUNT = (
    "the account that owns the instance: submit the request from that account or "
    "switch the credentials this skill runs with"
)
