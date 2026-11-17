"""Constants for the ECS BT (Baota) panel use and access diagnosis skill.

Every lookup table this skill uses is embedded here as code; no data file is
shipped alongside the scripts.

Provenance discipline: symptom patterns, root-cause candidates, whitelisted
probes, self-check templates and hand-off targets below were distilled from
the support-case history of this scenario (entries keep the case ids they came
from) and from the API contracts confirmed for it. Anything not listed here is
never assumed. Where a reading is not obtainable through a verified query, the
report says so instead of guessing.
"""

SKILL_NAME = "alibabacloud-ecs-bt-panel-diagnosis"

# Observability: one session id per process, attached to every CLI call.
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill_name}/{session_id}"
USER_AGENT_FLAG = "--user-agent"

# The aliyun CLI is invoked in argument-list mode only; never through a shell.
CLI_BIN = "aliyun"
CLI_TIMEOUT_SECONDS = 40
MAX_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 1.5

# ecs / sts RPC API versions actually called by this skill.
ECS_API_VERSION = "2014-05-26"
STS_API_VERSION = "2015-04-01"

PRODUCT_ECS = "ecs"
PRODUCT_STS = "sts"

# Pagination ceilings for the informational queries.
DEFAULT_PAGE_SIZE = 50
INSTANCE_SCAN_MAX_PAGES = 8

# Guest dispatch polling: the whitelisted read-only command is dispatched, then
# its status and output are read back through DescribeInvocations.
GUEST_POLL_INTERVAL_SECONDS = 5
GUEST_POLL_MAX_ATTEMPTS = 12
GUEST_COMMAND_TIMEOUT_SECONDS = 60

# Actions whose failures are worth a bounded retry.
TRANSIENT_ERROR_TOKENS = (
    "Throttling",
    "ThrottlingUser",
    "InternalError",
    "ServiceUnavailable",
    "RequestTimeout",
    "SystemBusy",
)

# Authentication failures must be reported with these literals only.
AUTH_ERROR_TOKENS = ("NoPermission", "ImplicitDeny")
CREDENTIAL_ERROR_TOKENS = ("InvalidSecurityToken", "MissingCredential", "NoCredential")

# Redaction applied to every stderr / error / guest-output body before it
# reaches a report: a `bt default` reading embeds the panel password, so guest
# output is masked too, not just CLI errors.
SECRET_VALUE_PATTERNS = (
    r"(AccessKeyId\s*[=:]\s*)\S+",
    r"(AccessKeySecret\s*[=:]\s*)\S+",
    r"(SecurityToken\s*[=:]\s*)\S+",
    r"(Signature\s*[=:]\s*)\S+",
    r"(Password\s*[=:]\s*)\S+",
    r"(password\s*[:=]\s*)\S+",
    r"(Username\s*[=:]\s*)\S+",
)
MASKED = "***REDACTED***"

# ---------------------------------------------------------------------------
# API surface. Parameters are limited to those verified for this scenario;
# anything not listed here is never sent. DescribeSecurityGroupAttribute
# (security-group rule detail), CloudMonitor metric reads and billing/arrears
# queries were NOT verified for this scenario and are therefore absent from
# the scripts and from related_apis.yaml; the report says so and routes those
# readings to the customer's own console instead of guessing.
# ---------------------------------------------------------------------------
API_ECS_DESCRIBE_INSTANCES = "DescribeInstances"
API_ECS_DESCRIBE_INSTANCES_FULL_STATUS = "DescribeInstancesFullStatus"
API_ECS_DESCRIBE_CLOUD_ASSISTANT_STATUS = "DescribeCloudAssistantStatus"
API_ECS_RUN_COMMAND = "RunCommand"
API_ECS_DESCRIBE_INVOCATIONS = "DescribeInvocations"
API_STS_GET_CALLER_IDENTITY = "GetCallerIdentity"

# Instance lifecycle states that stop any panel conclusion: a not-running
# instance makes every access symptom trivially expected.
NON_RUNNING_STATES = ("Pending", "Starting", "Stopping", "Stopped")

# Terminal invocation states of a dispatched guest command.
FINISHED_STATES = ("Success", "Finished", "Failed", "Stopped", "PartialFailed",
                   "Error", "Timeout", "Invalid", "Aborted")
FAILED_STATES = ("Failed", "Stopped", "PartialFailed", "Error", "Timeout",
                 "Invalid", "Aborted")

# Characters that must never appear in a substituted path argument, per shell.
# POSIX: everything that could end the argument or start a new command, plus
# quotes and the escape character. PowerShell: the same intent, minus the
# backslash, which is a legal path separator on Windows.
SHELL_METACHARACTERS = (";", "|", "&", "$", "`", ">", "<", "\\", "\n", "\r",
                        "\"", "'", "(", ")", "{", "}", "*", "?", "[", "]",
                        "!", "~")
WINDOWS_SHELL_METACHARACTERS = (";", "|", "&", "$", "`", ">", "<", "\n", "\r",
                                "\"", "'", "(", ")", "{", "}", "*", "?", "[",
                                "]", "!", "~")

# ---------------------------------------------------------------------------
# Symptom classification. Matching is on ASCII substrings a customer dictates
# or pastes (browsers and panels localise their wording, so only stable
# tokens plus the English forms are matched). Unmatched text -> UNKNOWN, and
# the decision tree then runs on the five access layers.
# ---------------------------------------------------------------------------
CATEGORY_UNREACHABLE_RESET = "UNREACHABLE_CONNECTION_RESET"
CATEGORY_ENTRY_UNKNOWN = "PANEL_ENTRY_UNKNOWN"
CATEGORY_LOGIN_BROKEN = "PANEL_LOGIN_BROKEN"
CATEGORY_SG_BLOCKED = "SG_OR_FIREWALL_BLOCKED"
CATEGORY_PANEL_BAN = "PANEL_SELF_BAN"
CATEGORY_SERVICE_DOWN = "PANEL_OR_WEB_SERVICE_DOWN"
CATEGORY_PANEL_BROKEN = "PANEL_FILES_OR_DEPENDENCY_BROKEN"
CATEGORY_SITE_SSL = "SITE_CERT_OR_HTTPS_MISCONFIG"
CATEGORY_HTTP_ERROR = "SITE_5XX_GATEWAY_ERRORS"
CATEGORY_BLANK_RENDER = "PANEL_BLANK_OR_CRASH_RENDERING"
CATEGORY_RESOURCE = "RESOURCE_EXHAUSTION_SUSPECTED"
CATEGORY_ARREARS = "PLATFORM_ARREARS_SUSPECTED"
CATEGORY_BLACKHOLE = "PLATFORM_DDOS_BLACKHOLE_SUSPECTED"
CATEGORY_ICP = "PLATFORM_ICP_BLOCK_SUSPECTED"
CATEGORY_APP_SECURITY = "APPLICATION_LAYER_SECURITY_SUSPECTED"
CATEGORY_NOT_INSTALLED = "PANEL_NOT_INSTALLED"
CATEGORY_USAGE_GUIDE = "PANEL_USAGE_GUIDE"
CATEGORY_LOCAL_CLIENT = "LOCAL_CLIENT_SUSPECTED"
CATEGORY_UNKNOWN = "UNKNOWN"

ALL_CATEGORIES = (
    CATEGORY_UNREACHABLE_RESET,
    CATEGORY_ENTRY_UNKNOWN,
    CATEGORY_LOGIN_BROKEN,
    CATEGORY_SG_BLOCKED,
    CATEGORY_PANEL_BAN,
    CATEGORY_SERVICE_DOWN,
    CATEGORY_PANEL_BROKEN,
    CATEGORY_SITE_SSL,
    CATEGORY_HTTP_ERROR,
    CATEGORY_BLANK_RENDER,
    CATEGORY_RESOURCE,
    CATEGORY_ARREARS,
    CATEGORY_BLACKHOLE,
    CATEGORY_ICP,
    CATEGORY_APP_SECURITY,
    CATEGORY_NOT_INSTALLED,
    CATEGORY_USAGE_GUIDE,
    CATEGORY_LOCAL_CLIENT,
    CATEGORY_UNKNOWN,
)

# The one quotable customer-facing error code of this scenario. Browser
# wording normalizes onto it before the tree routes on it.
ERROR_CODE_CONNECTION_RESET = "err_connection_reset"

ERROR_CODE_ALIASES = {
    ERROR_CODE_CONNECTION_RESET: (
        "err_connection_reset",
        "connection reset",
        "connection was reset",
        "rejected on connect",
        "reset by peer",
    ),
}

# category -> lowercased substrings. First hit wins; multiple hits are listed.
SYMPTOM_PATTERNS = {
    CATEGORY_UNREACHABLE_RESET: (
        "err_connection_reset", "connection reset",
        "rejected on connect", "cant open the panel", "cannot open the panel",
        "panel won't open", "panel will not open", "panel inaccessible",
        "cannot access the panel", "cannot reach the panel",
    ),
    CATEGORY_ENTRY_UNKNOWN: (
        "forgot", "don't know the address", "do not know the address",
        "lost the address", "no idea what the url", "entry address",
        "find the panel address", "panel address",
    ),
    CATEGORY_LOGIN_BROKEN: (
        "wrong password", "password is not accepted", "account password",
        "locked after", "too many failed", "cannot log in", "can't log in",
        "login failed",
    ),
    CATEGORY_SG_BLOCKED: (
        "security group", "port not open", "only some computers",
        "worked from home not office", "ip changed", "whitelist ip",
    ),
    CATEGORY_PANEL_BAN: (
        "panel firewall", "ip blocked by the panel", "ban ip", "blacklist in the panel",
        "blocked my own ip", "system firewall plugin",
    ),
    CATEGORY_SERVICE_DOWN: (
        "service stopped", "apache stopped", "nginx stopped", "mysql stopped",
        "service died", "process not running", "starts then stops",
    ),
    CATEGORY_PANEL_BROKEN: (
        "port.pl", "panel error", "panel broken", "cannot start the panel",
        "panel service exception", "urllib3", "panel files missing",
    ),
    CATEGORY_SITE_SSL: (
        "certificate", "ssl", "https redirect", "force https", "fullchain",
        "443", "dcv", "domain control validation", "domain verification",
    ),
    CATEGORY_HTTP_ERROR: (
        "502", "504", "bad gateway", "gateway timeout", "connection queue full",
    ),
    CATEGORY_BLANK_RENDER: (
        "white screen", "blank page", "crashes when opening", "flash and close",
    ),
    CATEGORY_RESOURCE: (
        "out of memory", "oom", "killed process", "cpu 100", "cpu high",
        "load average", "disk full", "no space left", "iops",
    ),
    CATEGORY_ARREARS: (
        "arrears", "overdue", "unpaid", "out of balance", "recharge",
    ),
    CATEGORY_BLACKHOLE: (
        "blackhole", "black hole", "ddos", "traffic scrubbing", "isp blocked",
    ),
    CATEGORY_ICP: (
        "icp", "filing", "record blocked", "beian", "filing cancelled",
    ),
    CATEGORY_APP_SECURITY: (
        "webshell", "trojan", "hacked", "defaced", "malicious file",
    ),
    CATEGORY_NOT_INSTALLED: (
        "command not found", "bt: not found", "no bt command", "never installed",
        "which bt",
    ),
    CATEGORY_USAGE_GUIDE: (
        "how to use", "how do i add", "how to create a site", "asp", "iis",
        "upload the file", "which version", "old version", "php 8", "node project",
        "npm install",
    ),
    CATEGORY_LOCAL_CLIENT: (
        "browser", "incognito", "other computer", "phone hotspots", "cleared cache",
        "works on my phone", "proxy", "vpn",
    ),
}
# Matching is English-only end to end: customer wording reaching this skill is
# pasted browser and console text, and references/ and SKILL.md are English.

# ---------------------------------------------------------------------------
# The five access layers of this scenario, in the order the tree walks them.
# Every layer reports tri-state: excluded / hit / no-evidence.
# ---------------------------------------------------------------------------
TRIAGE_LAYERS = (
    {
        "id": "admission",
        "name": "Access admission (security group, then OS firewall, then the "
                "panel's own ban list)",
        "cloud_evidence": "Bound security-group ids (DescribeInstances). Rule "
                          "detail has no verified query here: the customer "
                          "reads it in the console.",
        "guest_evidence": "none whitelisted (iptables/firewalld readers are "
                          "outside the low-risk list) -> customer reading",
        "self_checks": ("os_firewall_state", "panel_ban_list"),
        "wording": "The port the customer tries is not admitted before it "
                   "even reaches the guest.",
    },
    {
        "id": "address-port",
        "name": "Address and port (the panel rarely runs on the install default)",
        "cloud_evidence": "none: no API can see the panel's listening port.",
        "guest_evidence": "customer runs bt default / bt 14 and pastes the "
                          "address line only (never the password line)",
        "self_checks": ("panel_entry_default", "listen_ports"),
        "wording": "The customer is dialling a port the panel does not use. "
                   "Cases T-952279A8 (51973), T-38543E1F (39575), "
                   "T-43233650 (19356): a cloud-side '8888 allowed' reading "
                   "points the diagnosis the wrong way.",
    },
    {
        "id": "service-file",
        "name": "Service and file layer (panel process hung, cert or config "
                "file missing/empty, dependency mismatch)",
        "cloud_evidence": "Cloud Assistant reachability decides whether the "
                          "file layer can be probed at all.",
        "guest_evidence": "whitelisted read-only probes (stat / ls / wc / df / "
                          "findmnt) after per-command consent",
        "self_checks": ("service_status", "dependency_versions"),
        "wording": "Something inside is not running or not where the panel "
                   "expects it.",
    },
    {
        "id": "platform",
        "name": "Platform layer (lifecycle events; arrears, blackhole and ICP "
                "are recognized only, then handed off)",
        "cloud_evidence": "instance status, health and scheduled events "
                          "(DescribeInstances + DescribeInstancesFullStatus)",
        "guest_evidence": "not applicable",
        "self_checks": ("billing_overview",),
        "wording": "The instance itself is fine; something above it is not.",
    },
    {
        "id": "local-client",
        "name": "Customer-local layer (browser cache, proxy, VPN, wrong exit IP)",
        "cloud_evidence": "only reached when every cloud and guest layer above "
                          "is excluded or green",
        "guest_evidence": "not applicable",
        "self_checks": ("local_retest", "proxy_route"),
        "wording": "Server-side everything checked out; cases T-13C89CBC and "
                   "T-8BC236C5 recovered on the customer side.",
    },
)

# ---------------------------------------------------------------------------
# Side-effect-free guest commands. Exactly one command per key; the assembled
# string is re-checked for shell metacharacters and rejected tokens before
# dispatch. These cover the file-layer readings the support threads of this
# scenario actually needed (certificate presence, key panel files, disk
# watermark, mounts). Everything else this scenario reads in dialogs -
# bt default / bt 14, ss, netstat, systemctl, service, top, free, ps,
# iptables, firewall-cmd, openssl version, pip show - stays OUTSIDE the
# whitelist: outside the low-risk list, therefore printed as customer-run
# steps and never executed. That matches how these cases ran: support asked
# the customer to paste most of those readings anyway.
# ---------------------------------------------------------------------------
GUEST_TYPE_LINUX = "RunShellScript"
GUEST_TYPE_WINDOWS = "RunPowerShellScript"

# target_required commands validate --target before the string is assembled.
GUEST_COMMANDS = {
    "stat_path": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("stat", "--"),
        "target_required": True,
        "purpose": "Existence, size and block count of one path.",
        "reports": "Whether one named certificate or panel file exists and is "
                   "empty. Case T-76855857: a certificate path was one "
                   "directory level wrong; case T-84281A4D: port.pl was "
                   "missing.",
        "case_refs": ("T-76855857", "T-84281A4D"),
    },
    "ls_dir": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("ls", "-lh", "--"),
        "target_required": True,
        "purpose": "Long listing of one directory.",
        "reports": "What the panel actually has under a cert or panel "
                   "directory - the comparison behind case T-76855857.",
        "case_refs": ("T-76855857",),
    },
    "wc_lines": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("wc", "-l", "--"),
        "target_required": True,
        "purpose": "Line count of one text file (presence and content volume "
                   "without reading contents).",
        "reports": "An empty or zero-line config/certificate file where the "
                   "panel expects content.",
        "case_refs": ("T-76855857", "T-84281A4D"),
    },
    "df_h": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("df", "-h"),
        "target_required": False,
        "purpose": "Byte usage and free space of every mounted volume.",
        "reports": "The disk-watermark exclusion for the resource area "
                   "(panel and sites stall on full volumes).",
        "case_refs": ("T-7726D6AA",),
    },
    "df_i": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("df", "-i"),
        "target_required": False,
        "purpose": "inode usage per volume.",
        "reports": "inode exhaustion behind 'cannot create new file' failures "
                   "on site directories.",
        "case_refs": (),
    },
    "findmnt": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("findmnt",),
        "target_required": False,
        "purpose": "Mount table: device, mount point, filesystem, options.",
        "reports": "A missing or unexpected mount behind a panel that cannot "
                   "write (data disk gone from the tree).",
        "case_refs": (),
    },
    "du_top": {
        "os": "linux",
        "type": GUEST_TYPE_LINUX,
        "argv": ("du", "-x", "--max-depth=1", "--"),
        "target_required": True,
        "purpose": "Size of each direct child of one directory, without "
                   "crossing mounts.",
        "reports": "Which site directory dominates volume usage before the "
                   "customer's own cleanup decision (cleanup itself is not "
                   "this skill's).",
        "case_refs": ("T-7726D6AA",),
    },
    "get_volume": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-Volume",),
        "target_required": False,
        "purpose": "Health, size and free space of every Windows volume.",
        "reports": "Which volume is full on a Windows instance running a "
                   "panel. NTFS has no cheap inode counter: file-count "
                   "conclusions carry reduced confidence.",
        "case_refs": ("T-EF9EA87F",),
    },
    "get_childitem": {
        "os": "windows",
        "type": GUEST_TYPE_WINDOWS,
        "argv": ("Get-ChildItem", "-Force"),
        "target_required": True,
        "purpose": "Listing of one directory, including hidden entries.",
        "reports": "Presence of panel and site files under a Windows panel "
                   "root. Windows service state and IIS site bindings have "
                   "no whitelisted equivalent: those readings stay manual "
                   "and any conclusion from them is marked low confidence.",
        "case_refs": ("T-EF9EA87F",),
    },
}

# Rejected outright, whatever the caller claims. A whitelist match is
# necessary but not sufficient: this list is re-applied to the assembled
# string. Note the entries this scenario's dialogs actually showed: bt (menu,
# default, 14, start/restart), ss / netstat (listening ports), systemctl and
# service (unit state), top / free / ps (resource readings), iptables /
# firewall-cmd (local firewall), openssl / pip (dependency versions), log
# readers (journalctl, tail, cat) - all deliberately manual.
REJECTED_COMMAND_TOKENS = (
    "bt", "ss", "netstat", "systemctl", "service", "top", "htop", "free", "vmstat",
    "mpstat", "sar", "iostat", "ps", "pgrep", "pidstat", "journalctl", "dmesg",
    "iptables", "ip6tables", "iptables-restore", "nft", "firewall-cmd", "ufw",
    "openssl", "pip", "pip3", "rpm", "dpkg", "yum", "apt", "apt-get", "dnf",
    "mysql", "mysqladmin", "mariadb", "redis-cli", "php", "php-fpm", "nginx",
    "httpd", "apache2ctl", "curl", "wget", "nc", "telnet", "ssh", "scp", "rsync",
    "rm", "rmdir", "mv", "cp", "dd", "truncate", "mkfs", "fdisk", "parted",
    "kill", "pkill", "killall", "reboot", "shutdown", "halt", "poweroff", "init",
    "chattr", "chmod", "chown", "setfacl", "mount", "umount", "echo", "printf",
    "tee", "sed", "awk", "perl", "python", "python3", "sh", "bash", "cat", "head",
    "tail", "grep", "diff", "find", "xargs", "crontab", "passwd", "useradd",
    "usermod", "hostnamectl", "systeminfo", "powershell", "wmic", "reg", "sc",
    "net", "iisreset", "taskkill", "Get-Service", "Stop-Service", "Start-Service",
    "Restart-Service", "Remove-Item", "New-Item", "Set-Content", "Add-Content",
    "Clear-Content", "Invoke-WebRequest", "Invoke-Command", "Restart-Computer",
)

# ---------------------------------------------------------------------------
# Customer self-check templates. These commands are OUTSIDE the guest
# whitelist: the skill prints them for the customer to run in their own
# session (Workbench / SSH / RDP) and pastes the reading back; the skill never
# dispatches them itself. Each entry names what to run, where, what to look
# for in the echo, and the case that proved the reading decisive.
# ---------------------------------------------------------------------------
CUSTOMER_SELFCHECK = {
    "panel_entry_default": {
        "command": "bt default",
        "run_where": "inside the instance over Workbench or SSH (customer session)",
        "read": "The echoed panel address includes the ACTUAL port, plus the "
                "username and password line. Report back only the address and "
                "port - never paste the credential lines.",
        "privacy": "Output contains live panel credentials; anything pasted to "
                   "the conversation is masked by this skill, and the skill "
                   "never asks for the password.",
        "case_refs": ("T-7AD5DAC8", "T-952279A8"),
    },
    "panel_entry_info_menu": {
        "command": "bt 14",
        "run_where": "inside the instance over Workbench or SSH (customer session)",
        "read": "Prints the external and internal access addresses with the "
                "current panel port and the panel path.",
        "privacy": "Same as bt default: paste the address line only.",
        "case_refs": ("T-C9CE1F85", "T-952279A8"),
    },
    "listen_ports": {
        "command": "ss -lntp",
        "run_where": "inside the instance (customer session); not dispatched "
                     "by this skill",
        "read": "Find the port the panel process actually listens on and "
                "whether 80/443 appear at all.",
        "case_refs": ("T-952279A8", "T-21252C12", "T-943A6E7E"),
    },
    "service_status": {
        "command": "systemctl status nginx    (or httpd / mysqld)",
        "run_where": "inside the instance (customer session); not dispatched "
                     "by this skill",
        "read": "active (running) vs failed/dead, plus the last log lines.",
        "case_refs": ("T-943A6E7E", "T-38543E1F"),
    },
    "os_firewall_state": {
        "command": "firewall-cmd --state    and    iptables -S",
        "run_where": "inside the instance (customer session); not dispatched "
                     "by this skill",
        "read": "running vs not running, and whether 80/443/panel-port are "
                "admitted locally. Cases show firewalld/iptables blocking "
                "despite an open security group.",
        "case_refs": ("T-45CF3415", "T-14A38F29"),
    },
    "panel_ban_list": {
        "command": "Panel UI -> Security firewall page: check blocked/allow lists",
        "run_where": "the panel web UI once it is reachable again",
        "read": "The panel's own security plugin can ban the customer's "
                "current exit IP; lift the block or add a whitelist entry in the panel.",
        "case_refs": ("T-943A6E7E",),
    },
    "resource_readings": {
        "command": "top -bn1 | head -n 20    and    free -m",
        "run_where": "inside the instance (customer session); not dispatched "
                     "by this skill",
        "read": "Load average, the top memory and CPU consumers, and available "
                "memory. Paste the first screen back.",
        "case_refs": ("T-E279891E", "T-48B136B7", "T-93C59065"),
    },
    "dependency_versions": {
        "command": "openssl version    and    pip show urllib3",
        "run_where": "inside the instance (customer session); not dispatched "
                     "by this skill",
        "read": "Old OpenSSL against urllib3 v2 breaks the panel service on "
                "startup (case T-C714FE28). Version readings decide whether "
                "the fix is a dependency change - which stays a manual step.",
        "case_refs": ("T-C714FE28",),
    },
    "local_retest": {
        "command": "curl -v http://<public-ip>:<panel-port>/    (run on the "
                   "customer's own machine)",
        "run_where": "the customer's laptop, ideally on a second network",
        "read": "Whether the TCP connect succeeds and what the first response "
                "line says; compare a normal browser vs an incognito window.",
        "case_refs": ("T-13C89CBC", "T-8BC236C5"),
    },
    "proxy_route": {
        "command": "ip route    and    check for VPN/tunnelling software",
        "run_where": "inside the instance (customer session); not dispatched "
                     "by this skill",
        "read": "Third-party tunnelling software can capture internal DNS "
                "ranges and break name resolution for panel features like "
                "package installs.",
        "case_refs": ("T-0F4D1442",),
    },
    "billing_overview": {
        "command": "Console -> Billing -> Account overview",
        "run_where": "the customer's own console",
        "read": "Whether the account has overdue payment; overdue can suspend "
                "pay-as-you-go bandwidth and every public port with it.",
        "case_refs": ("T-C9ABB457",),
    },
}

# ---------------------------------------------------------------------------
# Root-cause candidates, per category. cloud_checks: what the automatic
# read-only queries prove. probe_keys: whitelisted guest readings offered
# under consent. self_checks: customer-run templates above. manual_steps:
# guidance this skill outputs but never executes. handoff: adjacent area.
# ---------------------------------------------------------------------------
CANDIDATES = {
    CATEGORY_UNREACHABLE_RESET: {
        "summary": "The browser cannot establish a connection at all "
                   "(normalized to " + ERROR_CODE_CONNECTION_RESET + "). "
                   "Walk the five access layers before naming any cause.",
        "confidence": "needs layer evidence",
        "cloud_checks": ("instance-exists-running", "bound-security-groups"),
        "probe_keys": (),
        "self_checks": ("panel_entry_default", "listen_ports"),
        "manual_steps": (),
        "handoff": None,
        "case_refs": ("T-8095CBCB", "T-952279A8"),
    },
    CATEGORY_ENTRY_UNKNOWN: {
        "summary": "Forgotten panel address or port. The panel does not keep "
                   "a fixed memorable path: recover the entry from inside "
                   "the instance.",
        "confidence": "high (repeated, recovered the same way)",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": ("panel_entry_default", "panel_entry_info_menu"),
        "manual_steps": (
            "Connect to the instance OS (Workbench or SSH), run bt default or "
            "bt 14, take the address and port from the echo, then check the "
            "security group admits that port before opening it in a browser.",
        ),
        "handoff": None,
        "case_refs": ("T-C9CE1F85", "T-7AD5DAC8"),
    },
    CATEGORY_LOGIN_BROKEN: {
        "summary": "Panel account or password rejected, or the account is "
                   "locked after repeated failures; sometimes the panel "
                   "service itself is the thing that died.",
        "confidence": "medium",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": ("panel_entry_default", "service_status"),
        "manual_steps": (
            "Recover credentials from inside the instance (bt default echo, "
            "or the panel's own reset menu entry the customer runs "
            "themselves). If the instance OS login itself is unusable, the "
            "console password reset is a customer operation: do it after "
            "creating a snapshot from the console first - this skill never "
            "creates snapshots or resets anything.",
        ),
        "handoff": ("login-credential-repair", "The instance OS credential "
                    "is lost; keep this report for the receiving thread."),
        "case_refs": ("T-43233650", "T-4B98459C"),
    },
    CATEGORY_SG_BLOCKED: {
        "summary": "Access admission is missing or too narrow: security-group "
                   "rules not allowing the panel port, or allowed only for "
                   "an IP that is no longer the customer's exit IP.",
        "confidence": "high (largest single cluster of this scenario)",
        "cloud_checks": ("instance-exists-running", "bound-security-groups"),
        "probe_keys": (),
        "self_checks": ("os_firewall_state", "panel_entry_default"),
        "manual_steps": (
            "In the console, open the instance's security group and add an "
            "inbound rule for the panel's ACTUAL port (from the customer "
            "reading, never from a hard-coded default) with the narrowest "
            "source that fits. The one-click 'allow common web ports' entry "
            "exists in the console for a quick first pass.",
        ),
        "handoff": None,
        "case_refs": ("T-8095CBCB", "T-64C4EEC1", "T-7AD5DAC8"),
    },
    CATEGORY_PANEL_BAN: {
        "summary": "The panel is reachable but the customer's own IP got "
                   "banned by the panel's security-plugin fail2ban-style list.",
        "confidence": "medium",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": ("ls_dir",),
        "self_checks": ("panel_ban_list", "local_retest"),
        "manual_steps": (
            "Open the panel security-firewall page from another exit IP (or "
            "inside the instance console) and lift the block or add a "
            "whitelist entry for the customer's current address; unblocking "
            "is a panel action the customer performs.",
        ),
        "handoff": None,
        "case_refs": ("T-943A6E7E",),
    },
    CATEGORY_SERVICE_DOWN: {
        "summary": "Panel or web service is dead/hung while the instance runs "
                   "(the 502/504-and-panel-dead combination recovered by a "
                   "service restart in several cases).",
        "confidence": "medium",
        "cloud_checks": ("instance-exists-running", "assistant-reachable"),
        "probe_keys": (),
        "self_checks": ("service_status", "panel_entry_default"),
        "manual_steps": (
            "Restart the panel service and the affected web service from the "
            "instance console (the customer runs the panel's own restart "
            "entry). This skill never starts or restarts anything. Before "
            "restarting, recommend the customer create a console snapshot; "
            "if a restart recovers it, the earlier state was a hung process "
            "or resource stall - chase frequency with the resource area.",
        ),
        "handoff": ("resource-bottleneck", "recurrences point at resource "
                    "exhaustion; hand this report over."),
        "case_refs": ("T-38543E1F", "T-13B097B7", "T-4C614B5F"),
    },
    CATEGORY_PANEL_BROKEN: {
        "summary": "The panel's own runtime is broken: key file missing "
                   "(port.pl), or a dependency mismatch (urllib3 v2 against "
                   "old OpenSSL) stops it from starting.",
        "confidence": "medium-high once files are probed",
        "cloud_checks": ("instance-exists-running", "assistant-reachable"),
        "probe_keys": ("stat_path", "ls_dir", "wc_lines"),
        "self_checks": ("dependency_versions", "service_status"),
        "manual_steps": (
            "If a named panel file is missing, restoring it and the panel "
            "repair path belong to the customer (with a snapshot first) and, "
            "for panel-internal bugs, to the vendor's official support. This "
            "skill only proves presence/absence and size of files.",
        ),
        "handoff": None,
        "case_refs": ("T-84281A4D", "T-C714FE28"),
    },
    CATEGORY_SITE_SSL: {
        "summary": "Certificate placed at the wrong path or in the wrong "
                   "format for the web server, forced HTTPS without anything "
                   "listening on 443, or an ACME domain-control-validation "
                   "failure.",
        "confidence": "high once path is compared",
        "cloud_checks": ("instance-exists-running", "assistant-reachable"),
        "probe_keys": ("ls_dir", "stat_path"),
        "self_checks": ("listen_ports",),
        "manual_steps": (
            "Compare the error's certificate path against the actual "
            "directory listing (cases showed a one-level path difference and "
            "empty files). Apache-format files go under "
            "/www/server/panel/vhost/cert/<domain>/. Issuing or replacing "
            "certificates is done in the panel or the certificate console by "
            "the customer.",
        ),
        "handoff": None,
        "case_refs": ("T-76855857", "T-21252C12", "T-9B0DD777"),
    },
    CATEGORY_HTTP_ERROR: {
        "summary": "Sites behind the panel return 502/504: upstream (PHP or "
                   "the web service) queue and connection settings, not the "
                   "panel UI itself.",
        "confidence": "medium",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": ("df_h",),
        "self_checks": ("service_status", "resource_readings"),
        "manual_steps": (
            "The customer pastes service status and resource readings; "
            "upstream keepalive / queue tuning and TIME_WAIT policy are "
            "manual configuration changes made by the customer with a "
            "snapshot first.",
        ),
        "handoff": ("resource-bottleneck", "if readings confirm saturation"),
        "case_refs": ("T-EF5FB057", "T-13B097B7"),
    },
    CATEGORY_BLANK_RENDER: {
        "summary": "Panel page renders blank or the window flashes and "
                   "closes: browser-side rendering and client security "
                   "software sit in front; a stale panel build can too.",
        "confidence": "low until cloud layers are excluded",
        "cloud_checks": ("instance-exists-running", "bound-security-groups"),
        "probe_keys": (),
        "self_checks": ("local_retest", "panel_entry_default"),
        "manual_steps": (
            "Incognito window, another browser, another network; if the "
            "echo from the server side is healthy, a panel build issue goes "
            "to the vendor's official support channel.",
        ),
        "handoff": None,
        "case_refs": ("T-13C89CBC",),
    },
    CATEGORY_RESOURCE: {
        "summary": "Resource exhaustion (OOM-killed MySQL, CPU pegged by "
                   "stray processes, full volume) makes the panel and its "
                   "sites unresponsive.",
        "confidence": "needs readings",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": ("df_h", "df_i", "findmnt", "du_top"),
        "self_checks": ("resource_readings", "service_status"),
        "manual_steps": (
            "Disk watermark is probed read-only here; CPU/memory process "
            "detail rides on the customer-pasted readings (the support "
            "threads worked the same way: top came from the customer).",
        ),
        "handoff": ("resource-bottleneck", "process-level analysis and any "
                    "config change move there with this report"),
        "case_refs": ("T-93C59065", "T-48B136B7", "T-7726D6AA", "T-E279891E"),
    },
    CATEGORY_ARREARS: {
        "summary": "Overdue account suspended pay-as-you-go bandwidth: every "
                   "public port, panel included, goes dark while the instance "
                   "says Running.",
        "confidence": "signature-based only (no billing query verified)",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": ("billing_overview",),
        "manual_steps": (
            "The customer checks the billing overview and tops up. No "
            "billing API is verified for this skill, so this is recognized, "
            "not proven.",
        ),
        "handoff": None,
        "case_refs": ("T-C9ABB457",),
    },
    CATEGORY_BLACKHOLE: {
        "summary": "All ports dead on one public IP while the instance is "
                   "Running points at DDoS blackhole; instances are "
                   "independent - a blackhole on one does not touch others.",
        "confidence": "signature-based only",
        "cloud_checks": ("instance-exists-running", "full-status-clean"),
        "probe_keys": (),
        "self_checks": ("local_retest",),
        "manual_steps": (
            "Console anti-DDoS overview shows the blackhole record; it "
            "lifts automatically after the attack ends. Explain instance "
            "independence to calm cross-instance fear.",
        ),
        "handoff": ("attack-blackhole-diagnosis", "blackhole records, "
                    "duration and protection options live there"),
        "case_refs": ("T-86E76038", "T-C3DB3C57"),
    },
    CATEGORY_ICP: {
        "summary": "Domain access shows a filing-interception page, or "
                   "resources referenced by domain break after a cancelled "
                   "ICP filing: a compliance state, not a panel fault.",
        "confidence": "signature-based",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": ("local_retest",),
        "manual_steps": (
            "The customer verifies filing status in the ICP filing console; "
            "sites that reference resources by domain may need rebuilding "
            "against an IP while filing is re-applied.",
        ),
        "handoff": None,
        "case_refs": ("T-36495FE9",),
    },
    CATEGORY_APP_SECURITY: {
        "summary": "Injected or malicious files and defacement are "
                   "application-layer incidents; the panel area only proves "
                   "server-side reachability.",
        "confidence": "out of scope by design",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": (),
        "manual_steps": (
            "State the responsibility boundary plainly: server-layer help "
            "here, application-layer incident response via the dedicated "
            "area.",
        ),
        "handoff": ("host-intrusion-cleanup", "application-layer malware "
                    "response moves there with this report"),
        "case_refs": ("T-1A92AC8C",),
    },
    CATEGORY_NOT_INSTALLED: {
        "summary": "The panel is not installed or its command is gone "
                   "(bt: command not found): this is the install area, not "
                   "this diagnosis.",
        "confidence": "high when the customer echo proves it",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": ("panel_entry_default",),
        "manual_steps": (
            "Installation, image choice and version selection are not this "
            "skill; the customer decides the deployment path themselves.",
        ),
        "handoff": ("install-extension", "panel installation and "
                    "image/version selection live there"),
        "case_refs": ("T-1A92AC8C", "T-9D4FCA66"),
    },
    CATEGORY_USAGE_GUIDE: {
        "summary": "Usage and environment guidance: adding a site (also "
                   "ASP/IIS on Windows panels), uploading files without the "
                   "panel, which versions an image ships.",
        "confidence": "n/a (guidance, not a fault)",
        "cloud_checks": ("instance-exists-running",),
        "probe_keys": (),
        "self_checks": ("panel_entry_default",),
        "manual_steps": (
            "Answer from the official deployment docs in "
            "references/bt-panel-diagnosis__bt-site-config-guide.md; marketplace images "
            "generally ship the latest stable panel build, older pinned "
            "versions are the customer's own install choice.",
        ),
        "handoff": None,
        "case_refs": ("T-EF9EA87F", "T-9D4FCA66", "T-DFBE216E"),
    },
    CATEGORY_LOCAL_CLIENT: {
        "summary": "Browser cache, client security software, or the "
                   "customer's exit IP changed: server-side green, "
                   "local-side problem.",
        "confidence": "last-resort branch",
        "cloud_checks": ("instance-exists-running", "bound-security-groups"),
        "probe_keys": (),
        "self_checks": ("local_retest", "panel_ban_list"),
        "manual_steps": (
            "Incognito window, another browser, another network, then a "
            "curl -v from the customer's machine pasted back.",
        ),
        "handoff": None,
        "case_refs": ("T-13C89CBC", "T-8BC236C5"),
    },
    CATEGORY_UNKNOWN: {
        "summary": "No pattern matched; run the five access layers on "
                   "readings instead of naming a cause.",
        "confidence": "none",
        "cloud_checks": ("instance-exists-running", "bound-security-groups"),
        "probe_keys": (),
        "self_checks": ("panel_entry_default", "listen_ports"),
        "manual_steps": (),
        "handoff": None,
        "case_refs": (),
    },
}

# ---------------------------------------------------------------------------
# Hand-off rules (adjacent areas). Destinations are existing skill names where
# one is delivered, generic console paths where no skill exists yet (the
# requirements note that the neighbour list of this batch was not fixed; a
# not-yet-online area is therefore named by its console path, never invented).
# ---------------------------------------------------------------------------
HANDOFF_RULES = (
    {"when": "SSH (22) or RDP (3389) itself is down and the panel question "
             "follows from that",
     "target": "area:remote-connection-entry / "
               "area:ssh-connection / area:windows-rdp"},
    {"when": "the panel was never installed or the question is image/version "
             "selection",
     "target": "alibabacloud-ecs-install-extension (installation area)"},
    {"when": "volume full / inode exhaustion is the cause and cleanup or "
             "expansion follows",
     "target": "area:disk-expand-diagnosis, then "
               "area:disk-expand-diagnosis"},
    {"when": "CPU/memory/load or an OOM kill needs process-level analysis",
     "target": "area:resource-bottleneck (monitoring readings: "
               "the CloudMonitor console alert rules (no skill here reads alert history))"},
    {"when": "all public ports dead on a Running instance and blackhole is "
             "suspected",
     "target": "area:attack-blackhole-diagnosis"},
    {"when": "overdue payment is suspected",
     "target": "customer console: Billing -> Account overview (no verified "
               "billing query exists for this skill)"},
    {"when": "an ICP filing interception page appears on domain access",
     "target": "customer console: ICP filing status (compliance area; no "
               "verified query exists here)"},
    {"when": "application-layer malware or defacement is in play",
     "target": "area:host-intrusion-cleanup"},
    {"when": "the guest OS itself is corrupt and offline repair is needed",
     "target": "area:instance-state-diagnosis (manual offline "
               "repair; never performed here)"},
    {"when": "the Cloud Assistant agent is missing/stopped/offline and blocks "
             "every guest reading",
     "target": "area:cloud-assistant-diagnosis"},
    {"when": "a non-panel website is slow or unreachable and the panel "
             "itself works",
     "target": "area:web-inaccessible-slow"},
    {"when": "site certificates are managed through the certificate console "
             "instead of the panel",
     "target": "customer console: certificate management (manual)"},
)

# ---------------------------------------------------------------------------
# Panel facts, each anchored to the cases that taught them. No default-port
# assumption is ever applied to a real instance: the reading decides.
# ---------------------------------------------------------------------------
PANEL_FACTS = {
    "entry": (
        "The panel prints its own access URL - address, PORT, entry path and "
        "credentials - only from inside the guest via bt default or bt 14. "
        "The install-time default port is 8888, but observed real ports in "
        "this scenario's cases include 39575, 51973 and 19356: never assume "
        "the port, read it. Cases: T-C9CE1F85, T-7AD5DAC8, T-952279A8."
    ),
    "cert_path": (
        "Per-site panel certificates live under "
        "/www/server/panel/vhost/cert/<domain>/ and must be in the format "
        "the chosen web server accepts; a one-level path error or an empty "
        "file keeps Apache from starting. Case T-76855857."
    ),
    "key_files": (
        "Named panel runtime files (e.g. port.pl) can go missing and keep "
        "the panel from starting; existence and size are whitelisted "
        "readings, restoration is manual. Case T-84281A4D."
    ),
    "dependencies": (
        "The panel service can fail on a Python-dependency mismatch "
        "(urllib3 v2 vs OpenSSL 1.0.2). Reading versions is manual; the fix "
        "(downgrade/repair) is a customer change, snapshot first. Case "
        "T-C714FE28."
    ),
    "local_bans": (
        "The panel's own security plugin keeps its own allow/deny list and "
        "can lock out the customer's current IP - a server-side firewall "
        "layer the cloud security group cannot show. Case T-943A6E7E."
    ),
    "third_party_capture": (
        "Tunnelling/VPN software inside the guest can capture internal DNS "
        "ranges and break resolution behind panel features that fetch "
        "packages. Case T-0F4D1442."
    ),
    "windows": (
        "Windows instances run the panel too (site types like ASP via IIS). "
        "Only volume and directory readings are whitelisted there; panel "
        "service state and IIS bindings have no whitelisted equivalent - "
        "mark any such conclusion low confidence and rely on the customer's "
        "panel UI reading. Case T-EF9EA87F."
    ),
    "responsibility": (
        "The cloud side maintains server-layer reachability; application "
        "code, panel product bugs and third-party plugins go to the vendor "
        "or the application layer. Cases T-1A92AC8C, T-4B98459C (outsourced "
        "credentials), T-DFBE216E (files do not require the panel)."
    ),
}

# ---------------------------------------------------------------------------
# Official documentation references. Group A entries were matched by the
# batch's help-search and are quoted to customers. Group B entries were cited
# by support threads; re-verify each link before quoting it to a new customer.
# ---------------------------------------------------------------------------
HELP_DOCS = (
    {"group": "A", "title": "Purchase a Linux instance from the console and "
     "deploy the BT panel",
     "url": "https://help.aliyun.com/zh/ecs/user-guide/purchase-a-linux-"
            "instance-and-deploy-bt-panel-from-the-console.md",
     "use": "first-use entry flow and port opening (quoted by support in "
            "T-E279891E)"},
    {"group": "A", "title": "Deploy the BT panel",
     "url": "https://help.aliyun.com/zh/ecs/user-guide/installation-of-"
            "pagoda-panel.md",
     "use": "deployment overview; recognizes the 'not installed' hand-off "
            "(T-1A92AC8C)"},
    {"group": "A", "title": "Alibaba Cloud Marketplace mirror images",
     "url": "https://help.aliyun.com/zh/ecs/user-guide/alibaba-cloud-market-"
            "mirror-images.md",
     "use": "image semantics behind version-choice misunderstandings "
            "(T-9D4FCA66)"},
    {"group": "A", "title": "Build a WordPress website on a Windows instance",
     "url": "https://help.aliyun.com/zh/ecs/user-guide/build-a-wordpress-"
            "website-on-a-windows-instance.md",
     "use": "Windows-side web environment reference (T-EF9EA87F)"},
    {"group": "A", "title": "Network connectivity FAQ",
     "url": "https://help.aliyun.com/zh/ecs/network-connectivity-faqs.md",
     "use": "generic reachability wording for the panel-won't-open area"},
    {"group": "B", "title": "Connect to a Linux instance by password or key",
     "url": "https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-linux-"
            "instance-by-using-a-password-or-key",
     "use": "step before bt default; cited by support in T-7AD5DAC8 - "
            "re-verify before quoting"},
    {"group": "B", "title": "Get started with security groups",
     "url": "https://help.aliyun.com/zh/ecs/user-guide/start-using-security-"
            "groups",
     "use": "rule-adding steps incl. the one-click common-web-ports entry; "
            "cited in T-E279891E - re-verify before quoting"},
)

# ---------------------------------------------------------------------------
# explain --topic payloads (short, pointer-shaped; the long form lives in
# references/). Kept as constants so no data file ships with the scripts.
# ---------------------------------------------------------------------------
EXPLAIN_TOPICS = {
    "permission-model": (
        "Class A: the five read-only cloud queries run automatically. "
        "Class B: ONE whitelisted side-effect-free guest command per explicit "
        "customer consent (disclose -> confirm token -> dispatch -> read back "
        "-> mask). There is deliberately NO class C in this skill: no "
        "snapshots, no restarts, no config edits, no resets, nothing written - "
        "fixes are printed as manual steps and this skill then re-verifies "
        "read-only. Class D (destructive) is never executed, ever. See "
        "SKILL.md 'Permission model' and references/bt-panel-diagnosis__bt-readonly-evidence.md."),
    "decision-tree": (
        "Five layers, each reported as excluded / hit / no-evidence: "
        "admission (security group, then OS firewall, then panel ban list) -> "
        "address-port (bt default/bt 14 reading decides) -> service-file "
        "(consented whitelisted probes + customer service readings) -> platform "
        "(lifecycle and events from cloud; arrears/blackhole/ICP recognized "
        "then handed off) -> local-client (last, only when all else is green). "
        "See references/bt-panel-diagnosis__bt-access-triage.md."),
    "panel-entry": (
        "Recover the entry from the guest, not from memory: run bt default or "
        "bt 14 in the instance and report ONLY the address and port. Never "
        "paste credential lines into a conversation. Then confirm the security "
        "group admits that exact port. Case refs: T-C9CE1F85, T-7AD5DAC8, "
        "T-952279A8. See references/bt-panel-diagnosis__bt-site-config-guide.md."),
    "site-config": (
        "Certificates: /www/server/panel/vhost/cert/<domain>/ in the web "
        "server's format; compare error path vs actual listing with the "
        "consented ls/stat probes. Forced HTTPS needs something listening on "
        "443 (ss reading is customer-side). Plugin-level redirect weirdness "
        "is application layer. Case refs: T-76855857, T-21252C12. See "
        "references/bt-panel-diagnosis__bt-site-config-guide.md."),
    "whitelist": (
        "Executable probes (read-only, low-risk list): stat, ls, wc -l, df -h, "
        "df -i, findmnt, du --max-depth=1; Windows: Get-Volume, Get-ChildItem. "
        "Everything else this scenario mentions (bt menu commands, ss, "
        "netstat, systemctl, service, top, free, ps, iptables, firewall-cmd, "
        "openssl, pip, log readers) is REFUSED for dispatch and printed as a "
        "customer self-check instead. See references/bt-panel-diagnosis__bt-readonly-evidence.md."),
    "handoff": (
        "Recognise, summarize, route: installation area, remote-connection "
        "area, disk capacity, resource bottleneck, blackhole, billing "
        "(console path, no verified query), ICP (console path), application "
        "security, offline OS repair, Cloud Assistant itself. "
        "See references/bt-panel-diagnosis__handoff-boundaries.md."),
}
