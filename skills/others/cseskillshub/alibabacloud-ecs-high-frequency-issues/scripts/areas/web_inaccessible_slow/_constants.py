"""Embedded constants and data tables.

Everything the skill knows as *data* lives here as code constants: the ``scripts/``
directory must not contain stand-alone data files. Facts encoded below come from the
verified OpenAPI surface of this tier and from the ticket-derived requirement document;
capabilities that were NOT verified are listed in ``UNVERIFIED_CAPABILITIES`` and are
never implemented as calls.
"""

import re

SKILL_NAME = "alibabacloud-ecs-web-inaccessible-slow"

SKILL_TITLE = "ECS website or API endpoint unreachable / slow - layered troubleshooting"

# ---------------------------------------------------------------------------
# Observability (attached to every CLI invocation)
# ---------------------------------------------------------------------------
UA_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session-id}"

# ---------------------------------------------------------------------------
# Transport discipline: bounded, per-call timeouts and retries
# ---------------------------------------------------------------------------
DEFAULT_TIMEOUT = 60          # seconds, per metadata describe call
GUEST_TIMEOUT = 90            # seconds, per RunCommand / DescribeInvocations call
STS_TIMEOUT = 30              # seconds, credential preflight
MAX_RETRIES = 3               # hard cap: never retry forever
BACKOFF_BASE_SECONDS = 1.5
RETRYABLE_ERROR_CODES = (
    "Throttling",
    "ThrottlingUser",
    "ServiceUnavailable",
    "InternalError",
    "RequestTimeout",
    "SDK.ServerUnreachable",
    "SDK.HttpError",
)
# Authorisation failures are reported by these exact codes (never a generic HTTP word).
DENIAL_ERROR_CODES = ("NoPermission", "ImplicitDeny")

PAGE_SIZE = 50
MAX_PAGES = 10
MAX_ITEMS = 200
MAX_SECURITY_GROUPS = 10

DEFAULT_REGION = "cn-hangzhou"

# API versions actually invoked (aligned with related_apis.yaml).
ECS_API_VERSION = "2014-05-26"
VPC_API_VERSION = "2016-04-28"
ALIDNS_API_VERSION = "2015-01-09"
CMS_API_VERSION = "2019-01-01"
STS_API_VERSION = "2015-04-01"

# ---------------------------------------------------------------------------
# L0 - elements that must be collected before any layer is judged
# ---------------------------------------------------------------------------
REQUIRED_ELEMENTS = (
    ("target", ("--domain or --url or --ip", "What the customer types into the browser or app")),
    ("port", ("--port", "80, 443 or a custom port; 80 vs 443 is a key differential area")),
    ("protocol", ("--protocol", "http or https; decides whether TLS/filing layers apply")),
    ("error_string", ("--error-string or --http-status", "Customer-visible error string or status code; primary key of the decision tree")),
    ("change_history", ("--change", "Most recent change: when, what, by whom, revertible or not")),
    ("impact_scope", ("--scope", "all users / some users / some regions / some resources / some ports")),
)
RECOMMENDED_ELEMENTS = (
    ("--instance-id / --region-id", "Needed for the cloud-side checks; can be derived from the IP but must be confirmed with the customer"),
    ("--client-location / --client-isp / --client-network", "Client region, ISP and network type (home, enterprise, campus, VDI)"),
    ("--window", "Time window for metric reads and log searches"),
)

SCOPE_VALUES = ("all", "some-users", "some-regions", "some-resources", "some-ports", "unknown")
CLIENT_NETWORK_VALUES = ("unknown", "home", "enterprise", "campus", "vdi", "mobile-data")

# ---------------------------------------------------------------------------
# Error string / status code -> family -> first layers to test
# ---------------------------------------------------------------------------
LAYER_NAMES = {
    "L1": "asset and account ownership",
    "L2": "DNS resolution",
    "L3": "public path and intermediate carriers",
    "L4": "cloud-side access control (security groups, cloud firewall, EIP)",
    "L5": "in-guest service, listeners and system firewall",
    "L6": "application and content",
    "L7": "certificate, TLS and filing compliance",
    "L8": "resource capacity and load",
}

ERROR_ROUTES = (
    # (normalised match, family, layer order, reading)
    ("err_connection_timed_out", "drop", ("L4", "L5", "L3"),
     "No TCP answer at all: packets are being discarded somewhere on the path."),
    ("connection refused", "rst", ("L5", "L7", "L4"),
     "A SYN was answered with RST: the packet arrived, so the path is largely fine and "
     "the problem is a missing listener, a loopback bind or a compliance reset."),
    ("err_connection_refused", "rst", ("L5", "L7", "L4"), "See 'connection refused'."),
    ("timed out", "drop", ("L4", "L5", "L3"), "See 'err_connection_timed_out'."),
    ("timeout", "drop", ("L4", "L5", "L3"), "See 'err_connection_timed_out'."),
    ("err_connection_reset", "rst", ("L5", "L7", "L4"),
     "Established or half-open connection torn down; check listeners, then filing reset "
     "behaviour, then any REJECT-shaped rule."),
    ("reset by peer", "rst", ("L5", "L7", "L4"), "See 'err_connection_reset'."),
    ("err_connection_closed", "tls", ("L7", "L6"),
     "Connection closed during handshake or immediately after: TLS version, cipher suite, "
     "SNI or origin-certificate trust."),
    ("err_cert_date_invalid", "cert", ("L7",),
     "Certificate validity window is wrong (expired or not yet valid)."),
    ("certificate", "cert", ("L7",), "Certificate complaint reported by the client."),
    ("http_404", "app", ("L6", "L2"), "Entry file or route missing in the served site root."),
    ("http_405", "app", ("L6", "L3"), "Method rejected - often a peer or edge security policy."),
    ("http_500", "app", ("L6",), "Application fault; read the application error log."),
    ("http_502", "app", ("L6", "L5"), "Reverse proxy cannot reach its backend (backend down, "
     "wrong socket/port, php-fpm not listening)."),
    ("http_504", "app", ("L6", "L8"), "Backend took too long (slow query, slow upstream)."),
    ("http_521", "app", ("L6", "L3"), "Edge node could not reach the origin at all."),
    ("blank page", "app", ("L6", "L5"), "Blank or partially blank page: fatal application error, "
     "tamper-protection module, or injected code."),
    ("white screen", "app", ("L6", "L5"), "See 'blank page'."),
    ("slow", "slow", ("L8", "L6", "L3"), "Slowness must be tested on three lines at once; "
     "never conclude from one line alone."),
    ("port_not_reachable", "drop", ("L4", "L5"), "telnet/nc to the port fails while the host answers ping."),
)

FAMILY_SUMMARY = {
    "drop": "DROP family - silence. Look for rules and devices that discard packets.",
    "rst": "RST family - an answer came back. The path works; look down-stack.",
    "tls": "TLS/handshake family - the socket opened but the secure layer failed.",
    "cert": "Certificate validity or trust.",
    "app": "Application layer - an HTTP answer exists, so the path is proven good.",
    "slow": "Performance - capacity, application time and link quality in parallel.",
    "unknown": "No customer-visible error string captured yet.",
}

# ---------------------------------------------------------------------------
# L2 - DNS record shapes
# ---------------------------------------------------------------------------
PRIVATE_NETWORKS = ("10.", "127.", "192.168.", "169.254.")
PRIVATE_NETWORKS_172 = ("172.16.", "172.17.", "172.18.", "172.19.", "172.20.",
                        "172.21.", "172.22.", "172.23.", "172.24.", "172.25.",
                        "172.26.", "172.27.", "172.28.", "172.29.", "172.30.", "172.31.")
EDGE_PROVIDER_HINTS = ("cdn", "dcdn", "alicdn", "kunlun", "waf", "eds", "ga",
                       "cloudflare", "cf-cloud", "ghs", "cdn301", "er")
CNAME_TYPES = ("CNAME",)
EXPECTED_HOST_RECORDS = ("@", "www")
DNS_LIST_SEMANTICS_STATEMENT = (
    "alidns:DescribeDomainRecords is used only for its list semantics. This skill "
    "never calls a DNS write operation; record changes are output as instructions for the "
    "customer to perform in the DNS console."
)

# ---------------------------------------------------------------------------
# L4 - security group reading
# ---------------------------------------------------------------------------
ADMIN_PORTS = ("22", "3389", "1433", "3306", "6379", "9200", "27017")
FULL_OPEN_CIDRS = ("0.0.0.0/0", "::/0")
POLICY_ACCEPT = "Accept"
POLICY_DROP = "Drop"

# ---------------------------------------------------------------------------
# L5/L6/L8 - in-guest, non-mutating checks
# ---------------------------------------------------------------------------
# The batch low-risk whitelist was authored for the disk-capacity tier (df, du, lsof,
# findmnt, stat, ls, wc). None of the web-path checks below are literally listed there,
# and one (systemctl) is literally excluded. Therefore every entry ships with
# "approved": False: the skill refuses to dispatch, states why, and hands the customer an
# execute-and-paste-back sheet instead of silently widening its own permissions.


def guest_path(*segments):
    """One absolute path inside the customer's instance, composed from its segments."""
    return "/".join(("",) + tuple(segments))


GUEST_CHECKS = {
    "listening-sockets": {
        "argv": ["ss", "-lntp"],
        "fallback_argv": ["netstat", "-lntp"],
        "purpose": "Which ports listen, and on 0.0.0.0 or only on 127.0.0.1",
        "layers": ("L5",),
        "approved": False,
    },
    "firewall-rules": {
        "argv": ["iptables", "-S"],
        "fallback_argv": ["nft", "list", "ruleset"],
        "purpose": "Enumerate packet-filter rules (listing only; rule mutation is never issued)",
        "layers": ("L5",),
        "approved": False,
    },
    "service-state": {
        "argv": ["systemctl", "status", "nginx"],
        "fallback_argv": ["service", "nginx", "status"],
        "purpose": "Is the web service alive and enabled at boot",
        "layers": ("L5",),
        "approved": False,
        "note": "systemctl is literally excluded by the current batch whitelist even though "
                "engineers used 'systemctl status firewalld' in ticket T-D57EF39A.",
    },
    "route-table": {
        "argv": ["ip", "route"],
        "fallback_argv": ["route", "-n"],
        "purpose": "Return path and Docker bridge conflicts",
        "layers": ("L5",),
        "approved": False,
    },
    "docker-networks": {
        "argv": ["docker", "network", "ls"],
        "fallback_argv": ["docker", "ps"],
        "purpose": "Extra docker bridge subnets shadowing the service port",
        "layers": ("L5",),
        "approved": False,
    },
    "self-curl": {
        "argv": ["curl", "-sv", "--max-time", "10", "http://127.0.0.1/"],
        "fallback_argv": ["curl", "-sv", "--max-time", "10", "http://localhost/"],
        "purpose": "Loopback self-test of the served port; for name-based virtual hosts the "
                   "operator adds -H 'Host: <site domain>' to the argv",
        "layers": ("L5", "L6"),
        "approved": False,
    },
    "host-files": {
        "argv": ["cat", guest_path("etc", "hosts")],
        "fallback_argv": ["type", "C:\\Windows\\System32\\drivers\\etc\\hosts"],
        "purpose": "Local name overrides and TCP wrappers deny list",
        "layers": ("L2", "L5"),
        "approved": False,
    },
    "resolver-config": {
        "argv": ["cat", guest_path("etc", "resolv.conf")],
        "fallback_argv": ["nslookup", "example.com"],
        "purpose": "nameserver actually in use inside the guest",
        "layers": ("L2",),
        "approved": False,
    },
    "web-error-log": {
        "argv": ["tail", "-n", "80", guest_path("var", "log", "nginx", "error.log")],
        "fallback_argv": ["tail", "-n", "80", guest_path("var", "log", "httpd", "error_log")],
        "purpose": "Tail of the web and PHP error log (append-only read; log truncation is prohibited)",
        "layers": ("L6",),
        "approved": False,
    },
    "connection-sources": {
        "argv": ["ss", "-H", "-tn", "state", "established"],
        "fallback_argv": ["netstat", "-an", "-t"],
        "purpose": "Connection distribution and abnormal source ranges",
        "layers": ("L8",),
        "approved": False,
    },
}

GUEST_APPROVAL_STATEMENT = (
    "STATUS: DEGRADED for in-guest evidence. The guest checks required by this scenario "
    "are not covered by the currently approved low-risk command list, so nothing is "
    "dispatched into the instance. The customer executes them and pastes the readings back."
)

# ---------------------------------------------------------------------------
# Cloud Assistant dispatch shape (only reachable for an approved check)
# ---------------------------------------------------------------------------
CLOUD_ASSISTANT_TYPE_LINUX = "RunShellScript"
CLOUD_ASSISTANT_TYPE_WINDOWS = "RunPowerShellScript"
CLOUD_ASSISTANT_TIMEOUT = 60
INVOKE_POLL_INTERVAL = 5
INVOKE_MAX_POLLS = 24
# Windows readings are guidance-only this release: no Windows command set was approved.
WINDOWS_DISPATCH_ENABLED = False

# ---------------------------------------------------------------------------
# Snapshot-first economics (state the live price caveat when quoting)
# ---------------------------------------------------------------------------
SNAPSHOT_COST_NOTE = ("Snapshot billing reference: a 100 GB disk is roughly 0.016 CNY per hour, "
                      "about 0.4 CNY per day. Prices follow the live official pricing page. "
                      "Delete the snapshot when the work is finished to stop the charge.")
SNAPSHOT_EXEMPTION = "Pure non-mutating diagnosis does not require a snapshot."

# ---------------------------------------------------------------------------
# Capabilities that were NOT verified -> manual guidance, never an API call
# ---------------------------------------------------------------------------
UNVERIFIED_CAPABILITIES = {
    "blackhole-or-ddos-cleaning-state": "L3/L8: no verified describe call; point the customer to the Anti-DDoS console and state the unblocking window there.",
    "icp-or-access-filing-status": "L7: no verified describe call; infer from the symptom combination and label it an inference, then point to the filing console.",
    "cms-namespace-and-metric-names": "L8: the call exists, the metric names were not confirmed; only names supplied by the operator are used.",
    "cdn-waf-ga-onboarding-config": "L3/L4/L6: cross-product configuration is not read; prove it by connecting straight to the origin and compare.",
    "arrears-or-expiry-authoritative-state": "L1: instance list state is an indirect signal; billing centre is authoritative.",
    "multi-region-dial-test": "L3/L7: no verified programmatic probe; hand out the public probe page and ask for the result.",
    "client-egress-ip": "L3: read from the web access log or ask the customer to open a public 'what is my ip' page.",
    "simple-application-server-firewall": "L4: not an ECS security group; identify and hand off.",
    "windows-guest-command-set": "L5/L6: command set unapproved; Windows is guidance-only.",
}

# ---------------------------------------------------------------------------
# Hand-off register (why it is out of scope / what was already excluded / who takes it)
# ---------------------------------------------------------------------------
HANDOFFS = (
    ("Cannot log in to the instance itself, instance hung or down",
     "That is instance health, not an external access path.",
     "alibabacloud-ecs-diagnose / instance operations",
     "Report the instance state that was read and ask for a login-focused ticket."),
    ("Disk full or inodes exhausted",
     "Capacity hygiene, only a side-cause of 5xx here.",
     "disk capacity tier",
     "Mention it as an L6 side observation; do not take over cleanup."),
    ("Writing DNS records",
     "DNS writes are outside this scenario; only the current records are listed.",
     "DNS resolution tier / the customer in the DNS console",
     "Output the exact record that should exist and where to change it."),
    ("CDN, DCDN, ESA, WAF or GA origin and policy tuning",
     "Cross-product edge configuration is not visible or changeable here.",
     "the matching product tier",
     "Show the origin-versus-edge comparison result, then hand over."),
    ("ICP filing or access filing application, change, cancellation",
     "Filing workflow belongs to the filing product.",
     "filing tier / the customer",
     "State the inference, its evidence and the filing console entry point."),
    ("Blackhole unblocking, Anti-DDoS purchase and policy",
     "Mitigation operations are not ECS operations.",
     "DDoS protection tier",
     "State the attack evidence collected (connections, sources, bandwidth)."),
    ("Domain registration, transfer, real-name, redemption",
     "Not an ECS access path.",
     "domain tier",
     "State that resolution content is correct but the domain lifecycle is elsewhere."),
    ("Origin server outside Alibaba Cloud",
     "Traffic may never enter this cloud network.",
     "the customer and their provider",
     "Show the comparison test that isolates the peer side."),
    ("JuShiTa / open platform hosting",
     "Different control plane and network policy.",
     "JuShiTa support channel",
     "Report the asset type that was identified, then hand over."),
    ("Simple Application Server firewall",
     "It is not an ECS security group.",
     "Simple Application Server tier",
     "Report the asset type and the rule to check in its own console."),
    ("Customer-side LAN, enterprise or campus network, VDI",
     "Unobservable from the cloud.",
     "the customer IT team or their carrier",
     "Attach the retest-from-another-network evidence before claiming this."),
    ("Disk I/O as the root cause of slowness",
     "No ticket evidence in this batch; a designed branch would be invented.",
     "re-evaluate when evidence exists",
     "Say explicitly that this cause was not tested."),
)

# ---------------------------------------------------------------------------
# Credential hygiene
# ---------------------------------------------------------------------------
CREDENTIAL_REMINDER = ("If you have shared an account password or any other credential in this "
                       "conversation, change it immediately.")
CREDENTIAL_POLICY = (
    "This skill never asks for, accepts, echoes, stores or transmits a plaintext password, "
    "private key or panel credential. In-guest work goes through Cloud Assistant (passwordless) "
    "or through the customer executing a listed check; console access is authorised through the "
    "console, never by collecting secrets in chat."
)

# ---------------------------------------------------------------------------
# Output contract
# ---------------------------------------------------------------------------
STATUS_OK = "OK"
STATUS_DEGRADED = "DEGRADED"
STATUS_FAIL = "FAIL"

VERDICT_CONFIRMED = "CONFIRMED"
VERDICT_EXCLUDED = "EXCLUDED"
VERDICT_INCONCLUSIVE = "INCONCLUSIVE"

REPORT_SECTIONS = (
    "1. Verdict - which layer failed, or which layers could not be decided",
    "2. Evidence chain - the concrete readings behind the verdict",
    "3. Actions - automated / needs-confirmation / customer-manual / hand-off",
    "4. Next step - after any change, retest and report the NEW error string",
    "5. Not excluded - layers this run could not rule out, and why",
)

AGENT_OFFLINE_DOC = (
    "https://help.aliyun.com/zh/ecs/user-guide/"
    "stop-and-uninstall-the-cloud-assistant-agent.md")
AGENT_OFFLINE_RE = re.compile(
    r"(?:云助手|云监控|云安全中心|插件|\bagent\b)[^。；\n]{0,24}"
    r"(?:失效|消失|不见|离线|停止|停了|没了|未运行|掉线|无法连接)"
    r"|(?:失效|消失|不见|离线|停止|停了|没了)[^。；\n]{0,16}"
    r"(?:云助手|云监控|插件|\bagent\b)", re.I)
AGENT_OFFLINE_PROCEDURE_RE = re.compile(
    r"(?:如何|怎么|怎样|能否|可以|想要?)[^。；\n]{0,12}(?:停止|卸载|关闭|禁用)")
AGENT_OFFLINE_LINES = (
    "Have the customer check the Agent first: plugins vanishing after a reboot "
    "usually mean the Cloud Assistant and monitoring agents were stopped.",
    "Have the customer log in over VNC and start BOTH agents on boot: Cloud Assistant "
    "(`systemctl start aliyun.service`; Aliyun Assist Service on Windows) and the "
    "CloudMonitor plugin `argusagent`.",
    "Have the customer read only after the Agent is online: a stopped Agent accepts "
    "no command, and a forced reboot drops writes still only in memory.",
)


def agent_offline_signal(question):
    text = question or ""
    if AGENT_OFFLINE_PROCEDURE_RE.search(text):
        return False
    return bool(AGENT_OFFLINE_RE.search(text))
